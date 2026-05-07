# Módulo Compliance

## Objetivo

Representar, de forma estruturada e versionada, a Matriz de Correlação INOVA V1
do Provimento CNJ nº 213/2026, e permitir o registro de evidências regulatórias
reais vinculadas aos requisitos normativos.

O módulo apoia a organização da conformidade da serventia, mas **não declara
conformidade**, não substitui validação humana, jurídica ou administrativa, e
não emite qualquer certificação de regularidade.

## Sprints implementadas

### Sprint LGPD/Compliance-1 (fundação)

- Camada fundacional `app/modules/compliance/`.
- Modelo de dados para requisitos, políticas indicadas, prazos por classe e
  evidências sugeridas pela matriz (`ComplianceEvidenceTemplate`).
- Seed determinístico e idempotente da Matriz INOVA V1 (`matriz_v1`).
- Endpoints REST somente leitura.
- Fronteira estrita: nenhum import de `audit`, `lgpd` ou `retention`.

### Sprint LGPD/Compliance-2 — ComplianceEvidence MVP

- Entidade `ComplianceEvidence` — evidência regulatória real registrada.
- Enums: `ComplianceEvidenceType`, `ComplianceEvidenceStatus`,
  `ComplianceEvidenceSourceModule`.
- Migration `20260506_1500_add_compliance_evidences.py`.
- CRUD parcial: POST/GET/PATCH. DELETE não implementado nesta sprint.
- Integração por referência fraca: `source_module`, `source_type`, `source_ref`.
  Não há FK cruzada com `audit`, `retention` ou `lgpd` (ADR-001, ADR-002).

### Sprint LGPD/Compliance-3 — RequirementFindingLink MVP

- Entidade `RequirementFindingLink` — vínculo entre um requisito normativo e um
  achado, sinal, ação ou documento de origem externa.
- Enums: `ComplianceLinkSourceModule`, `ComplianceLinkSourceType`,
  `ComplianceLinkRiskLevel`.
- Migration `20260506_1600_add_compliance_requirement_finding_links.py`.
- CRUD parcial: POST/GET/GET detail/PATCH. DELETE não implementado.
- Unicidade: `UniqueConstraint(requirement_id, source_module, source_type, source_ref)`
  com nome `uq_compliance_requirement_finding_source`. Duplicata retorna 400.
- Integração exclusivamente por referência fraca: sem FK para `audit`,
  `retention` ou `lgpd` (ADR-002).
- Não calcula `ComplianceStatus`. Não afirma conformidade.

## O que o módulo faz

- Persiste o mapa: requisito normativo → política indicada → prazo estimado
  por classe (C1/C2/C3) → evidência sugerida → etapa.
- Fornece consultas para listar/filtrar requisitos e políticas.
- Calcula resumos por etapa e visão geral consolidada.
- Registra metadados de seed (`compliance_seed_meta`) com versão e checksum
  SHA-256 para detecção de mudanças.
- Permite registrar evidências regulatórias reais (`ComplianceEvidence`)
  vinculadas a requisitos normativos, com filtros por requisito, status e módulo
  de origem.
- Permite registrar vínculos entre requisitos e achados/sinais externos
  (`RequirementFindingLink`), por referência fraca, sem acoplamento com os
  módulos de origem.

## O que o módulo não faz

- Não declara que a serventia cumpre o Provimento.
- `ComplianceEvidenceTemplate` representa apenas a evidência sugerida pela
  matriz; `ComplianceEvidence` é a evidência real registrada, mas **não é
  validação automática de conformidade**.
- Não há upload de arquivos, armazenamento binário, geração de PDF, dossiê
  técnico, dashboard, workflow de descarte, status agregado de cumprimento ou
  cálculo automático de conformidade.
- Não importa nem consome `app.modules.audit`, `app.modules.lgpd` ou
  `app.modules.retention`.
- A referência a outro módulo via `source_module`/`source_ref` não valida a
  existência do recurso referenciado — é apenas referência fraca documental.

## Linguagem conservadora obrigatória

Toda evidência registrada exige linguagem conservadora:

- `evidência registrada para apoio à organização regulatória`
- `não representa declaração automática de conformidade`
- `exige validação humana, jurídica ou administrativa`

O campo `evidence_note` em todos os schemas de leitura repete este aviso
automaticamente.

## Relação com a Matriz INOVA V1

Origem: `Matriz_Correlacao_Provimento213_Politicas V1.pdf` (InovaLGPD,
Março 2026, v1.0).

O PDF **não é versionado no repositório** — apenas a referência textual
ao caminho local é registrada em `compliance_seed_meta.source_file_reference`:

```text
_local_data/LGPD - inova/Guia provimento 213/
Matriz_Correlacao_Provimento213_Politicas V1.pdf
```

## Entidades principais

- `ComplianceRequirement`: requisito mapeado da Matriz.
  - `source` indica a origem normativa (`PROV_213`, `LGPD`, `ANEXO_III`,
    `ANEXO_IV`, `MATRIZ_INOVA`). Mesmo quando a obrigação é LGPD, se o
    artigo está no Provimento 213 a `source` é `PROV_213`.
  - `classification` indica a natureza da obrigação (`OBRIGATORIO_LGPD`,
    `OBRIGATORIO_PROVIMENTO`, `COMPLEMENTAR_BOA_PRATICA`,
    `COMPLEMENTAR_GOVERNANCA`).
  - `mapping_status = "MAPPED"` é exposto pelo schema, **calculado** —
    não é coluna persistida.
- `CompliancePolicyDocument`: política/procedimento/documento indicado
  pela InovaLGPD. Contém `inova_filename` (apenas referência textual ao
  arquivo da consultoria; o arquivo não é servido via API).
- `ComplianceRequirementPolicy`: vínculo N:N requisito ↔ política, com
  `policy_section_notes` para registrar a seção/observação relevante.
- `ComplianceRequirementDeadline`: prazo estimado por `serventia_class`
  (`C1`/`C2`/`C3`). Pode ser numérico (`value` + `unit DIAS|MESES`) ou
  textual (`unit AO_FINAL_ETAPA`, `value=NULL`).
- `ComplianceEvidenceTemplate`: evidência sugerida pela matriz.
- `ComplianceSeedMeta`: metadados do seed `matriz_v1`, com checksum
  SHA-256 para detecção de mudanças.
- `RequirementFindingLink`: vínculo entre um `ComplianceRequirement` e um
  achado, sinal, ação ou documento de origem externa, identificado por
  `source_module` / `source_type` / `source_ref`.
  - `source_module`: origem do achado (`AUDIT`, `RETENTION`, `LGPD`,
    `MANUAL`, `EXTERNAL`).
  - `source_type`: natureza da referência (`FINDING`, `DIAGNOSIS`, `SIGNAL`,
    `ACTION`, `POLICY`, `DOCUMENT`, `MANUAL_NOTE`).
  - `source_ref`: código textual livre (ex.: `DIAG-004`, `TEMP-002`,
    `AC-01`). Não é validado contra tabelas externas — referência fraca.
  - `risk_level` (opcional): `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
  - `title`, `link_reason`, `notes`: metadados opcionais de contexto.
  - UniqueConstraint em `(requirement_id, source_module, source_type,
    source_ref)` impede vínculos duplicados da mesma origem para o mesmo
    requisito.
  - **Não declara conformidade.** A existência de um vínculo não indica
    que o requisito está atendido ou descumprido. Campo `link_note`
    conservador incluído em toda resposta.

## Tabelas

- `compliance_requirements`
- `compliance_policies`
- `compliance_requirement_policies`
- `compliance_requirement_deadlines`
- `compliance_evidence_templates`
- `compliance_seed_meta`

Criadas pela migration `c1d2e3f4b5a6 — add compliance tables`.

- `compliance_evidences`

Criada pela migration `d2e3f4a5b6c7 — add compliance evidences`.

- `compliance_requirement_finding_links`

Criada pela migration `e3f4a5b6c7d8 — add compliance requirement finding links`.
UniqueConstraint `uq_compliance_requirement_finding_link_source` em
`(requirement_id, source_module, source_type, source_ref)`.
FK interna para `compliance_requirements.id` com `ondelete=CASCADE`.
Sem FK cruzada com `audit`, `retention` ou `lgpd`.

## Seed e versionamento

Seed: `matriz_v1` (versão `V1.0_MAR2026`). Executar manualmente:

```bash
python -m app.modules.compliance.seed
```

Características:

- Determinístico: a ordem de iteração não afeta o checksum (listas
  ordenadas por chave canônica antes da serialização).
- Idempotente: upsert por `requirement.code` e `policy.code`; vínculos,
  prazos e evidências sincronizados por chaves naturais.
- Checksum SHA-256: se igual ao registrado em `compliance_seed_meta.data_checksum`,
  o seed retorna sem alterar dados.
- **Não roda automaticamente em `alembic upgrade`** — operação explícita
  do operador.

Volumes mínimos garantidos:

- Requisitos: 32 (≥ 30)
- Políticas: 30 (≥ 30)
- Vínculos requirement ↔ policy: ~75 (≥ 60)
- Prazos: 96 (≥ 80, sempre 3 por requisito — C1/C2/C3)
- Evidence templates: ~131 (≥ 90)

## Endpoints read-only

Todos sob `/api/v1/compliance`:

- `GET /requirements` — lista filtrável por `source`, `classification`,
  `stage` (paginação `limit`, `offset`).
- `GET /requirements/{code}` — detalhes do requisito, com prazos,
  evidências sugeridas e políticas vinculadas.
- `GET /policies` — lista filtrável por `kind`, `classification`.
- `GET /policies/{code}` — detalhes da política, com requisitos vinculados.
- `GET /etapas` — resumo por etapa: requisitos e políticas distintas.
- `GET /summary` — visão geral, distribuições e prazo C3 inicial
  estimado (90 dias para Etapas 1-2).

Métodos de escrita não existem (testado em `test_compliance_routes` e
`test_compliance_isolation`).

### Evidências regulatórias

Sob `/api/v1/compliance`:

- `POST /evidences` — registra evidência regulatória real; retorna 201.
  Payload: `requirement_code` (obrigatório), `title`, `description`,
  `evidence_type`, `source_module`, `source_type`, `source_ref`, etc.
- `GET /evidences` — lista, filtrável por `requirement_code`, `status`,
  `source_module`.
- `GET /evidences/{evidence_id}` — detalhe, com campo `evidence_note`
  conservador.
- `PATCH /evidences/{evidence_id}` — atualização parcial. DELETE não
  implementado.

### Vínculos com achados externos (RequirementFindingLink)

Sob `/api/v1/compliance`:

- `POST /requirement-links` — cria vínculo requisito ↔ achado. Payload
  identifica o requisito por `requirement_code`; se não existir, retorna 404.
  Duplicata `(requirement_code, source_module, source_type, source_ref)` retorna 400.
- `GET /requirement-links` — lista, filtrável por `requirement_code`,
  `source_module`, `source_type`, `source_ref`, `risk_level`.
- `GET /requirement-links/{link_id}` — detalhe, com campo `link_note`
  conservador.
- `PATCH /requirement-links/{link_id}` — atualiza `title`, `link_reason`,
  `risk_level`, `notes`, `source_ref`, `source_module`, `source_type`.
  Não permite trocar o `requirement_id`. Campos NOT NULL não aceitam null
  explícito. DELETE não implementado.

## Fronteiras com audit, lgpd e retention

- `audit` cuida de achados técnicos/documentais.
- `retention` cuida de temporalidade documental.
- `lgpd` cuida do plano de ações (AC-01..25) e proteção de dados.
- `compliance` cuida apenas do **mapeamento normativo consultivo** da
  Matriz INOVA V1.

Esta sprint não cria pontes entre os módulos. Integrações ficam para
sprints futuras (LGPD/Compliance-2 e seguintes).

## Linguagem conservadora

A documentação, schemas e testes utilizam linguagem deliberadamente
conservadora:

- "requisito mapeado" (não "cumprido")
- "política indicada pela INOVA" (não "implementada")
- "evidência sugerida" (não "evidência coletada")
- "prazo estimado por classe" (não "prazo cumprido")
- "apoia a organização da conformidade" (não "garante conformidade")

`RequirementDetail.source_note` retorna explicitamente:

> "Requisito mapeado a partir da Matriz INOVA V1; não representa
> declaração automática de conformidade."

## Limitações

- Datas absolutas (ex.: 23/05/2026) são informativas. O `summary` expõe
  `c3_initial_deadline_days = 90` como referência operacional e
  `c3_initial_deadline_reference_date` apenas como dado informativo a
  validar antes de uso oficial.
- A redação de artigos foi extraída do PDF da matriz; redação oficial do
  Provimento deve ser consultada para uso jurídico.
- Não há autenticação por papéis nesta sprint — endpoints públicos.

## Blueprint de integração regulatória

A Sprint Blueprint (2026-05-06) definiu as fronteiras, contratos futuros e
roadmap de integração entre `audit`, `retention`, `lgpd` e `compliance`.

Documentos produzidos:

- [CNJ_213_REGULATORY_INTEGRATION_BLUEPRINT.md](../CNJ_213_REGULATORY_INTEGRATION_BLUEPRINT.md)
  — fronteiras, fluxos conceituais, modelos futuros, roadmap
- [ADR-001 — ComplianceEvidence como entidade central](../decisions/ADR-001-compliance-evidence-ownership.md)
  — `ComplianceEvidence` pertence ao módulo `compliance`; outros módulos são
  referenciados por referência fraca
- [ADR-002 — Referências fracas entre módulos](../decisions/ADR-002-weak-references-between-regulatory-modules.md)
  — integração inicial por `source_module` + `source_type` + `source_ref`,
  sem FK direta entre módulos

### Decisões propostas (aguardam aprovação)

1. `ComplianceEvidence` é a entidade central de evidência regulatória real,
   pertencente ao módulo `compliance`.
2. A integração com `audit`, `lgpd` e `retention` ocorre por **referência fraca**
   textual, não por foreign key direta.
3. `ComplianceAction` só será criada após análise de casos reais que não possam
   ser cobertos por `LgpdAction` + `RequirementFindingLink`.
4. Status indicativo nunca usa termos como "CONFORME" ou "APROVADO" automaticamente;
   `status_note` conservadora é obrigatória em todo output.

## Roadmap futuro

- ~~**LGPD/Compliance-2**: evidências reais (`ComplianceEvidence`).~~ ✅ Concluída (commit `4ccf50c`).
- ~~**Sprint RequirementFindingLink**: vínculo entre requisito e achado/sinal.~~ ✅ Concluída (commit `c588bc2`).
- **Sprint Compliance-4 — ComplianceStatus**: cálculo de status indicativo por
  requisito. Baseado em `ComplianceEvidence` + `RequirementFindingLink`.
  Linguagem conservadora obrigatória; nenhum status automático declarará
  conformidade.
- **Retention-1C revisada**: persistência de `RetentionEvaluation`; alinhar
  fontes normativas e enums com a fronteira de compliance.
- **LGPD-2**: hash/_VISTORIA, políticas versionadas, treinamentos,
  evidências operacionais.
- **Dossiê técnico**: agregar `ComplianceEvidence` + achados (`audit`) + ações
  (`lgpd`) + sinais (`retention`) em um pacote por etapa para Sistema Justiça Aberta.
  Primeiro formato: JSON + Markdown. PDF em sprint posterior.
