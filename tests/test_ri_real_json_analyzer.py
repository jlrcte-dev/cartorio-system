"""
Testes sintéticos do analisador do Indicador Real JSON — sprint RI-REAL-JSON-1

IMPORTANTE: Todos os dados são FICTÍCIOS.
Nenhum dado pessoal real é usado neste arquivo.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "scripts" / "local_tools")
)

from analyze_ri_real_json import (  # noqa: I001
    RuralFlags,
    _is_pii_string,
    _normalize_rural,
    _sanitize_bairro,
    _sanitize_cep,
    calc_georreferenciamento,
    classify_natureza,
    compute_metrics,
    parse_numero_registro,
    process_record,
    record_to_dict,
)


# ---------------------------------------------------------------------------
# Helpers sintéticos — sem dados reais
# ---------------------------------------------------------------------------

CNS_FICTICIO = "999999"


def nr(matricula: int, livro: int = 2, dv: str = "00") -> str:
    """Gera NUMERO_REGISTRO fictício formatado."""
    return f"{CNS_FICTICIO}.{livro}.{matricula:07d}-{dv}"


def raw_urbano(matricula: int = 1, **kwargs) -> dict:
    base = {
        "NUMERO_REGISTRO": nr(matricula),
        "REGISTRO_TIPO": 1,
        "TIPO_DE_IMOVEL": 1,
        "LOCALIZACAO": 0,
        "UF": "GO",
        "CIDADE": "9999",
        "BAIRRO": "SETOR CENTRAL",
        "CEP": "75600-000",
        "QUADRA": "",
        "LOTE": "",
        "LOTEAMENTO": "",
        "CONTRIBUINTE": "CONTRIBUINTE FICTICIO SA",  # nunca deve aparecer na saída
        "CONDOMINIO": "",
        "RURAL": {
            "CAR": "", "NIRF": "", "CCIR": "",
            "NUMERO_INCRA": "", "SIGEF": "",
            "DENOMINACAORURAL": "", "ACIDENTEGEOGRAFICO": "",
        },
    }
    base.update(kwargs)
    return base


def raw_rural(matricula: int = 1000, **kwargs) -> dict:
    base = {
        "NUMERO_REGISTRO": nr(matricula),
        "REGISTRO_TIPO": 1,
        "TIPO_DE_IMOVEL": 1,
        "LOCALIZACAO": 1,
        "UF": "GO",
        "CIDADE": "9999",
        "BAIRRO": "",
        "CEP": "75600-000",
        "QUADRA": "",
        "LOTE": "",
        "LOTEAMENTO": "",
        "CONTRIBUINTE": "FAZENDEIRO FICTICIO",  # nunca deve aparecer na saída
        "CONDOMINIO": "",
        "RURAL": {
            "CAR": "",
            "NIRF": "",
            "CCIR": "",
            "NUMERO_INCRA": "",
            "SIGEF": "",
            "DENOMINACAORURAL": "Fazenda Fictícia",
            "ACIDENTEGEOGRAFICO": "",
        },
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# 1. Parse de NUMERO_REGISTRO válido
# ---------------------------------------------------------------------------

class TestParseNumeroRegistro:
    def test_parse_valido(self):
        p = parse_numero_registro("147454.2.0003520-36")
        assert p.valido is True
        assert p.cns == "147454"
        assert p.livro == "2"
        assert p.matricula_raw == "0003520"
        assert p.matricula_numero == 3520
        assert p.digito_verificador_onr == "36"

    # 2. Matrícula sem zeros à esquerda
    def test_matricula_sem_zeros(self):
        p = parse_numero_registro("999999.2.0000001-20")
        assert p.matricula_numero == 1
        assert p.matricula_raw == "0000001"

    def test_matricula_grande(self):
        p = parse_numero_registro("999999.2.0003524-99")
        assert p.matricula_numero == 3524

    # 3. NUMERO_REGISTRO inválido gera status
    def test_invalido_formato_errado(self):
        p = parse_numero_registro("INVALIDO")
        assert p.valido is False
        assert p.alerta == "numero_registro_invalido"

    def test_invalido_sem_dv(self):
        p = parse_numero_registro("999999.2.0000001")
        assert p.valido is False

    def test_invalido_vazio(self):
        p = parse_numero_registro("")
        assert p.valido is False

    def test_invalido_letras(self):
        p = parse_numero_registro("ABC.2.0000001-20")
        assert p.valido is False


# ---------------------------------------------------------------------------
# 4. CNS divergente gera alerta
# ---------------------------------------------------------------------------

class TestCNSDivergente:
    def test_cns_divergente(self):
        raw = raw_urbano(matricula=1)
        raw["NUMERO_REGISTRO"] = "111111.2.0000001-00"  # CNS diferente do esperado
        rec = process_record(raw, cns_esperado="999999", fonte="test.json")
        assert "cns_divergente" in rec.status_extracao

    def test_cns_correto(self):
        raw = raw_urbano(matricula=5)
        rec = process_record(raw, cns_esperado=CNS_FICTICIO, fonte="test.json")
        assert "cns_divergente" not in rec.status_extracao


# ---------------------------------------------------------------------------
# 5–7. LOCALIZACAO
# ---------------------------------------------------------------------------

class TestLocalizacao:
    def test_localizacao_0_urbano(self):
        natureza, fonte, confidence = classify_natureza(0)
        assert natureza == "urbano"
        assert confidence == "confirmado"

    def test_localizacao_1_rural(self):
        natureza, fonte, confidence = classify_natureza(1)
        assert natureza == "rural"
        assert confidence == "confirmado"

    def test_localizacao_invalida_indeterminado(self):
        natureza, fonte, confidence = classify_natureza(99)
        assert natureza == "indeterminado"
        assert confidence == "invalido"

    def test_localizacao_none_indeterminado(self):
        natureza, _, _ = classify_natureza(None)
        assert natureza == "indeterminado"

    def test_process_localizacao_0_urbano(self):
        rec = process_record(raw_urbano(matricula=2), CNS_FICTICIO, "test.json")
        assert rec.natureza_imovel == "urbano"

    def test_process_localizacao_1_rural(self):
        rec = process_record(raw_rural(matricula=1001), CNS_FICTICIO, "test.json")
        assert rec.natureza_imovel == "rural"

    def test_localizacao_invalida_marca_revisao(self):
        raw = raw_urbano(matricula=3, LOCALIZACAO=99)
        rec = process_record(raw, CNS_FICTICIO, "test.json")
        assert rec.natureza_imovel == "indeterminado"
        assert "localizacao_invalida" in rec.status_extracao
        assert rec.status_revisao_ri == "needs_manual_review"


# ---------------------------------------------------------------------------
# 8–10. NIRF
# ---------------------------------------------------------------------------

class TestNIRF:
    def test_nirf_vazio_ausente(self):
        r = _normalize_rural({"CAR": "", "NIRF": "", "CCIR": "", "NUMERO_INCRA": "",
                               "SIGEF": "", "DENOMINACAORURAL": "", "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_nirf is False
        assert r.nirf_status == "ausente"

    def test_nirf_so_zeros_placeholder(self):
        r = _normalize_rural({"NIRF": "00000000", "CAR": "", "CCIR": "",
                               "NUMERO_INCRA": "", "SIGEF": "", "DENOMINACAORURAL": "",
                               "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_nirf is False
        assert r.nirf_status == "placeholder_zeros"

    def test_nirf_valido(self):
        r = _normalize_rural({"NIRF": "12345678", "CAR": "", "CCIR": "",
                               "NUMERO_INCRA": "", "SIGEF": "", "DENOMINACAORURAL": "",
                               "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_nirf is True
        assert r.nirf_status == "valido"
        assert r.nirf_codigo == "12345678"

    def test_nirf_none_ausente(self):
        r = _normalize_rural({"NIRF": None, "CAR": "", "CCIR": "",
                               "NUMERO_INCRA": "", "SIGEF": "", "DENOMINACAORURAL": "",
                               "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_nirf is False
        assert r.nirf_status == "ausente"


# ---------------------------------------------------------------------------
# 11. CAR preenchido
# ---------------------------------------------------------------------------

class TestCAR:
    def test_car_preenchido(self):
        r = _normalize_rural({"CAR": "GO-1234567-ABC", "NIRF": "", "CCIR": "",
                               "NUMERO_INCRA": "", "SIGEF": "", "DENOMINACAORURAL": "",
                               "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_car is True
        assert r.car_codigo == "GO-1234567-ABC"

    def test_car_vazio(self):
        r = _normalize_rural({"CAR": "", "NIRF": "", "CCIR": "",
                               "NUMERO_INCRA": "", "SIGEF": "", "DENOMINACAORURAL": "",
                               "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_car is False


# ---------------------------------------------------------------------------
# 12. CCIR preenchido
# ---------------------------------------------------------------------------

class TestCCIR:
    def test_ccir_preenchido(self):
        r = _normalize_rural({"CAR": "", "NIRF": "", "CCIR": "987654321",
                               "NUMERO_INCRA": "", "SIGEF": "", "DENOMINACAORURAL": "",
                               "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_ccir is True

    def test_ccir_vazio(self):
        r = _normalize_rural({"CAR": "", "NIRF": "", "CCIR": "",
                               "NUMERO_INCRA": "", "SIGEF": "", "DENOMINACAORURAL": "",
                               "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_ccir is False


# ---------------------------------------------------------------------------
# 13–14. NUMERO_INCRA e SIGEF
# ---------------------------------------------------------------------------

class TestIncraESigef:
    def test_numero_incra_preenchido(self):
        r = _normalize_rural({"CAR": "", "NIRF": "", "CCIR": "",
                               "NUMERO_INCRA": "93018000018482", "SIGEF": "",
                               "DENOMINACAORURAL": "", "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_numero_incra is True

    def test_sigef_preenchido(self):
        r = _normalize_rural({"CAR": "", "NIRF": "", "CCIR": "",
                               "NUMERO_INCRA": "", "SIGEF": "SIGEF-GO-99999",
                               "DENOMINACAORURAL": "", "ACIDENTEGEOGRAFICO": ""})
        assert r.tem_sigef is True


# ---------------------------------------------------------------------------
# 15–17. Georreferenciamento
# ---------------------------------------------------------------------------

class TestGeorreferenciamento:
    def test_incra_gera_georef(self):
        r = RuralFlags(tem_numero_incra=True, numero_incra_codigo="93018000018482")
        possui, criterio = calc_georreferenciamento(r)
        assert possui is True
        assert "numero_incra" in criterio

    def test_sigef_gera_georef(self):
        r = RuralFlags(tem_sigef=True, sigef_codigo="SIGEF-GO-99999")
        possui, criterio = calc_georreferenciamento(r)
        assert possui is True
        assert "sigef" in criterio

    def test_ambos_gera_georef(self):
        r = RuralFlags(
            tem_numero_incra=True, numero_incra_codigo="93018000018482",
            tem_sigef=True, sigef_codigo="SIGEF-GO-99999",
        )
        possui, criterio = calc_georreferenciamento(r)
        assert possui is True
        assert "numero_incra" in criterio
        assert "sigef" in criterio

    def test_sem_incra_nem_sigef(self):
        r = RuralFlags()
        possui, criterio = calc_georreferenciamento(r)
        assert possui is False
        assert criterio == ""


# ---------------------------------------------------------------------------
# 18. CONTRIBUINTE não aparece na saída sanitizada
# ---------------------------------------------------------------------------

class TestContribuinteAusente:
    def test_contribuinte_nao_no_dict(self):
        raw = raw_urbano(matricula=10)
        raw["CONTRIBUINTE"] = "PROPRIETARIO FICTICIO"
        rec = process_record(raw, CNS_FICTICIO, "test.json")
        d = record_to_dict(rec)
        assert "CONTRIBUINTE" not in d
        assert "contribuinte" not in d
        assert "PROPRIETARIO FICTICIO" not in str(d.values())

    def test_contribuinte_nao_em_rural(self):
        raw = raw_rural(matricula=1010)
        raw["CONTRIBUINTE"] = "FAZENDEIRO FICTICIO"
        rec = process_record(raw, CNS_FICTICIO, "test.json")
        d = record_to_dict(rec)
        for v in d.values():
            assert "FAZENDEIRO FICTICIO" not in str(v)


# ---------------------------------------------------------------------------
# 19. Denominação rural suspeita é removida
# ---------------------------------------------------------------------------

class TestDenominacaoRuralSuspeita:
    def test_denominacao_imovel_valida(self):
        r = _normalize_rural({
            "CAR": "", "NIRF": "", "CCIR": "", "NUMERO_INCRA": "", "SIGEF": "",
            "DENOMINACAORURAL": "Fazenda Bela Vista",
            "ACIDENTEGEOGRAFICO": "",
        })
        assert r.tem_denominacao_rural is True
        assert r.denominacao_rural_sanitizada == "Fazenda Bela Vista"

    def test_denominacao_suspeita_nome_pessoa_removida(self):
        # Padrão de múltiplas palavras em caixa alta sem palavra-chave de imóvel
        r = _normalize_rural({
            "CAR": "", "NIRF": "", "CCIR": "", "NUMERO_INCRA": "", "SIGEF": "",
            "DENOMINACAORURAL": "JOAO FICTICIO DA SILVA",
            "ACIDENTEGEOGRAFICO": "",
        })
        assert r.tem_denominacao_rural is True
        assert r.denominacao_rural_sanitizada == ""

    def test_denominacao_com_cpf_removida(self):
        r = _normalize_rural({
            "CAR": "", "NIRF": "", "CCIR": "", "NUMERO_INCRA": "", "SIGEF": "",
            "DENOMINACAORURAL": "Proprietario CPF 000.000.000-00",
            "ACIDENTEGEOGRAFICO": "",
        })
        assert r.denominacao_rural_sanitizada == ""


# ---------------------------------------------------------------------------
# 20. Relatórios não contêm PII (varredura anti-PII básica)
# ---------------------------------------------------------------------------

class TestAntiPII:
    def test_is_pii_string_cpf(self):
        assert _is_pii_string("123.456.789-00") is True

    def test_is_pii_string_cnpj(self):
        assert _is_pii_string("12.345.678/0001-99") is True

    def test_is_pii_string_rotulo(self):
        assert _is_pii_string("CPF do contribuinte") is True

    def test_is_pii_string_clean(self):
        assert _is_pii_string("Fazenda Bela Vista") is False

    def test_record_dict_sem_pii(self):
        raw = raw_rural(matricula=2000)
        raw["CONTRIBUINTE"] = "NOME FICTICIO"
        rec = process_record(raw, CNS_FICTICIO, "test.json")
        d = record_to_dict(rec)
        saida = str(d)
        assert "NOME FICTICIO" not in saida
        assert "contribuinte" not in saida.lower() or "contribuinte" not in d


# ---------------------------------------------------------------------------
# 21. Duplicidades são detectadas
# ---------------------------------------------------------------------------

class TestDuplicidades:
    def _make_records(self) -> list:
        raws = [
            raw_urbano(matricula=1),
            raw_urbano(matricula=1),   # duplicata
            raw_urbano(matricula=2),
            raw_rural(matricula=1000),
        ]
        return [process_record(r, CNS_FICTICIO, "test.json") for r in raws]

    def test_duplicidade_detectada(self):
        records = self._make_records()
        metrics = compute_metrics(records)
        assert 1 in metrics["matriculas_duplicadas"]
        assert metrics["matriculas_duplicadas"][1] == 2

    def test_sem_duplicidade(self):
        raws = [raw_urbano(matricula=i) for i in range(1, 5)]
        records = [process_record(r, CNS_FICTICIO, "test.json") for r in raws]
        metrics = compute_metrics(records)
        assert len(metrics["matriculas_duplicadas"]) == 0


# ---------------------------------------------------------------------------
# 22. Matrículas faltantes são calculadas
# ---------------------------------------------------------------------------

class TestMatriculasFaltantes:
    def test_faltantes_detectadas(self):
        # Matrículas 1, 2, 4, 5 → faltante: 3
        raws = [
            raw_urbano(matricula=1),
            raw_urbano(matricula=2),
            raw_urbano(matricula=4),
            raw_urbano(matricula=5),
        ]
        records = [process_record(r, CNS_FICTICIO, "test.json") for r in raws]
        metrics = compute_metrics(records)
        assert 3 in metrics["matriculas_faltantes"]

    def test_sem_faltantes_sequencia_continua(self):
        raws = [raw_urbano(matricula=i) for i in range(1, 6)]
        records = [process_record(r, CNS_FICTICIO, "test.json") for r in raws]
        metrics = compute_metrics(records)
        assert metrics["matriculas_faltantes"] == []


# ---------------------------------------------------------------------------
# Extras: sanitize helpers
# ---------------------------------------------------------------------------

class TestSanitizeHelpers:
    def test_sanitize_cep_formatado(self):
        assert _sanitize_cep("75600-000") == "75600-000"

    def test_sanitize_cep_digits(self):
        assert _sanitize_cep("75600000") == "75600-000"

    def test_sanitize_cep_invalido(self):
        assert _sanitize_cep("abc") == ""

    def test_sanitize_bairro_ok(self):
        assert _sanitize_bairro("SETOR CENTRAL") == "SETOR CENTRAL"

    def test_sanitize_bairro_vazio(self):
        assert _sanitize_bairro("") == ""
