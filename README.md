# Sistema do Cartório

Backend independente do **Cartório Costa Teixeira**. O foco principal a partir de
Maio/2026 é o **Módulo de Auditoria da Serventia** — diagnóstico, inventário,
evidências e preparação para vistoria (Provimento CNJ nº 213/2026, Classe 3).

O módulo financeiro (Finance Core v1.2) está preservado e em backlog futuro.

O sistema **não substitui** o Engegraph (ERP cartorial existente) e **não**
compartilha código, banco ou credenciais com outros projetos. Integrações
futuras ocorrem por exports estruturados.

## Foco atual — Módulo de Auditoria

- [`docs/AUDIT_MODULE_ROADMAP.md`](docs/AUDIT_MODULE_ROADMAP.md) — **Roadmap
  principal:** 12 fases, Sprint 1 (Scanner Read-Only), critérios de aceite.
- [`docs/modules/audit.md`](docs/modules/audit.md) — Visão do módulo: princípios,
  estrutura de código, entidades, fases.
- [`docs/modules/audit_file_scanner.md`](docs/modules/audit_file_scanner.md) —
  Scanner Read-Only: guia de uso, exemplos, saídas, limitações, segurança.
- [`docs/AUDIT_READ_ONLY_POLICY.md`](docs/AUDIT_READ_ONLY_POLICY.md) — Política
  read-only: o que o sistema pode e não pode fazer.

## Documentação técnica do sistema

- [`docs/architecture.md`](docs/architecture.md) — visão geral, stack, layout e
  princípios de design.
- [`docs/roadmap.md`](docs/roadmap.md) — prioridade atual, etapas concluídas e
  backlog futuro.
- [`docs/decisions.md`](docs/decisions.md) — decisões técnicas (D-01 a D-22).
- [`docs/finance.md`](docs/finance.md) — Finance Core v1.2 (backlog futuro).
- [`docs/how_to_run.md`](docs/how_to_run.md) — instalação, banco, servidor, testes.
- [`docs/testing.md`](docs/testing.md) — fixtures, isolamento e cobertura por área.
- [`docs/operations/engegraph.md`](docs/operations/engegraph.md) — Engegraph:
  contexto operacional, backup, suporte e pendências técnicas.

## Adequação regulatória (Provimento CNJ nº 213/2026 — Classe 3)

- [`docs/ROADMAP_CNJ213.md`](docs/ROADMAP_CNJ213.md) — Roadmap estratégico: 6
  trilhas, planos emergencial/30/90/180 dias e maturidade.
- [`docs/CNJ_213_COMPLIANCE_PLAN.md`](docs/CNJ_213_COMPLIANCE_PLAN.md) — Matriz de
  45 requisitos Classe 3 com gaps e evidências necessárias.
- [`docs/CNJ_213_ALIGNMENT.md`](docs/CNJ_213_ALIGNMENT.md) — Como o módulo de
  auditoria apoia diretamente cada requisito do Provimento.
- [`docs/INFRASTRUCTURE_ROADMAP.md`](docs/INFRASTRUCTURE_ROADMAP.md) — Situação
  atual, VMs sugeridas, VLANs, backup e plano de migração.
- [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md) — Registro de riscos ativos.
- [`docs/RISK_REGISTER_MODEL.md`](docs/RISK_REGISTER_MODEL.md) — Modelo de campos
  e enums para registro de riscos.
- [`docs/VISITATION_READINESS_CHECKLIST.md`](docs/VISITATION_READINESS_CHECKLIST.md)
  — Checklist de 73 itens para prontidão da vistoria.
- [`docs/VISITATION_READINESS_PLAN.md`](docs/VISITATION_READINESS_PLAN.md) — Plano
  de ação semana a semana para chegar à vistoria preparado.
- [`docs/TECHNICAL_DOSSIER_STRUCTURE.md`](docs/TECHNICAL_DOSSIER_STRUCTURE.md) —
  Estrutura do dossiê técnico com modelos de ata e índice de hashes.
- [`docs/OPERATING_FLOWS_AUDIT_PLAN.md`](docs/OPERATING_FLOWS_AUDIT_PLAN.md) —
  Plano de auditoria de fluxos operacionais da serventia.
- [`docs/architecture/target_infrastructure.md`](docs/architecture/target_infrastructure.md)
  — Arquitetura-alvo: VMs, VLANs, segmentação e plano de restauração.

## Requisitos

- **Python 3.12.x** (obrigatório — `pyproject.toml` exige `>=3.12,<3.13`).
- `pip` ou `uv`.

> **Atenção:** o `.python-version` direciona `pyenv`/`mise` para a versão correta.

## Setup rápido

```bash
# 1. Venv
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 2. Dependências
pip install -e ".[dev]"

# 3. Variáveis de ambiente
cp .env.example .env

# 4. Banco (Alembic é a única fonte de DDL)
alembic upgrade head

# 5. Servidor
uvicorn app.main:app --reload
```

API: <http://localhost:8000> · Swagger: <http://localhost:8000/docs> ·
Healthcheck: <http://localhost:8000/api/v1/health>

## Validação

```bash
ruff check .
ruff format --check .
pytest tests/ -v
```

## Estrutura do projeto

```text
cartorio-system/
├── alembic/                 # migrations
├── app/
│   ├── core/                # config, logging, errors
│   ├── db/                  # session, base
│   ├── modules/
│   │   ├── finance/         # Finance Core v1.2 (backlog futuro)
│   │   └── audit/           # Módulo de Auditoria (foco atual)
│   ├── interfaces/api/v1/   # router HTTP
│   └── main.py
├── tests/
├── docs/                    # documentação técnica + operacional + regulatória
├── exports/audit/           # artefatos do módulo de auditoria
├── exports/atlas/           # exports estruturados (futuros)
├── .env.example
├── pyproject.toml
└── README.md
```

## Integração com sistemas externos

A integração com outros sistemas (ex.: Atlas) ocorre **exclusivamente** por
dados estruturados (JSON/CSV) ou por chamadas explícitas a APIs. Nenhum banco,
credencial ou código é compartilhado diretamente.
