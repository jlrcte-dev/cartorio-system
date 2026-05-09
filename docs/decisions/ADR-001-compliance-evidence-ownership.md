# ADR-001 — ComplianceEvidence como entidade central de evidência regulatória

## Status

Proposto — aguarda aprovação antes de implementação

Data: 2026-05-06  
Autores: João + Claude Code  
Sprint de origem: Blueprint Regulatório

---

## Contexto

O sistema possui quatro módulos regulatórios: `audit` (diagnóstico técnico),
`retention` (temporalidade documental), `lgpd` (plano de proteção de dados) e
`compliance` (mapeamento normativo CNJ 213/2026).

Após a Sprint LGPD/Compliance-1, o módulo `compliance` possui a Matriz INOVA V1
(requisitos, políticas, prazos, evidências sugeridas) mas **não possui evidências
reais**. Para avançar para status de conformidade, dossiê técnico e relatórios
executivos, é necessário definir onde residem as evidências regulatórias reais.

Existem três candidatos naturais para ser a entidade central de evidências:

1. **`ComplianceEvidence` no módulo `compliance`** — compliance como agregador
2. **Evidências distribuídas por módulo** — cada módulo cuida das suas
3. **Entidade genérica de evidências** — módulo utilitário compartilhado

A decisão impacta diretamente: acoplamento entre módulos, responsabilidade de
migrations, linguagem regulatória (associação com requisito normativo), e a
capacidade de referenciar fontes heterogêneas (audit, lgpd, retention, externas).

---

## Decisão

**`ComplianceEvidence` é a entidade central de evidência regulatória real,
pertencente exclusivamente ao módulo `compliance`.**

Campos mínimos propostos: `requirement_id`, `template_id (opcional)`, `title`,
`description`, `evidence_type`, `source_module`, `source_type`, `source_ref`,
`file_reference (opcional)`, `responsible`, `collected_at`, `status`.

A referência a outras fontes (audit, lgpd, retention) ocorre por **referência fraca**
(`source_module` + `source_type` + `source_ref`), não por FK direta. Ver ADR-002.

---

## Consequências positivas

**1. Requisito normativo como âncora natural**  
Toda evidência regulatória responde a um `ComplianceRequirement`. Compliance é o
único módulo que modela requisitos normativos — a ancoragem é semanticamente correta.

**2. Aggregação de fontes heterogêneas**  
Uma evidência pode vir de audit (DIAG-004), de lgpd (AC-15 concluída), de retention
(TEMP-003 resolvida) ou de fontes externas (documento PDF, ata, screenshot). Compliance
é o único lugar natural para consolidar essas fontes com linguagem regulatória.

**3. Separação de domínios preservada**  
Audit não sabe que seus findings viram evidências regulatórias.  
LGPD não sabe que suas ações são usadas para evidenciar requisitos do Provimento 213.  
Retention não sabe que seus sinais TEMP são rastreados como riscos regulatórios.

**4. Evolução independente**  
Compliance pode adicionar campos a `ComplianceEvidence` sem impactar `AuditFinding`,
`LgpdAction` ou `RetentionRule`. Migrations são isoladas por módulo.

**5. Linguagem regulatória concentrada**  
Status indicativo, nota conservadora, referência a etapa e prazo por classe ficam
em compliance — sem poluir os domínios de audit, lgpd e retention.

---

## Consequências negativas

**1. Validação de `source_ref` em tempo de execução**  
Sem FK direta, a consistência entre `source_ref = "DIAG-004"` e a existência real
do finding é verificada pelo service de compliance, não pelo banco. Se um finding for
renomeado (improvável, dado que achados são imutáveis), a referência fica inconsistente.

**Mitigação:** findings e ações são imutáveis por design; apenas status evolui.
A probabilidade de `source_ref` ficar inválida é muito baixa.

**2. Carga extra no service de compliance**  
O service de `ComplianceEvidence` precisa fazer consultas em outros módulos para
validar `source_ref` antes de aceitar criação de evidência. Isso requer que o
service de compliance acesse repositórios de audit/lgpd por injeção (sem import
de model direto).

**Mitigação:** injeção de interfaces/serviços por parâmetro no constructor do service,
seguindo o mesmo padrão de `retention_rules` no `DocumentAnalyzer`.

**3. Duplicidade potencial de informação**  
O `title` e a `description` de uma `ComplianceEvidence` baseada em `DIAG-004` podem
replicar informação já presente no `AuditFinding`. É necessário disciplina para
referenciar sem copiar.

**Mitigação:** documentação explícita de que `ComplianceEvidence` não deve replicar
dados de outras tabelas; `description` deve explicar a relevância regulatória,
não recriar o finding.

---

## Alternativas consideradas

### Alternativa A: Evidências distribuídas por módulo

Cada módulo teria sua própria entidade de evidência (`AuditEvidence`, `LgpdEvidence`,
`RetentionEvidence`). Compliance consolidaria lendo de todos.

**Por que descartada:**
- Compliance precisaria de FK direta em todos os módulos (alto acoplamento)
- Linguagem regulatória (requisito, prazo, etapa) ficaria duplicada ou ausente
- Evidências externas (documentos PDF, atas) não têm módulo natural de origem
- Dossiê técnico precisaria juntar N tabelas de N módulos com joins cruzados

### Alternativa B: Módulo utilitário compartilhado `evidence`

Um módulo `evidence` separado centraliza todas as evidências (técnicas e regulatórias).

**Por que descartada:**
- Cria dependência cruzada: audit/lgpd/retention precisariam importar `evidence`
- Mistura semântica: evidência técnica de scanner é diferente de evidência regulatória
- Aumenta a superfície de mudança: qualquer sprint em qualquer módulo impacta `evidence`
- Não há precedente no projeto; introduz complexidade antes de validar o modelo

### Alternativa C: FK direta de `AuditFinding` → `ComplianceRequirement`

Adicionar um campo opcional `compliance_requirement_id` no `AuditFinding`.

**Por que descartada:**
- Viola a separação de domínios: audit passaria a importar compliance
- Audit não deve ter conhecimento de requisitos normativos
- Cria dependência bidirecional (compliance já referenciaria audit)
- A relação é M:N (um finding pode evidenciar múltiplos requisitos)

---

## Impacto nas próximas sprints

| Sprint | Impacto |
|--------|---------|
| LGPD/Compliance-2 | Implementa `ComplianceEvidence` com base nesta decisão |
| Sprint RequirementFindingLink | Usa o mesmo princípio de ownership em compliance |
| Sprint ComplianceStatus | Calcula status baseado em `ComplianceEvidence` do compliance |
| Sprint DossieTecnico | Consolida `ComplianceEvidence` + referências fracas |
| LGPD-2+ | `LgpdEvidence` permanece no módulo lgpd (evidências operacionais LGPD); `ComplianceEvidence` no compliance (evidências de requisitos normativos) |

---

## Referências

- [Blueprint de Integração Regulatória](../regulatory/cnj_213/regulatory_integration_blueprint.md) — Seções 5, 7, 12.3
- [ADR-002 — Referências fracas entre módulos](ADR-002-weak-references-between-regulatory-modules.md)
- [docs/modules/compliance.md](../modules/compliance.md) — Estado atual do módulo
