# Sistema do Cartório

Backend independente do **Cartório Costa Teixeira**.

O sistema **não substitui** o Engegraph (ERP cartorial existente) e **não**
compartilha código, banco ou credenciais com outros projetos. Integrações
futuras ocorrem por exports estruturados.

## Por onde começar

| Se você quer... | Leia |
|---|---|
| Entender o estado real do sistema hoje | [`docs/reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md`](docs/reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md) |
| Saber o que vem a seguir | [`docs/roadmap.md`](docs/roadmap.md) — **roadmap geral autoritativo** |
| Entender a arquitetura | [`docs/architecture.md`](docs/architecture.md) |
| Navegar a documentação | [`docs/README.md`](docs/README.md) |

## Duas frentes ativas

**Atos notariais — `notas/inventarios` (maduro, em uso real).** Gera a
minuta-base de escritura pública de inventário e partilha a partir de entrada
estruturada, com cálculo determinístico em `Decimal` e saída em Markdown e ODT.
É o módulo com uso operacional comprovado — 6 casos reais entre maio e agosto de
2026. Ver [`docs/modules/notas_inventarios.md`](docs/modules/notas_inventarios.md)
e o [POP de uso](docs/modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md).

**Eixo regulatório — auditoria, LGPD, retenção e compliance.** Diagnóstico,
inventário, evidências e preparação para vistoria (Provimento CNJ nº 213/2026,
Classe 3). O scanner e o diagnóstico documental já foram executados em ambiente
real; a camada de compliance está construída e **ainda não ativada**.

O módulo financeiro (Finance Core v1.2) está preservado e em backlog futuro.

## Módulo de Auditoria

- [`docs/audit/module_roadmap.md`](docs/audit/module_roadmap.md) — **Roadmap
  principal:** 12 fases, Sprint 1 (Scanner Read-Only), critérios de aceite.
- [`docs/modules/audit.md`](docs/modules/audit.md) — Visão do módulo: princípios,
  estrutura de código, entidades, fases.
- [`docs/modules/audit_file_scanner.md`](docs/modules/audit_file_scanner.md) —
  Scanner Read-Only: guia de uso, exemplos, saídas, limitações, segurança.
- [`docs/audit/read_only_policy.md`](docs/audit/read_only_policy.md) — Política
  read-only: o que o sistema pode e não pode fazer.

## Documentação técnica do sistema

- [`docs/architecture.md`](docs/architecture.md) — visão geral, stack, layout e
  princípios de design.
- [`docs/roadmap.md`](docs/roadmap.md) — prioridade atual, etapas concluídas e
  backlog futuro.
- [`docs/decisions/technical_decisions.md`](docs/decisions/technical_decisions.md) — decisões técnicas (D-01 a D-23).
- [`docs/modules/finance.md`](docs/modules/finance.md) — Finance Core v1.2 (backlog futuro).
- [`docs/operations/how_to_run.md`](docs/operations/how_to_run.md) — instalação, banco, servidor, testes.
- [`docs/quality/testing.md`](docs/quality/testing.md) — fixtures, isolamento e cobertura por área.

## Adequação regulatória (Provimento CNJ nº 213/2026 — Classe 3)

- [`docs/regulatory/cnj_213/roadmap.md`](docs/regulatory/cnj_213/roadmap.md) — Roadmap estratégico: 6
  trilhas, planos emergencial/30/90/180 dias e maturidade.
- [`docs/regulatory/cnj_213/compliance_plan.md`](docs/regulatory/cnj_213/compliance_plan.md) — Matriz de
  45 requisitos Classe 3 com gaps e evidências necessárias.
- [`docs/regulatory/cnj_213/alignment.md`](docs/regulatory/cnj_213/alignment.md) — Como o módulo de
  auditoria apoia diretamente cada requisito do Provimento.
- [`docs/infrastructure/infrastructure_roadmap.md`](docs/infrastructure/infrastructure_roadmap.md) — Situação
  atual, VMs sugeridas, VLANs, backup e plano de migração.
- [`docs/quality/risk_register_model.md`](docs/quality/risk_register_model.md) — Modelo de campos
  e enums para registro de riscos.
- [`docs/readiness/visitation_readiness_checklist.md`](docs/readiness/visitation_readiness_checklist.md)
  — Checklist de 73 itens para prontidão da vistoria.
- [`docs/readiness/visitation_readiness_plan.md`](docs/readiness/visitation_readiness_plan.md) — Plano
  de ação semana a semana para chegar à vistoria preparado.
- [`docs/readiness/technical_dossier_structure.md`](docs/readiness/technical_dossier_structure.md) —
  Estrutura do dossiê técnico com modelos de ata e índice de hashes.
- [`docs/readiness/operating_flows_audit_plan.md`](docs/readiness/operating_flows_audit_plan.md) —
  Plano de auditoria de fluxos operacionais da serventia.
- [`docs/infrastructure/target_infrastructure.md`](docs/infrastructure/target_infrastructure.md)
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

Os mesmos comandos que o CI executa
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)):

```bash
ruff format --check .
ruff check .
pytest -q
alembic check
```

## Estrutura do projeto

```text
cartorio-system/
├── alembic/                 # migrations
├── app/
│   ├── core/                # config, logging, errors
│   ├── db/                  # session, base
│   ├── modules/
│   │   ├── notas/           # atos notariais — inventarios (CLI, em uso real)
│   │   ├── audit/           # scanner, diagnosis, findings
│   │   ├── compliance/      # Matriz INOVA, evidências, status indicativo
│   │   ├── lgpd/            # ações do plano LGPD
│   │   ├── retention/       # temporalidade documental (sem router)
│   │   └── finance/         # Finance Core v1.2 (backlog futuro)
│   ├── interfaces/api/v1/   # router HTTP
│   └── main.py
├── scripts/local_tools/     # pipeline do Registro de Imóveis (fora de app/)
├── tests/                   # 904 testes; golden files em tests/golden/
├── docs/                    # documentação técnica + operacional + regulatória
├── exports/audit/           # artefatos do módulo de auditoria
├── exports/atlas/           # exports estruturados (futuros)
├── .github/workflows/ci.yml # quality gate automático
├── .env.example
├── pyproject.toml
└── README.md
```

## Integração com sistemas externos

A integração com outros sistemas (ex.: Atlas) ocorre **exclusivamente** por
dados estruturados (JSON/CSV) ou por chamadas explícitas a APIs. Nenhum banco,
credencial ou código é compartilhado diretamente.
