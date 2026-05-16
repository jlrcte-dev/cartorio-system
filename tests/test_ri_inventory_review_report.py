"""Tests for export_ri_inventory_review_report.py.

Covers: no PII in output, ordering, column projection, duplicate classification,
INCRA-without-georref routing, georref-direct separation, summary stats.
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "local_tools"))

from export_ri_inventory_review_report import (  # noqa: I001
    _build_select_cols,
    _classify_duplicates,
    _db_summary_stats,
    _fetch,
    _project,
    _run_anti_pii_scan,
    _scan_file_for_pii,
    _text_has_pii,
    _write_csv,
    _TECH_COMPARE_COLS,
    INSTITUTIONAL_TOTAL,
    MISSING_MATRICULAS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE ri_matriculas_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_registro TEXT,
    matricula_numero INTEGER,
    nome_imovel_sanitizado TEXT,
    municipio TEXT,
    area_texto_original TEXT,
    area_valor_normalizado REAL,
    area_unidade TEXT,
    is_rural INTEGER,
    tem_georreferenciamento INTEGER,
    georreferenciamento_detectado_direto INTEGER NOT NULL DEFAULT 0,
    georreferenciamento_inferido_por_fonte INTEGER NOT NULL DEFAULT 0,
    georreferenciamento_valor TEXT,
    tem_incra INTEGER,
    incra_codigo TEXT,
    tem_nirf INTEGER,
    nirf_codigo TEXT,
    tem_reserva INTEGER,
    reserva_valor TEXT,
    fonte_relatorio TEXT,
    pagina_origem INTEGER,
    ordem_no_relatorio INTEGER,
    hash_bloco_origem TEXT,
    status_extracao TEXT,
    observacoes_tecnicas_sem_pii TEXT,
    created_at TEXT,
    UNIQUE(fonte_relatorio, matricula_numero, hash_bloco_origem)
);

CREATE TABLE ri_inventory_duplicates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    matricula_numero INTEGER,
    ocorrencias INTEGER,
    fontes TEXT,
    observacao TEXT
);
"""


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(_DDL)
    return conn


def _insert(
    conn: sqlite3.Connection,
    matricula: int,
    fonte: str = "rural.pdf",
    pagina: int = 1,
    ordem: int = 1,
    georref: int = 0,
    georref_direto: int = 0,
    georref_inferido: int = 0,
    incra: int = 0,
    incra_cod: str | None = None,
    nirf: int = 0,
    nirf_cod: str | None = None,
    reserva: int | None = 0,
    reserva_val: str | None = "Não",
    status: str = "ok",
    obs: str = "",
    nome: str = "Sítio Ficticio",
    municipio: str = "Terezópolis de Goiás",
    area_txt: str = "",
    area_val: float | None = None,
    hash_val: str | None = None,
    tipo: str = "M",
) -> None:
    h = hash_val or f"H-{matricula:06x}"
    conn.execute(
        """
        INSERT OR IGNORE INTO ri_matriculas_inventory (
            tipo_registro, matricula_numero, nome_imovel_sanitizado, municipio,
            area_texto_original, area_valor_normalizado, area_unidade, is_rural,
            tem_georreferenciamento, georreferenciamento_detectado_direto,
            georreferenciamento_inferido_por_fonte, georreferenciamento_valor,
            tem_incra, incra_codigo, tem_nirf, nirf_codigo,
            tem_reserva, reserva_valor, fonte_relatorio,
            pagina_origem, ordem_no_relatorio, hash_bloco_origem,
            status_extracao, observacoes_tecnicas_sem_pii, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            tipo, matricula, nome, municipio,
            area_txt, area_val, "ha", 1,
            georref, georref_direto,
            georref_inferido, "Sim" if georref_direto else None,
            incra, incra_cod, nirf, nirf_cod,
            reserva, reserva_val, fonte,
            pagina, ordem, h, status, obs, "2026-01-01",
        ),
    )
    conn.commit()


def _insert_dup(
    conn: sqlite3.Connection,
    matricula: int,
    ocorrencias: int = 2,
    fontes: str = "rural.pdf",
) -> None:
    sql = (
        "INSERT INTO ri_inventory_duplicates "
        "(run_id, matricula_numero, ocorrencias, fontes, observacao) "
        "VALUES (?,?,?,?,?)"
    )
    conn.execute(sql, ("test", matricula, ocorrencias, fontes, "duplicidade_no_relatorio"))
    conn.commit()


# ---------------------------------------------------------------------------
# TestPiiDetection
# ---------------------------------------------------------------------------

class TestPiiDetection:
    def test_clean_text_returns_empty(self) -> None:
        assert _text_has_pii("Sítio Bom Retiro") == []

    def test_formatted_cpf_detected(self) -> None:
        alerts = _text_has_pii("CPF: 123.456.789-09")
        assert "CPF" in alerts

    def test_formatted_cnpj_detected(self) -> None:
        alerts = _text_has_pii("CNPJ: 12.345.678/0001-99")
        assert "CNPJ" in alerts

    def test_pii_keyword_detected(self) -> None:
        assert "PII_keyword" in _text_has_pii("proprietario da fazenda")
        assert "PII_keyword" in _text_has_pii("adquirente do imóvel")

    def test_incra_code_11digits_no_false_positive(self) -> None:
        # INCRA codes without formatting must NOT trigger CPF alert
        assert _text_has_pii("00010015002") == []
        assert _text_has_pii("93018000098") == []

    def test_incra_code_14digits_no_false_positive(self) -> None:
        # 14-digit INCRA codes must NOT trigger CNPJ alert
        assert _text_has_pii("93018000305004") == []
        assert _text_has_pii("00010002001303") == []

    def test_incra_dotted_format_no_false_positive(self) -> None:
        # INCRA with dots but not CPF/CNPJ structure
        assert _text_has_pii("001.005.00290004.0181") == []


class TestFilePiiScan:
    def test_clean_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.csv"
        f.write_text("matricula_numero,municipio\n100,Terezópolis\n", encoding="utf-8")
        assert _scan_file_for_pii(f) == []

    def test_cpf_in_file_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "pii.csv"
        f.write_text("dados\n123.456.789-09\n", encoding="utf-8")
        alerts = _scan_file_for_pii(f)
        assert any("CPF" in a for a in alerts)

    def test_incra_in_file_no_alert(self, tmp_path: Path) -> None:
        f = tmp_path / "incra.csv"
        f.write_text("matricula,incra_codigo\n100,93018000305004\n", encoding="utf-8")
        assert _scan_file_for_pii(f) == []


# ---------------------------------------------------------------------------
# TestBuildSelectCols
# ---------------------------------------------------------------------------

class TestBuildSelectCols:
    def test_v3_cols_included_when_present(self) -> None:
        conn = _make_conn()
        cols = _build_select_cols(conn)
        assert "georreferenciamento_detectado_direto" in cols
        assert "georreferenciamento_inferido_por_fonte" in cols

    def test_v3_cols_after_georref_valor(self) -> None:
        conn = _make_conn()
        cols = _build_select_cols(conn)
        gv_idx = cols.index("georreferenciamento_valor")
        direto_idx = cols.index("georreferenciamento_detectado_direto")
        assert direto_idx > gv_idx

    def test_hash_not_in_select_cols(self) -> None:
        conn = _make_conn()
        cols = _build_select_cols(conn)
        assert "hash_bloco_origem" not in cols

    def test_no_pii_cols_in_select(self) -> None:
        conn = _make_conn()
        cols = _build_select_cols(conn)
        forbidden = {"proprietario", "cpf", "cnpj", "rg", "ci", "documento"}
        assert not forbidden.intersection(set(cols))


# ---------------------------------------------------------------------------
# TestFetch — ordering
# ---------------------------------------------------------------------------

class TestFetchOrdering:
    def test_ordered_by_matricula_asc(self) -> None:
        conn = _make_conn()
        _insert(conn, 500, pagina=10)
        _insert(conn, 100, pagina=20)
        _insert(conn, 300, pagina=5)
        cols = _build_select_cols(conn)
        rows = _fetch(conn, cols)
        nums = [r["matricula_numero"] for r in rows]
        assert nums == sorted(nums)

    def test_same_matricula_ordered_by_fonte(self) -> None:
        conn = _make_conn()
        _insert(conn, 100, fonte="zzz.pdf", hash_val="H-aaa001")
        _insert(conn, 100, fonte="aaa.pdf", hash_val="H-aaa002")
        cols = _build_select_cols(conn)
        rows = _fetch(conn, cols, "matricula_numero = 100")
        fontes = [r["fonte_relatorio"] for r in rows]
        assert fontes == sorted(fontes)

    def test_same_matricula_fonte_ordered_by_pagina(self) -> None:
        conn = _make_conn()
        _insert(conn, 200, pagina=99, ordem=1, hash_val="H-b00001")
        _insert(conn, 200, pagina=1, ordem=2, hash_val="H-b00002")
        cols = _build_select_cols(conn)
        rows = _fetch(conn, cols, "matricula_numero = 200")
        paginas = [r["pagina_origem"] for r in rows]
        assert paginas == sorted(paginas)


# ---------------------------------------------------------------------------
# TestProject
# ---------------------------------------------------------------------------

class TestProject:
    def test_project_restricts_cols(self) -> None:
        rows = [{"a": 1, "b": 2, "c": 3}]
        result = _project(rows, ["a", "c"])
        assert result == [{"a": 1, "c": 3}]

    def test_project_skips_missing_cols(self) -> None:
        rows = [{"a": 1}]
        result = _project(rows, ["a", "missing"])
        assert "missing" not in result[0]
        assert result[0]["a"] == 1


# ---------------------------------------------------------------------------
# TestClassifyDuplicates
# ---------------------------------------------------------------------------

class TestClassifyDuplicates:
    def test_exact_duplicate_same_hash(self) -> None:
        conn = _make_conn()
        # Two rows with same hash (only first survives UNIQUE, so simulate via dup table)
        _insert(conn, 300, hash_val="H-abc123")
        _insert_dup(conn, 300, ocorrencias=2)
        result = _classify_duplicates(conn)
        # Only 1 row in DB → classified as EXACT (same hash, 1 occurrence = counts as exact)
        assert len(result) == 1
        assert result[0]["matricula_numero"] == 300
        # With only 1 DB row, unique_hashes == 1 → EXACT_DUPLICATE
        assert result[0]["classificacao_duplicidade"] == "EXACT_DUPLICATE"

    def test_technical_duplicate_same_fields_different_hash(self) -> None:
        conn = _make_conn()
        _insert(conn, 400, hash_val="H-aa0001", pagina=10, ordem=1)
        _insert(conn, 400, hash_val="H-bb0002", pagina=20, ordem=1)
        _insert_dup(conn, 400, ocorrencias=2)
        result = _classify_duplicates(conn)
        assert len(result) == 1
        assert result[0]["classificacao_duplicidade"] == "TECHNICAL_DUPLICATE"
        assert result[0]["tem_diferenca_tecnica"] == 0

    def test_conflict_duplicate_different_fields(self) -> None:
        conn = _make_conn()
        _insert(conn, 500, hash_val="H-cc0001", nome="Sítio A", municipio="Cidade A")
        _insert(conn, 500, hash_val="H-dd0002", nome="Sítio B", municipio="Cidade B")
        _insert_dup(conn, 500, ocorrencias=2)
        result = _classify_duplicates(conn)
        assert len(result) == 1
        cls = result[0]["classificacao_duplicidade"]
        assert cls in ("CONFLICT_DUPLICATE", "NEEDS_MANUAL_REVIEW")
        assert result[0]["tem_diferenca_tecnica"] == 1
        assert result[0]["campos_tecnicos_diferentes"] != ""

    def test_paginas_field_populated(self) -> None:
        conn = _make_conn()
        _insert(conn, 600, hash_val="H-ee0001", pagina=5)
        _insert(conn, 600, hash_val="H-ee0002", pagina=15)
        _insert_dup(conn, 600, ocorrencias=2)
        result = _classify_duplicates(conn)
        assert "5" in result[0]["paginas"]
        assert "15" in result[0]["paginas"]

    def test_no_pii_in_classified_output(self) -> None:
        conn = _make_conn()
        _insert(conn, 700, hash_val="H-ff0001", nome="Sítio X")
        _insert(conn, 700, hash_val="H-ff0002", nome="Sítio Y")
        _insert_dup(conn, 700, ocorrencias=2)
        result = _classify_duplicates(conn)
        for row in result:
            text = " ".join(str(v) for v in row.values())
            assert _text_has_pii(text) == []


# ---------------------------------------------------------------------------
# TestWriteCsv
# ---------------------------------------------------------------------------

class TestWriteCsv:
    def test_creates_file_with_header(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        rows = [{"matricula_numero": 1, "municipio": "TestCity"}]
        _write_csv(path, rows, ["matricula_numero", "municipio"])
        assert path.exists()
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            data = list(reader)
        assert data[0]["matricula_numero"] == "1"
        assert data[0]["municipio"] == "TestCity"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "a" / "b" / "out.csv"
        _write_csv(path, [], ["col"])
        assert path.exists()


# ---------------------------------------------------------------------------
# TestGeorefDirect
# ---------------------------------------------------------------------------

class TestGeorefDirect:
    def test_only_direct_georref_in_report(self) -> None:
        conn = _make_conn()
        _insert(conn, 10, georref=1, georref_direto=1, hash_val="H-g00001")
        _insert(conn, 20, georref=0, georref_direto=0, hash_val="H-g00002")
        _insert(conn, 30, georref=1, georref_direto=0, georref_inferido=1, hash_val="H-g00003")
        cols = _build_select_cols(conn)
        rows = _fetch(conn, cols, "georreferenciamento_detectado_direto = 1")
        nums = {r["matricula_numero"] for r in rows}
        assert nums == {10}

    def test_georref_inferido_not_in_direct_report(self) -> None:
        conn = _make_conn()
        _insert(conn, 40, georref=1, georref_inferido=1, hash_val="H-gi0001")
        cols = _build_select_cols(conn)
        rows = _fetch(conn, cols, "georreferenciamento_detectado_direto = 1")
        assert not rows


# ---------------------------------------------------------------------------
# TestIncraWithoutGeoref
# ---------------------------------------------------------------------------

class TestIncraWithoutGeoref:
    def test_incra_no_georref_in_report(self) -> None:
        conn = _make_conn()
        _insert(conn, 50, incra=1, incra_cod="93018000099888", georref=0,
                hash_val="H-i00001")
        _insert(conn, 60, incra=1, incra_cod="93018000099777", georref=1,
                georref_direto=1, hash_val="H-i00002")
        _insert(conn, 70, incra=0, georref=0, hash_val="H-i00003")
        cols = _build_select_cols(conn)
        rows = _fetch(conn, cols, "tem_incra = 1 AND tem_georreferenciamento = 0")
        nums = {r["matricula_numero"] for r in rows}
        assert 50 in nums
        assert 60 not in nums  # has georref
        assert 70 not in nums  # no INCRA

    def test_incra_code_not_triggering_pii_in_output(self, tmp_path: Path) -> None:
        conn = _make_conn()
        _insert(conn, 80, incra=1, incra_cod="00010015002", georref=0, hash_val="H-i00004")
        cols = _build_select_cols(conn)
        rows = _fetch(conn, cols, "tem_incra = 1 AND tem_georreferenciamento = 0")
        out = tmp_path / "incra_test.csv"
        _write_csv(out, _project(rows, cols), cols)
        assert _scan_file_for_pii(out) == []


# ---------------------------------------------------------------------------
# TestDbSummaryStats
# ---------------------------------------------------------------------------

class TestDbSummaryStats:
    def _populated_conn(self) -> sqlite3.Connection:
        conn = _make_conn()
        _insert(conn, 1, georref=1, georref_direto=1, incra=1, nirf=0,
                reserva=0, hash_val="H-s00001")
        _insert(conn, 2, georref=0, incra=1, incra_cod="93018000099", hash_val="H-s00002",
                obs="incra_sem_georef_explicito")
        _insert(conn, 3, georref=0, incra=0, nirf=1, reserva=1, hash_val="H-s00003")
        _insert(conn, 4, status="needs_review", hash_val="H-s00004")
        _insert(conn, 5, status="area_ambigua", hash_val="H-s00005")
        return conn

    def test_unique_matriculas_count(self) -> None:
        conn = self._populated_conn()
        s = _db_summary_stats(conn)
        assert s["unique_matriculas"] == 5

    def test_georref_direto_count(self) -> None:
        conn = self._populated_conn()
        s = _db_summary_stats(conn)
        assert s["georref_direto"] == 1

    def test_incra_sem_georref_count(self) -> None:
        conn = self._populated_conn()
        s = _db_summary_stats(conn)
        assert s["incra_sem_georef"] == 1

    def test_nirf_valido_count(self) -> None:
        conn = self._populated_conn()
        s = _db_summary_stats(conn)
        assert s["nirf_valido"] == 1

    def test_status_counts(self) -> None:
        conn = self._populated_conn()
        s = _db_summary_stats(conn)
        assert s["status_needs_review"] == 1
        assert s["status_area_ambigua"] == 1

    def test_reserva_counts(self) -> None:
        conn = self._populated_conn()
        s = _db_summary_stats(conn)
        assert s["reserva_sim"] == 1
        assert s["reserva_nao"] >= 1


# ---------------------------------------------------------------------------
# TestRunAntiPiiScan
# ---------------------------------------------------------------------------

class TestRunAntiPiiScan:
    def test_clean_files_all_empty_alerts(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.csv"
        f2 = tmp_path / "b.csv"
        f1.write_text("matricula_numero,municipio\n1,CityX\n", encoding="utf-8")
        f2.write_text("matricula_numero,status\n2,ok\n", encoding="utf-8")
        results = _run_anti_pii_scan([f1, f2])
        assert results["a.csv"] == []
        assert results["b.csv"] == []

    def test_pii_file_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.csv"
        f.write_text("col\n123.456.789-09\n", encoding="utf-8")
        results = _run_anti_pii_scan([f])
        assert results["bad.csv"] != []

    def test_incra_codes_not_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "incra.csv"
        f.write_text(
            "matricula_numero,incra_codigo\n"
            "100,93018000305004\n"
            "200,00010015002\n",
            encoding="utf-8",
        )
        results = _run_anti_pii_scan([f])
        assert results["incra.csv"] == []

    def test_nonexistent_file_skipped(self, tmp_path: Path) -> None:
        ghost = tmp_path / "ghost.csv"
        results = _run_anti_pii_scan([ghost])
        assert results == {}


# ---------------------------------------------------------------------------
# TestConstants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_institutional_total(self) -> None:
        assert INSTITUTIONAL_TOTAL == 3523

    def test_missing_matriculas(self) -> None:
        assert set(MISSING_MATRICULAS) == {1431, 1490, 2804, 2974}

    def test_tech_compare_cols_no_pii(self) -> None:
        forbidden = {"proprietario", "cpf", "cnpj", "rg", "ci", "nome"}
        assert not forbidden.intersection(set(c.lower() for c in _TECH_COMPARE_COLS))
