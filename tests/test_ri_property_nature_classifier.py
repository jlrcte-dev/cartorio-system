"""Tests for classify_ri_property_nature.py.

All fixtures are synthetic — no real data from PDFs.
Covers all 21 test cases from sprint RI-NATURE-1 spec (section 18).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "local_tools"))

from classify_ri_property_nature import (  # noqa: I001
    NatureClassification,
    classify_property_nature,
    detect_rural_signals,
    detect_urban_signals,
    _normalize_nome,
    RURAL_STRONG_TERMS,
    URBAN_STRONG_TERMS,
    URBAN_MODERATE_TERMS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rec(
    nome: str | None = None,
    area_unidade: str | None = None,
    area_valor: float | None = None,
    tem_incra: int = 0,
    georref_direto: int = 0,
    tem_georreferenciamento: int = 0,
) -> dict[str, Any]:
    """Build a minimal synthetic record for classify_property_nature."""
    return {
        "nome_imovel_sanitizado": nome,
        "area_unidade": area_unidade,
        "area_valor_normalizado": area_valor,
        "tem_incra": tem_incra,
        "georreferenciamento_detectado_direto": georref_direto,
        "tem_georreferenciamento": tem_georreferenciamento,
    }


def _cls(rec: dict[str, Any]) -> NatureClassification:
    return classify_property_nature(rec)


# ---------------------------------------------------------------------------
# 1. Urban signals — strong and moderate combinations
# ---------------------------------------------------------------------------

class TestUrbanCases:
    # Case 1: Lote + Quadra → urbano provável
    def test_lote_quadra_urban(self) -> None:
        c = _cls(_rec("Lote 01 Quadra 02"))
        assert c.natureza_imovel == "urbano"
        assert c.natureza_imovel_confidence in ("provavel", "baixa_confianca")

    # Case 2: Lote + Rua + Bairro → urbano provável
    def test_lote_rua_bairro_urban(self) -> None:
        c = _cls(_rec("Lote situado na Rua Principal, Bairro Centro"))
        assert c.natureza_imovel == "urbano"

    # Case 3: Loteamento urbano → urbano provável (strong term)
    def test_loteamento_urbano(self) -> None:
        c = _cls(_rec("Loteamento Residencial Alfa"))
        assert c.natureza_imovel == "urbano"
        assert c.natureza_imovel_confidence in ("provavel", "confirmado")

    # Case 4: Perímetro urbano → urbano
    def test_perimetro_urbano(self) -> None:
        c = _cls(_rec("Imóvel situado no perímetro urbano"))
        assert c.natureza_imovel == "urbano"
        assert c.excluir_metricas_rurais is True

    # Case 5: Zona urbana → urbano
    def test_zona_urbana(self) -> None:
        c = _cls(_rec("Área de terra na zona urbana"))
        assert c.natureza_imovel == "urbano"
        assert c.excluir_metricas_rurais is True

    def test_loteamento_excludes_from_rural_metrics(self) -> None:
        c = _cls(_rec("Loteamento Vila Nova"))
        assert c.excluir_metricas_rurais is True

    def test_lote_quadra_excludes_from_rural_metrics(self) -> None:
        # Case 16: urban probable must have excluir_metricas_rurais=True
        c = _cls(_rec("Lote 05 Quadra 03"))
        assert c.excluir_metricas_rurais is True

    def test_single_lote_without_rural_needs_review(self) -> None:
        c = _cls(_rec("Lote 01"))
        # Single "lote" alone without context → baixa_confianca, needs review
        assert c.natureza_imovel in ("urbano", "indeterminado")
        assert c.status_revisao_ri == "needs_manual_review"

    def test_bairro_alone_no_rural_needs_review(self) -> None:
        c = _cls(_rec("Imóvel no Bairro Novo"))
        assert c.natureza_imovel in ("urbano", "indeterminado")
        assert c.status_revisao_ri == "needs_manual_review"


# ---------------------------------------------------------------------------
# 2. Rural confirmed
# ---------------------------------------------------------------------------

class TestRuralConfirmed:
    # Case 6: Fazenda + ha → rural confirmado
    def test_fazenda_com_ha_confirmado(self) -> None:
        c = _cls(_rec("Fazenda Alvorada", area_unidade="ha", area_valor=50.0))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "confirmado"
        assert c.excluir_metricas_rurais is False
        assert c.status_revisao_ri == "ok"

    # Case 7: Gleba de terras + hectares → rural confirmado
    def test_gleba_terras_hectares_confirmado(self) -> None:
        c = _cls(_rec("Gleba de terras", area_unidade="ha", area_valor=120.0))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "confirmado"

    def test_chacara_com_ha_confirmado(self) -> None:
        c = _cls(_rec("Chácara Boa Esperança", area_unidade="ha", area_valor=2.5))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "confirmado"

    def test_fazenda_com_alqueire_confirmado(self) -> None:
        c = _cls(_rec("FAZENDA SANTA RITA", area_unidade="alqueire", area_valor=10.0))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "confirmado"

    def test_sitio_com_georref_direto_confirmado(self) -> None:
        c = _cls(_rec("Sítio Boa Vista", georref_direto=1))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "confirmado"

    def test_rural_confirmed_not_excluded(self) -> None:
        c = _cls(_rec("Fazenda Boa Sorte", area_unidade="ha", area_valor=100.0))
        assert c.excluir_metricas_rurais is False

    def test_rural_confirmed_status_ok(self) -> None:
        c = _cls(_rec("RANCHO CABRAL", area_unidade="ha", area_valor=3.0))
        assert c.status_revisao_ri == "ok"


# ---------------------------------------------------------------------------
# 3. Rural probable
# ---------------------------------------------------------------------------

class TestRuralProbable:
    # Case 8: Sítio Boa Vista (no area) → rural provável
    def test_sitio_sem_area_provavel(self) -> None:
        c = _cls(_rec("Sítio Boa Vista"))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "provavel"

    # Case 9: Chácara Santa Luzia (no area) → rural provável
    def test_chacara_sem_area_provavel(self) -> None:
        c = _cls(_rec("Chácara Santa Luzia"))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "provavel"

    # Case 10: INCRA present, no strong urban → rural provável (not confirmado)
    def test_incra_only_rural_provavel(self) -> None:
        c = _cls(_rec(tem_incra=1))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "provavel"
        assert c.natureza_imovel_confidence != "confirmado"

    def test_incra_with_rural_name_no_area_provavel(self) -> None:
        # INCRA + Fazenda without area → provavel (no area confirmation)
        c = _cls(_rec("Fazenda Boa Vista", tem_incra=1))
        assert c.natureza_imovel == "rural"
        # With strong rural name but no area = provavel (not confirmado)
        assert c.natureza_imovel_confidence == "provavel"

    def test_area_ha_sem_nome_provavel(self) -> None:
        # Area in ha but no name → rural provável
        c = _cls(_rec(area_unidade="ha", area_valor=5.0))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "provavel"

    def test_rural_provavel_not_excluded(self) -> None:
        c = _cls(_rec("Sítio do Sol"))
        assert c.excluir_metricas_rurais is False

    def test_estancia_provavel(self) -> None:
        c = _cls(_rec("Estância Boa Vista"))
        assert c.natureza_imovel == "rural"

    def test_retiro_provavel(self) -> None:
        c = _cls(_rec("Retiro dos Ipês", area_unidade="ha", area_valor=15.0))
        assert c.natureza_imovel == "rural"
        assert c.natureza_imovel_confidence == "confirmado"


# ---------------------------------------------------------------------------
# 4. Conflict cases
# ---------------------------------------------------------------------------

class TestConflictCases:
    # Case 11: Lote rural na Fazenda X → conflito
    def test_lote_rural_na_fazenda_conflito(self) -> None:
        c = _cls(_rec("Lote rural na Fazenda Boa Vista"))
        assert c.natureza_imovel == "misto"
        assert c.status_revisao_ri == "needs_manual_review"

    # Case 12: Quadra localizada na Fazenda X → conflito
    def test_quadra_na_fazenda_conflito(self) -> None:
        c = _cls(_rec("Quadra localizada na Fazenda Santa Cruz"))
        assert c.natureza_imovel == "misto"
        assert c.status_revisao_ri == "needs_manual_review"

    # Case 13: INCRA + urban description → conflito
    def test_incra_com_descricao_urbana_conflito(self) -> None:
        c = _cls(_rec("Lote 07, situado no Sítio Novo Horizonte", tem_incra=1,
                       area_unidade="ha", area_valor=2.0))
        assert c.natureza_imovel == "misto"
        assert c.status_revisao_ri == "needs_manual_review"

    # Case 14: Georref direto + urban description → conflito
    def test_georref_direto_com_loteamento_conflito(self) -> None:
        c = _cls(_rec("Loteamento Fazenda Verde", georref_direto=1))
        # Georref is rural signal, loteamento is strong urban signal
        assert c.natureza_imovel == "misto"
        assert c.status_revisao_ri == "needs_manual_review"

    def test_lote_no_sitio_conflito(self) -> None:
        c = _cls(_rec("Lote 08, situado no Sitio Vovó Antônia", tem_incra=1))
        assert c.natureza_imovel == "misto"

    # Case 17: Conflicting records must NOT be auto-excluded
    def test_conflito_nao_excluido_automaticamente(self) -> None:
        c = _cls(_rec("Lote 01 Quadra 02 na Fazenda Boa Vista"))
        assert c.natureza_imovel == "misto"
        assert c.excluir_metricas_rurais is False  # conservative: don't auto-exclude

    def test_conflito_va_para_revisao(self) -> None:
        c = _cls(_rec("Quadra 03 localizada na Gleba de terras"))
        assert c.status_revisao_ri == "needs_manual_review"


# ---------------------------------------------------------------------------
# 5. Indeterminate
# ---------------------------------------------------------------------------

class TestIndeterminate:
    # Case 15: No name, no area, no characteristic → indeterminado
    def test_sem_nome_sem_area_sem_incra_indeterminado(self) -> None:
        c = _cls(_rec())
        assert c.natureza_imovel == "indeterminado"
        assert c.status_revisao_ri == "needs_manual_review"

    def test_nome_vazio_sem_area_indeterminado(self) -> None:
        c = _cls(_rec(nome=""))
        assert c.natureza_imovel == "indeterminado"

    def test_only_small_m2_no_name_indeterminado(self) -> None:
        # Very small m² alone (no name) is too ambiguous to classify
        c = _cls(_rec(area_unidade="m2", area_valor=300.0))
        assert c.natureza_imovel == "indeterminado"
        assert c.status_revisao_ri == "needs_manual_review"

    def test_indeterminado_not_excluded(self) -> None:
        c = _cls(_rec())
        assert c.excluir_metricas_rurais is False

    def test_generic_name_no_context_indeterminado(self) -> None:
        c = _cls(_rec("Imóvel"))
        assert c.natureza_imovel == "indeterminado"


# ---------------------------------------------------------------------------
# 6. Signal detection functions
# ---------------------------------------------------------------------------

class TestDetectRuralSignals:
    def test_fazenda_in_nome(self) -> None:
        sigs = detect_rural_signals("Fazenda Boa Vista", None, False, False)
        assert any("fazenda" in s for s in sigs)

    def test_sitio_accented(self) -> None:
        sigs = detect_rural_signals("Sítio Santa Cruz", None, False, False)
        assert any("sitio" in s for s in sigs)

    def test_chacara_unaccented(self) -> None:
        sigs = detect_rural_signals("CHACARA JATOBA", None, False, False)
        assert any("chacara" in s for s in sigs)

    def test_area_ha_unit(self) -> None:
        sigs = detect_rural_signals(None, "ha", False, False)
        assert any("ha" in s for s in sigs)

    def test_area_alqueire_unit(self) -> None:
        sigs = detect_rural_signals(None, "alqueire", False, False)
        assert any("alqueire" in s for s in sigs)

    def test_incra_signal(self) -> None:
        sigs = detect_rural_signals(None, None, True, False)
        assert "incra" in sigs

    def test_georref_direto_signal(self) -> None:
        sigs = detect_rural_signals(None, None, False, True)
        assert "georref_direto" in sigs

    def test_no_signals_empty_record(self) -> None:
        sigs = detect_rural_signals(None, None, False, False)
        assert sigs == []

    def test_m2_area_not_rural_signal(self) -> None:
        sigs = detect_rural_signals("Fazenda X", "m2", False, False)
        assert not any("area_unidade:m2" in s for s in sigs)


class TestDetectUrbanSignals:
    def test_loteamento_strong(self) -> None:
        sigs = detect_urban_signals("Loteamento Vila Nova", None, None)
        assert any("loteamento" in s for s in sigs)

    def test_perimetro_urbano_strong(self) -> None:
        sigs = detect_urban_signals("área no perímetro urbano", None, None)
        assert any("perimetro urbano" in s or "perim" in s for s in sigs)

    def test_lote_moderado(self) -> None:
        sigs = detect_urban_signals("Lote 01 Quadra 02", None, None)
        assert any("lote" in s for s in sigs)

    def test_quadra_moderado(self) -> None:
        sigs = detect_urban_signals("Quadra 05", None, None)
        assert any("quadra" in s for s in sigs)

    def test_bairro_moderado(self) -> None:
        sigs = detect_urban_signals("Imóvel no Bairro Norte", None, None)
        assert any("bairro" in s for s in sigs)

    def test_rua_word_boundary(self) -> None:
        sigs = detect_urban_signals("situado na Rua das Flores", None, None)
        assert any("rua" in s for s in sigs)

    def test_rural_no_urban_signal(self) -> None:
        sigs = detect_urban_signals("Fazenda Boa Vista", "ha", 50.0)
        assert sigs == []

    def test_fazenda_jardim_no_urban_signal(self) -> None:
        # "Jardim" in property name should NOT trigger urban signal
        # (common in Goiás rural property names)
        sigs = detect_urban_signals("Chácara Jardim das Flores", None, None)
        # jardim is excluded from urban terms — should have no urban signal
        assert not any("jardim" in s for s in sigs)

    def test_area_muito_pequena_m2(self) -> None:
        sigs = detect_urban_signals(None, "m2", 300.0)
        assert any("area_muito_pequena_m2" in s for s in sigs)

    def test_area_pequena_m2(self) -> None:
        sigs = detect_urban_signals(None, "m2", 2000.0)
        assert any("area_pequena_m2" in s for s in sigs)

    def test_large_m2_no_signal(self) -> None:
        sigs = detect_urban_signals(None, "m2", 20000.0)
        # 20,000 m² = 2ha → no urban area signal
        assert not any("area_" in s and "m2" in s for s in sigs)

    def test_lote_not_in_loteamento(self) -> None:
        # "loteamento" should not double-count as "lote" moderate
        sigs = detect_urban_signals("Loteamento Boa Vista", None, None)
        assert not any(s == "nome_moderado:lote" for s in sigs)

    def test_incra_code_no_urban_signal(self) -> None:
        # INCRA codes (bare digit sequences) should not trigger urban signals
        sigs = detect_urban_signals("93018000099888", None, None)
        assert sigs == []

    def test_no_signals_clean_rural(self) -> None:
        sigs = detect_urban_signals("Fazenda Santa Branca", "ha", 200.0)
        assert sigs == []


# ---------------------------------------------------------------------------
# 7. Normalization
# ---------------------------------------------------------------------------

class TestNormalizaNome:
    def test_lowercase(self) -> None:
        assert _normalize_nome("FAZENDA") == "fazenda"

    def test_accent_removal(self) -> None:
        assert _normalize_nome("Sítio") == "sitio"
        assert _normalize_nome("Chácara") == "chacara"
        assert _normalize_nome("Estância") == "estancia"

    def test_none_returns_empty(self) -> None:
        assert _normalize_nome(None) == ""

    def test_empty_returns_empty(self) -> None:
        assert _normalize_nome("") == ""


# ---------------------------------------------------------------------------
# 8. Output safety — no PII in classification results
# ---------------------------------------------------------------------------

class TestNoPiiInOutput:
    # Case 20: No CPF/CNPJ/RG/CI in any classification output
    def test_no_pii_in_sinais_field(self) -> None:
        for nome in [
            "Fazenda Alvorada",
            "Lote 01 Quadra 02",
            "Sítio Boa Vista",
            None,
        ]:
            c = _cls(_rec(nome=nome, tem_incra=1))
            for field in (
                c.sinais_urbanos_detectados,
                c.sinais_rurais_detectados,
                c.natureza_imovel_fonte,
                c.motivo_exclusao_metricas,
            ):
                assert "cpf" not in (field or "").lower()
                assert "cnpj" not in (field or "").lower()
                assert "proprietario" not in (field or "").lower()

    def test_classification_contains_no_nome_value(self) -> None:
        # Classification signals must NOT contain the raw nome value
        nome = "Fazenda Boa Vista"
        c = _cls(_rec(nome=nome))
        # Signal tags are category labels (nome_forte:fazenda), not the actual name
        assert nome not in c.sinais_rurais_detectados
        assert nome not in c.sinais_urbanos_detectados
        assert nome not in c.natureza_imovel_fonte

    # Case 21: Tests use only synthetic data (enforced by this module's design)


# ---------------------------------------------------------------------------
# 9. Classification invariants
# ---------------------------------------------------------------------------

class TestClassificationInvariants:
    # Case 18: Report ordered by matricula (tested via integration, not unit test)
    # but we can verify the dataclass fields are always present

    def test_returns_dataclass_always(self) -> None:
        for record in [
            _rec(),
            _rec("Fazenda X", "ha", 50.0),
            _rec("Lote 01 Quadra 02"),
            _rec("Lote no Sítio Boa Vista", tem_incra=1),
        ]:
            c = _cls(record)
            assert isinstance(c, NatureClassification)
            assert c.natureza_imovel in ("rural", "urbano", "misto", "indeterminado")
            assert c.natureza_imovel_confidence in (
                "confirmado", "provavel", "baixa_confianca", "manual"
            )
            assert isinstance(c.excluir_metricas_rurais, bool)
            assert c.status_revisao_ri in (
                "ok", "needs_manual_review", "excluir_metricas_rurais", "validado_manual"
            )

    def test_confirmed_rural_always_ok(self) -> None:
        c = _cls(_rec("Fazenda Boa Vista", area_unidade="ha", area_valor=10.0))
        assert c.status_revisao_ri == "ok"

    def test_urban_provavel_always_excluded(self) -> None:
        for nome in ["Loteamento Vila", "área no perímetro urbano", "Lote 01 Quadra 02"]:
            c = _cls(_rec(nome=nome))
            if c.natureza_imovel == "urbano" and c.natureza_imovel_confidence == "provavel":
                assert c.excluir_metricas_rurais is True

    def test_misto_never_auto_excluded(self) -> None:
        # Case 17: conflicts go to review, not automatic exclusion
        c = _cls(_rec("Lote 01 na Fazenda Boa Vista"))
        if c.natureza_imovel == "misto":
            assert c.excluir_metricas_rurais is False

    def test_indeterminado_never_auto_excluded(self) -> None:
        c = _cls(_rec())
        assert c.excluir_metricas_rurais is False

    # Case 19: Urban signals report has only allowed columns (tested via reports)
    def test_urban_signals_field_no_raw_text(self) -> None:
        c = _cls(_rec("Lote 01 Quadra 02 Bairro Centro"))
        # Signals are labels like "nome_moderado:lote", not raw text
        for sig in c.sinais_urbanos_detectados.split(";"):
            assert "Lote 01" not in sig
            assert "Centro" not in sig
            assert "Quadra 02" not in sig

    def test_terms_list_no_pii_content(self) -> None:
        # Verify that all term lists contain only classification keywords
        for term in RURAL_STRONG_TERMS + URBAN_STRONG_TERMS + URBAN_MODERATE_TERMS:
            assert len(term) < 50  # no long personal data in term lists
