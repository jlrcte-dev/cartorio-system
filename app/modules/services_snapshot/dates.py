"""Datas civis dos campos de data identificados e indicadores temporais agregados.

Conversão — só em campos de data reconhecidos pelo cabeçalho; nada é adivinhado:

- número serial em célula cujo estilo declara formato de data, no sistema 1900 ou 1904
  do pacote; a fração (hora) é descartada, sem conversão de fuso;
- texto ``d/m/aaaa`` (ano com quatro dígitos) ou ``aaaa-mm-dd``.

Todo o resto é **inválido**: número sem formato de data (pode ser protocolo), serial
menor que 1 (o "00/01/1900" do sistema 1900 e a origem do 1904 são sentinelas), o
29/02/1900 fictício, texto livre, booleano, erro e fórmula sem resultado gravado. Célula
vazia é **ausência**, nunca serial zero. Inválido não é corrigido nem trocado por hoje.

Referência: data civil da captura em America/Sao_Paulo (UTC−03:00 fixo; sem horário de
verão desde 2019 e sem base IANA garantida no ambiente). Idade e duração em dias
corridos, sem pausas, feriados, suspensões ou prazos legais.
"""

from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from app.modules.services_snapshot.xlsx import Cell

BRT = timezone(timedelta(hours=-3), "UTC−03:00")
TIMEZONE_NAME = "America/Sao_Paulo"

AUSENTE, INVALIDA, VALIDA = "ausente", "invalida", "valida"
_BR_RE = re.compile(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})")
_ISO_RE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")

DATE_FIELDS = ["data_inicio", "data_termino", "data_prenotacao", "vencimento_prenotacao"]
FIELD_STATES = ["identificado", "nao_identificado", "ambiguo"]
GROUPS = ["nao_encerrados", "concluidos", "cancelados", "sem_status_reconhecido"]
CLOSED_GROUPS = ["concluidos", "cancelados"]
COVERAGE_KEYS = ["validas", "ausentes", "invalidas", "futuras"]
AGE_BANDS = [("0_7", 7), ("8_15", 15), ("16_30", 30), ("31_60", 60), ("mais_de_60", None)]
SIGNALS = [
    "encerramento_anterior_ao_cadastro",
    "nao_encerrado_com_data_final",
    "encerrado_sem_data_final",
]
DUE_BUCKETS = [
    "anteriores_a_referencia",
    "na_referencia",
    "proximos_1_a_7_dias",
    "alem_de_7_dias",
]
SAMPLES = "_amostras"  # durações por registro: só em memória, nunca no relatório


def capture_reference(captured_at: str | None) -> date | None:
    if not captured_at:
        return None
    try:
        return datetime.fromisoformat(captured_at).astimezone(BRT).date()
    except ValueError:
        return None


def from_serial(raw: str, date1904: bool) -> date | None:
    try:
        serial = float(raw)
    except ValueError:
        return None
    if not math.isfinite(serial) or serial < 1:
        return None
    days = int(serial)
    try:
        if date1904:
            return date(1904, 1, 1) + timedelta(days=days)
        if days == 60:  # 29/02/1900 não existe; o Excel herdou o erro do Lotus 1-2-3
            return None
        return date(1899, 12, 31 if days < 60 else 30) + timedelta(days=days)
    except OverflowError:
        return None


def from_text(text: str) -> date | None:
    s = text.strip()
    if m := _BR_RE.fullmatch(s):
        d, mo, y = map(int, m.groups())
    elif m := _ISO_RE.fullmatch(s):
        y, mo, d = map(int, m.groups())
    else:
        return None
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def cell_date(cell: Cell | None, date1904: bool) -> tuple[str, date | None]:
    if cell is None or not cell.filled():
        return AUSENTE, None
    value, parsed = cell.value, None
    if value is not None:
        kind, raw = value
        if kind == "numero" and cell.date_format:
            parsed = from_serial(raw, date1904)
        elif kind == "texto":
            parsed = from_text(raw)
    return (VALIDA, parsed) if parsed else (INVALIDA, None)


def stats(values: list[int]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return round(statistics.fmean(values), 1), statistics.median(values)


def _bands(ages: list[int]) -> dict[str, int]:
    out = Counter()
    for age in ages:
        out[next(k for k, top in AGE_BANDS if top is None or age <= top)] += 1
    return {k: out[k] for k, _ in AGE_BANDS}


def _duration(base: int, values: list[int]) -> dict:
    mean, median = stats(values)
    return {"base": base, "calculaveis": len(values), "media_dias": mean, "mediana_dias": median}


class TabDates:
    """Acumula, linha a linha, os sinais de datas de uma aba interpretada."""

    def __init__(
        self,
        reference: date,
        date1904: bool,
        columns: dict[str, int],
        states: dict[str, str],
        *,
        prenotation: bool,
    ) -> None:
        self.reference = reference
        self.date1904 = date1904
        self.columns = columns  # só campos identificados de forma inequívoca
        self.states = states
        self.prenotation = prenotation
        self.groups: Counter[str] = Counter()
        self.coverage = {n: {g: Counter() for g in GROUPS} for n in ("cadastro", "encerramento")}
        self.ages: list[int] = []
        self.durations: dict[str, list[int]] = {g: [] for g in CLOSED_GROUPS}
        self.signals: Counter[str] = Counter()
        self.pren: Counter[str] = Counter()
        self.pren_days: list[int] = []
        self.due: Counter[str] = Counter()

    def _read(self, field_key: str, cells: dict[int, Cell]) -> tuple[str, date | None] | None:
        col = self.columns.get(field_key)
        return None if col is None else cell_date(cells.get(col), self.date1904)

    def _coverage_key(self, got: tuple[str, date | None]) -> str:
        state, d = got
        if state == VALIDA:
            return "futuras" if d > self.reference else "validas"  # type: ignore[operator]
        return "ausentes" if state == AUSENTE else "invalidas"

    def add(self, group: str, cells: dict[int, Cell]) -> None:
        ref = self.reference
        self.groups[group] += 1
        start = self._read("data_inicio", cells)
        end = self._read("data_termino", cells)
        for name, got in (("cadastro", start), ("encerramento", end)):
            if got is not None:
                self.coverage[name][group][self._coverage_key(got)] += 1
        start_date = start[1] if start else None
        end_day = end[1] if end else None
        start_day = start_date if start_date and start_date <= ref else None  # não futuro
        if group == "nao_encerrados" and start_day:
            self.ages.append((ref - start_day).days)
        if start_date and end_day and end_day < start_date:
            self.signals[SIGNALS[0]] += 1
        if end is not None:
            if group == "nao_encerrados" and end[0] != AUSENTE:
                self.signals[SIGNALS[1]] += 1
            if group in CLOSED_GROUPS and end[0] == AUSENTE:
                self.signals[SIGNALS[2]] += 1
        if group in CLOSED_GROUPS and start_day and end_day and start_day <= end_day <= ref:
            self.durations[group].append((end_day - start_day).days)
        if self.prenotation and group == "nao_encerrados":
            self._add_prenotation(cells)

    def _add_prenotation(self, cells: dict[int, Cell]) -> None:
        ref = self.reference
        if (got := self._read("data_prenotacao", cells)) is not None:
            self.pren[self._coverage_key(got)] += 1
            if got[1] and got[1] <= ref:
                self.pren_days.append((ref - got[1]).days)
        if (got := self._read("vencimento_prenotacao", cells)) is not None:
            state, d = got
            if d is None:
                self.due["ausentes" if state == AUSENTE else "invalidos"] += 1
                return
            delta = (d - ref).days
            self.due["validos"] += 1
            if delta < 0:
                self.due["anteriores_a_referencia"] += 1
            elif delta == 0:
                self.due["na_referencia"] += 1
            elif delta <= 7:
                self.due["proximos_1_a_7_dias"] += 1
            else:
                self.due["alem_de_7_dias"] += 1

    def _has(self, field_key: str) -> bool:
        return field_key in self.columns

    def to_dict(self) -> dict:
        has_start, has_end = self._has("data_inicio"), self._has("data_termino")
        g = self.groups

        def cov(name: str, available: bool) -> dict | None:
            if not available:
                return None
            return {
                grp: {
                    "registros": g[grp],
                    **{k: self.coverage[name][grp][k] for k in COVERAGE_KEYS},
                }
                for grp in GROUPS
            }

        both = has_start and has_end
        return {
            "campos": dict(self.states),
            "cobertura": {
                "cadastro": cov("cadastro", has_start),
                "encerramento": cov("encerramento", has_end),
            },
            "idade_carteira": (
                {
                    "base": g["nao_encerrados"],
                    "calculaveis": len(self.ages),
                    "faixas": _bands(self.ages),
                }
                if has_start
                else None
            ),
            "duracao_conclusao": _duration(g["concluidos"], self.durations["concluidos"])
            if both
            else None,
            "duracao_cancelamento": _duration(g["cancelados"], self.durations["cancelados"])
            if both
            else None,
            "sinais": {
                SIGNALS[0]: self.signals[SIGNALS[0]] if both else None,
                SIGNALS[1]: self.signals[SIGNALS[1]] if has_end else None,
                SIGNALS[2]: self.signals[SIGNALS[2]] if has_end else None,
            },
            "prenotacao": self._prenotation_dict() if self.prenotation else None,
        }

    def _prenotation_dict(self) -> dict:
        pren = None
        if self._has("data_prenotacao"):
            mean, median = stats(self.pren_days)
            pren = {
                **{k: self.pren[k] for k in COVERAGE_KEYS},
                "media_dias_desde": mean,
                "mediana_dias_desde": median,
            }
        due = None
        if self._has("vencimento_prenotacao"):
            due = {k: self.due[k] for k in ["validos", "ausentes", "invalidos", *DUE_BUCKETS]}
        return {
            "base": self.groups["nao_encerrados"],
            "data_prenotacao": pren,
            "vencimento_informado": due,
        }

    def samples(self) -> dict[str, list[int]]:
        return {
            "duracao_conclusao": list(self.durations["concluidos"]),
            "duracao_cancelamento": list(self.durations["cancelados"]),
        }


def aggregate_dates(tabs: list[dict]) -> dict:
    """Soma das abas interpretadas que têm o campo; durações agregadas pelas amostras."""
    done = [t for t in tabs if t["situacao"] == "interpretada"]
    with_start = [t for t in done if t["datas"]["cobertura"]["cadastro"] is not None]
    with_end = [t for t in done if t["datas"]["cobertura"]["encerramento"] is not None]

    def cov(name: str, group_tabs: list[dict]) -> dict | None:
        if not group_tabs:
            return None
        return {
            grp: {
                k: sum(t["datas"]["cobertura"][name][grp][k] for t in group_tabs)
                for k in ["registros", *COVERAGE_KEYS]
            }
            for grp in GROUPS
        }

    ages = [t["datas"]["idade_carteira"] for t in with_start]
    age = None
    if ages:
        age = {
            "base": sum(a["base"] for a in ages),
            "calculaveis": sum(a["calculaveis"] for a in ages),
            "faixas": {k: sum(a["faixas"][k] for a in ages) for k, _ in AGE_BANDS},
        }

    def duration(key: str) -> dict | None:
        parts = [t for t in done if t["datas"][key] is not None]
        if not parts:
            return None
        values = [v for t in parts for v in t[SAMPLES][key]]
        return _duration(sum(t["datas"][key]["base"] for t in parts), values)

    def signal(key: str) -> int | None:
        values = [t["datas"]["sinais"][key] for t in done if t["datas"]["sinais"][key] is not None]
        return sum(values) if values else None

    return {
        "abas_com_cadastro": [t["alias"] for t in with_start],
        "abas_com_encerramento": [t["alias"] for t in with_end],
        "cobertura": {
            "cadastro": cov("cadastro", with_start),
            "encerramento": cov("encerramento", with_end),
        },
        "idade_carteira": age,
        "duracao_conclusao": duration("duracao_conclusao"),
        "duracao_cancelamento": duration("duracao_cancelamento"),
        "sinais": {k: signal(k) for k in SIGNALS},
    }
