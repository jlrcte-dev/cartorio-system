"""
Extrator sanitizado de matrículas rurais — Cartório System v3
Fonte: relatórios PDF do Engegraph (FICHA TABULAR - ÁREA RURAL)

PROTEÇÃO DE DADOS:
- Nenhum nome, CPF, CNPJ ou RG é salvo ou impresso em nenhuma hipótese.
- Linhas de PII (proprietário, CPF/CI/SSP) são descartadas silenciosamente.
- Se PII for detectada na saída, a extração aborta sem salvar nada.
- Os PDFs brutos devem ficar exclusivamente em _local_data/ri_inventory/raw/.

USO:
    # Inspeção rápida (2 páginas, sem salvar):
    python scripts/local_tools/extract_ri_rural_inventory.py \\
        --input _local_data/ri_inventory/raw/Relatorio_matriculas_rurais.pdf \\
        --tipo rural --dry-run --sample-pages 2

    # Extração completa com CSV/JSON e banco SQLite:
    python scripts/local_tools/extract_ri_rural_inventory.py \\
        --input _local_data/ri_inventory/raw/Relatorio_matriculas_rurais.pdf \\
        --tipo rural --write-sanitized --write-db

    python scripts/local_tools/extract_ri_rural_inventory.py \\
        --input _local_data/ri_inventory/raw/Relatorio_matriculas_rurais_georreferenciadas.pdf \\
        --tipo georref --write-sanitized --write-db

CHANGELOG v3:
    - Corrigido: INCRA NÃO implica georreferenciamento — apenas "Sim" explícito no campo Georef.
    - Novo: georreferenciamento_detectado_direto (Sim explícito em Georef.)
    - Novo: georreferenciamento_inferido_por_fonte (registro no relatório georref)
    - Novo: _normalize_nirf — rejeita NIRF composto somente por zeros
    - Novo: _extract_all_totals — detecta subtotais vs total global
    - Novo: _migrate_db — migração idempotente para DBs pré-existentes
    - Adicionado "incra_sem_georef_explicito" em observacoes_tecnicas_sem_pii quando aplicável
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Caminhos base
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
LOCAL_DATA = BASE_DIR / "_local_data"
SANITIZED_DIR = LOCAL_DATA / "ri_inventory" / "sanitized"
REPORTS_DIR = LOCAL_DATA / "ri_inventory" / "reports"
DB_DIR = LOCAL_DATA / "ri_inventory" / "db"

# Campos da base sanitizada (25 campos)
FIELDNAMES = [
    "record_id",
    "tipo_registro",
    "matricula_numero",
    "nome_imovel_sanitizado",
    "municipio",
    "area_texto_original",
    "area_valor_normalizado",
    "area_unidade",
    "is_rural",
    "tem_georreferenciamento",
    "georreferenciamento_detectado_direto",
    "georreferenciamento_inferido_por_fonte",
    "georreferenciamento_valor",
    "tem_incra",
    "incra_codigo",
    "tem_nirf",
    "nirf_codigo",
    "tem_reserva",
    "reserva_valor",
    "fonte_relatorio",
    "pagina_origem",
    "ordem_no_relatorio",
    "hash_bloco_origem",
    "status_extracao",
    "observacoes_tecnicas_sem_pii",
]

# Total da serventia (dado institucional) — usado como controle de qualidade
_TOTAL_GERAL_SERVENTIA = 3523

# ---------------------------------------------------------------------------
# Padrões de detecção de PII — usados para DESCARTAR linhas e validar saída
# ---------------------------------------------------------------------------
_CPF_RE = re.compile(r"\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[\-\.\s]?\d{2}")
_CNPJ_RE = re.compile(r"\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\.\s\/]?\d{4}[\-\.\s]?\d{2}")
_DOC_LABEL = re.compile(
    r"\bCPF\b|\bCNPJ\b|\bCI\b|\bSSP\b|\bRG\b|\bCIC\b|\bCED\b", re.I
)
# Detecta 2+ palavras em caixa alta consecutivas (suspeito de nome de pessoa)
_NOME_CAPS = re.compile(
    r"([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]{3,}\s+){1,}[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]{3,}"
)

# ---------------------------------------------------------------------------
# Padrões estruturais do PDF
# ---------------------------------------------------------------------------
_SEP = re.compile(r"^_{4,}")
_TIPO_NUM_RE = re.compile(r"^([MTmt])\s+(\d+)\s*(.*)", re.DOTALL)
_CARACT_RE = re.compile(r"^Caract\.", re.I)
_GEOREF_LINE_RE = re.compile(r"^Georef\.", re.I)
# "Total: N" ou "Total N" — qualquer posição na página
_TOTAL_RE = re.compile(r"\bTotal\s*[:\-]?\s*(\d{3,})\b", re.I)

# ---------------------------------------------------------------------------
# Padrões de campos técnicos
# ---------------------------------------------------------------------------
_AREA_RE = re.compile(
    r"([\d.,]+)\s*(ha|hectares?|m[²2]|alqueires?|ac\.?|ares?)",
    re.IGNORECASE,
)
_UNIDADE_MAP = {
    "ha": "ha", "hectare": "ha", "hectares": "ha",
    "m²": "m2", "m2": "m2",
    "alqueire": "alqueire", "alqueires": "alqueire",
    "ac": "ac", "ac.": "ac",
    "are": "are", "ares": "are",
}

_GEOREF_SIM_RE = re.compile(r"\bSim\b", re.I)
# INCRA: dígitos e pontos, mínimo 4 chars a partir de dígito (exclui "NIRF" e outros textos)
_INCRA_CODE_RE = re.compile(r"(?:Incra\s+)(\d[\d.]{3,})", re.I)
_INCRA_ZEROS = re.compile(r"^[0.]+$")
# NIRF: requer ao menos 3 dígitos após o rótulo
_NIRF_VALUE_RE = re.compile(r"\bNIRF\s+([0-9]{3,})\b", re.I)
_NIRF_ALL_ZEROS = re.compile(r"^0+$")
_RESERVA_SIM_RE = re.compile(r"\bReserva\s+Sim\b", re.I)
_RESERVA_NAO_RE = re.compile(r"\bReserva\s+N[ãa]o\b", re.I)
_RESERVA_LABEL_RE = re.compile(r"\bReserva\b", re.I)

_MUNICIPIO_RE = re.compile(
    r"munic[íi]pio\s+de\s+([A-Za-záéíóúâêîôûãõçÁÉÍÓÚ][A-Za-záéíóúâêîôûãõçÁÉÍÓÚ\s]+?)"
    r"(?:\s*,|\s*GO\b|\s*Reserv|\s*Geo\b|$)",
    re.I,
)
_MUNICIPIO_INVALIDO = re.compile(
    r"Reserv|Incra|Georef|NIRF|\bSim\b|\bNão\b", re.I
)
# Municípios conhecidos da circunscrição
_MUNICIPIO_KNOWN = re.compile(
    r"Terez[oó]polis\s+de\s+Goi[aá]s|Goian[aá]polis",
    re.I,
)
# Palavras-chave que indicam nome de imóvel/fazenda (não de pessoa)
_IMOVEL_KEYWORDS = re.compile(
    r"\b(fazenda|s[ií]tio|ch[áa]cara|gleba|retiro|rancho|[áa]rea|lote|granja|"
    r"brejo|v[áa]rzea|haras|ribeir[ãa]o|c[oó]rrego|parque|quinta|propr\.?|"
    r"c[áa]pula|campo|cerrado|mata|estrada|bairro)\b",
    re.I,
)

# Campos técnicos cujos valores podem ter dígitos longos — excluídos da varredura de PII
_CAMPOS_CODIGOS_TECNICOS = frozenset({
    "hash_bloco_origem",
    "incra_codigo",
    "nirf_codigo",
    "georreferenciamento_valor",
})


# ---------------------------------------------------------------------------
# Hash de bloco — rastreabilidade sem expor conteúdo
# Prefixo "H-" + 6 hex chars → máximo 6 dígitos consecutivos possíveis.
# Impossível atingir os 11 dígitos mínimos de CPF ou 14 de CNPJ.
# ---------------------------------------------------------------------------
def _hash_bloco(lines: list[str]) -> str:
    texto = "\n".join(lines[:3])
    return "H-" + hashlib.sha256(texto.encode("utf-8", errors="replace")).hexdigest()[:6]


# ---------------------------------------------------------------------------
# Detecção de PII nas linhas brutas
# ---------------------------------------------------------------------------
def _is_pii_line(line: str) -> bool:
    """Retorna True se a linha contiver padrão de dados pessoais."""
    # Linhas técnicas estruturadas do Engegraph nunca contêm CPF/CNPJ pessoais.
    # Os códigos INCRA (14 dígitos) casariam incorretamente com o regex CNPJ.
    if _CARACT_RE.match(line) or _GEOREF_LINE_RE.match(line):
        return False
    if _DOC_LABEL.search(line):
        return True
    if _CPF_RE.search(line):
        return True
    if _CNPJ_RE.search(line):
        return True
    # Sequência de nomes em caixa alta — excluindo linha de registro (M/T + número)
    if _NOME_CAPS.search(line) and not _TIPO_NUM_RE.match(line):
        return True
    return False


# ---------------------------------------------------------------------------
# Normalização de área — returns (valor, unidade, is_ambiguous)
# ---------------------------------------------------------------------------
def _normalize_area(texto: str) -> tuple[float | None, str | None, bool]:
    m = _AREA_RE.search(texto or "")
    if not m:
        return None, None, False

    valor_raw = m.group(1)
    commas = valor_raw.count(",")
    dots = valor_raw.count(".")
    is_ambiguous = commas > 1

    valor: float | None = None
    try:
        if commas > 1:
            # Ex: "174,25,22" — múltiplas vírgulas, interpretação ambígua
            valor = None
        elif commas == 1 and dots >= 1:
            # Formato BR com milhar: "1.200,50"
            valor = float(valor_raw.replace(".", "").replace(",", "."))
        elif commas == 1:
            # "200,50" → "200.50"
            valor = float(valor_raw.replace(",", "."))
        elif dots > 1:
            # "1.200.500" → milhar sem decimal
            valor = float(valor_raw.replace(".", ""))
        else:
            valor = float(valor_raw)
    except ValueError:
        valor = None
        is_ambiguous = True

    unidade_raw = m.group(2).lower().rstrip(".")
    unidade = _UNIDADE_MAP.get(unidade_raw, unidade_raw)
    return valor, unidade, is_ambiguous


# ---------------------------------------------------------------------------
# Normalização de NIRF — rejeita zeros e valores ambíguos
# ---------------------------------------------------------------------------
def _normalize_nirf(
    raw_value: str | None,
) -> tuple[bool, str | None, str | None]:
    """
    Valida e normaliza código NIRF.
    Returns: (tem_nirf, nirf_codigo, obs_tecnica)
      - None/""/espaços                   → (False, None, None)
      - somente zeros (qualquer tamanho)  → (False, None, "nirf_zerado_ignorado")
      - dígitos com ao menos 1 não-zero  → (True, valor_normalizado, None)
      - caracteres não numéricos          → (False, None, "nirf_ambiguo")
    """
    if raw_value is None:
        return False, None, None

    stripped = raw_value.strip()
    if not stripped:
        return False, None, None

    # Remover separadores para análise
    digits_only = re.sub(r"[\s.\-]", "", stripped)
    if not digits_only:
        return False, None, None

    if not digits_only.isdigit():
        return False, None, "nirf_ambiguo"

    if _NIRF_ALL_ZEROS.match(digits_only):
        return False, None, "nirf_zerado_ignorado"

    return True, stripped, None


# ---------------------------------------------------------------------------
# Extração segura do nome do imóvel/fazenda
# ---------------------------------------------------------------------------
def _extract_nome_imovel(denominacao_raw: str) -> tuple[str, bool]:
    """
    Tenta extrair nome do imóvel de forma segura da linha principal.
    Returns (nome_sanitizado, is_suspicious).
    Se suspeito de ser nome de pessoa, retorna ("", True).
    """
    if not denominacao_raw.strip():
        return "", False

    texto = denominacao_raw.strip()

    # Remover área se presente
    texto = _AREA_RE.sub("", texto).strip()

    # Remover município conhecido se presente
    texto = _MUNICIPIO_KNOWN.sub("", texto).strip()

    # Remover trailing punctuation
    texto = re.sub(r"[,/\-]+$", "", texto).strip()

    if not texto or len(texto) <= 2:
        return "", False

    # Segurança: ALL CAPS com 2+ palavras → suspeito de nome de pessoa,
    # EXCETO se começa com keyword de imóvel (Fazenda, Sítio, Chácara...).
    # No Engegraph, fazenda names aparecem em ALL CAPS na coluna "Nome".
    if _NOME_CAPS.match(texto) and not _IMOVEL_KEYWORDS.match(texto.strip()):
        return "", True

    # Segurança: padrões PII diretos
    if _DOC_LABEL.search(texto) or _CPF_RE.search(texto) or _CNPJ_RE.search(texto):
        return "", True

    return texto, False


# ---------------------------------------------------------------------------
# Divisão de texto em blocos separados por ____
# ---------------------------------------------------------------------------
def _split_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_ln in text.splitlines():
        ln = raw_ln.strip()
        if _SEP.match(ln):
            if current:
                blocks.append(current)
            current = []
        elif ln:
            current.append(ln)
    if current:
        blocks.append(current)
    return blocks


# ---------------------------------------------------------------------------
# Detecção de total reportado no PDF
# ---------------------------------------------------------------------------
def _extract_total_reportado(pages_text: list[str]) -> int | None:
    """Busca padrão 'Total: N' nas primeiras 3 páginas do PDF (compatibilidade)."""
    for text in pages_text[:3]:
        m = _TOTAL_RE.search(text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


def _extract_all_totals(pages_text: list[str]) -> dict[str, Any]:
    """
    Varre TODAS as páginas por padrão 'Total: N'.
    Classifica cada valor como global_candidato, subtotal_repetido ou indeterminado.
    Não imprime conteúdo textual — apenas números e posições de página.
    """
    occurrences: dict[int, list[int]] = {}
    for i, text in enumerate(pages_text):
        for m in _TOTAL_RE.finditer(text):
            try:
                val = int(m.group(1))
                occurrences.setdefault(val, []).append(i + 1)
            except ValueError:
                pass

    result: dict[str, Any] = {}
    for val, pages in occurrences.items():
        n = len(pages)
        if n > 5:
            classificacao = "subtotal_repetido"
        elif n == 1 and val >= 100:
            classificacao = "total_global_candidato"
        elif n <= 3 and val >= _TOTAL_GERAL_SERVENTIA * 0.8:
            classificacao = "total_global_candidato"
        else:
            classificacao = "indeterminado"
        result[str(val)] = {
            "valor": val,
            "ocorrencias": n,
            "paginas": pages[:10],  # limitar lista de páginas para segurança
            "classificacao": classificacao,
        }
    return result


# ---------------------------------------------------------------------------
# Parsing de um único bloco
# ---------------------------------------------------------------------------
def _parse_block(
    block: list[str],
    record_id: int,
    ordem: int,
    pagina: int,
    fonte: str,
    tipo_relatorio: str,
) -> dict[str, Any] | None:
    """
    Extrai campos técnicos de um bloco de linhas descartando PII.
    Retorna None se o bloco não corresponder a um registro válido.

    REGRAS DE GEORREFERENCIAMENTO (v3):
    - tem_georreferenciamento_detectado_direto=True SOMENTE quando "Sim" está
      explícito na linha "Georef." do relatório rural.
    - INCRA válido NÃO implica georreferenciamento por si só.
    - "Georef. Incra XXXXX NIRF" sem "Sim" antes do INCRA → georref=False.
    - Relatório georref: todos os registros recebem
      georreferenciamento_inferido_por_fonte=True.
    """
    if not block:
        return None

    primeira = block[0]
    m = _TIPO_NUM_RE.match(primeira)
    if not m:
        return None

    tipo = m.group(1).upper()
    try:
        numero = int(m.group(2))
    except ValueError:
        return None

    denominacao_raw = m.group(3).strip()

    # Campos a preencher
    area_texto = ""
    area_valor: float | None = None
    area_unidade: str | None = None
    area_ambigua = False
    nome_imovel = ""
    municipio = ""
    tem_georref = False
    georref_detectado_direto = False
    georref_inferido_fonte = False
    georref_valor: str | None = None
    tem_incra = False
    incra_codigo: str | None = None
    tem_nirf = False
    nirf_codigo: str | None = None
    tem_reserva: bool | None = None
    reserva_valor: str | None = None
    obs_parts: list[str] = []
    needs_review = False
    pii_linhas = 0

    # Área pode aparecer na linha principal (denominacao_raw)
    area_m = _AREA_RE.search(denominacao_raw)
    if area_m:
        area_texto = area_m.group(0).strip()
        area_valor, area_unidade, area_ambigua = _normalize_area(area_texto)
        if area_ambigua:
            obs_parts.append("area_ambigua")

    # Nome do imóvel — extração segura do residual da linha principal
    nome_imovel, suspeito = _extract_nome_imovel(denominacao_raw)
    if suspeito:
        nome_imovel = ""
        needs_review = True
        obs_parts.append("nome_linha_principal_suspeito")

    # Processar linhas restantes (descartando PII silenciosamente)
    for line in block[1:]:
        if _is_pii_line(line):
            pii_linhas += 1
            continue  # NUNCA imprimir conteúdo PII

        if _CARACT_RE.match(line):
            # Área: tentar extrair da Caract. se não encontrada na linha principal
            if not area_texto:
                area_m2 = _AREA_RE.search(line)
                if area_m2:
                    area_texto = area_m2.group(0).strip()
                    area_valor, area_unidade, area_ambigua = _normalize_area(area_texto)
                    obs_parts.append("area_extraida_da_caracteristica")
                    if area_ambigua:
                        obs_parts.append("area_ambigua")

            # Reserva na Caract.
            if tem_reserva is None:
                if _RESERVA_SIM_RE.search(line):
                    tem_reserva = True
                    reserva_valor = "Sim"
                elif _RESERVA_NAO_RE.search(line):
                    tem_reserva = False
                    reserva_valor = "Não"
                elif _RESERVA_LABEL_RE.search(line):
                    tem_reserva = None
                    reserva_valor = None

            # Município na Caract.
            if not municipio:
                mun_m = _MUNICIPIO_RE.search(line)
                if mun_m:
                    mun_cand = mun_m.group(1).strip()
                    if not _MUNICIPIO_INVALIDO.search(mun_cand):
                        municipio = mun_cand
            continue

        if _GEOREF_LINE_RE.match(line):
            # REGRA v3: georreferenciamento confirmado SOMENTE se "Sim" explícito em Georef.
            if _GEOREF_SIM_RE.search(line):
                tem_georref = True
                georref_detectado_direto = True
                if not georref_valor:
                    georref_valor = "Sim"

            # INCRA: código numérico inequívoco
            incra_m = _INCRA_CODE_RE.search(line)
            if incra_m:
                code_raw = incra_m.group(1).strip()
                code_clean = re.sub(r"[.\-\s]", "", code_raw)
                if code_clean and not _INCRA_ZEROS.match(code_clean):
                    tem_incra = True
                    incra_codigo = code_raw
                    # INCRA NÃO implica georreferenciamento por si só (v3)
                    if not georref_detectado_direto:
                        obs_parts.append("incra_sem_georef_explicito")

            # NIRF: normalizar — rejeitar zeros e ambiguidades
            nirf_m = _NIRF_VALUE_RE.search(line)
            if nirf_m:
                nirf_raw = nirf_m.group(1).strip()
                nirf_valido, nirf_cod, nirf_obs = _normalize_nirf(nirf_raw)
                if nirf_valido:
                    tem_nirf = True
                    nirf_codigo = nirf_cod
                elif nirf_obs:
                    obs_parts.append(nirf_obs)

            # Reserva na linha Georef. (aparece quando não há Caract.)
            if tem_reserva is None:
                if _RESERVA_SIM_RE.search(line):
                    tem_reserva = True
                    reserva_valor = "Sim"
                elif _RESERVA_NAO_RE.search(line):
                    tem_reserva = False
                    reserva_valor = "Não"
            continue

    # Georreferenciamento por fonte: todos os registros do relatório georref
    # recebem inferência por origem (separado da detecção direta)
    if tipo_relatorio == "georref" and not georref_detectado_direto:
        tem_georref = True
        georref_inferido_fonte = True
        if not georref_valor:
            georref_valor = "inferred_by_fonte"
    elif tipo_relatorio == "georref" and georref_detectado_direto:
        # Mesmo com detecção direta, a fonte confirma que é georref
        georref_inferido_fonte = False  # já confirmado por Sim direto

    # Normalizar município
    municipio = _normalize_municipio(municipio)

    # Registrar área ausente nas observações
    if not area_texto:
        obs_parts.append("area_ausente")
    if pii_linhas > 0:
        obs_parts.append(f"pii_descartada:{pii_linhas}linhas")

    # Status de extração
    if needs_review:
        status = "needs_review"
    elif area_ambigua:
        status = "area_ambigua"
    else:
        status = "ok"

    return {
        "record_id": record_id,
        "tipo_registro": tipo,
        "matricula_numero": numero,
        "nome_imovel_sanitizado": nome_imovel,
        "municipio": municipio,
        "area_texto_original": area_texto,
        "area_valor_normalizado": area_valor,
        "area_unidade": area_unidade,
        "is_rural": True,
        "tem_georreferenciamento": tem_georref,
        "georreferenciamento_detectado_direto": georref_detectado_direto,
        "georreferenciamento_inferido_por_fonte": georref_inferido_fonte,
        "georreferenciamento_valor": georref_valor,
        "tem_incra": tem_incra,
        "incra_codigo": incra_codigo,
        "tem_nirf": tem_nirf,
        "nirf_codigo": nirf_codigo,
        "tem_reserva": tem_reserva,
        "reserva_valor": reserva_valor,
        "fonte_relatorio": fonte,
        "pagina_origem": pagina,
        "ordem_no_relatorio": ordem,
        "hash_bloco_origem": _hash_bloco(block),
        "status_extracao": status,
        "observacoes_tecnicas_sem_pii": "; ".join(obs_parts) if obs_parts else "",
    }


def _normalize_municipio(municipio: str) -> str:
    """Normaliza nome de município corrigindo garbled text do PDF."""
    if not municipio:
        return "Terezópolis de Goiás"
    mun_lower = municipio.lower()
    if "terezop" in mun_lower or "terezóp" in mun_lower:
        return "Terezópolis de Goiás"
    if "goianap" in mun_lower or "goianáp" in mun_lower:
        return "Goianápolis"
    if len(municipio) < 4 or _MUNICIPIO_INVALIDO.search(municipio):
        return "Terezópolis de Goiás"
    return municipio


# ---------------------------------------------------------------------------
# Detecção de duplicidades
# ---------------------------------------------------------------------------
def _detect_duplicates(
    records: list[dict[str, Any]], run_id: str
) -> list[dict[str, Any]]:
    count: dict[int, int] = {}
    fontes_map: dict[int, set[str]] = {}
    for r in records:
        n = r["matricula_numero"]
        count[n] = count.get(n, 0) + 1
        fontes_map.setdefault(n, set()).add(r["fonte_relatorio"])

    return [
        {
            "run_id": run_id,
            "matricula_numero": num,
            "ocorrencias": ocorrencias,
            "fontes": ";".join(sorted(fontes_map[num])),
            "observacao": "duplicidade_no_relatorio",
        }
        for num, ocorrencias in count.items()
        if ocorrencias > 1
    ]


# ---------------------------------------------------------------------------
# Extração do PDF
# ---------------------------------------------------------------------------
def _extract_from_pdf(
    pdf_path: Path,
    tipo_relatorio: str,
    sample_pages: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Extrai registros sanitizados do PDF.
    Returns: (records, meta) onde meta contém estatísticas da extração.
    """
    try:
        import pdfplumber
    except ImportError:
        print(
            "[ERRO] pdfplumber não instalado. Execute: pip install pdfplumber",
            file=sys.stderr,
        )
        sys.exit(1)

    records: list[dict[str, Any]] = []
    total_blocos = 0
    blocos_sem_registro = 0
    pages_text: list[str] = []
    ordem = 0
    record_id = 0

    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        limit = min(sample_pages, n_pages) if sample_pages else n_pages

        for i in range(limit):
            page = pdf.pages[i]
            text = page.extract_text() or ""
            pages_text.append(text)

            for block in _split_blocks(text):
                if not block:
                    continue
                if not _TIPO_NUM_RE.match(block[0]):
                    blocos_sem_registro += 1
                    continue

                total_blocos += 1
                ordem += 1
                record_id += 1

                rec = _parse_block(
                    block, record_id, ordem, i + 1, pdf_path.name, tipo_relatorio
                )
                if rec:
                    records.append(rec)
                else:
                    blocos_sem_registro += 1

    total_reportado = _extract_total_reportado(pages_text)
    total_analysis = _extract_all_totals(pages_text)

    meta = {
        "n_pages": n_pages,
        "pages_analisadas": len(pages_text),
        "total_blocos": total_blocos,
        "blocos_sem_registro": blocos_sem_registro,
        "total_reportado": total_reportado,
        "total_analysis": total_analysis,
    }
    return records, meta


# ---------------------------------------------------------------------------
# SQLite — DDL v3 (25 campos + 2 novos de georref)
# ---------------------------------------------------------------------------
_DDL = """
CREATE TABLE IF NOT EXISTS ri_matriculas_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_registro TEXT NOT NULL,
    matricula_numero INTEGER NOT NULL,
    nome_imovel_sanitizado TEXT,
    municipio TEXT,
    area_texto_original TEXT,
    area_valor_normalizado REAL,
    area_unidade TEXT,
    is_rural INTEGER NOT NULL DEFAULT 1,
    tem_georreferenciamento INTEGER NOT NULL DEFAULT 0,
    georreferenciamento_detectado_direto INTEGER NOT NULL DEFAULT 0,
    georreferenciamento_inferido_por_fonte INTEGER NOT NULL DEFAULT 0,
    georreferenciamento_valor TEXT,
    tem_incra INTEGER NOT NULL DEFAULT 0,
    incra_codigo TEXT,
    tem_nirf INTEGER NOT NULL DEFAULT 0,
    nirf_codigo TEXT,
    tem_reserva INTEGER,
    reserva_valor TEXT,
    fonte_relatorio TEXT NOT NULL,
    pagina_origem INTEGER,
    ordem_no_relatorio INTEGER,
    hash_bloco_origem TEXT NOT NULL,
    status_extracao TEXT NOT NULL DEFAULT 'ok',
    observacoes_tecnicas_sem_pii TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(fonte_relatorio, matricula_numero, hash_bloco_origem)
);
CREATE INDEX IF NOT EXISTS idx_mat_numero ON ri_matriculas_inventory(matricula_numero);
CREATE INDEX IF NOT EXISTS idx_mat_tipo ON ri_matriculas_inventory(tipo_registro);
CREATE INDEX IF NOT EXISTS idx_mat_georef ON ri_matriculas_inventory(tem_georreferenciamento);
CREATE INDEX IF NOT EXISTS idx_mat_georef_direto ON ri_matriculas_inventory(georreferenciamento_detectado_direto);
CREATE INDEX IF NOT EXISTS idx_mat_georef_fonte ON ri_matriculas_inventory(georreferenciamento_inferido_por_fonte);
CREATE INDEX IF NOT EXISTS idx_mat_incra ON ri_matriculas_inventory(tem_incra);
CREATE INDEX IF NOT EXISTS idx_mat_nirf ON ri_matriculas_inventory(tem_nirf);

CREATE TABLE IF NOT EXISTS ri_inventory_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    fonte_relatorio TEXT NOT NULL,
    input_filename TEXT NOT NULL,
    total_reportado INTEGER,
    total_blocos_detectados INTEGER,
    total_registros_sanitizados INTEGER,
    total_duplicidades INTEGER,
    total_rejeitados_pii INTEGER,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS ri_inventory_duplicates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    matricula_numero INTEGER NOT NULL,
    ocorrencias INTEGER NOT NULL,
    fontes TEXT,
    observacao TEXT
);
"""


def _migrate_db(conn: sqlite3.Connection) -> None:
    """
    Adiciona colunas novas v3 se não existirem (migração idempotente).
    Permite operar com DBs criados por versões anteriores do extrator.
    """
    cursor = conn.execute("PRAGMA table_info(ri_matriculas_inventory)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    new_cols = {
        "georreferenciamento_detectado_direto": "INTEGER NOT NULL DEFAULT 0",
        "georreferenciamento_inferido_por_fonte": "INTEGER NOT NULL DEFAULT 0",
    }

    for col, defn in new_cols.items():
        if col not in existing_cols:
            conn.execute(
                f"ALTER TABLE ri_matriculas_inventory ADD COLUMN {col} {defn}"
            )
            print(f"[MIGRAÇÃO] Coluna adicionada: {col}")
    conn.commit()


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_DDL)
    conn.commit()
    _migrate_db(conn)


def _write_db(
    records: list[dict[str, Any]],
    run_id: str,
    filename: str,
    total_reportado: int | None,
    total_blocos: int,
    duplicates: list[dict[str, Any]],
    started_at: str,
) -> Path:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db_path = DB_DIR / "ri_inventory.sqlite"
    conn = sqlite3.connect(str(db_path))
    now = datetime.now(timezone.utc).isoformat()

    try:
        _init_db(conn)
        inserted = 0
        skipped_dup = 0

        for r in records:
            try:
                conn.execute(
                    """
                    INSERT INTO ri_matriculas_inventory (
                        tipo_registro, matricula_numero, nome_imovel_sanitizado,
                        municipio, area_texto_original, area_valor_normalizado, area_unidade,
                        is_rural, tem_georreferenciamento,
                        georreferenciamento_detectado_direto,
                        georreferenciamento_inferido_por_fonte,
                        georreferenciamento_valor,
                        tem_incra, incra_codigo, tem_nirf, nirf_codigo,
                        tem_reserva, reserva_valor,
                        fonte_relatorio, pagina_origem, ordem_no_relatorio,
                        hash_bloco_origem, status_extracao, observacoes_tecnicas_sem_pii,
                        created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        r["tipo_registro"],
                        r["matricula_numero"],
                        r.get("nome_imovel_sanitizado") or None,
                        r.get("municipio"),
                        r.get("area_texto_original") or None,
                        r.get("area_valor_normalizado"),
                        r.get("area_unidade"),
                        1 if r.get("is_rural") else 0,
                        1 if r.get("tem_georreferenciamento") else 0,
                        1 if r.get("georreferenciamento_detectado_direto") else 0,
                        1 if r.get("georreferenciamento_inferido_por_fonte") else 0,
                        r.get("georreferenciamento_valor"),
                        1 if r.get("tem_incra") else 0,
                        r.get("incra_codigo"),
                        1 if r.get("tem_nirf") else 0,
                        r.get("nirf_codigo"),
                        (
                            None
                            if r.get("tem_reserva") is None
                            else (1 if r["tem_reserva"] else 0)
                        ),
                        r.get("reserva_valor"),
                        r["fonte_relatorio"],
                        r.get("pagina_origem"),
                        r.get("ordem_no_relatorio"),
                        r["hash_bloco_origem"],
                        r.get("status_extracao", "ok"),
                        r.get("observacoes_tecnicas_sem_pii") or None,
                        now,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped_dup += 1

        conn.commit()

        for dup in duplicates:
            conn.execute(
                """
                INSERT OR IGNORE INTO ri_inventory_duplicates
                (run_id, matricula_numero, ocorrencias, fontes, observacao)
                VALUES (?,?,?,?,?)
                """,
                (
                    dup["run_id"],
                    dup["matricula_numero"],
                    dup["ocorrencias"],
                    dup["fontes"],
                    dup["observacao"],
                ),
            )

        finished_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT OR REPLACE INTO ri_inventory_runs (
                run_id, fonte_relatorio, input_filename,
                total_reportado, total_blocos_detectados, total_registros_sanitizados,
                total_duplicidades, total_rejeitados_pii, status, started_at, finished_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id, filename, filename,
                total_reportado, total_blocos, len(records),
                len(duplicates), 0, "completed", started_at, finished_at,
            ),
        )
        conn.commit()

        print(
            f"[OK] SQLite: {db_path} "
            f"(inseridos: {inserted}, já existentes/ignorados: {skipped_dup})"
        )
    finally:
        conn.close()

    return db_path


# ---------------------------------------------------------------------------
# Validação anti-PII da saída
# ---------------------------------------------------------------------------
def _validate_sanitized(records: list[dict[str, Any]]) -> None:
    """
    Verifica se qualquer campo da saída contém padrão de CPF ou CNPJ.
    Se encontrar: aborta sem salvar e exibe mensagem genérica.
    Nunca imprime o conteúdo sensível.
    """
    proibidos = {
        "nome", "cpf", "cnpj", "rg", "nome_proprietario", "nome_conjuge",
        "nome_transmitente", "nome_adquirente", "documento_identidade", "endereco_pessoal",
    }
    campos_texto = [
        "municipio", "nome_imovel_sanitizado", "area_texto_original",
        "reserva_valor", "observacoes_tecnicas_sem_pii",
    ]

    for rec in records:
        for campo in proibidos:
            if campo in rec:
                print(
                    "PII detectada na saída sanitizada — extração bloqueada",
                    file=sys.stderr,
                )
                sys.exit(1)

        for campo in campos_texto:
            val = str(rec.get(campo, "") or "")
            if _CPF_RE.search(val) or _CNPJ_RE.search(val):
                print(
                    "PII detectada na saída sanitizada — extração bloqueada",
                    file=sys.stderr,
                )
                sys.exit(1)
            if campo == "observacoes_tecnicas_sem_pii" and _NOME_CAPS.search(val):
                print(
                    "PII detectada na saída sanitizada — extração bloqueada",
                    file=sys.stderr,
                )
                sys.exit(1)

        num = rec.get("matricula_numero")
        if num is not None and not str(num).isdigit():
            print(
                "PII detectada na saída sanitizada — extração bloqueada",
                file=sys.stderr,
            )
            sys.exit(1)

    print(
        f"[OK] Validação anti-PII: {len(records)} registros verificados — sem PII detectada."
    )


# ---------------------------------------------------------------------------
# Varredura de arquivos gerados
# ---------------------------------------------------------------------------
_DOC_REF_WHITELIST = re.compile(
    r"PROAD\s+n[oº°]?\s*[\d./\-]+"
    r"|CNJ\s+n[oº°]?\s*[\d./\-]+"
    r"|Prov\w*\.?\s*[\d./\-]+"
    r"|art\.\s*\d+"
    r"|Arts\.\s*\d+"
    r"|Art\.\s*\d+"
    r"|§\s*\d+"
    r"|\brun_id\b"
    r"|\bH-[0-9a-f]{6}\b",  # hash prefixado — seguro
    re.I,
)


def _scan_output_files() -> bool:
    """
    Varre CSV/JSON/MD gerados em busca de PII.
    CSV/JSON: campo a campo, excluindo campos de código técnico.
    MD: linha por linha, com whitelist de referências normativas.
    """
    pii_found = False

    for d in [SANITIZED_DIR, REPORTS_DIR, DB_DIR]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*")):
            if not f.is_file():
                continue
            ext = f.suffix.lower()

            if ext == ".csv":
                with f.open(encoding="utf-8", errors="replace") as fh:
                    for row in csv.DictReader(fh):
                        for campo, val in row.items():
                            if campo in _CAMPOS_CODIGOS_TECNICOS:
                                continue
                            s = str(val)
                            if _CPF_RE.search(s) or _CNPJ_RE.search(s):
                                print(
                                    f"PII detectada em {f.name} — saída bloqueada",
                                    file=sys.stderr,
                                )
                                pii_found = True
                                break
                        if pii_found:
                            break

            elif ext == ".json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                except Exception:
                    continue
                if isinstance(data, list):
                    for rec in data:
                        if not isinstance(rec, dict):
                            continue
                        for campo, val in rec.items():
                            if campo in _CAMPOS_CODIGOS_TECNICOS:
                                continue
                            s = str(val)
                            if _CPF_RE.search(s) or _CNPJ_RE.search(s):
                                print(
                                    f"PII detectada em {f.name} — saída bloqueada",
                                    file=sys.stderr,
                                )
                                pii_found = True
                                break
                        if pii_found:
                            break

            elif ext == ".md":
                for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                    linha_limpa = _DOC_REF_WHITELIST.sub("REF", line)
                    if _CPF_RE.search(linha_limpa) or _CNPJ_RE.search(linha_limpa):
                        print(
                            f"PII detectada em {f.name} — saída bloqueada",
                            file=sys.stderr,
                        )
                        pii_found = True
                        break

            if pii_found:
                break
        if pii_found:
            break

    if not pii_found:
        print("[OK] Varredura de arquivos gerados: sem PII detectada. Resultado: LIMPO")
    return not pii_found


# ---------------------------------------------------------------------------
# Salvamento CSV/JSON
# ---------------------------------------------------------------------------
def _save_sanitized(
    records: list[dict[str, Any]], suffix: str = ""
) -> tuple[Path, Path]:
    SANITIZED_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"ri_rural_inventory{suffix}"
    csv_path = SANITIZED_DIR / f"{stem}_sanitized.csv"
    json_path = SANITIZED_DIR / f"{stem}_sanitized.json"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(f"[OK] CSV: {csv_path}")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)
    print(f"[OK] JSON: {json_path}")

    return csv_path, json_path


# ---------------------------------------------------------------------------
# Relatório agregado
# ---------------------------------------------------------------------------
def _generate_report(
    records: list[dict[str, Any]],
    fonte: str,
    total_reportado: int | None,
    total_blocos: int,
    duplicates: list[dict[str, Any]],
    run_id: str,
    total_analysis: dict[str, Any] | None = None,
) -> str:
    total = len(records)
    if total == 0:
        return "# Relatório — Nenhum registro extraído.\n"

    numeros = [r["matricula_numero"] for r in records]
    numeros_unicos = set(numeros)
    total_unicos = len(numeros_unicos)
    menor = min(numeros_unicos) if numeros_unicos else None
    maior = max(numeros_unicos) if numeros_unicos else None

    total_M = sum(1 for r in records if r["tipo_registro"] == "M")
    total_T = sum(1 for r in records if r["tipo_registro"] == "T")

    # Georreferenciamento: separa direto / inferido / total
    total_georref_direto = sum(
        1 for r in records if r.get("georreferenciamento_detectado_direto")
    )
    total_georref_inferido = sum(
        1 for r in records if r.get("georreferenciamento_inferido_por_fonte")
    )
    total_georref = sum(1 for r in records if r.get("tem_georreferenciamento"))
    total_incra = sum(1 for r in records if r.get("tem_incra"))
    total_incra_sem_georref = sum(
        1 for r in records
        if r.get("tem_incra") and not r.get("georreferenciamento_detectado_direto")
        and not r.get("georreferenciamento_inferido_por_fonte")
    )

    # NIRF: válido vs zerado vs ausente
    total_nirf_valido = sum(1 for r in records if r.get("tem_nirf"))
    total_nirf_zerado = sum(
        1 for r in records
        if "nirf_zerado_ignorado" in (r.get("observacoes_tecnicas_sem_pii") or "")
    )
    total_nirf_ambiguo = sum(
        1 for r in records
        if "nirf_ambiguo" in (r.get("observacoes_tecnicas_sem_pii") or "")
    )

    total_reserva_sim = sum(1 for r in records if r.get("reserva_valor") == "Sim")
    total_reserva_nao = sum(1 for r in records if r.get("reserva_valor") == "Não")
    total_com_area = sum(1 for r in records if r.get("area_valor_normalizado") is not None)
    total_sem_area = total - total_com_area
    total_needs_review = sum(
        1 for r in records if r.get("status_extracao") == "needs_review"
    )
    total_area_ambigua = sum(
        1 for r in records if r.get("status_extracao") == "area_ambigua"
    )

    # Distribuição por município
    municipios: dict[str, int] = {}
    for r in records:
        mun = r.get("municipio") or "Não identificado"
        municipios[mun] = municipios.get(mun, 0) + 1
    mun_table = "\n".join(
        f"| {mun} | {qtd} |"
        for mun, qtd in sorted(municipios.items(), key=lambda x: -x[1])
    )

    # Análise de totais detectados no PDF
    totais_str = "Não analisado."
    if total_analysis:
        linhas = []
        for val_str, info in sorted(
            total_analysis.items(), key=lambda x: -x[1]["ocorrencias"]
        ):
            linhas.append(
                f"| {info['valor']} | {info['ocorrencias']} | {info['classificacao']} |"
            )
        if linhas:
            totais_str = (
                "| Valor | Ocorrências | Classificação |\n|---|---|---|\n"
                + "\n".join(linhas)
            )

    # Alertas de qualidade
    alertas: list[str] = []
    tr_str = str(total_reportado) if total_reportado is not None else "não detectado"
    if total_reportado is not None:
        if total > total_reportado:
            alertas.append(
                f"ALERTA: total extraído ({total}) > total reportado detectado ({total_reportado})"
            )
        elif total < total_reportado:
            alertas.append(
                f"ALERTA: total extraído ({total}) < total reportado detectado ({total_reportado})"
            )
        # Verificar se o total reportado parece ser subtotal
        if total_analysis:
            for val_str, info in total_analysis.items():
                if info["valor"] == total_reportado and info["classificacao"] == "subtotal_repetido":
                    alertas.append(
                        f"AVISO: 'Total: {total_reportado}' aparece {info['ocorrencias']} vezes "
                        f"— classificado como subtotal repetido, não total global"
                    )
    else:
        alertas.append(
            "AVISO: padrão 'Total: N' não encontrado — controle de qualidade parcial"
        )

    if total_unicos > _TOTAL_GERAL_SERVENTIA:
        alertas.append(
            f"ALERTA CRÍTICO: {total_unicos} matrículas únicas > {_TOTAL_GERAL_SERVENTIA} "
            f"(total geral da serventia) — reconciliar com equipe do RI"
        )
    if len(duplicates) > 0:
        alertas.append(f"ALERTA: {len(duplicates)} duplicidades detectadas neste relatório")
    if total_needs_review > 0:
        alertas.append(
            f"AVISO: {total_needs_review} registros com nome ambíguo marcados para revisão"
        )
    if total_area_ambigua > 0:
        alertas.append(
            f"AVISO: {total_area_ambigua} registros com área ambígua (verificar formatação)"
        )
    if total_incra_sem_georref > 0:
        alertas.append(
            f"AVISO: {total_incra_sem_georref} registros têm INCRA mas sem Georef. explícito"
        )
    if total_nirf_zerado > 0:
        alertas.append(
            f"AVISO: {total_nirf_zerado} registros com NIRF composto somente por zeros — ignorado"
        )

    alertas_str = "\n".join(f"- {a}" for a in alertas)

    # Tabela de revisão manual (apenas número e motivo técnico — SEM PII)
    needs_review_rows = [
        r for r in records if r.get("status_extracao") in ("needs_review", "area_ambigua")
    ]
    needs_review_table = ""
    if needs_review_rows:
        rows_md = "\n".join(
            f"| {r['matricula_numero']} | {r.get('status_extracao', '')} | "
            f"{r.get('observacoes_tecnicas_sem_pii', '')} |"
            for r in needs_review_rows[:50]
        )
        needs_review_table = (
            "\n| Matrícula | Status | Motivo técnico |\n|---|---|---|\n" + rows_md
        )
        if len(needs_review_rows) > 50:
            needs_review_table += f"\n... e mais {len(needs_review_rows) - 50} registros."

    # Duplicidades (apenas número)
    dup_table = ""
    if duplicates:
        dup_rows = "\n".join(
            f"| {d['matricula_numero']} | {d['ocorrencias']} | {d.get('fontes', '')} |"
            for d in duplicates[:30]
        )
        dup_table = "\n| Matrícula | Ocorrências | Fontes |\n|---|---|---|\n" + dup_rows

    menor_str = str(menor) if menor is not None else "—"
    maior_str = str(maior) if maior is not None else "—"
    pct_georref = (total_georref / total * 100) if total else 0
    pct_incra = (total_incra / total * 100) if total else 0

    return f"""# Relatório Técnico — Inventário de Matrículas Rurais v3
## Cartório Costa Teixeira — Terezópolis de Goiás

**Fonte analisada:** {fonte}
**Run ID:** {run_id}
**Versão do parser:** v3 (georref semântica corrigida, NIRF zerado normalizado)
**Classificação:** USO INTERNO — NÃO VERSIONAR
**Gerado por:** scripts/local_tools/extract_ri_rural_inventory.py

---

## 1. Resumo executivo

| Indicador | Valor |
|---|---|
| Total reportado (primeiro match no PDF) | {tr_str} |
| Total de blocos detectados | {total_blocos} |
| Total de registros extraídos | {total} |
| Total de matrículas únicas | {total_unicos} |
| Total de duplicidades | {len(duplicates)} |
| Menor número de matrícula | {menor_str} |
| Maior número de matrícula | {maior_str} |

---

## 2. Tipos de registro

| Tipo | Quantidade |
|---|---|
| Matrículas (M) | {total_M} |
| Transcrições (T) | {total_T} |

---

## 3. Georreferenciamento — separação semântica (v3)

| Indicador | Quantidade | % |
|---|---|---|
| Georref. detectado direto (Sim explícito) | {total_georref_direto} | {total_georref_direto/total*100:.1f}% |
| Georref. inferido por fonte (relatório georref) | {total_georref_inferido} | {total_georref_inferido/total*100:.1f}% |
| Total com georreferenciamento (direto+inferido) | {total_georref} | {pct_georref:.1f}% |
| Sem georreferenciamento | {total - total_georref} | {100-pct_georref:.1f}% |
| Com certificação INCRA/SIGEF | {total_incra} | {pct_incra:.1f}% |
| INCRA sem Georef. explícito | {total_incra_sem_georref} | |
| Sem certificação INCRA | {total - total_incra} | {100-pct_incra:.1f}% |

---

## 4. NIRF — normalização (v3)

| Indicador | Quantidade |
|---|---|
| NIRF válido detectado | {total_nirf_valido} |
| NIRF ausente | {total - total_nirf_valido - total_nirf_zerado - total_nirf_ambiguo} |
| NIRF zerado/placeholder ignorado | {total_nirf_zerado} |
| NIRF ambíguo | {total_nirf_ambiguo} |

---

## 5. Reserva legal

| Valor | Quantidade |
|---|---|
| Reserva Sim | {total_reserva_sim} |
| Reserva Não | {total_reserva_nao} |
| Não informado / rótulo ausente | {total - total_reserva_sim - total_reserva_nao} |

---

## 6. Área

| Indicador | Quantidade |
|---|---|
| Com área extraída | {total_com_area} |
| Sem área | {total_sem_area} |

---

## 7. Distribuição por município

| Município | Quantidade |
|---|---|
{mun_table}

---

## 8. Análise de totais detectados no PDF

{totais_str}

---

## 9. Alertas de qualidade

{alertas_str}

---

## 10. Registros para revisão manual{needs_review_table}

---

## 11. Duplicidades detectadas{dup_table if dup_table else chr(10) + "Nenhuma duplicidade detectada."}

---

## 12. Confirmação de proteção de dados

- Nenhum nome de proprietário foi salvo ou impresso.
- Nenhum CPF, CNPJ ou RG foi salvo ou impresso.
- Todas as linhas de PII foram descartadas silenciosamente.
- Os PDFs brutos permanecem em `_local_data/ri_inventory/raw/`.
- A base sanitizada está em `_local_data/ri_inventory/sanitized/`.

---

## 13. Como usar no Relatório Diagnóstico v2.0

### Seção 4 — IND-02 (Matrículas analisadas)
> Total de matrículas da serventia: **{_TOTAL_GERAL_SERVENTIA}** (dado institucional)
> Matrículas rurais identificadas por extração: **{total_unicos}** (sujeito a validação)

### Seção 5 — IND-05 (Imóveis georreferenciados)
> Imóveis com georref. detectado diretamente (Sim explícito): **{total_georref_direto}**
> Imóveis no relatório georref (inferido por fonte): **{total_georref_inferido}**
> Com certificação INCRA/SIGEF: **{total_incra}**

### Seção 10 — SIGEF/INCRA
> Imóveis com INCRA identificados: **{total_incra}**
> Desses, com INCRA mas sem Georef. explícito: **{total_incra_sem_georref}**
> Recomendação: cruzar com consulta direta no SIGEF para confirmar.

### Seção 12 — Diagnóstico do legado
> Imóveis sem georreferenciamento: **{total - total_georref}** ({100-pct_georref:.1f}%)
> Base para o plano de saneamento progressivo (48 meses até 01/09/2029).

---

*Relatório gerado automaticamente — uso restrito à equipe técnica da serventia.*
"""


# ---------------------------------------------------------------------------
# Consolidação (mantido para compatibilidade)
# ---------------------------------------------------------------------------
def _consolidate() -> None:
    """Lê todos os CSVs parciais de sanitized/ e gera base consolidada."""
    csvs = sorted(
        f for f in SANITIZED_DIR.glob("ri_rural_inventory_*_sanitized.csv")
        if "consolidado" not in f.name
    )
    if not csvs:
        print("[AVISO] Nenhum arquivo parcial encontrado para consolidar.")
        return

    all_records: list[dict[str, Any]] = []
    fontes = []
    for c in csvs:
        with c.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            all_records.extend(rows)
            fontes.append(c.name)
        print(f"[INFO] Lido: {c.name} ({len(rows)} registros)")

    for i, r in enumerate(all_records, 1):
        r["record_id"] = i

    _validate_sanitized(all_records)
    csv_path, json_path = _save_sanitized(all_records, suffix="_consolidado")
    run_id = str(uuid.uuid4())[:8]
    dups = _detect_duplicates(all_records, run_id)
    report = _generate_report(
        all_records, ", ".join(fontes), None, len(all_records), dups, run_id
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "ri_rural_inventory_summary.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"[OK] Relatório: {report_path}")
    print(f"\n[CONSOLIDADO] {len(all_records)} registros totais.")


# ---------------------------------------------------------------------------
# Impressão do dry-run (métricas seguras apenas)
# ---------------------------------------------------------------------------
def _print_dry_run(
    records: list[dict[str, Any]],
    meta: dict[str, Any],
    pdf_name: str,
    sample_pages: int | None,
) -> None:
    n_pages = meta["n_pages"]
    pages_analisadas = meta["pages_analisadas"]
    total_blocos = meta["total_blocos"]
    total_reportado = meta["total_reportado"]
    total_analysis = meta.get("total_analysis", {})

    com_area = sum(1 for r in records if r.get("area_valor_normalizado") is not None)
    com_georref_direto = sum(
        1 for r in records if r.get("georreferenciamento_detectado_direto")
    )
    com_georref_inferido = sum(
        1 for r in records if r.get("georreferenciamento_inferido_por_fonte")
    )
    com_georref_total = sum(1 for r in records if r.get("tem_georreferenciamento"))
    com_incra = sum(1 for r in records if r.get("tem_incra"))
    incra_sem_georref = sum(
        1 for r in records
        if r.get("tem_incra")
        and not r.get("georreferenciamento_detectado_direto")
        and not r.get("georreferenciamento_inferido_por_fonte")
    )
    com_nirf_valido = sum(1 for r in records if r.get("tem_nirf"))
    nirf_zerado = sum(
        1 for r in records
        if "nirf_zerado_ignorado" in (r.get("observacoes_tecnicas_sem_pii") or "")
    )
    com_reserva_sim = sum(1 for r in records if r.get("reserva_valor") == "Sim")
    com_reserva_nao = sum(1 for r in records if r.get("reserva_valor") == "Não")
    needs_review = sum(1 for r in records if r.get("status_extracao") == "needs_review")
    duplicates = _detect_duplicates(records, "dry-run")
    numeros_unicos = len(set(r["matricula_numero"] for r in records))
    tipos: dict[str, int] = {}
    for r in records:
        tipos[r["tipo_registro"]] = tipos.get(r["tipo_registro"], 0) + 1

    print(f"\n[DRY-RUN] Arquivo: {pdf_name}")
    print(f"  Páginas analisadas:                 {pages_analisadas} (de {n_pages} total)")
    print(f"  Blocos candidatos a registro:       {total_blocos}")
    print(f"  Registros sanitizados:              {len(records)}")
    print(f"  Matrículas únicas:                  {numeros_unicos}")
    print(f"  Duplicidades detectadas:            {len(duplicates)}")
    print(f"  Total reportado (1ª ocorrência):   "
          f"{total_reportado if total_reportado is not None else 'não detectado'}")

    if total_analysis:
        subtotais = [
            v for v in total_analysis.values()
            if v["classificacao"] == "subtotal_repetido"
        ]
        if subtotais:
            for s in subtotais:
                print(
                    f"  !! Subtotal repetido detectado:     "
                    f"'Total: {s['valor']}' aparece {s['ocorrencias']}x — NÃO é total global"
                )

    print("\n  Campos detectados:")
    print(f"    tipos (M/T):                      {tipos}")
    print(f"    com área:                         {com_area}/{len(records)}")
    print(f"    georref. direto (Sim explícito):  {com_georref_direto}/{len(records)}")
    print(f"    georref. inferido por fonte:      {com_georref_inferido}/{len(records)}")
    print(f"    georref. total:                   {com_georref_total}/{len(records)}")
    print(f"    com INCRA:                        {com_incra}/{len(records)}")
    print(f"    INCRA sem Georef. explícito:      {incra_sem_georref}/{len(records)}")
    print(f"    NIRF válido:                      {com_nirf_valido}/{len(records)}")
    print(f"    NIRF zerado ignorado:             {nirf_zerado}/{len(records)}")
    print(f"    Reserva Sim:                      {com_reserva_sim}/{len(records)}")
    print(f"    Reserva Não:                      {com_reserva_nao}/{len(records)}")
    print(f"    needs_review:                     {needs_review}")
    print("\n  PII descartada silenciosamente em todas as linhas processadas.")
    if sample_pages:
        projecao = (
            int(len(records) / pages_analisadas * n_pages)
            if pages_analisadas
            else "—"
        )
        print(f"  Nota: dry-run parcial ({sample_pages} páginas de {n_pages}).")
        print(f"  Projeção total estimada:            ~{projecao} registros")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extrator sanitizado de matrículas rurais — Engegraph PDF → "
            "CSV/JSON/SQLite limpos (v3)"
        )
    )
    parser.add_argument("--input", help="Caminho para o PDF bruto")
    parser.add_argument(
        "--tipo",
        choices=["rural", "georref"],
        help="Tipo de relatório: 'rural' ou 'georref'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analisar sem salvar — exibe métricas seguras",
    )
    parser.add_argument(
        "--sample-pages",
        type=int,
        metavar="N",
        help="Analisar apenas as N primeiras páginas",
    )
    parser.add_argument(
        "--write-sanitized",
        action="store_true",
        help="Salvar CSV e JSON sanitizados",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Salvar no banco SQLite local (_local_data/ri_inventory/db/)",
    )
    parser.add_argument(
        "--consolidate",
        action="store_true",
        help="Consolidar arquivos parciais em sanitized/ em base final",
    )
    args = parser.parse_args()

    if args.consolidate:
        _consolidate()
        return

    if not args.input or not args.tipo:
        parser.print_help()
        sys.exit(1)

    pdf_path = Path(args.input).resolve()
    if not pdf_path.exists():
        print(f"[ERRO] Arquivo não encontrado: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        print("[ERRO] Apenas PDFs suportados.", file=sys.stderr)
        sys.exit(1)

    try:
        pdf_path.relative_to(LOCAL_DATA)
    except ValueError:
        print(
            "[ERRO] O PDF deve estar em _local_data/ para não ser versionado.",
            file=sys.stderr,
        )
        sys.exit(1)

    modo = "DRY-RUN" if args.dry_run else "EXTRAÇÃO"
    print(
        f"[INFO] {modo}: {pdf_path.name} | tipo: {args.tipo}"
        + (f" | {args.sample_pages} páginas" if args.sample_pages else "")
    )

    started_at = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())[:8]

    records, meta = _extract_from_pdf(
        pdf_path,
        tipo_relatorio=args.tipo,
        sample_pages=args.sample_pages,
    )

    if args.dry_run:
        _print_dry_run(records, meta, pdf_path.name, args.sample_pages)
        print("[DRY-RUN] Nenhum arquivo salvo.")
        return

    if not records:
        print("[AVISO] Nenhum registro extraído. Verifique o layout do PDF.")
        sys.exit(0)

    print(f"[INFO] {len(records)} registros — validando anti-PII...")
    _validate_sanitized(records)

    duplicates = _detect_duplicates(records, run_id)
    if duplicates:
        print(
            f"[AVISO] {len(duplicates)} duplicidades detectadas "
            f"(matrículas: {[d['matricula_numero'] for d in duplicates[:10]]})"
        )

    suffix = f"_{args.tipo}"

    if args.write_sanitized:
        _save_sanitized(records, suffix=suffix)

    if args.write_db:
        _write_db(
            records,
            run_id=run_id,
            filename=pdf_path.name,
            total_reportado=meta["total_reportado"],
            total_blocos=meta["total_blocos"],
            duplicates=duplicates,
            started_at=started_at,
        )

    if not args.write_sanitized and not args.write_db:
        print(
            "[AVISO] Nenhuma flag de escrita especificada. "
            "Use --write-sanitized e/ou --write-db para salvar."
        )
    else:
        report = _generate_report(
            records,
            fonte=pdf_path.name,
            total_reportado=meta["total_reportado"],
            total_blocos=meta["total_blocos"],
            duplicates=duplicates,
            run_id=run_id,
            total_analysis=meta.get("total_analysis"),
        )
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / f"ri_{args.tipo}_summary.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"[OK] Relatório: {report_path}")

    print(
        f"\n[CONCLUÍDO] run_id={run_id} | "
        f"{len(records)} registros sanitizados | "
        f"duplicidades: {len(duplicates)}"
    )


if __name__ == "__main__":
    main()
