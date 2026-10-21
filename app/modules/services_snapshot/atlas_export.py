"""Exportação do retrato para o Atlas: um arquivo único, sanitizado, com contrato próprio.

Contrato ``cartorio_system.atlas.services_snapshot`` v1.0 — o ÚNICO formato que o Atlas
consome. O formato local (``cartorio_system.services_snapshot.local`` 1.1) continua
interno e livre para mudar; este objeto é montado campo a campo a partir dele, nunca
copiado, e validado contra um esquema fechado antes da troca atômica.

Entradas: só ``latest.json`` e ``last_attempt.json``, já validados pelos validadores do
retrato. Nada de config real exibida, credencial, rede, coleta ou XLSX. A relação com a
tentativa é a conservadora de ``attempt_relation``, observada no instante da exportação:
o Atlas não vê tentativas posteriores, e o arquivo diz isso em ``observada_em``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from app.modules.drive_capture.config import ALIAS_RE, FAMILIES, CaptureConfig
from app.modules.drive_capture.errors import Code, DriveCaptureError
from app.modules.drive_capture.store import RunLock, atomic_write_json, utc_now
from app.modules.services_snapshot.dates import (
    AGE_BANDS,
    COVERAGE_KEYS,
    DATE_FIELDS,
    DUE_BUCKETS,
    FIELD_STATES,
    GROUPS,
    SIGNALS,
    TIMEZONE_NAME,
)
from app.modules.services_snapshot.report import (
    BOOL,
    DATE_RE,
    FAILURE_CODES,
    INT,
    ISO_RE,
    LEGACY_REPORT_VERSION,
    NUM,
    PCT,
    REPORT_FORMAT,
    REPORT_VERSION,
    RUN_RE,
    STAGES,
    TAB_RE,
    ReportRejected,
    _check,
    _enum,
    _obj,
    _opt,
    attempt_relation,
    iso,
    validate_attempt,
    validate_report,
)
from app.modules.services_snapshot.rules import CATEGORIES, PENDING_REASONS, SECTORS

EXPORT_FORMAT = "cartorio_system.atlas.services_snapshot"
EXPORT_VERSION = "1.0"
EXPORT_FILE = "atlas_snapshot.json"
SCOPE = "fonte_piloto_unica"
RELATIONS = ["confirmada", "falhou_depois", "nao_confirmada"]
GAP_TOKENS = {"campo ausente": "campo_ausente", "campo ambíguo": "campo_ambiguo"}
PENDING_TOKENS = dict(
    zip(
        PENDING_REASONS,
        [
            "tabela_nao_unica",
            "tabela_sem_cabecalho",
            "tarefa_ausente",
            "tarefa_duplicada",
            "status_ausente",
            "status_duplicado",
        ],
        strict=True,
    )
)
_READ_TRIES = 3

# --------------------------------------------------------------------------- esquema

_SERVICES = _obj(
    total=INT,
    concluidos=INT,
    cancelados=INT,
    nao_encerrados=INT,
    sem_status=INT,
    status_nao_mapeado=INT,
    categorias=_obj(**{c: INT for c in CATEGORIES}),
)
_GAP = ("union", (INT, _enum(GAP_TOKENS.values())))
_COV = _opt(_obj(**{g: _obj(registros=INT, **{k: INT for k in COVERAGE_KEYS}) for g in GROUPS}))
_AGE = _opt(_obj(base=INT, amostra=INT, faixas=_obj(**{k: INT for k, _ in AGE_BANDS})))
_DUR = _opt(_obj(base=INT, amostra=INT, media_dias=_opt(NUM), mediana_dias=_opt(NUM)))
_DATES_COMMON = {
    "cobertura": _obj(cadastro=_COV, encerramento=_COV),
    "idade_carteira": _AGE,
    "duracao_conclusao": _DUR,
    "duracao_cancelamento": _DUR,
    "sinais": _obj(**{k: _opt(INT) for k in SIGNALS}),
}
_DUE_KEYS = ["validos", "ausentes", "invalidos", *DUE_BUCKETS]
_PRENOTATION = _opt(
    _obj(
        base=INT,
        data_prenotacao=_obj(
            estado_campo=_enum(FIELD_STATES),
            contagens=_opt(_obj(**{k: INT for k in COVERAGE_KEYS})),
            media_dias_desde=_opt(NUM),
            mediana_dias_desde=_opt(NUM),
        ),
        vencimento_informado=_obj(
            estado_campo=_enum(FIELD_STATES),
            contagens=_opt(_obj(**{k: INT for k in _DUE_KEYS})),
        ),
    )
)
_SECTOR = _obj(
    aba=("re", TAB_RE),
    setor=_opt(_enum(SECTORS)),
    situacao=_enum(["interpretada", "pendente"]),
    motivo_pendencia=_opt(_enum(PENDING_TOKENS.values())),
    servicos=_opt(_SERVICES),
    lacunas=_opt(_obj(sem_tarefa=_GAP, sem_responsavel=_GAP, sem_data_de_inicio=_GAP)),
    datas=_opt(
        _obj(
            campos=_obj(**{f: _enum(FIELD_STATES) for f in DATE_FIELDS}),
            **_DATES_COMMON,
            prenotacao=_PRENOTATION,
        )
    ),
)
EXPORT_SCHEMA = _obj(
    formato=_enum([EXPORT_FORMAT]),
    versao=_enum([EXPORT_VERSION]),
    origem=_obj(
        formato_local=_enum([REPORT_FORMAT]),
        versao_local=_enum([REPORT_VERSION]),
        escopo=_enum([SCOPE]),
        fonte_alias=("re", ALIAS_RE.pattern),
        familia=_enum(FAMILIES),
        run_id=("re", RUN_RE),
    ),
    tempos=_obj(
        capturada_em=("re", ISO_RE),
        relatorio_gerado_em=("re", ISO_RE),
        exportado_em=("re", ISO_RE),
        referencia_indicadores=("re", DATE_RE),
        fuso_referencia=_enum([TIMEZONE_NAME]),
    ),
    atualizacao=_obj(
        relacao=_enum(RELATIONS),
        observada_em=("re", ISO_RE),
        tentativa=_opt(
            _obj(
                tentativa_em=("re", ISO_RE),
                resultado=_enum(["sucesso", "falha"]),
                etapa=_opt(_enum(STAGES)),
                codigo=_opt(_enum(FAILURE_CODES)),
                mesmo_run=BOOL,
            )
        ),
    ),
    cobertura=_obj(
        qualidade=_enum(["completa", "parcial"]),
        abas_total=INT,
        abas_interpretadas=INT,
        abas_pendentes=INT,
        abas_sem_vinculo_de_setor=INT,
        status_reconhecido_pct_do_total=PCT,
        status_reconhecido_pct_dos_preenchidos=PCT,
        reconciliacoes_ok=BOOL,
    ),
    agregado=_obj(
        servicos=_SERVICES,
        datas=_obj(
            abas_com_cadastro=("list", ("re", TAB_RE)),
            abas_com_encerramento=("list", ("re", TAB_RE)),
            **_DATES_COMMON,
        ),
    ),
    setores=("list", _SECTOR),
)


class ExportFailed(Exception):
    """Código fixo; nunca carrega valor lido."""

    def __init__(self, code: str, exit_code: int = 2) -> None:
        self.code = code
        self.exit_code = exit_code
        super().__init__(code)


# --------------------------------------------------------------------------- montagem


def _services(item: dict) -> dict:
    return {
        "total": item["total"],
        "concluidos": item["concluidos"],
        "cancelados": item["cancelados"],
        "nao_encerrados": item["nao_encerrados_reconhecidos"],
        "sem_status": item["status_ausente"],
        "status_nao_mapeado": item["status_nao_mapeado"],
        "categorias": {c: item["categorias"][c] for c in CATEGORIES},
    }


def _gap(value: int | str) -> int | str:
    return value if isinstance(value, int) else GAP_TOKENS[value]


def _coverage(cov: dict | None) -> dict | None:
    if cov is None:
        return None
    return {
        g: {"registros": cov[g]["registros"], **{k: cov[g][k] for k in COVERAGE_KEYS}}
        for g in GROUPS
    }


def _age(age: dict | None) -> dict | None:
    if age is None:
        return None
    return {
        "base": age["base"],
        "amostra": age["calculaveis"],
        "faixas": {k: age["faixas"][k] for k, _ in AGE_BANDS},
    }


def _duration(dur: dict | None) -> dict | None:
    if dur is None:
        return None
    return {
        "base": dur["base"],
        "amostra": dur["calculaveis"],
        "media_dias": dur["media_dias"],
        "mediana_dias": dur["mediana_dias"],
    }


def _dates_common(datas: dict) -> dict:
    return {
        "cobertura": {
            "cadastro": _coverage(datas["cobertura"]["cadastro"]),
            "encerramento": _coverage(datas["cobertura"]["encerramento"]),
        },
        "idade_carteira": _age(datas["idade_carteira"]),
        "duracao_conclusao": _duration(datas["duracao_conclusao"]),
        "duracao_cancelamento": _duration(datas["duracao_cancelamento"]),
        "sinais": {k: datas["sinais"][k] for k in SIGNALS},
    }


def _prenotation(datas: dict) -> dict | None:
    pren = datas["prenotacao"]
    if pren is None:
        return None
    data, due = pren["data_prenotacao"], pren["vencimento_informado"]
    counts = mean = median = None
    if data is not None:
        counts = {k: data[k] for k in COVERAGE_KEYS}
        mean, median = data["media_dias_desde"], data["mediana_dias_desde"]
    return {
        "base": pren["base"],
        "data_prenotacao": {
            "estado_campo": datas["campos"]["data_prenotacao"],
            "contagens": counts,
            "media_dias_desde": mean,
            "mediana_dias_desde": median,
        },
        "vencimento_informado": {
            "estado_campo": datas["campos"]["vencimento_prenotacao"],
            "contagens": None if due is None else {k: due[k] for k in _DUE_KEYS},
        },
    }


def _sector(tab: dict) -> dict:
    if tab["situacao"] != "interpretada":
        return {
            "aba": tab["alias"],
            "setor": tab["setor"],
            "situacao": "pendente",
            "motivo_pendencia": PENDING_TOKENS[tab["motivo"]],
            "servicos": None,
            "lacunas": None,
            "datas": None,
        }
    datas = tab["datas"]
    return {
        "aba": tab["alias"],
        "setor": tab["setor"],
        "situacao": "interpretada",
        "motivo_pendencia": None,
        "servicos": _services(tab),
        "lacunas": {
            "sem_tarefa": _gap(tab["sem_tarefa"]),
            "sem_responsavel": _gap(tab["sem_responsavel"]),
            "sem_data_de_inicio": _gap(tab["sem_data_de_inicio"]),
        },
        "datas": {
            "campos": {f: datas["campos"][f] for f in DATE_FIELDS},
            **_dates_common(datas),
            "prenotacao": _prenotation(datas),
        },
    }


def build_export(report: dict, attempt: dict | None, exported_at: datetime) -> dict:
    """``report`` 1.1 e ``attempt`` JÁ validados; nada é repassado sem nome explícito."""
    cap, cob, agg = report["captura"], report["cobertura"], report["agregado"]
    tentativa = None
    if attempt is not None:
        tentativa = {
            "tentativa_em": attempt["tentativa_em"],
            "resultado": attempt["resultado"],
            "etapa": attempt["etapa"],
            "codigo": attempt["codigo"],
            "mesmo_run": attempt["run_id"] == cap["run_id"],
        }
    stamp = iso(exported_at)
    return {
        "formato": EXPORT_FORMAT,
        "versao": EXPORT_VERSION,
        "origem": {
            "formato_local": report["formato"],
            "versao_local": report["versao"],
            "escopo": SCOPE,
            "fonte_alias": report["fonte"]["alias"],
            "familia": report["fonte"]["familia"],
            "run_id": cap["run_id"],
        },
        "tempos": {
            "capturada_em": cap["capturada_em"],
            "relatorio_gerado_em": report["gerado_em"],
            "exportado_em": stamp,
            "referencia_indicadores": report["referencia_temporal"]["data"],
            "fuso_referencia": report["referencia_temporal"]["fuso"],
        },
        "atualizacao": {
            "relacao": attempt_relation(report, attempt),
            "observada_em": stamp,
            "tentativa": tentativa,
        },
        "cobertura": {
            "qualidade": cob["qualidade"],
            "abas_total": cob["abas_total"],
            "abas_interpretadas": len(cob["abas_interpretadas"]),
            "abas_pendentes": len(cob["abas_pendentes"]),
            "abas_sem_vinculo_de_setor": len(cob["abas_sem_vinculo_de_setor"]),
            "status_reconhecido_pct_do_total": cob["status_reconhecido_pct_do_total"],
            "status_reconhecido_pct_dos_preenchidos": cob["status_reconhecido_pct_dos_preenchidos"],
            "reconciliacoes_ok": cob["reconciliacoes_ok"],
        },
        "agregado": {
            "servicos": _services(agg),
            "datas": {
                "abas_com_cadastro": list(agg["datas"]["abas_com_cadastro"]),
                "abas_com_encerramento": list(agg["datas"]["abas_com_encerramento"]),
                **_dates_common(agg["datas"]),
            },
        },
        "setores": [_sector(t) for t in report["abas"]],
    }


def validate_export(export: object) -> None:
    """Esquema fechado + coerência mínima com o próprio objeto. Só caminhos nos erros."""
    _check(export, EXPORT_SCHEMA, "exportacao")
    done = [s for s in export["setores"] if s["situacao"] == "interpretada"]  # type: ignore[index]
    total = export["agregado"]["servicos"]  # type: ignore[index]
    for key in ("total", "concluidos", "cancelados", "nao_encerrados", "sem_status"):
        if total[key] != sum(s["servicos"][key] for s in done):
            raise ReportRejected(f"exportacao.agregado.servicos.{key} (reconciliação)")
    if export["cobertura"]["abas_total"] != len(export["setores"]):  # type: ignore[index]
        raise ReportRejected("exportacao.cobertura.abas_total (reconciliação)")


# --------------------------------------------------------------------------- execução


def _read_pair(out: Path, latest: str, attempt_name: str) -> tuple[bytes | None, bytes | None]:
    def read(path: Path) -> bytes | None:
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    return read(out / latest), read(out / attempt_name)


def _stable_pair(out: Path, latest: str, attempt_name: str) -> tuple[bytes | None, bytes | None]:
    """Os dois arquivos não são uma transação: só aceita o par lido igual duas vezes."""
    for _ in range(_READ_TRIES):
        first = _read_pair(out, latest, attempt_name)
        if first == _read_pair(out, latest, attempt_name):
            return first
    raise ExportFailed("leitura_instavel")


def _decode(raw: bytes, validator: Callable[[object], None]) -> dict:
    try:
        data = json.loads(raw.decode("utf-8"))
        validator(data)
    except (UnicodeDecodeError, ValueError, ReportRejected):
        raise ExportFailed("entrada_invalida") from None
    return data


def export_atlas(
    config: CaptureConfig,
    *,
    out: Path,
    latest: str,
    attempt_name: str,
    clock: Callable[[], datetime] = utc_now,
) -> dict:
    """Gera ``atlas_snapshot.json``. Falha antes da troca preserva a exportação anterior."""
    from app.modules.services_snapshot.pipeline import RefreshFailed, pilot_source

    try:
        source = pilot_source(config)  # mesma regra do refresh: uma fonte, sem pastas
    except RefreshFailed:
        raise ExportFailed("fora_do_recorte_piloto") from None
    try:
        with RunLock(out, "services-snapshot-export-atlas"):
            raw_report, raw_attempt = _stable_pair(out, latest, attempt_name)
            if raw_report is None:
                raise ExportFailed("sem_relatorio", 3)
            report = _decode(raw_report, validate_report)
            attempt = None if raw_attempt is None else _decode(raw_attempt, validate_attempt)
            if report["versao"] == LEGACY_REPORT_VERSION:
                raise ExportFailed("relatorio_sem_datas", 5)
            if (report["fonte"]["alias"], report["fonte"]["familia"]) != (
                source.alias,
                source.family,
            ):
                raise ExportFailed("fonte_divergente")
            export = build_export(report, attempt, clock())
            try:
                validate_export(export)
            except ReportRejected:
                raise ExportFailed("exportacao_invalida") from None
            try:
                atomic_write_json(out / EXPORT_FILE, export)
            except (OSError, DriveCaptureError):
                raise ExportFailed("falha_ao_gravar") from None
    except DriveCaptureError as exc:
        if exc.code == Code.RUN_LOCKED:
            raise ExportFailed("refresh_em_andamento", 4) from None
        raise ExportFailed("erro_local") from None
    return export
