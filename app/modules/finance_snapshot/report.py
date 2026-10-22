"""Formato local ``cartorio_system.finance_snapshot.local`` 0.1: montagem, validação e Markdown.

Experimental e PRIVADO (fica no data_dir da descoberta): contém valores agregados por bloco
e dia, nunca registro individual, descrição, nome, protocolo ou nome de aba. Chaves
fechadas, domínios por campo e reconciliação das contagens com a lista de abas; o
Markdown é função pura do objeto validado. Erros de validação informam só o caminho.

Estado da aba, em ordem de precedência:
  1. ``ignorada`` — nome sem ``ddmm`` inicial, data inválida ou fora do período aprovado;
  2. ``fora_do_padrao`` — sufixo não aprovado, data repetida em outra aba ou bloco não
     localizado (nenhuma checagem roda);
  3. ``feriado`` — sufixo aprovado; os valores do dia são preservados;
  4. ``preenchido`` — algum registro não nulo em dinheiro, malote, PIX, protesto ou cartão;
  5. ``sem_lancamento`` — nada disso na cópia (não quer dizer que não houve movimento).
A temporalidade (anterior, na referência, futura) é independente do estado; aba futura não
recebe checagem.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal

from app.modules.drive_capture.config import ALIAS_RE
from app.modules.finance_snapshot.layout import (
    APPROVED_SUFFIXES,
    BLOCK_COUNTS,
    BLOCK_FIELDS,
    BLOCK_FLAGS,
    BLOCK_KEYS,
    BLOCK_REASONS,
    BLOCKS,
    FORMULA_COVERAGE,
    SUM_FIELDS,
    SUM_REASONS,
    VALUE_REASONS,
    DayRead,
    norm,
    read_day,
)
from app.modules.services_snapshot.dates import TIMEZONE_NAME
from app.modules.services_snapshot.xlsx import Sheet

REPORT_FORMAT = "cartorio_system.finance_snapshot.local"
REPORT_VERSION = "0.1"
FAMILY = "gerenciamento_financeiro"

STATES = ["preenchido", "sem_lancamento", "feriado", "fora_do_padrao", "ignorada"]
STATE_REASONS = [
    "nome_sem_data",
    "data_invalida",
    "fora_do_periodo",
    "sufixo_nao_aprovado",
    "data_repetida",
    "bloco_nao_localizado",
]
TEMPORAL = ["anterior", "referencia", "futura"]
CONFERENCE = ["valida", "sem_conferencia", "indisponivel", "nao_aplicavel"]
CONTINUITY = ["confere", "diverge", "indisponivel", "nao_aplicavel"]
CONTINUITY_REASONS = [
    "sem_base",
    "base_ambigua",
    "base_fora_do_padrao",
    "base_sem_saldo",
    "caixa_inicial_indisponivel",
]
SUM_STATES = ["confere", "diverge", "indisponivel", "nao_aplicavel"]
BODY_DATE = ["concorda", "diverge", "indisponivel", "nao_aplicavel"]
NA_REASONS = ["estado_nao_elegivel", "data_futura"]
LIMITATIONS = [
    "fonte_copia_de_desenvolvimento",
    "sem_atualizacao_periodica",
    "cancelamentos_estornos_nao_registrados",
    "sem_consolidacao_entre_blocos",
    "valores_conforme_gravados_na_planilha",
]
# Acrescentada só quando alguma aba lida tem fórmula de total do PIX que, legivelmente, não
# alcança todas as linhas do bloco: o total publicado não é o total integral validado.
PIX_FORMULA_LIMITATION = "pix_total_publicado_omite_linhas_do_bloco"
ELIGIBLE = {"preenchido", "sem_lancamento", "feriado"}

_NAME = re.compile(r"^\s*(\d{2})(\d{2})(?!\d)(.*)$", re.S)
_DECIMAL = re.compile(r"-?(0|[1-9]\d*)(\.\d*[1-9])?")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ISO_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})")
_RUN = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{6}")
_PERIOD = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


class ReportRejected(Exception):
    """Objeto fora do formato. A mensagem traz só o caminho no esquema."""


# -- montagem ---------------------------------------------------------------------------------


def parse_tab_name(name: str, year: int, month: int) -> tuple[date | None, str | None, str | None]:
    """(data, sufixo aprovado ou None, motivo de recusa ou None). O nome é usado só aqui."""
    m = _NAME.match(name)
    if not m:
        return None, None, "nome_sem_data"
    day, mon = int(m.group(1)), int(m.group(2))
    try:
        when = date(year, mon, day)
    except ValueError:
        return None, None, "data_invalida"
    if mon != month:
        return None, None, "fora_do_periodo"
    suffix = norm(m.group(3)).lstrip(" -").strip()
    if not suffix:
        return when, None, None
    if suffix in APPROVED_SUFFIXES:
        return when, APPROVED_SUFFIXES[suffix], None
    return when, None, "sufixo_nao_aprovado"


def _na(reason: str) -> dict:
    return {"estado": "nao_aplicavel", "motivo": reason}


def _temporal(when: date, reference: date) -> str:
    return "anterior" if when < reference else "referencia" if when == reference else "futura"


def build_tabs(sheets: list[Sheet], year: int, month: int, reference: date) -> list[dict]:
    parsed = [parse_tab_name(s.name, year, month) for s in sheets]
    dates = Counter(d for d, _, reason in parsed if d is not None and reason is None)
    tabs: list[dict] = []
    reads: list[DayRead | None] = []
    for pos, (sheet, (when, suffix, reason)) in enumerate(zip(sheets, parsed, strict=True), 1):
        tab: dict = {
            "posicao": pos,
            "data": None,
            "estado": "ignorada",
            "motivo_estado": reason,
            "temporalidade": None,
            "blocos": None,
        }
        read = None
        if when is not None:  # inclui sufixo não aprovado, que tem data mas não estado
            read = read_day(sheet)
            tab["data"] = when.isoformat()
            tab["temporalidade"] = _temporal(when, reference)
            tab["blocos"] = read.blocks
            if reason is None and dates[when] > 1:
                reason = "data_repetida"
            if reason is None and not all(b["localizado"] for b in read.blocks.values()):
                reason = "bloco_nao_localizado"
            if reason is not None:
                tab["estado"], tab["motivo_estado"] = "fora_do_padrao", reason
            elif suffix == "feriado":
                tab["estado"], tab["motivo_estado"] = "feriado", None
            else:
                tab["estado"] = "preenchido" if read.movement else "sem_lancamento"
                tab["motivo_estado"] = None
        tabs.append(tab)
        reads.append(read)

    for tab, read in zip(tabs, reads, strict=True):
        if read is None or tab["estado"] not in ELIGIBLE or tab["temporalidade"] == "futura":
            why = "data_futura" if tab["estado"] in ELIGIBLE else "estado_nao_elegivel"
            tab["checagens"] = {
                "conferencia": {**_na(why), "sinal": None},
                "continuidade": {**_na(why), "base_data": None, "dias_desde_base": None},
                "soma": {k: _na(why) for k in SUM_FIELDS},
                "data_corpo": _na(why),
            }
            continue
        if read.body_date is None:
            body = {"estado": "indisponivel", "motivo": None}
        else:
            ok = read.body_date.isoformat() == tab["data"]
            body = {"estado": "concorda" if ok else "diverge", "motivo": None}
        tab["checagens"] = {
            "conferencia": read.conferencia,
            "continuidade": _continuity(tab, tabs),
            "soma": read.sums,
            "data_corpo": body,
        }
    return tabs


def _continuity(tab: dict, tabs: list[dict]) -> dict:
    """Caixa inicial × saldo teórico da aba de data imediatamente anterior, por data."""

    def out(
        state: str, reason: str | None, base: str | None = None, gap: int | None = None
    ) -> dict:
        return {"estado": state, "motivo": reason, "base_data": base, "dias_desde_base": gap}

    earlier = [t for t in tabs if t["data"] is not None and t["data"] < tab["data"]]
    if not earlier:
        return out("indisponivel", "sem_base")
    base_date = max(t["data"] for t in earlier)
    bases = [t for t in earlier if t["data"] == base_date]
    gap = (date.fromisoformat(tab["data"]) - date.fromisoformat(base_date)).days
    if len(bases) > 1:
        return out("indisponivel", "base_ambigua", base_date, gap)
    base = bases[0]
    if base["estado"] not in ELIGIBLE:
        return out("indisponivel", "base_fora_do_padrao", base_date, gap)
    # Saldo teórico só é saldo se a sua própria base (caixa inicial) existe: fórmula sobre
    # caixa inicial vazio (feriado, aba não preenchida) não transporta saldo.
    base_cash = base["blocos"]["dinheiro"]
    previous = base_cash["saldo_teorico"]["valor"]
    if previous is None or base_cash["caixa_inicial"]["valor"] is None:
        return out("indisponivel", "base_sem_saldo", base_date, gap)
    current = tab["blocos"]["dinheiro"]["caixa_inicial"]["valor"]
    if current is None:
        return out("indisponivel", "caixa_inicial_indisponivel", base_date, gap)
    same = Decimal(current) == Decimal(previous)
    return out("confere" if same else "diverge", None, base_date, gap)


def _fields(tab: dict) -> list[dict]:
    if not tab["blocos"]:
        return []
    return [tab["blocos"][b][f] for b in BLOCKS for f in BLOCK_FIELDS[b]]


def coverage(tabs: list[dict]) -> dict:
    states = Counter(t["estado"] for t in tabs)
    temporal = Counter(t["temporalidade"] or "sem_data" for t in tabs)
    dated = Counter(t["data"] for t in tabs if t["data"] is not None)
    reasons = Counter(f["motivo"] for t in tabs for f in _fields(t) if f["valor"] is None)
    blocks = {}
    for b in BLOCKS:
        located = sum(1 for t in tabs if t["blocos"] and t["blocos"][b]["localizado"])
        unread = sum(1 for t in tabs if not t["blocos"])
        blocks[b] = {
            "localizado": located,
            "nao_localizado": len(tabs) - located - unread,
            "nao_lido": unread,
        }
    long_values = sum(
        1
        for t in tabs
        for f in _fields(t)
        if f["valor"] is not None and "." in f["valor"] and len(f["valor"].split(".")[1]) > 2
    )
    return {
        "abas_total": len(tabs),
        "por_estado": {s: states[s] for s in STATES},
        "por_temporalidade": {k: temporal[k] for k in [*TEMPORAL, "sem_data"]},
        "datas_interpretadas": len(dated),
        "datas_repetidas": sum(1 for n in dated.values() if n > 1),
        "abas_com_campo_indisponivel": sum(
            1 for t in tabs if any(f["valor"] is None for f in _fields(t))
        ),
        "campos_indisponiveis_por_motivo": {r: reasons[r] for r in VALUE_REASONS},
        "valores_com_mais_de_duas_casas": long_values,
        "blocos": blocks,
        "pix_formula_do_total": {
            k: sum(1 for t in tabs if _pix_formula(t) == k) for k in [*FORMULA_COVERAGE, "nao_lido"]
        },
    }


def _pix_formula(tab: dict) -> str:
    pix = tab["blocos"]["pix"] if tab["blocos"] else None
    return pix["formula_do_total"] if pix and pix["localizado"] else "nao_lido"


def limitations(tabs: list[dict]) -> list[str]:
    omits = any(_pix_formula(t) == "omite_linhas" for t in tabs)
    return [*LIMITATIONS, PIX_FORMULA_LIMITATION] if omits else list(LIMITATIONS)


def check_totals(tabs: list[dict]) -> dict:
    conf: Counter[str] = Counter()
    for t in tabs:
        c = t["checagens"]["conferencia"]
        conf[f"valida_{c['sinal']}" if c["estado"] == "valida" else c["estado"]] += 1
    cont = Counter(t["checagens"]["continuidade"]["estado"] for t in tabs)
    body = Counter(t["checagens"]["data_corpo"]["estado"] for t in tabs)
    sums = {k: Counter(t["checagens"]["soma"][k]["estado"] for t in tabs) for k in SUM_FIELDS}
    conf_keys = [
        "valida_zero",
        "valida_nao_zero",
        "sem_conferencia",
        "indisponivel",
        "nao_aplicavel",
    ]
    return {
        "conferencia": {k: conf[k] for k in conf_keys},
        "continuidade": {k: cont[k] for k in CONTINUITY},
        "soma": {k: {s: sums[k][s] for s in SUM_STATES} for k in SUM_FIELDS},
        "data_corpo": {k: body[k] for k in BODY_DATE},
    }


def build_report(
    *,
    source_alias: str,
    manifest: dict,
    period: tuple[int, int],
    reference: date,
    sheets: list[Sheet],
    generated_at: datetime,
) -> dict:
    tabs = build_tabs(sheets, period[0], period[1], reference)
    return {
        "formato": REPORT_FORMAT,
        "versao": REPORT_VERSION,
        "gerado_em": generated_at.isoformat(timespec="seconds"),
        "origem": {
            "fonte_alias": source_alias,
            "familia": FAMILY,
            "run_id": manifest.get("run_id"),
            "capturada_em": manifest.get("captured_at"),
            "drive_modified_time": manifest.get("drive_modified_time"),
            "drive_version": manifest.get("drive_version"),
            "bytes": manifest.get("bytes"),
            "sha256": manifest.get("sha256"),
        },
        "periodo": f"{period[0]:04d}-{period[1]:02d}",
        "referencia": {"data": reference.isoformat(), "fuso": TIMEZONE_NAME},
        "limitacoes": limitations(tabs),
        "cobertura": coverage(tabs),
        "checagens": check_totals(tabs),
        "abas": tabs,
    }


# -- validação ----------------------------------------------------------------------------------


def _fail(path: str) -> ReportRejected:
    return ReportRejected(f"fora do formato em {path}")


def _keys(obj: object, keys: list[str], path: str) -> dict:
    if not isinstance(obj, dict) or list(obj) != keys:
        raise _fail(path)
    return obj


def _int(v: object, path: str, *, nullable: bool = False) -> None:
    if v is None and nullable:
        return
    if not isinstance(v, int) or isinstance(v, bool) or v < 0:
        raise _fail(path)


def _enum(v: object, domain: list[str], path: str, *, nullable: bool = False) -> None:
    if v is None and nullable:
        return
    if v not in domain:
        raise _fail(path)


def _match(v: object, rx: re.Pattern, path: str, *, nullable: bool = False) -> None:
    if v is None and nullable:
        return
    if not isinstance(v, str) or not rx.fullmatch(v):
        raise _fail(path)


def _money_field(v: object, path: str, reasons: list[str]) -> None:
    f = _keys(v, ["valor", "motivo"], path)
    if f["valor"] is None:
        _enum(f["motivo"], reasons, f"{path}.motivo")
    else:
        _match(f["valor"], _DECIMAL, f"{path}.valor")
        if f["motivo"] is not None:
            raise _fail(f"{path}.motivo")


def _counts(v: object, keys: list[str], path: str) -> int:
    obj = _keys(v, keys, path)
    for k in keys:
        _int(obj[k], f"{path}.{k}")
    return sum(obj.values())


def _validate_tab(t: object, i: int) -> None:
    p = f"abas[{i}]"
    tab = _keys(
        t, ["posicao", "data", "estado", "motivo_estado", "temporalidade", "blocos", "checagens"], p
    )
    if tab["posicao"] != i + 1:
        raise _fail(f"{p}.posicao")
    _enum(tab["estado"], STATES, f"{p}.estado")
    _enum(tab["motivo_estado"], STATE_REASONS, f"{p}.motivo_estado", nullable=True)
    if (tab["estado"] in ("ignorada", "fora_do_padrao")) != (tab["motivo_estado"] is not None):
        raise _fail(f"{p}.motivo_estado")
    if tab["estado"] == "ignorada":
        if tab["data"] is not None or tab["temporalidade"] is not None or tab["blocos"] is not None:
            raise _fail(p)
    else:
        _match(tab["data"], _ISO_DATE, f"{p}.data")
        _enum(tab["temporalidade"], TEMPORAL, f"{p}.temporalidade")
        blocks = _keys(tab["blocos"], BLOCKS, f"{p}.blocos")
        for b in BLOCKS:
            bp = f"{p}.blocos.{b}"
            blk = _keys(blocks[b], ["localizado", "motivo", *BLOCK_KEYS[b]], bp)
            if not isinstance(blk["localizado"], bool):
                raise _fail(f"{bp}.localizado")
            _enum(blk["motivo"], BLOCK_REASONS, f"{bp}.motivo", nullable=blk["localizado"])
            if blk["localizado"] and blk["motivo"] is not None:
                raise _fail(f"{bp}.motivo")
            for f in BLOCK_FIELDS[b]:
                _money_field(blk[f], f"{bp}.{f}", VALUE_REASONS)
            for flag, domain in BLOCK_FLAGS.get(b, {}).items():
                _enum(blk[flag], domain, f"{bp}.{flag}", nullable=not blk["localizado"])
                if not blk["localizado"] and blk[flag] is not None:
                    raise _fail(f"{bp}.{flag}")
            for c in BLOCK_COUNTS[b]:
                _int(blk[c], f"{bp}.{c}", nullable=not blk["localizado"])
    ck = _keys(
        tab["checagens"], ["conferencia", "continuidade", "soma", "data_corpo"], f"{p}.checagens"
    )
    conf = _keys(ck["conferencia"], ["estado", "motivo", "sinal"], f"{p}.conferencia")
    _enum(conf["estado"], CONFERENCE, f"{p}.conferencia.estado")
    _enum(
        conf["motivo"],
        [*VALUE_REASONS, *NA_REASONS, "bloco_indisponivel"],
        f"{p}.conferencia.motivo",
        nullable=True,
    )
    _enum(
        conf["sinal"],
        ["zero", "nao_zero"],
        f"{p}.conferencia.sinal",
        nullable=conf["estado"] != "valida",
    )
    cont = _keys(
        ck["continuidade"],
        ["estado", "motivo", "base_data", "dias_desde_base"],
        f"{p}.continuidade",
    )
    _enum(cont["estado"], CONTINUITY, f"{p}.continuidade.estado")
    _enum(
        cont["motivo"],
        [*CONTINUITY_REASONS, *NA_REASONS],
        f"{p}.continuidade.motivo",
        nullable=True,
    )
    _match(cont["base_data"], _ISO_DATE, f"{p}.continuidade.base_data", nullable=True)
    _int(cont["dias_desde_base"], f"{p}.continuidade.dias_desde_base", nullable=True)
    if cont["estado"] in ("confere", "diverge") and cont["base_data"] is None:
        raise _fail(f"{p}.continuidade.base_data")
    soma = _keys(ck["soma"], SUM_FIELDS, f"{p}.soma")
    for k in SUM_FIELDS:
        s = _keys(soma[k], ["estado", "motivo"], f"{p}.soma.{k}")
        _enum(s["estado"], SUM_STATES, f"{p}.soma.{k}.estado")
        _enum(
            s["motivo"],
            [*SUM_REASONS, *NA_REASONS],
            f"{p}.soma.{k}.motivo",
            nullable=s["estado"] in ("confere", "diverge"),
        )
    body = _keys(ck["data_corpo"], ["estado", "motivo"], f"{p}.data_corpo")
    _enum(body["estado"], BODY_DATE, f"{p}.data_corpo.estado")
    _enum(body["motivo"], NA_REASONS, f"{p}.data_corpo.motivo", nullable=True)
    eligible = tab["estado"] in ELIGIBLE and tab["temporalidade"] != "futura"
    if eligible == (conf["estado"] == "nao_aplicavel"):
        raise _fail(f"{p}.checagens")


def validate_report(rep: object) -> None:
    r = _keys(
        rep,
        [
            "formato",
            "versao",
            "gerado_em",
            "origem",
            "periodo",
            "referencia",
            "limitacoes",
            "cobertura",
            "checagens",
            "abas",
        ],
        "$",
    )
    if r["formato"] != REPORT_FORMAT or r["versao"] != REPORT_VERSION:
        raise _fail("formato")
    _match(r["gerado_em"], _ISO_TS, "gerado_em")
    o = _keys(
        r["origem"],
        [
            "fonte_alias",
            "familia",
            "run_id",
            "capturada_em",
            "drive_modified_time",
            "drive_version",
            "bytes",
            "sha256",
        ],
        "origem",
    )
    if not isinstance(o["fonte_alias"], str) or not ALIAS_RE.fullmatch(o["fonte_alias"]):
        raise _fail("origem.fonte_alias")
    if o["familia"] != FAMILY:
        raise _fail("origem.familia")
    _match(o["run_id"], _RUN, "origem.run_id")
    _match(o["capturada_em"], _ISO_TS, "origem.capturada_em")
    _match(o["drive_modified_time"], _ISO_TS, "origem.drive_modified_time", nullable=True)
    _match(o["drive_version"], re.compile(r"\d{1,20}"), "origem.drive_version", nullable=True)
    _int(o["bytes"], "origem.bytes")
    _match(o["sha256"], re.compile(r"[0-9a-f]{64}"), "origem.sha256")
    _match(r["periodo"], _PERIOD, "periodo")
    ref = _keys(r["referencia"], ["data", "fuso"], "referencia")
    _match(ref["data"], _ISO_DATE, "referencia.data")
    if ref["fuso"] != TIMEZONE_NAME:
        raise _fail("referencia.fuso")
    tabs = r["abas"]
    if not isinstance(tabs, list) or not tabs:
        raise _fail("abas")
    for i, t in enumerate(tabs):
        _validate_tab(t, i)
    # Reconciliação: agregados precisam ser exatamente o recálculo a partir das abas.
    cov = _keys(
        r["cobertura"],
        [
            "abas_total",
            "por_estado",
            "por_temporalidade",
            "datas_interpretadas",
            "datas_repetidas",
            "abas_com_campo_indisponivel",
            "campos_indisponiveis_por_motivo",
            "valores_com_mais_de_duas_casas",
            "blocos",
            "pix_formula_do_total",
        ],
        "cobertura",
    )
    if _counts(cov["por_estado"], STATES, "cobertura.por_estado") != len(tabs):
        raise _fail("cobertura.por_estado")
    if _counts(
        cov["por_temporalidade"], [*TEMPORAL, "sem_data"], "cobertura.por_temporalidade"
    ) != len(tabs):
        raise _fail("cobertura.por_temporalidade")
    _counts(cov["campos_indisponiveis_por_motivo"], VALUE_REASONS, "cobertura.campos")
    for b in BLOCKS:
        if _counts(
            cov["blocos"][b], ["localizado", "nao_localizado", "nao_lido"], f"cobertura.blocos.{b}"
        ) != len(tabs):
            raise _fail(f"cobertura.blocos.{b}")
    if cov != coverage(tabs):
        raise _fail("cobertura")
    if r["checagens"] != check_totals(tabs):
        raise _fail("checagens")
    if r["limitacoes"] != limitations(tabs):
        raise _fail("limitacoes")
    period = tuple(int(x) for x in r["periodo"].split("-"))
    for t in tabs:
        if t["data"] is not None and tuple(int(x) for x in t["data"].split("-")[:2]) != period:
            raise _fail("abas.data")


# -- renderização -------------------------------------------------------------------------------


def _v(f: dict) -> str:
    return f["valor"] if f["valor"] is not None else f"— ({f['motivo']})"


def render_markdown(rep: dict) -> str:
    """Markdown PRIVADO (tem valores). Só deve ser chamado com relatório validado."""
    o, cov, ck, ref = rep["origem"], rep["cobertura"], rep["checagens"], rep["referencia"]
    missing = {k: v for k, v in cov["campos_indisponiveis_por_motivo"].items() if v}
    lines = [
        "# Leitura local do Financeiro — PRIVADO (não versionar, não colar em chat)",
        "",
        f"Formato `{rep['formato']}` {rep['versao']} · gerado em {rep['gerado_em']}",
        f"Origem: {o['fonte_alias']} · run {o['run_id']} · capturada em {o['capturada_em']} · "
        f"versão do Drive {o['drive_version']} · {o['bytes']} bytes",
        f"Período {rep['periodo']} · referência {ref['data']} ({ref['fuso']})",
        "Limitações: " + ", ".join(rep["limitacoes"]),
        *(
            [
                "",
                f"**Aviso:** em {cov['pix_formula_do_total']['omite_linhas']} aba(s) a fórmula do "
                "total do PIX não alcança todas as linhas do bloco. O total mostrado é o valor "
                "publicado pela planilha, não um total integral validado; a soma diagnóstica "
                "usa todas as linhas do bloco e não substitui o total.",
            ]
            if PIX_FORMULA_LIMITATION in rep["limitacoes"]
            else []
        ),
        "",
        "## Cobertura",
        "",
        f"- Abas: {cov['abas_total']} · estados {cov['por_estado']}",
        f"- Temporalidade: {cov['por_temporalidade']}",
        f"- Datas interpretadas {cov['datas_interpretadas']} · repetidas "
        f"{cov['datas_repetidas']} · abas com campo indisponível "
        f"{cov['abas_com_campo_indisponivel']}",
        f"- Campos indisponíveis por motivo: {missing}",
        f"- Blocos: {cov['blocos']}",
        f"- Fórmula do total do PIX: {cov['pix_formula_do_total']}",
        f"- Valores com mais de duas casas decimais: {cov['valores_com_mais_de_duas_casas']}",
        "",
        "## Checagens (sinais para conferência, não conclusões)",
        "",
        f"- Conferência de caixa: {ck['conferencia']}",
        f"- Continuidade: {ck['continuidade']}",
        f"- Data do corpo × nome: {ck['data_corpo']}",
        *[f"- Soma × total ({k}): {v}" for k, v in ck["soma"].items()],
        "",
        "## Por dia",
        "",
        "| Pos. | Data | Estado | Tempo | Caixa inicial | Reg. | Entradas | Saídas | Malote | "
        "Saldo teórico | Conferido | Diferença | Conferência | Continuidade (base) | PIX | "
        "Protesto (reg./receb./repasse/emol.) | Maquininha (receber/cobrado) | "
        "Verif. (ok/inc.) | Data corpo |",
        "|" + "---|" * 19,
    ]
    for t in rep["abas"]:
        c = t["checagens"]
        if not t["blocos"]:
            lines.append(
                f"| {t['posicao']} | — | {t['estado']} ({t['motivo_estado']}) |" + " |" * 16
            )
            continue
        d, pix, pro, maq, ver = (
            t["blocos"][b] for b in ("dinheiro", "pix", "protesto", "maquininha", "verificacao")
        )
        conf = c["conferencia"]["estado"] + (
            f":{c['conferencia']['sinal']}" if c["conferencia"]["sinal"] else ""
        )
        cont = c["continuidade"]
        pix_total = _v(pix["total"]) + (
            " (fórmula omite linhas)" if pix["formula_do_total"] == "omite_linhas" else ""
        )
        estado = t["estado"] + (f" ({t['motivo_estado']})" if t["motivo_estado"] else "")
        lines.append(
            f"| {t['posicao']} | {t['data']} | {estado} | {t['temporalidade']} | "
            f"{_v(d['caixa_inicial'])} | {d['registros']} | {_v(d['total_entradas'])} | "
            f"{_v(d['total_saidas'])} | {_v(d['retirada_malote'])} | {_v(d['saldo_teorico'])} | "
            f"{_v(d['saldo_conferido'])} | {_v(d['diferenca'])} | {conf} | "
            f"{cont['estado']} ({cont['base_data'] or cont['motivo']}) | {pix_total} | "
            f"{pro['registros']} / {_v(pro['total_recebido'])} / {_v(pro['total_repassado'])} / "
            f"{_v(pro['total_emolumentos'])} | {_v(maq['total_a_receber'])} / "
            f"{_v(maq['total_cobrado'])} | "
            f"{ver['preenchidas']}/{ver['incompletas']} | {c['data_corpo']['estado']} |"
        )
    lines += [
        "",
        "Somas por soma×total com estado `diverge` pedem conferência na planilha; o "
        "total exibido é sempre o publicado.",
        "",
    ]
    return "\n".join(lines)


def render_summary(rep: dict) -> str:
    """Resumo COMPARTILHÁVEL: só códigos e contagens — nenhum valor, data ou nome."""
    cov, ck = rep["cobertura"], rep["checagens"]
    sums = {s: sum(ck["soma"][k][s] for k in SUM_FIELDS) for s in SUM_STATES}
    blocks = {b: cov["blocos"][b]["localizado"] for b in BLOCKS}
    return "\n".join(
        [
            f"Leitura local do Financeiro: run {rep['origem']['run_id']} · formato "
            f"{rep['formato']} {rep['versao']}",
            f"Abas {cov['abas_total']} · estados {cov['por_estado']}",
            f"Temporalidade {cov['por_temporalidade']}",
            f"Blocos localizados {blocks}",
            f"Abas com campo indisponível {cov['abas_com_campo_indisponivel']} · por motivo "
            f"{ {k: v for k, v in cov['campos_indisponiveis_por_motivo'].items() if v} }",
            f"Conferência {ck['conferencia']}",
            f"Continuidade {ck['continuidade']}",
            f"Data do corpo {ck['data_corpo']}",
            f"Soma × total (todos os campos) {sums}",
            f"Fórmula do total do PIX {cov['pix_formula_do_total']}",
            "Limitações " + ", ".join(rep["limitacoes"]),
        ]
    )
