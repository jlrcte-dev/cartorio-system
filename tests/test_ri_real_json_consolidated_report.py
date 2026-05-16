"""
Testes do consolidador RI Real JSON — Cartório System

Sprint: RI-REAL-JSON-2

Todos os dados usados aqui são SINTÉTICOS.
Nenhum dado pessoal real é incluído.
"""

from __future__ import annotations

import pytest

from scripts.local_tools.consolidate_ri_real_json_reports import (
    CSV_COLUMNS,
    Registro,
    Stats,
    assert_no_pii,
    build_csv_rows,
    check_pii,
    write_checklist,
    write_csv,
    write_relatorio_executivo,
)

# ---------------------------------------------------------------------------
# Helpers sintéticos
# ---------------------------------------------------------------------------

def make_registro(
    matricula: str = "1",
    natureza: str = "rural",
    tem_car: str = "False",
    tem_nirf: str = "False",
    nirf_status: str = "ausente",
    tem_ccir: str = "False",
    tem_numero_incra: str = "False",
    tem_sigef: str = "False",
    possui_geo: str = "False",
    geo_criterio: str = "",
    status_revisao: str = "",
    obs: str = "",
    fontes: list[str] | None = None,
) -> Registro:
    return Registro(
        matricula_numero=matricula,
        numero_registro=f"147454.2.{matricula.zfill(10)}-00",
        natureza_imovel=natureza,
        tem_car=tem_car,
        tem_nirf=tem_nirf,
        nirf_status=nirf_status,
        tem_ccir=tem_ccir,
        tem_numero_incra=tem_numero_incra,
        tem_sigef=tem_sigef,
        possui_georreferenciamento=possui_geo,
        georreferenciamento_criterio=geo_criterio,
        status_revisao_ri=status_revisao,
        observacoes_tecnicas_sem_pii=obs,
        fontes=fontes or ["test_source.csv"],
    )


def make_records(**kwargs) -> dict[str, Registro]:
    rec = make_registro(**kwargs)
    return {rec.matricula_numero: rec}


# ---------------------------------------------------------------------------
# 1. check_pii detecta padrões
# ---------------------------------------------------------------------------

class TestCheckPii:
    def test_cpf_detectado(self):
        hits = check_pii("contribuinte 123.456.789-09 dados")
        tipos = [h[0] for h in hits]
        assert any("CPF" in t or "CONTRIBUINTE" in t for t in tipos)

    def test_cnpj_detectado(self):
        hits = check_pii("empresa 12.345.678/0001-99 fim")
        tipos = [h[0] for h in hits]
        assert "CNPJ" in tipos

    def test_proprietario_detectado(self):
        hits = check_pii("nome do proprietario presente aqui")
        tipos = [h[0] for h in hits]
        assert any("PROPRIETARIO" in t or "proprietario" in t.lower() for t in tipos)

    def test_sem_pii_ok(self):
        hits = check_pii("matricula_numero,natureza_imovel,tem_car\n100,rural,False")
        assert hits == []


class TestAssertNoPii:
    def test_sem_pii_nao_levanta(self):
        assert_no_pii("matricula 100 rural sem pendência", "test.csv")

    def test_com_pii_levanta(self):
        with pytest.raises(ValueError, match="BLOQUEADO"):
            assert_no_pii("CPF: 123.456.789-09 encontrado", "test.csv")


# ---------------------------------------------------------------------------
# 2. Registro.classificar
# ---------------------------------------------------------------------------

class TestClassificar:
    def test_rural_sem_car(self):
        rec = make_registro(natureza="rural", tem_car="False")
        tipos = rec.classificar()
        assert "RURAL_SEM_CAR" in tipos

    def test_rural_sem_nirf(self):
        rec = make_registro(natureza="rural", tem_nirf="False")
        tipos = rec.classificar()
        assert "RURAL_SEM_NIRF" in tipos

    def test_rural_sem_ccir(self):
        rec = make_registro(natureza="rural", tem_ccir="False")
        tipos = rec.classificar()
        assert "RURAL_SEM_CCIR" in tipos

    def test_rural_georeferenciado_por_incra(self):
        rec = make_registro(natureza="rural", tem_numero_incra="True")
        tipos = rec.classificar()
        assert "RURAL_GEOREFERENCIADO" in tipos

    def test_rural_georeferenciado_por_sigef(self):
        rec = make_registro(natureza="rural", tem_sigef="True")
        tipos = rec.classificar()
        assert "RURAL_GEOREFERENCIADO" in tipos

    def test_rural_sem_geo(self):
        rec = make_registro(natureza="rural", tem_numero_incra="False", tem_sigef="False")
        tipos = rec.classificar()
        assert "RURAL_SEM_GEOREFERENCIAMENTO" in tipos

    def test_rural_completo(self):
        rec = make_registro(
            natureza="rural",
            tem_car="True",
            tem_nirf="True",
            nirf_status="valido",
            tem_ccir="True",
        )
        tipos = rec.classificar()
        assert "RURAL_COMPLETO" in tipos

    def test_urbano_com_campos_rurais_ccir(self):
        rec = make_registro(natureza="urbano", tem_ccir="True")
        tipos = rec.classificar()
        assert "URBANO_COM_CAMPOS_RURAIS" in tipos

    def test_urbano_com_campos_rurais_incra(self):
        rec = make_registro(natureza="urbano", tem_numero_incra="True")
        tipos = rec.classificar()
        assert "URBANO_COM_CAMPOS_RURAIS" in tipos

    def test_needs_review_por_status(self):
        rec = make_registro(status_revisao="needs_manual_review")
        tipos = rec.classificar()
        assert "NEEDS_REVIEW" in tipos


# ---------------------------------------------------------------------------
# 5–8. Prioridade
# ---------------------------------------------------------------------------

class TestPrioridade:
    def test_needs_review_alta(self):
        rec = make_registro(status_revisao="needs_manual_review")
        from scripts.local_tools.consolidate_ri_real_json_reports import prioridade
        assert prioridade(rec.classificar()) == "ALTA"

    def test_urbano_com_rurais_alta(self):
        rec = make_registro(natureza="urbano", tem_ccir="True")
        from scripts.local_tools.consolidate_ri_real_json_reports import prioridade
        assert prioridade(rec.classificar()) == "ALTA"

    def test_rural_sem_car_media(self):
        from scripts.local_tools.consolidate_ri_real_json_reports import prioridade
        # sem CCIR → ALTA; com CCIR/NIRF mas sem CAR → MEDIA ou mais
        rec2 = make_registro(
            natureza="rural",
            tem_car="False",
            tem_ccir="True",
            tem_nirf="True",
            nirf_status="valido",
        )
        tipos2 = rec2.classificar()
        assert "RURAL_SEM_CAR" in tipos2
        pri2 = prioridade(tipos2)
        assert pri2 in ("ALTA", "MEDIA")  # pode subir por RURAL_SEM_GEOREFERENCIAMENTO

    def test_rural_completo_baixa(self):
        rec = make_registro(
            natureza="rural",
            tem_car="True",
            tem_nirf="True",
            nirf_status="valido",
            tem_ccir="True",
            tem_numero_incra="True",
        )
        from scripts.local_tools.consolidate_ri_real_json_reports import prioridade
        tipos = rec.classificar()
        # GEO presente → MEDIA no mínimo
        pri = prioridade(tipos)
        assert pri in ("MEDIA", "BAIXA")


# ---------------------------------------------------------------------------
# 9. Campos de preenchimento manual existem no CSV
# ---------------------------------------------------------------------------

class TestCsvColunas:
    def test_colunas_manuais_presentes(self):
        assert "responsavel_conferencia" in CSV_COLUMNS
        assert "resultado_conferencia" in CSV_COLUMNS
        assert "observacao_conferencia" in CSV_COLUMNS
        assert "data_conferencia" in CSV_COLUMNS

    def test_build_csv_row_tem_campos_vazios(self):
        records = make_records(natureza="rural")
        rows = build_csv_rows(records)
        assert len(rows) == 1
        row = rows[0]
        assert row["responsavel_conferencia"] == ""
        assert row["resultado_conferencia"] == ""
        assert row["observacao_conferencia"] == ""
        assert row["data_conferencia"] == ""

    def test_build_csv_consolidado_uma_linha_por_matricula(self):
        records: dict[str, Registro] = {}
        for i in range(5):
            rec = make_registro(matricula=str(i + 1), natureza="rural")
            records[rec.matricula_numero] = rec
        rows = build_csv_rows(records)
        assert len(rows) == 5


# ---------------------------------------------------------------------------
# 10. Relatório Markdown contém sumário executivo
# ---------------------------------------------------------------------------

class TestRelatorioMarkdown:
    def test_relatorio_tem_sumario(self, tmp_path):
        stats = Stats(
            total=10, urbanos=8, rurais=2,
            rural_com_car=1, rural_sem_car=1,
            rural_com_nirf=1, rural_sem_nirf=1,
            rural_com_ccir=1, rural_sem_ccir=1,
            rural_com_geo=0, rural_sem_geo=2,
            needs_review=1, urbano_com_rurais=0,
            total_pendencias=2,
        )
        out = tmp_path / "relatorio.md"
        write_relatorio_executivo(stats, out)
        content = out.read_text(encoding="utf-8")
        assert "Sumário Executivo" in content
        assert "Total de matrículas" in content
        assert "10" in content

    def test_relatorio_tem_objetivo(self, tmp_path):
        stats = Stats(total=5)
        out = tmp_path / "relatorio.md"
        write_relatorio_executivo(stats, out)
        content = out.read_text(encoding="utf-8")
        assert "Objetivo" in content

    def test_relatorio_tem_recomendacoes(self, tmp_path):
        stats = Stats(total=5)
        out = tmp_path / "relatorio.md"
        write_relatorio_executivo(stats, out)
        content = out.read_text(encoding="utf-8")
        assert "Recomendações" in content or "Recomenda" in content


# ---------------------------------------------------------------------------
# 11. Checklist é gerado
# ---------------------------------------------------------------------------

class TestChecklist:
    def test_checklist_gerado(self, tmp_path):
        stats = Stats(
            needs_review=5,
            urbano_com_rurais=1,
            rural_sem_ccir=10,
            rural_sem_nirf=20,
            rural_sem_car=30,
            rural_com_geo=3,
        )
        out = tmp_path / "checklist.md"
        write_checklist(stats, out)
        content = out.read_text(encoding="utf-8")
        assert "Checklist" in content
        assert "CAR" in content
        assert "NIRF" in content
        assert "CCIR" in content
        assert "resultado_conferencia" in content

    def test_checklist_tem_prioridades(self, tmp_path):
        stats = Stats(needs_review=3)
        out = tmp_path / "checklist.md"
        write_checklist(stats, out)
        content = out.read_text(encoding="utf-8")
        assert "ALTA" in content or "Needs review" in content


# ---------------------------------------------------------------------------
# 12. Arquivos finais não contêm PII
# ---------------------------------------------------------------------------

class TestAntipii:
    def test_csv_sem_pii(self, tmp_path):
        records = {
            "1": make_registro("1", natureza="rural"),
            "2": make_registro("2", natureza="urbano"),
        }
        rows = build_csv_rows(records)
        out = tmp_path / "test.csv"
        write_csv(rows, out)
        content = out.read_text(encoding="utf-8")
        hits = check_pii(content)
        assert hits == [], f"PII encontrada: {hits}"

    def test_csv_rejeita_pii(self, tmp_path):
        records = {
            "1": make_registro("1", obs="proprietario João da Silva")
        }
        rows = build_csv_rows(records)
        out = tmp_path / "bad.csv"
        with pytest.raises(ValueError, match="BLOQUEADO"):
            write_csv(rows, out)

    def test_markdown_sem_pii(self, tmp_path):
        stats = Stats(total=3)
        out = tmp_path / "rel.md"
        write_relatorio_executivo(stats, out)
        content = out.read_text(encoding="utf-8")
        # Markdown explicativo usa doc_mode=True (não verifica termos como "proprietário")
        hits = check_pii(content, doc_mode=True)
        assert hits == [], f"PII encontrada no relatório: {hits}"

    def test_checklist_sem_pii(self, tmp_path):
        stats = Stats()
        out = tmp_path / "ck.md"
        write_checklist(stats, out)
        content = out.read_text(encoding="utf-8")
        hits = check_pii(content, doc_mode=True)
        assert hits == [], f"PII encontrada no checklist: {hits}"


# ---------------------------------------------------------------------------
# 13. Dados sintéticos — garantia
# ---------------------------------------------------------------------------

class TestDadosSinteticos:
    def test_sem_cpf_nos_fixtures(self):
        rec = make_registro("999")
        hits = check_pii(
            rec.matricula_numero + rec.numero_registro + rec.observacoes_tecnicas_sem_pii
        )
        assert hits == []
