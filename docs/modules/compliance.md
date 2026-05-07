# Módulo Compliance

## Objetivo

Representar, de forma estruturada, versionada e somente leitura, a Matriz de
Correlação INOVA V1 do Provimento CNJ nº 213/2026. O módulo apoia a
organização da conformidade da serventia, mas **não declara conformidade**,
não armazena evidências reais e não substitui validação humana, jurídica
ou administrativa.

## Escopo da Sprint LGPD/Compliance-1

- Camada fundacional `app/modules/compliance/`.
- Modelo de dados para requisitos, políticas indicadas, prazos por classe e
  evidências sugeridas pela matriz.
- Seed determinístico e idempotente da Matriz INOVA V1 (`matriz_v1`).
- Endpoints REST somente leitura.
- Fronteira estrita: nenhum import de `audit`, `lgpd` ou `retention`.

## O que o módulo faz

- Persiste o mapa: requisito normativo → política indicada → prazo estimado
  por classe (C1/C2/C3) → evidência sugerida → etapa.
- Fornece consultas para listar/filtrar requisitos e políticas.
- Calcula resumos por etapa e visão geral consolidada.
- Registra metadados de seed (`compliance_seed_meta`) com versão e checksum
  SHA-256 para detecção de mudanças.

## O que o módulo não faz

- Não declara que a serventia cumpre o Provimento.
- Não persiste evidências reais — `ComplianceEvidenceTemplate` representa
  apenas a evidência sugerida pela matriz.
- Não há ações corretivas, dossiê técnico, geração de PDF, dashboard,
  upload, workflow de descarte, status de cumprimento ou cálculo de
  conformidade.
- Não importa nem consome `app.modules.audit`, `app.modules.lgpd` ou
  `app.modules.retention`.
- Não expõe métodos de escrita via HTTP (`POST/PATCH/PUT/DELETE`).

## Relação com a Matriz INOVA V1

Origem: `Matriz_Correlacao_Provimento213_Politicas V1.pdf` (InovaLGPD,
Março 2026, v1.0).

O PDF **não é versionado no repositório** — apenas a referência textual
ao caminho local é registrada em `compliance_seed_meta.source_file_reference`:

```
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

## Tabelas

- `compliance_requirements`
- `compliance_policies`
- `compliance_requirement_policies`
- `compliance_requirement_deadlines`
- `compliance_evidence_templates`
- `compliance_seed_meta`

Todas criadas pela migration `c1d2e3f4b5a6 — add compliance tables`.

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
   pertencendo ao módulo `compliance`.
2. A integração com `audit`, `lgpd` e `retention` ocorre por **referência fraca**
   textual, não por foreign key direta.
3. `ComplianceAction` só será criada após análise de casos reais que não possam
   ser cobertos por `LgpdAction` + `RequirementFindingLink`.
4. Status indicativo nunca usa termos como "CONFORME" ou "APROVADO" automaticamente;
   `status_note` conservadora é obrigatória em todo output.

## Roadmap futuro

- **LGPD/Compliance-2**: evidências reais (`ComplianceEvidence`),
  vinculadas a requisitos por referência fraca; primeiros relatórios de cobertura.
- **Sprint RequirementFindingLink**: vínculo entre requisito e achado/sinal.
- **Sprint ComplianceStatus**: cálculo de status indicativo por requisito.
- **Retention-1C revisada**: persistência de `RetentionEvaluation`; alinhar
  fontes normativas e enums com a fronteira de compliance.
- **LGPD-2**: hash/_VISTORIA, políticas versionadas, treinamentos,
  evidências operacionais.
- **Dossiê técnico**: agregar `ComplianceEvidence` + achados (`audit`) + ações
  (`lgpd`) + sinais (`retention`) em um pacote por etapa para Sistema Justiça Aberta.
  Primeiro formato: JSON + Markdown. PDF em sprint posterior.
