# Blueprint de Integração Regulatória — CNJ 213

> **Aviso:** Este documento é um plano arquitetural e não constitui declaração de
> conformidade jurídica. Decisões técnicas aqui propostas são sujeitas a validação
> humana antes de implementação. Status indicativo nunca equivale a declaração de
> conformidade.

Última atualização: 2026-05-07
Versão: 1.4 — Documentação Compliance-4 e preparação Document Registry-0
Estado: Em implementação — ComplianceRequirementStatus MVP entregue; próxima: Document Registry-0

---

## 1. Objetivo

Este documento registra as **fronteiras adotadas, decisões arquiteturais tomadas,
contratos futuros pendentes e roadmap de implementação** para os módulos regulatórios
do Cartório System:

```
audit       → diagnóstico documental e técnico
retention   → temporalidade documental (Provimento CNJ nº 50/2015)
lgpd        → operacionalização do plano de proteção de dados
compliance  → consolidação regulatória (Provimento CNJ nº 213/2026)
```

As sprints Compliance-2, Compliance-3 e Compliance-4 já foram implementadas;
as seções correspondentes refletem o estado real do código.
Seções marcadas como "futuro" ou "não implementar" descrevem especificações
conceituais ainda não materializadas em código.

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
- LGPD/Compliance-4 — `ComplianceRequirementStatus` MVP (2026-05-07, commit `d782013`)

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
- `ComplianceRequirementStatus` — status indicativo derivado por requisito.
  "View materializada conceitual": reconstruível por recompute REST explícito.
  Campos: `status`, contadores de evidência e link, `human_review_required`,
  `status_note` conservadora, `computed_at`, e campos de revisão humana
  (`review_note`, `reviewed_by`, `reviewed_at`) somente leitura nesta sprint.
  Enum `ComplianceRequirementStatusValue`: `EVIDENCE_PENDING`, `EVIDENCE_AVAILABLE`,
  `HAS_OPEN_FINDINGS`, `NEEDS_HUMAN_REVIEW`, `UNDER_REVIEW` (reservado).
- `ComplianceRequirementStatusHistory` — histórico append-only de mutações de
  status e contadores. FK somente para `compliance_requirements.id`. Sem FK
  para o status atual. Sem `UPDATE`, sem `DELETE`.
- Seed determinístico e idempotente da Matriz INOVA V1
- Endpoints: GET (requisitos, políticas, etapas, summary) +
  POST/GET/PATCH (evidências) + POST/GET/PATCH (requirement-links) +
  GET/POST-recompute (status indicativo)

**O que não existe ainda:**

- `ComplianceAction` — ação corretiva regulatória
- `PATCH` humano para campos de revisão (`review_note`, `reviewed_by`, `reviewed_at`)
- Upload de arquivos de evidência (hash SHA-256, armazenamento binário)
- Auto-recompute de status ao criar evidência ou vínculo
- Integração real bidirecional com audit, lgpd ou retention (apenas referência fraca)
- Dossiê técnico consolidado
- Módulo `document_registry` (planejado; fora do escopo de `compliance`)

**Fronteira estrita:** nenhum import de `audit`, `lgpd` ou `retention` no código
(ADR-001, ADR-002). `ComplianceRequirementStatus` não possui FK cruzada com
nenhum outro módulo.

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

**Decisão adotada (implementada na Compliance-2):** `ComplianceEvidence` é a
entidade central de evidência regulatória real, pertencente ao módulo `compliance`.

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

**Decisão adotada (implementada nas Compliance-2 e Compliance-3):** a integração
entre `compliance` e os demais módulos ocorre por **referência fraca**, não por
foreign key direta entre módulos.

### Modelo conceitual de referência fraca

O padrão conceitual de referência fraca usa três campos:

```
source_module  →  identifica o módulo de origem
source_type    →  identifica a natureza da referência
source_ref     →  código textual livre que aponta ao recurso externo
```

A materialização desse padrão varia por entidade:

- **`ComplianceEvidence`**: `source_module` é enum (`ComplianceEvidenceSourceModule`),
  `source_type` é string livre (`str(64)`), `source_ref` é string livre (`str(200)`).
- **`RequirementFindingLink`**: `source_module` é enum (`ComplianceLinkSourceModule`),
  `source_type` é enum (`ComplianceLinkSourceType`), `source_ref` é string obrigatória
  (`str(200)`).

Exemplos de valores para orientação:

```
source_module : "AUDIT" | "RETENTION" | "LGPD" | "EXTERNAL" | "MANUAL"
source_type   : "FINDING" | "SIGNAL" | "ACTION" | "DOCUMENT" | "MANUAL_NOTE" | ...
source_ref    : "DIAG-004" | "TEMP-002" | "AC-15" | "98-PSI.docx" | ...
```

Em nenhum caso há FK entre tabelas de módulos distintos.

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

Até então, a verificação operacional do `source_ref` é responsabilidade do
operador humano no momento do registro; não há validação cruzada automática
contra módulos externos nesta fase (ADR-002).

---

## 7. `ComplianceEvidence` — implementado na Compliance-2 e evolução futura

> **Implementado (MVP).** Commit `4ccf50c` — Sprint LGPD/Compliance-2 (2026-05-06).
> A seção abaixo descreve primeiro o que existe no MVP e depois o que ainda é
> especificação futura.

### 7.1 Campos implementados no MVP

```
ComplianceEvidence
├── id                    Integer     PK autoincrement
├── requirement_id        Integer     FK → compliance_requirements.id (NOT NULL, CASCADE)
├── evidence_template_id  Integer     FK → compliance_evidence_templates.id (nullable, SET NULL)
│                                     referência à evidência sugerida pela Matriz
├── title                 str(300)    NOT NULL — descrição curta
├── description           text        NOT NULL — detalhamento
├── evidence_type         enum        NOT NULL — ComplianceEvidenceType
├── status                enum        NOT NULL — ComplianceEvidenceStatus (default COLLECTED)
├── source_module         enum        NOT NULL — ComplianceEvidenceSourceModule (default MANUAL)
├── source_type           str(64)     nullable — natureza da referência (string livre)
├── source_ref            str(200)    nullable — código de referência (ex: "DIAG-004")
├── file_reference        str(500)    nullable — caminho relativo em _VISTORIA/
├── responsible_name      str(200)    nullable — quem coletou/validou
├── collected_at          datetime    nullable — data de coleta
├── reviewed_at           datetime    nullable — data de revisão
├── notes                 text        nullable — observações
├── created_at            datetime    automático
└── updated_at            datetime    automático
```

### 7.2 Enum `ComplianceEvidenceType` (implementado)

```
DOCUMENT          → documento formal (PDF, DOCX, contrato)
POLICY            → política ou procedimento versionado
REPORT            → relatório gerado pelo sistema
SCREENSHOT        → captura de tela
LOG               → log de sistema
DECLARATION       → declaração formal
CONTRACT          → contrato ou instrumento formal
CERTIFICATE       → certificado ou atestado
MEETING_MINUTES   → ata de reunião
CONFIGURATION     → configuração de sistema documentada
EXTERNAL_REFERENCE → referência externa
OTHER             → outros
```

### 7.3 Enum `ComplianceEvidenceStatus` (implementado)

```
COLLECTED      → registrada; estado inicial padrão
UNDER_REVIEW   → em revisão humana
ACCEPTED       → revisada e aceita
REJECTED       → revisada e rejeitada (motivo em notes)
EXPIRED        → prazo vencido
NEEDS_UPDATE   → válida, mas requer atualização
```

> **Nota de MVP:** no cálculo de status indicativo (Compliance-4), todas as
> evidências contam independentemente do status — inclusive `REJECTED` e `EXPIRED`.
> Distinções por status de evidência ficam para Compliance-5+.

### 7.4 Enum `ComplianceEvidenceSourceModule` (implementado)

```
MANUAL     → registrada manualmente pelo gestor
EXTERNAL   → documento externo (sem referência a módulo interno)
AUDIT      → referência a achado do módulo audit
RETENTION  → referência a sinal do módulo retention
LGPD       → referência a ação do módulo lgpd
SYSTEM     → gerada pelo próprio sistema
```

### 7.5 Endpoints implementados (MVP)

- `POST /compliance/evidences` — registra evidência; status inicial `COLLECTED`.
- `GET /compliance/evidences` — lista, filtrável por `requirement_code`, `status`,
  `source_module`.
- `GET /compliance/evidences/{id}` — detalhe com campo `evidence_note` conservador.
- `PATCH /compliance/evidences/{id}` — atualização parcial. DELETE não exposto.

### 7.6 O que `ComplianceEvidence` não deve fazer (invariante)

- Não deve replicar dados de outras tabelas (não copiar `title` do `AuditFinding`).
- Não deve ser o único critério automático de status de requisito.
- Não deve ser criada por processos automáticos sem revisão humana posterior.
- Não deve armazenar dados pessoais de titulares (apenas metadados).

### 7.7 Evolução futura — não implementado no MVP

- Upload de arquivo binário com hash SHA-256 e armazenamento controlado.
- Validação cruzada de `source_ref` contra módulo de origem (decidido como
  referência fraca intencional — ver ADR-002; pode mudar em sprint futura).
- Status `DRAFT` não existe no MVP; se necessário, avaliar antes de Compliance-5.
- Distinção de cálculo de status por `evidence_status` (apenas `ACCEPTED` conta)
  — avaliação pendente para Compliance-5+.
- Geração de dossiê a partir de evidências.

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
| Status indicativo | Previsto após criação de link | **Implementado na Compliance-4** — recompute REST explícito; link com `risk_level` HIGH/CRITICAL gera `HAS_OPEN_FINDINGS` |

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

- `ComplianceEvidence` e `RequirementFindingLink`, embora já existentes como MVPs,
  estarem validados com casos de uso operacionais reais na serventia
- Haver ao menos um caso real que exige ação corretiva regulatória não
  coberta pelo plano LGPD

---

## 10. Modelo implementado de `ComplianceRequirementStatus`

> **Implementado.** Commit `d782013` — Sprint LGPD/Compliance-4 (2026-05-07).

A seção a seguir documenta o que foi efetivamente implementado, contrastando com
a especificação original onde houve divergências de escopo conservadoras.

### Enum implementado: `ComplianceRequirementStatusValue`

```
EVIDENCE_PENDING   → sem evidência registrada e sem achado vinculado
EVIDENCE_AVAILABLE → uma ou mais evidências registradas; sem achados vinculados
HAS_OPEN_FINDINGS  → há link com risk_level CRITICAL ou HIGH
NEEDS_HUMAN_REVIEW → há link com risk_level MEDIUM, LOW, INFO ou NULL
UNDER_REVIEW       → reservado para sprint futura; não emitido pelo recompute atual
```

**Diferenças em relação à especificação original (seção 10 anterior):**

| Aspecto | Proposta original | Implementado |
| ------- | ----------------- | ------------ |
| `NOT_STARTED` | Previsto | **Não implementado** — sem evidência e sem link resulta em `EVIDENCE_PENDING` |
| `MAPPED_ONLY` | Previsto | **Não implementado** — mesclado em `EVIDENCE_PENDING` (MVP conservador) |
| `PARTIAL_EVIDENCE` | Previsto | **Não implementado** — MVP não conta templates satisfeitos |
| `EVIDENCED` | Previsto | **Não implementado** — evita qualquer semântica de "cumprimento" automático |
| `NEEDS_REVIEW` | Previsto | **Não implementado** — aguarda lógica de prazo definida |
| `EXPIRED` | Previsto | **Não implementado** — aguarda definição de prazo de expiração de evidência |
| `UNDER_REVIEW` | Previsto | **Reservado** — existe no enum; não emitido pelo recompute nesta sprint |

A simplificação do MVP é intencional e conservadora: evita qualquer semântica que
possa ser interpretada como afirmação de conformidade.

### Regras de cálculo implementadas

```
risk_level CRITICAL ou HIGH em qualquer link → HAS_OPEN_FINDINGS  (human_review_required=True)
qualquer outro link (MEDIUM/LOW/INFO/NULL)   → NEEDS_HUMAN_REVIEW (human_review_required=True)
evidência(s) presente(s), sem links          → EVIDENCE_AVAILABLE  (human_review_required=False)
sem evidência e sem link                     → EVIDENCE_PENDING    (human_review_required=False)
```

Notas de implementação:

- `NULL risk_level` é tratado como equivalente a `INFO`.
- Todas as evidências contam no MVP, independentemente do status
  (`COLLECTED`, `REJECTED`, `EXPIRED`, etc.).
- `last_evidence_at` usa `MAX(COALESCE(collected_at, created_at))`.
- `last_link_at` usa `MAX(created_at)` de `RequirementFindingLink`.

### Regras obrigatórias de linguagem (mantidas)

- **Proibido como status automático:** `COMPLIANT`, `CONFORME`, `APROVADO`,
  `CUMPRIDO`, `REGULAR`, `CERTIFIED`, `VALIDADO COMO CONFORME`.
- `status_note` é validada contra essa lista em tempo de execução; presença de
  termo proibido levanta `RuntimeError` antes de persistir.
- Todo endpoint que expõe status inclui disclaimer fixo:
  > "Este status é indicativo e não representa declaração automática de
  > conformidade. A conclusão depende de revisão humana e validação documental."

### Idempotência e histórico

- Recompute redundante não cria histórico, não toca `computed_at`, `updated_at`
  ou `status_note`, e não marca o objeto SQLAlchemy como dirty.
- Primeira computação cria history com `previous_status=NULL`.
- Mudança de status ou contadores cria history com `change_reason` descritivo.
- `ComplianceRequirementStatusHistory` é append-only: sem `UPDATE`, sem `DELETE`,
  sem FK para o snapshot de status atual.

### Campos de revisão humana (somente leitura nesta sprint)

`review_note`, `reviewed_by`, `reviewed_at` existem no modelo e são expostos nas
respostas. Sem endpoint de escrita nesta sprint. O recompute nunca os altera.
`UNDER_REVIEW` como status de revisão humana está reservado para **Compliance-6**.

### Limitações remanescentes desta sprint

- Não há auto-recompute ao criar evidência ou vínculo.
- Não há `PATCH` humano para campos de revisão.
- Não há `DELETE` de status ou histórico.
- Não há dashboard, relatório, PDF ou dossiê.
- Não há FK cruzada com outros módulos.

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
│   └── risk_level, notes                  ← (link_type não existe; usar risk_level)
│
├── acoes_lgpd_relacionadas[]              → referência fraca a LgpdAction
│   ├── action_code, title, status
│   └── completed_date
│
├── pendencias[]                           → requisitos com status EVIDENCE_PENDING
├── riscos[]                               → links com risk_level HIGH ou CRITICAL
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
4. Gestor cria RequirementFindingLink via POST /compliance/requirement-links:
     requirement_code = "REQ-013" (ex: controle de acesso documental)
     source_module    = "AUDIT"
     source_type      = "FINDING"
     source_ref       = "DIAG-004"
     risk_level       = "HIGH"   ← (ou CRITICAL, MEDIUM, LOW, INFO conforme severidade)
5. Gestor executa recompute: POST /compliance/requirements/REQ-013/status/recompute
   → risk_level HIGH resulta em status HAS_OPEN_FINDINGS (human_review_required=True)
6. Gestor inicia ação corretiva (manual ou via ComplianceAction futura)
7. Após tratamento, gestor cria ComplianceEvidence via POST /compliance/evidences:
     requirement_code = "REQ-013"
     evidence_type    = "DOCUMENT"  ← (tipo conforme o artefato coletado)
     source_module    = "AUDIT"
     source_ref       = "DIAG-004"
     status           = "COLLECTED" ← status inicial padrão
8. Gestor executa recompute novamente; o status é recalculado
   → enquanto o link HIGH permanecer, status continua HAS_OPEN_FINDINGS
   → se o link for atualizado para risk_level baixo, pode evoluir para NEEDS_HUMAN_REVIEW
9. Revisão humana decide o encaminhamento final
```

**Nota:** audit não sabe dos passos 4..9. A tabela `audit_findings` não é alterada.
O recompute é sempre explícito via REST — não há trigger automático.

---

### 12.2 TEMP-* do retention → alerta de temporalidade

```
1. CLI roda DocumentDiagnosis com --with-retention-rules
2. Regra TEMP-002 emite finding para arquivo aparentemente vencido
3. Gestor revisa o finding com responsável jurídico/documental
4. Decisão: arquivo deve ser encaminhado para guarda intermediária
5. Gestor cria RequirementFindingLink via POST /compliance/requirement-links:
     requirement_code = "REQ-XXX" (requisito de temporalidade relevante)
     source_module    = "RETENTION"
     source_type      = "SIGNAL"
     source_ref       = "TEMP-002"
     risk_level       = "HIGH"   ← (conforme avaliação humana do risco)
6. Gestor executa recompute: POST /compliance/requirements/REQ-XXX/status/recompute
   → risk_level HIGH resulta em HAS_OPEN_FINDINGS (human_review_required=True)
7. Ação corretiva documentada manualmente (fora do sistema por ora)
8. Após resolução: ComplianceEvidence criada via POST /compliance/evidences:
     evidence_type = "DOCUMENT"  ← (conforme artefato comprobatório disponível)
     source_module = "RETENTION"
     source_ref    = "TEMP-002"
9. Tabela retention_rules não é alterada; signals TEMP não são deletados
```

---

### 12.3 Ação LGPD → evidência regulatória

```
1. Gestor registra AC-15 como COMPLETED (módulo lgpd)
2. Módulo lgpd registra completed_date em lgpd_actions
3. Gestor identifica que AC-15 (nomeação do DPO) é relevante para REQ-005
   (ex: designação de responsável pela proteção de dados)
4. Gestor cria ComplianceEvidence via POST /compliance/evidences:
     requirement_code = "REQ-005"
     evidence_type    = "DECLARATION"  ← (ou DOCUMENT; não existe LGPD_ACTION no enum)
     source_module    = "LGPD"
     source_type      = "lgpd_action"  ← (string livre)
     source_ref       = "AC-15"
     status           = "COLLECTED"    ← status inicial padrão
5. Gestor executa recompute: POST /compliance/requirements/REQ-005/status/recompute
   → sem links, com evidência → status EVIDENCE_AVAILABLE (human_review_required=False)
6. Revisão humana decide o encaminhamento final; o status indicativo é sinalização
   operacional, não declaração de conformidade
```

**Nota:** `lgpd_actions` não recebe campo `compliance_evidence_id`. O vínculo
existe apenas na direção compliance → lgpd, por referência fraca.
No MVP, todas as evidências contam para o status, independentemente de `status`.
A distinção por `evidence_status = ACCEPTED` é evolução futura (Compliance-5+).

---

### 12.4 EvidenceTemplate → Evidence real

```
1. GET /compliance/requirements/REQ-005 retorna evidence_templates[]
     template: "Ata de designação do DPO assinada pelo responsável"
2. Gestor coleta o documento real
3. Gestor cria ComplianceEvidence via POST /compliance/evidences:
     requirement_code      = "REQ-005"
     evidence_template_id  = id do template  ← (opcional; associa ao template sugerido)
     evidence_type         = "DOCUMENT"
     source_module         = "EXTERNAL"
     file_reference        = "_VISTORIA/01_Governanca/Atas/ata_dpo.pdf"
     status                = "COLLECTED"     ← status inicial padrão
4. Gestor executa recompute: POST /compliance/requirements/REQ-005/status/recompute
5. Revisão humana atualiza o status da evidência via PATCH /compliance/evidences/{id}
```

O `evidence_template_id` é opcional: evidências sem template correspondente também
são válidas (ex: evidência não prevista pela Matriz INOVA).

---

### 12.5 Evidence real → status indicativo (recompute explícito)

```
1. Gestor chama POST /compliance/requirements/REQ-005/status/recompute
2. ComplianceService aplica as regras de cálculo (seção 10):
   - Conta RequirementFindingLink com risk_level CRITICAL/HIGH → HAS_OPEN_FINDINGS
   - Conta quaisquer outros links (MEDIUM/LOW/INFO/NULL) → NEEDS_HUMAN_REVIEW
   - Conta ComplianceEvidence (todas, independente de status) → EVIDENCE_AVAILABLE
   - Sem evidência e sem link → EVIDENCE_PENDING
3. Persiste ComplianceRequirementStatus com status_note conservadora
4. Cria ComplianceRequirementStatusHistory se houve mutação
5. Retorna: { mutated, status, change_reason, ... }
6. Status é exposto em GET /compliance/requirements/REQ-005/status
   Toda resposta inclui disclaimer: "Este status é indicativo e não representa
   declaração automática de conformidade. A conclusão depende de revisão humana
   e validação documental."
```

**Nota:** não há cálculo automático ao criar evidência. O recompute é sempre
explícito. Não há contagem de templates satisfeitos no MVP. Todas as evidências
contam, independentemente de `evidence_status`.

---

### 12.6 Status indicativo → dossiê técnico (fluxo futuro — não implementado)

> **Não implementado.** Este fluxo é especificação conceitual para sprint futura
> (Sprint DossieTecnico). As referências abaixo refletem o modelo atual implementado.

```
1. Operador solicita geração de DossieTecnico para ETAPA_1
2. DossieService (futuro) lê:
   - ComplianceRequirement WHERE stage = "ETAPA_1"
   - ComplianceRequirementStatus de cada requisito (já computados via recompute)
   - ComplianceEvidence de cada requisito (todas as evidências registradas)
   - RequirementFindingLink de cada requisito, com seu risk_level
   - LgpdAction (por referência fraca de evidências com source_module = "LGPD")
3. Consolida sinalização operacional:
   - Requisitos com status EVIDENCE_PENDING → sem evidência ou vínculo
   - Requisitos com status HAS_OPEN_FINDINGS → links CRITICAL/HIGH pendentes
   - Requisitos com status NEEDS_HUMAN_REVIEW → links de risco médio/baixo
4. Consolida links por risk_level (HIGH/CRITICAL como prioridade de revisão)
5. Gera JSON + Markdown com nota conservadora obrigatória
6. Nenhuma tabela é modificada durante a geração
```

**Nota:** o dossiê não deve usar `link_type` (campo não implementado); usa
`risk_level`. Não deve filtrar evidências por `status = ACCEPTED` (distinção
por evidence_status é evolução futura). Deve incluir disclaimer conservador
em toda saída.

---

## 13. Riscos de acoplamento e mitigação

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| `AuditFinding` renomeado/removido | Referências orphãs em `ComplianceEvidence` | Baixa (achados imutáveis) | Revisão humana e rastreabilidade operacional; `source_ref` preservado no registro; sem validação cruzada automática nesta fase |
| `LgpdAction` removida | Referência órfã em evidência | Muito baixa (ações imutáveis) | Rastreabilidade operacional; `source_ref` preservado no registro; integridade é responsabilidade do operador humano (ADR-002) |
| `RetentionRule.codigo` alterado | Referência TEMP-* inconsistente | Baixa | `source_ref` guarda código no momento de criação |
| FK cruzada criada prematuramente | Migration de um módulo bloqueia outro | Média | Princípio: referência fraca até modelo estabilizar |
| Duplicidade `LgpdAction` + `ComplianceAction` | Retrabalho operacional | Alta | Não criar `ComplianceAction` até avaliar casos reais |
| Status automático interpretado como conformidade | Risco jurídico | Alta | `status_note` conservadora obrigatória em todo output |
| Dossiê gerado com dados desatualizados | Informação incorreta para vistoria | Média | Executar recompute antes de gerar dossiê; incluir `data_geracao` e instruir revisão antes de envio |

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
[concluída]  Sprint Compliance-4 — ComplianceRequirementStatus MVP (commit d782013)
  - ComplianceRequirementStatus: status indicativo derivado por requisito
  - ComplianceRequirementStatusHistory: histórico append-only
  - Recompute REST explícito: bulk (lotes de 100) e individual
  - Idempotência estrita: sem history em recompute redundante
  - Campos humanos somente leitura; UNDER_REVIEW reservado
  - Disclaimer conservador obrigatório em todo output de status
  - Testes: model, service, routes, isolamento, history (433 passed)
  - Sem PATCH humano, sem DELETE, sem auto-recompute, sem FK cruzada
              │
              ▼
[próxima — documental/normativa]
  Document Registry-0 — CNPFE-GO Normative Matrix Blueprint
  - Sem implementação de código
  - Mapeamento normativo de documentos, livros, acervo, arquivos,
    pastas e classificadores esperados (CNPFE-GO)
  - Definição da arquitetura conceitual do módulo document_registry
  - document_registry será dono da matriz documental e do inventário
    institucional; compliance consumirá por referência fraca
              │
              ▼
[futuro]  Document Registry-1 — Expected Documents MVP
  - Matriz de documentos esperados
  - Candidatos encontrados pelo audit
  - Conciliação entre esperado e observado; lacunas documentais
              │
              ▼
[futuro]  Compliance-5 — Operational Reporting MVP
  - Relatórios operacionais indicativos
  - Consolidação de compliance + document_registry
  - Depende de Document Registry-0/1
              │
              ▼
[futuro]  Compliance-6 — Human Review MVP
  - PATCH humano: review_note, reviewed_by, reviewed_at
  - Uso efetivo de UNDER_REVIEW
  - Workflow de revisão humana explícita
              │
              ▼
[futuro]  LGPD-2 — Evidências, hash, políticas versionadas, treinamentos
              │
              ▼
[futuro]  Sprint DossieTecnico — consolidação por etapa
  - DossieService: leitura de compliance, referências fracas a audit/lgpd
  - Saída: JSON + Markdown por etapa
  - Sem PDF nesta sprint
              │
              ▼
[futuro]  Sprint PDF/Vistoria — exportação para Sistema Justiça Aberta
  - Geração de PDF do dossiê
  - Estrutura _VISTORIA/ consolidada
  - Checklist de prontidão para vistoria
```

### Relação futura entre módulos

```text
audit
  → encontra arquivos, caminhos, metadados, duplicidades,
    localização inadequada e achados documentais (DIAG-*)

document_registry  ← próxima frente prioritária (Document Registry-0/1)
  → compara arquivos encontrados pelo audit com a matriz normativa
    de documentos esperados (CNPFE-GO)
  → dono da matriz documental e do inventário institucional
  → não deve ser confundido com compliance

retention
  → aplica temporalidade, guarda, destinação e eliminação documental
    quando aplicável (TEMP-*)

lgpd
  → avalia privacidade, dados pessoais, sigilo e risco ao titular (AC-*)

compliance
  → consolida evidências, lacunas e achados contra requisitos regulatórios
  → não declara conformidade automática
  → consumirá document_registry por referência fraca:
      source_module: "document_registry"
      source_type:   "expected_document_match" | "missing_expected_document"
      source_ref:    "DOCMATCH-000123" | "DOCGAP-000045"

reports (futuro)
  → visão operacional e gerencial para diretoria e equipe
```

> **Nota:** O módulo `document_registry` ainda não foi implementado.
> Document Registry-0 é exclusivamente documental/normativo — sem código.
> A integração entre `compliance` e `document_registry` ocorrerá por referência
> fraca, seguindo ADR-002, preservando o isolamento modular.

---

## 15. Critérios de aceite para próximas sprints

### LGPD/Compliance-2 — ComplianceEvidence MVP ✅ concluída (commit `4ccf50c`)

- [x] `ComplianceEvidence` criada via `POST` com campos do modelo MVP
- [x] Listagem por `requirement_code` com filtro por `status` e `source_module`
- [x] Nenhuma FK direta para tabelas de `audit`, `lgpd` ou `retention`
- [x] Status inicial padrão `COLLECTED` (não `DRAFT` — enum diferente da proposta original)
- [x] Campo `evidence_note` conservador incluído em toda resposta de detalhe
- [x] Testes de isolamento: nenhum import de `audit`, `lgpd`, `retention` em
      `app/modules/compliance/`
- [x] Ruff clean; testes passando
- [~] Validação forte de `source_ref` contra módulo de origem — **decisão
      arquitetural: não implementar** (ADR-002). Referência fraca é a estratégia
      adotada. Integridade referencial entre módulos é responsabilidade do
      operador humano, não do banco de dados.
- [~] Status `DRAFT` — **decisão: não implementar no MVP**; avaliar em
      Compliance-5+ somente se surgir caso de uso específico.

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
- [~] `link_type` (GAP/RISK/etc.) — **substituído definitivamente por `risk_level`
      (INFO..CRITICAL)**; decisão conservadora e arquitetural desta sprint
- [~] Validação forte de `source_ref` contra módulos externos — **decisão
      arquitetural: não implementar** (ADR-002). Referência fraca intencional.

### Sprint Compliance-4 — ComplianceRequirementStatus ✅ concluída (commit d782013)

- [x] `ComplianceRequirementStatus` criado por recompute REST explícito
- [x] Enum `ComplianceRequirementStatusValue` com valores conservadores (seção 10)
- [x] Recompute bulk: `POST /requirement-statuses/recompute` — lotes de 100, savepoint
- [x] Recompute individual: `POST /requirements/{code}/status/recompute`
- [x] Leitura paginada: `GET /requirement-statuses` com filtros múltiplos
- [x] Detalhe: `GET /requirements/{code}/status` — 404 se não computado
- [x] `status_note` conservadora com validação contra termos proibidos
- [x] Disclaimer obrigatório em toda resposta de status
- [x] Idempotência estrita: recompute redundante não cria history nem toca timestamps
- [x] `ComplianceRequirementStatusHistory` append-only: sem UPDATE, sem DELETE
- [x] Campos humanos somente leitura; recompute nunca os altera
- [x] Sem auto-recompute ao criar evidência ou vínculo
- [x] Nenhum status com semântica de "conforme" ou "aprovado"
- [x] Isolamento modular: sem import de `audit`, `lgpd`, `retention`; sem FK cruzada
- [x] Testes: model, service, routes, history, isolamento — 433 passed, 1 skipped
- [x] Ruff clean
- [ ] `UNDER_REVIEW` — **reservado**; não emitido pelo recompute; aguarda Compliance-6
- [ ] `PATCH` humano para `review_note`, `reviewed_by`, `reviewed_at` — aguarda Compliance-6
- [ ] Auto-recompute ao criar evidência/vínculo — **não implementado** (recompute é explícito)

### Document Registry-0 — CNPFE-GO Normative Matrix Blueprint

- [ ] Mapeamento normativo de documentos, livros, acervo, arquivos e pastas esperados
      conforme CNPFE-GO
- [ ] Definição da arquitetura conceitual do módulo `document_registry`
- [ ] Definição de como `compliance` consumirá `document_registry` por referência fraca
- [ ] Escopo exclusivamente documental/normativo: sem implementação de código

---

## 16. Decisões pendentes

| # | Questão | Impacto | Quando resolver |
|---|---------|---------|-----------------|
| D-01 | `ComplianceAction` deve nascer própria ou só referenciar `LgpdAction`? | Evitar duplicidade | Antes de implementar ComplianceAction |
| D-02 | ~~Quantas evidências `ACCEPTED` são suficientes para status `EVIDENCED`?~~ | ✅ Adiado | MVP Compliance-4 não usa `EVIDENCED`; reavaliar em Compliance-5+ |
| D-03 | Validação jurídica do status indicativo: quem valida e com qual periodicidade? | Risco jurídico | Antes de expor status em relatórios para vistoria |
| D-04 | Formato do dossiê técnico para Sistema Justiça Aberta: JSON estruturado, PDF, ou ambos? | Sprint DossieTecnico | Antes de sprint DossieTecnico |
| D-05 | `RetentionEvaluation` (persistida): sprint retention-1C — prioridade no roadmap? | Prioridade de roadmap | Próximo ciclo de planejamento |
| D-06 | Autenticação multiusuário: antecipada para antes de expor evidências via API? | Segurança | Avaliar antes de Compliance-5 |
| D-07 | ~~`RequirementFindingLink`: permitir criação por fonte externa?~~ | ✅ Resolvido | `source_module=MANUAL/EXTERNAL` implementados; `source_ref` é string livre |
| D-08 | ~~Prazo de expiração de evidência: sistema calcula ou é manual?~~ | ✅ Adiado | MVP Compliance-4 não usa `EXPIRED` em status; reavaliar em Compliance-5+ |
| D-09 | Escopo de Document Registry-0: CNPFE-GO é a fonte principal da matriz inicial; Provimento 213, Provimento CNJ nº 50/2015 e INOVA entram como integrações complementares/futuras após a base estadual estar mapeada. | Abrangência da matriz | Confirmar no início de Document Registry-0 |
| D-10 | Como `compliance` referenciará `document_registry` por referência fraca? Códigos `DOCMATCH-*` e `DOCGAP-*` são suficientes? | Integração futura | Durante Document Registry-0 |
| D-11 | `PATCH` humano para revisão: campos isolados ou payload completo? Quem tem permissão? | Compliance-6 | Antes de Compliance-6 |
