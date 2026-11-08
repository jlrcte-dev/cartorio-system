"""Modelos .service/.timer do verificador: renderização, estrutura e systemd-analyze.

A verificação estrutural roda em qualquer plataforma. ``systemd-analyze verify`` roda
onde existir (Linux com systemd, como o runner do CI) e é pulado no Windows.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.ops import cli
from app.ops.units import UnitParamsError, load_params, render_template, render_units

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "deploy" / "ops"
LAB = load_params((TEMPLATES / "lab.params").read_text(encoding="utf-8"))


def _sections(text: str) -> dict[str, list[tuple[str, str]]]:
    """Parser mínimo de unidade: aceita chave repetida (ex.: dois EnvironmentFile=)."""
    sections: dict[str, list[tuple[str, str]]] = {}
    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections[current] = []
            continue
        key, _, value = line.partition("=")
        sections[current].append((key, value))
    return sections


def _values(section: list[tuple[str, str]], key: str) -> list[str]:
    return [v for k, v in section if k == key]


def test_lab_params_render_three_units_with_cross_references() -> None:
    units = render_units(TEMPLATES, LAB)
    assert sorted(units) == [
        "cartorio-lab-ops-alert.service",
        "cartorio-lab-ops-check.service",
        "cartorio-lab-ops-check.timer",
    ]
    for text in units.values():
        assert "@" not in text.replace("postgresql@", "")

    check = _sections(units["cartorio-lab-ops-check.service"])
    assert _values(check["Unit"], "OnFailure") == ["cartorio-lab-ops-alert.service"]
    assert _values(check["Service"], "Type") == ["oneshot"]
    assert _values(check["Service"], "EnvironmentFile") == [
        "/etc/cartorio-lab/ops.env",
        "/etc/cartorio-lab/db.env",
    ]
    [exec_start] = _values(check["Service"], "ExecStart")
    assert exec_start.startswith("/opt/cartorio-lab/current/.venv/bin/python -m app.ops.cli check")
    assert _values(check["Service"], "ProtectSystem") == ["strict"]
    assert _values(check["Service"], "NoNewPrivileges") == ["yes"]

    timer = _sections(units["cartorio-lab-ops-check.timer"])
    assert _values(timer["Timer"], "Unit") == ["cartorio-lab-ops-check.service"]
    assert _values(timer["Timer"], "OnCalendar") == ["*:0/30"]
    assert _values(timer["Timer"], "OnBootSec") == ["10min"]
    assert _values(timer["Install"], "WantedBy") == ["timers.target"]

    alert = _sections(units["cartorio-lab-ops-alert.service"])
    [alert_exec] = _values(alert["Service"], "ExecStart")
    # Acionada só por falha: relatório saudável anterior não pode silenciar o alerta.
    assert " alert --expect-failure --report /var/lib/cartorio-lab-ops/last-check.json " in (
        alert_exec
    )


def test_check_schedule_is_independent_from_the_backup_timer() -> None:
    timer = _sections(render_units(TEMPLATES, LAB)["cartorio-lab-ops-check.timer"])
    directives = [value for section in timer.values() for _, value in section]
    assert directives and not any("backup" in value for value in directives)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("RELEASE_DIR", "opt/relativo"),
        ("PYTHON", "/opt/x/python --flag"),
        ("CONFIG_FILE", "/etc/%n.env"),  # % é especificador do systemd
        ("UNIT_PREFIX", "Cartorio Ops"),
        ("SERVICE_USER", "root;rm"),
        ("CHECK_CALENDAR", "*:0/30\nExecStart=/bin/sh"),
    ],
)
def test_invalid_parameter_values_are_refused(key: str, value: str) -> None:
    with pytest.raises(UnitParamsError) as info:
        render_units(TEMPLATES, {**LAB, key: value})
    assert f"{key}: valor inválido" in info.value.problems


def test_missing_and_unknown_parameters_are_refused() -> None:
    params = {k: v for k, v in LAB.items() if k != "PYTHON"} | {"EXTRA": "x"}
    with pytest.raises(UnitParamsError) as info:
        render_units(TEMPLATES, params)
    assert "PYTHON: ausente" in info.value.problems
    assert "EXTRA: desconhecido" in info.value.problems


def test_placeholder_without_value_is_refused() -> None:
    with pytest.raises(UnitParamsError):
        render_template("ExecStart=@NAO_EXISTE@", LAB)


def test_params_file_format_errors() -> None:
    with pytest.raises(UnitParamsError):
        load_params("UNIT_PREFIX=a\nUNIT_PREFIX=b\n")
    with pytest.raises(UnitParamsError):
        load_params("sem-igual\n")


def test_render_units_cli_writes_files(tmp_path: Path, capsys) -> None:
    code = cli.main(
        [
            "render-units",
            "--templates",
            str(TEMPLATES),
            "--params",
            str(TEMPLATES / "lab.params"),
            "--out",
            str(tmp_path),
        ]
    )
    assert code == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "cartorio-lab-ops-alert.service",
        "cartorio-lab-ops-check.service",
        "cartorio-lab-ops-check.timer",
    ]
    assert (tmp_path / "cartorio-lab-ops-check.timer").read_bytes().count(b"\r\n") == 0


def test_example_config_has_no_secret_and_lab_values_only() -> None:
    text = (TEMPLATES / "ops.env.example").read_text(encoding="utf-8")
    assert "DATABASE_URL=" not in text.replace("# DATABASE_URL", "")
    assert "homol" not in text and "192.168." not in text
    assert "CARTORIO_OPS_BACKUP_MAX_AGE_HOURS=" in text


_SYSTEMD_ANALYZE = shutil.which("systemd-analyze") if sys.platform == "linux" else None
# No job postgres-gate a verificação é prova obrigatória: ausente, falha em vez de pular.
_REQUIRE_SYSTEMD_ANALYZE = os.environ.get("CARTORIO_OPS_REQUIRE_SYSTEMD_ANALYZE") == "1"


@pytest.mark.skipif(
    _SYSTEMD_ANALYZE is None and not _REQUIRE_SYSTEMD_ANALYZE,
    reason="systemd-analyze indisponível nesta plataforma",
)
def test_rendered_units_pass_systemd_analyze_verify(tmp_path: Path) -> None:
    assert _SYSTEMD_ANALYZE, "CARTORIO_OPS_REQUIRE_SYSTEMD_ANALYZE=1 exige systemd-analyze"
    import grp
    import pwd

    params = {
        **LAB,
        "UNIT_PREFIX": "cartorio-ci-ops",
        "SERVICE_USER": pwd.getpwuid(os.getuid()).pw_name,
        "SERVICE_GROUP": grp.getgrgid(os.getgid()).gr_name,
        "RELEASE_DIR": str(REPO_ROOT),
        "PYTHON": sys.executable,
        "CONFIG_FILE": str(TEMPLATES / "ops.env.example"),
        "DB_ENV_FILE": str(TEMPLATES / "ops.env.example"),
        "STATE_DIR_NAME": "cartorio-ci-ops",
    }
    for name, text in render_units(TEMPLATES, params).items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    files = sorted(str(p) for p in tmp_path.iterdir())
    result = subprocess.run(
        ["systemd-analyze", "verify", "--man=no", *files],
        env={**os.environ, "SYSTEMD_UNIT_PATH": f"{tmp_path}:"},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
