"""Validação estrutural e numérica do inventário."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.modules.notas.inventarios.application.calculator import (
    DECIMAL_TOLERANCIA,
    quantize_money,
)
from app.modules.notas.inventarios.application.formatting import (
    formatar_fracao,
    percentual_da_fracao,
    tolerancia_percentual,
)
from app.modules.notas.inventarios.domain.models import (
    BENEFICIARIO_MEEIRO,
    Distribuicao,
    Inventario,
)

_ZERO = Decimal("0")
_CEM = Decimal("100")


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


class InventarioValidator:
    """Aplica as regras descritas em `docs/modules/notas_inventarios.md` § 3.2."""

    TIPO_ATO_PERMITIDO = "inventario_extrajudicial"

    def validate(self, inv: Inventario) -> ValidationResult:
        result = ValidationResult()

        if inv.tipo_ato != self.TIPO_ATO_PERMITIDO:
            result.add(
                f"tipo_ato inválido: '{inv.tipo_ato}'. "
                f"Apenas '{self.TIPO_ATO_PERMITIDO}' é suportado nesta sprint."
            )

        if inv.patrimonio_total <= _ZERO:
            result.add(
                f"patrimonio_total deve ser maior que zero (recebido: {inv.patrimonio_total})."
            )

        self._validate_meacao(inv, result)
        self._validate_herdeiros(inv, result)
        self._validate_bens(inv, result)

        return result

    @staticmethod
    def _validate_meacao(inv: Inventario, result: ValidationResult) -> None:
        if inv.possui_meeiro:
            if not (_ZERO < inv.percentual_meacao <= _CEM):
                result.add(
                    "percentual_meacao deve estar entre 0 (exclusivo) e 100 "
                    f"quando possui_meeiro=true (recebido: {inv.percentual_meacao})."
                )
        else:
            if inv.percentual_meacao != _ZERO:
                result.add(
                    "percentual_meacao deve ser 0 quando possui_meeiro=false "
                    f"(recebido: {inv.percentual_meacao})."
                )

    @classmethod
    def _validate_herdeiros(cls, inv: Inventario, result: ValidationResult) -> None:
        if not inv.herdeiros:
            result.add("É necessário ao menos um herdeiro.")
            return

        ids = [h.id for h in inv.herdeiros]
        cls._check_unique_non_empty(ids, "herdeiros", result)

        if any(h.id.strip().upper() == BENEFICIARIO_MEEIRO for h in inv.herdeiros):
            result.add(
                f"'{BENEFICIARIO_MEEIRO}' é um identificador reservado e não pode "
                "ser usado como id de herdeiro."
            )

        soma_pct = sum((h.percentual_heranca for h in inv.herdeiros), _ZERO)
        if abs(soma_pct - _CEM) > DECIMAL_TOLERANCIA:
            result.add(f"Soma dos percentuais de herança deve ser 100 (recebido: {soma_pct}).")

        for h in inv.herdeiros:
            if h.percentual_heranca < _ZERO:
                result.add(
                    f"herdeiro '{h.id}' tem percentual_heranca negativo: {h.percentual_heranca}."
                )

    @classmethod
    def _validate_bens(cls, inv: Inventario, result: ValidationResult) -> None:
        if not inv.bens:
            result.add("É necessário ao menos um bem.")
            return

        ids = [b.id for b in inv.bens]
        cls._check_unique_non_empty(ids, "bens", result)

        soma_bens = quantize_money(sum((b.valor for b in inv.bens), _ZERO))
        if abs(soma_bens - quantize_money(inv.patrimonio_total)) > DECIMAL_TOLERANCIA:
            result.add(
                "Soma dos valores dos bens "
                f"({soma_bens}) difere do patrimonio_total "
                f"declarado ({quantize_money(inv.patrimonio_total)})."
            )

        herdeiros_ids = {h.id for h in inv.herdeiros}
        beneficiarios_permitidos = herdeiros_ids | (
            {BENEFICIARIO_MEEIRO} if inv.possui_meeiro else set()
        )

        for bem in inv.bens:
            if bem.valor < _ZERO:
                result.add(f"bem '{bem.id}' tem valor negativo: {bem.valor}.")

            if not bem.distribuicao:
                result.add(f"bem '{bem.id}' não possui distribuição definida.")
                continue

            soma_pct = sum((d.percentual for d in bem.distribuicao), _ZERO)
            if abs(soma_pct - _CEM) > DECIMAL_TOLERANCIA:
                result.add(
                    f"bem '{bem.id}': soma dos percentuais da distribuição deve ser "
                    f"100 (recebido: {soma_pct})."
                )

            for d in bem.distribuicao:
                if d.percentual < _ZERO:
                    result.add(
                        f"bem '{bem.id}': beneficiário '{d.beneficiario}' tem "
                        f"percentual negativo: {d.percentual}."
                    )
                cls._validate_fracao_ideal(bem.id, d, result)
                if d.beneficiario not in beneficiarios_permitidos:
                    if d.beneficiario == BENEFICIARIO_MEEIRO and not inv.possui_meeiro:
                        result.add(
                            f"bem '{bem.id}': beneficiário '{BENEFICIARIO_MEEIRO}' "
                            "usado, mas possui_meeiro=false."
                        )
                    else:
                        result.add(
                            f"bem '{bem.id}': beneficiário '{d.beneficiario}' não "
                            "consta na lista de herdeiros."
                        )

    @staticmethod
    def _validate_fracao_ideal(bem_id: str, d: Distribuicao, result: ValidationResult) -> None:
        """Recusa fração ideal incoerente com o percentual declarado (ADR-010).

        A comparação é feita com tolerância derivada da precisão do próprio
        percentual — ver :func:`tolerancia_percentual`. Igualdade textual de
        ``Decimal`` seria impossível de exigir: frações como ``1/3`` têm
        expansão decimal infinita, e o percentual escrito na entrada é
        necessariamente arredondado.
        """

        if d.fracao_ideal is None:
            return

        esperado = percentual_da_fracao(d.fracao_ideal)
        tolerancia = tolerancia_percentual(d.percentual)
        if abs(esperado - d.percentual) > tolerancia:
            result.add(
                f"bem '{bem_id}': beneficiário '{d.beneficiario}' declara fração "
                f"{formatar_fracao(d.fracao_ideal)}, equivalente a "
                f"{esperado.normalize():f}%, incompatível com o percentual "
                f"informado {d.percentual}% (tolerância {tolerancia:f})."
            )

    @staticmethod
    def _check_unique_non_empty(ids: list[str], rotulo: str, result: ValidationResult) -> None:
        seen: set[str] = set()
        for i in ids:
            if not i or not i.strip():
                result.add(f"{rotulo}: id vazio encontrado.")
                continue
            if i in seen:
                result.add(f"{rotulo}: id duplicado '{i}'.")
            seen.add(i)


__all__ = ["InventarioValidator", "ValidationResult"]
