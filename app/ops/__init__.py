"""Continuidade operacional do Cartório System (CARTORIO-OPS-1).

Ferramentas de operação, fora dos módulos de domínio e sem importá-los:

- ``cli check``: verificador somente leitura (processo/API, PostgreSQL, Alembic, backup);
- ``cli alert``: emissão do alerta a partir do relatório do verificador;
- ``cli render-units``: modelos ``.service``/``.timer`` parametrizados;
- ``drill``: prova de recuperação em PostgreSQL descartável (bancada).

Contrato operacional: ``docs/operations/ops_verifier_runbook.md``.
"""
