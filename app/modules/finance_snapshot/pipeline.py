"""analyze: leitura offline da geração financeira já capturada → relatório local validado.

Sem rede, sem credencial, sem coletor: só ``state.json``/manifesto/bytes da geração do run
informado, vinculados e conferidos por ``bind_generation`` (o mesmo vínculo do retrato de
serviços) sobre os MESMOS bytes que são interpretados. Recusa config fora do recorte antes
de abrir qualquer conteúdo.

Publicação (``_publish``), depois da validação:
  1. o Markdown é gerado e os dois arquivos são gravados em ``.staging`` — falha aqui não
     toca nada publicado;
  2. promove ``latest.md`` (derivado);
  3. promove ``latest.json`` — PONTO DE COMMIT. Se esta troca falha, o ``latest.md``
     anterior é restaurado (ou removido, se não havia), e o par anterior fica intacto.
Só se a restauração também falhar o resultado é ``publicacao_inconsistente``: o JSON
anterior está intacto, mas o Markdown é o da tentativa recusada — nunca é anunciado como
preservação.
"""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from app.core.logging import get_logger
from app.modules.drive_capture.config import CaptureConfig, FileSource
from app.modules.drive_capture.errors import DriveCaptureError
from app.modules.drive_capture.store import (
    CaptureStore,
    atomic_write_bytes,
    utc_now,
)
from app.modules.finance_snapshot.report import (
    ELIGIBLE,
    FAMILY,
    ReportRejected,
    build_report,
    render_markdown,
    validate_report,
)

logger = get_logger("finance_snapshot")

SNAPSHOT_DIR = "finance_snapshot"
LATEST = "latest.json"
LATEST_MD = "latest.md"


class AnalyzeFailed(Exception):
    def __init__(self, stage: str, code: str) -> None:
        super().__init__(f"{stage}: {code}")
        self.stage = stage
        self.code = code


def finance_source(config: CaptureConfig) -> FileSource:
    if config.folders or len(config.files) != 1 or config.files[0].family != FAMILY:
        raise AnalyzeFailed("configuracao", "fora_do_recorte_financeiro")
    return config.files[0]


def output_dir(config: CaptureConfig) -> Path:
    return config.data_dir / SNAPSHOT_DIR


def analyze(
    config: CaptureConfig,
    run_id: str,
    period: tuple[int, int],
    *,
    clock: Callable[[], datetime] = utc_now,
) -> dict:
    """Relatório publicado. Levanta AnalyzeFailed com etapa e código controlados."""
    from app.modules.services_snapshot.dates import capture_reference
    from app.modules.services_snapshot.pipeline import RefreshFailed, bind_generation
    from app.modules.services_snapshot.xlsx import XlsxError, parse_workbook

    source = finance_source(config)
    try:
        content, _current, manifest = bind_generation(
            CaptureStore(config.data_dir), source.alias, run_id, source.file_id
        )
    except RefreshFailed as failed:
        raise AnalyzeFailed(failed.stage, failed.code) from None
    except DriveCaptureError:
        raise AnalyzeFailed("vinculo", "geracao_indisponivel") from None
    reference = capture_reference(manifest.get("captured_at"))
    if reference is None:
        raise AnalyzeFailed("validacao", "referencia_invalida")
    try:
        sheets = parse_workbook(content)
    except XlsxError:
        raise AnalyzeFailed("leitura", "xlsx_invalido") from None
    report = build_report(
        source_alias=source.alias,
        manifest=manifest,
        period=period,
        reference=reference,
        sheets=sheets,
        generated_at=clock(),
    )
    try:
        validate_report(report)
    except ReportRejected:
        raise AnalyzeFailed("validacao", "relatorio_invalido") from None
    if not any(t["estado"] in ELIGIBLE for t in report["abas"]):
        # Nenhuma aba lida no modelo: publicar seria apresentar recusa como leitura.
        raise AnalyzeFailed("leitura", "nenhuma_aba_no_modelo")
    _publish(output_dir(config), report)
    logger.info("leitura do financeiro publicada (run %s)", report["origem"]["run_id"])
    return report


def _promote(src: Path, dst: Path) -> None:
    os.replace(src, dst)


def _publish(out: Path, report: dict) -> None:
    try:
        md = render_markdown(report).encode("utf-8")
    except Exception:  # relatório já validado; falha aqui é defeito, nunca publicação parcial
        raise AnalyzeFailed("publicacao", "markdown_nao_gerado") from None
    payload = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    stage_json, stage_md = out / f".{LATEST}.staging", out / f".{LATEST_MD}.staging"
    try:
        previous_md = (out / LATEST_MD).read_bytes() if (out / LATEST_MD).is_file() else None
        atomic_write_bytes(stage_json, payload)
        atomic_write_bytes(stage_md, md)
        _promote(stage_md, out / LATEST_MD)
        try:
            _promote(stage_json, out / LATEST)  # ponto de commit
        except OSError:
            _restore_markdown(out, previous_md)
            raise
    except (OSError, DriveCaptureError):
        raise AnalyzeFailed("publicacao", "falha_ao_publicar") from None
    finally:
        with contextlib.suppress(OSError):  # sobra de staging não muda o que foi publicado
            stage_json.unlink(missing_ok=True)
            stage_md.unlink(missing_ok=True)


def _restore_markdown(out: Path, previous: bytes | None) -> None:
    try:
        if previous is None:
            (out / LATEST_MD).unlink(missing_ok=True)
        else:
            atomic_write_bytes(out / LATEST_MD, previous)
    except (OSError, DriveCaptureError):
        raise AnalyzeFailed("publicacao", "publicacao_inconsistente") from None
