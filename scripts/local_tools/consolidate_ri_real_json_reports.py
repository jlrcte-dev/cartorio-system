"""
Consolidador de relatórios RI Real JSON — Cartório System

Sprint: RI-REAL-JSON-2 (consolidação diretoria)

PROTEÇÃO DE DADOS (LGPD):
- Nenhum dado pessoal (CPF, CNPJ, RG, CI, nome de proprietário) é incluído.
- Varredura anti-PII é executada nos arquivos gerados antes de salvar.
- Apenas campos técnicos sanitizados são propagados.

USO:
    python scripts/local_tools/consolidate_ri_real_json_reports.py

SAÍDA:
    _local_data/ri_inventory/reports/real_json/consolidated/
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "_local_data/ri_inventory/reports/real_json/manual_review"
OUT_DIR = REPO_ROOT / "_local_data/ri_inventory/reports/real_json/consolidated"

CSV_SOURCES = [
    "ri_real_json_needs_review.csv",
    "ri_real_json_rural_records.csv",
    "ri_real_json_urban_records.csv",
    "ri_real_json_georeferenced_rural.csv",
    "ri_real_json_rural_missing_car.csv",
    "ri_real_json_rural_missing_ccir.csv",
    "ri_real_json_rural_missing_nirf.csv",
    "ri_real_json_urban_with_rural_fields.csv",
]

# ---------------------------------------------------------------------------
# Anti-PII
# ---------------------------------------------------------------------------

# Padrões para dados CSV — inclui palavras-chave de campo PII
_PII_PATTERNS_DATA = [
    (re.compile(r"\b\d{3}[\.\-]?\d{3}[\.\-]?\d{3}[\.\-]?\d{2}\b"), "CPF"),
    (re.compile(r"\b\d{2}[\.\-]?\d{3}[\.\-]?\d{3}[\/]?\d{4}[\-]?\d{2}\b"), "CNPJ"),
    (re.compile(r"\b[Cc][Oo][Nn][Tt][Rr][Ii][Bb][Uu][Ii][Nn][Tt][Ee]\b"), "CONTRIBUINTE"),
    (re.compile(r"\b[Pp][Rr][Oo][Pp][Rr][Ii][Ee][Tt][AÁaá][Rr][Ii][Oo]\b"), "PROPRIETARIO"),
    (re.compile(r"\b[Aa][Dd][Qq][Uu][Ii][Rr][Ee][Nn][Tt][Ee]\b"), "ADQUIRENTE"),
    (re.compile(r"\b[Tt][Rr][Aa][Nn][Ss][Mm][Ii][Tt][Ee][Nn][Tt][Ee]\b"), "TRANSMITENTE"),
    (re.compile(r"\bnome_proprietario\b", re.I), "nome_proprietario"),
]

# Padrões para documentos Markdown — apenas valores numéricos de PII
# (termos como "proprietário", "RG", "CI" são legítimos em texto explicativo)
_PII_PATTERNS_DOC = [
    (re.compile(r"\b\d{3}[\.\-]?\d{3}[\.\-]?\d{3}[\.\-]?\d{2}\b"), "CPF"),
    (re.compile(r"\b\d{2}[\.\-]?\d{3}[\.\-]?\d{3}[\/]?\d{4}[\-]?\d{2}\b"), "CNPJ"),
    (re.compile(r"\b[Cc][Oo][Nn][Tt][Rr][Ii][Bb][Uu][Ii][Nn][Tt][Ee]\s*[:=]\s*\S"), "CONTRIBUINTE_VALOR"),
]


def check_pii(text: str, doc_mode: bool = False) -> list[tuple[str, int]]:
    """Retorna lista de (tipo_pii, count) se encontrar padrões PII.

    doc_mode=True usa padrões menos rígidos, adequados para Markdown explicativo.
    """
    patterns = _PII_PATTERNS_DOC if doc_mode else _PII_PATTERNS_DATA
    found: list[tuple[str, int]] = []
    for pattern, label in patterns:
        matches = pattern.findall(text)
        if matches:
            found.append((label, len(matches)))
    return found


def assert_no_pii(content: str, filename: str, doc_mode: bool = False) -> None:
    hits = check_pii(content, doc_mode=doc_mode)
    if hits:
        summary = "; ".join(f"{label}={count}" for label, count in hits)
        raise ValueError(
            f"[BLOQUEADO] PII detectada em '{filename}': {summary}. "
            "Arquivo não será gravado."
        )


# ---------------------------------------------------------------------------
# Tipos de pendência e prioridade
# ---------------------------------------------------------------------------

TIPO_PENDENCIA = {
    "RURAL_SEM_CAR": "Rural sem CAR",
    "RURAL_SEM_NIRF": "Rural sem NIRF",
    "RURAL_SEM_CCIR": "Rural sem CCIR",
    "RURAL_GEOREFERENCIADO": "Rural com georreferenciamento",
    "NEEDS_REVIEW": "Needs review",
    "URBANO_COM_CAMPOS_RURAIS": "Urbano com campos rurais",
    "RURAL_COMPLETO": "Rural completo",
    "RURAL_SEM_GEOREFERENCIAMENTO": "Rural sem georreferenciamento",
    "DADO_INCONSISTENTE": "Dado inconsistente",
    "URBANO_SEM_PENDENCIA": "Urbano sem pendência",
}

ACOES = {
    "RURAL_SEM_CAR": "Conferir no sistema se o imóvel é rural e atualizar CAR, se disponível.",
    "RURAL_SEM_NIRF": "Conferir NIRF no sistema; se estiver zerado ou vazio, validar se há dado oficial.",
    "RURAL_SEM_CCIR": "Conferir CCIR/INCRA no sistema.",
    "RURAL_GEOREFERENCIADO": "Validar se NUMERO_INCRA/SIGEF indica georreferenciamento ativo.",
    "NEEDS_REVIEW": "Conferir natureza do imóvel e corrigir cadastro se necessário.",
    "URBANO_COM_CAMPOS_RURAIS": "Verificar se imóvel urbano possui campos rurais preenchidos indevidamente.",
    "RURAL_COMPLETO": "Registro informativo; sem ação imediata.",
    "RURAL_SEM_GEOREFERENCIAMENTO": "Conferir NUMERO_INCRA/SIGEF no sistema.",
    "DADO_INCONSISTENTE": "Confirmar natureza do imóvel e corrigir cadastro se necessário.",
    "URBANO_SEM_PENDENCIA": "Registro informativo; sem ação imediata.",
}


def prioridade(tipos: list[str]) -> str:
    alta = {"NEEDS_REVIEW", "URBANO_COM_CAMPOS_RURAIS", "RURAL_SEM_CCIR", "DADO_INCONSISTENTE"}
    media = {"RURAL_SEM_CAR", "RURAL_SEM_NIRF", "RURAL_SEM_GEOREFERENCIAMENTO", "RURAL_GEOREFERENCIADO"}
    baixa = {"RURAL_COMPLETO", "URBANO_SEM_PENDENCIA"}
    for t in tipos:
        if t in alta:
            return "ALTA"
    for t in tipos:
        if t in media:
            return "MEDIA"
    return "BAIXA"


# ---------------------------------------------------------------------------
# Leitura dos CSVs
# ---------------------------------------------------------------------------

@dataclass
class Registro:
    matricula_numero: str
    numero_registro: str
    natureza_imovel: str
    tem_car: str
    tem_nirf: str
    nirf_status: str
    tem_ccir: str
    tem_numero_incra: str
    tem_sigef: str
    possui_georreferenciamento: str
    georreferenciamento_criterio: str
    status_revisao_ri: str
    observacoes_tecnicas_sem_pii: str
    fontes: list[str] = field(default_factory=list)

    def is_true(self, campo: str) -> bool:
        val = getattr(self, campo, "").strip().lower()
        return val in ("true", "1", "yes", "sim")

    def classificar(self) -> list[str]:
        tipos: list[str] = []
        is_rural = self.natureza_imovel.strip().lower() == "rural"
        is_urban = self.natureza_imovel.strip().lower() == "urbano"

        if self.status_revisao_ri.strip().lower() == "needs_manual_review":
            tipos.append("NEEDS_REVIEW")

        if is_rural:
            car = self.is_true("tem_car")
            nirf = self.is_true("tem_nirf")
            ccir = self.is_true("tem_ccir")
            incra = self.is_true("tem_numero_incra")
            sigef = self.is_true("tem_sigef")

            if not car:
                tipos.append("RURAL_SEM_CAR")
            if not nirf:
                tipos.append("RURAL_SEM_NIRF")
            if not ccir:
                tipos.append("RURAL_SEM_CCIR")
            if incra or sigef:
                tipos.append("RURAL_GEOREFERENCIADO")
            else:
                tipos.append("RURAL_SEM_GEOREFERENCIAMENTO")

            if car and nirf and ccir:
                tipos.append("RURAL_COMPLETO")

        if is_urban:
            campos_rurais = (
                self.is_true("tem_car")
                or self.is_true("tem_ccir")
                or self.is_true("tem_numero_incra")
                or self.is_true("tem_sigef")
                or (self.is_true("tem_nirf") and self.nirf_status.strip().lower() not in ("ausente", ""))
            )
            obs = self.observacoes_tecnicas_sem_pii.strip().lower()
            if campos_rurais or "rural" in obs:
                tipos.append("URBANO_COM_CAMPOS_RURAIS")

        if not tipos:
            nat = self.natureza_imovel.strip().lower()
            if nat == "rural":
                tipos.append("RURAL_COMPLETO")
            else:
                tipos.append("URBANO_SEM_PENDENCIA")

        return tipos


def _bool_val(v: str) -> str:
    lv = v.strip().lower()
    if lv == "true":
        return "Sim"
    if lv == "false":
        return "Não"
    return v.strip() or "—"


def read_csv_source(path: Path) -> Iterator[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield row


def load_all_records() -> dict[str, Registro]:
    records: dict[str, Registro] = {}

    for fname in CSV_SOURCES:
        fpath = SOURCE_DIR / fname
        if not fpath.exists():
            print(f"  [AVISO] Arquivo não encontrado: {fpath}")
            continue

        for row in read_csv_source(fpath):
            key = row.get("matricula_numero", "").strip()
            if not key:
                continue

            # Verificação anti-PII na linha bruta
            linha_raw = ",".join(row.values())
            hits = check_pii(linha_raw)
            if hits:
                summary = "; ".join(f"{label}={count}" for label, count in hits)
                print(f"  [BLOQUEADO] PII em {fname} matrícula {key}: {summary} — linha ignorada")
                continue

            if key not in records:
                records[key] = Registro(
                    matricula_numero=key,
                    numero_registro=row.get("numero_registro", "").strip(),
                    natureza_imovel=row.get("natureza_imovel", "").strip(),
                    tem_car=row.get("tem_car", "").strip(),
                    tem_nirf=row.get("tem_nirf", "").strip(),
                    nirf_status=row.get("nirf_status", "").strip(),
                    tem_ccir=row.get("tem_ccir", "").strip(),
                    tem_numero_incra=row.get("tem_numero_incra", "").strip(),
                    tem_sigef=row.get("tem_sigef", "").strip(),
                    possui_georreferenciamento=row.get("possui_georreferenciamento", "").strip(),
                    georreferenciamento_criterio=row.get("georreferenciamento_criterio", "").strip(),
                    status_revisao_ri=row.get("status_revisao_ri", "").strip(),
                    observacoes_tecnicas_sem_pii=row.get("observacoes_tecnicas_sem_pii", "").strip(),
                    fontes=[fname],
                )
            else:
                rec = records[key]
                if fname not in rec.fontes:
                    rec.fontes.append(fname)
                # Atualizar campos se ausentes
                if not rec.status_revisao_ri and row.get("status_revisao_ri"):
                    rec.status_revisao_ri = row["status_revisao_ri"].strip()
                if not rec.observacoes_tecnicas_sem_pii and row.get("observacoes_tecnicas_sem_pii"):
                    rec.observacoes_tecnicas_sem_pii = row["observacoes_tecnicas_sem_pii"].strip()
                if not rec.georreferenciamento_criterio and row.get("georreferenciamento_criterio"):
                    rec.georreferenciamento_criterio = row["georreferenciamento_criterio"].strip()

    return records


# ---------------------------------------------------------------------------
# Geração do CSV operacional
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "matricula_numero",
    "numero_registro",
    "natureza_imovel",
    "tipo_pendencia",
    "prioridade_conferencia",
    "responsavel_conferencia",
    "acao_recomendada",
    "motivo_tecnico",
    "tem_car",
    "tem_nirf",
    "nirf_status",
    "tem_ccir",
    "tem_numero_incra",
    "tem_sigef",
    "possui_georreferenciamento",
    "georreferenciamento_criterio",
    "status_revisao_ri",
    "fonte_relatorio",
    "observacoes_para_colaborador",
    "resultado_conferencia",
    "observacao_conferencia",
    "data_conferencia",
]


def build_csv_rows(records: dict[str, Registro]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rec in sorted(records.values(), key=lambda r: int(r.matricula_numero) if r.matricula_numero.isdigit() else 0):
        tipos = rec.classificar()
        pri = prioridade(tipos)
        tipo_str = "; ".join(tipos)
        acoes_str = " | ".join(dict.fromkeys(ACOES.get(t, "") for t in tipos if ACOES.get(t)))
        obs_col = rec.observacoes_tecnicas_sem_pii or ""

        rows.append({
            "matricula_numero": rec.matricula_numero,
            "numero_registro": rec.numero_registro,
            "natureza_imovel": rec.natureza_imovel,
            "tipo_pendencia": tipo_str,
            "prioridade_conferencia": pri,
            "responsavel_conferencia": "",
            "acao_recomendada": acoes_str,
            "motivo_tecnico": obs_col,
            "tem_car": _bool_val(rec.tem_car),
            "tem_nirf": _bool_val(rec.tem_nirf),
            "nirf_status": rec.nirf_status or "—",
            "tem_ccir": _bool_val(rec.tem_ccir),
            "tem_numero_incra": _bool_val(rec.tem_numero_incra),
            "tem_sigef": _bool_val(rec.tem_sigef),
            "possui_georreferenciamento": _bool_val(rec.possui_georreferenciamento),
            "georreferenciamento_criterio": rec.georreferenciamento_criterio or "—",
            "status_revisao_ri": rec.status_revisao_ri or "—",
            "fonte_relatorio": "; ".join(rec.fontes),
            "observacoes_para_colaborador": obs_col,
            "resultado_conferencia": "",
            "observacao_conferencia": "",
            "data_conferencia": "",
        })
    return rows


def write_csv(rows: list[dict[str, str]], out_path: Path) -> None:
    content_lines: list[str] = [",".join(CSV_COLUMNS)]
    for row in rows:
        line = ",".join(f'"{row.get(c, "")}"' for c in CSV_COLUMNS)
        content_lines.append(line)
    content = "\n".join(content_lines) + "\n"
    assert_no_pii(content, out_path.name)
    out_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Estatísticas
# ---------------------------------------------------------------------------

@dataclass
class Stats:
    total: int = 0
    urbanos: int = 0
    rurais: int = 0
    rural_com_car: int = 0
    rural_sem_car: int = 0
    rural_com_nirf: int = 0
    rural_sem_nirf: int = 0
    rural_com_ccir: int = 0
    rural_sem_ccir: int = 0
    rural_com_geo: int = 0
    rural_sem_geo: int = 0
    needs_review: int = 0
    urbano_com_rurais: int = 0
    total_pendencias: int = 0
    por_tipo: dict[str, int] = field(default_factory=dict)


def calcular_stats(records: dict[str, Registro], rows: list[dict[str, str]]) -> Stats:
    s = Stats()
    s.total = len(records)

    for rec in records.values():
        nat = rec.natureza_imovel.strip().lower()
        if nat == "urbano":
            s.urbanos += 1
        elif nat == "rural":
            s.rurais += 1

        if nat == "rural":
            if rec.is_true("tem_car"):
                s.rural_com_car += 1
            else:
                s.rural_sem_car += 1
            if rec.is_true("tem_nirf"):
                s.rural_com_nirf += 1
            else:
                s.rural_sem_nirf += 1
            if rec.is_true("tem_ccir"):
                s.rural_com_ccir += 1
            else:
                s.rural_sem_ccir += 1
            if rec.is_true("tem_numero_incra") or rec.is_true("tem_sigef"):
                s.rural_com_geo += 1
            else:
                s.rural_sem_geo += 1

    for rec in records.values():
        tipos = rec.classificar()
        if "NEEDS_REVIEW" in tipos:
            s.needs_review += 1
        if "URBANO_COM_CAMPOS_RURAIS" in tipos:
            s.urbano_com_rurais += 1
        for t in tipos:
            s.por_tipo[t] = s.por_tipo.get(t, 0) + 1

    pendencias = {"RURAL_SEM_CAR", "RURAL_SEM_NIRF", "RURAL_SEM_CCIR", "NEEDS_REVIEW", "URBANO_COM_CAMPOS_RURAIS", "DADO_INCONSISTENTE"}
    s.total_pendencias = sum(1 for rec in records.values() if any(t in pendencias for t in rec.classificar()))
    return s


# ---------------------------------------------------------------------------
# Relatório executivo
# ---------------------------------------------------------------------------

def write_relatorio_executivo(stats: Stats, out_path: Path) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    arquivos_analisados = "\n".join(f"  - `{f}`" for f in CSV_SOURCES)

    pendencias_table_rows = []
    ordem_tipos = [
        "NEEDS_REVIEW",
        "URBANO_COM_CAMPOS_RURAIS",
        "RURAL_SEM_CCIR",
        "RURAL_SEM_NIRF",
        "RURAL_SEM_CAR",
        "RURAL_GEOREFERENCIADO",
        "RURAL_SEM_GEOREFERENCIAMENTO",
        "RURAL_COMPLETO",
        "DADO_INCONSISTENTE",
    ]
    prioridade_map = {
        "NEEDS_REVIEW": "ALTA",
        "URBANO_COM_CAMPOS_RURAIS": "ALTA",
        "RURAL_SEM_CCIR": "ALTA",
        "RURAL_SEM_NIRF": "MEDIA",
        "RURAL_SEM_CAR": "MEDIA",
        "RURAL_GEOREFERENCIADO": "MEDIA",
        "RURAL_SEM_GEOREFERENCIAMENTO": "MEDIA",
        "RURAL_COMPLETO": "BAIXA",
        "DADO_INCONSISTENTE": "ALTA",
    }
    for t in ordem_tipos:
        qt = stats.por_tipo.get(t, 0)
        if qt > 0:
            pendencias_table_rows.append(
                f"| {TIPO_PENDENCIA.get(t, t)} | {qt:,} | {prioridade_map.get(t, '—')} | {ACOES.get(t, '—')} |"
            )
    pendencias_table = "\n".join(pendencias_table_rows)

    md = f"""# Relatório Consolidado — Indicador Real da Serventia

> Gerado automaticamente em: {now}
> Classificação: **USO INTERNO — NÃO CONTÉM DADOS PESSOAIS**

---

## 1. Objetivo

Este relatório consolida a análise do JSON estruturado do Indicador Real da serventia, com o objetivo de orientar a revisão cadastral e a conferência das matrículas no sistema Engegraph/Indicador Real.

Os dados foram extraídos e sanitizados a partir do JSON exportado do sistema, sem inclusão de dados pessoais. O relatório serve como instrumento de planejamento operacional para a diretoria e como guia de trabalho para os colaboradores responsáveis pela conferência.

---

## 2. Fonte dos Dados

- **Origem:** JSON estruturado do Indicador Real (exportação local)
- **Data/hora da consolidação:** {now}
- **Arquivos CSV analisados:**
{arquivos_analisados}
- **Observação:** Todos os relatórios são derivados sanitizados. Nenhum dado pessoal (CPF, CNPJ, nome de proprietário, RG, CI) foi incluído nos arquivos gerados.

---

## 3. Sumário Executivo

| Indicador | Quantidade |
|---|---:|
| Total de matrículas analisadas | **{stats.total:,}** |
| Matrículas urbanas | {stats.urbanos:,} |
| Matrículas rurais | {stats.rurais:,} |
| Rurais com CAR | {stats.rural_com_car:,} |
| Rurais sem CAR | {stats.rural_sem_car:,} |
| Rurais com NIRF válido | {stats.rural_com_nirf:,} |
| Rurais sem NIRF | {stats.rural_sem_nirf:,} |
| Rurais com CCIR | {stats.rural_com_ccir:,} |
| Rurais sem CCIR | {stats.rural_sem_ccir:,} |
| Rurais com georreferenciamento (INCRA/SIGEF) | {stats.rural_com_geo:,} |
| Rurais sem georreferenciamento | {stats.rural_sem_geo:,} |
| Matrículas marcadas para revisão (needs_review) | {stats.needs_review:,} |
| Urbanos com campos rurais preenchidos | {stats.urbano_com_rurais:,} |
| **Total de pendências para conferência** | **{stats.total_pendencias:,}** |

---

## 4. Situação dos Imóveis Urbanos

- **Quantidade de urbanos:** {stats.urbanos:,}
- **Urbanos sem pendência:** {stats.urbanos - stats.urbano_com_rurais - stats.needs_review:,} (estimativa; pode haver sobreposição)
- **Urbanos com campos rurais preenchidos:** {stats.urbano_com_rurais:,}

**Recomendação:** Os imóveis urbanos com campos rurais preenchidos (CAR, CCIR, NUMERO_INCRA, SIGEF, NIRF) devem ser priorizados para conferência, pois indicam possível erro de cadastro ou inconsistência de natureza do imóvel.

---

## 5. Situação dos Imóveis Rurais

- **Quantidade de rurais:** {stats.rurais:,}
- **Com CAR:** {stats.rural_com_car:,} | **Sem CAR:** {stats.rural_sem_car:,}
- **Com NIRF válido:** {stats.rural_com_nirf:,} | **Sem NIRF:** {stats.rural_sem_nirf:,}
- **Com CCIR:** {stats.rural_com_ccir:,} | **Sem CCIR:** {stats.rural_sem_ccir:,}
- **Com NUMERO_INCRA ou SIGEF:** {stats.rural_com_geo:,}
- **Sem NUMERO_INCRA e sem SIGEF:** {stats.rural_sem_geo:,}

Os imóveis rurais sem CCIR representam prioridade ALTA de conferência, dado o caráter obrigatório desse documento para imóveis rurais.

---

## 6. Georreferenciamento

O critério técnico adotado para identificar indício de georreferenciamento é a presença de valor preenchido nos campos **NUMERO_INCRA** ou **SIGEF** no JSON exportado.

- **Importante:** A presença desses campos é tratada como *indício técnico*, não como confirmação de georreferenciamento registral oficialmente homologado.
- Recomenda-se conferência no sistema Engegraph antes de usar esse dado como conclusão operacional definitiva.
- Os dois campos são analisados separadamente para permitir granularidade na conferência.

---

## 7. Principais Pendências de Conferência

| Tipo de pendência | Quantidade | Prioridade | Ação recomendada |
|---|---:|---|---|
{pendencias_table}

---

## 8. Plano de Conferência pelos Colaboradores

A planilha CSV gerada (`ri_real_json_plano_conferencia_colaboradores.csv`) deve ser distribuída ou usada internamente pelos colaboradores responsáveis pela conferência.

**Fluxo sugerido:**

1. Abrir a matrícula indicada na planilha no sistema Engegraph/Indicador Real.
2. Confirmar a natureza do imóvel (urbano ou rural).
3. Conferir os campos indicados na coluna `tipo_pendencia`.
4. Atualizar o sistema se necessário ou registrar a divergência.
5. Preencher a coluna `resultado_conferencia` (OK / Corrigir cadastro / Dado não localizado / Exige validação do responsável).
6. Preencher `observacao_conferencia` com nota objetiva.
7. Registrar `data_conferencia`.
8. Retornar a planilha consolidada para revisão final.

---

## 9. Campos a Conferir no Sistema

### Imóveis rurais

| Campo | O que verificar |
|---|---|
| CAR | Número do Cadastro Ambiental Rural; se ausente, verificar disponibilidade |
| NIRF | Número do Imóvel na Receita Federal; validar se não está zerado/vazio |
| CCIR | Certificado de Cadastro de Imóvel Rural; obrigatório para rurais |
| NUMERO_INCRA | Indicativo de georreferenciamento; confirmar se é válido |
| SIGEF | Sistema de Gestão Fundiária; confirmar se está ativo |
| Denominação rural | Conferir nome do imóvel |
| Natureza do imóvel | Confirmar se está classificado como rural |

### Imóveis urbanos

| Campo | O que verificar |
|---|---|
| Natureza do imóvel | Confirmar se está classificado como urbano |
| Campos rurais | Verificar se CAR, CCIR, NIRF, NUMERO_INCRA ou SIGEF estão preenchidos indevidamente |
| Lote/quadra/logradouro | Conferir dados de localização urbana |
| Possível erro de cadastro | Registrar se a natureza parece incorreta |

---

## 10. Recomendações à Diretoria

1. **Autorizar conferência cadastral** por amostragem ou por tipo de pendência, priorizando needs_review e urbanos com campos rurais.
2. **Prioridade imediata:** matrículas marcadas como needs_review e imóveis urbanos com campos rurais preenchidos.
3. **Prioridade secundária:** rurais sem CCIR e rurais sem NIRF.
4. **Validar dados rurais críticos** (CAR, CCIR, NIRF) antes da elaboração do Relatório Diagnóstico final da serventia.
5. **Manter o JSON exportado** como fonte estruturada principal para análises futuras; os relatórios PDF anteriores devem ser usados apenas como apoio comparativo posterior.
6. **Registrar resultado da conferência** na planilha distribuída para fins de rastreabilidade.

---

## 11. Limitações

- Este relatório **não substitui a conferência registral** realizada no sistema.
- A classificação depende integralmente da **qualidade e completude do JSON exportado** do Indicador Real.
- Campos como NUMERO_INCRA e SIGEF indicam presença de informação técnica, mas precisam ser **confirmados operacionalmente** antes de qualquer uso conclusivo.
- **Nenhum dado pessoal** foi incluído nos arquivos gerados, em conformidade com a LGPD.
- A análise reflete o estado do JSON no momento da exportação; atualizações posteriores no sistema não são refletidas automaticamente.

---

## 12. Próximos Passos

1. Diretoria aprova o plano de conferência.
2. Colaboradores realizam validação no sistema Engegraph, usando a planilha CSV como guia.
3. Resultados são consolidados na planilha (colunas `resultado_conferencia`, `observacao_conferencia`, `data_conferencia`).
4. Cadastros inconsistentes são corrigidos no sistema.
5. Gerar relatório final revisado após conferência.
6. Opcionalmente, comparar os dados do JSON com os relatórios PDF anteriores para validação cruzada.

---

*Relatório gerado pelo Cartório System — uso interno. Não distribuir externamente.*
"""

    assert_no_pii(md, out_path.name, doc_mode=True)
    out_path.write_text(md, encoding="utf-8")


# ---------------------------------------------------------------------------
# Checklist operacional
# ---------------------------------------------------------------------------

def write_checklist(stats: Stats, out_path: Path) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    md = f"""# Checklist de Conferência — Indicador Real

> Gerado em: {now} | Uso interno dos colaboradores

---

## Para cada matrícula da planilha

- [ ] Abrir a matrícula no sistema (Engegraph / Indicador Real).
- [ ] Confirmar se o imóvel é **urbano** ou **rural**.

### Se rural

- [ ] Conferir **CAR** — está preenchido com número válido?
- [ ] Conferir **NIRF** — está preenchido? Não está zerado ou com placeholder?
- [ ] Conferir **CCIR** — está preenchido?
- [ ] Conferir **NUMERO_INCRA** — há número válido que indique georreferenciamento?
- [ ] Conferir **SIGEF** — há código SIGEF preenchido?
- [ ] Conferir **denominação rural** do imóvel.
- [ ] Confirmar se a natureza cadastrada está correta como **rural**.

### Se urbano

- [ ] Confirmar se a natureza cadastrada está correta como **urbano**.
- [ ] Verificar se há campos rurais preenchidos indevidamente (CAR, CCIR, NIRF, NUMERO_INCRA, SIGEF).
- [ ] Registrar se há inconsistência de cadastro.

---

## Registrar resultado

Preencher as colunas da planilha:

| Coluna | Valores possíveis |
|---|---|
| `resultado_conferencia` | OK / Corrigir cadastro / Dado não localizado / Exige validação do responsável / Outro |
| `observacao_conferencia` | Nota objetiva (ex.: "CCIR encontrado e atualizado", "imóvel parece ser rural") |
| `data_conferencia` | Data no formato AAAA-MM-DD |
| `responsavel_conferencia` | Nome ou iniciais do colaborador |

---

## Prioridade de conferência

1. **ALTA — Needs review** ({stats.needs_review:,} matrículas)
   - Imóveis com indício técnico de inconsistência ou sinal misto urbano/rural.
2. **ALTA — Urbano com campos rurais** ({stats.urbano_com_rurais:,} matrículas)
   - Imóvel cadastrado como urbano, mas com CAR, CCIR, INCRA ou SIGEF preenchidos.
3. **ALTA — Rural sem CCIR** ({stats.rural_sem_ccir:,} matrículas)
   - CCIR é obrigatório para rurais; ausência indica dado incompleto.
4. **MEDIA — Rural sem NIRF** ({stats.rural_sem_nirf:,} matrículas)
   - NIRF ausente ou zerado; verificar junto à Receita Federal.
5. **MEDIA — Rural sem CAR** ({stats.rural_sem_car:,} matrículas)
   - CAR não preenchido; verificar disponibilidade no SICAR.
6. **MEDIA — Rural com georreferenciamento** ({stats.rural_com_geo:,} matrículas)
   - NUMERO_INCRA ou SIGEF preenchidos; confirmar se dado é válido e ativo.
7. **BAIXA — Demais registros** — informativos; sem ação imediata obrigatória.

---

## Observações importantes

- Não incluir dados pessoais na planilha — preencher apenas os campos indicados.
- Em caso de dúvida sobre a natureza do imóvel, escalar para o responsável.
- Em caso de dado não localizado no sistema, registrar "Dado não localizado" no resultado.
- Retornar a planilha preenchida para consolidação final.

---

*Checklist gerado pelo Cartório System — uso interno.*
"""

    assert_no_pii(md, out_path.name, doc_mode=True)
    out_path.write_text(md, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("Consolidador RI Real JSON — Cartório System")
    print("=" * 60)

    if not SOURCE_DIR.exists():
        print(f"[ERRO] Pasta de origem não encontrada: {SOURCE_DIR}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nLendo CSVs de: {SOURCE_DIR}")
    records = load_all_records()
    print(f"  Matrículas únicas carregadas: {len(records):,}")

    if not records:
        print("[ERRO] Nenhuma matrícula carregada. Verifique os arquivos de origem.")
        return 1

    rows = build_csv_rows(records)
    stats = calcular_stats(records, rows)

    print("\nEstatísticas:")
    print(f"  Total: {stats.total:,} | Urbanos: {stats.urbanos:,} | Rurais: {stats.rurais:,}")
    print(f"  Rural com CAR: {stats.rural_com_car:,} | Sem CAR: {stats.rural_sem_car:,}")
    print(f"  Rural com NIRF: {stats.rural_com_nirf:,} | Sem NIRF: {stats.rural_sem_nirf:,}")
    print(f"  Rural com CCIR: {stats.rural_com_ccir:,} | Sem CCIR: {stats.rural_sem_ccir:,}")
    print(f"  Rural com geo: {stats.rural_com_geo:,} | Sem geo: {stats.rural_sem_geo:,}")
    print(f"  Needs review: {stats.needs_review:,} | Urbano c/ rurais: {stats.urbano_com_rurais:,}")
    print(f"  Total pendências: {stats.total_pendencias:,}")

    # CSV operacional
    csv_path = OUT_DIR / "ri_real_json_plano_conferencia_colaboradores.csv"
    print(f"\nGerando CSV: {csv_path}")
    write_csv(rows, csv_path)
    print(f"  OK — {len(rows):,} linhas")

    # Relatório executivo
    md_path = OUT_DIR / "RI_REAL_JSON_RELATORIO_CONSOLIDADO_DIRETORIA.md"
    print(f"Gerando relatório executivo: {md_path}")
    write_relatorio_executivo(stats, md_path)
    print("  OK")

    # Checklist
    ck_path = OUT_DIR / "ri_real_json_checklist_conferencia.md"
    print(f"Gerando checklist: {ck_path}")
    write_checklist(stats, ck_path)
    print("  OK")

    # Validação anti-PII nos arquivos gerados
    print("\nValidação anti-PII nos arquivos gerados...")
    pii_ok = True
    for fpath, is_doc in [(csv_path, False), (md_path, True), (ck_path, True)]:
        content = fpath.read_text(encoding="utf-8")
        hits = check_pii(content, doc_mode=is_doc)
        if hits:
            summary = "; ".join(f"{label}={count}" for label, count in hits)
            print(f"  [ALERTA] {fpath.name}: {summary}")
            pii_ok = False
        else:
            print(f"  [OK] {fpath.name} — sem PII detectada")

    print("\n" + "=" * 60)
    if pii_ok:
        print("Consolidação concluída com sucesso. Nenhuma PII detectada.")
    else:
        print("[ATENÇÃO] PII detectada em um ou mais arquivos. Revisar antes de distribuir.")
    print("=" * 60)

    print(f"\nArquivos gerados em: {OUT_DIR}")
    print("  Para a diretoria : RI_REAL_JSON_RELATORIO_CONSOLIDADO_DIRETORIA.md")
    print("  Para colaboradores: ri_real_json_plano_conferencia_colaboradores.csv")
    print("  Checklist         : ri_real_json_checklist_conferencia.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
