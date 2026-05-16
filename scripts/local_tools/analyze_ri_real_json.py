"""
Analisador sanitizado do Indicador Real JSON — Cartório System

Sprint: RI-REAL-JSON-1

PROTEÇÃO DE DADOS (LGPD):
- CONTRIBUINTE e dados pessoais NUNCA são impressos, salvos ou incluídos nos derivados.
- Varredura anti-PII é executada em todos os arquivos de saída.
- Os JSONs brutos devem ficar exclusivamente em _local_data/ri_inventory/raw/.

USO:
    # Inspeção sem salvar:
    python scripts/local_tools/analyze_ri_real_json.py \\
        --input _local_data/ri_inventory/raw/Indicador_Real.json \\
        --dry-run

    # Execução completa:
    python scripts/local_tools/analyze_ri_real_json.py \\
        --input _local_data/ri_inventory/raw/Indicador_Real.json \\
        --write-sanitized --write-db --write-reports
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Caminhos base
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
LOCAL_DATA = BASE_DIR / "_local_data"
SANITIZED_DIR = LOCAL_DATA / "ri_inventory" / "sanitized"
DB_DIR = LOCAL_DATA / "ri_inventory" / "db"
REPORTS_DIR = LOCAL_DATA / "ri_inventory" / "reports" / "real_json"
MANUAL_REVIEW_DIR = REPORTS_DIR / "manual_review"

# ---------------------------------------------------------------------------
# Campos sanitizados
# ---------------------------------------------------------------------------
FIELDNAMES = [
    "record_id",
    "cns",
    "numero_registro",
    "livro",
    "matricula_numero",
    "digito_verificador_onr",
    "registro_tipo",
    "tipo_de_imovel",
    "localizacao_codigo",
    "natureza_imovel",
    "natureza_imovel_fonte",
    "natureza_imovel_confidence",
    "uf_codigo",
    "cidade_codigo",
    "bairro_sanitizado",
    "cep_sanitizado",
    "tem_quadra",
    "tem_lote",
    "tem_loteamento",
    "tem_condominio",
    "tem_car",
    "car_codigo",
    "tem_nirf",
    "nirf_codigo",
    "nirf_status",
    "tem_ccir",
    "ccir_codigo",
    "tem_numero_incra",
    "numero_incra_codigo",
    "tem_sigef",
    "sigef_codigo",
    "tem_denominacao_rural",
    "denominacao_rural_sanitizada",
    "tem_acidente_geografico",
    "acidente_geografico_sanitizado",
    "possui_georreferenciamento",
    "georreferenciamento_criterio",
    "status_extracao",
    "status_revisao_ri",
    "observacoes_tecnicas_sem_pii",
    "fonte_arquivo",
    "hash_registro_sanitizado",
]

# ---------------------------------------------------------------------------
# Padrões anti-PII
# ---------------------------------------------------------------------------
_CPF_RE = re.compile(r"\b\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[\-\.\s]?\d{2}\b")
_CNPJ_RE = re.compile(r"\b\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\.\s\/]?\d{4}[\-\.\s]?\d{2}\b")
_DOC_LABEL_RE = re.compile(
    r"\b(CPF|CNPJ|CI|SSP|RG|CIC|CED|contribuinte|proprietario|proprietário|"
    r"adquirente|transmitente|nome_proprietario)\b",
    re.I,
)

# Campos técnicos com números longos — excluídos da varredura CPF/CNPJ
_CAMPOS_CODIGOS_TECNICOS = frozenset({
    "hash_registro_sanitizado",
    "record_id",
    "car_codigo",
    "ccir_codigo",
    "numero_incra_codigo",
    "sigef_codigo",
    "nirf_codigo",
    "cep_sanitizado",
})

# Denominação rural: padrões suspeitos de nome de pessoa
# Aceita preposições curtas (DA, DE, DO, etc.) como separadores com {2,}
_NOME_PESSOA_RE = re.compile(
    r"\b(cpf|cnpj|ci\b|rg\b|cédula|cic)\b"
    r"|([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]{2,}\s+){2,}[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]{3,}",
    re.I,
)
# Palavras-chave indicativas de imóvel (não de pessoa)
_IMOVEL_KW_RE = re.compile(
    r"\b(fazenda|s[ií]tio|ch[áa]cara|gleba|retiro|rancho|[áa]rea|granja|brejo|"
    r"v[áa]rzea|haras|ribeir[ãa]o|c[oó]rrego|parque|quinta|campo|cerrado|mata|"
    r"estrada|lote[0-9a-z]|loteamento|propri?\.?|h[íi]pica|fazendola|fazendo)\b",
    re.I,
)

# ---------------------------------------------------------------------------
# Padrões de bairro/CEP (técnicos, sem PII)
# ---------------------------------------------------------------------------
_CEP_RE = re.compile(r"(\d{5}-?\d{3})")

# ---------------------------------------------------------------------------
# Regex de NUMERO_REGISTRO
# ---------------------------------------------------------------------------
_NR_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)-(\d+)$")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ParsedNumeroRegistro:
    cns: str = ""
    livro: str = ""
    matricula_raw: str = ""
    matricula_numero: int = 0
    digito_verificador_onr: str = ""
    valido: bool = True
    alerta: str = ""


@dataclass
class RuralFlags:
    tem_car: bool = False
    car_codigo: str = ""
    tem_nirf: bool = False
    nirf_codigo: str = ""
    nirf_status: str = "ausente"
    tem_ccir: bool = False
    ccir_codigo: str = ""
    tem_numero_incra: bool = False
    numero_incra_codigo: str = ""
    tem_sigef: bool = False
    sigef_codigo: str = ""
    tem_denominacao_rural: bool = False
    denominacao_rural_sanitizada: str = ""
    tem_acidente_geografico: bool = False
    acidente_geografico_sanitizado: str = ""


@dataclass
class InventoryRecord:
    record_id: str = ""
    cns: str = ""
    numero_registro: str = ""
    livro: str = ""
    matricula_numero: int = 0
    digito_verificador_onr: str = ""
    registro_tipo: int = 0
    tipo_de_imovel: int = 0
    localizacao_codigo: Any = None
    natureza_imovel: str = "indeterminado"
    natureza_imovel_fonte: str = ""
    natureza_imovel_confidence: str = ""
    uf_codigo: str = ""
    cidade_codigo: str = ""
    bairro_sanitizado: str = ""
    cep_sanitizado: str = ""
    tem_quadra: bool = False
    tem_lote: bool = False
    tem_loteamento: bool = False
    tem_condominio: bool = False
    rural: RuralFlags = field(default_factory=RuralFlags)
    possui_georreferenciamento: bool = False
    georreferenciamento_criterio: str = ""
    status_extracao: list[str] = field(default_factory=list)
    status_revisao_ri: str = ""
    observacoes_tecnicas_sem_pii: list[str] = field(default_factory=list)
    fonte_arquivo: str = ""
    hash_registro_sanitizado: str = ""


# ---------------------------------------------------------------------------
# Parsing de NUMERO_REGISTRO
# ---------------------------------------------------------------------------
def parse_numero_registro(numero_registro: str) -> ParsedNumeroRegistro:
    """Parseia CNS.LIVRO.MATRICULA-DV do campo NUMERO_REGISTRO."""
    p = ParsedNumeroRegistro()
    nr = str(numero_registro).strip()
    m = _NR_RE.match(nr)
    if not m:
        p.valido = False
        p.alerta = "numero_registro_invalido"
        return p
    p.cns = m.group(1)
    p.livro = m.group(2)
    p.matricula_raw = m.group(3)
    p.matricula_numero = int(m.group(3))
    p.digito_verificador_onr = m.group(4)
    return p


# ---------------------------------------------------------------------------
# Classificação de natureza por LOCALIZACAO
# ---------------------------------------------------------------------------
def classify_natureza(localizacao: Any) -> tuple[str, str, str]:
    """Retorna (natureza_imovel, natureza_imovel_fonte, natureza_imovel_confidence)."""
    if localizacao == 0:
        return "urbano", "localizacao_json", "confirmado"
    if localizacao == 1:
        return "rural", "localizacao_json", "confirmado"
    return "indeterminado", "localizacao_json", "invalido"


# ---------------------------------------------------------------------------
# Normalização de campos rurais
# ---------------------------------------------------------------------------
def _is_blank(v: Any) -> bool:
    return v is None or str(v).strip() == ""


def _is_all_zeros(v: str) -> bool:
    return bool(v) and re.match(r"^0+$", v.strip())


def _normalize_rural(raw: dict) -> RuralFlags:
    r = RuralFlags()

    # CAR
    car = str(raw.get("CAR", "") or "").strip()
    if car:
        r.tem_car = True
        r.car_codigo = car

    # NIRF
    nirf = str(raw.get("NIRF", "") or "").strip()
    if not nirf:
        r.nirf_status = "ausente"
    elif _is_all_zeros(nirf):
        r.nirf_status = "placeholder_zeros"
        r.nirf_codigo = nirf
    elif re.search(r"[1-9]", nirf):
        r.tem_nirf = True
        r.nirf_codigo = nirf
        r.nirf_status = "valido"
    else:
        r.nirf_status = "ambiguo"
        r.nirf_codigo = nirf

    # CCIR
    ccir = str(raw.get("CCIR", "") or "").strip()
    if ccir:
        r.tem_ccir = True
        r.ccir_codigo = ccir

    # NUMERO_INCRA
    incra = str(raw.get("NUMERO_INCRA", "") or "").strip()
    if incra:
        r.tem_numero_incra = True
        r.numero_incra_codigo = incra

    # SIGEF
    sigef = str(raw.get("SIGEF", "") or "").strip()
    if sigef:
        r.tem_sigef = True
        r.sigef_codigo = sigef

    # DENOMINACAORURAL
    denom = str(raw.get("DENOMINACAORURAL", "") or "").strip()
    if denom:
        if _is_pii_string(denom) or _nome_pessoa_suspeito(denom):
            r.tem_denominacao_rural = True
            r.denominacao_rural_sanitizada = ""
        else:
            r.tem_denominacao_rural = True
            r.denominacao_rural_sanitizada = denom[:200]

    # ACIDENTEGEOGRAFICO
    acidente = str(raw.get("ACIDENTEGEOGRAFICO", "") or "").strip()
    if acidente:
        if _is_pii_string(acidente):
            r.tem_acidente_geografico = True
            r.acidente_geografico_sanitizado = ""
        else:
            r.tem_acidente_geografico = True
            r.acidente_geografico_sanitizado = acidente[:200]

    return r


def _nome_pessoa_suspeito(v: str) -> bool:
    if _NOME_PESSOA_RE.search(v):
        return not bool(_IMOVEL_KW_RE.search(v))
    return False


# ---------------------------------------------------------------------------
# Georreferenciamento
# ---------------------------------------------------------------------------
def calc_georreferenciamento(rural: RuralFlags) -> tuple[bool, str]:
    criterios = []
    if rural.tem_numero_incra:
        criterios.append("numero_incra")
    if rural.tem_sigef:
        criterios.append("sigef")
    if criterios:
        return True, "|".join(criterios)
    return False, ""


# ---------------------------------------------------------------------------
# Heurísticas de inconsistência urbano/rural
# ---------------------------------------------------------------------------
_RURAL_KW_RE = re.compile(
    r"\b(fazenda|s[ií]tio|ch[áa]cara|gleba|retiro|rancho|granja|brejo|v[áa]rzea|"
    r"haras|ribeir[ãa]o|c[oó]rrego|pastagem|cerrado|lavoura|roça|campo|rural)\b",
    re.I,
)
_URBAN_KW_RE = re.compile(
    r"\b(rua|avenida|alameda|travessa|quadra|lote|bairro|conjunto|setor|"
    r"apartamento|condomin[ií]o|residencial|comercial|industrial)\b",
    re.I,
)


def _detect_inconsistency(rec: InventoryRecord, raw: dict) -> list[str]:
    alertas = []
    natureza = rec.natureza_imovel
    bairro = str(raw.get("BAIRRO", "") or "").lower()
    nome_log = str(raw.get("NOME_LOGRADOURO", "") or "").lower()
    denom = rec.rural.denominacao_rural_sanitizada.lower()
    texto = " ".join([bairro, nome_log, denom])

    if natureza == "rural":
        if _URBAN_KW_RE.search(texto):
            alertas.append("rural_com_sinais_urbanos")
        if not rec.rural.tem_denominacao_rural:
            alertas.append("rural_sem_denominacao_rural")
    elif natureza == "urbano":
        if _RURAL_KW_RE.search(texto):
            alertas.append("urbano_com_sinais_rurais")
        rural_fields = [
            rec.rural.tem_car, rec.rural.tem_nirf, rec.rural.tem_ccir,
            rec.rural.tem_numero_incra, rec.rural.tem_sigef,
        ]
        if any(rural_fields):
            alertas.append("urbano_com_campos_rurais_preenchidos")
    return alertas


# ---------------------------------------------------------------------------
# Anti-PII: detectar no valor de uma string
# ---------------------------------------------------------------------------
def _is_pii_string(v: str) -> bool:
    if _DOC_LABEL_RE.search(v):
        return True
    if _CPF_RE.search(v):
        return True
    if _CNPJ_RE.search(v):
        return True
    return False


# ---------------------------------------------------------------------------
# Sanitização de bairro/CEP
# ---------------------------------------------------------------------------
def _sanitize_bairro(bairro: str) -> str:
    """Retorna bairro se não for PII; caso contrário retorna string vazia."""
    b = str(bairro or "").strip()
    if not b:
        return ""
    if _is_pii_string(b):
        return ""
    # Limita a 100 chars e remove excesso
    return b[:100]


def _sanitize_cep(cep: Any) -> str:
    v = str(cep or "").strip()
    digits = re.sub(r"\D", "", v)
    if len(digits) == 8:
        return digits[:5] + "-" + digits[5:]
    return ""


# ---------------------------------------------------------------------------
# Hash de registro sanitizado — rastreabilidade sem expor conteúdo bruto
# ---------------------------------------------------------------------------
def _hash_registro(numero_registro: str, matricula_numero: int) -> str:
    chave = f"{numero_registro}:{matricula_numero}"
    return "H-" + hashlib.sha256(chave.encode()).hexdigest()[:10]


# ---------------------------------------------------------------------------
# Processar um registro bruto
# ---------------------------------------------------------------------------
def process_record(raw: dict, cns_esperado: str, fonte: str) -> InventoryRecord:
    rec = InventoryRecord()
    rec.record_id = str(uuid.uuid4())
    rec.fonte_arquivo = fonte

    # NUMERO_REGISTRO
    nr_raw = str(raw.get("NUMERO_REGISTRO", "") or "").strip()
    rec.numero_registro = nr_raw
    parsed = parse_numero_registro(nr_raw)

    if not parsed.valido:
        rec.status_extracao.append("numero_registro_invalido")
    else:
        rec.cns = parsed.cns
        rec.livro = parsed.livro
        rec.matricula_numero = parsed.matricula_numero
        rec.digito_verificador_onr = parsed.digito_verificador_onr
        if parsed.cns != str(cns_esperado):
            rec.status_extracao.append("cns_divergente")
            rec.observacoes_tecnicas_sem_pii.append(
                f"CNS do registro ({parsed.cns}) != CNS do arquivo ({cns_esperado})"
            )

    rec.hash_registro_sanitizado = _hash_registro(nr_raw, rec.matricula_numero)

    # Campos técnicos do registro
    rec.registro_tipo = int(raw.get("REGISTRO_TIPO") or 0)
    rec.tipo_de_imovel = int(raw.get("TIPO_DE_IMOVEL") or 0)

    # LOCALIZACAO
    loc = raw.get("LOCALIZACAO")
    rec.localizacao_codigo = loc
    natureza, fonte_nat, confidence = classify_natureza(loc)
    rec.natureza_imovel = natureza
    rec.natureza_imovel_fonte = fonte_nat
    rec.natureza_imovel_confidence = confidence
    if natureza == "indeterminado":
        rec.status_extracao.append("localizacao_invalida")
        rec.status_revisao_ri = "needs_manual_review"

    # UF e Cidade (códigos técnicos, não PII)
    rec.uf_codigo = str(raw.get("UF", "") or "").strip()
    rec.cidade_codigo = str(raw.get("CIDADE", "") or "").strip()

    # Bairro e CEP (sanitizados)
    rec.bairro_sanitizado = _sanitize_bairro(raw.get("BAIRRO", ""))
    rec.cep_sanitizado = _sanitize_cep(raw.get("CEP", ""))

    # Quadra, Lote, Loteamento, Condomínio — flags booleanas
    rec.tem_quadra = bool(str(raw.get("QUADRA", "") or "").strip())
    rec.tem_lote = bool(str(raw.get("LOTE", "") or "").strip())
    rec.tem_loteamento = bool(str(raw.get("LOTEAMENTO", "") or "").strip())
    rec.tem_condominio = bool(str(raw.get("CONDOMINIO", "") or "").strip())

    # RURAL
    rural_raw = raw.get("RURAL", {}) or {}
    rec.rural = _normalize_rural(rural_raw)

    # Georreferenciamento
    rec.possui_georreferenciamento, rec.georreferenciamento_criterio = (
        calc_georreferenciamento(rec.rural)
    )

    # Inconsistências heurísticas
    alertas = _detect_inconsistency(rec, raw)
    rec.observacoes_tecnicas_sem_pii.extend(alertas)

    # Status revisão manual consolidado
    if not rec.status_revisao_ri and (
        "localizacao_invalida" in rec.status_extracao
        or "cns_divergente" in rec.status_extracao
        or "numero_registro_invalido" in rec.status_extracao
        or any(a in alertas for a in [
            "rural_com_sinais_urbanos", "urbano_com_sinais_rurais"
        ])
    ):
        rec.status_revisao_ri = "needs_manual_review"

    return rec


# ---------------------------------------------------------------------------
# Converter InventoryRecord para dict sanitizado
# ---------------------------------------------------------------------------
def record_to_dict(rec: InventoryRecord) -> dict:
    return {
        "record_id": rec.record_id,
        "cns": rec.cns,
        "numero_registro": rec.numero_registro,
        "livro": rec.livro,
        "matricula_numero": rec.matricula_numero,
        "digito_verificador_onr": rec.digito_verificador_onr,
        "registro_tipo": rec.registro_tipo,
        "tipo_de_imovel": rec.tipo_de_imovel,
        "localizacao_codigo": rec.localizacao_codigo,
        "natureza_imovel": rec.natureza_imovel,
        "natureza_imovel_fonte": rec.natureza_imovel_fonte,
        "natureza_imovel_confidence": rec.natureza_imovel_confidence,
        "uf_codigo": rec.uf_codigo,
        "cidade_codigo": rec.cidade_codigo,
        "bairro_sanitizado": rec.bairro_sanitizado,
        "cep_sanitizado": rec.cep_sanitizado,
        "tem_quadra": rec.tem_quadra,
        "tem_lote": rec.tem_lote,
        "tem_loteamento": rec.tem_loteamento,
        "tem_condominio": rec.tem_condominio,
        "tem_car": rec.rural.tem_car,
        "car_codigo": rec.rural.car_codigo,
        "tem_nirf": rec.rural.tem_nirf,
        "nirf_codigo": rec.rural.nirf_codigo,
        "nirf_status": rec.rural.nirf_status,
        "tem_ccir": rec.rural.tem_ccir,
        "ccir_codigo": rec.rural.ccir_codigo,
        "tem_numero_incra": rec.rural.tem_numero_incra,
        "numero_incra_codigo": rec.rural.numero_incra_codigo,
        "tem_sigef": rec.rural.tem_sigef,
        "sigef_codigo": rec.rural.sigef_codigo,
        "tem_denominacao_rural": rec.rural.tem_denominacao_rural,
        "denominacao_rural_sanitizada": rec.rural.denominacao_rural_sanitizada,
        "tem_acidente_geografico": rec.rural.tem_acidente_geografico,
        "acidente_geografico_sanitizado": rec.rural.acidente_geografico_sanitizado,
        "possui_georreferenciamento": rec.possui_georreferenciamento,
        "georreferenciamento_criterio": rec.georreferenciamento_criterio,
        "status_extracao": "|".join(rec.status_extracao) if rec.status_extracao else "ok",
        "status_revisao_ri": rec.status_revisao_ri,
        "observacoes_tecnicas_sem_pii": "; ".join(rec.observacoes_tecnicas_sem_pii),
        "fonte_arquivo": rec.fonte_arquivo,
        "hash_registro_sanitizado": rec.hash_registro_sanitizado,
    }


# ---------------------------------------------------------------------------
# Varredura anti-PII em arquivo de texto (CSV/JSON/MD)
# ---------------------------------------------------------------------------
def scan_file_anti_pii(path: Path) -> list[tuple[str, int, str]]:
    """
    Varre arquivo em busca de PII.
    Para CSV, avalia coluna a coluna excluindo campos técnicos conhecidos.
    Não imprime o conteúdo — apenas metadados (arquivo, tipo, linha).
    """
    issues: list[tuple[str, int, str]] = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return issues

    lines = content.splitlines()
    is_csv = path.suffix.lower() == ".csv"

    # Para CSV: varredura ciente de colunas
    if is_csv:
        try:
            import io
            reader = csv.DictReader(io.StringIO(content))
            for row_num, row in enumerate(reader, start=2):
                for col, val in row.items():
                    if col in _CAMPOS_CODIGOS_TECNICOS:
                        continue
                    v = str(val)
                    if re.search(r"\bCONTRIBUINTE\b", col, re.I):
                        issues.append(("campo_contribuinte", row_num, f"Coluna {col!r} detectada"))
                    if _DOC_LABEL_RE.search(v):
                        issues.append(("rotulo_pii", row_num, f"Rótulo PII na coluna {col!r}"))
                    if _CPF_RE.search(v):
                        issues.append(("cpf_pattern", row_num, f"Padrão CPF na coluna {col!r}"))
                    if _CNPJ_RE.search(v):
                        issues.append(("cnpj_pattern", row_num, f"Padrão CNPJ na coluna {col!r}"))
            return issues
        except Exception:
            pass  # fallback para varredura de linha completa

    # Para JSON/Markdown: varredura de linha completa com heurística técnica
    for i, line in enumerate(lines, start=1):
        if i == 1 and any(fn in line for fn in ["record_id", "cns", "numero_registro"]):
            continue
        if re.search(r"\bCONTRIBUINTE\b", line, re.I):
            issues.append(("campo_contribuinte", i, "Rótulo CONTRIBUINTE detectado"))
        if _DOC_LABEL_RE.search(line):
            issues.append(("rotulo_pii", i, "Rótulo de documento pessoal detectado"))
        # Para JSON, checar se a linha é de um campo técnico seguro antes de verificar números
        line_lower = line.lower()
        in_safe_field = any(f in line_lower for f in _CAMPOS_CODIGOS_TECNICOS)
        if not in_safe_field:
            if _CPF_RE.search(line):
                issues.append(("cpf_pattern", i, "Padrão CPF detectado"))
            if _CNPJ_RE.search(line):
                issues.append(("cnpj_pattern", i, "Padrão CNPJ detectado"))
    return issues


def scan_sqlite_anti_pii(db_path: Path, table: str) -> list[tuple[str, str, str]]:
    """Varre colunas proibidas no SQLite. Retorna (coluna, tipo, descricao)."""
    issues: list[tuple[str, str, str]] = []
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Verificar se tabela existe
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cur.fetchone():
            conn.close()
            return issues
        # Verificar se coluna CONTRIBUINTE existe
        cur.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cur.fetchall()]
        if "CONTRIBUINTE" in cols or "contribuinte" in cols:
            issues.append(("coluna_contribuinte", table, "Coluna CONTRIBUINTE encontrada no SQLite"))
        conn.close()
    except Exception as e:
        issues.append(("erro_scan", str(e), "Erro ao escanear SQLite"))
    return issues


# ---------------------------------------------------------------------------
# Calcular métricas
# ---------------------------------------------------------------------------
def compute_metrics(records: list[InventoryRecord]) -> dict:
    matriculas = [r.matricula_numero for r in records if r.matricula_numero > 0]
    matriculas_unicas = sorted(set(matriculas))
    min_mat = min(matriculas_unicas) if matriculas_unicas else 0
    max_mat = max(matriculas_unicas) if matriculas_unicas else 0
    faltantes = sorted(set(range(min_mat, max_mat + 1)) - set(matriculas_unicas))

    dup_counter = Counter(matriculas)
    duplicadas = {m: c for m, c in dup_counter.items() if c > 1}

    urbanos = [r for r in records if r.natureza_imovel == "urbano"]
    rurais = [r for r in records if r.natureza_imovel == "rural"]
    indeterminados = [r for r in records if r.natureza_imovel == "indeterminado"]

    rurais_com_car = [r for r in rurais if r.rural.tem_car]
    rurais_sem_car = [r for r in rurais if not r.rural.tem_car]
    rurais_com_nirf = [r for r in rurais if r.rural.tem_nirf]
    rurais_nirf_zeros = [r for r in rurais if r.rural.nirf_status == "placeholder_zeros"]
    rurais_sem_nirf = [r for r in rurais if r.rural.nirf_status == "ausente"]
    rurais_com_ccir = [r for r in rurais if r.rural.tem_ccir]
    rurais_sem_ccir = [r for r in rurais if not r.rural.tem_ccir]
    rurais_com_incra = [r for r in rurais if r.rural.tem_numero_incra]
    rurais_com_sigef = [r for r in rurais if r.rural.tem_sigef]
    rurais_com_georef = [r for r in rurais if r.possui_georreferenciamento]
    rurais_com_denom = [r for r in rurais if r.rural.tem_denominacao_rural]
    rurais_sem_denom = [r for r in rurais if not r.rural.tem_denominacao_rural]

    urbanos_com_rurais = [
        r for r in urbanos
        if r.rural.tem_car or r.rural.tem_nirf or r.rural.tem_ccir
        or r.rural.tem_numero_incra or r.rural.tem_sigef
    ]

    inconsistentes = [
        r for r in records
        if any(a in r.observacoes_tecnicas_sem_pii for a in [
            "rural_com_sinais_urbanos", "urbano_com_sinais_rurais",
            "urbano_com_campos_rurais_preenchidos",
        ])
    ]

    needs_review = [r for r in records if r.status_revisao_ri == "needs_manual_review"]

    nr_invalidos = [r for r in records if "numero_registro_invalido" in r.status_extracao]
    cns_divergentes = [r for r in records if "cns_divergente" in r.status_extracao]
    loc_invalidas = [r for r in records if "localizacao_invalida" in r.status_extracao]

    return {
        "total_registros": len(records),
        "matriculas_unicas": len(matriculas_unicas),
        "min_matricula": min_mat,
        "max_matricula": max_mat,
        "matriculas_faltantes": faltantes,
        "matriculas_duplicadas": duplicadas,
        "total_urbano": len(urbanos),
        "total_rural": len(rurais),
        "total_indeterminado": len(indeterminados),
        "rurais_com_car": len(rurais_com_car),
        "rurais_sem_car": len(rurais_sem_car),
        "rurais_com_nirf": len(rurais_com_nirf),
        "rurais_nirf_zeros": len(rurais_nirf_zeros),
        "rurais_sem_nirf": len(rurais_sem_nirf),
        "rurais_com_ccir": len(rurais_com_ccir),
        "rurais_sem_ccir": len(rurais_sem_ccir),
        "rurais_com_incra": len(rurais_com_incra),
        "rurais_com_sigef": len(rurais_com_sigef),
        "rurais_com_georef": len(rurais_com_georef),
        "rurais_com_denominacao": len(rurais_com_denom),
        "rurais_sem_denominacao": len(rurais_sem_denom),
        "urbanos_com_campos_rurais": len(urbanos_com_rurais),
        "inconsistentes": len(inconsistentes),
        "needs_review": len(needs_review),
        "nr_invalidos": len(nr_invalidos),
        "cns_divergentes": len(cns_divergentes),
        "loc_invalidas": len(loc_invalidas),
        # listas para relatório
        "_rurais": rurais,
        "_urbanos": urbanos,
        "_georef": rurais_com_georef,
        "_needs_review": needs_review,
        "_duplicadas_detail": duplicadas,
        "_faltantes": faltantes,
        "_rurais_sem_car": rurais_sem_car,
        "_rurais_sem_nirf": rurais_sem_nirf,
        "_rurais_sem_ccir": rurais_sem_ccir,
        "_urbanos_com_rurais": urbanos_com_rurais,
    }


# ---------------------------------------------------------------------------
# Escrever CSV sanitizado
# ---------------------------------------------------------------------------
def write_csv(records: list[InventoryRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for rec in records:
            writer.writerow(record_to_dict(rec))


# ---------------------------------------------------------------------------
# Escrever JSON sanitizado
# ---------------------------------------------------------------------------
def write_json_sanitized(records: list[InventoryRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [record_to_dict(r) for r in records]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Escrever/atualizar SQLite
# ---------------------------------------------------------------------------
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ri_real_json_inventory (
    record_id TEXT PRIMARY KEY,
    cns TEXT,
    numero_registro TEXT,
    livro TEXT,
    matricula_numero INTEGER,
    digito_verificador_onr TEXT,
    registro_tipo INTEGER,
    tipo_de_imovel INTEGER,
    localizacao_codigo INTEGER,
    natureza_imovel TEXT,
    natureza_imovel_fonte TEXT,
    natureza_imovel_confidence TEXT,
    uf_codigo TEXT,
    cidade_codigo TEXT,
    bairro_sanitizado TEXT,
    cep_sanitizado TEXT,
    tem_quadra INTEGER,
    tem_lote INTEGER,
    tem_loteamento INTEGER,
    tem_condominio INTEGER,
    tem_car INTEGER,
    car_codigo TEXT,
    tem_nirf INTEGER,
    nirf_codigo TEXT,
    nirf_status TEXT,
    tem_ccir INTEGER,
    ccir_codigo TEXT,
    tem_numero_incra INTEGER,
    numero_incra_codigo TEXT,
    tem_sigef INTEGER,
    sigef_codigo TEXT,
    tem_denominacao_rural INTEGER,
    denominacao_rural_sanitizada TEXT,
    tem_acidente_geografico INTEGER,
    acidente_geografico_sanitizado TEXT,
    possui_georreferenciamento INTEGER,
    georreferenciamento_criterio TEXT,
    status_extracao TEXT,
    status_revisao_ri TEXT,
    observacoes_tecnicas_sem_pii TEXT,
    fonte_arquivo TEXT,
    hash_registro_sanitizado TEXT
)
"""

_CREATE_RUNS_SQL = """
CREATE TABLE IF NOT EXISTS ri_real_json_runs (
    run_id TEXT PRIMARY KEY,
    fonte_arquivo TEXT,
    cns TEXT,
    total_registros INTEGER,
    total_urbano INTEGER,
    total_rural INTEGER,
    total_indeterminado INTEGER,
    executed_at TEXT
)
"""

_INSERT_SQL = """
INSERT OR REPLACE INTO ri_real_json_inventory VALUES (
    :record_id, :cns, :numero_registro, :livro, :matricula_numero,
    :digito_verificador_onr, :registro_tipo, :tipo_de_imovel,
    :localizacao_codigo, :natureza_imovel, :natureza_imovel_fonte,
    :natureza_imovel_confidence, :uf_codigo, :cidade_codigo,
    :bairro_sanitizado, :cep_sanitizado,
    :tem_quadra, :tem_lote, :tem_loteamento, :tem_condominio,
    :tem_car, :car_codigo, :tem_nirf, :nirf_codigo, :nirf_status,
    :tem_ccir, :ccir_codigo, :tem_numero_incra, :numero_incra_codigo,
    :tem_sigef, :sigef_codigo, :tem_denominacao_rural,
    :denominacao_rural_sanitizada, :tem_acidente_geografico,
    :acidente_geografico_sanitizado, :possui_georreferenciamento,
    :georreferenciamento_criterio, :status_extracao, :status_revisao_ri,
    :observacoes_tecnicas_sem_pii, :fonte_arquivo, :hash_registro_sanitizado
)
"""


def write_sqlite(records: list[InventoryRecord], db_path: Path, metrics: dict, fonte: str, cns: str) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_TABLE_SQL)
    conn.execute(_CREATE_RUNS_SQL)

    rows = []
    for rec in records:
        d = record_to_dict(rec)
        # Converter bool para int para SQLite
        for k in ["tem_quadra", "tem_lote", "tem_loteamento", "tem_condominio",
                   "tem_car", "tem_nirf", "tem_ccir", "tem_numero_incra",
                   "tem_sigef", "tem_denominacao_rural", "tem_acidente_geografico",
                   "possui_georreferenciamento"]:
            d[k] = int(d[k])
        rows.append(d)

    conn.executemany(_INSERT_SQL, rows)

    run_id = str(uuid.uuid4())
    conn.execute(
        "INSERT OR REPLACE INTO ri_real_json_runs VALUES (?,?,?,?,?,?,?,?)",
        (
            run_id, fonte, cns,
            metrics["total_registros"],
            metrics["total_urbano"],
            metrics["total_rural"],
            metrics["total_indeterminado"],
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Escrever CSV de revisão manual (somente campos-chave, sem PII)
# ---------------------------------------------------------------------------
_REVIEW_FIELDS = [
    "matricula_numero", "numero_registro", "natureza_imovel",
    "tem_car", "tem_nirf", "nirf_status", "tem_ccir",
    "tem_numero_incra", "tem_sigef", "possui_georreferenciamento",
    "georreferenciamento_criterio", "status_extracao",
    "status_revisao_ri", "observacoes_tecnicas_sem_pii",
]


def write_review_csv(records: list[InventoryRecord], path: Path) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_REVIEW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow(record_to_dict(rec))


# ---------------------------------------------------------------------------
# Relatório summary Markdown
# ---------------------------------------------------------------------------
def write_summary_report(
    metrics: dict,
    cns: str,
    fonte: str,
    executed_at: str,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    rurais = metrics["_rurais"]
    urbanos = metrics["_urbanos"]
    georef = metrics["_georef"]
    needs_review = metrics["_needs_review"]
    faltantes = metrics["_faltantes"]
    duplicadas = metrics["_duplicadas_detail"]

    def mat_list(lst: list[InventoryRecord], n: int = 50) -> str:
        nums = sorted(set(r.matricula_numero for r in lst if r.matricula_numero > 0))[:n]
        return ", ".join(str(m) for m in nums) if nums else "—"

    lines = [
        "# Relatório Resumo — Indicador Real JSON",
        "",
        "## 1. Identificação",
        f"- **CNS:** {cns}",
        f"- **Arquivo:** `{fonte}`",
        f"- **Executado em:** {executed_at}",
        "",
        "## 2. Totais",
        f"- Total de registros processados: **{metrics['total_registros']}**",
        f"- Matrículas únicas: **{metrics['matriculas_unicas']}**",
        f"- Menor matrícula: **{metrics['min_matricula']}**",
        f"- Maior matrícula: **{metrics['max_matricula']}**",
        f"- Duplicidades (matrícula_numero repetida): **{len(duplicadas)}**",
        f"- Matrículas faltantes no intervalo: **{len(faltantes)}**",
        "",
        "## 3. Natureza do Imóvel",
        f"- Urbanos (LOCALIZACAO=0): **{metrics['total_urbano']}**",
        f"- Rurais (LOCALIZACAO=1): **{metrics['total_rural']}**",
        f"- Indeterminados (LOCALIZACAO inválida): **{metrics['total_indeterminado']}**",
        "",
        "## 4. Dados Rurais",
        f"- Rurais com CAR: **{metrics['rurais_com_car']}**",
        f"- Rurais sem CAR: **{metrics['rurais_sem_car']}**",
        f"- Rurais com NIRF válido: **{metrics['rurais_com_nirf']}**",
        f"- Rurais com NIRF placeholder (só zeros): **{metrics['rurais_nirf_zeros']}**",
        f"- Rurais sem NIRF: **{metrics['rurais_sem_nirf']}**",
        f"- Rurais com CCIR: **{metrics['rurais_com_ccir']}**",
        f"- Rurais sem CCIR: **{metrics['rurais_sem_ccir']}**",
        f"- Rurais com NUMERO_INCRA: **{metrics['rurais_com_incra']}**",
        f"- Rurais com SIGEF: **{metrics['rurais_com_sigef']}**",
        f"- Rurais com DENOMINACAORURAL: **{metrics['rurais_com_denominacao']}**",
        f"- Rurais sem DENOMINACAORURAL: **{metrics['rurais_sem_denominacao']}**",
        f"- Rurais com georreferenciamento (INCRA ou SIGEF): **{metrics['rurais_com_georef']}**",
        "",
        "## 5. Qualidade",
        f"- NUMERO_REGISTRO inválido: **{metrics['nr_invalidos']}**",
        f"- CNS divergente: **{metrics['cns_divergentes']}**",
        f"- LOCALIZACAO inválida: **{metrics['loc_invalidas']}**",
        f"- Urbanos com campos rurais preenchidos: **{metrics['urbanos_com_campos_rurais']}**",
        f"- Registros com inconsistência urbano/rural: **{metrics['inconsistentes']}**",
        f"- Registros needs_manual_review: **{metrics['needs_review']}**",
        "",
        "## 6. Listas Seguras (primeiras 50)",
        "",
        "### Matrículas Rurais",
        mat_list(rurais),
        "",
        "### Matrículas Urbanas",
        mat_list(urbanos),
        "",
        "### Matrículas Georreferenciadas",
        mat_list(georef),
        "",
        "### Matrículas Needs Review",
        mat_list(needs_review),
        "",
    ]

    if faltantes:
        lines.append("### Matrículas Faltantes no Intervalo")
        falt_str = ", ".join(str(m) for m in faltantes[:200])
        if len(faltantes) > 200:
            falt_str += f" ... (+{len(faltantes) - 200} mais)"
        lines.append(falt_str)
        lines.append("")

    if duplicadas:
        lines.append("### Duplicidades (matricula_numero -> ocorrências)")
        for mat, cnt in sorted(duplicadas.items()):
            lines.append(f"- Matrícula {mat}: {cnt} registros")
        lines.append("")

    lines += [
        "---",
        "*Relatório gerado automaticamente. Não contém dados pessoais.*",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Relatório de alertas de qualidade
# ---------------------------------------------------------------------------
def write_quality_alerts(records: list[InventoryRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    alertas_por_tipo: dict[str, list[int]] = {}
    for rec in records:
        for obs in rec.observacoes_tecnicas_sem_pii:
            alertas_por_tipo.setdefault(obs, []).append(rec.matricula_numero)
        for st in rec.status_extracao:
            if st != "ok":
                alertas_por_tipo.setdefault(st, []).append(rec.matricula_numero)

    lines = [
        "# Alertas de Qualidade — Indicador Real JSON",
        "",
    ]
    if not alertas_por_tipo:
        lines.append("Nenhum alerta de qualidade detectado.")
    else:
        for tipo, mats in sorted(alertas_por_tipo.items()):
            uniq = sorted(set(mats))
            sample = ", ".join(str(m) for m in uniq[:50])
            if len(uniq) > 50:
                sample += f" ... (+{len(uniq) - 50})"
            lines.append(f"## {tipo}")
            lines.append(f"- Ocorrências: {len(uniq)}")
            lines.append(f"- Matrículas: {sample}")
            lines.append("")

    lines += [
        "---",
        "*Relatório gerado automaticamente. Não contém dados pessoais.*",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Lógica principal
# ---------------------------------------------------------------------------
def run(
    input_path: Path,
    dry_run: bool,
    write_sanitized: bool,
    write_db: bool,
    write_reports: bool,
) -> None:
    executed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fonte = input_path.name

    print(f"[analyze_ri_real_json] Lendo: {input_path}")
    try:
        with open(input_path, encoding="utf-8") as f:
            raw_json = json.load(f)
    except Exception as e:
        print(f"[ERRO] Não foi possível ler o JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if "INDICADOR_REAL" not in raw_json:
        print("[ERRO] Chave 'INDICADOR_REAL' não encontrada no JSON.", file=sys.stderr)
        sys.exit(1)

    ir = raw_json["INDICADOR_REAL"]
    cns = str(ir.get("CNS", ""))
    reals = ir.get("REAL", [])

    print(f"[analyze_ri_real_json] CNS identificado: {cns}")
    print(f"[analyze_ri_real_json] Total de registros em REAL: {len(reals)}")

    if not reals:
        print("[AVISO] Nenhum registro encontrado em INDICADOR_REAL.REAL.")
        return

    # Processar registros
    records: list[InventoryRecord] = []
    for raw in reals:
        rec = process_record(raw, cns, fonte)
        records.append(rec)

    # Calcular métricas
    metrics = compute_metrics(records)

    # Exibir resumo no console (sem PII)
    print("\n=== RESUMO ===")
    print(f"  Total registros       : {metrics['total_registros']}")
    print(f"  Matrículas únicas     : {metrics['matriculas_unicas']}")
    print(f"  Menor matrícula       : {metrics['min_matricula']}")
    print(f"  Maior matrícula       : {metrics['max_matricula']}")
    print(f"  Matrículas faltantes  : {len(metrics['matriculas_faltantes'])}")
    print(f"  Duplicidades          : {len(metrics['matriculas_duplicadas'])}")
    print(f"  Urbanos               : {metrics['total_urbano']}")
    print(f"  Rurais                : {metrics['total_rural']}")
    print(f"  Indeterminados        : {metrics['total_indeterminado']}")
    print(f"  Rurais com CAR        : {metrics['rurais_com_car']}")
    print(f"  Rurais com NIRF válido: {metrics['rurais_com_nirf']}")
    print(f"  Rurais NIRF zeros     : {metrics['rurais_nirf_zeros']}")
    print(f"  Rurais com CCIR       : {metrics['rurais_com_ccir']}")
    print(f"  Rurais com INCRA      : {metrics['rurais_com_incra']}")
    print(f"  Rurais com SIGEF      : {metrics['rurais_com_sigef']}")
    print(f"  Com georreferenciamento: {metrics['rurais_com_georef']}")
    print(f"  Urbanos c/ campos rurais: {metrics['urbanos_com_campos_rurais']}")
    print(f"  Inconsistências       : {metrics['inconsistentes']}")
    print(f"  Needs review          : {metrics['needs_review']}")
    print(f"  NUMERO_REGISTRO inv.  : {metrics['nr_invalidos']}")
    print(f"  CNS divergente        : {metrics['cns_divergentes']}")
    print(f"  LOCALIZACAO inválida  : {metrics['loc_invalidas']}")

    if dry_run:
        print("\n[DRY-RUN] Nenhum arquivo escrito.")
        return

    pii_issues_total = 0

    # Sanitized CSV
    if write_sanitized:
        csv_path = SANITIZED_DIR / "ri_real_json_inventory_sanitized.csv"
        print(f"\n[write] CSV -> {csv_path}")
        write_csv(records, csv_path)

        json_path = SANITIZED_DIR / "ri_real_json_inventory_sanitized.json"
        print(f"[write] JSON -> {json_path}")
        write_json_sanitized(records, json_path)

        # Anti-PII scan
        for p in [csv_path, json_path]:
            issues = scan_file_anti_pii(p)
            if issues:
                pii_issues_total += len(issues)
                print(f"[ANTI-PII] {p.name}: {len(issues)} ocorrências suspeitas detectadas")
                for tipo, linha, desc in issues[:5]:
                    print(f"  -> linha {linha}: {tipo} — {desc}")
            else:
                print(f"[ANTI-PII] {p.name}: OK")

    # SQLite
    if write_db:
        db_path = DB_DIR / "ri_inventory.sqlite"
        print(f"[write] SQLite -> {db_path}")
        write_sqlite(records, db_path, metrics, fonte, cns)

        db_issues = scan_sqlite_anti_pii(db_path, "ri_real_json_inventory")
        if db_issues:
            pii_issues_total += len(db_issues)
            for col, tbl, desc in db_issues:
                print(f"[ANTI-PII] SQLite/{tbl}/{col}: {desc}")
        else:
            print("[ANTI-PII] SQLite: OK")

    # Reports
    if write_reports:
        rurais = metrics["_rurais"]
        urbanos = metrics["_urbanos"]
        georef = metrics["_georef"]
        needs_review = metrics["_needs_review"]

        rurais_sem_car = metrics["_rurais_sem_car"]
        rurais_sem_nirf = metrics["_rurais_sem_nirf"]
        rurais_sem_ccir = metrics["_rurais_sem_ccir"]
        urbanos_com_rurais = metrics["_urbanos_com_rurais"]

        # Summary
        summary_path = REPORTS_DIR / "ri_real_json_summary.md"
        print(f"[write] Summary -> {summary_path}")
        write_summary_report(metrics, cns, fonte, executed_at, summary_path)

        # Quality alerts
        quality_path = REPORTS_DIR / "ri_real_json_quality_alerts.md"
        print(f"[write] Quality alerts -> {quality_path}")
        write_quality_alerts(records, quality_path)

        # Manual review CSVs
        review_map = {
            "ri_real_json_rural_records.csv": rurais,
            "ri_real_json_urban_records.csv": urbanos,
            "ri_real_json_georeferenced_rural.csv": georef,
            "ri_real_json_rural_missing_car.csv": rurais_sem_car,
            "ri_real_json_rural_missing_nirf.csv": rurais_sem_nirf,
            "ri_real_json_rural_missing_ccir.csv": rurais_sem_ccir,
            "ri_real_json_needs_review.csv": needs_review,
            "ri_real_json_urban_with_rural_fields.csv": urbanos_com_rurais,
        }
        for fname, lst in review_map.items():
            p = MANUAL_REVIEW_DIR / fname
            print(f"[write] Review CSV -> {p} ({len(lst)} registros)")
            write_review_csv(lst, p)

        # Duplicatas
        dup_path = MANUAL_REVIEW_DIR / "ri_real_json_duplicates.csv"
        duplicadas = metrics["_duplicadas_detail"]
        dup_records = [r for r in records if r.matricula_numero in duplicadas]
        write_review_csv(dup_records, dup_path)
        print(f"[write] Duplicatas -> {dup_path} ({len(dup_records)} registros)")

        # Anti-PII scan nos relatórios
        for p in [summary_path, quality_path]:
            issues = scan_file_anti_pii(p)
            if issues:
                pii_issues_total += len(issues)
                print(f"[ANTI-PII] {p.name}: {len(issues)} ocorrências suspeitas")
            else:
                print(f"[ANTI-PII] {p.name}: OK")

    if pii_issues_total > 0:
        print(f"\n[ANTI-PII] ATENÇÃO: {pii_issues_total} ocorrências suspeitas detectadas nos derivados.")
        print("[ANTI-PII] Revisar manualmente antes de compartilhar arquivos.")
    else:
        print("\n[ANTI-PII] Varredura concluída: nenhuma PII detectada nos derivados.")

    print("\n[analyze_ri_real_json] Concluído.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Analisa o Indicador Real JSON da serventia — sprint RI-REAL-JSON-1"
    )
    p.add_argument("--input", required=True, help="Caminho para o Indicador_Real.json")
    p.add_argument(
        "--dry-run", action="store_true",
        help="Processa e exibe métricas sem escrever nenhum arquivo",
    )
    p.add_argument("--write-sanitized", action="store_true", help="Escrever CSV e JSON sanitizados")
    p.add_argument("--write-db", action="store_true", help="Escrever/atualizar SQLite")
    p.add_argument("--write-reports", action="store_true", help="Escrever relatórios Markdown e CSVs de revisão")
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERRO] Arquivo não encontrado: {input_path}", file=sys.stderr)
        sys.exit(1)
    run(
        input_path=input_path,
        dry_run=args.dry_run,
        write_sanitized=args.write_sanitized,
        write_db=args.write_db,
        write_reports=args.write_reports,
    )
