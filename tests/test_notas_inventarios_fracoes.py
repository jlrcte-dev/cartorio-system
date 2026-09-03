"""Testes da fração ideal de ponta a ponta — ADR-010.

Sprint **NOTAS-INVENTARIO-FRACOES-1**.

Cobrem o contrato de entrada da fração, a regra de coerência fração ×
percentual, o transporte pelo calculador, a renderização nos artefatos e —
principalmente — a **classe do problema histórico** que forçou a rota manual em
2026-07-09.

Nenhum valor aqui reproduz o caso real: o cenário é sintético e reproduz apenas
a classe do problema (quinhões de 1/16 e 1/32 num único bem).
"""

from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from app.modules.notas.inventarios.application.calculator import InventarioCalculator
from app.modules.notas.inventarios.application.renderer import (
    render_minuta_markdown,
    render_resumo_markdown,
)
from app.modules.notas.inventarios.application.validator import InventarioValidator
from app.modules.notas.inventarios.domain.errors import InventarioInputError
from app.modules.notas.inventarios.domain.models import (
    BENEFICIARIO_MEEIRO,
    Bem,
    Distribuicao,
    Herdeiro,
    Inventario,
    TipoBem,
)
from app.modules.notas.inventarios.infrastructure.loaders import load_inventario
from app.modules.notas.inventarios.interfaces.schemas import parse_inventario_input

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXEMPLO_FRACOES = (
    PROJECT_ROOT
    / "app"
    / "modules"
    / "notas"
    / "inventarios"
    / "examples"
    / "inventario_fracoes.yaml"
)


def _entrada_minima(fracao: str | None, percentual: str) -> dict[str, object]:
    """Inventário de um bem e um herdeiro, para exercitar a fração isoladamente."""

    return {
        "tipo_ato": "inventario_extrajudicial",
        "possui_meeiro": False,
        "percentual_meacao": "0",
        "patrimonio_total": "1000.00",
        "herdeiros": [{"id": "HERDEIRO_1", "percentual_heranca": "100"}],
        "bens": [
            {
                "id": "BEM_1",
                "tipo": "outro",
                "descricao_generica": "Bem genérico",
                "valor": "1000.00",
                "distribuicao": [
                    {"beneficiario": "HERDEIRO_1", "percentual": percentual}
                    | ({"fracao_ideal": fracao} if fracao is not None else {})
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Contrato de entrada da fração
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fracao", ["1/32", "1/16", "1/2", "3/4", "1/1"])
def test_fracao_valida_e_aceita(fracao: str) -> None:
    inv = parse_inventario_input(_entrada_minima(fracao, "100"))
    assert inv.bens[0].distribuicao[0].fracao_ideal == Fraction(fracao)


def test_fracao_e_normalizada_para_forma_canonica() -> None:
    """2/64 chega ao domínio como 1/32 — decisão da ADR-010 § 6."""

    inv = parse_inventario_input(_entrada_minima("2/64", "3.125"))
    assert inv.bens[0].distribuicao[0].fracao_ideal == Fraction(1, 32)


@pytest.mark.parametrize(
    "fracao",
    [
        "1/0",  # denominador zero
        "0/5",  # numerador zero
        "-1/2",  # negativa
        "1/-2",  # denominador negativo
        "0.5",  # decimal, não fração
        "1e-2",  # notação científica
        "abc",  # texto arbitrário
        "1/2/3",  # malformada
        "",  # vazia
        "1 / 2",  # espaços
        "1//2",
        "/2",
        "1/",
    ],
)
def test_fracao_invalida_e_recusada(fracao: str) -> None:
    with pytest.raises(InventarioInputError):
        parse_inventario_input(_entrada_minima(fracao, "100"))


def test_fracao_e_opcional() -> None:
    """A ausência é o caso comum e não pode gerar fração inferida."""

    inv = parse_inventario_input(_entrada_minima(None, "100"))
    assert inv.bens[0].distribuicao[0].fracao_ideal is None


def test_sistema_nao_infere_fracao_a_partir_do_percentual() -> None:
    """Princípio de segurança da ADR-010: 3,125% NÃO vira 1/32 sozinho."""

    inv = parse_inventario_input(_entrada_minima(None, "100"))
    resumo = InventarioCalculator().compute(inv)
    assert all(q.fracao_ideal is None for r in resumo.bens for q in r.quinhoes)


# ---------------------------------------------------------------------------
# Coerência fração × percentual
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fracao", "percentual"),
    [
        ("1/1", "100"),
        ("1/2", "50"),
        ("1/32", "3.125"),
        ("1/16", "6.25"),
        ("1/3", "33.33"),  # dízima aceita dentro da tolerância derivada
    ],
)
def test_fracao_coerente_com_percentual_passa(fracao: str, percentual: str) -> None:
    inv = Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=False,
        percentual_meacao=Decimal("0"),
        patrimonio_total=Decimal("1000.00"),
        herdeiros=(Herdeiro(id="H1", percentual_heranca=Decimal("100")),),
        bens=(
            Bem(
                id="B1",
                tipo=TipoBem.OUTRO,
                descricao_generica="x",
                valor=Decimal("1000.00"),
                distribuicao=(
                    Distribuicao(
                        beneficiario="H1",
                        percentual=Decimal(percentual),
                        fracao_ideal=Fraction(fracao),
                    ),
                ),
            ),
        ),
    )
    erros = [e for e in InventarioValidator().validate(inv).errors if "fração" in e]
    assert erros == []


@pytest.mark.parametrize(
    ("fracao", "percentual"),
    [
        ("1/2", "40"),  # mismatch evidente
        ("1/32", "6.25"),  # fração de outro grupo
        ("1/3", "33.34"),  # não é o arredondamento correto de 1/3
        ("1/16", "3.125"),
    ],
)
def test_fracao_incoerente_com_percentual_falha(fracao: str, percentual: str) -> None:
    inv = Inventario(
        tipo_ato="inventario_extrajudicial",
        possui_meeiro=False,
        percentual_meacao=Decimal("0"),
        patrimonio_total=Decimal("1000.00"),
        herdeiros=(Herdeiro(id="H1", percentual_heranca=Decimal("100")),),
        bens=(
            Bem(
                id="B1",
                tipo=TipoBem.OUTRO,
                descricao_generica="x",
                valor=Decimal("1000.00"),
                distribuicao=(
                    Distribuicao(
                        beneficiario="H1",
                        percentual=Decimal(percentual),
                        fracao_ideal=Fraction(fracao),
                    ),
                ),
            ),
        ),
    )
    resultado = InventarioValidator().validate(inv)
    assert not resultado.ok
    assert any("incompatível com o percentual" in e for e in resultado.errors)


# ---------------------------------------------------------------------------
# Exemplo canônico de frações
# ---------------------------------------------------------------------------


def test_exemplo_fracoes_carrega_e_valida() -> None:
    inv = load_inventario(EXEMPLO_FRACOES)
    assert InventarioValidator().validate(inv).ok


def test_exemplo_fracoes_transporta_fracao_ate_o_quinhao() -> None:
    """O calculador repassa o metadado sem transformá-lo."""

    inv = load_inventario(EXEMPLO_FRACOES)
    resumo = InventarioCalculator().compute(inv)
    fracoes = {q.beneficiario: q.fracao_ideal for r in resumo.bens for q in r.quinhoes}
    assert fracoes[BENEFICIARIO_MEEIRO] == Fraction(1, 2)
    assert fracoes["HERDEIRO_1"] == Fraction(1, 16)
    assert fracoes["HERDEIRO_8"] == Fraction(1, 32)


def test_exemplo_fracoes_nao_tem_residuo_de_centavos() -> None:
    """A fixture isola representação de ADR-009: o cenário fecha exato."""

    inv = load_inventario(EXEMPLO_FRACOES)
    resumo = InventarioCalculator().compute(inv)
    assert resumo.divergencia_centavos == Decimal("0.00")


# ---------------------------------------------------------------------------
# Renderização
# ---------------------------------------------------------------------------


def test_resumo_exibe_coluna_de_fracao_quando_ha_fracao() -> None:
    inv = load_inventario(EXEMPLO_FRACOES)
    md = render_resumo_markdown(inv, InventarioCalculator().compute(inv))
    assert "| Beneficiário | Fração ideal | % | Valor |" in md
    assert "| 1/32 |" in md
    assert "| 1/16 |" in md


def test_resumo_sem_fracao_preserva_tabela_historica() -> None:
    """Documentos sem fração não podem ganhar coluna nova."""

    inv = parse_inventario_input(_entrada_minima(None, "100"))
    md = render_resumo_markdown(inv, InventarioCalculator().compute(inv))
    assert "| Beneficiário | % | Valor |" in md
    assert "Fração ideal" not in md


def test_minuta_nao_exibe_fracao_por_falta_de_redacao_aprovada() -> None:
    """Contrato explícito da ADR-010 § 8.

    A serventia, no caso real de 2026-07-09, redigiu a escritura **por
    percentual** — não há ocorrência de notação fracionária no texto aprovado.
    Enquanto o tabelião não definir a redação, a fração fica restrita aos
    artefatos técnicos. Este teste trava esse contrato: se alguém passar a
    renderizar fração na minuta, precisa fazê-lo deliberadamente, revendo a ADR.
    """

    inv = load_inventario(EXEMPLO_FRACOES)
    minuta = render_minuta_markdown(inv, InventarioCalculator().compute(inv))
    assert "1/32" not in minuta
    assert "1/16" not in minuta


# ---------------------------------------------------------------------------
# § 17 — o problema histórico que motivou a sprint
# ---------------------------------------------------------------------------


def test_problema_historico_3125_nao_e_mais_truncado_na_minuta() -> None:
    """Regressão da classe do caso de 2026-07-09.

    Antes da ADR-010, o quinhão de 3,125% saía da minuta como "3,12%", e foi
    exatamente por isso que aquele inventário precisou ser redigido à mão.
    """

    inv = load_inventario(EXEMPLO_FRACOES)
    minuta = render_minuta_markdown(inv, InventarioCalculator().compute(inv))
    assert "3,125%" in minuta
    assert "3,12%" not in minuta


def test_problema_historico_percentuais_exibidos_somam_cem() -> None:
    """O sintoma visível do defeito era o documento não fechar em 100%."""

    import re

    inv = load_inventario(EXEMPLO_FRACOES)
    resumo = render_resumo_markdown(inv, InventarioCalculator().compute(inv))
    secao_bem = resumo.split("## 4.")[1].split("## 5.")[0]
    percentuais = [Decimal(m.replace(",", ".")) for m in re.findall(r"\| (\d+,\d+)% \|", secao_bem)]
    assert percentuais, "nenhum percentual encontrado na tabela do bem"
    assert sum(percentuais) == Decimal("100")


def test_matematica_monetaria_identica_com_e_sem_fracao() -> None:
    """A fração é metadado: não pode mover um centavo sequer.

    Roda o mesmo inventário duas vezes — com e sem fração ideal — e compara
    todos os campos monetários do resumo.
    """

    def montar(com_fracao: bool) -> Inventario:
        def dist(beneficiario: str, pct: str, frac: str) -> Distribuicao:
            return Distribuicao(
                beneficiario=beneficiario,
                percentual=Decimal(pct),
                fracao_ideal=Fraction(frac) if com_fracao else None,
            )

        return Inventario(
            tipo_ato="inventario_extrajudicial",
            possui_meeiro=True,
            percentual_meacao=Decimal("50"),
            patrimonio_total=Decimal("32000.00"),
            herdeiros=(
                Herdeiro(id="H1", percentual_heranca=Decimal("87.5")),
                Herdeiro(id="H2", percentual_heranca=Decimal("12.5")),
            ),
            bens=(
                Bem(
                    id="B1",
                    tipo=TipoBem.VEICULO,
                    descricao_generica="x",
                    valor=Decimal("32000.00"),
                    distribuicao=(
                        dist(BENEFICIARIO_MEEIRO, "50", "1/2"),
                        dist("H1", "43.75", "7/16"),
                        dist("H2", "6.25", "1/16"),
                    ),
                ),
            ),
        )

    sem = InventarioCalculator().compute(montar(com_fracao=False))
    com = InventarioCalculator().compute(montar(com_fracao=True))

    assert com.patrimonio_total == sem.patrimonio_total
    assert com.valor_meacao == sem.valor_meacao
    assert com.monte_partilhavel == sem.monte_partilhavel
    assert com.divergencia_centavos == sem.divergencia_centavos
    assert com.quinhao_por_herdeiro == sem.quinhao_por_herdeiro
    assert com.total_por_beneficiario == sem.total_por_beneficiario
    assert [q.valor for r in com.bens for q in r.quinhoes] == [
        q.valor for r in sem.bens for q in r.quinhoes
    ]


# ---------------------------------------------------------------------------
# JSON de validação
# ---------------------------------------------------------------------------


def test_json_preserva_percentual_e_fracao(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.modules.notas.inventarios.interfaces.cli",
            "--input",
            str(EXEMPLO_FRACOES),
            "--output-dir",
            str(out_dir),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    payload = json.loads((out_dir / "inventario_validacao.json").read_text(encoding="utf-8"))
    quinhoes = payload["resumo"]["bens"][0]["quinhoes"]
    por_beneficiario = {q["beneficiario"]: q for q in quinhoes}

    # Percentual com 3 casas preservado — era "3.12" antes da ADR-010.
    assert por_beneficiario["HERDEIRO_8"]["percentual"] == "3.125"
    assert por_beneficiario["HERDEIRO_8"]["fracao_ideal"] == "1/32"
    # Dinheiro mantém o contrato de 2 casas.
    assert por_beneficiario["HERDEIRO_8"]["valor"] == "1000.00"
    assert payload["resumo"]["patrimonio_total"] == "32000.00"


def test_json_omite_fracao_quando_ausente(tmp_path: Path) -> None:
    """Casos sem fração preservam o formato histórico do artefato."""

    exemplo = PROJECT_ROOT / "app" / "modules" / "notas" / "inventarios" / "examples"
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.modules.notas.inventarios.interfaces.cli",
            "--input",
            str(exemplo / "inventario_simples.yaml"),
            "--output-dir",
            str(out_dir),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    payload = json.loads((out_dir / "inventario_validacao.json").read_text(encoding="utf-8"))
    for quinhao in payload["resumo"]["bens"][0]["quinhoes"]:
        assert "fracao_ideal" not in quinhao


# ---------------------------------------------------------------------------
# ODT
# ---------------------------------------------------------------------------


def test_odt_preserva_precisao_do_percentual(tmp_path: Path) -> None:
    import zipfile

    from app.modules.notas.inventarios.infrastructure.exporters import export_inventario_odt

    inv = load_inventario(EXEMPLO_FRACOES)
    minuta = render_minuta_markdown(inv, InventarioCalculator().compute(inv))
    destino = tmp_path / "minuta.odt"
    export_inventario_odt(minuta, destino)

    conteudo = zipfile.ZipFile(destino).read("content.xml").decode("utf-8")
    assert "3,125%" in conteudo
    assert "3,12%" not in conteudo
