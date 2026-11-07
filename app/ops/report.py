"""Contrato da saída do verificador: envelope JSON versionado, estados e precedência.

Precedência (também do código de saída): ``fail`` > ``inconclusive`` > ``ok``. Uma falha
comprovada vence a falta de evidência — o sistema está doente independentemente do que
não pôde ser observado — e as checagens inconclusivas continuam visíveis no relatório.
"""

from __future__ import annotations

import enum
import json
import os
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "cartorio_system.ops.check"
SCHEMA_VERSION = "1.0"

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Status(enum.StrEnum):
    OK = "ok"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    # Só em checagem: não selecionada em CARTORIO_OPS_CHECKS, logo não obrigatória.
    SKIPPED = "skipped"
    # Só em sinal: não configurado, ou sem como avaliar porque um pré-requisito falhou.
    NOT_CONFIGURED = "not_configured"
    NOT_EVALUATED = "not_evaluated"


EXIT_CODES: dict[Status, int] = {Status.OK: 0, Status.FAIL: 1, Status.INCONCLUSIVE: 2}

_SEVERITY = {Status.FAIL: 2, Status.INCONCLUSIVE: 1, Status.OK: 0}


def signal(status: Status, reason: str, **facts: object) -> dict[str, Any]:
    return {"status": status.value, "reason": reason, **facts}


def worst(statuses: Iterable[Status]) -> Status | None:
    """O estado mais grave entre os que contam; ``None`` quando nenhum conta."""
    counted = [s for s in statuses if s in _SEVERITY]
    if not counted:
        return None
    return max(counted, key=lambda s: _SEVERITY[s])


@dataclass
class CheckResult:
    name: str
    status: Status
    reason: str
    signals: dict[str, dict[str, Any]] = field(default_factory=dict)
    duration_ms: int | None = None
    # Banco que a conexão da checagem "database" abriu (current_database()). Só circula na
    # memória do processo, até a checagem de backup: nunca entra no relatório.
    observed_database: str | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_signals(
        cls, name: str, signals: dict[str, dict[str, Any]], *, empty_reason: str
    ) -> CheckResult:
        """Estado = o mais grave dos sinais; motivo = o do primeiro sinal com esse estado.

        A ordem de inserção dos sinais é, portanto, a prioridade do motivo exibido.
        """
        statuses = [Status(s["status"]) for s in signals.values()]
        status = worst(statuses)
        if status is None:
            return cls(name, Status.INCONCLUSIVE, empty_reason, signals)
        reason = next(s["reason"] for s in signals.values() if Status(s["status"]) is status)
        return cls(name, status, reason, signals)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "required": self.status is not Status.SKIPPED,
            "reason": self.reason,
            "duration_ms": self.duration_ms,
            "signals": self.signals,
        }


def single(name: str, key: str, status: Status, reason: str, **facts: object) -> CheckResult:
    """Checagem de um sinal só (ex.: diretório ilegível, configuração ausente)."""
    return CheckResult(name, status, reason, {key: signal(status, reason, **facts)})


def config_missing(name: str, variables: list[str]) -> CheckResult:
    return single(name, "config", Status.INCONCLUSIVE, "config_missing", missing=variables)


def config_invalid(name: str, variables: list[str]) -> CheckResult:
    return single(name, "config", Status.INCONCLUSIVE, "config_invalid", invalid=variables)


def overall(checks: Iterable[CheckResult]) -> tuple[Status, str]:
    executed = [c for c in checks if c.status is not Status.SKIPPED]
    if not executed:
        return Status.INCONCLUSIVE, "no_checks_executed"
    status = worst(c.status for c in executed)
    if status is Status.FAIL:
        return status, "check_failed"
    if status is Status.INCONCLUSIVE:
        return status, "check_inconclusive"
    return Status.OK, "all_checks_ok"


def build_report(
    checks: list[CheckResult],
    generated_at: datetime,
    *,
    config_errors: list[str] | None = None,
    release: dict[str, Any] | None = None,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    status, reason = overall(checks)
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_iso(generated_at),
        # Execução do systemd que gerou o relatório: o alerta confere se é a que falhou.
        "invocation_id": invocation_id,
        "overall": status.value,
        "reason": reason,
        "exit_code": EXIT_CODES[status],
        "release": release or {"id": None},
        "config_errors": sorted(config_errors or []),
        "output": {"requested": False},
        "checks": {c.name: c.as_dict() for c in checks},
    }


def mark_output_published(report: dict[str, Any]) -> None:
    report["output"] = {"requested": True, "published": True}


def mark_output_not_published(report: dict[str, Any], error_class: str) -> None:
    """Arquivo pedido e não publicado: sem ele o alerta não tem evidência desta execução.

    Checagens saudáveis viram inconclusivo; falha ou inconclusivo já detectados ficam como
    estão (falha continua vencendo). Chamado ANTES de imprimir: stdout e código de saída
    precisam dizer a mesma coisa.
    """
    report["output"] = {
        "requested": True,
        "published": False,
        "reason": "output_not_published",
        "error_class": error_class,
    }
    if report["overall"] == Status.OK.value:
        report.update(
            overall=Status.INCONCLUSIVE.value,
            reason="output_not_published",
            exit_code=EXIT_CODES[Status.INCONCLUSIVE],
        )


def internal_error_report(
    generated_at: datetime, error: BaseException, invocation_id: str | None = None
) -> dict[str, Any]:
    """Relatório mínimo quando o próprio verificador quebra: inconclusivo, nunca ``fail``.

    Só o nome da classe do erro sai — a mensagem pode carregar DSN ou caminho interno.
    """
    report = build_report([], generated_at, invocation_id=invocation_id)  # inconclusivo
    report.update(reason="verifier_internal_error", error_class=type(error).__name__)
    return report


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Grava num temporário do mesmo diretório e publica por ``os.replace``: um leitor
    nunca vê JSON pela metade."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
