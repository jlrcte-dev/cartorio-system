"""Diagnosis rules — metadata-only analysis of file_inventory.json entries.

SAFETY CONTRACT
---------------
- No rule ever calls open() on any path listed in the inventory.
- No rule accesses the file system beyond what was already collected in the JSON.
- Analysis is based exclusively on: name, path, extension, size, timestamps.
- Rules never assert definitive wrongdoing — only indicate candidates for review.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from app.modules.audit.diagnosis.models import DiagnosisCandidate
from app.modules.audit.findings.enums import (
    AuditCategory,
    AuditImpact,
    AuditPriority,
    AuditProbability,
    AuditSeverity,
)

FileDict = dict[str, Any]

_MB = 1024 * 1024
_MAX_EXAMPLES = 10
_MAX_PER_RULE = 30


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _path_lower(f: FileDict) -> str:
    return (f.get("path_relative") or "").lower().replace("\\", "/")


def _name_lower(f: FileDict) -> str:
    return (f.get("name") or "").lower()


def _bytes_human(n: int | float) -> str:
    val = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < 1024.0 or unit == "TB":
            return f"{int(val)} B" if unit == "B" else f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} B"


def _iso_str(value: object) -> str:
    return str(value) if value is not None else ""


def _parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _cutoff_dt(years: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=years * 365)


def _examples_note(files: list[FileDict], label: str) -> str:
    shown = files[:_MAX_EXAMPLES]
    lines = [
        f"  - {f.get('path_relative', '?')} ({_bytes_human(f.get('size_bytes', 0))})"
        for f in shown
    ]
    extra = len(files) - len(shown)
    if extra > 0:
        lines.append(f"  ... e mais {extra} arquivo(s).")
    return f"{label} ({len(files)} total):\n" + "\n".join(lines)



# ---------------------------------------------------------------------------
# DIAG-001 — Possível credencial por nome
# ---------------------------------------------------------------------------

_CREDENTIAL_KEYWORDS = (
    "login",
    "senha",
    "password",
    "credencial",
    "credenciais",
    "acesso",
    "dados_conta",
    "dados conta",
    "onvio",
    "engegraph",
    "sefaz",
    "ecac",
    "e-cac",
    "onmicrosoft",
    "token",
    "certificado digital",
    "certificado_digital",
)


def rule_credential_by_name(
    files: list[FileDict], scanner_run_id: str
) -> list[DiagnosisCandidate]:
    """DIAG-001: files whose name or path suggests stored credentials."""
    candidates: list[DiagnosisCandidate] = []
    for f in files:
        p = _path_lower(f)
        n = _name_lower(f)
        matched_kw = next(
            (kw for kw in _CREDENTIAL_KEYWORDS if kw in p or kw in n), None
        )
        if matched_kw is None:
            continue
        candidates.append(
            DiagnosisCandidate(
                title="Possível arquivo de credenciais identificado por nome",
                description=(
                    f"Arquivo contendo '{matched_kw}' no nome/caminho. "
                    "Pode indicar credenciais armazenadas. "
                    "Conteúdo não foi lido — requer validação manual."
                ),
                category=AuditCategory.ACCESS_CONTROL,
                severity=AuditSeverity.HIGH,
                probability=AuditProbability.MEDIUM,
                impact=AuditImpact.HIGH,
                priority=AuditPriority.SEVEN_DAYS,
                evidence_summary=(
                    "Possível arquivo de credenciais por nome; "
                    f"termo '{matched_kw}' em {f.get('path_relative', '?')}"
                ),
                evidence_reference=f.get("path_relative", ""),
                scanner_run_id=scanner_run_id,
                related_file_path=f.get("path_relative", ""),
                related_parent_path=f.get("parent_path", ""),
                related_extension=f.get("extension", ""),
                related_size_bytes=f.get("size_bytes"),
                related_modified_at=_iso_str(f.get("modified_at")),
                recommended_action=(
                    "Verificar manualmente se o arquivo contém credenciais. "
                    "Se confirmado: mover para local seguro ou excluir. "
                    "Nunca armazenar senhas em arquivos de texto."
                ),
                rule_id="DIAG-001",
                rule_name="credential_by_name",
                confidence=0.40,
                notes=f"Termo: '{matched_kw}'. Baseado em nome/caminho.",
            )
        )
        if len(candidates) >= _MAX_PER_RULE:
            break
    return candidates


# ---------------------------------------------------------------------------
# DIAG-002 — Executável / script por extensão
# ---------------------------------------------------------------------------

_EXECUTABLE_EXTENSIONS = frozenset({".exe", ".bat", ".cmd", ".ps1", ".vbs", ".scr", ".msi"})


def rule_executable_by_extension(
    files: list[FileDict], scanner_run_id: str
) -> list[DiagnosisCandidate]:
    """DIAG-002: executable or script files in the document tree."""
    matched = [f for f in files if (f.get("extension") or "").lower() in _EXECUTABLE_EXTENSIONS]
    candidates: list[DiagnosisCandidate] = []
    for f in matched[:_MAX_PER_RULE]:
        ext = (f.get("extension") or "").lower()
        candidates.append(
            DiagnosisCandidate(
                title=f"Arquivo executável ou script identificado: {f.get('name', '?')}",
                description=(
                    f"Arquivo com extensão '{ext}' encontrado na estrutura de documentos. "
                    "A presença de executáveis ou scripts em acervos documentais é incomum. "
                    "Recomenda-se verificar a origem e necessidade. "
                    "Análise baseada somente na extensão — o conteúdo não foi lido."
                ),
                category=AuditCategory.ENDPOINT_SECURITY,
                severity=AuditSeverity.HIGH,
                probability=AuditProbability.MEDIUM_HIGH,
                impact=AuditImpact.HIGH,
                priority=AuditPriority.THIRTY_DAYS,
                evidence_summary=(
                    f"Arquivo com extensão executável '{ext}' localizado em: "
                    f"{f.get('path_relative', '?')}"
                ),
                evidence_reference=f.get("path_relative", ""),
                scanner_run_id=scanner_run_id,
                related_file_path=f.get("path_relative", ""),
                related_parent_path=f.get("parent_path", ""),
                related_extension=ext,
                related_size_bytes=f.get("size_bytes"),
                related_modified_at=_iso_str(f.get("modified_at")),
                recommended_action=(
                    "Verificar a origem e finalidade do arquivo. "
                    "Se não houver justificativa documentada, "
                    "mover ou excluir após aprovação do responsável."
                ),
                rule_id="DIAG-002",
                rule_name="executable_by_extension",
                confidence=0.90,
                notes=(
                    f"Extensão identificada: '{ext}'. "
                    "A regra não afirma código malicioso — apenas a presença de executável/script."
                ),
            )
        )
    return candidates


# ---------------------------------------------------------------------------
# DIAG-003 — Documentos em pasta temporária
# ---------------------------------------------------------------------------

_TEMP_KEYWORDS = frozenset(
    {"temp", "temporário", "temporarios", "temporários", "temporario"}
)


def _is_temp_path(path_lower: str) -> bool:
    parts = path_lower.replace("\\", "/").split("/")
    return any(any(kw in part for kw in _TEMP_KEYWORDS) for part in parts[:-1])


def _find_temp_root(path_relative: str) -> str:
    parts_actual = path_relative.replace("\\", "/").split("/")
    parts_lower = path_relative.lower().replace("\\", "/").split("/")
    for i, part_l in enumerate(parts_lower[:-1]):
        if any(kw in part_l for kw in _TEMP_KEYWORDS):
            return "/".join(parts_actual[: i + 1])
    return parts_actual[0] if parts_actual else ""


def rule_temp_folder(
    files: list[FileDict], scanner_run_id: str
) -> list[DiagnosisCandidate]:
    """DIAG-003: real documents stored inside Temp/temporary folders."""
    groups: dict[str, list[FileDict]] = defaultdict(list)
    for f in files:
        if _is_temp_path(_path_lower(f)):
            groups[_find_temp_root(f.get("path_relative", ""))].append(f)

    candidates: list[DiagnosisCandidate] = []
    for folder_path, folder_files in list(groups.items())[:_MAX_PER_RULE]:
        total = len(folder_files)
        total_size = sum(ff.get("size_bytes", 0) for ff in folder_files)
        candidates.append(
            DiagnosisCandidate(
                title=f"Documentos em pasta temporária: {folder_path} ({total} arquivo(s))",
                description=(
                    f"{total} arquivo(s) encontrado(s) em pasta identificada como temporária "
                    f"('{folder_path}'). Documentos operacionais em pastas temporárias podem ser "
                    "perdidos em rotinas de limpeza e indicam processo de arquivamento inadequado."
                ),
                category=AuditCategory.DOCUMENT_MANAGEMENT,
                severity=AuditSeverity.MEDIUM,
                probability=AuditProbability.MEDIUM_HIGH,
                impact=AuditImpact.MEDIUM,
                priority=AuditPriority.THIRTY_DAYS,
                evidence_summary=(
                    f"{total} arquivo(s) em pasta temporária '{folder_path}'. "
                    f"Tamanho total: {_bytes_human(total_size)}."
                ),
                evidence_reference=folder_path,
                scanner_run_id=scanner_run_id,
                related_file_path=folder_files[0].get("path_relative", "") if folder_files else "",
                related_parent_path=folder_path,
                recommended_action=(
                    "Revisar os arquivos da pasta temporária. "
                    "Documentos operacionais devem ser movidos para pastas permanentes. "
                    "Arquivos desnecessários devem ser descartados conforme política de retenção."
                ),
                rule_id="DIAG-003",
                rule_name="temp_folder",
                confidence=0.80,
                notes=_examples_note(folder_files, "Arquivos encontrados na pasta temporária"),
            )
        )
    return candidates


# ---------------------------------------------------------------------------
# DIAG-004 — Arquivos grandes
# ---------------------------------------------------------------------------

_VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".avi", ".mkv"})


def rule_large_files(
    files: list[FileDict],
    scanner_run_id: str,
    large_file_mb: int = 50,
    large_pdf_mb: int = 10,
) -> list[DiagnosisCandidate]:
    """DIAG-004: files exceeding configured size thresholds."""
    candidates: list[DiagnosisCandidate] = []

    # 4a — PDFs grandes
    large_pdf = sorted(
        [
            f
            for f in files
            if (f.get("extension") or "").lower() == ".pdf"
            and f.get("size_bytes", 0) > large_pdf_mb * _MB
        ],
        key=lambda x: x.get("size_bytes", 0),
        reverse=True,
    )
    if large_pdf:
        total_size = sum(f.get("size_bytes", 0) for f in large_pdf)
        candidates.append(
            DiagnosisCandidate(
                title=f"{len(large_pdf)} PDF(s) com tamanho acima de {large_pdf_mb} MB",
                description=(
                    f"{len(large_pdf)} arquivo(s) PDF com tamanho superior a {large_pdf_mb} MB. "
                    "PDFs grandes podem indicar digitalização em alta resolução sem compressão, "
                    "documentos compostos ou artefatos incorretos."
                ),
                category=AuditCategory.DOCUMENT_MANAGEMENT,
                severity=AuditSeverity.MEDIUM,
                probability=AuditProbability.HIGH,
                impact=AuditImpact.LOW,
                priority=AuditPriority.NINETY_DAYS,
                evidence_summary=(
                    f"{len(large_pdf)} PDF(s) acima de {large_pdf_mb} MB. "
                    f"Tamanho total: {_bytes_human(total_size)}."
                ),
                scanner_run_id=scanner_run_id,
                related_file_path=large_pdf[0].get("path_relative", ""),
                related_extension=".pdf",
                related_size_bytes=large_pdf[0].get("size_bytes"),
                recommended_action=(
                    f"Revisar PDFs acima de {large_pdf_mb} MB. "
                    "Avaliar compressão ou reorganização. "
                    "Verificar se há duplicatas ou versões desnecessárias."
                ),
                rule_id="DIAG-004a",
                rule_name="large_pdf",
                confidence=0.90,
                notes=_examples_note(large_pdf, f"PDFs acima de {large_pdf_mb} MB"),
            )
        )

    # 4b — Vídeos (qualquer tamanho)
    videos = sorted(
        [f for f in files if (f.get("extension") or "").lower() in _VIDEO_EXTENSIONS],
        key=lambda x: x.get("size_bytes", 0),
        reverse=True,
    )
    if videos:
        total_size = sum(f.get("size_bytes", 0) for f in videos)
        candidates.append(
            DiagnosisCandidate(
                title=f"{len(videos)} arquivo(s) de vídeo encontrado(s) no acervo",
                description=(
                    f"{len(videos)} arquivo(s) de vídeo encontrado(s). "
                    "Vídeos consomem espaço significativo e raramente fazem parte "
                    "de acervos documentais de cartório. Recomenda-se revisar a necessidade."
                ),
                category=AuditCategory.DOCUMENT_MANAGEMENT,
                severity=AuditSeverity.LOW,
                probability=AuditProbability.HIGH,
                impact=AuditImpact.LOW,
                priority=AuditPriority.BACKLOG,
                evidence_summary=(
                    f"{len(videos)} arquivo(s) de vídeo. "
                    f"Tamanho total: {_bytes_human(total_size)}."
                ),
                scanner_run_id=scanner_run_id,
                related_size_bytes=total_size,
                recommended_action=(
                    "Revisar a necessidade dos vídeos no acervo. "
                    "Se forem treinamentos ou registros operacionais, "
                    "mover para servidor de mídia dedicado."
                ),
                rule_id="DIAG-004b",
                rule_name="large_video",
                confidence=0.95,
                notes=_examples_note(videos, "Arquivos de vídeo"),
            )
        )

    # 4c — Outros arquivos grandes (não-PDF, não-vídeo)
    other_large = sorted(
        [
            f
            for f in files
            if f.get("size_bytes", 0) > large_file_mb * _MB
            and (f.get("extension") or "").lower() not in ({".pdf"} | _VIDEO_EXTENSIONS)
        ],
        key=lambda x: x.get("size_bytes", 0),
        reverse=True,
    )
    if other_large:
        total_size = sum(f.get("size_bytes", 0) for f in other_large)
        candidates.append(
            DiagnosisCandidate(
                title=f"{len(other_large)} arquivo(s) acima de {large_file_mb} MB (não-PDF/vídeo)",
                description=(
                    f"{len(other_large)} arquivo(s) (excluindo PDFs e vídeos) com tamanho superior "
                    f"a {large_file_mb} MB. Podem indicar backups, dumps ou arquivos compostos "
                    "armazenados incorretamente no acervo."
                ),
                category=AuditCategory.DOCUMENT_MANAGEMENT,
                severity=AuditSeverity.LOW,
                probability=AuditProbability.HIGH,
                impact=AuditImpact.LOW,
                priority=AuditPriority.BACKLOG,
                evidence_summary=(
                    f"{len(other_large)} arquivo(s) acima de {large_file_mb} MB. "
                    f"Tamanho total: {_bytes_human(total_size)}."
                ),
                scanner_run_id=scanner_run_id,
                related_size_bytes=total_size,
                recommended_action=(
                    f"Revisar arquivos acima de {large_file_mb} MB. "
                    "Verificar se são backups, dumps ou arquivos desnecessários."
                ),
                rule_id="DIAG-004c",
                rule_name="large_other",
                confidence=0.90,
                notes=_examples_note(other_large, f"Arquivos acima de {large_file_mb} MB"),
            )
        )

    return candidates


# ---------------------------------------------------------------------------
# DIAG-005 — Nomes genéricos / pouco padronizados
# ---------------------------------------------------------------------------

_GENERIC_CONTAINS = (
    "novo documento",
    "new document",
    "sem título",
    "sem titulo",
    "untitled",
    "valida em todo o territorio nacional",
    "comprovante.pdf",
    "scan.pdf",
    "documento.pdf",
    "documento.docx",
    "documento.odt",
    "document.pdf",
    "document.docx",
)

_GENERIC_STEM_EXACT = frozenset({"imagem", "arquivo", "doc", "file"})


def _is_generic_name(name: str) -> bool:
    n = name.lower()
    for pattern in _GENERIC_CONTAINS:
        if n == pattern or n.startswith(pattern):
            return True
    stem = n.rsplit(".", 1)[0] if "." in n else n
    if stem in _GENERIC_STEM_EXACT:
        return True
    return bool(name.startswith("-"))


def rule_generic_name(
    files: list[FileDict], scanner_run_id: str
) -> list[DiagnosisCandidate]:
    """DIAG-005: files with non-descriptive or poorly standardised names."""
    matched = [f for f in files if _is_generic_name(f.get("name", ""))]
    if not matched:
        return []
    total = len(matched)
    return [
        DiagnosisCandidate(
            title=f"{total} arquivo(s) com nome genérico ou pouco padronizado",
            description=(
                f"{total} arquivo(s) com nomes genéricos (ex: 'documento.pdf', 'scan.pdf', "
                "'sem título', 'arquivo') identificados. Nomes não descritivos dificultam "
                "localização, rastreabilidade e gestão documental."
            ),
            category=AuditCategory.DOCUMENT_MANAGEMENT,
            severity=AuditSeverity.LOW,
            probability=AuditProbability.HIGH,
            impact=AuditImpact.LOW,
            priority=AuditPriority.BACKLOG,
            evidence_summary=(
                f"{total} arquivo(s) com nomes genéricos. "
                "Recomenda-se revisão da política de nomenclatura."
            ),
            scanner_run_id=scanner_run_id,
            related_file_path=matched[0].get("path_relative", "") if matched else "",
            recommended_action=(
                "Revisar a política de nomenclatura de arquivos. "
                "Renomear arquivos com nomes descritivos que identifiquem "
                "conteúdo, data e contexto documental."
            ),
            rule_id="DIAG-005",
            rule_name="generic_name",
            confidence=0.70,
            notes=_examples_note(matched, "Arquivos com nomes genéricos"),
        )
    ]


# ---------------------------------------------------------------------------
# DIAG-006 — Acervo financeiro histórico (candidato agregado por pasta)
# ---------------------------------------------------------------------------

_FINANCIAL_KEYWORDS = (
    "gerenciamento_financeiro",
    "gerenciamento financeiro",
    "financeiro",
    "emolumentos",
    "taxas",
    "fundos",
    "iss",
    "sefaz",
    "cnj",
    "boletos",
    "recibos",
    "pagamentos",
)


def _find_financial_root(path_relative: str) -> str | None:
    parts_actual = path_relative.replace("\\", "/").split("/")
    parts_lower = path_relative.lower().replace("\\", "/").split("/")
    for i, part_l in enumerate(parts_lower):
        if any(kw in part_l for kw in _FINANCIAL_KEYWORDS):
            return "/".join(parts_actual[: i + 1])
    return None


def rule_financial_archive(
    files: list[FileDict], scanner_run_id: str
) -> list[DiagnosisCandidate]:
    """DIAG-006: financial documents — one aggregated candidate per financial root."""
    groups: dict[str, list[FileDict]] = defaultdict(list)
    for f in files:
        root = _find_financial_root(f.get("path_relative", ""))
        if root:
            groups[root].append(f)

    candidates: list[DiagnosisCandidate] = []
    for financial_root, group_files in list(groups.items())[:10]:
        total = len(group_files)
        total_size = sum(ff.get("size_bytes", 0) for ff in group_files)
        valid_dates = [d for d in (_parse_dt(ff.get("modified_at")) for ff in group_files) if d]
        date_range = ""
        if valid_dates:
            oldest, newest = min(valid_dates).year, max(valid_dates).year
            date_range = f" (anos: {oldest}–{newest})" if oldest != newest else f" (ano: {oldest})"

        candidates.append(
            DiagnosisCandidate(
                title=f"Acervo financeiro: {financial_root} — {total} arquivo(s){date_range}",
                description=(
                    f"Pasta com dados financeiros identificada: '{financial_root}'. "
                    f"Contém {total} arquivo(s) totalizando {_bytes_human(total_size)}. "
                    "Documentos financeiros requerem controle de acesso, política de retenção "
                    "e proteção conforme LGPD e normas fiscais."
                ),
                category=AuditCategory.FINANCE,
                severity=AuditSeverity.MEDIUM,
                probability=AuditProbability.HIGH,
                impact=AuditImpact.MEDIUM,
                priority=AuditPriority.THIRTY_DAYS,
                evidence_summary=(
                    f"Acervo financeiro em '{financial_root}': {total} arquivo(s), "
                    f"{_bytes_human(total_size)}{date_range}."
                ),
                evidence_reference=financial_root,
                scanner_run_id=scanner_run_id,
                related_parent_path=financial_root,
                related_size_bytes=total_size,
                recommended_action=(
                    "Revisar controles de acesso à pasta financeira. "
                    "Verificar política de retenção e descarte. "
                    "Confirmar cobertura pelo plano de backup. "
                    "Avaliar conformidade com LGPD e normas do CNJ."
                ),
                rule_id="DIAG-006",
                rule_name="financial_archive",
                confidence=0.85,
                notes=_examples_note(group_files, f"Arquivos em '{financial_root}'"),
            )
        )
    return candidates


# ---------------------------------------------------------------------------
# DIAG-007 — Documentos antigos em POP / LGPD / políticas
# ---------------------------------------------------------------------------

_POLICY_KEYWORDS = (
    "politica",
    "política",
    "politicas",
    "políticas",
    "procedimento",
    "procedimentos",
    "pop",
    "manual",
    "sgcn",
    "lgpd",
    "segurança",
    "seguranca",
    "compliance",
)


def _find_policy_root(path_relative: str) -> str | None:
    parts_actual = path_relative.replace("\\", "/").split("/")
    parts_lower = path_relative.lower().replace("\\", "/").split("/")
    for i, part_l in enumerate(parts_lower):
        if any(kw in part_l for kw in _POLICY_KEYWORDS):
            return "/".join(parts_actual[: i + 1])
    return None


def rule_old_policy_docs(
    files: list[FileDict],
    scanner_run_id: str,
    old_file_years: int = 5,
) -> list[DiagnosisCandidate]:
    """DIAG-007: policy/compliance documents not modified for old_file_years+."""
    cutoff = _cutoff_dt(old_file_years)
    groups: dict[str, list[FileDict]] = defaultdict(list)
    for f in files:
        policy_root = _find_policy_root(f.get("path_relative", ""))
        if policy_root is None:
            continue
        dt = _parse_dt(f.get("modified_at"))
        if dt is not None and dt < cutoff:
            groups[policy_root].append(f)

    candidates: list[DiagnosisCandidate] = []
    for policy_root, group_files in list(groups.items())[:10]:
        total = len(group_files)
        valid_dts = [d for d in (_parse_dt(ff.get("modified_at")) for ff in group_files) if d]
        oldest_str = min(valid_dts).strftime("%Y-%m-%d") if valid_dts else "desconhecida"
        candidates.append(
            DiagnosisCandidate(
                title=(
                    f"{total} documento(s) de política/POP sem atualização "
                    f"há >{old_file_years} anos em: {policy_root}"
                ),
                description=(
                    f"{total} arquivo(s) em pasta de política/procedimentos ('{policy_root}') "
                    f"não foram modificados há mais de {old_file_years} anos "
                    f"(data mais antiga: {oldest_str}). "
                    "Documentos normativos desatualizados representam risco de conformidade."
                ),
                category=AuditCategory.POLICY_DOCUMENT,
                severity=AuditSeverity.MEDIUM,
                probability=AuditProbability.MEDIUM_HIGH,
                impact=AuditImpact.MEDIUM,
                priority=AuditPriority.NINETY_DAYS,
                evidence_summary=(
                    f"{total} documento(s) em '{policy_root}' com última modificação "
                    f"anterior a {cutoff.strftime('%Y-%m-%d')}. Mais antigo: {oldest_str}."
                ),
                evidence_reference=policy_root,
                scanner_run_id=scanner_run_id,
                related_parent_path=policy_root,
                recommended_action=(
                    f"Revisar documentos de política/procedimento em '{policy_root}'. "
                    "Atualizar desatualizados ou registrar validade contínua. "
                    "Documentos normativos devem ter revisão periódica documentada."
                ),
                rule_id="DIAG-007",
                rule_name="old_policy_docs",
                confidence=0.75,
                notes=_examples_note(
                    sorted(group_files, key=lambda x: _iso_str(x.get("modified_at"))),
                    f"Documentos mais antigos em '{policy_root}'",
                ),
            )
        )
    return candidates
