"""Schema Pydantic v2 para a entrada YAML/JSON de inventário extrajudicial.

Sprint **NOTAS-INVENTARIO-4 — Schema Pydantic + Golden Files.**

Este módulo cuida apenas do **contrato de entrada**:

- campos obrigatórios, tipos, listas não vazias;
- conversão segura para ``Decimal`` (sem passar por ``float``);
- ``extra="forbid"`` para detectar campos não previstos;
- ``tipo_ato`` restrito ao único valor suportado nesta sprint;
- ``tipo`` de cada bem restrito ao enum :class:`TipoBem`.

Validações de **negócio** (soma de percentuais, integridade referencial,
patrimônio = Σ bens, meeiro proibido sem ``possui_meeiro``, política de
centavos da ADR-009, ids únicos) continuam em
:mod:`app.modules.notas.inventarios.application.validator` — esta sprint
não move regras de negócio para o schema, apenas fortalece o filtro
estrutural antes do validador rodar.

Pipeline atual:

    YAML/JSON
        → :class:`InventarioInputSchema` (estrutural)
        → :meth:`InventarioInputSchema.to_inventario` (modelos imutáveis do domínio)
        → :class:`InventarioValidator` (regras de negócio)
        → :class:`InventarioCalculator`
        → renderização.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from app.modules.notas.inventarios.domain.errors import InventarioInputError
from app.modules.notas.inventarios.domain.models import (
    Bem,
    Distribuicao,
    Herdeiro,
    Inventario,
    TipoBem,
)

TIPO_ATO_SUPORTADO = "inventario_extrajudicial"


def _coerce_decimal_input(value: object) -> object:
    """Converte ``float`` para ``str`` antes do parsing de ``Decimal``.

    Sem isso, ``Decimal(0.1)`` no caminho padrão do Pydantic carregaria o
    ruído binário do ``float``. Booleanos são rejeitados explicitamente —
    ``Decimal(True) == 1`` é uma armadilha silenciosa que não interessa
    para valores monetários.
    """

    if isinstance(value, bool):
        raise ValueError("valor não pode ser booleano para campo numérico")
    if isinstance(value, float):
        return str(value)
    return value


SafeDecimal = Annotated[Decimal, BeforeValidator(_coerce_decimal_input)]


class DistribuicaoSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beneficiario: str = Field(..., min_length=1)
    percentual: SafeDecimal


class BemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    tipo: TipoBem
    descricao_generica: str = ""
    valor: SafeDecimal
    distribuicao: list[DistribuicaoSchema] = Field(default_factory=list)

    @field_validator("tipo", mode="before")
    @classmethod
    def _validar_tipo(cls, value: object) -> TipoBem:
        if isinstance(value, TipoBem):
            return value
        try:
            return TipoBem(str(value))
        except ValueError as exc:
            aceitos = [t.value for t in TipoBem]
            raise ValueError(f"tipo inválido: '{value}'. Valores aceitos: {aceitos}") from exc


class HerdeiroSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    percentual_heranca: SafeDecimal


class InventarioInputSchema(BaseModel):
    """Contrato estrutural da entrada YAML/JSON.

    Regras aqui são apenas estruturais. Negócio fica no validador.
    """

    model_config = ConfigDict(extra="forbid")

    tipo_ato: Literal["inventario_extrajudicial"]
    possui_meeiro: bool
    percentual_meacao: SafeDecimal = Decimal("0")
    patrimonio_total: SafeDecimal
    herdeiros: list[HerdeiroSchema] = Field(..., min_length=1)
    bens: list[BemSchema] = Field(..., min_length=1)

    def to_inventario(self) -> Inventario:
        herdeiros = tuple(
            Herdeiro(id=h.id, percentual_heranca=h.percentual_heranca) for h in self.herdeiros
        )
        bens = tuple(
            Bem(
                id=b.id,
                tipo=b.tipo,
                descricao_generica=b.descricao_generica,
                valor=b.valor,
                distribuicao=tuple(
                    Distribuicao(beneficiario=d.beneficiario, percentual=d.percentual)
                    for d in b.distribuicao
                ),
            )
            for b in self.bens
        )
        return Inventario(
            tipo_ato=self.tipo_ato,
            possui_meeiro=self.possui_meeiro,
            percentual_meacao=self.percentual_meacao,
            patrimonio_total=self.patrimonio_total,
            herdeiros=herdeiros,
            bens=bens,
        )


def parse_inventario_input(data: object) -> Inventario:
    """Roda o schema sobre ``data`` (já desserializado) e devolve um :class:`Inventario`.

    Em caso de violação estrutural, levanta
    :class:`InventarioInputError` com mensagem agregada — uma linha por
    erro Pydantic, prefixada pelo caminho do campo. Sem stack-trace
    cru de Pydantic vazando para a CLI.
    """

    if not isinstance(data, dict):
        raise InventarioInputError(
            f"raiz do arquivo deve ser um objeto/mapping (recebido: {type(data).__name__})."
        )
    try:
        parsed = InventarioInputSchema.model_validate(data)
    except ValidationError as exc:
        raise InventarioInputError(_format_validation_error(exc)) from exc
    return parsed.to_inventario()


def _format_validation_error(exc: ValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(item) for item in err.get("loc", ()))
        msg = err.get("msg", "valor inválido")
        if loc:
            parts.append(f"{loc}: {msg}")
        else:
            parts.append(msg)
    if not parts:
        return "entrada inválida"
    return "; ".join(parts)


__all__ = [
    "BemSchema",
    "DistribuicaoSchema",
    "HerdeiroSchema",
    "InventarioInputSchema",
    "SafeDecimal",
    "TIPO_ATO_SUPORTADO",
    "parse_inventario_input",
]
