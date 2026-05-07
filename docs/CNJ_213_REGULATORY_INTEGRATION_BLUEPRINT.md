# Blueprint de Integração Regulatória — CNJ 213

> **Aviso:** Este documento é um plano arquitetural e não constitui declaração de
> conformidade jurídica. Decisões técnicas aqui propostas são sujeitas a validação
> humana antes de implementação. Status indicativo nunca equivale a declaração de
> conformidade.

Última atualização: 2026-05-06  
Versão: 1.2 — Sprint LGPD/Compliance-3 concluída  
Estado: Em implementação — RequirementFindingLink MVP entregue

---

## 1. Objetivo

Este documento define as **fronteiras, responsabilidades, contratos futuros e
roadmap de implementação** para a integração entre os módulos regulatórios do
Cartório System:

```
audit       → diagnóstico documental e técnico
retention   → temporalidade documental (Provimento CNJ nº 50/2015)
lgpd        → operacionalização do plano de proteção de dados
compliance  → consolidação regulatória (Provimento CNJ nº 213/2026)
```

O objetivo principal é **reduzir risco de retrabalho** antes de implementar
evidências reais, vínculos com achados, status indicativo e dossiê técnico.
Esta sprint é exclusivamente documental e arquitetural: nenhuma tabela, endpoint,
migration ou código de produção é alterado.

---

## 2. Estado atual dos módulos

### 2.1 Módulo `audit`

**Sprints concluídas:** Scanner (1), AuditFinding CRUD (2), DocumentDiagnosis (3),
Hardening (3.5).

**O que existe:**
- Scanner read-only de arquivos (`file_scanner.py`) — gera `file_inventory.json`
- `AuditFinding` — CRUD de achados técnicos (DIAG-001..007)
- `DocumentDiagnosis` — analisa o inventário JSON, não acessa arquivos originais
- Regras `TEMP-001/002/003` em `temp_rules.py` — emitidas quando `retention_rules` é injetado
- Princípio read-only estrito: nenhum arquivo do servidor é modificado

**O que não existe ainda:**
- Questionnaires, actions (como entidade formal), relatórios, dossiê técnico
- Integração formal com `compliance` ou `lgpd`
- Exportação consolidada para vistoria

**Regra absoluta:** achados nunca são deletados; apenas status evolui.

---

### 2.2 Módulo `retention`

**Sprints concluídas:** retention-1A (domínio, seed, regras TEMP), retention-1B
(integração com DocumentDiagnosis por injeção opcional).

**O que existe:**
- `RetentionRule` — representa regras do Provimento CNJ nº 50/2015
- Seed idempotente de 24 regras com legibilidade confirmada
- Regras `TEMP-001/002/003` como funções puras em `temp_rules.py`
- Avaliação read-only em memória — sem persistência de resultado
- CLI `--with-retention-rules` que injeta regras no pipeline

**O que não existe ainda:**
- `RetentionEvaluation` (persistida) — sprint retention-1C
- Router/API pública
- Workflow de descarte
- Relatório semestral ao juízo competente

**Princípio absoluto:** nenhuma rotina autoriza, recomenda ou executa descarte
automático. Toda decisão é humana.

---

### 2.3 Módulo `lgpd`

**Sprint concluída:** LGPD-1 (ações AC-01..25, histórico, summary, export CSV).

**O que existe:**
- `LgpdAction` — 25 ações do Plano INOVA, importáveis via CSV
- `LgpdActionStatusHistory` — histórico de mudanças de status
- Endpoints: import, CRUD, summary, export CSV
- Normalização de status INOVA → enum interno

**O que não existe ainda:**
- Evidências com upload e hash SHA-256 (LGPD-2)
- `PolicyDocument`, `TrainingRecord`, `DpoRecord` (LGPD-2)
- `ProcessingActivity` (RAT/ROPa) (LGPD-3)
- `PrivacyIncident`, `VendorAssessment` (LGPD-4+)
- Integração com compliance ou audit

**Limitação:** o módulo não modela todos os artigos do Provimento 213; foca
na dimensão de proteção de dados pessoais conforme Plano INOVA.

---

### 2.4 Módulo `compliance`

**Sprints concluídas:**
- LGPD/Compliance-1 — Matriz INOVA V1, read-only (2026-05-06)
- LGPD/Compliance-2 — `ComplianceEvidence` MVP (2026-05-06)
- LGPD/Compliance-3 — `RequirementFindingLink` MVP (2026-05-06)

**O que existe:**
- `ComplianceRequirement` — 32 requisitos normativos mapeados
- `CompliancePolicyDocument` — 30 políticas/documentos indicados
- `ComplianceRequirementPolicy` — ~75 vínculos N:N requisito ↔ política
- `ComplianceRequirementDeadline` — 96 prazos por classe (C1/C2/C3)
- `ComplianceEvidenceTemplate` — ~131 evidências sugeridas pela matriz
- `ComplianceSeedMeta` — metadados de versão e checksum SHA-256
- `ComplianceEvidence` — evidências regulatórias reais (MVP, sem upload)
- `RequirementFindingLink` — vínculos requisito ↔ achado/sinal por referência
  fraca. Enums `ComplianceLinkSourceModule`, `ComplianceLinkSourceType`,
  `ComplianceLinkRiskLevel`. UniqueConstraint por origem. POST/GET/PATCH.
  Sem FK cruzada com `audit`, `retention` ou `lgpd` (ADR-002).
- Seed determinístico e idempotente da Matriz INOVA V1
- Endpoints: GET (requisitos, políticas, etapas, summary) +
  POST/GET/PATCH (evidências) + POST/GET/PATCH (requirement-links)

**O que não existe ainda:**

- `ComplianceAction` — ação corretiva regulatória
- Status de conformidade calculado por requisito (`ComplianceStatus`)
- Dossiê técnico consolidado
- Upload de arquivos de evidência (hash SHA-256, armazenamento binário)
- Integração real bidirecional com audit, lgpd ou retention (apenas referência fraca)

**Fronteira estrita:** nenhum import de `audit`, `lgpd` ou `retention` no código
(ADR-001, ADR-002).

---

## 3. Fronteiras entre audit, retention, lgpd e compliance

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Provimento CNJ 213/2026                         │
└──────────────────────────────────────────────────────────────────────────┘
              │                 │                │              │
              ▼                 ▼                ▼              ▼
       ┌─────────┐      ┌─────────────┐   ┌──────────┐  ┌───────────┐
       │  audit  │      │  retention  │   │   lgpd   │  │compliance │
       │         │      │             │   │          │  │           │
       │diagnóst.│      │temporalidad.│   │dados     │  │consolida  │
       │documental      │documental   │   │pessoais  │  │requisitos │
       │técnico  │      │CNJ 50/2015  │   │INOVA     │  │evidências │
       │findings │      │regras TEMP  │   │AC-01..25 │  │vínculos   │
       │DIAG-*   │      │TEMP-001..003│   │          │  │status     │
       └─────────┘      └─────────────┘   └──────────┘  └───────────┘
```

### Responsabilidade de cada módulo

| Módulo | Domínio | Produz | Não deve |
|--------|---------|--------|----------|
| `audit` | Diagnóstico técnico e documental | Findings DIAG-*, artefatos de varredura | Assumir governança regulatória |
| `retention` | Temporalidade documental | Sinais TEMP-*, avaliação read-only | Executar ou recomendar descarte automático |
| `lgpd` | Obrigações de proteção de dados pessoais | Status de ações AC-*, histórico | Modelar todos os artigos do Provimento 213 |
| `compliance` | Consolidação regulatória e normativos | Mapa de requisitos, evidências, status indicativo, dossiê | Executar operações dos outros módulos |

### Regra de não-dependência

```
audit       → não importa lgpd, retention (recebe retention_rules por injeção)
retention   → não importa audit, lgpd, compliance
lgpd        → não importa audit, retention, compliance
compliance  → não importa audit, lgpd, retention (consome por referência fraca)
```

A única exceção atual e intencional: `audit/diagnosis/temp_rules.py` recebe
`list[RetentionRule]` por parâmetro, sem import do pacote `retention`.

---

## 4. Princípios de integração

**P-01 — Separação de responsabilidades por módulo**  
Cada módulo mantém domínio exclusivo. Compliance não executa diagnóstico;
audit não declara conformidade; retention não consome endpoints do compliance.

**P-02 — Compliance como agregador, não executor**  
O módulo compliance consolida informação produzida por outros módulos por
referência fraca. Nunca escreve em tabelas de audit, lgpd ou retention.

**P-03 — Linguagem conservadora obrigatória**  
Nenhum status, relatório ou endpoint deve usar termos como "CONFORME",
"CUMPRIDO" ou "APROVADO" de forma automática. Status indicativo exige
validação humana explícita.

**P-04 — Referência fraca antes de FK formal**  
A integração inicial usa campos textuais (`source_module`, `source_type`,
`source_ref`) em vez de foreign keys entre módulos. FK formal pode ser
introduzida em sprint futura quando o modelo estabilizar.

**P-05 — Sem dependência circular**  
compliance lê (por referência fraca) achados de audit, sinais de retention
e ações de lgpd. Nenhum desses módulos lê ou depende de compliance.

**P-06 — Read-only na integração inicial**  
A primeira versão de ComplianceEvidence que referencie outros módulos deve
ser somente de leitura da perspectiva dos módulos referenciados. Compliance
não escreve em tabelas alheias.

**P-07 — Avaliação humana sempre necessária**  
Status indicativo calculado pelo sistema nunca substitui revisão jurídica,
administrativa ou do gestor. Todo relatório deve incluir nota conservadora.

---

## 5. Propriedade das evidências regulatórias

**Decisão proposta:** `ComplianceEvidence` é a entidade central de evidência
regulatória real, pertencente ao módulo `compliance`.

### Justificativa

1. **Requisito como âncora:** uma evidência regulatória sempre responde a um
   requisito normativo (`ComplianceRequirement`). Compliance é o único módulo
   que modela requisitos.
2. **Diversidade de fontes:** uma evidência pode vir de audit (finding DIAG-004),
   de lgpd (ação AC-15 concluída), de retention (regra TEMP-003 resolvida),
   ou de fonte externa (documento PDF, screenshot, ata). Compliance é o agregador
   natural.
3. **Linguagem regulatória:** o processo de evidenciar conformidade requer
   contexto regulatório que só compliance possui (requisito, prazo, etapa,
   política vinculada).
4. **Separação de domínios:** audit não deve saber que seus findings viram
   evidências regulatórias; lgpd não deve saber que suas ações são usadas como
   evidências de requisitos específicos do Provimento 213.

### Consequências

- Audit, lgpd e retention **nunca** recebem um campo `compliance_evidence_id`
  ou qualquer referência de volta ao compliance.
- Compliance cria `ComplianceEvidence` apontando para `source_ref = "DIAG-004"`,
  mas a tabela `audit_findings` não sabe disso.
- A integridade referencial entre módulos é de responsabilidade da camada de
  serviço de compliance, não do banco de dados.

---

## 6. Estratégia de referência fraca entre módulos

**Decisão proposta:** a integração inicial entre `compliance` e os demais módulos
ocorre por **referência fraca textual**, não por foreign key direta.

### Modelo proposto de referência fraca

```
source_module : str   →  "audit" | "retention" | "lgpd" | "external" | "manual"
source_type   : str   →  "finding" | "temp_signal" | "lgpd_action" | "document" | "other"
source_ref    : str   →  "DIAG-004" | "TEMP-002" | "AC-15" | "98-PSI.docx" | ...
```

### Comparação: referência fraca vs. FK direta

| Aspecto | Referência fraca | FK direta |
|---------|------------------|-----------|
| Acoplamento | Baixo — compliance não depende de schema de audit | Alto — migration de audit impacta compliance |
| Migrations | Independentes por módulo | Precisam ser coordenadas |
| Fontes externas | Pode referenciar documentos, PDFs, e-mails | Impossível sem tabela intermediária |
| Integridade referencial | Verificação em tempo de execução (service) | Verificada pelo banco |
| Evolução | Compliance evolui sem aguardar audit | Mudança em audit pode bloquear compliance |
| Risco de FK órfã | Não se aplica (não há FK) | Achado deletado (impossível por regra) quebraria FK |

### Quando promover para FK formal

A FK direta pode ser introduzida futuramente se:
- O modelo de `AuditFinding` estabilizar (sem renomeações previstas)
- A equipe confirmar que a inviolabilidade do `finding_id` é garantida
- O benefício de integridade automática superar o custo de acoplamento

Até então, a verificação de existência do `source_ref` é responsabilidade do
service de `compliance` em tempo de execução.

---

## 7. Modelo futuro de `ComplianceEvidence`

> **Não implementar.** Especificação para sprint futura (LGPD/Compliance-2 ou posterior).

### Proposta de campos

```
ComplianceEvidence
├── id                  UUID        PK
├── requirement_id      UUID        FK → compliance_requirements.id (NOT NULL)
├── template_id         UUID        FK → compliance_evidence_templates.id (nullable)
│                                   referência à evidência sugerida pela Matriz
├── title               str(200)    NOT NULL — descrição curta
├── description         text        NOT NULL — detalhamento
├── evidence_type       enum        NOT NULL — ver EvidenceType abaixo
├── source_module       str(50)     NOT NULL — "audit" | "retention" | "lgpd" |
│                                              "external" | "manual"
├── source_type         str(100)    nullable — "finding" | "temp_signal" |
│                                              "lgpd_action" | "document" | "other"
├── source_ref          str(200)    nullable — código de referência (ex: "DIAG-004")
├── file_reference      str(500)    nullable — caminho relativo em _VISTORIA/
├── responsible         str(200)    nullable — quem coletou/validou
├── collected_at        datetime    NOT NULL — data de coleta
├── status              enum        NOT NULL — ver EvidenceStatus abaixo
├── notes               text        nullable — observações do revisor
├── created_at          datetime    automático
└── updated_at          datetime    automático
```

### Enum `EvidenceType`

```
OBSERVATION      → observação direta (texto)
SCREENSHOT       → captura de tela
DOCUMENT         → documento formal (PDF, DOCX)
POLICY           → política ou procedimento versionado
REPORT           → relatório gerado pelo sistema
AUDIT_FINDING    → achado técnico do módulo audit
TEMP_SIGNAL      → sinal de temporalidade do módulo retention
LGPD_ACTION      → ação concluída do plano LGPD
SCAN_RESULT      → resultado de varredura de arquivos
EXTERNAL         → documento externo (contrato, ATA, e-mail)
OTHER            → outros
```

### Enum `EvidenceStatus`

```
DRAFT            → rascunho; não considerada para cálculo de status
PENDING_REVIEW   → coletada; aguarda revisão humana
ACCEPTED         → revisada e aceita como válida
REJECTED         → revisada e rejeitada (motivo em notes)
EXPIRED          → válida por prazo, prazo vencido
```

### O que `ComplianceEvidence` não deve fazer

- Não deve replicar dados de outras tabelas (não copiar `title` do `AuditFinding`)
- Não deve ser o único critério automático de status de requisito
- Não deve ser criada por processos automáticos sem revisão humana posterior
- Não deve armazenar dados pessoais de titulares (apenas metadados)

---

## 8. `RequirementFindingLink` — implementado (Sprint Compliance-3)

> **Implementado.** Commit `c588bc2` — Sprint LGPD/Compliance-3 (2026-05-06).

`RequirementFindingLink` representa o vínculo entre um requisito normativo e
um achado, sinal, ação ou documento de origem externa. É distinto de
`ComplianceEvidence`: o link rastreia a **relação com a fonte**, não a
evidência formal de cumprimento.

### Campos implementados

```
RequirementFindingLink
├── id               Integer     PK autoincrement
├── requirement_id   Integer     FK → compliance_requirements.id (NOT NULL, CASCADE)
├── source_module    enum        NOT NULL — AUDIT|RETENTION|LGPD|MANUAL|EXTERNAL
├── source_type      enum        NOT NULL — FINDING|DIAGNOSIS|SIGNAL|ACTION|
│                                           POLICY|DOCUMENT|MANUAL_NOTE
├── source_ref       str(200)    NOT NULL — ex: "DIAG-004", "TEMP-002", "AC-01"
├── title            str(300)    nullable — rótulo opcional do vínculo
├── link_reason      text        nullable — justificativa do vínculo
├── risk_level       enum        nullable — INFO|LOW|MEDIUM|HIGH|CRITICAL
├── notes            text        nullable — observações adicionais
├── created_at       datetime    automático
└── updated_at       datetime    automático
```

UniqueConstraint `uq_compliance_requirement_finding_link_source` em
`(requirement_id, source_module, source_type, source_ref)` impede vínculos
duplicados da mesma origem para o mesmo requisito.

### Diferenças em relação à proposta original

| Aspecto | Proposta original | Implementado |
| ------- | ----------------- | ------------ |
| `link_type` (GAP/RISK/etc.) | Previsto | **Não implementado** — substituído por `risk_level` (INFO/LOW/MEDIUM/HIGH/CRITICAL), mais flexível para sprint conservadora |
| `created_by` | Previsto | **Não implementado** — aguarda autenticação multiusuário |
| Validação de `source_ref` | Prevista | **Não implementada** — referência fraca intencional; validação seria acoplamento |
| Status indicativo | Previsto após criação de link | **Não implementado** — sprint Compliance-4 |

### Fronteiras mantidas (ADR-002)

- `audit`, `retention` e `lgpd` **não sabem** da existência de
  `RequirementFindingLink`.
- Nenhuma FK cruzada entre módulos.
- `source_ref` é string livre — não validada contra tabelas externas.
- A integridade referencial entre módulos é responsabilidade do operador
  humano, não do banco de dados.

### Linguagem conservadora

- A existência de um vínculo não implica que o requisito está atendido ou
  descumprido.
- Campo `link_note` conservador incluído em toda resposta de leitura:
  > "Vínculo registrado para apoio à rastreabilidade regulatória; não
  > representa declaração automática de conformidade. Exige validação
  > humana, jurídica ou administrativa."

---

## 9. Modelo futuro de `ComplianceAction`

> **Não implementar.** Especificação para sprint futura. Recomenda-se avaliar
> na sprint de planejamento antes de implementar.

### Quando deve existir

`ComplianceAction` representa ação corretiva regulatória vinculada a um
requisito do Provimento CNJ 213/2026. É distinta de `LgpdAction` (que cobre
o Plano INOVA de 25 ações AC-01..25).

### Diferença para `LgpdAction`

| Aspecto | `LgpdAction` | `ComplianceAction` |
|---------|-------------|---------------------|
| Origem | Plano de Ação INOVA (25 ações) | Lacunas identificadas em requisitos do Provimento 213 |
| Escopo | Proteção de dados pessoais | Todos os requisitos regulatórios (inf., segurança, governança, etc.) |
| Código | AC-01..25 | A definir (ex: CA-001) |
| Import | CSV INOVA | Manual ou gerado a partir de RequirementFindingLink |
| Status | PENDING / IN_PROGRESS / COMPLETED | A definir com enums próprios |

### Risco de duplicidade

Existe risco real de uma ação LGPD (AC-04) e uma ação corretiva regulatória
(CA-001) apontarem para o mesmo esforço. A recomendação é:

1. Na sprint de planejamento, verificar se `ComplianceAction` deve **nascer
   própria** ou apenas **referenciar** `LgpdAction` por referência fraca.
2. Preferir referência antes de criar modelo duplicado.
3. Não criar `ComplianceAction` antes de ter pelo menos 3 casos reais de
   uso que não possam ser cobertos por `LgpdAction` + `RequirementFindingLink`.

### Recomendação para sprint futura

Implementar `ComplianceAction` somente após:
- `ComplianceEvidence` estar em produção e validada
- `RequirementFindingLink` estar em produção
- Haver ao menos um caso real que exige ação corretiva regulatória não
  coberta pelo plano LGPD

---

## 10. Modelo futuro de `ComplianceStatus`

> **Não implementar.** Especificação para sprint futura.

### Enums propostos

```
NOT_STARTED      → requisito identificado; nenhuma ação ou evidência associada
MAPPED_ONLY      → mapeado na Matriz INOVA; sem evidências ou ações iniciadas
EVIDENCE_PENDING → tem ações ou links; sem evidências aceitas
PARTIAL_EVIDENCE → tem pelo menos uma evidência ACCEPTED; mas há lacunas
UNDER_REVIEW     → evidências coletadas; aguardando revisão humana
EVIDENCED        → evidências suficientes aceitas; aguarda validação jurídica
NEEDS_REVIEW     → evidências aceitas anteriormente; algo mudou (prazo, regra)
EXPIRED          → prazo de adequação vencido sem evidências suficientes
```

### Regras obrigatórias de linguagem

- **Proibido:** `COMPLIANT`, `CONFORME`, `APROVADO` como status automático
- **Permitido:** `EVIDENCED` + nota conservadora de que exige validação jurídica
- Todo endpoint que expõe status deve incluir `status_note` com texto:
  > "Status calculado pelo sistema com base nas evidências registradas.
  > Não constitui declaração de conformidade jurídica ou administrativa."

### Cálculo indicativo (regra sugerida)

```
NOT_STARTED     → sem RequirementFindingLink e sem ComplianceEvidence
MAPPED_ONLY     → sem link, sem evidência (apenas mapeado na Matriz)
EVIDENCE_PENDING → tem link GAP mas sem evidência ACCEPTED
PARTIAL_EVIDENCE → ≥1 evidência ACCEPTED mas template_count não satisfeito
UNDER_REVIEW    → evidências em PENDING_REVIEW
EVIDENCED       → ≥N evidências ACCEPTED (N = count de templates sugeridos)
NEEDS_REVIEW    → evidência ACCEPTED existe mas collected_at < prazo revisão
EXPIRED         → prazo C3 vencido e status não é EVIDENCED
```

O cálculo acima é sugestão inicial; a lógica real deve ser validada com
a consultoria INOVA antes de implementação.

---

## 11. Modelo futuro de `DossieTecnico`

> **Não implementar.** Especificação para sprint futura (Fase 10 do módulo audit).

O dossiê técnico é o artefato consolidado por etapa do Provimento CNJ 213/2026,
gerado para fins de vistoria pelo Sistema Justiça Aberta.

### Modelo conceitual

```
DossieTecnico (por etapa do Provimento)
├── etapa                       str         Ex: "ETAPA_1", "ETAPA_2"
├── titulo                      str         Ex: "Governança e Gestão de TI"
├── data_geracao                datetime
├── gerado_por                  str
├── serventia_class             str         "C3"
│
├── requisitos[]                           → lista de ComplianceRequirement da etapa
│   ├── code, title, status_indicativo
│   └── policies[], evidence_templates[]
│
├── evidencias_reais[]                     → lista de ComplianceEvidence (ACCEPTED)
│   ├── title, evidence_type, collected_at
│   └── source_module, source_ref
│
├── findings_relacionados[]                → via RequirementFindingLink
│   ├── source_module, source_type, source_ref
│   └── link_type, notes
│
├── acoes_lgpd_relacionadas[]              → referência fraca a LgpdAction
│   ├── action_code, title, status
│   └── completed_date
│
├── pendencias[]                           → requisitos sem evidência suficiente
├── riscos[]                               → findings do tipo GAP ou RISK
│
├── declaracao_observacoes      text       → espaço para declaração do gestor
└── nota_conservadora           text       → nota fixa sobre status indicativo
```

### Formatos previstos

- **JSON estruturado** — para processamento e API
- **Markdown** — para leitura humana e versionamento em Git
- **PDF** — geração futura (não nesta sprint); requer biblioteca externa

### Princípio: dossiê lê, não escreve

O dossiê técnico consolida dados existentes de compliance, audit, lgpd e
retention via leitura (ou referência fraca). Nunca cria, modifica ou deleta
dados dos módulos que agrega.

---

## 12. Fluxos conceituais

### 12.1 Finding do audit → lacuna regulatória

```
1. Operador executa DocumentDiagnosis via CLI
2. DocumentAnalyzer gera DiagnosisResult com finding DIAG-004
3. Gestor revisita o finding e decide que é lacuna regulatória real
4. Gestor (via interface futura de compliance) cria RequirementFindingLink:
     requirement_id = REQ-013 (ex: controle de acesso documental)
     source_module  = "audit"
     source_type    = "finding"
     source_ref     = "DIAG-004"
     link_type      = GAP
5. Status do REQ-013 passa de MAPPED_ONLY → EVIDENCE_PENDING
6. Gestor inicia ação corretiva (manual ou via ComplianceAction futura)
7. Após correção, gestor cria ComplianceEvidence:
     evidence_type  = AUDIT_FINDING
     source_module  = "audit"
     source_ref     = "DIAG-004"
     status         = PENDING_REVIEW
8. Revisor marca a evidência como ACCEPTED
9. Status do REQ-013 pode evoluir para PARTIAL_EVIDENCE ou EVIDENCED
```

**Nota:** audit não sabe dos passos 4..9. A tabela `audit_findings` não é alterada.

---

### 12.2 TEMP-* do retention → alerta de temporalidade

```
1. CLI roda DocumentDiagnosis com --with-retention-rules
2. Regra TEMP-002 emite finding para arquivo aparentemente vencido
3. Gestor revisa o finding com responsável jurídico/documental
4. Decisão: arquivo deve ser encaminhado para guarda intermediária
5. Gestor (via compliance, futuro) cria RequirementFindingLink:
     source_module = "retention"
     source_type   = "temp_signal"
     source_ref    = "TEMP-002"
     link_type     = RISK
6. Ação corretiva documentada manualmente (fora do sistema por ora)
7. Após resolução: ComplianceEvidence criada como OBSERVATION
8. Tabela retention_rules não é alterada; findings TEMP não são deletados
```

---

### 12.3 Ação LGPD → evidência regulatória

```
1. Gestor registra AC-15 como COMPLETED (módulo lgpd)
2. Módulo lgpd registra completed_date em lgpd_actions
3. Gestor identifica que AC-15 (nomeação do DPO) atende ao REQ-005
   (ex: designação de responsável pela proteção de dados)
4. Gestor cria ComplianceEvidence em compliance:
     requirement_id = id do REQ-005
     evidence_type  = LGPD_ACTION
     source_module  = "lgpd"
     source_type    = "lgpd_action"
     source_ref     = "AC-15"
     status         = PENDING_REVIEW
5. Revisor analisa e marca como ACCEPTED
6. Status do REQ-005 evolui para EVIDENCED ou PARTIAL_EVIDENCE
```

**Nota:** lgpd_actions não recebe campo compliance_evidence_id. O vínculo
existe apenas na direção compliance → lgpd, por referência fraca.

---

### 12.4 EvidenceTemplate → Evidence real

```
1. GET /compliance/requirements/REQ-005 retorna evidence_templates[]
     template: "Ata de designação do DPO assinada pelo responsável"
2. Gestor coleta o documento real
3. Gestor cria ComplianceEvidence:
     requirement_id = REQ-005
     template_id    = id do template
     evidence_type  = DOCUMENT
     source_module  = "external"
     file_reference = "_VISTORIA/01_Governanca/Atas/ata_dpo.pdf"
     status         = PENDING_REVIEW
4. Revisão → ACCEPTED
```

O `template_id` é opcional: evidências sem template correspondente também
são válidas (ex: evidência não prevista pela Matriz INOVA).

---

### 12.5 Evidence real → status indicativo

```
1. ComplianceService calcula status do requisito:
   - Busca ComplianceEvidence WHERE requirement_id = REQ-005 AND status = ACCEPTED
   - Conta quantos templates sugeridos têm evidência correspondente
   - Aplica lógica de status (seção 10)
2. Retorna status_indicativo com status_note conservadora
3. Status é exposto na API e no dossiê; nunca é persistido como "CONFORME"
```

---

### 12.6 Status indicativo → dossiê técnico

```
1. Operador solicita geração de DossieTecnico para ETAPA_1
2. DossieService lê:
   - ComplianceRequirement WHERE stage = "ETAPA_1"
   - ComplianceEvidence (ACCEPTED) de cada requisito
   - RequirementFindingLink de cada requisito
   - LgpdAction (por referência fraca de evidências com source_module = "lgpd")
3. Consolida pendências: requisitos sem evidência suficiente
4. Consolida riscos: links do tipo GAP ou RISK
5. Gera JSON + Markdown com nota conservadora obrigatória
6. Nenhuma tabela é modificada durante a geração
```

---

## 13. Riscos de acoplamento e mitigação

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| `AuditFinding` renomeado/removido | Referências orphãs em `ComplianceEvidence` | Baixa (achados imutáveis) | Validação em service ao criar evidência |
| `LgpdAction` removida | Referência órfã em evidência | Muito baixa (ações imutáveis) | Validação em service; `source_ref` preservado |
| `RetentionRule.codigo` alterado | Referência TEMP-* inconsistente | Baixa | `source_ref` guarda código no momento de criação |
| FK cruzada criada prematuramente | Migration de um módulo bloqueia outro | Média | Princípio: referência fraca até modelo estabilizar |
| Duplicidade `LgpdAction` + `ComplianceAction` | Retrabalho operacional | Alta | Não criar `ComplianceAction` até avaliar casos reais |
| Status automático interpretado como conformidade | Risco jurídico | Alta | `status_note` conservadora obrigatória em todo output |
| Dossiê gerado com dados desatualizados | Informação incorreta para vistoria | Média | Incluir `data_geracao` e instruir revisão antes de envio |

---

## 14. Roadmap técnico recomendado

```
[concluída]  Sprint Blueprint — definição de fronteiras e contratos
              │
              ▼
[concluída]  LGPD/Compliance-2 — ComplianceEvidence MVP (commit 4ccf50c)
  - ComplianceEvidence com campos mínimos
  - Endpoints: POST/GET/PATCH (evidências)
  - Integração por referência fraca (sem FK cruzada)
  - Testes: isolamento, criação, status, referência fraca
  - Sem PDF, sem dossiê, sem ComplianceAction
              │
              ▼
[concluída]  Sprint Compliance-3 — RequirementFindingLink MVP (commit c588bc2)
  - RequirementFindingLink com enums próprios e UniqueConstraint
  - Endpoints: POST/GET/GET detail/PATCH (requirement-links)
  - Referência fraca: source_module / source_type / source_ref
  - risk_level (INFO/LOW/MEDIUM/HIGH/CRITICAL) no lugar de link_type
  - Testes: model, service, routes, isolamento (376 passed)
  - Sem ComplianceStatus, sem FK cruzada, sem DELETE
              │
              ▼
Sprint Compliance-4 — ComplianceStatus — status indicativo
  - Cálculo de status por requisito (regra da seção 10)
  - Exposto nos endpoints de requirement
  - status_note conservadora obrigatória
              │
              ▼
LGPD-2 — Evidências, hash, políticas versionadas, treinamentos
  (pode ser paralela às sprints de compliance acima)
              │
              ▼
Sprint DossieTecnico — consolidação por etapa
  - DossieService: leitura de compliance, referências fracas a audit/lgpd
  - Saída: JSON + Markdown por etapa
  - Sem PDF nesta sprint
              │
              ▼
Sprint PDF/Vistoria — exportação para Sistema Justiça Aberta
  - Geração de PDF do dossiê
  - Estrutura _VISTORIA/ consolidada
  - Checklist de prontidão para vistoria
```

---

## 15. Critérios de aceite para próximas sprints

### LGPD/Compliance-2 — ComplianceEvidence MVP

- [ ] `ComplianceEvidence` criada via `POST` com todos os campos do modelo
- [ ] Listagem por `requirement_id` com filtro por `status`
- [ ] `source_module = "audit"` → service valida que `source_ref` corresponde a
      um finding existente (busca por DIAG-* no serviço de audit) antes de aceitar
- [ ] `source_module = "lgpd"` → service valida que `source_ref` corresponde a
      um `action_code` existente antes de aceitar
- [ ] Nenhuma FK direta para tabelas de audit, lgpd ou retention
- [ ] Status inicial sempre `DRAFT` ou `PENDING_REVIEW`
- [ ] `status_note` conservadora incluída em toda resposta
- [ ] Testes de isolamento: nenhum import de `audit`, `lgpd`, `retention` em
      `app/modules/compliance/`
- [ ] Ruff clean; testes passando

### Sprint Compliance-3 — RequirementFindingLink ✅ concluída (commit c588bc2)

- [x] Link criado com `requirement_code`, `source_module`, `source_type`, `source_ref`
- [x] `requirement_code` inexistente retorna 404
- [x] Duplicata `(requirement_id, source_module, source_type, source_ref)` retorna 400
- [x] Listagem com filtros: `requirement_code`, `source_module`, `source_type`,
      `source_ref`, `risk_level`
- [x] PATCH: campos opcionais atualizáveis; requirement não pode ser trocado;
      campos NOT NULL rejeitam null explícito (422)
- [x] DELETE não exposto
- [x] Testes: model, service, routes, isolamento — 376 passed, 1 skipped
- [x] Ruff clean
- [ ] `link_type` (GAP/RISK/etc.) — **não implementado**; substituído por
      `risk_level` (INFO..CRITICAL); decisão conservadora da sprint
- [ ] Validação de `source_ref` contra módulos externos — **não implementada**;
      referência fraca intencional (ADR-002)
- [ ] Status indicativo calculado após criação de link — **não implementado**;
      aguarda Sprint Compliance-4

### Sprint ComplianceStatus

- [ ] Status calculado para cada `ComplianceRequirement` via endpoint
- [ ] Enum `ComplianceStatus` com valores da seção 10
- [ ] `status_note` com texto conservador fixo em toda resposta
- [ ] Nenhum status automático com semântica de "conforme" ou "aprovado"
- [ ] Testes: cada status, transições, casos de borda

---

## 16. Decisões pendentes

| # | Questão | Impacto | Quando resolver |
|---|---------|---------|-----------------|
| D-01 | `ComplianceAction` deve nascer própria ou só referenciar `LgpdAction`? | Evitar duplicidade | Antes de LGPD/Compliance-3 |
| D-02 | Quantas evidências `ACCEPTED` são suficientes para status `EVIDENCED`? | Cálculo de status | Antes de ComplianceStatus sprint |
| D-03 | Validação jurídica do status indicativo: quem valida e com qual periodicidade? | Risco jurídico | Antes de expor status em relatórios para vistoria |
| D-04 | Formato do dossiê técnico para Sistema Justiça Aberta: JSON estruturado, PDF, ou ambos? | Sprint DossieTecnico | Antes de sprint DossieTecnico |
| D-05 | `RetentionEvaluation` (persistida): sprint retention-1C antes ou depois de LGPD/Compliance-2? | Prioridade de roadmap | Próximo ciclo de planejamento |
| D-06 | Autenticação multiusuário: antecipada para antes de expor evidências via API? | Segurança | Urgente — antes de LGPD/Compliance-2 se evidências forem sensíveis |
| D-07 | ~~`RequirementFindingLink`: permitir criação por fonte externa (sem `source_ref` de módulo)?~~ | ✅ Resolvido | `source_module=MANUAL` e `source_module=EXTERNAL` implementados; `source_ref` é string livre |
| D-08 | Prazo de expiração de evidência: sistema calcula com base no prazo do requisito ou é manual? | Enum `EXPIRED` | Antes de ComplianceStatus sprint |
