"""Exportação financeira para o Atlas: um arquivo único com contrato próprio, fechado.

Contrato ``cartorio_system.atlas.finance_snapshot`` 1.0 (ADR-012). O formato local
``cartorio_system.finance_snapshot.local`` 0.1 continua interno: este objeto é montado
campo a campo a partir dele, com as listas e enumerações DECLARADAS AQUI (não importadas
de ``layout``/``report``), e validado contra esquema fechado, coerência interna e
aplicabilidade temporal antes da troca atômica. Mudança futura do formato local não
entra no contrato sem passar por este arquivo; o que o contrato não conhece recusa a
exportação, nunca a atravessa.

Entrada: só ``<data_dir>/finance_snapshot/latest.json``, lido uma vez. Sem rede,
credencial, coletor, XLSX, ``latest.md`` ou ``analyze``. A procedência é a DECLARADA no
relatório validado: o vínculo aos bytes do XLSX foi feito pelo ``analyze`` e não é refeito
aqui. Não há registro de tentativas: o contrato não informa atualização confirmada nem
tentativa posterior.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from app.core.logging import get_logger
from app.modules.drive_capture.config import CaptureConfig, FileSource
from app.modules.drive_capture.errors import Code, DriveCaptureError
from app.modules.drive_capture.store import RunLock, atomic_write_bytes, utc_now
from app.modules.finance_snapshot.pipeline import (
    LATEST,
    AnalyzeFailed,
    finance_source,
    output_dir,
)
from app.modules.finance_snapshot.report import (
    REPORT_FORMAT,
    REPORT_VERSION,
    validate_report,
)
from app.modules.finance_snapshot.report import ReportRejected as LocalReportRejected
from app.modules.services_snapshot.dates import capture_reference
from app.modules.services_snapshot.report import (
    BOOL,
    INT,
    NONE,
    ReportRejected,
    _check,
    _enum,
    _obj,
    _opt,
    iso,
)

logger = get_logger("finance_snapshot")

EXPORT_FORMAT = "cartorio_system.atlas.finance_snapshot"
EXPORT_VERSION = "1.0"
EXPORT_FILE = "atlas_snapshot.json"
SCOPE = "fonte_financeira_unica"
FAMILY = "gerenciamento_financeiro"
TIMEZONE = "America/Sao_Paulo"

# --------------------------------------------------------------------------- contrato

MONEY, COUNT, FORMULA = "monetario", "contagem", "formula"
# Seleção explícita e ordem do contrato. Nomes de aba, linhas, descrições, nomes de quem
# conferiu e protocolos não existem no formato local e não existem aqui.
BLOCKS = {
    "dinheiro": {
        "caixa_inicial": MONEY,
        "registros": COUNT,
        "total_entradas": MONEY,
        "total_saidas": MONEY,
        "retirada_malote": MONEY,
        "saldo_teorico": MONEY,
        "saldo_conferido": MONEY,
        "diferenca": MONEY,
    },
    "verificacao": {"preenchidas": COUNT, "incompletas": COUNT},
    "pix": {"total": MONEY, "formula_do_total": FORMULA},
    "protesto": {
        "registros": COUNT,
        "total_recebido": MONEY,
        "total_repassado": MONEY,
        "total_emolumentos": MONEY,
    },
    "maquininha": {"total_a_receber": MONEY, "total_cobrado": MONEY},
}
# Soma diagnóstica × total publicado: cada checagem compara com UM campo de um bloco.
SUMS = {
    "dinheiro_entradas": ("dinheiro", "total_entradas"),
    "dinheiro_saidas": ("dinheiro", "total_saidas"),
    "pix": ("pix", "total"),
    "protesto_recebido": ("protesto", "total_recebido"),
    "protesto_repassado": ("protesto", "total_repassado"),
    "maquininha_a_receber": ("maquininha", "total_a_receber"),
    "maquininha_cobrado": ("maquininha", "total_cobrado"),
}

STATES = ["preenchido", "sem_lancamento", "feriado", "fora_do_padrao", "ignorada"]
ELIGIBLE = {"preenchido", "sem_lancamento", "feriado"}
IGNORED_REASONS = ["nome_sem_data", "data_invalida", "fora_do_periodo"]
OUT_OF_PATTERN_REASONS = ["sufixo_nao_aprovado", "data_repetida", "bloco_nao_localizado"]
TEMPORAL = ["anterior", "referencia", "futura"]
VALUE_REASONS = [
    "vazio",
    "formula_sem_resultado",
    "erro_de_formula",
    "nao_numerico",
    "numero_invalido",
    "formato_de_data",
    "bloco_indisponivel",
    "total_nao_confirmado",
    "sem_conferencia",
    "conferencia_indisponivel",
]
BLOCK_REASONS = [
    "ancora_ausente",
    "ancora_repetida",
    "layout_invalido",
    "ordem_invalida",
    "limite_indefinido",
]
FORMULA_COVERAGE = ["cobre_o_bloco", "omite_linhas", "nao_verificavel"]
NA_REASONS = ["estado_nao_elegivel", "data_futura"]
CONFERENCE = ["valida", "sem_conferencia", "indisponivel", "nao_aplicavel"]
CONFERENCE_TOTALS = ["valida_zero", "valida_nao_zero", "sem_conferencia", "indisponivel"]
CONTINUITY = ["confere", "diverge", "indisponivel", "nao_aplicavel"]
CONTINUITY_REASONS = [
    "sem_base",
    "base_ambigua",
    "base_fora_do_padrao",
    "base_sem_saldo",
    "caixa_inicial_indisponivel",
]
SUM_STATES = ["confere", "diverge", "indisponivel", "nao_aplicavel"]
SUM_REASONS = [
    "total_indisponivel",
    "parcela_invalida",
    "parcela_incompleta",
    "parcela_por_formula",
    "subtotal_no_perimetro",
    "perimetro_divergente",
    "bloco_indisponivel",
]
BODY_DATE = ["concorda", "diverge", "indisponivel", "nao_aplicavel"]
LIMITATIONS = [
    "fonte_copia_de_desenvolvimento",
    "sem_atualizacao_periodica",
    "cancelamentos_estornos_nao_registrados",
    "sem_consolidacao_entre_blocos",
    "valores_conforme_gravados_na_planilha",
]
PIX_LIMITATION = "pix_total_publicado_omite_linhas_do_bloco"

# [0-9] e não \d: \d aceita dígitos Unicode, que o contrato não admite.
_DECIMAL = r"-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?"
_DATE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
_TS = (
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})"
)
_RUN = r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}"
_ALIAS = r"[a-z][a-z0-9_]{1,31}"
_PERIOD = r"[0-9]{4}-(0[1-9]|1[0-2])"

# --------------------------------------------------------------------------- esquema

_MONEY = (
    "union",
    (_obj(valor=("re", _DECIMAL), motivo=NONE), _obj(valor=NONE, motivo=_enum(VALUE_REASONS))),
)
_KIND = {MONEY: _MONEY, COUNT: _opt(INT), FORMULA: _opt(_enum(FORMULA_COVERAGE))}
_DAY = _obj(
    posicao=INT,
    data=_opt(("re", _DATE)),
    estado=_enum(STATES),
    motivo_estado=_opt(_enum([*IGNORED_REASONS, *OUT_OF_PATTERN_REASONS])),
    temporalidade=_opt(_enum(TEMPORAL)),
    blocos=_opt(
        _obj(
            **{
                b: _obj(
                    localizado=BOOL,
                    motivo=_opt(_enum(BLOCK_REASONS)),
                    **{k: _KIND[kind] for k, kind in fields.items()},
                )
                for b, fields in BLOCKS.items()
            }
        )
    ),
    checagens=_obj(
        conferencia=_obj(
            estado=_enum(CONFERENCE),
            motivo=_opt(_enum([*VALUE_REASONS, *NA_REASONS])),
            sinal=_opt(_enum(["zero", "nao_zero"])),
        ),
        continuidade=_obj(
            estado=_enum(CONTINUITY),
            motivo=_opt(_enum([*CONTINUITY_REASONS, *NA_REASONS])),
            base_data=_opt(("re", _DATE)),
            dias_desde_base=_opt(INT),
        ),
        soma=_obj(
            **{
                k: _obj(estado=_enum(SUM_STATES), motivo=_opt(_enum([*SUM_REASONS, *NA_REASONS])))
                for k in SUMS
            }
        ),
        data_corpo=_obj(estado=_enum(BODY_DATE), motivo=_opt(_enum(NA_REASONS))),
    ),
)


def _tally(keys: list[str]) -> tuple:
    return _obj(**{k: INT for k in keys})


EXPORT_SCHEMA = _obj(
    formato=_enum([EXPORT_FORMAT]),
    versao=_enum([EXPORT_VERSION]),
    origem=_obj(
        formato_local=_enum([REPORT_FORMAT]),
        versao_local=_enum([REPORT_VERSION]),
        escopo=_enum([SCOPE]),
        fonte_alias=("re", _ALIAS),
        familia=_enum([FAMILY]),
        run_id=("re", _RUN),
    ),
    periodo=("re", _PERIOD),
    tempos=_obj(
        capturada_em=("re", _TS),
        relatorio_gerado_em=("re", _TS),
        exportado_em=("re", _TS),
        referencia_indicadores=("re", _DATE),
        fuso_referencia=_enum([TIMEZONE]),
    ),
    limitacoes=("list", _enum([*LIMITATIONS, PIX_LIMITATION])),
    cobertura=_obj(
        abas_total=INT,
        por_estado=_tally(STATES),
        por_temporalidade=_tally([*TEMPORAL, "sem_data"]),
        datas_interpretadas=INT,
        datas_repetidas=INT,
        abas_com_campo_indisponivel=INT,
        campos_indisponiveis_por_motivo=_tally(VALUE_REASONS),
        valores_com_mais_de_duas_casas=INT,
        blocos=_obj(**{b: _tally(["localizado", "nao_localizado", "nao_lido"]) for b in BLOCKS}),
        pix_formula_do_total=_tally([*FORMULA_COVERAGE, "nao_lido"]),
    ),
    checagens=_obj(
        conferencia=_tally([*CONFERENCE_TOTALS, "nao_aplicavel"]),
        continuidade=_tally(CONTINUITY),
        soma=_obj(**{k: _tally(SUM_STATES) for k in SUMS}),
        data_corpo=_tally(BODY_DATE),
    ),
    dias=("list", _DAY),
)


class ExportRejected(Exception):
    """Objeto fora do contrato. ``code`` controlado; a mensagem é só o caminho."""

    def __init__(self, code: str, path: str) -> None:
        super().__init__(path)
        self.code = code


class ExportFailed(Exception):
    """Código fixo; nunca carrega valor lido. ``file_state`` só nas falhas de publicação:
    ``preservada`` · ``ausente`` (não havia anterior e nada foi criado) · ``substituida``
    (a troca concluiu antes da falha) · ``indeterminado``."""

    def __init__(self, code: str, exit_code: int = 2, file_state: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.exit_code = exit_code
        self.file_state = file_state


# --------------------------------------------------------------------------- montagem


def _money(field: dict) -> dict:
    return {"valor": field["valor"], "motivo": field["motivo"]}


def _block(name: str, blk: dict) -> dict:
    out = {"localizado": blk["localizado"], "motivo": blk["motivo"]}
    for key, kind in BLOCKS[name].items():
        out[key] = _money(blk[key]) if kind == MONEY else blk[key]
    return out


def _day(tab: dict) -> dict:
    ck = tab["checagens"]
    conf, cont = ck["conferencia"], ck["continuidade"]
    return {
        "posicao": tab["posicao"],
        "data": tab["data"],
        "estado": tab["estado"],
        "motivo_estado": tab["motivo_estado"],
        "temporalidade": tab["temporalidade"],
        "blocos": (
            None if tab["blocos"] is None else {b: _block(b, tab["blocos"][b]) for b in BLOCKS}
        ),
        "checagens": {
            "conferencia": {
                "estado": conf["estado"],
                "motivo": conf["motivo"],
                "sinal": conf["sinal"],
            },
            "continuidade": {
                "estado": cont["estado"],
                "motivo": cont["motivo"],
                "base_data": cont["base_data"],
                "dias_desde_base": cont["dias_desde_base"],
            },
            "soma": {
                k: {"estado": ck["soma"][k]["estado"], "motivo": ck["soma"][k]["motivo"]}
                for k in SUMS
            },
            "data_corpo": {
                "estado": ck["data_corpo"]["estado"],
                "motivo": ck["data_corpo"]["motivo"],
            },
        },
    }


def _counts(src: dict, keys: list[str]) -> dict:
    return {k: src[k] for k in keys}


def build_export(report: dict, exported_at: datetime) -> dict:
    """``report`` JÁ validado por ``validate_report``; nada é repassado sem nome explícito."""
    o, cov, ck = report["origem"], report["cobertura"], report["checagens"]
    return {
        "formato": EXPORT_FORMAT,
        "versao": EXPORT_VERSION,
        "origem": {
            "formato_local": report["formato"],
            "versao_local": report["versao"],
            "escopo": SCOPE,
            "fonte_alias": o["fonte_alias"],
            "familia": o["familia"],
            "run_id": o["run_id"],
        },
        "periodo": report["periodo"],
        "tempos": {
            "capturada_em": o["capturada_em"],
            "relatorio_gerado_em": report["gerado_em"],
            "exportado_em": iso(exported_at),
            "referencia_indicadores": report["referencia"]["data"],
            "fuso_referencia": report["referencia"]["fuso"],
        },
        "limitacoes": list(report["limitacoes"]),
        "cobertura": {
            "abas_total": cov["abas_total"],
            "por_estado": _counts(cov["por_estado"], STATES),
            "por_temporalidade": _counts(cov["por_temporalidade"], [*TEMPORAL, "sem_data"]),
            "datas_interpretadas": cov["datas_interpretadas"],
            "datas_repetidas": cov["datas_repetidas"],
            "abas_com_campo_indisponivel": cov["abas_com_campo_indisponivel"],
            "campos_indisponiveis_por_motivo": _counts(
                cov["campos_indisponiveis_por_motivo"], VALUE_REASONS
            ),
            "valores_com_mais_de_duas_casas": cov["valores_com_mais_de_duas_casas"],
            "blocos": {
                b: _counts(cov["blocos"][b], ["localizado", "nao_localizado", "nao_lido"])
                for b in BLOCKS
            },
            "pix_formula_do_total": _counts(
                cov["pix_formula_do_total"], [*FORMULA_COVERAGE, "nao_lido"]
            ),
        },
        "checagens": {
            "conferencia": _counts(ck["conferencia"], [*CONFERENCE_TOTALS, "nao_aplicavel"]),
            "continuidade": _counts(ck["continuidade"], CONTINUITY),
            "soma": {k: _counts(ck["soma"][k], SUM_STATES) for k in SUMS},
            "data_corpo": _counts(ck["data_corpo"], BODY_DATE),
        },
        "dias": [_day(t) for t in report["abas"]],
    }


# --------------------------------------------------------------------------- validação


def _require(ok: bool, path: str, code: str = "exportacao_invalida") -> None:
    if not ok:
        raise ExportRejected(code, path)


def _timestamp(text: str, path: str) -> datetime:
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        raise ExportRejected("inconsistencia_temporal", path) from None
    _require(value.tzinfo is not None, path, "inconsistencia_temporal")
    return value


def _civil(text: str, path: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ExportRejected("inconsistencia_temporal", path) from None


def _check_times(exp: dict) -> date:
    """Datas e instantes efetivos (não só o texto). Devolve a data de referência."""
    t = exp["tempos"]
    captured = _timestamp(t["capturada_em"], "tempos.capturada_em")
    generated = _timestamp(t["relatorio_gerado_em"], "tempos.relatorio_gerado_em")
    exported = _timestamp(t["exportado_em"], "tempos.exportado_em")
    temporal = "inconsistencia_temporal"
    _require(captured <= generated <= exported, "tempos (ordem)", temporal)
    reference = _civil(t["referencia_indicadores"], "tempos.referencia_indicadores")
    # Mesma conversão do analyze. O período NÃO precisa ser o mês da captura.
    _require(
        capture_reference(t["capturada_em"]) == reference,
        "tempos.referencia_indicadores",
        temporal,
    )
    year, month = (int(x) for x in exp["periodo"].split("-"))
    for i, d in enumerate(exp["dias"]):
        p = f"dias[{i}]"
        if d["data"] is None:
            continue
        when = _civil(d["data"], f"{p}.data")
        _require((when.year, when.month) == (year, month), f"{p}.data", temporal)
        expected = (
            "anterior" if when < reference else "referencia" if when == reference else "futura"
        )
        _require(d["temporalidade"] == expected, f"{p}.temporalidade", temporal)
        base = d["checagens"]["continuidade"]["base_data"]
        if base is not None:
            _civil(base, f"{p}.continuidade.base_data")
    return reference


def _check_block(name: str, blk: dict, path: str) -> None:
    money = [blk[k] for k, kind in BLOCKS[name].items() if kind == MONEY]
    plain = [blk[k] for k, kind in BLOCKS[name].items() if kind != MONEY]
    if blk["localizado"]:
        _require(blk["motivo"] is None, f"{path}.motivo")
        _require(all(v is not None for v in plain), path)
        _require(all(f["motivo"] != "bloco_indisponivel" for f in money), path)
    else:
        _require(blk["motivo"] is not None, f"{path}.motivo")
        _require(all(v is None for v in plain), path)
        _require(all(f == {"valor": None, "motivo": "bloco_indisponivel"} for f in money), path)


def _check_day(d: dict, i: int, by_date: dict[str, list[dict]]) -> None:
    p = f"dias[{i}]"
    _require(d["posicao"] == i + 1, f"{p}.posicao")
    state, reason = d["estado"], d["motivo_estado"]
    if state == "ignorada":
        _require(reason in IGNORED_REASONS, f"{p}.motivo_estado")
        _require(d["data"] is None and d["temporalidade"] is None and d["blocos"] is None, p)
    else:
        _require(d["data"] is not None and d["temporalidade"] is not None, p)
        _require(d["blocos"] is not None, f"{p}.blocos")
        if state == "fora_do_padrao":
            _require(reason in OUT_OF_PATTERN_REASONS, f"{p}.motivo_estado")
        else:
            _require(reason is None, f"{p}.motivo_estado")
    if d["blocos"] is not None:
        for b in BLOCKS:
            _check_block(b, d["blocos"][b], f"{p}.blocos.{b}")
        located = all(d["blocos"][b]["localizado"] for b in BLOCKS)
        _require(located or state not in ELIGIBLE, f"{p}.blocos")
        if reason == "bloco_nao_localizado":
            _require(not located, f"{p}.blocos")
    if reason == "data_repetida":
        _require(len(by_date[d["data"]]) > 1, f"{p}.motivo_estado")

    ck = d["checagens"]
    checks = [ck["conferencia"], ck["continuidade"], ck["data_corpo"], *ck["soma"].values()]
    applicable = state in ELIGIBLE and d["temporalidade"] != "futura"
    if not applicable:
        why = "data_futura" if state in ELIGIBLE else "estado_nao_elegivel"
        _require(
            all(c["estado"] == "nao_aplicavel" and c["motivo"] == why for c in checks),
            f"{p}.checagens",
        )
        _require(ck["conferencia"]["sinal"] is None, f"{p}.checagens.conferencia")
        cont = ck["continuidade"]
        _require(cont["base_data"] is None and cont["dias_desde_base"] is None, f"{p}.checagens")
        return
    _require(all(c["estado"] != "nao_aplicavel" for c in checks), f"{p}.checagens")
    _check_conference(ck["conferencia"], d["blocos"]["dinheiro"], f"{p}.checagens.conferencia")
    _check_continuity(d, by_date, f"{p}.checagens.continuidade")
    for k, (b, f) in SUMS.items():
        s = ck["soma"][k]
        sp = f"{p}.checagens.soma.{k}"
        if s["estado"] in ("confere", "diverge"):
            _require(s["motivo"] is None, sp)
        else:
            _require(s["motivo"] in SUM_REASONS, sp)
        # O total publicado ausente é o único caminho de "total_indisponivel".
        missing = d["blocos"][b][f]["valor"] is None
        _require(missing == (s["motivo"] == "total_indisponivel"), sp)
    _require(ck["data_corpo"]["motivo"] is None, f"{p}.checagens.data_corpo")


def _check_conference(conf: dict, cash: dict, path: str) -> None:
    diff, counted = cash["diferenca"], cash["saldo_conferido"]
    if conf["estado"] == "valida":
        # Diferença só comprova conferência com saldo conferido e teórico numéricos.
        _require(conf["motivo"] is None, path)
        _require(
            None not in (diff["valor"], counted["valor"], cash["saldo_teorico"]["valor"]), path
        )
        zero = Decimal(diff["valor"]) == 0
        _require(conf["sinal"] == ("zero" if zero else "nao_zero"), f"{path}.sinal")
        return
    _require(conf["sinal"] is None and diff["valor"] is None, path)
    if conf["estado"] == "sem_conferencia":
        _require(conf["motivo"] is None, path)
        _require(counted == {"valor": None, "motivo": "vazio"}, path)
        _require(diff["motivo"] == "sem_conferencia", path)
    else:
        _require(conf["motivo"] in VALUE_REASONS, path)
        _require(diff["motivo"] == "conferencia_indisponivel", path)


def _check_continuity(d: dict, by_date: dict[str, list[dict]], path: str) -> None:
    """Base = data imediatamente anterior entre as datas exportadas; nunca inventada."""
    cont = d["checagens"]["continuidade"]
    earlier = [x for x in by_date if x < d["data"]]
    if not earlier:
        none = {"estado": "indisponivel", "motivo": "sem_base"}
        _require(cont == {**none, "base_data": None, "dias_desde_base": None}, path)
        return
    base = max(earlier)
    _require(cont["base_data"] == base, f"{path}.base_data")
    gap = (date.fromisoformat(d["data"]) - date.fromisoformat(base)).days
    _require(cont["dias_desde_base"] == gap, f"{path}.dias_desde_base")
    # Mesma precedência da _continuity do leitor; o estado declarado tem de ser o único
    # compatível com os campos exportados. Comparar só aceita ou recusa: nada é corrigido.
    bases = by_date[base]
    current = d["blocos"]["dinheiro"]["caixa_inicial"]["valor"]
    if len(bases) > 1:
        expected = ("indisponivel", "base_ambigua")
    elif bases[0]["estado"] not in ELIGIBLE:
        expected = ("indisponivel", "base_fora_do_padrao")
    else:
        cash = (bases[0]["blocos"] or {}).get("dinheiro")
        _require(cash is not None, f"{path}.base_data")
        opening, theoretical = cash["caixa_inicial"]["valor"], cash["saldo_teorico"]["valor"]
        if opening is None or theoretical is None:
            expected = ("indisponivel", "base_sem_saldo")
        elif current is None:
            expected = ("indisponivel", "caixa_inicial_indisponivel")
        elif Decimal(current) == Decimal(theoretical):
            expected = ("confere", None)
        else:
            expected = ("diverge", None)
    _require((cont["estado"], cont["motivo"]) == expected, path)


def _money_fields(d: dict) -> list[dict]:
    if d["blocos"] is None:
        return []
    return [
        d["blocos"][b][k]
        for b, fields in BLOCKS.items()
        for k, kind in fields.items()
        if kind == MONEY
    ]


def _pix_formula(d: dict) -> str:
    pix = d["blocos"]["pix"] if d["blocos"] else None
    return pix["formula_do_total"] if pix and pix["localizado"] else "nao_lido"


def recount(days: list[dict]) -> tuple[list[str], dict, dict]:
    """Limitações, cobertura e totais de checagens recalculados a partir de ``dias``."""
    states = Counter(d["estado"] for d in days)
    temporal = Counter(d["temporalidade"] or "sem_data" for d in days)
    dated = Counter(d["data"] for d in days if d["data"] is not None)
    missing = Counter(f["motivo"] for d in days for f in _money_fields(d) if f["valor"] is None)
    blocks = {}
    for b in BLOCKS:
        located = sum(1 for d in days if d["blocos"] and d["blocos"][b]["localizado"])
        unread = sum(1 for d in days if not d["blocos"])
        blocks[b] = {
            "localizado": located,
            "nao_localizado": len(days) - located - unread,
            "nao_lido": unread,
        }
    formulas = Counter(_pix_formula(d) for d in days)
    coverage = {
        "abas_total": len(days),
        "por_estado": {s: states[s] for s in STATES},
        "por_temporalidade": {k: temporal[k] for k in [*TEMPORAL, "sem_data"]},
        "datas_interpretadas": len(dated),
        "datas_repetidas": sum(1 for n in dated.values() if n > 1),
        "abas_com_campo_indisponivel": sum(
            1 for d in days if any(f["valor"] is None for f in _money_fields(d))
        ),
        "campos_indisponiveis_por_motivo": {r: missing[r] for r in VALUE_REASONS},
        "valores_com_mais_de_duas_casas": sum(
            1
            for d in days
            for f in _money_fields(d)
            if f["valor"] is not None and len(f["valor"].partition(".")[2]) > 2
        ),
        "blocos": blocks,
        "pix_formula_do_total": {k: formulas[k] for k in [*FORMULA_COVERAGE, "nao_lido"]},
    }
    conf: Counter[str] = Counter()
    for d in days:
        c = d["checagens"]["conferencia"]
        conf[f"valida_{c['sinal']}" if c["estado"] == "valida" else c["estado"]] += 1
    checks = {
        "conferencia": {k: conf[k] for k in [*CONFERENCE_TOTALS, "nao_aplicavel"]},
        "continuidade": {
            k: sum(1 for d in days if d["checagens"]["continuidade"]["estado"] == k)
            for k in CONTINUITY
        },
        "soma": {
            k: {
                s: sum(1 for d in days if d["checagens"]["soma"][k]["estado"] == s)
                for s in SUM_STATES
            }
            for k in SUMS
        },
        "data_corpo": {
            k: sum(1 for d in days if d["checagens"]["data_corpo"]["estado"] == k)
            for k in BODY_DATE
        },
    }
    limits = [*LIMITATIONS, PIX_LIMITATION] if formulas["omite_linhas"] else list(LIMITATIONS)
    return limits, coverage, checks


def validate_export(export: object) -> None:
    """Esquema fechado em todos os níveis, tempos efetivos e coerência com ``dias``.
    Divergência recusa o objeto; nunca o corrige. Erros carregam só o caminho."""
    try:
        _check(export, EXPORT_SCHEMA, "exportacao")
    except ReportRejected as exc:
        raise ExportRejected("exportacao_invalida", str(exc)) from None
    exp: dict = export  # type: ignore[assignment]
    days = exp["dias"]
    _require(bool(days), "dias")
    _check_times(exp)
    by_date: dict[str, list[dict]] = {}
    for d in days:
        if d["data"] is not None:
            by_date.setdefault(d["data"], []).append(d)
    for i, d in enumerate(days):
        _check_day(d, i, by_date)
    limits, coverage, checks = recount(days)
    _require(exp["limitacoes"] == limits, "limitacoes")
    _require(exp["cobertura"] == coverage, "cobertura")
    _require(exp["checagens"] == checks, "checagens")


# --------------------------------------------------------------------------- execução


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("chave duplicada")
    return dict(pairs)


def _no_constant(_name: str) -> object:
    raise ValueError("constante não finita")


def _finite(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):  # 1e400 vira inf sem passar por parse_constant
        raise ValueError("número não finito")
    return value


def strict_loads(raw: bytes) -> object:
    """JSON UTF-8 sem chave duplicada e sem NaN/Infinity. Levanta ValueError."""
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_no_duplicates,
        parse_constant=_no_constant,
        parse_float=_finite,
    )


def serialize(export: dict) -> bytes:
    return json.dumps(export, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _decode_report(raw: bytes) -> dict:
    try:
        report = strict_loads(raw)
    except ValueError:  # inclui UnicodeDecodeError e JSONDecodeError
        raise ExportFailed("entrada_invalida") from None
    if not isinstance(report, dict) or (report.get("formato"), report.get("versao")) != (
        REPORT_FORMAT,
        REPORT_VERSION,
    ):
        raise ExportFailed("formato_nao_suportado")
    try:
        validate_report(report)
    except (LocalReportRejected, ValueError, TypeError, KeyError, AttributeError):
        raise ExportFailed("entrada_invalida") from None
    return report


def _publish(target: Path, payload: bytes) -> None:
    """Troca atômica pelo auxiliar do coletor. Se falhar, o estado do arquivo é CONFERIDO
    em disco: o auxiliar pode falhar depois do ``os.replace`` (limpeza do temporário)."""
    previous = _read(target)
    try:
        atomic_write_bytes(target, payload)
    except Exception:  # qualquer falha: o estado real em disco decide a mensagem
        try:
            now = _read(target)
        except OSError:
            raise ExportFailed("falha_ao_gravar", file_state="indeterminado") from None
        if now == previous:
            state = "ausente" if previous is None else "preservada"
            raise ExportFailed("falha_ao_gravar", file_state=state) from None
        if now == payload:
            raise ExportFailed("gravado_com_falha_posterior", file_state="substituida") from None
        raise ExportFailed("falha_ao_gravar", file_state="indeterminado") from None


def _export_locked(
    out: Path, source: FileSource, run_id: str, period: str, clock: Callable[[], datetime]
) -> dict:
    try:
        raw = _read(out / LATEST)  # uma leitura só: fixa a versão exportada
    except OSError:
        raise ExportFailed("leitura_falhou") from None
    if raw is None:
        raise ExportFailed("sem_relatorio", 3)
    report = _decode_report(raw)
    origin = report["origem"]
    if (origin["fonte_alias"], origin["familia"]) != (source.alias, source.family):
        raise ExportFailed("fonte_divergente")
    if origin["run_id"] != run_id:
        raise ExportFailed("run_divergente")
    if report["periodo"] != period:
        raise ExportFailed("periodo_divergente")
    try:
        export = build_export(report, clock())
        validate_export(export)
    except ExportRejected as rejected:
        raise ExportFailed(rejected.code) from None
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ExportFailed("exportacao_invalida") from None
    try:
        payload = serialize(export)
        if strict_loads(payload) != export:
            raise ValueError("ida e volta divergente")
    except (TypeError, ValueError):
        raise ExportFailed("falha_ao_serializar") from None
    _publish(out / EXPORT_FILE, payload)
    return export


def export_atlas(
    config: CaptureConfig,
    run_id: str,
    period: str,
    *,
    clock: Callable[[], datetime] | None = None,
) -> dict:
    """Publica ``<data_dir>/finance_snapshot/atlas_snapshot.json``. Levanta ExportFailed.

    A trava (``finance_snapshot/run.lock``) só exclui OUTRA exportação financeira: o
    ``analyze`` não a usa. A consistência com ele vem de ler um único ``latest.json``,
    promovido atomicamente, e exigir que ele seja do run e do período pedidos."""
    if not re.fullmatch(_RUN, run_id) or not re.fullmatch(_PERIOD, period):
        raise ExportFailed("argumento_invalido")
    try:
        source = finance_source(config)  # mesma regra do analyze, antes de abrir conteúdo
    except AnalyzeFailed:
        raise ExportFailed("fora_do_recorte_financeiro") from None
    out = output_dir(config)
    if not out.is_dir():  # não cria o diretório só para dizer que não há relatório
        raise ExportFailed("sem_relatorio", 3)
    lock = RunLock(out, "finance-snapshot-export-atlas")
    try:
        lock.__enter__()
    except DriveCaptureError as exc:
        code = "exportacao_em_andamento" if exc.code == Code.RUN_LOCKED else "erro_local"
        raise ExportFailed(code, 4 if exc.code == Code.RUN_LOCKED else 2) from None
    except OSError:
        raise ExportFailed("erro_local") from None
    try:
        export = _export_locked(out, source, run_id, period, clock or utc_now)
    except OSError:  # antes da troca: nada do arquivo final foi tocado
        raise ExportFailed("erro_local") from None
    finally:
        try:
            lock.__exit__(None, None, None)
        except OSError:
            released = False
        else:
            released = True
    if not released:  # a exportação JÁ foi publicada; só a trava ficou
        raise ExportFailed("trava_nao_removida", file_state="substituida")
    logger.info("exportação financeira para o Atlas publicada (run %s)", run_id)
    return export
