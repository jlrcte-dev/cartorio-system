# Backlog Estruturado — Módulo LGPD

> **Nota:** Este backlog detalha todas as epics propostas para o módulo LGPD.  
> O MVP inclui Epics LGPD-0 a LGPD-3. Epics LGPD-4+ são futuras (Sprint 4+).

Última atualização: 2026-05-05  
Versão: 1.0

---

## Epic LGPD-0 — Preparação Documental (Sprint LGPD-0)

**Objetivo:** Consolidar design arquitetural, backlog e decisões técnicas para a implementação.

**Status:** ✅ Em andamento (este relatório)

### User Stories

#### US-LGPD-0.1: Criar documentação arquitetural do módulo

**Como:** Engenheiro arquiteto  
**Quero:** Documento unificado definindo objetivo, escopo, princípios, arquitetura  
**Para:** Guiar implementação e manter coerência

**Critério de aceite:**
- [ ] `docs/modules/lgpd.md` criado com todas as seções (objetivo, limites, relações, princípios)
- [ ] Relação com Audit, CNJ 213, INOVA, Atlas explicada
- [ ] Entidades do MVP identificadas
- [ ] APIs principais documentadas
- [ ] Critério de pronto por sprint definido

**Tarefa:** Realizar

**Arquivos:** `docs/modules/lgpd.md`

#### US-LGPD-0.2: Consolidar backlog de epics e user stories

**Como:** Product owner  
**Quero:** Backlog estruturado com epics LGPD-0 a LGPD-7  
**Para:** Planejar sprints e estimar trabalho

**Critério de aceite:**
- [ ] 7 epics documentadas com objetivo e escopo
- [ ] Cada epic com 3-5 user stories
- [ ] Critérios de aceite definidos por story
- [ ] Dependências identificadas
- [ ] Riscos apontados

**Tarefa:** Realizar

**Arquivos:** `docs/analysis/lgpd_module_backlog.md` (este documento)

#### US-LGPD-0.3: Definir modelo de domínio inicial

**Como:** Arquiteto técnico  
**Quero:** Documento com entidades, campos, relacionamentos, enums  
**Para:** Guiar criação de models SQLAlchemy

**Critério de aceite:**
- [ ] 5 entidades do MVP (LgpdAction, LgpdActionOwner, LgpdEvidence, PolicyDocument, TrainingRecord)
- [ ] Campos mínimos por entidade documentados
- [ ] Enums definidos (status, tipos, prioridades)
- [ ] Relacionamentos descritos
- [ ] Entidades futuras listadas

**Tarefa:** Realizar

**Arquivos:** `docs/analysis/lgpd_domain_model.md`

#### US-LGPD-0.4: Listar perguntas críticas para INOVA LGPD

**Como:** Gestor técnico  
**Quero:** Lista estruturada de 12 perguntas por prioridade (A, B, C)  
**Para:** Refinar roadmap com resposta jurídica

**Critério de aceite:**
- [ ] 12 perguntas organizadas por prioridade (A: críticas, B: altas, C: operacionais)
- [ ] Cada pergunta com: enunciado, por quê importa, qual decisão depende, impacto no módulo
- [ ] Grupo A com mínimo 5 perguntas críticas
- [ ] Referência a cada pergunta em documentos de análise

**Tarefa:** Realizar

**Arquivos:** `docs/analysis/lgpd_inova_questions.md`

#### US-LGPD-0.5: Criar matriz de decisão do MVP

**Como:** Arquiteto  
**Quero:** Matriz avaliando 15+ funcionalidades ("entra no MVP" sim/não)  
**Para:** Definir escopo preciso de Sprint 1-3

**Critério de aceite:**
- [ ] 15+ funcionalidades avaliadas (importar CSV, CRUD ações, evidências, dashboard, etc.)
- [ ] Cada funcionalidade com: coluna sim/não, justificativa, risco, sprint recomendada
- [ ] Decisões técnicas documentadas (armazenamento, autenticação, versioning)
- [ ] Explicitamente fora do MVP marcado como "Sprint 4+"

**Tarefa:** Realizar

**Arquivos:** `docs/analysis/lgpd_mvp_decision_matrix.md`

### Critério de Pronto (Sprint LGPD-0)

- [ ] 5 documentos criados e validados
- [ ] Nenhum código implementado
- [ ] Nenhuma migration criada
- [ ] Nenhum endpoint adicionado
- [ ] Nenhum modelo SQLAlchemy criado
- [ ] Validação de git: apenas docs/ alterados
- [ ] Resumo executivo preparado para João

---

## Epic LGPD-1 — Importação e Rastreamento de Ações (Sprint 1 — junho/2026)

**Objetivo:** Trazer o Plano de Ação LGPD (25 ações) para banco de dados estruturado com interface de acompanhamento.

**Estimativa:** 2 semanas (1 dev)

**Status:** ✅ Implementada em 2026-05-05 — ver `docs/modules/lgpd.md` seção 0 para endpoints, modelo, regras de normalização e limitações conhecidas. Migration: `a7f1c2d3e4b5`. Testes: `tests/test_lgpd_actions.py` (37 testes). Suíte total: 191 passed.

**Diferenças em relação ao plano original:**
- `LgpdActionOwner` **não** foi criada como entidade separada — `responsible_party` é string em `LgpdAction` (suficiente para os dados da INOVA, pode ser promovida em sprint futura).
- Histórico foi implementado em **`LgpdActionStatusHistory`** dedicada, não via auditoria genérica.
- Filtros adicionais: `action_type`, `department` (além dos planejados `status`, `category`, `priority`, `responsible_party`).

### User Stories

#### US-LGPD-1.1: Criar entidades de ação e responsável

**Como:** Desenvolvedor  
**Quero:** Modelos SQLAlchemy `LgpdAction` e `LgpdActionOwner` com campos mínimos  
**Para:** Armazenar dados estruturados do Plano de Ação

**Critério de aceite:**
- [ ] `LgpdAction` com campos: id, action_code (AC-01..25), activity_name, category, status, owner_id, dates
- [ ] `LgpdActionOwner` com campos: id, name, department, email, phone
- [ ] Relacionamento entre LgpdAction ← LgpdActionOwner
- [ ] Enums para status (pending, in_progress, completed) e category (Governança, Preparação, Implantação)
- [ ] Testes: 5+ testes de modelo (validação, relacionamento)
- [ ] Constraints: action_code é unique; status válido

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/models.py`

**Risco:** Erro de relacionamento pode quebrar future (evidências)

#### US-LGPD-1.2: Implementar importação de CSV

**Como:** Desenvolvedor  
**Quero:** Endpoint POST `/api/v1/lgpd/actions/import` e serviço de import  
**Para:** Carregar 25 ações do Plano de Ação.csv

**Critério de aceite:**
- [ ] Função `import_from_csv(file_path)` que lê CSV
- [ ] Validação: 25 linhas esperadas, colunas corretas, sem duplicatas
- [ ] Criação de 25 registros LgpdAction
- [ ] Retorno com relatório: "25 ações importadas com sucesso"
- [ ] Testes: 5+ testes (validação, duplicatas, erro de formato)
- [ ] Suporta overwrite ou erro se já existem

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/actions/service.py`, `app/modules/lgpd/actions/router.py`

**Risco:** CSV mal formatado pode causar falha parcial

#### US-LGPD-1.3: Implementar CRUD de ações

**Como:** Usuário (gestor)  
**Quero:** Endpoints GET, PATCH para ler e atualizar status de ações  
**Para:** Acompanhar execução do Plano

**Critério de aceite:**
- [ ] GET `/api/v1/lgpd/actions` → lista com filtros (categoria, prioridade, status)
- [ ] GET `/api/v1/lgpd/actions/{id}` → detalhe completo
- [ ] PATCH `/api/v1/lgpd/actions/{id}` → atualizar status, owner, due_date
- [ ] Validação de transições: pending → in_progress → completed
- [ ] Testes: 10+ testes (CRUD, filtros, validação de transição)
- [ ] Logs de mudança: quem, quando, qual o valor anterior

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/actions/router.py`, `app/modules/lgpd/actions/service.py`

**Risco:** Transições de status mal validadas podem causar estado inválido

#### US-LGPD-1.4: Implementar resumo de execução

**Como:** Usuário (gestor)  
**Quero:** Endpoint GET `/api/v1/lgpd/actions/summary` retornando JSON com métricas  
**Para:** Ver panorama geral (11/25 concluídas, 14 pendentes, etc.)

**Critério de aceite:**
- [ ] Retorna JSON com: total_actions, completed, pending, no_date, completion_percentage
- [ ] Breakdown por categoria (Governança, Preparação, Implantação)
- [ ] Breakdown por prioridade (Alta, Média)
- [ ] Lista de ações atrasadas (overdue_actions)
- [ ] Próximos milestones
- [ ] Testes: 5+ testes (números batem, cálculos corretos)

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/actions/service.py`

#### US-LGPD-1.5: Implementar exportação CSV

**Como:** Usuário (gestor)  
**Quero:** GET `/api/v1/lgpd/actions/export?format=csv` retornando arquivo CSV  
**Para:** Usar em planilha para apresentação

**Critério de aceite:**
- [ ] CSV com colunas: code, name, category, status, owner, dates, evidence_count
- [ ] UTF-8 com BOM (Excel-friendly)
- [ ] Dados validados (sem valores null inesperados)
- [ ] Testes: 3+ testes (formato, dados, corrupção)

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/actions/service.py`

#### US-LGPD-1.6: Criar testes de integração Sprint 1

**Como:** Desenvolvedor  
**Quero:** 20+ testes cobrindo import, CRUD, filtros, resumo, export  
**Para:** Garantir qualidade

**Critério de aceite:**
- [ ] 20+ testes passando
- [ ] Coverage > 80% para `actions/`
- [ ] Ruff clean (sem warnings)
- [ ] Todos os happy paths testados
- [ ] Alguns edge cases (CSV corrompido, duplicatas)

**Tarefa:** Implementar

**Arquivos:** `tests/modules/lgpd/test_actions_*.py`

### Critério de Pronto (Sprint 1)

- [ ] 100% dos 25 itens importados e no banco
- [ ] Dashboard mostra 44% (11/25 concluídas, 14 pendentes)
- [ ] CRUD funcionando
- [ ] Filtros funcionando (categoria, prioridade, status)
- [ ] Exportação CSV funcionando
- [ ] 20+ testes passando
- [ ] Ruff clean
- [ ] Documentação: como importar, como usar endpoints
- [ ] Nenhuma alteração em módulos existentes

---

## Epic LGPD-2 — Gestão de Evidências (Sprint 2 — julho/2026)

**Objetivo:** Permitir upload, armazenamento e rastreamento de documentos, políticas e evidências de execução.

**Estimativa:** 2 semanas (1 dev)

### User Stories

#### US-LGPD-2.1: Criar entidades de evidência e política

**Como:** Desenvolvedor  
**Quero:** Modelos `LgpdEvidence` e `PolicyDocument` com campos mínimos  
**Para:** Armazenar documentos e metadados

**Critério de aceite:**
- [ ] `LgpdEvidence`: id, action_id (FK), evidence_type, file_name, file_path, file_hash, description, collected_date, collected_by
- [ ] `PolicyDocument`: id, policy_code, policy_name, current_version, file_path, published_date, approval_by
- [ ] Enum: evidence_type (policy, screenshot, ata, certificado, parecer, email)
- [ ] Relacionamento: LgpdEvidence → LgpdAction
- [ ] Testes: 5+ testes de modelo

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/evidences/models.py`

#### US-LGPD-2.2: Implementar upload de evidências

**Como:** Usuário (gestor)  
**Quero:** Endpoint POST `/api/v1/lgpd/evidences` aceitando multipart file  
**Para:** Anexar documento à ação

**Critério de aceite:**
- [ ] POST com form-data: file, action_id, evidence_type, collected_date
- [ ] Validação de tamanho (máx 50MB) e tipo (doc, pdf, png, xlsx)
- [ ] Arquivo copiado para `_VISTORIA/01_Evidencias_LGPD/{action_id}/`
- [ ] SHA-256 calculado automaticamente
- [ ] Registro de `LgpdEvidence` criado
- [ ] Resposta: { id, filename, hash, size, path }
- [ ] Testes: 5+ testes (upload, validação, tamanho, tipo)

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/evidences/router.py`, `app/modules/lgpd/evidences/storage.py`

**Risco:** Permissões de escrita em `_VISTORIA/` — coordenar com TI

#### US-LGPD-2.3: Implementar listar evidências por ação

**Como:** Usuário  
**Quero:** GET `/api/v1/lgpd/evidences?action_id=AC-04` listando evidências  
**Para:** Ver documentos anexados a uma ação

**Critério de aceite:**
- [ ] GET com query param `action_id`
- [ ] Retorna lista: [{ id, type, filename, collected_date, hash }, ...]
- [ ] Paginação (padrão 10 itens)
- [ ] Filtro por evidence_type
- [ ] Testes: 3+ testes (listagem, filtro, paginação)

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/evidences/router.py`

#### US-LGPD-2.4: Importar e versionar 14 políticas

**Como:** Administrador  
**Quero:** Carregar 14 políticas .docx da INOVA como `PolicyDocument`  
**Para:** Referenciar em ações e evidências

**Critério de aceite:**
- [ ] 14 políticas identificadas em `_local_data/LGPD-inova/Politicas-Procedimentos/`
- [ ] Cada política com code, name, version (1.0), published_date
- [ ] POST `/api/v1/lgpd/policies/import` ou CLI
- [ ] Verificar 14 registros no banco
- [ ] Testes: 3+ testes (import, duplicatas, versioning)

**Tarefa:** Implementar (parcialmente manual + CLI)

**Arquivos:** `app/modules/lgpd/evidences/router.py`, `app/modules/lgpd/cli.py`

#### US-LGPD-2.5: Implementar registro de treinamentos

**Como:** Usuário (gestor/RH)  
**Quero:** POST `/api/v1/lgpd/training` registrando treinamento realizado  
**Para:** Rastrear AC-11 (Treinamento e Conscientização)

**Critério de aceite:**
- [ ] POST com: training_name, training_date, participants (lista), certificate_hash
- [ ] Cria 1 `TrainingRecord` por participante
- [ ] Vincula automaticamente a AC-11
- [ ] GET `/api/v1/lgpd/training?action_id=AC-11` lista treinamentos
- [ ] Testes: 5+ testes (criação, listagem, múltiplos participantes)

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/training/models.py`, `app/modules/lgpd/training/router.py`

#### US-LGPD-2.6: Gerar manifesto de evidências

**Como:** Sistema  
**Quero:** GET `/api/v1/lgpd/evidences/manifest` retornando JSON com todos os hashes  
**Para:** Rastreabilidade completa para dossiê

**Critério de aceite:**
- [ ] JSON contém: generated_date, total_evidences, array com [id, action_id, filename, path, hash, type, collected_date]
- [ ] Pronto para integração com `_VISTORIA/00_Indice_Hashes.xlsx`
- [ ] Testes: 2+ testes (geração, formato)

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/evidences/service.py`

#### US-LGPD-2.7: Criar testes de integração Sprint 2

**Como:** Desenvolvedor  
**Quero:** 25+ testes cobrindo evidências, políticas, treinamentos  
**Para:** Garantir qualidade

**Critério de aceite:**
- [ ] 25+ testes passando
- [ ] Coverage > 80% para `evidences/`, `training/`
- [ ] Ruff clean
- [ ] Happy paths + edge cases (arquivo grande, tipo inválido)

**Tarefa:** Implementar

**Arquivos:** `tests/modules/lgpd/test_evidences_*.py`, `test_training_*.py`

### Critério de Pronto (Sprint 2)

- [ ] 14 políticas importadas e versionadas
- [ ] Upload de evidências funcionando
- [ ] Mínimo 2 evidências por ação concluída (22+ arquivos)
- [ ] Manifesto de evidências gerado com hashes
- [ ] Dashboard mostra evidências por ação
- [ ] Treinamentos registrados
- [ ] 25+ testes passando
- [ ] Ruff clean
- [ ] `_VISTORIA/01_Evidencias_LGPD/` estruturado

---

## Epic LGPD-3 — Relatórios de Conformidade (Sprint 3 — julho/2026)

**Objetivo:** Gerar relatórios estruturados de status, conformidade e rastreabilidade.

**Estimativa:** 1-2 semanas (1 dev)

### User Stories

#### US-LGPD-3.1: Gerar dashboard JSON (resumo de execução)

**Como:** Gestor  
**Quero:** GET `/api/v1/lgpd/reports/status` retornando JSON com métricas  
**Para:** Visualizar panorama geral (já feito em Sprint 1, agora com templates)

**Critério de aceite:**
- [ ] JSON com: total_actions, completed, pending, completion_%, breakdown por categoria/prioridade
- [ ] Overdue_actions listadas
- [ ] Next_milestones com prazos
- [ ] Pronto para frontend consumir
- [ ] Testes: 2+ testes

**Tarefa:** Refatorar/consolidar de Sprint 1

**Arquivos:** `app/modules/lgpd/reports/router.py`

#### US-LGPD-3.2: Gerar relatório Markdown de resumo

**Como:** Gestor  
**Quero:** Arquivo `lgpd_status_summary.md` com panorama legível  
**Para:** Documentar status para INOVA/vistoria

**Critério de aceite:**
- [ ] Markdown com: data, sumário executivo, tabela de ações por status, gráfico (Markdown)
- [ ] Incluir overdue_actions com dias de atraso
- [ ] Salvo em `_VISTORIA/04_Relatorios_LGPD/`
- [ ] Testes: 2+ testes (geração, conteúdo, formato)

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/reports/generator.py`, `app/modules/lgpd/reports/exports/`

#### US-LGPD-3.3: Gerar relatório detalhe de ações

**Como:** Gestor  
**Quero:** Arquivo `lgpd_action_detail.md` com detalhe de cada ação  
**Para:** Documentar status individual por ação

**Critério de aceite:**
- [ ] Markdown com seção por ação: AC-01, AC-02, ..., AC-25
- [ ] Por ação: descrição, categoria, prioridade, responsável, prazos, evidências, status
- [ ] Salvo em `_VISTORIA/04_Relatorios_LGPD/`
- [ ] Testes: 2+ testes

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/reports/exports/`

#### US-LGPD-3.4: Gerar matriz de conformidade CNJ 213

**Como:** Auditor/vistoriador  
**Quero:** CSV `lgpd_conformity_cnj213.csv` mapeando ações LGPD → blocos CNJ  
**Para:** Demonstrar cobertura de requisitos

**Critério de aceite:**
- [ ] CSV com colunas: AC-code, Action_name, CNJ_Bloco, CNJ_Requisito, LGPD_Status, Evidence_Count
- [ ] Todas as 25 ações mapeadas a blocos CNJ 213 (G, A, B, T, I, D)
- [ ] Status sincronizado com LgpdAction.status
- [ ] Salvo em `_VISTORIA/04_Relatorios_LGPD/`
- [ ] Testes: 2+ testes

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/reports/exports/`

#### US-LGPD-3.5: Gerar relatório de treinamentos

**Como:** Gestor  
**Quero:** CSV `lgpd_training_summary.csv` com lista de treinamentos e participantes  
**Para:** Demonstrar capacitação para vistoria

**Critério de aceite:**
- [ ] CSV com colunas: training_name, training_date, participant_name, certificate_hash, duration, trainer
- [ ] Consolidação de todos os `TrainingRecord`
- [ ] Salvo em `_VISTORIA/04_Relatorios_LGPD/`
- [ ] Testes: 2+ testes

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/reports/exports/`

#### US-LGPD-3.6: Integrar relatórios em endpoints

**Como:** Desenvolvedor  
**Quero:** Endpoints GET para gerar/exportar relatórios  
**Para:** Acessar via API

**Critério de aceite:**
- [ ] GET `/api/v1/lgpd/reports/status` → JSON dashboard
- [ ] GET `/api/v1/lgpd/reports/export?format=pdf|csv|json` → arquivo
- [ ] GET `/api/v1/lgpd/reports/conformity?mapping=cnj213` → matriz CSV
- [ ] Testes: 5+ testes

**Tarefa:** Implementar

**Arquivos:** `app/modules/lgpd/reports/router.py`

#### US-LGPD-3.7: Criar testes de relatórios

**Como:** Desenvolvedor  
**Quero:** 15+ testes cobrindo geração de relatórios  
**Para:** Garantir qualidade de saída

**Critério de aceite:**
- [ ] 15+ testes passando
- [ ] Coverage > 80% para `reports/`
- [ ] Ruff clean
- [ ] Validação: números batem, formato correto, sem dados sensíveis

**Tarefa:** Implementar

**Arquivos:** `tests/modules/lgpd/test_reports_*.py`

### Critério de Pronto (Sprint 3)

- [ ] 4 relatórios principais gerando sem erros
- [ ] Números validados (11/25, etc.)
- [ ] Dashboard JSON integrado a `/api/v1/`
- [ ] Relatórios salvos em `_VISTORIA/04_Relatorios_LGPD/`
- [ ] Integração com estrutura dossiê pronta
- [ ] 15+ testes passando
- [ ] Ruff clean
- [ ] MVP pronto para testes integrados

---

## Epic LGPD-4 — Incidentes e Resposta (Sprint 4 — agosto/2026+)

**Objetivo:** Implementar registro formal de incidentes para suportar AC-25 (Plano de Resposta a Incidentes).

**Estimativa:** 1-2 semanas (futuro)

### User Stories

#### US-LGPD-4.1: Criar entidade PrivacyIncident

#### US-LGPD-4.2: Implementar CRUD de incidentes

#### US-LGPD-4.3: Integrar com AuditAction para rastreabilidade

#### US-LGPD-4.4: Gerar relatório de incidentes

**Critério de Pronto (Sprint 4):** AC-25 com suporte para registro e resposta formal

---

## Epic LGPD-5 — Avaliação de Fornecedores (Sprint 5 — setembro/2026+)

**Objetivo:** Estruturar avaliação de fornecedores para AC-13.

### User Stories

#### US-LGPD-5.1: Criar entidade VendorAssessment

#### US-LGPD-5.2: Implementar CRUD de fornecedores

#### US-LGPD-5.3: Gerar relatório de conformidade de fornecedores

---

## Epic LGPD-6 — RAT/ROPa Estruturado (Sprint 6 — setembro/2026+)

**Objetivo:** Estruturar e rastrear 38 atividades de tratamento de dados.

### User Stories

#### US-LGPD-6.1: Criar entidade ProcessingActivity

#### US-LGPD-6.2: Importar 38 atividades da plataforma INOVA (quando integração funcionar)

#### US-LGPD-6.3: Gerar inventário estruturado de RAT/ROPa

---

## Epic LGPD-7 — Integração com Dossiê Técnico (Sprint 7 — setembro/2026+)

**Objetivo:** Consolidar artefatos LGPD + Audit em `_VISTORIA/` para Fase 10 do Audit.

### User Stories

#### US-LGPD-7.1: Integrar manifesto LGPD com índice Audit

#### US-LGPD-7.2: Gerar índice mestre consolidado com todos os hashes

#### US-LGPD-7.3: Validar integridade do dossiê (hashes)

---

## Dependências e Riscos

### Dependências

| Epic | Depende de |
|------|-----------|
| LGPD-0 | Nenhuma (fundação) |
| LGPD-1 | LGPD-0 (design) |
| LGPD-2 | LGPD-1 (LgpdAction existe) |
| LGPD-3 | LGPD-1, LGPD-2 |
| LGPD-4 | LGPD-3 + resposta INOVA (AC-25 template) |
| LGPD-5 | LGPD-3 + resposta INOVA (AC-13 critérios) |
| LGPD-6 | INOVA integração funcionar (erro chave) |
| LGPD-7 | Audit Fase 10 (consolidação) |

### Riscos Altos

| Risco | Mitigation |
|-------|-----------|
| INOVA integração continua bloqueada | LGPD funciona sem integração; resolver depois |
| Espaço em `_VISTORIA/` insuficiente | Coordenar com TI antes de Sprint 2 |
| CSV corrompido durante import | Validação rigorosa; rollback automático |
| Dev deixa o projeto | Documentação completa; padrões do Audit (familiar) |
| Vistoria acontece antes de MVP pronto | Usar Audit Sprint 1 como evidência principal; LGPD como suporte |

---

## Roadmap Resumido

```
Maio 2026       Junho 2026          Julho 2026           Agosto 2026
│               │                   │                    │
LGPD-0          LGPD-1              LGPD-2               LGPD-3
(design)        (ações)             (evidências)         (relatórios)
✅              ⏳ paralelo          ⏳ paralelo           ⏳ paralelo
                com Audit Sprint 2   com Audit Sprint 2   com Audit Sprint 2

MVP pronto ➜ Testes integrados ➜ Validação ➜ Produção (01/08/2026)

LGPD-4+ futuro (Sprint 4+)
```

---

## Critério de Aceitação Global (MVP)

- [ ] Epics LGPD-0 a LGPD-3 concluídas
- [ ] 60+ testes passando
- [ ] Ruff clean
- [ ] Nenhum código em módulos existentes alterado
- [ ] Nenhuma migration em módulos existentes alterada
- [ ] Documentação completa
- [ ] Pronto para validação com INOVA e vistoria

---

**Preparado por:** Claude Code  
**Data:** 2026-05-05  
**Versão:** 1.0  
**Status:** Backlog Consolidado
