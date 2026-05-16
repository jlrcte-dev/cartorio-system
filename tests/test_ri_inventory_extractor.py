"""
Testes sintéticos do extrator de matrículas rurais — v3.

IMPORTANTE: Todos os dados são FICTÍCIOS.
Nenhum dado pessoal real é usado neste arquivo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Caminho para o módulo local (não instalado no projeto principal)
sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "scripts" / "local_tools")
)

from extract_ri_rural_inventory import (  # noqa: I001
    _detect_duplicates,
    _extract_all_totals,
    _extract_nome_imovel,
    _extract_total_reportado,
    _hash_bloco,
    _is_pii_line,
    _normalize_area,
    _normalize_municipio,
    _normalize_nirf,
    _parse_block,
    _validate_sanitized,
)


# ---------------------------------------------------------------------------
# Helpers de blocos sintéticos (sem dados reais)
# ---------------------------------------------------------------------------

def bloco_minimo() -> list[str]:
    """Matrícula M 1 sem nome do imóvel, sem área, sem campos técnicos."""
    return [
        "M 1 Terezópolis de Goiás",
        "PROPRIETARIO FICTICIO CPF: 000.000.000-00",  # linha PII → descartada
        "Caract. Reserva Não",
        "Georef. Incra NIRF",
    ]


def bloco_fazenda_alvorada() -> list[str]:
    """Matrícula M 381 com Georef. Sim explícito, INCRA e nome de fazenda."""
    return [
        "M 381 Fazenda Alvorada 174,2522 HA Terezópolis de Goiás",
        "PROPRIETARIO FICTICIO CI. 9999999 SSP/GO",  # linha PII → descartada
        "Caract. Uma gleba de terras com a área de 174,2522ha no município de "
        "Terezópolis de Goiás Reserva Sim",
        "Georef. Sim Incra 93018000018482 NIRF Reserva Sim",
    ]


def bloco_nirf_presente() -> list[str]:
    """Matrícula M 500 com NIRF preenchido válido."""
    return [
        "M 500 Sítio Bela Vista Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Sim Incra 93018000099999 NIRF 12345678 Reserva Não",
    ]


def bloco_incra_sem_numero() -> list[str]:
    """Matrícula M 10 com rótulo 'Incra' mas sem código — não deve marcar tem_incra=True."""
    return [
        "M 10 Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Incra NIRF",
    ]


def bloco_nirf_sem_numero() -> list[str]:
    """Matrícula M 20 com rótulo 'NIRF' mas sem código — não deve marcar tem_nirf=True."""
    return [
        "M 20 Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Sim Incra 93018000000001 NIRF",
    ]


def bloco_georef_vazio() -> list[str]:
    """Matrícula M 30 com linha Georef. sem nenhum indicador positivo."""
    return [
        "M 30 Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Incra NIRF",
    ]


def bloco_reserva_nao() -> list[str]:
    """Matrícula M 40 com 'Reserva Não' — deve preencher reserva_valor='Não'."""
    return [
        "M 40 Terezópolis de Goiás",
        "Caract. Uma gleba de terras no município de Terezópolis de Goiás Reserva Não",
        "Georef. Incra NIRF",
    ]


def bloco_area_ambigua() -> list[str]:
    """Matrícula M 50 com área em formato ambíguo (duas vírgulas)."""
    return [
        "M 50 Fazenda Esperança 174,25,22 HA Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Incra NIRF",
    ]


def bloco_transricao() -> list[str]:
    """Transcrição T 1001."""
    return [
        "T 1001 Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Incra NIRF",
    ]


def bloco_incra_sem_georref_explicito() -> list[str]:
    """
    Matrícula M 200 com INCRA válido mas SEM 'Sim' explícito em Georef.
    Cenário v3: tem_incra=True, tem_georreferenciamento=False (rural),
    observações devem incluir 'incra_sem_georef_explicito'.
    """
    return [
        "M 200 Fazenda Ficticia Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Incra 93018000099888 NIRF",  # INCRA com código mas SEM Sim
    ]


def bloco_nirf_zerado() -> list[str]:
    """Matrícula M 300 com NIRF composto somente por zeros — deve ser ignorado."""
    return [
        "M 300 Sítio Ficticio Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Sim Incra 93018000077777 NIRF 00000000 Reserva Não",
    ]


def bloco_nirf_zerado_6dig() -> list[str]:
    """Matrícula M 301 com NIRF de 6 zeros — deve ser ignorado."""
    return [
        "M 301 Sítio Ficticio Terezópolis de Goiás",
        "Caract. Reserva Não",
        "Georef. Sim Incra 93018000066666 NIRF 000000 Reserva Não",
    ]


# ---------------------------------------------------------------------------
# Testes: _is_pii_line
# ---------------------------------------------------------------------------

class TestIsPiiLine:
    def test_cpf_formatado(self):
        assert _is_pii_line("NOME FICTICIO CPF: 123.456.789-00")

    def test_cpf_sem_formatacao(self):
        assert _is_pii_line("12345678900")

    def test_ci_ssp(self):
        assert _is_pii_line("CI. 1234567 SSP/GO")

    def test_rg_label(self):
        assert _is_pii_line("RG. 9876543")

    def test_cnpj(self):
        assert _is_pii_line("CNPJ: 12.345.678/0001-99")

    def test_nome_caps_duas_palavras(self):
        # Nome em caixa alta — suspeito de ser proprietário
        assert _is_pii_line("JOAO FICTICIO")

    def test_linha_tecnica_nao_e_pii(self):
        assert not _is_pii_line("Caract. Uma gleba de terras")

    def test_georef_nao_e_pii(self):
        assert not _is_pii_line("Georef. Sim Incra 93018000018482 NIRF")

    def test_linha_registro_nao_e_pii(self):
        assert not _is_pii_line("M 381 Fazenda Alvorada Terezópolis de Goiás")

    def test_texto_tecnico_simples(self):
        assert not _is_pii_line("Reserva Não")


# ---------------------------------------------------------------------------
# Testes: _normalize_area
# ---------------------------------------------------------------------------

class TestNormalizeArea:
    def test_ha_simples(self):
        valor, unidade, ambigua = _normalize_area("174,2522 ha")
        assert abs(valor - 174.2522) < 0.001
        assert unidade == "ha"
        assert not ambigua

    def test_ha_milhar(self):
        valor, unidade, ambigua = _normalize_area("1.200,50 ha")
        assert abs(valor - 1200.50) < 0.001
        assert unidade == "ha"
        assert not ambigua

    def test_ha_inteiro(self):
        valor, unidade, ambigua = _normalize_area("500 ha")
        assert abs(valor - 500.0) < 0.001
        assert not ambigua

    def test_alqueire(self):
        valor, unidade, ambigua = _normalize_area("3 alqueires")
        assert abs(valor - 3.0) < 0.001
        assert unidade == "alqueire"

    def test_m2(self):
        valor, unidade, ambigua = _normalize_area("5000 m2")
        assert valor is not None
        assert unidade == "m2"

    def test_area_ambigua_duas_virgulas(self):
        # "174,25,22 HA" — múltiplas vírgulas: deve sinalizar ambiguidade
        valor, unidade, ambigua = _normalize_area("174,25,22 HA")
        assert ambigua
        assert valor is None  # conservador: não assumir interpretação

    def test_ausente(self):
        valor, unidade, ambigua = _normalize_area("")
        assert valor is None
        assert unidade is None
        assert not ambigua

    def test_texto_sem_unidade(self):
        valor, unidade, ambigua = _normalize_area("174,25 metros")
        assert valor is None  # "metros" não está no mapa de unidades reconhecidas


# ---------------------------------------------------------------------------
# Testes: _normalize_nirf
# ---------------------------------------------------------------------------

class TestNormalizeNirf:
    def test_none_retorna_false(self):
        tem, cod, obs = _normalize_nirf(None)
        assert not tem
        assert cod is None
        assert obs is None

    def test_vazio_retorna_false(self):
        tem, cod, obs = _normalize_nirf("")
        assert not tem
        assert cod is None

    def test_espacos_retorna_false(self):
        tem, cod, obs = _normalize_nirf("   ")
        assert not tem

    def test_zeros_6dig_ignorado(self):
        tem, cod, obs = _normalize_nirf("000000")
        assert not tem
        assert cod is None
        assert obs == "nirf_zerado_ignorado"

    def test_zeros_8dig_ignorado(self):
        tem, cod, obs = _normalize_nirf("00000000")
        assert not tem
        assert cod is None
        assert obs == "nirf_zerado_ignorado"

    def test_zeros_qualquer_tamanho_ignorado(self):
        for n in [3, 5, 9, 12]:
            tem, cod, obs = _normalize_nirf("0" * n)
            assert not tem, f"NIRF com {n} zeros deve ser ignorado"
            assert obs == "nirf_zerado_ignorado"

    def test_nirf_valido_com_digito_nao_zero(self):
        tem, cod, obs = _normalize_nirf("12345678")
        assert tem
        assert cod == "12345678"
        assert obs is None

    def test_nirf_valido_comecando_com_zero(self):
        # Se tem pelo menos um dígito não-zero → válido
        tem, cod, obs = _normalize_nirf("01234567")
        assert tem
        assert obs is None

    def test_nirf_com_letras_ambiguo(self):
        tem, cod, obs = _normalize_nirf("1234ABC")
        assert not tem
        assert obs == "nirf_ambiguo"

    def test_nirf_apenas_um_zero(self):
        # "0" com 3+ chars exigido pelo regex, mas se passado aqui → only-zeros → ignorado
        tem, cod, obs = _normalize_nirf("000")
        assert not tem
        assert obs == "nirf_zerado_ignorado"


# ---------------------------------------------------------------------------
# Testes: _extract_nome_imovel
# ---------------------------------------------------------------------------

class TestExtractNomeImovel:
    def test_fazenda_alvorada(self):
        # Residual após remover área e município deve ser o nome da fazenda
        denominacao = "Fazenda Alvorada 174,2522 HA Terezópolis de Goiás"
        nome, suspeito = _extract_nome_imovel(denominacao)
        assert "Fazenda Alvorada" in nome
        assert not suspeito

    def test_so_municipio(self):
        # Sem nome de imóvel — apenas município → deve retornar vazio
        denominacao = "Terezópolis de Goiás"
        nome, suspeito = _extract_nome_imovel(denominacao)
        assert nome == ""
        assert not suspeito

    def test_vazio(self):
        nome, suspeito = _extract_nome_imovel("")
        assert nome == ""
        assert not suspeito

    def test_nome_em_caps_suspeito(self):
        # ALL CAPS sem keyword de imóvel → suspeito de nome de pessoa
        denominacao = "JOAO SILVA FICTICIO"
        nome, suspeito = _extract_nome_imovel(denominacao)
        assert nome == ""
        assert suspeito

    def test_fazenda_em_caps_permitida(self):
        # ALL CAPS com keyword "FAZENDA" → nome de imóvel legítimo
        denominacao = "FAZENDA BOA VISTA 150 HA Terezópolis de Goiás"
        nome, suspeito = _extract_nome_imovel(denominacao)
        assert not suspeito
        assert "FAZENDA" in nome or "BOA" in nome

    def test_sitio(self):
        denominacao = "Sítio Boa Esperança Terezópolis de Goiás"
        nome, suspeito = _extract_nome_imovel(denominacao)
        assert not suspeito
        assert "Sítio" in nome or "Boa" in nome


# ---------------------------------------------------------------------------
# Testes: _parse_block
# ---------------------------------------------------------------------------

class TestParseBlock:
    def _parse(self, block, record_id=1, ordem=1, pagina=1,
                fonte="teste_ficticio.pdf", tipo="rural"):
        return _parse_block(block, record_id, ordem, pagina, fonte, tipo)

    def test_bloco_invalido_sem_tipo_numero(self):
        bloco = ["Linha sem padrão M/T + número"]
        assert self._parse(bloco) is None

    def test_bloco_vazio(self):
        assert self._parse([]) is None

    def test_bloco_minimo_campos_basicos(self):
        rec = self._parse(bloco_minimo())
        assert rec is not None
        assert rec["tipo_registro"] == "M"
        assert rec["matricula_numero"] == 1
        assert rec["municipio"] == "Terezópolis de Goiás"

    def test_bloco_minimo_sem_incra(self):
        rec = self._parse(bloco_minimo())
        assert not rec["tem_incra"]
        assert rec["incra_codigo"] is None

    def test_bloco_minimo_sem_nirf(self):
        rec = self._parse(bloco_minimo())
        assert not rec["tem_nirf"]
        assert rec["nirf_codigo"] is None

    def test_bloco_minimo_sem_georef(self):
        rec = self._parse(bloco_minimo())
        assert not rec["tem_georreferenciamento"]
        assert not rec["georreferenciamento_detectado_direto"]
        assert not rec["georreferenciamento_inferido_por_fonte"]

    def test_bloco_minimo_reserva_nao(self):
        rec = self._parse(bloco_minimo())
        assert rec["reserva_valor"] == "Não"
        assert rec["tem_reserva"] is False

    def test_bloco_fazenda_alvorada_nome(self):
        rec = self._parse(bloco_fazenda_alvorada())
        assert rec is not None
        assert rec["matricula_numero"] == 381
        # Nome do imóvel deve ser capturado (fazenda é keyword segura)
        assert "Fazenda Alvorada" in (rec["nome_imovel_sanitizado"] or "")

    def test_bloco_fazenda_alvorada_incra(self):
        rec = self._parse(bloco_fazenda_alvorada())
        assert rec["tem_incra"]
        assert rec["incra_codigo"] == "93018000018482"

    def test_bloco_fazenda_alvorada_georef_direto(self):
        """Georef. Sim explícito → detecção direta, não inferida."""
        rec = self._parse(bloco_fazenda_alvorada())
        assert rec["tem_georreferenciamento"]
        assert rec["georreferenciamento_detectado_direto"]
        assert not rec["georreferenciamento_inferido_por_fonte"]
        assert rec["georreferenciamento_valor"] == "Sim"

    def test_bloco_fazenda_alvorada_reserva_sim(self):
        rec = self._parse(bloco_fazenda_alvorada())
        assert rec["reserva_valor"] == "Sim"
        assert rec["tem_reserva"] is True

    def test_bloco_fazenda_alvorada_area(self):
        rec = self._parse(bloco_fazenda_alvorada())
        assert rec["area_valor_normalizado"] is not None
        assert abs(rec["area_valor_normalizado"] - 174.2522) < 0.001

    def test_incra_sem_numero_nao_marca_true(self):
        """'Incra' sem código numérico válido → tem_incra deve ser False."""
        rec = self._parse(bloco_incra_sem_numero())
        assert not rec["tem_incra"]
        assert rec["incra_codigo"] is None

    def test_nirf_sem_numero_nao_marca_true(self):
        """'NIRF' sem valor numérico → tem_nirf deve ser False."""
        rec = self._parse(bloco_nirf_sem_numero())
        assert not rec["tem_nirf"]
        assert rec["nirf_codigo"] is None

    # ------------------------------------------------------------------
    # Testes v3 — Georef. sem valor NÃO marca georreferenciamento
    # ------------------------------------------------------------------

    def test_georef_vazio_nao_marca_true(self):
        """'Georef.' sem Sim e sem INCRA → tem_georreferenciamento deve ser False."""
        rec = self._parse(bloco_georef_vazio())
        assert not rec["tem_georreferenciamento"]
        assert not rec["georreferenciamento_detectado_direto"]

    def test_incra_com_codigo_sem_sim_nao_marca_georref(self):
        """
        'Georef. Incra 93018000099888 NIRF' sem 'Sim' → georref=False (rural).
        Requisito v3: INCRA válido NÃO implica georreferenciamento.
        """
        rec = self._parse(bloco_incra_sem_georref_explicito())
        assert not rec["tem_georreferenciamento"]
        assert not rec["georreferenciamento_detectado_direto"]
        assert not rec["georreferenciamento_inferido_por_fonte"]

    def test_incra_valido_sem_sim_marca_tem_incra(self):
        """Mesmo sem Sim, INCRA com código válido → tem_incra=True."""
        rec = self._parse(bloco_incra_sem_georref_explicito())
        assert rec["tem_incra"]
        assert rec["incra_codigo"] == "93018000099888"

    def test_incra_sem_georref_obs_registrada(self):
        """
        INCRA com código mas sem Georef. Sim → observação
        'incra_sem_georef_explicito' deve aparecer.
        """
        rec = self._parse(bloco_incra_sem_georref_explicito())
        obs = rec.get("observacoes_tecnicas_sem_pii") or ""
        assert "incra_sem_georef_explicito" in obs

    def test_incra_com_sim_nao_gera_obs_incra_sem_georref(self):
        """
        Quando Sim está presente (bloco_fazenda_alvorada), NÃO deve gerar
        'incra_sem_georef_explicito' nas observações.
        """
        rec = self._parse(bloco_fazenda_alvorada())
        obs = rec.get("observacoes_tecnicas_sem_pii") or ""
        assert "incra_sem_georef_explicito" not in obs

    # ------------------------------------------------------------------
    # Testes v3 — Relatório georref: georreferenciamento inferido por fonte
    # ------------------------------------------------------------------

    def test_tipo_georref_marca_georref_true(self):
        """No relatório 'georref', todos os registros devem ter tem_georreferenciamento=True."""
        bloco = ["M 1 Terezópolis de Goiás", "Caract. Reserva Não", "Georef. Incra NIRF"]
        rec = self._parse(bloco, tipo="georref")
        assert rec["tem_georreferenciamento"]

    def test_tipo_georref_sem_sim_marca_inferido_por_fonte(self):
        """
        No relatório georref sem Sim explícito → georreferenciamento_inferido_por_fonte=True
        e georreferenciamento_detectado_direto=False.
        """
        bloco = ["M 1 Terezópolis de Goiás", "Caract. Reserva Não", "Georef. Incra NIRF"]
        rec = self._parse(bloco, tipo="georref")
        assert rec["georreferenciamento_inferido_por_fonte"]
        assert not rec["georreferenciamento_detectado_direto"]

    def test_tipo_georref_com_sim_marca_direto_nao_inferido(self):
        """
        No relatório georref COM Sim explícito → detecção direta,
        inferido_por_fonte=False (Sim já confirma).
        """
        bloco = [
            "M 50 Fazenda Ficticia Terezópolis de Goiás",
            "Caract. Reserva Não",
            "Georef. Sim Incra 93018000012345 NIRF",
        ]
        rec = self._parse(bloco, tipo="georref")
        assert rec["tem_georreferenciamento"]
        assert rec["georreferenciamento_detectado_direto"]
        assert not rec["georreferenciamento_inferido_por_fonte"]

    def test_tipo_rural_incra_sem_sim_nao_marca_inferido(self):
        """Rural com INCRA mas sem Sim → georref false, nenhum tipo de inferência."""
        rec = self._parse(bloco_incra_sem_georref_explicito(), tipo="rural")
        assert not rec["tem_georreferenciamento"]
        assert not rec["georreferenciamento_detectado_direto"]
        assert not rec["georreferenciamento_inferido_por_fonte"]

    # ------------------------------------------------------------------
    # Testes v3 — NIRF zerado ignorado
    # ------------------------------------------------------------------

    def test_nirf_zerado_8dig_nao_marca_true(self):
        """NIRF '00000000' → tem_nirf=False."""
        rec = self._parse(bloco_nirf_zerado())
        assert not rec["tem_nirf"]
        assert rec["nirf_codigo"] is None

    def test_nirf_zerado_obs_registrada(self):
        """NIRF zerado → 'nirf_zerado_ignorado' em observacoes_tecnicas_sem_pii."""
        rec = self._parse(bloco_nirf_zerado())
        obs = rec.get("observacoes_tecnicas_sem_pii") or ""
        assert "nirf_zerado_ignorado" in obs

    def test_nirf_zerado_6dig_nao_marca_true(self):
        """NIRF '000000' (6 dígitos) → tem_nirf=False."""
        rec = self._parse(bloco_nirf_zerado_6dig())
        assert not rec["tem_nirf"]
        assert rec["nirf_codigo"] is None

    def test_nirf_zerado_georref_ainda_detectado(self):
        """Bloco com NIRF zerado ainda deve ter Georef. corretamente detectado."""
        rec = self._parse(bloco_nirf_zerado())
        assert rec["tem_georreferenciamento"]  # Sim explícito presente
        assert rec["georreferenciamento_detectado_direto"]

    # ------------------------------------------------------------------
    # Testes originais — preservados
    # ------------------------------------------------------------------

    def test_reserva_nao_preenche_valor(self):
        """'Reserva Não' → reserva_valor='Não', tem_reserva=False."""
        rec = self._parse(bloco_reserva_nao())
        assert rec["reserva_valor"] == "Não"
        assert rec["tem_reserva"] is False

    def test_nirf_presente_com_codigo(self):
        rec = self._parse(bloco_nirf_presente())
        assert rec["tem_nirf"]
        assert rec["nirf_codigo"] == "12345678"

    def test_area_ambigua_status(self):
        rec = self._parse(bloco_area_ambigua())
        assert rec["status_extracao"] == "area_ambigua"
        assert "area_ambigua" in (rec["observacoes_tecnicas_sem_pii"] or "")
        assert rec["area_valor_normalizado"] is None  # conservador

    def test_tipo_transricao(self):
        rec = self._parse(bloco_transricao())
        assert rec["tipo_registro"] == "T"
        assert rec["matricula_numero"] == 1001

    def test_pii_nao_exposta_na_saida(self):
        """Após parse de bloco com PII, os campos de saída não devem conter dados pessoais."""
        rec = self._parse(bloco_fazenda_alvorada())
        assert rec is not None
        # Garantir que nenhum campo óbvio de PII existe
        for campo_proibido in ("cpf", "nome", "rg", "cnpj"):
            assert campo_proibido not in rec

    def test_pagina_origem_registrada(self):
        rec = self._parse(bloco_minimo(), pagina=3)
        assert rec["pagina_origem"] == 3

    def test_ordem_registrada(self):
        rec = self._parse(bloco_minimo(), ordem=42)
        assert rec["ordem_no_relatorio"] == 42

    def test_hash_bloco_formato(self):
        rec = self._parse(bloco_minimo())
        h = rec["hash_bloco_origem"]
        assert h.startswith("H-")
        assert len(h) == 8  # "H-" + 6 chars hex
        import re
        digits_run = re.findall(r"\d+", h)
        assert all(len(d) <= 6 for d in digits_run), "hash tem sequência de dígitos longa"

    def test_novos_campos_presentes_no_registro(self):
        """Registros devem incluir os dois novos campos de georref."""
        rec = self._parse(bloco_minimo())
        assert "georreferenciamento_detectado_direto" in rec
        assert "georreferenciamento_inferido_por_fonte" in rec


# ---------------------------------------------------------------------------
# Testes: _detect_duplicates
# ---------------------------------------------------------------------------

class TestDetectDuplicates:
    def test_sem_duplicidades(self):
        records = [
            {"matricula_numero": 1, "fonte_relatorio": "test.pdf"},
            {"matricula_numero": 2, "fonte_relatorio": "test.pdf"},
        ]
        dups = _detect_duplicates(records, "run-001")
        assert dups == []

    def test_com_duplicidade(self):
        records = [
            {"matricula_numero": 100, "fonte_relatorio": "test.pdf"},
            {"matricula_numero": 100, "fonte_relatorio": "test.pdf"},
            {"matricula_numero": 200, "fonte_relatorio": "test.pdf"},
        ]
        dups = _detect_duplicates(records, "run-001")
        assert len(dups) == 1
        assert dups[0]["matricula_numero"] == 100
        assert dups[0]["ocorrencias"] == 2

    def test_duplicidade_entre_fontes(self):
        records = [
            {"matricula_numero": 50, "fonte_relatorio": "rural.pdf"},
            {"matricula_numero": 50, "fonte_relatorio": "georref.pdf"},
        ]
        dups = _detect_duplicates(records, "run-002")
        assert len(dups) == 1
        assert "rural.pdf" in dups[0]["fontes"]
        assert "georref.pdf" in dups[0]["fontes"]

    def test_multiplas_duplicidades(self):
        records = [
            {"matricula_numero": 1, "fonte_relatorio": "test.pdf"},
            {"matricula_numero": 1, "fonte_relatorio": "test.pdf"},
            {"matricula_numero": 2, "fonte_relatorio": "test.pdf"},
            {"matricula_numero": 2, "fonte_relatorio": "test.pdf"},
            {"matricula_numero": 3, "fonte_relatorio": "test.pdf"},
        ]
        dups = _detect_duplicates(records, "run-003")
        assert len(dups) == 2
        matriculas_dup = {d["matricula_numero"] for d in dups}
        assert matriculas_dup == {1, 2}


# ---------------------------------------------------------------------------
# Testes: _validate_sanitized
# ---------------------------------------------------------------------------

class TestValidateSanitized:
    def _make_record(self, **kwargs) -> dict:
        base = {
            "record_id": 1,
            "tipo_registro": "M",
            "matricula_numero": 100,
            "nome_imovel_sanitizado": "Fazenda Ficticia",
            "municipio": "Terezópolis de Goiás",
            "area_texto_original": "50 ha",
            "area_valor_normalizado": 50.0,
            "area_unidade": "ha",
            "is_rural": True,
            "tem_georreferenciamento": False,
            "georreferenciamento_detectado_direto": False,
            "georreferenciamento_inferido_por_fonte": False,
            "georreferenciamento_valor": None,
            "tem_incra": False,
            "incra_codigo": None,
            "tem_nirf": False,
            "nirf_codigo": None,
            "tem_reserva": False,
            "reserva_valor": "Não",
            "fonte_relatorio": "teste.pdf",
            "pagina_origem": 1,
            "ordem_no_relatorio": 1,
            "hash_bloco_origem": "H-abc123",
            "status_extracao": "ok",
            "observacoes_tecnicas_sem_pii": "",
        }
        base.update(kwargs)
        return base

    def test_registro_valido_passa(self):
        records = [self._make_record()]
        # Não deve lançar exceção nem chamar sys.exit
        _validate_sanitized(records)

    def test_campo_proibido_falha(self):
        records = [self._make_record(cpf="000.000.000-00")]
        with pytest.raises(SystemExit):
            _validate_sanitized(records)

    def test_campo_proibido_nome_falha(self):
        records = [self._make_record(nome="Nome Ficticio")]
        with pytest.raises(SystemExit):
            _validate_sanitized(records)

    def test_cpf_em_municipio_falha(self):
        # CPF embutido em campo de texto → deve ser bloqueado
        records = [self._make_record(municipio="Cidade 000.000.000-00")]
        with pytest.raises(SystemExit):
            _validate_sanitized(records)

    def test_matricula_nao_numerico_falha(self):
        records = [self._make_record(matricula_numero="ABC123")]
        with pytest.raises(SystemExit):
            _validate_sanitized(records)

    def test_incra_codigo_longo_nao_bloqueia(self):
        # Código INCRA com 14 dígitos NÃO deve bloquear (é whitelisted)
        records = [self._make_record(
            incra_codigo="93018000018482",
            tem_incra=True,
        )]
        _validate_sanitized(records)  # Não deve lançar SystemExit

    def test_nirf_zerado_em_obs_nao_expoe_pii(self):
        """Observação 'nirf_zerado_ignorado' é técnica e não contém PII."""
        records = [self._make_record(
            observacoes_tecnicas_sem_pii="nirf_zerado_ignorado; area_ausente",
        )]
        _validate_sanitized(records)  # Deve passar sem bloquear


# ---------------------------------------------------------------------------
# Testes: _extract_total_reportado
# ---------------------------------------------------------------------------

class TestExtractTotalReportado:
    def test_total_detectado(self):
        pages = ["FICHA TABULAR - ÁREA RURAL\nTotal: 3523\nOutro texto"]
        assert _extract_total_reportado(pages) == 3523

    def test_total_com_dois_pontos(self):
        pages = ["Total: 100\nRegistros"]
        assert _extract_total_reportado(pages) == 100

    def test_total_nao_encontrado(self):
        pages = ["Texto sem total aqui", "Outra página sem info"]
        assert _extract_total_reportado(pages) is None

    def test_total_na_segunda_pagina(self):
        pages = ["Primeira sem total", "Total: 500 registros"]
        assert _extract_total_reportado(pages) == 500

    def test_total_apos_terceira_pagina_ignorado(self):
        # Só busca nas primeiras 3 páginas
        pages = ["p1", "p2", "p3", "Total: 999"]
        assert _extract_total_reportado(pages) is None


# ---------------------------------------------------------------------------
# Testes: _extract_all_totals
# ---------------------------------------------------------------------------

class TestExtractAllTotals:
    def test_total_unico_candidato(self):
        """Total que aparece só uma vez e é >= 100 → classificado como candidato global."""
        pages = [
            "Texto de cabeçalho\nTotal: 3523\nOutros dados",
            "Página 2 com dados",
        ]
        result = _extract_all_totals(pages)
        assert "3523" in result
        assert result["3523"]["ocorrencias"] == 1
        assert result["3523"]["classificacao"] == "total_global_candidato"

    def test_total_repetido_classificado_como_subtotal(self):
        """Total que aparece 6+ vezes → classificado como subtotal_repetido."""
        pages = [f"Total: 100 dados na página {i}" for i in range(10)]
        result = _extract_all_totals(pages)
        assert "100" in result
        assert result["100"]["ocorrencias"] == 10
        assert result["100"]["classificacao"] == "subtotal_repetido"

    def test_multiplos_totais(self):
        """Deve detectar múltiplos valores de Total na mesma análise."""
        pages = [
            "Total: 100 início",
            "Total: 100 segunda ocorrência",
            "Total: 100 terceira",
            "Total: 100 quarta",
            "Total: 100 quinta",
            "Total: 100 sexta",
            "Página final Total: 3500 global",
        ]
        result = _extract_all_totals(pages)
        assert "100" in result
        assert result["100"]["classificacao"] == "subtotal_repetido"
        assert "3500" in result

    def test_paginas_vazias_sem_erro(self):
        """Páginas sem padrão Total: não devem causar erro."""
        pages = ["Texto sem total", "Outra página"]
        result = _extract_all_totals(pages)
        assert result == {}

    def test_total_100_repetido_e_subtotal(self):
        """Simula o cenário do relatório rural: 'Total: 100' repetido em cabeçalhos."""
        pages = [f"FICHA TABULAR\nTotal: 100\nPágina {i}" for i in range(8)]
        result = _extract_all_totals(pages)
        assert "100" in result
        assert result["100"]["classificacao"] == "subtotal_repetido"

    def test_resultado_nao_expoe_texto(self):
        """A análise deve conter apenas números e classificações — sem texto bruto."""
        pages = ["Total: 200 algum texto irrelevante"]
        result = _extract_all_totals(pages)
        assert "200" in result
        info = result["200"]
        # Verificar que apenas campos técnicos existem
        allowed_keys = {"valor", "ocorrencias", "paginas", "classificacao"}
        assert set(info.keys()) == allowed_keys


# ---------------------------------------------------------------------------
# Testes: _normalize_municipio
# ---------------------------------------------------------------------------

class TestNormalizeMunicipio:
    def test_terezopolis_aceito(self):
        assert _normalize_municipio("Terezópolis de Goiás") == "Terezópolis de Goiás"

    def test_terezopolis_sem_acento(self):
        assert _normalize_municipio("Terezopolis de Goias") == "Terezópolis de Goiás"

    def test_terezopolis_garbled(self):
        # Texto garbled por interleaving do PDF
        assert _normalize_municipio("TerezóReservapolisNão de Goiás") == "Terezópolis de Goiás"

    def test_vazio_default(self):
        assert _normalize_municipio("") == "Terezópolis de Goiás"

    def test_goianapolis(self):
        assert _normalize_municipio("Goianápolis") == "Goianápolis"

    def test_municipio_invalido_default(self):
        assert _normalize_municipio("Reserva") == "Terezópolis de Goiás"


# ---------------------------------------------------------------------------
# Testes: _hash_bloco
# ---------------------------------------------------------------------------

class TestHashBloco:
    def test_formato_prefixo(self):
        h = _hash_bloco(["M 1 Terezópolis de Goiás"])
        assert h.startswith("H-")

    def test_comprimento(self):
        h = _hash_bloco(["M 1 Terezópolis de Goiás"])
        assert len(h) == 8  # "H-" + 6 hex chars

    def test_deterministico(self):
        block = ["M 100 Fazenda Ficticia", "Caract. Reserva Não"]
        assert _hash_bloco(block) == _hash_bloco(block)

    def test_diferentes_blocos_diferentes_hashes(self):
        h1 = _hash_bloco(["M 1 Terezópolis de Goiás"])
        h2 = _hash_bloco(["M 2 Terezópolis de Goiás"])
        assert h1 != h2

    def test_sem_sequencia_longa_de_digitos(self):
        import re
        for block in [bloco_minimo(), bloco_fazenda_alvorada(), bloco_nirf_presente()]:
            h = _hash_bloco(block)
            digits = re.findall(r"\d+", h)
            assert all(len(d) <= 6 for d in digits), (
                f"Hash {h!r} contém sequência de dígitos >= 7 — risco de falso positivo CPF/CNPJ"
            )
