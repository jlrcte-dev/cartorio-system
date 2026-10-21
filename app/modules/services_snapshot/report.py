"""Formato local versionado do retrato e do registro de tentativa, validação e Markdown.

Formato ``cartorio_system.services_snapshot.local`` — local e experimental, NÃO é
contrato do Atlas. ``refresh`` grava a v1.1 (com indicadores de datas); ``show`` lê também
a v1.0, que não tem datas e nunca é reinterpretada como se tivesse. A proteção é por
construção: o objeto é montado só com chaves fixas, e validate_* confere cada valor
contra o domínio do seu campo (enumerações aprovadas, contagens, estatísticas numéricas,
percentuais, timestamps ISO 8601 com fuso, identificadores técnicos por regex) e, na
v1.1, as reconciliações das métricas de datas. Nenhuma data individual é gravada: só a
referência, que é a data civil da captura. O Markdown é função pura do objeto já
validado. Erros de validação informam só o caminho no esquema, nunca o valor.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, date, datetime

from app.modules.drive_capture.config import ALIAS_RE, FAMILIES
from app.modules.drive_capture.errors import Code
from app.modules.services_snapshot.dates import (
    AGE_BANDS,
    BRT,
    CLOSED_GROUPS,
    COVERAGE_KEYS,
    DATE_FIELDS,
    DUE_BUCKETS,
    FIELD_STATES,
    GROUPS,
    SAMPLES,
    SIGNALS,
    TIMEZONE_NAME,
    aggregate_dates,
    capture_reference,
)
from app.modules.services_snapshot.rules import (
    CATEGORIES,
    CATEGORY_LABEL,
    FIELD_LABEL,
    GAP_TEXT,
    NAMED_IGNORED,
    NAMED_IGNORED_V10,
    OPEN,
    PENDING_REASONS,
    PRENOTATION_SECTOR,
    SECTORS,
    SIGNAL_KEYS,
    aggregate,
)

REPORT_FORMAT = "cartorio_system.services_snapshot.local"
ATTEMPT_FORMAT = "cartorio_system.services_snapshot.attempt"
REPORT_VERSION = "1.1"  # o que refresh grava
LEGACY_REPORT_VERSION = "1.0"  # só leitura: sem indicadores de datas
ATTEMPT_VERSION = "1.0"

STAGES = [
    "configuracao",
    "coleta",
    "vinculo",
    "integridade",
    "leitura",
    "validacao",
    "publicacao",
    "desconhecida",
]
LOCAL_CODES = [
    "fora_do_recorte_piloto",
    "coleta_sem_captura",
    "geracao_nao_vinculada",
    "geracao_indisponivel",
    "formato_nao_suportado",
    "procedencia_divergente",
    "integridade_divergente",
    "xlsx_invalido",
    "relatorio_invalido",
    "falha_ao_publicar",
    "erro_inesperado",
]

FAILURE_CODES = [c.value for c in Code] + LOCAL_CODES

ISO_RE = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})"
RUN_RE = r"\d{8}T\d{6}Z-[0-9a-f]{6}"
TAB_RE = r"aba_\d{2}"
UNKNOWN_RE = r"desconhecido_\d{2}"
DATE_RE = r"\d{4}-\d{2}-\d{2}"
MAX_COUNT = 1_000_000


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def iso_from_text(text: str | None) -> str | None:
    """Normaliza timestamp do manifesto/Drive para ISO 8601 em UTC; inválido vira None."""
    if not text:
        return None
    try:
        return iso(datetime.fromisoformat(text))
    except ValueError:
        return None


# --------------------------------------------------------------------------- esquema

INT, BOOL, PCT, NUM, NONE = ("int",), ("bool",), ("pct",), ("num",), ("none",)


def _obj(**fields: tuple) -> tuple:
    return ("obj", fields)


def _enum(values: object) -> tuple:
    return ("enum", frozenset(values))  # type: ignore[arg-type]


def _opt(schema: tuple) -> tuple:
    return ("union", (NONE, schema))


GAP = ("union", (INT, _enum(GAP_TEXT)))
CATS = _obj(**{c: INT for c in CATEGORIES})
COUNTS = {
    "total": INT,
    "status_ausente": INT,
    "status_nao_mapeado": INT,
    "concluidos": INT,
    "cancelados": INT,
    "nao_encerrados_reconhecidos": INT,
    "visiveis": INT,
    "ocultos": INT,
}
TAB_BASE = {
    "alias": ("re", TAB_RE),
    "setor": _opt(_enum(SECTORS)),
    "vinculo_setor": _enum(["nome_confere", "nao_vinculado"]),
}
TAB_PENDING = _obj(**TAB_BASE, situacao=_enum(["schema_pending"]), motivo=_enum(PENDING_REASONS))
TAB_OK_V10 = _obj(
    **TAB_BASE,
    **COUNTS,
    situacao=_enum(["interpretada"]),
    motivo=NONE,
    campos_ausentes=("list", _enum(FIELD_LABEL.values())),
    campos_ambiguos=("list", _enum(FIELD_LABEL.values())),
    campos_ignorados_nomeados=("list", _enum(NAMED_IGNORED_V10)),
    campos_ignorados_outros=INT,
    linhas_desconsideradas=_obj(so_campos_ignorados=INT, vazias=INT, totais_subtotais=INT),
    categorias=CATS,
    nao_mapeados_por_alias=("map", UNKNOWN_RE, INT),
    sem_tarefa=GAP,
    sem_responsavel=GAP,
    sem_data_de_inicio=GAP,
    sinais_de_conferencia=_obj(**{k: INT for k in SIGNAL_KEYS}),
    status_reconhecido_pct=PCT,
    reconciliacoes=_obj(
        categorias_ausentes_nao_mapeados=BOOL,
        encerrados_nao_encerrados_ausentes_nao_mapeados=BOOL,
        visiveis_ocultos=BOOL,
    ),
)
AGG_V10 = _obj(
    **COUNTS,
    categorias=CATS,
    status_reconhecido_pct_do_total=PCT,
    status_reconhecido_pct_dos_preenchidos=PCT,
)
REPORT_SCHEMA_V10 = _obj(
    formato=_enum([REPORT_FORMAT]),
    versao=_enum([LEGACY_REPORT_VERSION]),
    fonte=_obj(alias=("re", ALIAS_RE.pattern), familia=_enum(FAMILIES)),
    captura=_obj(
        run_id=("re", RUN_RE),
        capturada_em=("re", ISO_RE),
        drive_modified_time=_opt(("re", ISO_RE)),
        drive_version=_opt(("re", r"\d{1,20}")),
    ),
    gerado_em=("re", ISO_RE),
    cobertura=_obj(
        qualidade=_enum(["completa", "parcial"]),
        abas_total=INT,
        abas_interpretadas=("list", ("re", TAB_RE)),
        abas_pendentes=("list", ("re", TAB_RE)),
        abas_sem_vinculo_de_setor=("list", ("re", TAB_RE)),
        status_reconhecido_pct_do_total=PCT,
        status_reconhecido_pct_dos_preenchidos=PCT,
        reconciliacoes_ok=BOOL,
    ),
    agregado=AGG_V10,
    abas=("list", ("union", (TAB_OK_V10, TAB_PENDING))),
)

# --- v1.1: indicadores de datas (só contagens e estatísticas; nenhuma data individual)
COV_GROUP = _obj(registros=INT, **{k: INT for k in COVERAGE_KEYS})
COVERAGE = _opt(_obj(**{g: COV_GROUP for g in GROUPS}))
AGE = _opt(_obj(base=INT, calculaveis=INT, faixas=_obj(**{k: INT for k, _ in AGE_BANDS})))
DURATION = _opt(_obj(base=INT, calculaveis=INT, media_dias=_opt(NUM), mediana_dias=_opt(NUM)))
DATE_SIGNALS = _obj(**{k: _opt(INT) for k in SIGNALS})
DUE_KEYS = ["validos", "ausentes", "invalidos", *DUE_BUCKETS]
PRENOTATION = _opt(
    _obj(
        base=INT,
        data_prenotacao=_opt(
            _obj(
                **{k: INT for k in COVERAGE_KEYS},
                media_dias_desde=_opt(NUM),
                mediana_dias_desde=_opt(NUM),
            )
        ),
        vencimento_informado=_opt(_obj(**{k: INT for k in DUE_KEYS})),
    )
)
DATES_COMMON = {
    "cobertura": _obj(cadastro=COVERAGE, encerramento=COVERAGE),
    "idade_carteira": AGE,
    "duracao_conclusao": DURATION,
    "duracao_cancelamento": DURATION,
    "sinais": DATE_SIGNALS,
}
DATES_TAB = _obj(
    campos=_obj(**{f: _enum(FIELD_STATES) for f in DATE_FIELDS}),
    **DATES_COMMON,
    prenotacao=PRENOTATION,
)
DATES_AGG = _obj(
    abas_com_cadastro=("list", ("re", TAB_RE)),
    abas_com_encerramento=("list", ("re", TAB_RE)),
    **DATES_COMMON,
)
TAB_OK = _obj(
    **{
        **TAB_OK_V10[1],
        "campos_ignorados_nomeados": ("list", _enum(NAMED_IGNORED)),
        "datas": DATES_TAB,
    }
)
REPORT_SCHEMA = _obj(
    **{
        **REPORT_SCHEMA_V10[1],
        "versao": _enum([REPORT_VERSION]),
        "referencia_temporal": _obj(
            data=("re", DATE_RE),
            fuso=_enum([TIMEZONE_NAME]),
            base=_enum(["data_civil_da_captura"]),
        ),
        "agregado": _obj(**AGG_V10[1], datas=DATES_AGG),
        "abas": ("list", ("union", (TAB_OK, TAB_PENDING))),
    }
)
ATTEMPT_SCHEMA = _obj(
    formato=_enum([ATTEMPT_FORMAT]),
    versao=_enum([ATTEMPT_VERSION]),
    tentativa_em=("re", ISO_RE),
    resultado=_enum(["sucesso", "falha"]),
    etapa=_opt(_enum(STAGES)),
    codigo=_opt(_enum(FAILURE_CODES)),
    run_id=_opt(("re", RUN_RE)),
)


class ReportRejected(Exception):
    """Mensagem com o caminho no esquema, nunca com o valor rejeitado."""


def _check(value: object, schema: tuple, path: str) -> None:
    kind = schema[0]
    if kind == "obj":
        if not isinstance(value, dict) or set(value) != set(schema[1]):
            raise ReportRejected(f"{path} (chaves)")
        for key, sub in schema[1].items():
            _check(value[key], sub, f"{path}.{key}")
        return
    if kind == "list":
        if not isinstance(value, list):
            raise ReportRejected(path)
        for i, item in enumerate(value):
            _check(item, schema[1], f"{path}[{i}]")
        return
    if kind == "map":
        if not isinstance(value, dict):
            raise ReportRejected(path)
        for key, item in value.items():
            if not (isinstance(key, str) and re.fullmatch(schema[1], key)):
                raise ReportRejected(f"{path}.<chave>")
            _check(item, schema[2], f"{path}.<valor>")
        return
    if kind == "union":
        for option in schema[1]:
            try:
                _check(value, option, path)
                return
            except ReportRejected:
                continue
        raise ReportRejected(path)
    ok = {
        "int": lambda v: isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= MAX_COUNT,
        "num": lambda v: (
            isinstance(v, int | float)
            and not isinstance(v, bool)
            and math.isfinite(v)
            and 0 <= v <= MAX_COUNT
        ),
        "bool": lambda v: isinstance(v, bool),
        "pct": lambda v: (
            v is None or (isinstance(v, int | float) and not isinstance(v, bool) and 0 <= v <= 100)
        ),
        "none": lambda v: v is None,
        "enum": lambda v: isinstance(v, str) and v in schema[1],
        "re": lambda v: isinstance(v, str) and re.fullmatch(schema[1], v) is not None,
    }[kind](value)
    if not ok:
        raise ReportRejected(path)


def _require(ok: bool, path: str) -> None:
    if not ok:
        raise ReportRejected(f"{path} (reconciliação)")


def _check_dates(datas: dict, groups: dict[str, int], path: str) -> None:
    """Aritmética das métricas de datas contra os totais por grupo de Status."""
    cov = datas["cobertura"]
    for name in ("cadastro", "encerramento"):
        for g, block in (cov[name] or {}).items():
            _require(block["registros"] == groups[g], f"{path}.cobertura.{name}.{g}")
            _require(sum(block[k] for k in COVERAGE_KEYS) == block["registros"], f"{path}.{name}")
    start, end = cov["cadastro"], cov["encerramento"]
    age = datas["idade_carteira"]
    _require((age is None) == (start is None), f"{path}.idade_carteira")
    if age is not None:
        _require(age["base"] == groups["nao_encerrados"], f"{path}.idade_carteira.base")
        _require(
            sum(age["faixas"].values()) == age["calculaveis"] == start["nao_encerrados"]["validas"],
            f"{path}.idade_carteira.faixas",
        )
    for key, g in (("duracao_conclusao", "concluidos"), ("duracao_cancelamento", "cancelados")):
        dur = datas[key]
        _require((dur is None) == (start is None or end is None), f"{path}.{key}")
        if dur is None:
            continue
        _require(dur["base"] == groups[g], f"{path}.{key}.base")
        _require(dur["calculaveis"] <= min(start[g]["validas"], end[g]["validas"]), f"{path}.{key}")
        empty = dur["calculaveis"] == 0
        _require(empty == (dur["media_dias"] is None) == (dur["mediana_dias"] is None), path)
    sig = datas["sinais"]
    _require((sig[SIGNALS[0]] is None) == (start is None or end is None), f"{path}.sinais")
    _require((sig[SIGNALS[1]] is None) == (end is None) == (sig[SIGNALS[2]] is None), path)
    if end is not None:
        open_end = end["nao_encerrados"]
        _require(sig[SIGNALS[1]] == open_end["registros"] - open_end["ausentes"], f"{path}.sinais")
        missing = sum(end[g]["ausentes"] for g in CLOSED_GROUPS)
        _require(sig[SIGNALS[2]] == missing, f"{path}.sinais")


def _check_prenotation(tab: dict, path: str) -> None:
    pren = tab["datas"]["prenotacao"]
    states = tab["datas"]["campos"]
    _require((pren is None) == (tab["setor"] != PRENOTATION_SECTOR), path)
    if pren is None:
        return
    _require(pren["base"] == tab["nao_encerrados_reconhecidos"], f"{path}.base")
    data = pren["data_prenotacao"]
    _require((data is None) == (states["data_prenotacao"] != "identificado"), path)
    if data is not None:
        _require(sum(data[k] for k in COVERAGE_KEYS) == pren["base"], f"{path}.data_prenotacao")
        empty = data["validas"] == 0
        _require(
            empty == (data["media_dias_desde"] is None) == (data["mediana_dias_desde"] is None),
            f"{path}.data_prenotacao",
        )
    due = pren["vencimento_informado"]
    _require((due is None) == (states["vencimento_prenotacao"] != "identificado"), path)
    if due is not None:
        _require(due["validos"] + due["ausentes"] + due["invalidos"] == pren["base"], path)
        _require(sum(due[k] for k in DUE_BUCKETS) == due["validos"], f"{path}.vencimento")


def _groups(item: dict) -> dict[str, int]:
    return {
        "nao_encerrados": item["nao_encerrados_reconhecidos"],
        "concluidos": item["concluidos"],
        "cancelados": item["cancelados"],
        "sem_status_reconhecido": item["status_ausente"] + item["status_nao_mapeado"],
    }


def _sum_blocks(parts: list[dict], keys: list[str]) -> dict:
    return {k: sum(p[k] for p in parts) for k in keys}


def _check_temporal(report: dict) -> None:
    ref = capture_reference(report["captura"]["capturada_em"])
    _require(
        ref is not None and report["referencia_temporal"]["data"] == ref.isoformat(),
        "relatorio.referencia_temporal.data",
    )
    done = [t for t in report["abas"] if t["situacao"] == "interpretada"]
    for i, tab in enumerate(report["abas"]):
        if tab["situacao"] != "interpretada":
            continue
        path = f"relatorio.abas[{i}].datas"
        states, cov = tab["datas"]["campos"], tab["datas"]["cobertura"]
        for f, name in (("data_inicio", "cadastro"), ("data_termino", "encerramento")):
            _require((cov[name] is None) == (states[f] != "identificado"), f"{path}.{name}")
        _check_dates(tab["datas"], _groups(tab), path)
        _check_prenotation(tab, f"{path}.prenotacao")

    # O agregado é a soma das abas que têm o campo; as estatísticas vêm das amostras,
    # que não são gravadas, então aqui só a coerência entre quantidade e presença.
    agg = report["agregado"]["datas"]
    path = "relatorio.agregado.datas"
    for key, name in (("abas_com_cadastro", "cadastro"), ("abas_com_encerramento", "encerramento")):
        parts = [t["datas"]["cobertura"][name] for t in done if t["datas"]["cobertura"][name]]
        listed = [t["alias"] for t in done if t["datas"]["cobertura"][name] is not None]
        _require(agg[key] == listed, f"{path}.{key}")
        expected = (
            {g: _sum_blocks([p[g] for p in parts], ["registros", *COVERAGE_KEYS]) for g in GROUPS}
            if parts
            else None
        )
        _require(agg["cobertura"][name] == expected, f"{path}.cobertura.{name}")
    ages = [t["datas"]["idade_carteira"] for t in done if t["datas"]["idade_carteira"]]
    got = agg["idade_carteira"]
    _require((got is None) == (not ages), f"{path}.idade_carteira")
    if got is not None:
        _require(
            got["faixas"] == _sum_blocks([a["faixas"] for a in ages], [k for k, _ in AGE_BANDS])
            and got["base"] == sum(a["base"] for a in ages)
            and got["calculaveis"] == sum(a["calculaveis"] for a in ages),
            f"{path}.idade_carteira",
        )
    for key in ("duracao_conclusao", "duracao_cancelamento"):
        parts = [t["datas"][key] for t in done if t["datas"][key] is not None]
        dur = agg[key]
        _require((dur is None) == (not parts), f"{path}.{key}")
        if dur is not None:
            _require((dur | _sum_blocks(parts, ["base", "calculaveis"])) == dur, f"{path}.{key}")
            empty = dur["calculaveis"] == 0
            _require(empty == (dur["media_dias"] is None) == (dur["mediana_dias"] is None), path)
    for k in SIGNALS:
        parts = [t["datas"]["sinais"][k] for t in done if t["datas"]["sinais"][k] is not None]
        _require(agg["sinais"][k] == (sum(parts) if parts else None), f"{path}.sinais")


def validate_report(report: object) -> None:
    """Aceita a v1.1 (gravada pelo refresh) e a v1.0 legada (só leitura, sem datas)."""
    version = report.get("versao") if isinstance(report, dict) else None
    if version == LEGACY_REPORT_VERSION:
        _check(report, REPORT_SCHEMA_V10, "relatorio")
        return
    _check(report, REPORT_SCHEMA, "relatorio")
    _check_temporal(report)  # type: ignore[arg-type]


def validate_attempt(attempt: object) -> None:
    _check(attempt, ATTEMPT_SCHEMA, "tentativa")


# --------------------------------------------------------------------------- montagem


def build_report(
    *,
    source_alias: str,
    family: str,
    run_id: str,
    captured_at: str | None,
    drive_modified_time: str | None,
    drive_version: str | None,
    tabs: list[dict],
    reference: date,
    generated_at: datetime,
) -> dict:
    """``tabs`` e ``reference`` vêm da mesma classificação; as amostras por registro
    ficam fora do relatório."""
    agg = aggregate(tabs) | {"datas": aggregate_dates(tabs)}
    done = [t["alias"] for t in tabs if t["situacao"] == "interpretada"]
    pending = [t["alias"] for t in tabs if t["situacao"] != "interpretada"]
    unbound = [t["alias"] for t in tabs if t["vinculo_setor"] != "nome_confere"]
    reconciled = all(
        all(t["reconciliacoes"].values()) for t in tabs if t["situacao"] == "interpretada"
    )
    complete = (
        not pending and not unbound and not agg["status_ausente"] and not agg["status_nao_mapeado"]
    )
    return {
        "formato": REPORT_FORMAT,
        "versao": REPORT_VERSION,
        "fonte": {"alias": source_alias, "familia": family},
        "captura": {
            "run_id": run_id,
            "capturada_em": iso_from_text(captured_at),
            "drive_modified_time": iso_from_text(drive_modified_time),
            "drive_version": drive_version,
        },
        "gerado_em": iso(generated_at),
        "referencia_temporal": {
            "data": reference.isoformat(),
            "fuso": TIMEZONE_NAME,
            "base": "data_civil_da_captura",
        },
        "cobertura": {
            "qualidade": "completa" if complete else "parcial",
            "abas_total": len(tabs),
            "abas_interpretadas": done,
            "abas_pendentes": pending,
            "abas_sem_vinculo_de_setor": unbound,
            "status_reconhecido_pct_do_total": agg["status_reconhecido_pct_do_total"],
            "status_reconhecido_pct_dos_preenchidos": agg["status_reconhecido_pct_dos_preenchidos"],
            "reconciliacoes_ok": reconciled,
        },
        "agregado": agg,
        "abas": [{k: v for k, v in t.items() if k != SAMPLES} for t in tabs],
    }


def build_attempt(
    attempted_at: datetime, ok: bool, stage: str | None, code: str | None, run_id: str | None
) -> dict:
    return {
        "formato": ATTEMPT_FORMAT,
        "versao": ATTEMPT_VERSION,
        "tentativa_em": iso(attempted_at),
        "resultado": "sucesso" if ok else "falha",
        "etapa": stage,
        "codigo": code,
        "run_id": run_id,
    }


# --------------------------------------------------------------------------- Markdown


def _when(text: str | None) -> str:
    if not text:
        return "—"
    dt = datetime.fromisoformat(text)
    local = dt.astimezone(BRT)
    return f"{dt.astimezone(UTC):%Y-%m-%d %H:%M:%S} UTC ({local:%Y-%m-%d %H:%M} UTC−03:00)"


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value}%"


def _yn(flag: bool) -> str:
    return "sim" if flag else "não"


def _row(cells: list[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _sector(tab: dict) -> str:
    return tab["setor"] or f"{tab['alias']} (setor não vinculado)"


def _num(value: float | None) -> str:
    return "—" if value is None else str(value)


STATE_LABEL = {"nao_identificado": "campo não identificado", "ambiguo": "campo ambíguo"}


def _gap(value: int | None) -> str:
    return "campo ausente" if value is None else str(value)


def render_attempt(attempt: dict | None) -> list[str]:
    if attempt is None:
        return ["- última tentativa de atualização: nenhuma registrada"]
    when = _when(attempt["tentativa_em"])
    line = f"- última tentativa de atualização: {when} — {attempt['resultado']}"
    if attempt["resultado"] == "falha":
        line += f" (etapa {attempt['etapa']}, código {attempt['codigo']})"
    return [line]


def attempt_relation(report: dict, attempt: dict | None) -> str:
    """``confirmada``: o registro é o sucesso que publicou este relatório ·
    ``falhou_depois``: falha posterior a ele (o relatório é o preservado) ·
    ``nao_confirmada``: registro ausente, de outro run ou anterior a este relatório — a
    publicação aconteceu, mas o registro dela não foi gravado."""
    if attempt is None:
        return "nao_confirmada"
    if attempt["resultado"] == "sucesso":
        same_run = attempt["run_id"] == report["captura"]["run_id"]
        return "confirmada" if same_run else "nao_confirmada"
    after = datetime.fromisoformat(attempt["tentativa_em"]) > datetime.fromisoformat(
        report["gerado_em"]
    )
    return "falhou_depois" if after else "nao_confirmada"


def _render_dates(report: dict) -> list[str]:
    ref = report["referencia_temporal"]
    done = [t for t in report["abas"] if t["situacao"] == "interpretada"]
    agg = report["agregado"]["datas"]
    total = {"_soma": True, "alias": "", "setor": "**soma das abas com o campo**", "datas": agg}
    rows = [*done, total]

    def name(t: dict) -> str:
        return t["setor"] if t.get("_soma") else _sector(t)

    L = [
        "",
        "## Datas",
        "",
        f"- referência: **{ref['data']}** — data civil da captura em {ref['fuso']};"
        " os indicadores foram calculados no refresh e não mudam com o dia da consulta.",
        "- cadastro = Data de início/Data inicial · encerramento = Data de término/Data final."
        " Status continua classificando: data final preenchida não encerra serviço,"
        " e sem status reconhecido nada entra em carteira ou duração.",
        "",
        "### Cobertura das datas por grupo de Status",
        "",
        "Válidas = data reconhecida até a referência. Futuras, ausentes e inválidas ficam"
        " fora dos cálculos e pedem conferência; não indicam falha do colaborador.",
        "",
        _row(
            [
                "Setor",
                "Campo",
                "Grupo",
                "Registros",
                "Válidas",
                "Ausentes",
                "Inválidas",
                "Futuras",
            ]
        ),
        _row(["---"] * 8),
    ]
    group_label = {
        "nao_encerrados": "não encerrados",
        "concluidos": "concluídos",
        "cancelados": "cancelados",
        "sem_status_reconhecido": "sem status reconhecido",
    }
    for t in rows:
        for field_name, f in (("cadastro", "data_inicio"), ("encerramento", "data_termino")):
            cov = t["datas"]["cobertura"][field_name]
            if cov is None:
                if not t.get("_soma"):
                    label = STATE_LABEL[t["datas"]["campos"][f]]
                    L.append(_row([name(t), field_name, "—", label, *[""] * 4]))
                continue
            for g in GROUPS:
                c = cov[g]
                if c["registros"]:
                    L.append(
                        _row(
                            [
                                name(t),
                                field_name,
                                group_label[g],
                                c["registros"],
                                *[c[k] for k in COVERAGE_KEYS],
                            ]
                        )
                    )
    L += [
        "",
        "### Idade da carteira não encerrada (dias corridos desde o cadastro)",
        "",
        "Faixas gerenciais, sem SLA nem conclusão de atraso; sem histórico de pausas.",
        "",
        _row(
            ["Setor", "Não encerrados", "Idade calculável", "0–7", "8–15", "16–30", "31–60", ">60"]
        ),
        _row(["---"] * 8),
    ]
    for t in rows:
        age = t["datas"]["idade_carteira"]
        if age is None:
            if not t.get("_soma"):
                label = STATE_LABEL[t["datas"]["campos"]["data_inicio"]]
                L.append(_row([name(t), f"cadastro: {label}", *[""] * 6]))
            continue
        L.append(
            _row(
                [
                    name(t),
                    age["base"],
                    age["calculaveis"],
                    *[age["faixas"][k] for k, _ in AGE_BANDS],
                ]
            )
        )
    L += [
        "",
        "### Duração até o encerramento (dias corridos, cadastro → encerramento)",
        "",
        "Só registros com as duas datas válidas, encerramento não anterior ao cadastro"
        " nem posterior à referência. Concluídos e cancelados em separado.",
        "",
        _row(
            [
                "Setor",
                "Concluídos",
                "calculáveis",
                "média",
                "mediana",
                "Cancelados",
                "calculáveis",
                "média",
                "mediana",
            ]
        ),
        _row(["---"] * 9),
    ]
    for t in rows:
        done_d, canc_d = t["datas"]["duracao_conclusao"], t["datas"]["duracao_cancelamento"]
        if done_d is None or canc_d is None:
            if not t.get("_soma"):
                L.append(_row([name(t), "campo de data não identificado ou ambíguo", *[""] * 7]))
            continue
        cells: list[object] = [name(t)]
        for d in (done_d, canc_d):
            cells += [d["base"], d["calculaveis"], _num(d["media_dias"]), _num(d["mediana_dias"])]
        L.append(_row(cells))
    L += [
        "",
        "### Sinais de conferência de datas",
        "",
        _row(
            [
                "Setor",
                "Encerramento antes do cadastro",
                "Não encerrado com data final",
                "Encerrado sem data final",
            ]
        ),
        _row(["---"] * 4),
    ]
    for t in rows:
        s = t["datas"]["sinais"]
        L.append(_row([name(t), *[_gap(s[k]) for k in SIGNALS]]))
    for t in done:
        pren = t["datas"]["prenotacao"]
        if pren is None:
            continue
        L += [
            "",
            f"### Prenotação — {_sector(t)} (não encerrados: {pren['base']})",
            "",
        ]
        data = pren["data_prenotacao"]
        if data is None:
            L.append(
                f"- data da prenotação: {STATE_LABEL[t['datas']['campos']['data_prenotacao']]};"
                " métrica indisponível. PRENOTAÇÃO não é tratada como data."
            )
        else:
            L.append(
                f"- data da prenotação: válidas {data['validas']} · ausentes {data['ausentes']}"
                f" · inválidas {data['invalidas']} · futuras {data['futuras']}"
                f" · dias corridos desde ela: média {_num(data['media_dias_desde'])},"
                f" mediana {_num(data['mediana_dias_desde'])}"
                " (ausência pode significar serviço ainda não prenotado)"
            )
        due = pren["vencimento_informado"]
        if due is None:
            label = STATE_LABEL[t["datas"]["campos"]["vencimento_prenotacao"]]
            L.append(f"- vencimento informado na planilha: {label}; indisponível")
        else:
            L.append(
                f"- vencimento informado na planilha: válidos {due['validos']} · ausentes"
                f" {due['ausentes']} · inválidos {due['invalidos']}"
            )
            L.append(
                f"  - data informada anterior à referência {due['anteriores_a_referencia']}"
                f" · igual à referência {due['na_referencia']}"
                f" · nos próximos 1–7 dias {due['proximos_1_a_7_dias']}"
                f" · além de 7 dias {due['alem_de_7_dias']}"
            )
        L.append(
            "- controle gerencial da fonte: não atesta prazo legal, caducidade"
            " nem perda de prioridade."
        )
    return L


def render_markdown(report: dict | None, attempt: dict | None) -> str:
    """Função pura de objetos JÁ validados."""
    L = ["# Retrato de serviços por setor e status", ""]
    if report is None:
        L += ["Nenhum relatório válido publicado ainda.", "", *render_attempt(attempt), ""]
        return "\n".join(L)
    cap, cob, agg = report["captura"], report["cobertura"], report["agregado"]
    legacy = report["versao"] == LEGACY_REPORT_VERSION
    relation = attempt_relation(report, attempt)
    if relation == "falhou_depois":
        L += [
            "> **A última atualização falhou.** O retrato abaixo é o último válido,"
            " da captura indicada;"
            " ele não reflete a tentativa malsucedida.",
            "",
        ]
    elif relation == "nao_confirmada":
        L += [
            "> **Atualização não confirmada.** O registro da última tentativa está ausente"
            " ou não corresponde a este relatório; o retrato abaixo é válido, mas não se"
            " pode afirmar o resultado da última atualização.",
            "",
        ]
    if legacy:
        L += [
            "> Indicadores de datas indisponíveis: relatório no formato 1.0, anterior à"
            " interpretação das datas. Um refresh bem-sucedido grava o formato 1.1.",
            "",
        ]
    L += [
        f"- captura (leitura da planilha): {_when(cap['capturada_em'])} · run `{cap['run_id']}`",
        f"- modificação informada pelo Drive (sinal técnico): {_when(cap['drive_modified_time'])}",
        f"- relatório gerado: {_when(report['gerado_em'])} · formato {report['versao']}",
        *render_attempt(attempt),
        "- o horário de leitura não indica quando os colaboradores atualizaram os serviços;"
        " gerar o relatório de novo não comprova atualização do serviço.",
        "",
        "## Cobertura",
        "",
        f"- qualidade da fonte: **{cob['qualidade']}** · abas interpretadas"
        f" {len(cob['abas_interpretadas'])}"
        f" de {cob['abas_total']} · pendentes {len(cob['abas_pendentes'])}"
        f" · sem vínculo de setor {len(cob['abas_sem_vinculo_de_setor'])}",
        f"- registros de serviços: **{agg['total']}**"
        " (um serviço pode envolver vários atos; sem deduplicação)",
        f"- status reconhecido: {_pct(cob['status_reconhecido_pct_do_total'])} do total ·"
        f" {_pct(cob['status_reconhecido_pct_dos_preenchidos'])} dos preenchidos ·"
        f" sem status {agg['status_ausente']} · não mapeado {agg['status_nao_mapeado']}",
        f"- reconciliações conferem: {_yn(cob['reconciliacoes_ok'])}",
        "",
        "## Por setor",
        "",
        _row(
            [
                "Setor",
                "Total",
                "Concluídos",
                "Cancelados",
                "Não encerrados",
                "Sem status",
                "Não mapeado",
                "Visíveis",
                "Ocultos",
            ]
        ),
        _row(["---"] * 9),
    ]
    done = [t for t in report["abas"] if t["situacao"] == "interpretada"]
    for t in done:
        L.append(
            _row(
                [
                    _sector(t),
                    t["total"],
                    t["concluidos"],
                    t["cancelados"],
                    t["nao_encerrados_reconhecidos"],
                    t["status_ausente"],
                    t["status_nao_mapeado"],
                    t["visiveis"],
                    t["ocultos"],
                ]
            )
        )
    L.append(
        _row(
            [
                "**soma das abas interpretadas**",
                agg["total"],
                agg["concluidos"],
                agg["cancelados"],
                agg["nao_encerrados_reconhecidos"],
                agg["status_ausente"],
                agg["status_nao_mapeado"],
                agg["visiveis"],
                agg["ocultos"],
            ]
        )
    )
    for t in report["abas"]:
        if t["situacao"] != "interpretada":
            L.append(
                f"\n- {_sector(t)}: pendente — {t['motivo']};"
                " fora das contagens (não equivale a zero serviços)"
            )
    L += [
        "",
        "## Carteira não encerrada (status reconhecido)",
        "",
        _row(["Setor", *[CATEGORY_LABEL[c] for c in OPEN]]),
        _row(["---"] * (len(OPEN) + 1)),
    ]
    for t in done:
        L.append(_row([_sector(t), *[t["categorias"][c] for c in OPEN]]))
    L.append(_row(["**soma**", *[agg["categorias"][c] for c in OPEN]]))
    L += [
        "",
        "## Lacunas e sinais por setor",
        "",
        _row(
            [
                "Setor",
                "Sem Tarefa",
                "Sem Responsável",
                "Sem Data de início",
                "Ocultos fora da regra",
                "Visíveis bloqueados/concluídos",
            ]
        ),
        _row(["---"] * 6),
    ]
    for t in done:
        s = t["sinais_de_conferencia"]
        L.append(
            _row(
                [
                    _sector(t),
                    t["sem_tarefa"],
                    t["sem_responsavel"],
                    t["sem_data_de_inicio"],
                    s[SIGNAL_KEYS[0]],
                    s[SIGNAL_KEYS[1]],
                ]
            )
        )
    if not legacy:
        L += _render_dates(report)
    L += [
        "",
        "## Limites",
        "",
        "- Retrato de uma captura: não é situação em tempo real nem evolução entre dias.",
    ]
    if legacy:
        L += [
            "- Datas não interpretadas: sem idade, prazo, atraso ou produção por período.",
            "- Sinais comparam Status com a regra visual informada;"
            " não indicam erro de filtro ou de colaborador.",
            "- PRENOTAÇÃO, Vencimento da Prenotação e Outorgante ficam fora deste retrato.",
            "",
        ]
    else:
        L += [
            "- Datas em dias corridos até a referência da captura: sem feriados, pausas,"
            " suspensões, SLA ou prazo legal; não medem produção por período nem por pessoa.",
            "- Sinais comparam Status e datas com as regras informadas;"
            " não indicam erro de filtro ou de colaborador.",
            "- PRENOTAÇÃO (pode ser protocolo) e Outorgante ficam fora dos cálculos.",
            "",
        ]
    return "\n".join(L)
