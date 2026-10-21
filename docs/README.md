# Documentação — Cartório System

Índice principal da documentação, organizado por domínio documental.

> Esta pasta é organizada por domínio documental. Novos documentos devem ser adicionados
> na pasta correspondente, evitando arquivos soltos na raiz de `docs/`.

---

## 1. Governança e configuração

| Documento | Descrição |
|-----------|-----------|
| [`../CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](../CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md) | Documento completo de governança técnica, metodológica e operacional |
| [`../CLAUDE.md`](../CLAUDE.md) | Instrução operacional resumida para Claude Code |
| [`../README.md`](../README.md) | Visão geral do projeto, setup rápido e links principais |

---

## 2. Arquitetura

| Documento | Descrição |
|-----------|-----------|
| [`architecture.md`](architecture.md) | Visão geral, stack, camadas e princípios de design |
| [`infrastructure/infrastructure_roadmap.md`](infrastructure/infrastructure_roadmap.md) | Situação atual de infraestrutura, VMs, VLANs e plano de migração |
| [`infrastructure/target_infrastructure.md`](infrastructure/target_infrastructure.md) | Arquitetura-alvo: VMs, segmentação de rede e plano de restauração |

---

## 3. Módulos

| Módulo | Documento principal |
|--------|---------------------|
| Auditoria | [`modules/audit.md`](modules/audit.md) |
| Auditoria — Scanner | [`modules/audit_file_scanner.md`](modules/audit_file_scanner.md) |
| Auditoria — Findings | [`modules/audit_findings.md`](modules/audit_findings.md) |
| Auditoria — Diagnóstico | [`modules/audit_document_diagnosis.md`](modules/audit_document_diagnosis.md) |
| Auditoria — Execução do diagnóstico | [`modules/audit_document_diagnosis_execution.md`](modules/audit_document_diagnosis_execution.md) |
| Compliance | [`modules/compliance.md`](modules/compliance.md) |
| LGPD | [`modules/lgpd.md`](modules/lgpd.md) |
| Retenção | [`modules/retention.md`](modules/retention.md) |
| Finance | [`modules/finance.md`](modules/finance.md) |
| **Notas — Inventários** | [`modules/notas_inventarios.md`](modules/notas_inventarios.md) |
| **Notas — Checklist humano** | [`modules/notas_inventarios_checklist.md`](modules/notas_inventarios_checklist.md) |
| **Notas — POP de uso do gerador** | [`modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md`](modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md) |
| **Registro de Imóveis** | [`modules/registro_imoveis.md`](modules/registro_imoveis.md) |
| Coletor somente leitura do Drive | [`modules/drive_capture.md`](modules/drive_capture.md) — acesso real validado em smoke local da fonte piloto |
| Retrato de serviços por setor e status | [`modules/services_snapshot.md`](modules/services_snapshot.md) — atualização manual local, com indicadores de datas |
| **Registro de Imóveis — dicionário sanitizado** | [`ri_inventory/SANITIZED_DATA_DICTIONARY.md`](ri_inventory/SANITIZED_DATA_DICTIONARY.md) |

### Documentação operacional do módulo de auditoria

| Documento | Descrição |
|-----------|-----------|
| [`audit/module_roadmap.md`](audit/module_roadmap.md) | Roadmap das 12 fases, critérios de aceite, sprints |
| [`audit/deployment_and_operation.md`](audit/deployment_and_operation.md) | Procedimento completo de deployment e operação |
| [`audit/operational_procedure.md`](audit/operational_procedure.md) | Procedimento operacional detalhado (Sprint 2.5) |
| [`audit/read_only_policy.md`](audit/read_only_policy.md) | Política formal de operação read-only |

---

## 4. Regulatório

### CNJ 213/2026 — Classe 3

| Documento | Descrição |
|-----------|-----------|
| [`regulatory/cnj_213/roadmap.md`](regulatory/cnj_213/roadmap.md) | Roadmap estratégico: 6 trilhas, planos 7/30/90/180 dias |
| [`regulatory/cnj_213/compliance_plan.md`](regulatory/cnj_213/compliance_plan.md) | Matriz de 45 requisitos Classe 3 com gaps e evidências |
| [`regulatory/cnj_213/alignment.md`](regulatory/cnj_213/alignment.md) | Como o módulo de auditoria apoia cada requisito do Provimento |
| [`regulatory/cnj_213/regulatory_integration_blueprint.md`](regulatory/cnj_213/regulatory_integration_blueprint.md) | Blueprint de integração entre módulos regulatórios |

---

## 5. Operação

| Documento | Descrição |
|-----------|-----------|
| [`operations/how_to_run.md`](operations/how_to_run.md) | Instalação, banco, servidor, testes |
| [`operations/local_data_policy.md`](operations/local_data_policy.md) | Política de dados locais e dados sensíveis |

---

## 6. Qualidade e segurança

| Documento | Descrição |
|-----------|-----------|
| [`quality/testing.md`](quality/testing.md) | Fixtures, isolamento e cobertura por área |
| [`quality/risk_register_model.md`](quality/risk_register_model.md) | Modelo de campos e enums para registro de riscos |

---

## 7. Readiness / Vistoria / Dossiê

| Documento | Descrição |
|-----------|-----------|
| [`readiness/visitation_readiness_plan.md`](readiness/visitation_readiness_plan.md) | Plano semana a semana para a vistoria |
| [`readiness/visitation_readiness_checklist.md`](readiness/visitation_readiness_checklist.md) | Checklist de 73 itens para prontidão à vistoria |
| [`readiness/technical_dossier_structure.md`](readiness/technical_dossier_structure.md) | Estrutura do dossiê técnico em 12 seções |
| [`readiness/operating_flows_audit_plan.md`](readiness/operating_flows_audit_plan.md) | Plano de auditoria de fluxos operacionais da serventia |

---

## 8. Decisões técnicas e arquiteturais

| Documento | Descrição |
|-----------|-----------|
| [`decisions/index.md`](decisions/index.md) | Índice de todas as decisões (D-01 a D-23 + ADRs) |
| [`decisions/technical_decisions.md`](decisions/technical_decisions.md) | Decisões técnicas D-01 a D-23 |
| [`decisions/ADR-001-compliance-evidence-ownership.md`](decisions/ADR-001-compliance-evidence-ownership.md) | ComplianceEvidence como entidade central |
| [`decisions/ADR-002-weak-references-between-regulatory-modules.md`](decisions/ADR-002-weak-references-between-regulatory-modules.md) | Referências fracas entre módulos |
| [`decisions/ADR-003-document-registry-ownership.md`](decisions/ADR-003-document-registry-ownership.md) | Document Registry — ownership |
| [`decisions/ADR-004..008`](decisions/) | Governança de IA e Knowledge Base — estado *Proposto* |
| [`decisions/ADR-009-inventory-cent-rounding-policy.md`](decisions/ADR-009-inventory-cent-rounding-policy.md) | Política de centavos em inventários — o sistema alerta, não corrige |
| [`decisions/ADR-011-drive-readonly-capture.md`](decisions/ADR-011-drive-readonly-capture.md) | Captura somente leitura do Drive do cartório — *Proposto* |

---

## 9. Planejamento

| Documento | Descrição |
|-----------|-----------|
| [`roadmap.md`](roadmap.md) | Prioridade atual, sprints concluídas e backlog futuro |

---

## 10. Relatórios

| Documento | Descrição |
|-----------|-----------|
| [`reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md`](reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md) | **Rebaseline estratégico (2026-09-02) — diagnóstico autoritativo do estado atual** |
| [`reports/RELATORIO_CARTORIO_SYSTEM_ENGINEERING_STABILIZATION_1.md`](reports/RELATORIO_CARTORIO_SYSTEM_ENGINEERING_STABILIZATION_1.md) | Estabilização de engenharia (2026-09-03): CI, dependências, formatação, migrations |
| [`reports/RELATORIO_EXECUTIVO_CARTORIO_SYSTEM_DIRETORIA.md`](reports/RELATORIO_EXECUTIVO_CARTORIO_SYSTEM_DIRETORIA.md) | Relatório executivo para a diretoria (maio/2026 — histórico) |
| [`reports/generated/`](reports/generated/) | Artefatos gerados (CSS, templates) |
| [`audits/repository_rebaseline_2026_07/`](audits/repository_rebaseline_2026_07/) | Auditoria de repositório de julho/2026 (8 documentos + 2 CSV) |

---

## 11. Análises e Document Registry

| Diretório | Conteúdo |
|-----------|----------|
| [`analysis/`](analysis/) | Análises de domínio LGPD, matrizes de decisão |
| [`document_registry/`](document_registry/) | Blueprint CNPFE-GO, conceito do módulo, matriz esperada |
| [`proad/`](proad/) | Resposta ao PROAD da Corregedoria (Provimento CNJ 195/2025 — IERI-e e SIG-RI) |
| [`ai/`](ai/) | Investigação sobre ferramentas jurídicas de IA (sem código) |

---

## 12. Knowledge Base (preparação documental — sem código)

| Documento | Descrição |
|-----------|-----------|
| [`knowledge_base/README.md`](knowledge_base/README.md) | Visão geral da pasta e aviso de que ainda não há módulo implementado |
| [`knowledge_base/KNOWLEDGE_BASE_BLUEPRINT.md`](knowledge_base/KNOWLEDGE_BASE_BLUEPRINT.md) | Blueprint conceitual da futura base normativa (classificação, metadados, chunks, citações) |
| [`knowledge_base/PHASE_1_SOURCE_ALLOWLIST.md`](knowledge_base/PHASE_1_SOURCE_ALLOWLIST.md) | Lista explícita de fontes candidatas/autorizadas/bloqueadas para a Fase 1 |
| [`knowledge_base/GOVERNANCE_DECISIONS.md`](knowledge_base/GOVERNANCE_DECISIONS.md) | Decisões humanas pendentes (DHP-01..10), critérios de aprovação e regras de não regressão |
| [`knowledge_base/IMPLEMENTATION_ROADMAP.md`](knowledge_base/IMPLEMENTATION_ROADMAP.md) | Roadmap incremental para implementação futura |
