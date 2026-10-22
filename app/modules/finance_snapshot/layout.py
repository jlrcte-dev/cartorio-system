"""Leitura do demonstrativo diário de caixa por âncoras de rótulo (uma aba = um dia).

Modelo calibrado com o operador em CARTORIO-NEW-SOURCES-DISCOVERY-1 (22/10/2026). Só os
rótulos ESTRUTURAIS abaixo entram no código; descrições, nomes, protocolos e valores nunca.
Correspondência é exata depois de ``norm`` (acentos, caixa, espaços e variantes de hífen);
não há busca por palavra solta. Toda âncora precisa ser única na sua região: ausente ou
repetida deixa o bloco indisponível, e nunca se escolhe a primeira ocorrência.

Valores são o que a planilha guardou (número digitado ou resultado gravado de fórmula),
convertidos para ``Decimal`` a partir do texto do XML — nunca via float. Vazio, fórmula sem
resultado, erro, texto e número malformado ficam indisponíveis com motivo; zero digitado
continua zero. Nenhuma fórmula é avaliada.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modules.services_snapshot.dates import VALIDA, cell_date
from app.modules.services_snapshot.xlsx import Cell, Sheet

# -- rótulos aprovados (já normalizados) ---------------------------------------------------
L_MOVIMENTACAO = "movimentacao do caixa dia"
L_CAIXA_INICIAL = "caixa inicial"
L_DESCRICAO = "descricao"
L_ENTRADA = "entrada"
L_SAIDA = "saida"
L_MALOTE = "retirada para malote"
L_SALDO_TEORICO = "saldo (caixa inicial + entrada - saida)"
L_SALDO_CONFERIDO = "saldo do dia em dinheiro no caixa"
L_DIFERENCA = "diferenca"
L_VERIFICACAO = "verificacao do caixa"
L_HORARIO = "horario"
L_VALOR = "valor"
L_CONFERIDO = "conferido"
L_PIX = "transferencias / pix"
L_VALOR_TOTAL = "valor total"
L_TOTAL = "total"
L_REPASSE = "repasse"
L_EMOLUMENTOS = "emolumentos"
# Texto pré-impresso nas linhas de protesto ainda não preenchidas ("Protocolo nº", sem número);
# aprovado pelo operador como rótulo do modelo, não como descrição de registro.
L_PROTOCOLO_MODELO = "protocolo no"
L_A_RECEBER = "valor a receber"
L_COBRADO = "valor cobrado"
# O modelo rotula a linha de total da maquininha assim (22/22 abas na calibração).
L_TOTAL_MAQUININHA = "total em transferencias"
# Sufixo literal do nome da aba → estado. Só o que o operador aprovou.
APPROVED_SUFFIXES = {"feriado": "feriado"}

BLOCKS = ["dinheiro", "verificacao", "pix", "protesto", "maquininha"]
SUM_FIELDS = [
    "dinheiro_entradas",
    "dinheiro_saidas",
    "pix",
    "protesto_recebido",
    "protesto_repassado",
    "maquininha_a_receber",
    "maquininha_cobrado",
]
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
SUM_REASONS = [
    "total_indisponivel",
    "parcela_invalida",
    "parcela_incompleta",
    "parcela_por_formula",
    "subtotal_no_perimetro",
    "perimetro_divergente",
    "bloco_indisponivel",
]

_DASHES = re.compile(r"[‐-―−]")
_NUMBER = re.compile(r"-?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?")
_SUM = re.compile(r"SUM\(\$?([A-Z]{1,3})\$?(\d+):\$?([A-Z]{1,3})\$?(\d+)\)")
_SUBTOTAL = re.compile(r"^(sub ?-?)?(total|totais)\b")
# Marcador de ausência aprovado pelo operador: só hífens ASCII (um ou mais), digitados, sem
# os espaços externos. Outros traços (–, —) e qualquer outro texto continuam inválidos.
_HYPHENS = re.compile(r"-+")
FORMULA_COVERAGE = ["cobre_o_bloco", "omite_linhas", "nao_verificavel"]


def norm(text: str) -> str:
    s = unicodedata.normalize("NFKD", text)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = _DASHES.sub("-", s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def is_hyphen_marker(cell: Cell | None) -> bool:
    text = cell.text() if cell else None  # só texto digitado; resultado de fórmula não conta
    return bool(text and _HYPHENS.fullmatch(text.strip()))


def money(cell: Cell | None) -> tuple[Decimal | None, str | None]:
    """(valor, None) ou (None, motivo). Zero digitado é Decimal('0')."""
    if cell is None:
        return None, "vazio"
    if cell.formula is not None and cell.cache is None:
        return None, "formula_sem_resultado"
    value = cell.value
    if value is None:
        return None, "vazio"
    kind, raw = value
    if kind == "texto":
        return (
            (None, "vazio") if not raw.strip() or is_hyphen_marker(cell) else (None, "nao_numerico")
        )
    if kind == "erro":
        return None, "erro_de_formula"
    if kind != "numero":
        return None, "nao_numerico"
    if cell.date_format:
        return None, "formato_de_data"
    if not _NUMBER.fullmatch(raw.strip()):
        return None, "numero_invalido"  # inclui NaN/Infinity, que Decimal aceitaria
    return Decimal(raw.strip()), None


def canonical(d: Decimal) -> str:
    """Decimal em ponto fixo, sem expoente e sem zeros finais; nunca arredonda."""
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _col_number(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


class BlockError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Grid:
    """Rótulos de texto literal por posição e faixas mescladas de uma aba."""

    def __init__(self, sheet: Sheet) -> None:
        self.sheet = sheet
        self.labels: dict[str, list[tuple[int, int]]] = {}
        for pos, cell in sheet.cells.items():
            text = cell.text()
            if text and text.strip():
                self.labels.setdefault(norm(text), []).append(pos)
        self.merge_of: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        for rng in sheet.merges:
            r1, c1, r2, c2 = rng
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    self.merge_of[(r, c)] = rng

    def cell(self, r: int, c: int) -> Cell | None:
        return self.sheet.cells.get((r, c))

    def one(
        self, label: str, *, rows: range | None = None, cols: range | None = None
    ) -> tuple[int, int]:
        hits = [
            (r, c)
            for r, c in self.labels.get(label, [])
            if (rows is None or r in rows) and (cols is None or c in cols)
        ]
        if not hits:
            raise BlockError("ancora_ausente")
        if len(hits) > 1:
            raise BlockError("ancora_repetida")
        return hits[0]

    def right_of(self, r: int, c: int) -> tuple[int, int]:
        """Célula de valor ao lado do rótulo, respeitando a faixa mesclada do rótulo e a do
        valor (que precisa começar exatamente ali)."""
        rng = self.merge_of.get((r, c))
        if rng and (rng[0], rng[1]) != (r, c):
            raise BlockError("layout_invalido")
        target = (r, (rng[3] if rng else c) + 1)
        trng = self.merge_of.get(target)
        if trng and (trng[0], trng[1]) != target:
            raise BlockError("layout_invalido")
        return target

    def text(self, r: int, c: int) -> str:
        cell = self.cell(r, c)
        return (cell.text() if cell else None) or ""

    def is_text(self, r: int, c: int) -> bool:
        return bool(self.text(r, c).strip())


def _field(value: Decimal | None, reason: str | None) -> dict:
    return {"valor": canonical(value) if value is not None else None, "motivo": reason}


def _unavailable(reason: str) -> dict:
    return {"valor": None, "motivo": reason}


@dataclass
class Column:
    """Parcelas de uma coluna num perímetro de linhas, com o que impede somá-las."""

    values: list[Decimal] = field(default_factory=list)
    nonzero_rows: set[int] = field(default_factory=set)
    filled_rows: set[int] = field(default_factory=set)
    invalid: set[str] = field(default_factory=set)  # motivos das parcelas não numéricas
    formula: bool = False


def _scan(grid: Grid, rows: range, col: int) -> Column:
    out = Column()
    for r in rows:
        cell = grid.cell(r, col)
        value, reason = money(cell)
        if value is not None:
            out.values.append(value)
            out.filled_rows.add(r)
            if value != 0:
                out.nonzero_rows.add(r)
            if cell is not None and cell.formula is not None:
                out.formula = True
        elif reason is not None and reason != "vazio":
            out.invalid.add(reason)
            out.filled_rows.add(r)
    return out


def _sum_range(grid: Grid, total_pos: tuple[int, int]) -> range | None:
    """Linhas somadas pela fórmula do total, se ela for um SUM legível da própria coluna."""
    cell = grid.cell(*total_pos)
    m = _SUM.fullmatch(((cell.formula if cell else None) or "").replace(" ", ""))
    if m and m.group(1) == m.group(3) and _col_number(m.group(1)) == total_pos[1]:
        return range(int(m.group(2)), int(m.group(4)) + 1)
    return None


def formula_coverage(grid: Grid, total_pos: tuple[int, int], area: range) -> str:
    """Se a fórmula do total publicado alcança todas as linhas do bloco. Depende só da
    fórmula, nunca dos valores: linha omitida e vazia continua sendo linha omitida."""
    covered = _sum_range(grid, total_pos)
    if covered is None:
        return "nao_verificavel"
    return "cobre_o_bloco" if all(r in covered for r in area) else "omite_linhas"


def _sum_check(
    grid: Grid,
    column: Column,
    total_pos: tuple[int, int],
    subtotal: bool,
    incomplete: bool,
    *,
    approved_perimeter: bool = False,
) -> dict:
    """Soma das parcelas × total publicado: só diagnóstico, nunca substitui o total.

    ``approved_perimeter``: o operador aprovou o bloco inteiro como perímetro de negócio
    (PIX). A soma cobre todas as linhas do bloco mesmo que a fórmula da fonte omita
    algumas, e o total publicado é comparado com ela como está."""
    total, _ = money(grid.cell(*total_pos))
    if total is None:
        return {"estado": "indisponivel", "motivo": "total_indisponivel"}
    if subtotal:
        return {"estado": "indisponivel", "motivo": "subtotal_no_perimetro"}
    if column.invalid:
        return {"estado": "indisponivel", "motivo": "parcela_invalida"}
    if incomplete:
        return {"estado": "indisponivel", "motivo": "parcela_incompleta"}
    if column.formula:
        return {"estado": "indisponivel", "motivo": "parcela_por_formula"}
    # Sem perímetro aprovado, fórmula legível que deixa de fora linha preenchida do bloco
    # torna a comparação uma comparação de somas diferentes.
    covered = None if approved_perimeter else _sum_range(grid, total_pos)
    if covered is not None and any(r not in covered for r in column.filled_rows):
        return {"estado": "indisponivel", "motivo": "perimetro_divergente"}
    ok = sum(column.values, Decimal(0)) == total
    return {"estado": "confere" if ok else "diverge", "motivo": None}


def _described_rows_without_value(
    grid: Grid,
    rows: range,
    label_cols: range,
    value_cols: list[int],
    template_labels: frozenset[str] = frozenset(),
) -> bool:
    """Linha com descrição e nenhum valor utilizável — célula ausente, vazia, em branco ou
    com o marcador de hífens, indistintamente. Ela não pode sumir da conferência nem a soma
    parcial confirmar o total. Uma só coluna preenchida já é valor; texto inválido e fórmula
    sem resultado têm tratamento próprio (motivo diferente de ``vazio``). Rótulo pré-impresso
    do modelo, em ``template_labels``, não é descrição."""
    for r in rows:
        described = any(
            grid.is_text(r, c)
            and not is_hyphen_marker(grid.cell(r, c))
            and norm(grid.text(r, c)) not in template_labels
            for c in label_cols
        )
        if described and all(money(grid.cell(r, c))[1] == "vazio" for c in value_cols):
            return True
    return False


def _has_subtotal(grid: Grid, rows: range, label_cols: range) -> bool:
    return any(
        _SUBTOTAL.match(norm(grid.text(r, c)))
        for r in rows
        for c in label_cols
        if grid.is_text(r, c)
    )


# -- blocos ---------------------------------------------------------------------------------


@dataclass
class DayRead:
    blocks: dict
    sums: dict
    conferencia: dict
    movement: bool  # algum registro não nulo em dinheiro, malote, PIX, protesto ou cartão
    body_date: date | None
    body_date_state: str  # valida | ausente | invalida | indisponivel


def _dinheiro(grid: Grid) -> tuple[dict, dict, bool]:
    ci = grid.one(L_CAIXA_INICIAL)
    malote = grid.one(L_MALOTE)
    teorico = grid.one(L_SALDO_TEORICO)
    conferido = grid.one(L_SALDO_CONFERIDO)
    diferenca = grid.one(L_DIFERENCA)
    between = range(ci[0] + 1, malote[0])
    ent = grid.one(L_ENTRADA, rows=between)
    sai = grid.one(L_SAIDA, rows=between)
    desc = grid.one(L_DESCRICAO, rows=range(ci[0] + 1, ent[0] + 1))
    header, total_row = ent[0], malote[0] - 1
    if sai[0] != header or not (
        ci[0] < header < total_row < malote[0] < teorico[0] < conferido[0] < diferenca[0]
    ):
        raise BlockError("ordem_invalida")
    area = range(header + 1, total_row)
    ce, cs, cd = ent[1], sai[1], desc[1]

    vci, rci = money(grid.cell(*grid.right_of(*ci)))
    vmal, rmal = money(grid.cell(*grid.right_of(*malote)))
    vteo, rteo = money(grid.cell(*grid.right_of(*teorico)))
    vcon, rcon = money(grid.cell(*grid.right_of(*conferido)))
    vdif, rdif = money(grid.cell(*grid.right_of(*diferenca)))

    # Linha de totais: imediatamente acima do malote e sem descrição; é a linha que o
    # saldo teórico do modelo referencia. Com texto na descrição, a associação não fecha.
    confirmed = not grid.is_text(total_row, cd)
    if confirmed:
        tent = _field(*money(grid.cell(total_row, ce)))
        tsai = _field(*money(grid.cell(total_row, cs)))
    else:
        tent = tsai = _unavailable("total_nao_confirmado")

    col_e, col_s = _scan(grid, area, ce), _scan(grid, area, cs)
    records = len(col_e.nonzero_rows | col_s.nonzero_rows)
    subtotal = _has_subtotal(grid, area, range(cd, cd + 1))
    incomplete = _described_rows_without_value(grid, area, range(cd, cd + 1), [ce, cs])
    sums = {}
    for key, column, c in (("dinheiro_entradas", col_e, ce), ("dinheiro_saidas", col_s, cs)):
        sums[key] = (
            _sum_check(grid, column, (total_row, c), subtotal, incomplete)
            if confirmed
            else {"estado": "indisponivel", "motivo": "total_indisponivel"}
        )

    if rcon == "vazio":
        conf = {"estado": "sem_conferencia", "motivo": None, "sinal": None}
        dif = _unavailable("sem_conferencia")
    elif vcon is None or vteo is None or vdif is None:
        conf = {"estado": "indisponivel", "motivo": rcon or rteo or rdif, "sinal": None}
        dif = _unavailable("conferencia_indisponivel")
    else:
        conf = {"estado": "valida", "motivo": None, "sinal": "zero" if vdif == 0 else "nao_zero"}
        dif = _field(vdif, None)

    block = {
        "localizado": True,
        "motivo": None,
        "caixa_inicial": _field(vci, rci),
        "registros": records,
        "total_entradas": tent,
        "total_saidas": tsai,
        "retirada_malote": _field(vmal, rmal),
        "saldo_teorico": _field(vteo, rteo),
        "saldo_conferido": _field(vcon, rcon),
        "diferenca": dif,
    }
    moved = bool(records) or (vmal is not None and vmal != 0)
    return block, {"sums": sums, "conferencia": conf}, moved


def _pix(grid: Grid) -> tuple[dict, dict, bool, int, int]:
    title = grid.one(L_PIX)
    vpos = grid.right_of(*title)
    if not grid.is_text(*vpos) or norm(grid.text(*vpos)) != L_VALOR_TOTAL:
        raise BlockError("layout_invalido")
    total = grid.one(L_TOTAL, rows=range(title[0] + 1, 10**6), cols=range(title[1], title[1] + 1))
    area = range(title[0] + 1, total[0])
    col = _scan(grid, area, vpos[1])
    subtotal = _has_subtotal(grid, area, range(title[1], title[1] + 1))
    incomplete = _described_rows_without_value(grid, area, range(title[1], title[1] + 1), [vpos[1]])
    block = {
        "localizado": True,
        "motivo": None,
        "total": _field(*money(grid.cell(total[0], vpos[1]))),
        "formula_do_total": formula_coverage(grid, (total[0], vpos[1]), area),
    }
    total_pos = (total[0], vpos[1])
    sums = {"pix": _sum_check(grid, col, total_pos, subtotal, incomplete, approved_perimeter=True)}
    return block, sums, bool(col.nonzero_rows), title[0], vpos[1]


def _protesto(grid: Grid, pix_row: int, pix_value_col: int) -> tuple[dict, dict, bool]:
    # Bloco identificado pelos cabeçalhos exatos na linha do título do PIX (modelo).
    row = range(pix_row, pix_row + 1)
    rep = grid.one(L_REPASSE, rows=row)
    emo = grid.one(L_EMOLUMENTOS, rows=row)
    rec = grid.one(L_VALOR_TOTAL, rows=row, cols=range(rep[1] - 1, rep[1]))
    if emo[1] != rep[1] + 1 or rec[1] <= pix_value_col + 1:
        raise BlockError("layout_invalido")
    label_cols = range(pix_value_col + 1, rec[1])
    total = grid.one(L_TOTAL, rows=range(pix_row + 1, 10**6), cols=label_cols)
    area = range(pix_row + 1, total[0])
    col_rec, col_rep = _scan(grid, area, rec[1]), _scan(grid, area, rep[1])
    records = len(col_rec.nonzero_rows | col_rep.nonzero_rows)
    subtotal = _has_subtotal(grid, area, label_cols)
    incomplete = _described_rows_without_value(
        grid, area, label_cols, [rec[1], rep[1]], frozenset({L_PROTOCOLO_MODELO})
    )
    block = {
        "localizado": True,
        "motivo": None,
        "registros": records,
        "total_recebido": _field(*money(grid.cell(total[0], rec[1]))),
        "total_repassado": _field(*money(grid.cell(total[0], rep[1]))),
        "total_emolumentos": _field(*money(grid.cell(total[0], emo[1]))),
    }
    sums = {
        "protesto_recebido": _sum_check(grid, col_rec, (total[0], rec[1]), subtotal, incomplete),
        "protesto_repassado": _sum_check(grid, col_rep, (total[0], rep[1]), subtotal, incomplete),
    }
    return block, sums, bool(records)


def _maquininha(grid: Grid) -> tuple[dict, dict, bool]:
    rec = grid.one(L_A_RECEBER)
    cob = grid.one(L_COBRADO, rows=range(rec[0], rec[0] + 1))
    if cob[1] != rec[1] + 1 or rec[1] < 2:
        raise BlockError("layout_invalido")
    label_col = rec[1] - 1
    total = grid.one(
        L_TOTAL_MAQUININHA, rows=range(rec[0] + 1, 10**6), cols=range(label_col, label_col + 1)
    )
    area = range(rec[0] + 1, total[0])
    col_rec, col_cob = _scan(grid, area, rec[1]), _scan(grid, area, cob[1])
    subtotal = _has_subtotal(grid, area, range(label_col, label_col + 1))
    incomplete = _described_rows_without_value(
        grid, area, range(label_col, label_col + 1), [rec[1], cob[1]]
    )
    block = {
        "localizado": True,
        "motivo": None,
        "total_a_receber": _field(*money(grid.cell(total[0], rec[1]))),
        "total_cobrado": _field(*money(grid.cell(total[0], cob[1]))),
    }
    sums = {
        "maquininha_a_receber": _sum_check(grid, col_rec, (total[0], rec[1]), subtotal, incomplete),
        "maquininha_cobrado": _sum_check(grid, col_cob, (total[0], cob[1]), subtotal, incomplete),
    }
    return block, sums, bool(col_rec.nonzero_rows | col_cob.nonzero_rows)


def _verificacao(grid: Grid, pix_row: int | None) -> dict:
    if pix_row is None:
        raise BlockError("limite_indefinido")
    title = grid.one(L_VERIFICACAO)
    header = range(title[0] + 1, title[0] + 2)
    hor = grid.one(L_HORARIO, rows=header)
    val = grid.one(L_VALOR, rows=header)
    con = grid.one(L_CONFERIDO, rows=header)
    if not hor[1] < val[1] < con[1] or pix_row <= title[0] + 1:
        raise BlockError("layout_invalido")
    done = partial = 0
    for r in range(title[0] + 2, pix_row):
        h = grid.cell(r, hor[1])
        has_h = h is not None and h.filled()
        v, vreason = money(grid.cell(r, val[1]))
        has_c = grid.is_text(r, con[1])
        if has_h and v is not None and has_c:
            done += 1
        elif has_h or has_c or vreason != "vazio":
            partial += 1
    return {"localizado": True, "motivo": None, "preenchidas": done, "incompletas": partial}


BLOCK_FIELDS = {
    "dinheiro": [
        "caixa_inicial",
        "total_entradas",
        "total_saidas",
        "retirada_malote",
        "saldo_teorico",
        "saldo_conferido",
        "diferenca",
    ],
    "verificacao": [],
    "pix": ["total"],
    "protesto": ["total_recebido", "total_repassado", "total_emolumentos"],
    "maquininha": ["total_a_receber", "total_cobrado"],
}
BLOCK_COUNTS = {
    "dinheiro": ["registros"],
    "verificacao": ["preenchidas", "incompletas"],
    "pix": [],
    "protesto": ["registros"],
    "maquininha": [],
}


# Ordem canônica das chaves de cada bloco no relatório (o validador exige exatamente esta).
BLOCK_KEYS = {
    "dinheiro": [
        "caixa_inicial",
        "registros",
        "total_entradas",
        "total_saidas",
        "retirada_malote",
        "saldo_teorico",
        "saldo_conferido",
        "diferenca",
    ],
    "verificacao": ["preenchidas", "incompletas"],
    "pix": ["total", "formula_do_total"],
    "protesto": ["registros", "total_recebido", "total_repassado", "total_emolumentos"],
    "maquininha": ["total_a_receber", "total_cobrado"],
}


# Códigos estruturais por bloco (não monetários); null quando o bloco não é localizado.
BLOCK_FLAGS = {"pix": {"formula_do_total": FORMULA_COVERAGE}}


def _failed_block(name: str, reason: str) -> dict:
    out: dict = {"localizado": False, "motivo": reason}
    for key in BLOCK_KEYS[name]:
        plain = key in BLOCK_COUNTS[name] or key in BLOCK_FLAGS.get(name, {})
        out[key] = None if plain else _unavailable("bloco_indisponivel")
    return out


def read_day(sheet: Sheet) -> DayRead:
    grid = Grid(sheet)
    blocks: dict = {}
    sums: dict = {k: {"estado": "indisponivel", "motivo": "bloco_indisponivel"} for k in SUM_FIELDS}
    moved = False
    conferencia = {"estado": "indisponivel", "motivo": "bloco_indisponivel", "sinal": None}

    try:
        blocks["dinheiro"], extra, m = _dinheiro(grid)
        sums.update(extra["sums"])
        conferencia = extra["conferencia"]
        moved |= m
    except BlockError as exc:
        blocks["dinheiro"] = _failed_block("dinheiro", exc.reason)

    pix_row = pix_col = None
    try:
        blocks["pix"], s, m, pix_row, pix_col = _pix(grid)
        sums.update(s)
        moved |= m
    except BlockError as exc:
        blocks["pix"] = _failed_block("pix", exc.reason)

    try:
        if pix_row is None or pix_col is None:
            raise BlockError("limite_indefinido")
        blocks["protesto"], s, m = _protesto(grid, pix_row, pix_col)
        sums.update(s)
        moved |= m
    except BlockError as exc:
        blocks["protesto"] = _failed_block("protesto", exc.reason)

    try:
        blocks["maquininha"], s, m = _maquininha(grid)
        sums.update(s)
        moved |= m
    except BlockError as exc:
        blocks["maquininha"] = _failed_block("maquininha", exc.reason)

    try:
        blocks["verificacao"] = _verificacao(grid, pix_row)
    except BlockError as exc:
        blocks["verificacao"] = _failed_block("verificacao", exc.reason)

    body_state, body = "indisponivel", None
    try:
        mov = grid.one(L_MOVIMENTACAO)
        body_state, body = cell_date(grid.cell(*grid.right_of(*mov)), sheet.date1904)
    except BlockError:
        pass

    return DayRead(
        blocks={k: blocks[k] for k in BLOCKS},
        sums=sums,
        conferencia=conferencia,
        movement=moved,
        body_date=body if body_state == VALIDA else None,
        body_date_state=body_state,
    )
