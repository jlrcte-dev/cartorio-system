# Módulo de Auditoria — app/modules/audit/

> **Prioridade:** Este é o módulo principal de desenvolvimento do Cartório System
> a partir de Maio/2026. O módulo financeiro está preservado em backlog futuro.

Última atualização: 2026-05-04

---

## Objetivo

O módulo de auditoria (`app/modules/audit/`) é a ferramenta interna de diagnóstico,
inventário, análise e governança da serventia.

Ele permite:

- varrer a estrutura de arquivos e pastas do servidor sem alterar nada
- coletar metadados e identificar riscos documentais
- registrar achados, evidências e ações corretivas
- gerar relatórios, checklists e dossiê técnico para vistoria
- apoiar a adequação ao Provimento CNJ nº 213/2026 (Classe 3)

A construção é incremental e **read-only first**: cada fase entrega valor utilizável
ao final do desenvolvimento, e a fase inicial não modifica nenhum arquivo do servidor.

Ver [`docs/audit/module_roadmap.md`](../audit/module_roadmap.md) para o roadmap
detalhado com todas as 12 fases, Sprint 1 e critérios de aceite.

Ver [`docs/audit/read_only_policy.md`](../audit/read_only_policy.md) para a política
de operação read-only e o que o sistema pode e não pode fazer.

---

## Contexto estratégico

O diagnóstico técnico da infraestrutura identificou riscos críticos:

- backup local sem dump consistente do banco do Engegraph
- disco de dados com pouco espaço livre
- ausência de VPN e controle de acesso formal
- dependência crítica do Engegraph sem plano de contingência
- digitalização descentralizada com histórico de perdas
- documentos sensíveis sem segregação adequada
- ausência de PSI, PCN e PRD próprios da serventia

A serventia foi classificada como **Classe 3** (Provimento CNJ 213/2026) e será
vistoriada em breve. O módulo de auditoria é a ferramenta imediata para diagnosticar,
evidenciar e preparar a serventia para essa vistoria.

---

## Princípios

1. **Read-only first.** A primeira fase não modifica nenhum dado ou arquivo.
2. **Diagnóstico antes de intervenção.** O sistema entende, recomenda; nunca age sozinho.
3. **Geração de evidências.** Cada execução produz artefatos rastreáveis com timestamp e hash.
4. **Rastreabilidade.** Toda execução é registrada: quando, quem, parâmetros, resultados.
5. **Mínimo privilégio.** O scanner solicita apenas leitura. Erros de permissão são logados, não contornados.
6. **Proteção de dados sensíveis.** Conteúdo de arquivos nunca é lido na fase inicial. Dados pessoais nunca entram nos relatórios.
7. **Compatibilidade com Provimento CNJ 213/2026 Classe 3.** Relatórios formatados como evidência para dossiê.
8. **Uso prático ao final de cada sprint.** Nenhuma sprint é preparatória sem entregável.
9. **Funcionar sem o Atlas.** Módulo autossuficiente; integração com Atlas é futura e unidirecional.
10. **Separação entre servidor analisado e sistema.** O scanner roda no Cartório System; os artefatos ficam em `exports/audit/`, nunca no servidor analisado.

---

## Áreas de auditoria

| Área | Descrição |
| ------ | ----------- |
| `INFRASTRUCTURE` | Servidores, hardware, discos, sistema operacional |
| `BACKUP` | Políticas, ferramentas, janelas, testes de restauração |
| `ENGEGRAPH` | Banco, backup, suporte, acesso remoto, reinstalação |
| `NETWORK` | Roteador, portas expostas, VPN, acesso remoto |
| `ACCESS` | Usuários, grupos, permissões de pasta e sistema |
| `DOCUMENT` | Digitalização, organização documental, arquivos sensíveis |
| `LGPD` | Sigilo de dados pessoais, conformidade LGPD |
| `CONTINUITY` | Planos de contingência, dependências críticas, RTO/RPO |
| `OPERATIONAL` | Fluxos, POPs, procedimentos, treinamento |
| `SYSTEM` | Cartório System: banco, logs, exports, autenticação |
| `REGULATORY` | CNJ, ARPEN, ONR, SEDI, obrigações externas |

---

## Estrutura do módulo no código

```text
app/modules/audit/
├── __init__.py
├── scanner/                     # Sprint 1 — read-only ✅
│   ├── __init__.py
│   ├── file_scanner.py          # lógica de varredura (os.walk, sem open)
│   ├── models.py                # FileEntry, ScanResult (dataclasses)
│   ├── report.py                # geração de JSON, CSV, Markdown, manifest
│   └── cli.py                   # entry point CLI
├── findings/                    # Sprint 2 — AuditFinding CRUD ✅
│   ├── enums.py
│   ├── models.py
│   ├── rules.py
│   ├── schemas.py
│   ├── service.py
│   └── router.py
├── diagnosis/                   # Sprint 3 ✅ + Sprint 3.5 ✅ — DocumentDiagnosis
│   ├── __init__.py
│   ├── models.py                # DiagnosisCandidate, DiagnosisResult (Pydantic)
│   ├── rules.py                 # 7 regras DIAG-001..007 (metadados apenas)
│   ├── analyzer.py              # DocumentAnalyzer — carrega inventory, executa regras
│   ├── report.py                # geração de JSON, CSV, Markdown, manifest
│   └── cli.py                   # entry point CLI
└── (fases futuras: questionnaires/, actions/, reports/, dossier/)
```

---

## Implantação e operação

Para saber como executar o scanner no servidor real, organizar artefatos,
gerar evidências e executar o diagnóstico, ver:

- [`docs/audit/deployment_and_operation.md`](../audit/deployment_and_operation.md)
  — procedimento completo, modos de execução, checklists, fluxo de evidências
- [`docs/decisions/technical_decisions.md`](../decisions/technical_decisions.md) (D-23) — decisão arquitetural: DocumentDiagnosis
  analisa artefatos, não o servidor diretamente
- [`docs/modules/audit_document_diagnosis_execution.md`](audit_document_diagnosis_execution.md)
  — guia completo para executar DocumentDiagnosis em dados reais, validar candidatos
  e iniciar revisão humana

---

### Fluxo operacional do módulo

```text
scanner → artefatos → diagnóstico → candidatos → revisão humana → AuditFinding → dossiê
```

| Etapa | O que acontece | Quem executa |
| ------ | -------------- | ------------ |
| scanner | os.walk read-only; coleta metadados | gestor (CLI) |
| artefatos | file_inventory.json/.csv, scan_summary.md, scan_manifest.json | automático |
| diagnóstico | DocumentDiagnosis lê o inventory.json (Sprint 3) | sistema |
| candidatos | listas por categoria: nomes genéricos, antigos, suspeitos | automático |
| revisão humana | gestor decide o que é achado real vs. falso positivo | gestor |
| AuditFinding | POST /api/v1/audit/findings com origin=SCANNER | gestor |
| dossiê | consolidação de artefatos + findings para vistoria (Fase 10) | futuro |

**Regra:** o diagnóstico nunca acessa o servidor diretamente — opera apenas sobre
os artefatos gerados pelo scanner. Ver D-23 em `decisions.md`.

---

## Sprint 1 — Scanner Read-Only ✅ (concluída e validada)

72 testes passando. Validado em ambiente real (1.539 arquivos, 0,428 s).
Ver guia completo em [`audit_file_scanner.md`](audit_file_scanner.md).

Para executar no servidor real, ver [`docs/audit/deployment_and_operation.md`](../audit/deployment_and_operation.md).

---

## Sprint 3 — DocumentDiagnosis Core v1 ✅ (concluída)

29 testes passando. 7 regras de diagnóstico implementadas (DIAG-001 a DIAG-007).
Análise metadata-only de `file_inventory.json` — nenhum arquivo original acessado.
Ver documentação em [`audit_document_diagnosis.md`](audit_document_diagnosis.md).

---

## Sprint 3.5 — DocumentDiagnosis Operational Hardening & Validation ✅ (concluída)

Hardening operacional e validação de segurança do DocumentDiagnosis:
- Documentação operacional completa para execução real controlada
- Auditoria de conformidade com contrato de segurança (metadata-only)
- Validação: 29/29 testes, ruff aprovado, segurança mantida
- Commit: `6e3a39f`

Ver guia operacional em [`audit_document_diagnosis_execution.md`](audit_document_diagnosis_execution.md).

**Próximo passo:** Execução Real Controlada do DocumentDiagnosis em dados da serventia,
com revisão humana de candidatos para criação de AuditFindings.

### Interface

```bash
python -m app.modules.audit.scanner.cli \
    --root "C:\Dados\Servidor" \
    --exclude "C:\Dados\Servidor\Sistema" \
    --max-depth 8 \
    --output-dir "exports/audit/scan-2026-05-04" \
    --run-name "scan-inicial"
```

### Saídas geradas em `exports/audit/<run-name>/`

| Arquivo | Conteúdo |
| --------- | ---------- |
| `file_inventory.json` | Lista completa de arquivos com metadados |
| `file_inventory.csv` | Versão tabular (UTF-8 com BOM para Excel) |
| `scan_summary.md` | Relatório legível: top maiores, extensões, antigos, suspeitos |
| `scan_manifest.json` | Rastreabilidade: quem, quando, parâmetros, hash SHA-256 |
| `errors.json` | Caminhos com acesso negado |

### Regras absolutas do scanner

- Nunca usar `open(file)` para ler conteúdo — apenas `os.stat()` e `os.path.*`
- Nunca usar `os.remove()`, `shutil.move()`, `os.rename()` ou equivalentes
- Nunca escrever nada fora de `exports/audit/`
- Erros de `PermissionError`: registrar em `errors.json` e continuar
- Caminhos absolutos do servidor: nunca entram em logs ou relatórios

---

## Sprint 2 — AuditFinding CRUD

Após o Scanner validado em uso real:

### Entidades

#### AuditFinding

| Campo | Tipo | Descrição |
| ------- | ------ | ----------- |
| `id` | UUID | Identificador único |
| `title` | str | Título curto (máx. 80 chars) |
| `description` | str | Descrição detalhada |
| `category` | enum | Área auditada |
| `severity` | enum | CRITICAL / HIGH / MEDIUM / LOW / INFO |
| `probability` | enum | HIGH / MEDIUM / LOW |
| `impact` | enum | HIGH / MEDIUM / LOW |
| `priority` | enum | URGENT / HIGH / MEDIUM / LOW |
| `status` | enum | OPEN / IN_PROGRESS / RESOLVED / ACCEPTED / CLOSED |
| `origin` | enum | SCANNER / MANUAL / TECHNICAL_REPORT / CHECKLIST / INTERVIEW / CNJ_MAPPING / BACKUP_LOG / DISK_SCAN / NETWORK_REVIEW / POLICY_REVIEW / OTHER |
| `cnj_requirement` | str | Requisito CNJ 213/2026 relacionado (opcional) |
| `evidence_summary` | str | Resumo das evidências |
| `recommendation` | str | Ação recomendada |
| `owner` | str | Responsável sugerido |
| `due_date` | date | Prazo (opcional) |
| `created_at` | datetime | Timestamp de criação |
| `updated_at` | datetime | Timestamp de última atualização |
| `created_by` | str | Usuário que registrou |

**Regra:** achados nunca são deletados — apenas atualizados de status (rastreabilidade).

#### AuditEvidence

| Campo | Tipo | Descrição |
| ------- | ------ | ----------- |
| `id` | UUID | Identificador único |
| `finding_id` | UUID | Achado ao qual pertence |
| `evidence_type` | enum | OBSERVATION / SCREENSHOT / REPORT / MEASUREMENT / SCAN_RESULT |
| `description` | str | Descrição da evidência |
| `source` | str | Origem |
| `collected_at` | datetime | Quando foi coletada |
| `collected_by` | str | Quem coletou |
| `file_reference` | str | Caminho relativo ao artefato (opcional) |
| `confidentiality_level` | enum | PUBLIC / INTERNAL / RESTRICTED / CONFIDENTIAL |

#### AuditAction

| Campo | Tipo | Descrição |
| ------- | ------ | ----------- |
| `id` | UUID | Identificador único |
| `finding_id` | UUID | Achado ao qual responde |
| `title` | str | Título da ação |
| `description` | str | Descrição detalhada |
| `priority` | enum | URGENT / HIGH / MEDIUM / LOW |
| `status` | enum | PENDING / IN_PROGRESS / COMPLETED / CANCELLED |
| `owner` | str | Responsável pela execução |
| `due_date` | date | Prazo |
| `completed_at` | datetime | Quando foi concluída (opcional) |
| `validation_notes` | str | Notas de validação |

---

## Roadmap de fases

| Fase | Nome | Status |
| ------ | ------ | -------- |
| 0 | Reposicionamento e documentação | ✅ |
| 1 | Scanner read-only de arquivos | ✅ Sprint 1 |
| 1b | AuditFinding CRUD | ✅ Sprint 2 |
| 1c | Procedimento Operacional Read-Only | ✅ Sprint 2.5 |
| 2 | Diagnóstico documental (DocumentDiagnosis) | ✅ Sprint 3 + Sprint 3.5 |
| 2.5 | Execução Real Controlada (próximo) | ⏳ |
| 4 | Human Review Workflow (Sprint 4 recomendado) | ⏳ |
| 3 | Auditoria de discos | ⏳ |
| 4 | Auditoria de backup | ⏳ |
| 5 | Auditoria de segurança local | ⏳ |
| 6 | Auditoria de rede | ⏳ |
| 7 | POPs, políticas e documentos | ⏳ |
| 8 | Fluxos operacionais | ⏳ |
| 9 | Motor de riscos e recomendações | ⏳ |
| 10 | Dossiê técnico e vistoria | ⏳ |
| 11 | Automação assistida futura | ⏳ |

---

## Saídas padronizadas

Todos os artefatos vão para `exports/audit/<run-name>/`:

```text
exports/audit/
├── <run-name>/
│   ├── manifest.json     # rastreabilidade completa
│   ├── inventory.json    # dados estruturados
│   ├── inventory.csv     # para análise em planilha
│   ├── report.md         # relatório legível
│   └── errors.json       # erros de acesso
└── catalog.csv           # índice de todas as execuções
```

---

## Relação com outros documentos

| Documento | Conteúdo |
| ----------- | ---------- |
| [`audit/module_roadmap.md`](../audit/module_roadmap.md) | Roadmap detalhado: 12 fases, Sprint 1 completa |
| [`audit/read_only_policy.md`](../audit/read_only_policy.md) | Política de operação: o que pode e não pode |
| [`regulatory/cnj_213/alignment.md`](../regulatory/cnj_213/alignment.md) | Como o módulo apoia a adequação ao Provimento |
| [`quality/risk_register_model.md`](../quality/risk_register_model.md) | Modelo de campos para AuditFinding |
| [`readiness/operating_flows_audit_plan.md`](../readiness/operating_flows_audit_plan.md) | Plano de auditoria de fluxos operacionais |
| [`operations/engegraph.md`](../operations/engegraph.md) | Contexto e pendências técnicas do Engegraph |
