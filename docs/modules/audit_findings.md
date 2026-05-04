# AuditFinding — Submódulo de Achados de Auditoria

Módulo: `app/modules/audit/findings/`
Versão: 1.0 (Sprint 2)
Status: **implementado e testado** ✅

---

## Objetivo

O submódulo `AuditFinding` permite registrar, classificar, acompanhar e encerrar
achados de auditoria da serventia de forma estruturada.

Um achado é qualquer vulnerabilidade, risco, não conformidade, inconsistência ou
observação relevante identificada por qualquer origem: scanner automatizado,
checklist manual, relatório técnico, entrevista, análise de backup, revisão de
políticas, mapeamento CNJ etc.

O AuditFinding não substitui o Scanner — ele **recebe e organiza** o que o scanner
e outros meios de coleta identificam.

---

## Diferença entre Scanner e Finding

| Scanner (Sprint 1) | Finding (Sprint 2) |
| -------------------- | -------------------- |
| Executa a varredura | Registra o achado |
| Gera inventário de arquivos | Registra vulnerabilidades e riscos |
| Não armazena no banco | Persiste no banco com ciclo de vida |
| Produz JSON/CSV/Markdown | Permite CRUD e rastreabilidade |
| Identifica candidatos a achado | O gestor decide o que é um achado real |

O campo `scanner_run_id` vincula um achado à execução de scanner que o originou.

---

## Ciclo de vida de um achado

```text
OPEN → IN_PROGRESS → WAITING_VALIDATION → RESOLVED
                                        → DISMISSED
     → ARCHIVED (a qualquer momento, com justificativa)
```

| Status | Descrição |
| -------- | ----------- |
| `OPEN` | Achado identificado; nenhuma ação iniciada |
| `IN_PROGRESS` | Ação corretiva em andamento |
| `WAITING_VALIDATION` | Ação concluída; aguardando confirmação |
| `RESOLVED` | Achado tratado com evidência documentada |
| `DISMISSED` | Achado descartado com justificativa |
| `ARCHIVED` | Arquivado após ciclo de auditoria; não é exclusão |

**Regras de transição:**

- `RESOLVED` exige `resolution_summary` + (`resolution_evidence` ou `notes`)
- `DISMISSED` exige `dismissed_reason` ou `resolution_summary`
- `ARCHIVED` exige `notes` — nunca arquivar silenciosamente
- Transicionar fora de `RESOLVED` preserva `resolution_summary` (trilha não é apagada)

---

## Endpoints

Base: `GET|POST /api/v1/audit/findings`

| Método | Endpoint | Descrição |
| -------- | --------- | ----------- |
| `POST` | `/api/v1/audit/findings` | Criar achado |
| `GET` | `/api/v1/audit/findings` | Listar com filtros |
| `GET` | `/api/v1/audit/findings/{id}` | Consultar por ID |
| `PATCH` | `/api/v1/audit/findings/{id}` | Atualizar campos gerais |
| `POST` | `/api/v1/audit/findings/{id}/status` | Mudar status com validação |
| `POST` | `/api/v1/audit/findings/{id}/archive` | Arquivar com justificativa |

`DELETE` não existe — achados nunca são excluídos fisicamente.

### Filtros no GET list

```text
?status=OPEN
?severity=HIGH
?category=BACKUP
?priority=IMMEDIATE
?origin=SCANNER
?scanner_run_id=ef8139c3-07cb-400c-8c48-e319623dbacf
?due_before=2026-06-01
?due_after=2026-05-01
?created_after=2026-05-04T00:00:00Z
?q=protesto           # busca no título e descrição
?limit=50&offset=0
```

---

## Enums

### AuditCategory

| Valor | Descrição |
| ------- | ----------- |
| `INFRASTRUCTURE` | Hardware, servidor, discos, SO |
| `BACKUP` | Backup, restauração, RPO, RTO |
| `ACCESS_CONTROL` | Usuários, grupos, permissões NTFS |
| `NETWORK` | Rede, firewall, VPN, portas |
| `ENDPOINT_SECURITY` | Antivírus, EDR, patches |
| `DOCUMENT_MANAGEMENT` | Arquivos, GED, digitalização |
| `OPERATIONAL_FLOW` | Fluxos, POPs, procedimentos |
| `POLICY_DOCUMENT` | PSI, PCN, PRD, políticas |
| `COMPLIANCE` | CNJ, LGPD, normas externas |
| `VENDOR` | Fornecedores, contratos, SLA |
| `FINANCE` | Dados financeiros históricos |
| `SYSTEM` | Cartório System, banco, logs |
| `OTHER` | Não classificado |

### AuditSeverity

| Valor | Critério |
| ------- | --------- |
| `CRITICAL` | Pode causar perda permanente de dados ou paralisação total |
| `HIGH` | Impacto severo mas recuperável |
| `MEDIUM` | Impacto moderado, operação continua degradada |
| `LOW` | Impacto pequeno |
| `INFORMATIONAL` | Observação sem impacto imediato |

### AuditPriority

| Valor | Prazo implícito |
| ------- | ---------------- |
| `IMMEDIATE` | Imediato — tratar em horas |
| `SEVEN_DAYS` | Até 7 dias |
| `THIRTY_DAYS` | Até 30 dias |
| `NINETY_DAYS` | Até 90 dias |
| `BACKLOG` | Sem prazo urgente |

> Achado `CRITICAL` exige `IMMEDIATE` ou `SEVEN_DAYS`, salvo justificativa em `notes`.

---

## Campos

### Obrigatórios na criação

| Campo | Tipo | Descrição |
| ------- | ------ | ----------- |
| `title` | str (max 200) | Título curto do achado |
| `description` | str | Descrição detalhada |
| `category` | AuditCategory | Área do achado |
| `origin` | AuditOrigin | Como foi identificado |
| `severity` | AuditSeverity | Gravidade do impacto |
| `probability` | AuditProbability | Probabilidade de ocorrência |
| `impact` | AuditImpact | Impacto operacional |
| `priority` | AuditPriority | Prioridade de tratamento |
| `evidence_summary` | str | Resumo da evidência que sustenta o achado |
| `recommended_action` | str | Ação recomendada para tratamento |

### Opcionais

| Campo | Tipo | Descrição |
| ------- | ------ | ----------- |
| `finding_code` | str (max 32) | Código fornecido pelo usuário (ex.: `AF-001`) |
| `scanner_run_id` | str (max 36) | UUID da execução de scanner que originou |
| `related_file_path` | str | Caminho relativo do arquivo relacionado |
| `cnj_requirement` | str | Requisito do Provimento 213/2026 (ex.: `B-01: RPO ≤4h`) |
| `due_date` | date | Prazo para resolução (não pode ser anterior a hoje) |
| `assigned_to` | str | Responsável designado |
| `responsible_area` | str | Área responsável |
| `notes` | str | Notas adicionais e justificativas |
| `evidence_artifact_path` | str | Caminho para artefato de evidência |
| `evidence_hash` | str (max 64) | Hash SHA-256 do artefato de evidência |

### Campos de auditoria (preenchidos automaticamente ou pelo sistema)

| Campo | Quando preenchido |
| ------- | ------------------- |
| `id` | Auto-incremento na criação |
| `status` | `OPEN` por padrão |
| `created_at` | Timestamp de criação (automático) |
| `updated_at` | Timestamp de última atualização (automático) |
| `created_by` | Padrão `"gestor"` até autenticação multiusuário |
| `updated_by` | Espelha `created_by` na criação; atualizado em PATCH |
| `resolved_at` | Auto-preenchido ao transicionar para `RESOLVED` |

---

## Exemplos de payload

### Criar achado simples (origem: scanner)

```json
POST /api/v1/audit/findings

{
  "title": "POPs de Protesto sem revisão desde 2019",
  "description": "Documentos Procedimento Protesto.odt e .pdf com data de modificação de 2019. Mais de 6 anos sem atualização confirmada.",
  "category": "POLICY_DOCUMENT",
  "origin": "SCANNER",
  "severity": "MEDIUM",
  "probability": "HIGH",
  "impact": "MEDIUM",
  "priority": "THIRTY_DAYS",
  "evidence_summary": "Scanner scan-docs-cartorio identificou os arquivos com mtime de 2019.",
  "recommended_action": "Revisar os POPs listados e criar nova versão aprovada alinhada ao Provimento CNJ 213/2026.",
  "scanner_run_id": "ef8139c3-07cb-400c-8c48-e319623dbacf",
  "related_file_path": "Politicas, manuais e procedimentos/Procedimento Protesto.odt",
  "cnj_requirement": "RO: fluxos operacionais documentados",
  "due_date": "2026-06-04",
  "assigned_to": "Gestor"
}
```

### Criar achado crítico

```json
POST /api/v1/audit/findings

{
  "title": "Banco do Engegraph sem dump consistente",
  "description": "Cobian Gravity copia arquivos mas não executa dump SQL. Em caso de falha de disco, os arquivos copiados podem não ser suficientes para restaurar o banco com integridade.",
  "category": "BACKUP",
  "origin": "TECHNICAL_REPORT",
  "severity": "CRITICAL",
  "probability": "HIGH",
  "impact": "CRITICAL",
  "priority": "IMMEDIATE",
  "evidence_summary": "Observação direta do Cobian Gravity + confirmação do fornecedor de que não oferece ferramenta própria de backup.",
  "recommended_action": "Confirmar com Engegraph procedimento oficial de backup. Implementar dump SQL agendado. Testar restauração em ambiente isolado.",
  "cnj_requirement": "B-04: Dump consistente do banco de dados",
  "assigned_to": "Responsável TI"
}
```

### Mudar status para RESOLVED

```json
POST /api/v1/audit/findings/{id}/status

{
  "status": "RESOLVED",
  "resolution_summary": "POPs de Protesto revisados e nova versão v2.0 aprovada pelo gestor em 2026-05-15.",
  "resolution_evidence": "exports/audit/scan-docs-cartorio/scan_manifest.json",
  "notes": "Aprovação em reunião de 2026-05-15. Nova versão disponível em docs/Politicas, manuais e procedimentos/."
}
```

### Arquivar achado

```text
POST /api/v1/audit/findings/{id}/archive
  ?notes=Achado arquivado após ciclo de auditoria de Maio/2026 concluído.
```

---

## Achados de exemplo (baseados na Sprint 1)

Estes achados foram identificados na execução `scan-docs-cartorio` e ilustram o uso
do módulo. Não incluem dados pessoais reais.

| ID | Categoria | Título | Severidade | Status |
| ---- | ----------- | ------- | ------------ | -------- |
| — | `POLICY_DOCUMENT` | POPs de Protesto sem revisão desde 2019 | MEDIUM | OPEN |
| — | `BACKUP` | Banco do Engegraph sem dump consistente | CRITICAL | OPEN |
| — | `DOCUMENT_MANAGEMENT` | Vídeo de 1 GB em pasta de documentos (movido) | MEDIUM | RESOLVED |
| — | `INFRASTRUCTURE` | Disco de dados com espaço crítico | CRITICAL | OPEN |
| — | `SYSTEM` | Scanner Read-Only validado em ambiente real | INFORMATIONAL | RESOLVED |

> O achado do executável (`ExtensionModule.exe`) foi tratado manualmente antes da
> Sprint 2 e pode ser registrado com status `DISMISSED` ou `RESOLVED` para fins de
> rastreabilidade histórica.

---

## Como vincular um achado a uma execução de scanner

```json
{
  "origin": "SCANNER",
  "scanner_run_id": "ef8139c3-07cb-400c-8c48-e319623dbacf",
  "evidence_artifact_path": "exports/audit/scan-docs-cartorio/file_inventory.json",
  "evidence_hash": "sha256-do-arquivo-de-inventario"
}
```

O `scanner_run_id` é o `run_id` gerado automaticamente pelo scanner e registrado
no `scan_manifest.json` da execução.

---

## Como usar evidências sem copiar dados sensíveis

- `evidence_artifact_path`: caminho **relativo** para o artefato gerado pelo scanner
  (nunca caminho absoluto do servidor)
- `evidence_hash`: hash SHA-256 do artefato, não do arquivo original da serventia
- `evidence_summary`: descrição textual da evidência — nunca conteúdo de documentos
- `related_file_path`: caminho relativo ao arquivo relacionado — sem conteúdo, sem
  dados pessoais de clientes
- `notes`: contexto adicional — nunca incluir CPF, nome de cliente ou dados sigilosos

---

## Regras de negócio

| # | Regra |
| --- | ------- |
| 1 | Status inicial é `OPEN` por padrão |
| 2 | Campos obrigatórios: title, description, category, origin, severity, probability, impact, priority, evidence_summary, recommended_action |
| 3 | `CRITICAL` exige `IMMEDIATE` ou `SEVEN_DAYS`, salvo justificativa em `notes` |
| 4 | `RESOLVED` exige: `resolution_summary` + (`resolution_evidence` ou `notes`) |
| 5 | `DISMISSED` exige: `dismissed_reason` ou `resolution_summary` |
| 6 | `ARCHIVED` exige `notes` — não é exclusão silenciosa |
| 7 | `due_date` não pode ser anterior à data de hoje (validado na criação) |
| 8 | Delete físico não existe — `DELETE /findings/{id}` retorna 404/405 |
| 9 | `updated_at` é atualizado automaticamente em todo PATCH |
| 10 | `resolved_at` é preenchido automaticamente ao transicionar para `RESOLVED` |
| 11 | Ao sair de `RESOLVED`, `resolution_summary` é preservado |
| 12 | Status é alterado exclusivamente via `POST /findings/{id}/status` ou `/archive` |

---

## Limitações da v1

| Limitação | Nota |
|-----------|------|
| Sem autenticação multiusuário | `created_by` usa `"gestor"` como padrão |
| Sem histórico de transições | Apenas o estado atual é persistido |
| Sem anexo de arquivo | `evidence_artifact_path` é apenas um caminho textual |
| Sem vinculação com `AuditEvidence` | Entidade separada planejada para Sprint futura |
| Sem notificações | Alertas de prazo vencido planejados para Sprint futura |
| Sem validação de formato do `scanner_run_id` | Qualquer string de até 36 chars é aceita |

---

## Próximos passos — Sprint 3

Sprint 3 implementa o **Diagnóstico Documental Inicial** (Fase 2 do roadmap):

- Análise semântica do inventário gerado pelo scanner
- Identificação automática de nomes genéricos, arquivos antigos, extensões suspeitas
- Geração de achados candidatos (`AuditFinding`) a partir do inventário
- Vinculação automática via `scanner_run_id`

Ver [`docs/AUDIT_MODULE_ROADMAP.md`](../AUDIT_MODULE_ROADMAP.md) para o roadmap completo.
