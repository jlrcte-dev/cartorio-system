# Knowledge Base Blueprint — Cartório System

> Documento conceitual produzido na Sprint **KNOWLEDGE-BASE-0**.
> **Nenhum código foi implementado.** Esta é a base documental e arquitetural
> mínima para permitir a implementação futura segura do módulo `knowledge_base`.
>
> Toda decisão técnica abaixo está subordinada às proibições permanentes do
> [`CLAUDE.md`](../../CLAUDE.md) e à hierarquia de fontes lá definida.

## Documentos relacionados

- [ADR-004 — Separação entre Knowledge Base e AI Gateway](../decisions/ADR-004-separacao-knowledge-base-ai-gateway.md) (status: **Proposto**)
- [ADR-005 — Knowledge Base antes de IA externa](../decisions/ADR-005-knowledge-base-antes-de-ia-externa.md) (status: **Proposto**)
- [ADR-006 — Dados permitidos e proibidos para IA](../decisions/ADR-006-dados-permitidos-e-proibidos-para-ia.md) (status: **Proposto**)
- [ADR-007 — MCP e agentes autônomos fora das fases iniciais](../decisions/ADR-007-mcp-e-agentes-fora-das-fases-iniciais.md) (status: **Proposto**)
- [ADR-008 — Toda saída de IA é rascunho sujeito à revisão humana](../decisions/ADR-008-saida-de-ia-e-rascunho-sujeito-a-revisao.md) (status: **Proposto**)
- [Investigação AI-LEGAL-0](../ai/AI_LEGAL_TOOLS_INVESTIGATION.md)
- [PHASE_1_SOURCE_ALLOWLIST.md](PHASE_1_SOURCE_ALLOWLIST.md) — lista explícita de fontes da Fase 1
- [GOVERNANCE_DECISIONS.md](GOVERNANCE_DECISIONS.md) — decisões humanas pendentes (DHP-01..10)
- [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)

> **Atenção.** As ADRs 004–008 estão em status **Proposto** — ainda não
> equivalem a aprovação formal. As regras deste blueprint são aplicadas
> como **premissas operacionais** até que [`GOVERNANCE_DECISIONS.md`](GOVERNANCE_DECISIONS.md)
> registre decisão diferente.

---

## 1. Objetivo

A `knowledge_base` será a base documental estruturada do Cartório System para
organizar **normas oficiais, referências legais públicas, documentação técnica
interna e materiais auxiliares de consultoria**, com **metadados, versões,
chunks e citações rastreáveis**.

Sua função é preparar o terreno para inteligência normativa futura — sempre
**informativa, auxiliar e sujeita a revisão humana** — mantendo a separação
rígida em relação ao `ai_gateway` (ADR-004) e a precedência sobre qualquer
chamada externa de IA (ADR-005).

A Fase 1 da knowledge_base é **documental, local e sem IA externa**. Não há
embeddings, RAG, MCP, agentes nem API externa neste momento.

---

## 2. Escopo

A knowledge_base pode receber, em fase apropriada:

- **fontes normativas oficiais**: Provimento CNJ 213/2026, Provimento CNJ 50/2015
  e seu compilado, Código de Normas e Procedimentos do Foro Extrajudicial de
  Goiás (CNPFE-GO), demais normas públicas aplicáveis;
- **referências legais públicas**: leis, decretos, resoluções, súmulas e atos
  normativos federais/estaduais com texto público;
- **documentação técnica interna sem dados sensíveis**: ADRs, blueprints de
  arquitetura, roadmaps, documentação de módulos, decisões registradas;
- **documentação de compliance, LGPD, retenção e auditoria** sem dados pessoais
  reais — apenas textos normativos, políticas, procedimentos e modelos;
- **materiais auxiliares de consultoria**, quando corretamente classificados
  (ex.: Matriz de Correlação Provimento 213 × Políticas InovaLGPD; Guia de Uso
  das Políticas InovaLGPD).

Esses materiais entram com **classificação explícita** e jamais como norma
oficial (ver Seção 6).

---

## 3. Fora do Escopo

Não entram na knowledge_base nesta fase, e não podem ser implementados nesta
sprint:

- dados operacionais reais da serventia;
- matrículas reais, atos concretos, certidões emitidas;
- documentos de clientes ou de partes;
- nomes de partes, CPF, RG, endereços, telefones, e-mails reais;
- valores financeiros reais de atos, emolumentos ou movimentações;
- logs de produção contendo dados pessoais;
- backups operacionais;
- planilhas financeiras reais (incluindo séries históricas);
- banco de dados, schemas, migrations;
- IA externa (Anthropic, OpenAI, Google, qualquer provedor);
- embeddings, vector store, índice semântico;
- RAG, recuperação aumentada por geração;
- agentes autônomos;
- MCP Server, MCP Connectors ou conectores externos;
- respostas automáticas com efeito jurídico, regulatório ou cartorário.

A proibição abrange tanto o conteúdo da base quanto qualquer pipeline ou
ingestão automatizada. **Nada disso deve ser implementado nesta sprint.**

---

## 4. Princípios Arquiteturais

A knowledge_base será construída sobre os seguintes princípios, todos
derivados das ADRs 004–008 e da governança do projeto:

1. **Conhecimento estruturado antes de IA.** A base existe e tem valor próprio
   sem qualquer modelo externo (ADR-005).
2. **Citação antes de resposta.** Nenhum conteúdo passível de uso futuro pela
   IA é admitido sem citação canônica rastreável (ADR-008).
3. **Revisão humana obrigatória** em toda saída futura, sem exceção.
4. **Separação entre norma oficial e interpretação.** Matrizes, guias e
   materiais de consultoria nunca são tratados como norma.
5. **Local-first.** O índice e o conteúdo permanecem locais por padrão; envio
   externo requer autorização explícita por categoria (ADR-006).
6. **Confidencialidade por padrão.** Em dúvida, classifica-se como mais
   restritivo, não menos.
7. **Rastreabilidade.** Toda fonte, versão, chunk e citação deve ser
   reproduzível e auditável.
8. **Baixo acoplamento.** A knowledge_base não importa nem é importada por
   `audit`, `lgpd`, `retention`, `compliance`, `finance`, `registro_imoveis`
   ou `notas`. Comunicação futura ocorre por interfaces explícitas.
9. **Compatibilidade futura com `ai_gateway`.** Os metadados são desenhados
   para que o `ai_gateway` possa filtrar fontes admissíveis sem reinterpretar
   regras de uso (ADR-004, ADR-006).
10. **Independência do Atlas.** A knowledge_base vive no domínio do Cartório
    System e não compartilha banco, código ou ciclo com o Atlas.

---

## 5. Relação entre knowledge_base e ai_gateway

| Camada | Papel | Existe nesta fase? |
|---|---|---|
| `knowledge_base` | Fonte organizada, citável, classificada e versionada | Apenas **documentalmente** — sem código |
| `ai_gateway` | Consumidor futuro de chunks da base, com redaction, logs e disclaimers | **Não existe** — adiado para fase posterior (ADR-004, ADR-005) |

Regras fundamentais:

- `ai_gateway` **não pode operar** sem fonte citável e classificada na
  knowledge_base (ADR-005).
- Toda resposta futura do `ai_gateway` deve **carregar citações específicas**
  (artigo, anexo, item, seção). Resposta genérica é proibida (ADR-008).
- O `ai_gateway` deve **bloquear** automaticamente fontes com
  `external_api_allowed=false` (ADR-006).
- O sistema **não decide** automaticamente sobre questões jurídicas,
  cartorárias, regulatórias ou operacionais (ADR-008).
- Aplica-se sempre o disclaimer estrutural exigido pela ADR-008 a qualquer
  output que venha a usar a base.

---

## 6. Classificação de Fontes

Toda fonte indexada (ou candidata a indexação futura) deve receber uma
categoria explícita. A categoria determina o que pode entrar na Fase 1, o
nível de risco e o tratamento futuro.

| Categoria | Descrição | Entra Fase 1? | `local_index_allowed` | `external_api_allowed` | `pii_risk_level` | `requires_human_approval` |
|---|---|---|---|---|---|---|
| **PUBLIC_NORMATIVE** | Norma oficial pública | Sim | true | true (futuro, com cautela) | NONE | Recomendada (curadoria) |
| **PUBLIC_LEGAL_REFERENCE** | Lei, decreto, súmula, ato normativo público | Sim | true | true (futuro, com cautela) | NONE/LOW | Recomendada |
| **INTERNAL_TECHNICAL_DOC** | ADRs, blueprints, docs internos sem PII | Sim, se sem dado sensível | true | **false** por padrão | NONE/LOW | **Obrigatória** |
| **INTERNAL_CONFIDENTIAL_DOC** | Relatório interno confidencial, diagnóstico | **Não**, salvo decisão expressa futura | false por padrão | **false sempre** | NONE/HIGH (variável) | Obrigatória |
| **THIRD_PARTY_CONSULTING_DOC** | Matriz/Guia InovaLGPD; consultorias | Sim, como auxiliar | true | **false** | LOW/MEDIUM | Obrigatória |
| **OPERATIONAL_METADATA** | Nomes de arquivo, caminhos, achados sem PII | **Não** na Fase 1, salvo anonimização futura | false por padrão | false por padrão | LOW/MEDIUM | Obrigatória |
| **SENSITIVE_OPERATIONAL_DATA** | Matrículas, partes, CPF, RG, valores, atos | **Proibido** em todas as fases iniciais | false | false | PROHIBITED | Obrigatória (e proibido) |

### Detalhamento por categoria

#### PUBLIC_NORMATIVE
- **Exemplos:** Provimento CNJ 213/2026; Provimento CNJ 50/2015; Provimento
  50/2015 compilado; CNPFE-GO; Resoluções CNJ aplicáveis.
- **Entra na Fase 1:** sim.
- **Local index:** permitido.
- **API externa (uso futuro):** permitido com cautela — manter cópia local
  como fonte primária.
- **PII risk:** NONE.
- **Aprovação humana:** recomendada para curadoria editorial (versionamento e
  decisão sobre compilados vs. originais).

#### PUBLIC_LEGAL_REFERENCE
- **Exemplos:** Lei 8.935/1994; Lei 6.015/1973; Lei 13.709/2018 (LGPD);
  Lei 10.169/2000; demais leis federais/estaduais públicas aplicáveis;
  súmulas, instruções normativas.
- **Entra na Fase 1:** sim.
- **Local index:** permitido.
- **API externa (uso futuro):** permitido com cautela quando o texto for
  publicamente disponível.
- **PII risk:** NONE ou LOW.
- **Aprovação humana:** recomendada para curadoria.

#### INTERNAL_TECHNICAL_DOC
- **Exemplos:** ADRs do projeto; blueprint regulatório; documentação de
  módulos (`docs/modules/*.md`); roadmaps técnicos sem dados.
- **Entra na Fase 1:** apenas se **sem dado pessoal real**, sem credenciais e
  sem informação confidencial proibida.
- **Local index:** permitido.
- **API externa:** **false** por padrão. Pode revelar estratégia interna,
  arquitetura sensível ou postura regulatória (ver ADR-006).
- **PII risk:** NONE ou LOW.
- **Aprovação humana:** obrigatória antes de indexar.

#### INTERNAL_CONFIDENTIAL_DOC
- **Exemplos:** diagnósticos internos, relatórios técnicos confidenciais,
  documentos InovaLGPD com restrição contratual, planos de contingência
  detalhados.
- **Entra na Fase 1:** **não**, salvo decisão expressa futura registrada em
  ADR específica.
- **Local index:** false por padrão.
- **API externa:** **false sempre**.
- **PII risk:** variável (NONE a HIGH).
- **Aprovação humana:** obrigatória.

#### THIRD_PARTY_CONSULTING_DOC
- **Exemplos:** Matriz de Correlação Provimento 213 × Políticas InovaLGPD;
  Guia de Uso das Políticas InovaLGPD; demais materiais de consultoria.
- **Entra na Fase 1:** sim, **como material auxiliar**.
- **Local index:** permitido.
- **API externa:** **false** — material de terceiros, sem clareza sobre
  termos de uso para retransmissão.
- **PII risk:** LOW/MEDIUM (depende do conteúdo).
- **Aprovação humana:** obrigatória.
- **Regra absoluta:** **nunca tratar como norma oficial.** Citações desses
  materiais devem ser claramente identificadas como interpretação ou
  correlação, não como prescrição normativa.

#### OPERATIONAL_METADATA
- **Exemplos:** nomes/caminhos de arquivos do scanner, códigos de achados
  sem detalhe, identificadores opacos.
- **Entra na Fase 1:** **não**, salvo metadado claramente não sensível e
  anonimizado em fase futura, com ADR específica.
- **Local index:** false por padrão.
- **API externa:** false por padrão.
- **PII risk:** LOW/MEDIUM.

#### SENSITIVE_OPERATIONAL_DATA
- **Exemplos:** matrículas reais, dados de partes, CPF, RG, endereços,
  telefones, valores monetários reais, atos concretos, conteúdo de certidões.
- **Entra em qualquer fase inicial:** **proibido**.
- **Local index:** false.
- **API externa:** false.
- **PII risk:** PROHIBITED.
- **Uso futuro:** requer base legal LGPD explícita, anonimização, contrato
  Enterprise/ZDR e decisão formal do delegatário (ADR-006).

---

## 7. Fontes Permitidas na Fase 1

> **A lista explícita e revisável de fontes da Fase 1** está em
> [`PHASE_1_SOURCE_ALLOWLIST.md`](PHASE_1_SOURCE_ALLOWLIST.md). Esta seção
> apresenta apenas os candidatos a entrar na allowlist; nenhum item abaixo
> está em `APPROVED_FOR_PHASE_1` por padrão — todos exigem revisão e
> decisão humana conforme [`GOVERNANCE_DECISIONS.md`](GOVERNANCE_DECISIONS.md)
> (DHP-06, DHP-07, DHP-08, DHP-09).

A Fase 1 (knowledge_base sem IA externa) admite, sujeitas a curadoria e
aprovação humana caso a caso:

- **Provimento CNJ nº 213/2026** (texto público).
- **Provimento CNJ nº 50/2015** (texto público).
- **Provimento CNJ nº 50/2015 compilado** — versão consolidada, marcada
  como compilação, com referência cruzada ao original.
- **CNPFE-GO** — Código de Normas e Procedimentos do Foro Extrajudicial de
  Goiás. Pode ser indexado por capítulos relevantes para evitar volume
  desnecessário na Fase 1.
- **ADRs 004 a 008** (e demais ADRs do projeto, conforme curadoria).
- **Documentação interna técnica** (`docs/`) sem dados pessoais reais.
- **Documentação de compliance, retenção, LGPD e auditoria** do próprio
  projeto, sem dados pessoais reais.

A **Matriz de Correlação Provimento 213 × Políticas InovaLGPD** e o **Guia de
Uso das Políticas InovaLGPD** entram **apenas** como
`THIRD_PARTY_CONSULTING_DOC`, isto é, material auxiliar de correlação e
execução. Nunca como norma oficial.

---

## 8. Fontes Proibidas na Fase 1

Listagem explícita do que **não** pode entrar na knowledge_base na Fase 1
(reiterando ADR-006 e Seção 3):

- matrículas reais;
- documentos de clientes ou de partes;
- nomes de partes, CPF, RG, endereços, telefones, e-mails reais;
- valores monetários reais de atos, emolumentos ou movimentações;
- atos concretos praticados pela serventia;
- logs de produção contendo dados pessoais;
- backups operacionais;
- planilhas financeiras reais;
- documentos operacionais sensíveis;
- relatórios internos confidenciais **como fonte normativa**;
- qualquer conteúdo sensível destinado a API externa.

---

## 9. Política de Confidencialidade e LGPD

### Níveis de confidencialidade

| Nível | Descrição |
|---|---|
| **PUBLIC** | Conteúdo publicamente disponível (normas, leis, atos públicos) |
| **INTERNAL** | Conteúdo interno sem informação sensível, mas não publicado externamente |
| **CONFIDENTIAL** | Conteúdo interno com sensibilidade estratégica, contratual ou regulatória |
| **RESTRICTED** | Conteúdo de acesso restrito a poucos responsáveis designados |

### Níveis de risco PII

| Nível | Descrição |
|---|---|
| **NONE** | Sem qualquer dado pessoal |
| **LOW** | Dados não identificáveis ou amplamente públicos (ex.: nome de autoridade pública em texto normativo) |
| **MEDIUM** | Dados parcialmente identificáveis; risco de reidentificação |
| **HIGH** | Dados pessoais identificáveis; PII real |
| **PROHIBITED** | Dados sensíveis vedados por LGPD ou política interna |

### Regras

- Qualquer fonte com `pii_risk_level` **HIGH** ou **PROHIBITED** fica
  **proibida na Fase 1**, sem exceção.
- Qualquer fonte **CONFIDENTIAL** ou **RESTRICTED** exige aprovação humana
  formal e **não pode ir para API externa** em nenhuma fase inicial.
- Quando há dúvida entre dois níveis, escolher o mais restritivo.
- Toda reclassificação deve ser registrada em ADR específica, com
  justificativa.

---

## 10. Política Local versus API Externa

Toda fonte indexada deve responder, no mínimo, às perguntas abaixo:

1. **Pode indexar localmente?** (`local_index_allowed`)
2. **Pode ser enviada a API externa futuramente?** (`external_api_allowed`)
3. **Exige anonimização** prévia?
4. **Exige aprovação humana** antes de indexar e/ou antes de enviar?
5. **Exige revisão jurídica ou de LGPD** antes de qualquer uso?

### Regra-base resumida

| Categoria | Local | API externa | Anonimização | Aprovação humana |
|---|---|---|---|---|
| PUBLIC_NORMATIVE | Sim | Candidata futura | Não | Recomendada |
| PUBLIC_LEGAL_REFERENCE | Sim | Candidata futura | Não | Recomendada |
| INTERNAL_TECHNICAL_DOC | Sim | **Não** | Não, mas revisar conteúdo | **Obrigatória** |
| INTERNAL_CONFIDENTIAL_DOC | Restrito | **Nunca** | N/A | Obrigatória |
| THIRD_PARTY_CONSULTING_DOC | Sim | **Não** | N/A | Obrigatória |
| OPERATIONAL_METADATA | Restrito | **Não** por padrão | Sim, sempre | Obrigatória |
| SENSITIVE_OPERATIONAL_DATA | **Proibido** | **Proibido** | — | — |

> Regra de ouro: **na dúvida, não envia.** O default de `external_api_allowed`
> é `false`. Permitir saída externa exige decisão explícita e registrada.

---

## 11. Metadados Mínimos de Documento

Todo documento indexado terá, no mínimo, os campos abaixo. Os tipos são
indicativos; a sprint atual **não** os implementa em código.

| Campo | Tipo | Descrição |
|---|---|---|
| `document_id` | string estável | Identificador canônico do documento (não muda entre versões) |
| `title` | string | Título oficial ou descritivo |
| `source_type` | enum | Uma das categorias da Seção 6 |
| `source_origin` | string | Origem (CNJ, TJGO, InovaLGPD, projeto interno, etc.) |
| `jurisdiction` | string | Federal, GO, municipal, interno |
| `authority` | string | Órgão emissor (CNJ, TJGO, Congresso, etc.) |
| `publication_date` | date | Data de publicação oficial |
| `effective_date` | date \| null | Data de vigência (se distinta) |
| `version_label` | string | Rótulo de versão (ex.: `original`, `compilado_2025-08`, `v1.0`) |
| `is_current` | bool | É a versão vigente conforme curadoria local? |
| `is_revoked` | bool | Foi revogado? |
| `revoked_by` | document_id \| null | Documento que revogou este |
| `replaces` | list[document_id] | Documentos substituídos por este |
| `replaced_by` | document_id \| null | Próxima versão deste documento |
| `confidentiality_level` | enum | PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED |
| `pii_risk_level` | enum | NONE / LOW / MEDIUM / HIGH / PROHIBITED |
| `external_api_allowed` | bool | Pode ser enviado a API externa futuramente? |
| `local_index_allowed` | bool | Pode ser indexado localmente? |
| `requires_human_approval` | bool | Exige aprovação humana antes de uso |
| `source_path` | string \| null | Caminho local do arquivo (nunca dentro de `_local_data` quando contiver dado real) |
| `source_url` | string \| null | URL pública de referência |
| `checksum` | string (sha256) | Hash do conteúdo da versão indexada |
| `created_at` | datetime | Quando foi adicionado à base |
| `updated_at` | datetime | Última alteração dos metadados |
| `notes` | string \| null | Anotações livres de curadoria |

### Exemplos conceituais (fictícios)

> Os exemplos a seguir são **conceituais**. Não há ingestão real nesta sprint
> e nenhum exemplo corresponde a um registro persistido.

**Exemplo A — Provimento CNJ 213/2026 (norma oficial)**

```yaml
document_id: cnj-prov-213-2026
title: "Provimento CNJ nº 213/2026"
source_type: PUBLIC_NORMATIVE
source_origin: CNJ
jurisdiction: Federal
authority: Conselho Nacional de Justiça
publication_date: 2026-01-20
effective_date: 2026-03-01
version_label: original
is_current: true
is_revoked: false
revoked_by: null
replaces: []
replaced_by: null
confidentiality_level: PUBLIC
pii_risk_level: NONE
external_api_allowed: true
local_index_allowed: true
requires_human_approval: false
source_url: "https://www.cnj.jus.br/..."
checksum: "sha256:..."
```

**Exemplo B — Matriz InovaLGPD (consultoria)**

```yaml
document_id: inovalgpd-matriz-prov213-v1
title: "Matriz de Correlação Provimento 213 × Políticas InovaLGPD — v1.0"
source_type: THIRD_PARTY_CONSULTING_DOC
source_origin: InovaLGPD
jurisdiction: N/A
authority: InovaLGPD (consultoria)
publication_date: 2026-03-01
version_label: V1.0_MAR2026
is_current: true
confidentiality_level: INTERNAL
pii_risk_level: LOW
external_api_allowed: false
local_index_allowed: true
requires_human_approval: true
notes: "Material auxiliar de correlação. Não é norma oficial."
```

**Exemplo C — ADR-006 (documentação interna)**

```yaml
document_id: cartorio-adr-006
title: "ADR-006 — Política Inicial de Dados para Uso em IA"
source_type: INTERNAL_TECHNICAL_DOC
source_origin: Cartório System
jurisdiction: Interno
authority: Projeto Cartório System
publication_date: 2026-05-17
version_label: Proposto
is_current: true
confidentiality_level: INTERNAL
pii_risk_level: NONE
external_api_allowed: false
local_index_allowed: true
requires_human_approval: true
```

---

## 12. Metadados Mínimos de Chunk

Cada documento é dividido em chunks citáveis. Cada chunk carrega:

| Campo | Tipo | Descrição |
|---|---|---|
| `chunk_id` | string estável | Identificador único do chunk dentro do documento |
| `document_id` | string | Documento de origem |
| `chunk_type` | enum | `ARTICLE`, `PARAGRAPH`, `ITEM`, `ANNEX_ITEM`, `TABLE_ROW`, `SECTION`, `SLIDE`, `MAPPING_ROW`, `OTHER` |
| `canonical_citation` | string | Citação canônica autocontida (ver Seção 15) |
| `title` | string \| null | Título da seção/artigo, se houver |
| `article` | string \| null | Número do artigo |
| `paragraph` | string \| null | Parágrafo |
| `item` | string \| null | Inciso ou alínea |
| `annex` | string \| null | Anexo |
| `section` | string \| null | Seção ou capítulo |
| `table_id` | string \| null | Tabela de origem (Anexo Provimento 50, por ex.) |
| `row_id` | string \| null | Linha/código dentro da tabela |
| `page_start` | int \| null | Página inicial no PDF de origem |
| `page_end` | int \| null | Página final |
| `text_hash` | string (sha256) | Hash do texto do chunk |
| `is_normative` | bool | É texto de norma oficial? |
| `is_interpretative` | bool | É interpretação/comentário/correlação? |
| `is_evidence_mapping` | bool | Mapeia obrigação ↔ evidência sugerida? |
| `confidentiality_level` | enum | Herdado/sobrescrito do documento |
| `pii_risk_level` | enum | Herdado/sobrescrito do documento |
| `external_api_allowed` | bool | Herdado/sobrescrito do documento |
| `local_index_allowed` | bool | Herdado/sobrescrito do documento |
| `requires_human_approval` | bool | Herdado/sobrescrito do documento |

### Exemplos conceituais

**Chunk normativo — Provimento CNJ 213/2026, art. 10, §3º**

```yaml
chunk_id: cnj-prov-213-2026__art-10__par-3
document_id: cnj-prov-213-2026
chunk_type: PARAGRAPH
canonical_citation: "Provimento CNJ nº 213/2026, art. 10, §3º"
article: "10"
paragraph: "3"
is_normative: true
is_interpretative: false
is_evidence_mapping: false
confidentiality_level: PUBLIC
pii_risk_level: NONE
external_api_allowed: true
local_index_allowed: true
```

**Chunk de tabela — Provimento CNJ 50/2015, Anexo, item 3-2-1-4**

```yaml
chunk_id: cnj-prov-50-2015__anexo__3-2-1-4
document_id: cnj-prov-50-2015
chunk_type: TABLE_ROW
canonical_citation: "Provimento CNJ nº 50/2015, Anexo, item 3-2-1-4"
annex: "Anexo"
table_id: "Tabela de Temporalidade"
row_id: "3-2-1-4"
is_normative: true
external_api_allowed: true
```

**Chunk interpretativo — Matriz InovaLGPD**

```yaml
chunk_id: inovalgpd-matriz-prov213-v1__art-10__trilhas-auditoria
document_id: inovalgpd-matriz-prov213-v1
chunk_type: MAPPING_ROW
canonical_citation: 'Matriz InovaLGPD, seção "Art. 10 — Trilhas de Auditoria"'
section: "Art. 10 — Trilhas de Auditoria"
is_normative: false
is_interpretative: true
is_evidence_mapping: true
confidentiality_level: INTERNAL
external_api_allowed: false
requires_human_approval: true
```

---

## 13. Regras de Versionamento

- **`document_id` é estável** entre versões. Mudanças de versão **não** geram
  novo `document_id`.
- **`checksum` é obrigatório** para cada versão indexada.
- **`version_label` é obrigatório** e segue convenção curadora (ex.:
  `original`, `compilado_AAAA-MM`, `v1.0`).
- `is_current` marca a versão vigente conforme curadoria local.
- `is_revoked` distingue documentos revogados — mantidos para histórico,
  nunca apagados.
- `replaces` e `replaced_by` permitem reconstituir a cadeia de revisões.
- **Data de ingestão** (`created_at`) e **fonte original** (`source_url`,
  `source_path`) são obrigatórias.
- **Distinção explícita** entre:
  - **documento original** (`version_label: original`);
  - **compilado** (`version_label: compilado_*`) — versão consolidada com
    referência ao original;
  - **versão derivada** — extrato, recorte ou tradução.
- **Nunca sobrescrever** versão anterior sem rastreabilidade. Toda mudança
  cria nova versão; a anterior permanece com `is_current=false`.

---

## 14. Regras de Chunking por Tipo de Fonte

### Provimento CNJ 213/2026
- Chunk por **artigo**.
- **Subchunk** por **parágrafo, inciso, anexo, etapa ou item técnico** quando
  o conteúdo for autocontido para citação independente.
- **Preservar relação** entre o corpo principal e os anexos via `document_id`
  e referência explícita (`annex`, `section`).

### Provimento CNJ 50/2015 e seu compilado
- Chunk por **item da tabela de temporalidade**.
- **Preservar:** código (`row_id`), assunto, documento, prazo, destinação
  final e observações.
- Compilado é versão separada com `version_label: compilado_*` e referência
  ao original.

### CNPFE-GO
- Chunk por **livro, capítulo, seção, artigo e item**, conforme a hierarquia
  do código.
- Permitir indexação seletiva por capítulos relevantes na Fase 1.

### Matriz de Correlação InovaLGPD
- Chunk por **artigo mapeado** e por **documento correlato**.
- Marcar `is_interpretative=true` e/ou `is_evidence_mapping=true`.
- **Nunca marcar como norma oficial** (`is_normative=false`).
- Categoria de fonte: `THIRD_PARTY_CONSULTING_DOC`.

### Guia de Uso das Políticas InovaLGPD
- Chunk por **seção, slide ou tópico**.
- Marcar como material auxiliar de execução.
- Categoria: `THIRD_PARTY_CONSULTING_DOC`.

### Documentos internos
- Chunk por **seção**.
- Indexar **somente** se não houver dado pessoal real ou informação
  confidencial proibida.
- Categoria: `INTERNAL_TECHNICAL_DOC` (preferencial) ou
  `INTERNAL_CONFIDENTIAL_DOC` (com restrições).

---

## 15. Regras de Citação Rastreável

Toda saída futura da IA, e toda referência interna da knowledge_base, deve
usar citação canônica autocontida. Formatos aceitos (exemplos):

- `Provimento CNJ nº 213/2026, art. 10, §3º`
- `Provimento CNJ nº 213/2026, Anexo IV, Etapa 1, item 1.3`
- `Provimento CNJ nº 50/2015, Anexo, item 3-2-1-4`
- `CNPFE-GO, Livro X, Capítulo Y, art. Z`
- `Matriz InovaLGPD, seção "Art. 10 — Trilhas de Auditoria"`
- `Guia InovaLGPD, slide/seção "Etapa 1 — Governança"`
- `ADR-006, seção "Dados permitidos e proibidos"`

### Regra obrigatória

**Nunca aceitar resposta genérica** do tipo "conforme o Provimento", "segundo
a LGPD", "de acordo com a matriz". Toda citação deve incluir
**artigo/anexo/item/seção específica**, suficiente para reabrir a fonte e
verificar o trecho.

Citações que não respeitem esta regra devem ser tratadas como falha de
geração e bloqueadas pelo `ai_gateway` na fase futura (ADR-008).

---

## 16. Política de Revisão Humana

Resumo das regras já presentes na ADR-008, aplicadas à knowledge_base:

- Toda resposta futura de IA com base na knowledge_base é **rascunho
  informativo**, nunca decisão final.
- Toda **conclusão normativa** exige revisão humana antes de qualquer uso
  operacional.
- A IA **não substitui** titular, delegatário, escrevente, jurídico, DPO,
  consultoria ou profissional de TI.
- **Documentos interpretativos** (Matriz, Guia, consultoria) exigem atenção
  especial — nunca podem ser apresentados como norma.
- **Fontes conflitantes** (ex.: original vs. compilado; matriz vs.
  provimento) devem ser sinalizadas explicitamente na saída.
- A curadoria da base também é uma atividade humana: classificação,
  versionamento e aprovação prévia (ADR-006).

---

## 17. Uso Futuro pelo `ai_gateway`

Esta seção é **conceitual**. **Não implementar nada disto nesta sprint.**

O futuro `ai_gateway`, quando autorizado, deverá:

- consultar **apenas chunks já classificados** na knowledge_base;
- **bloquear** automaticamente fontes com `external_api_allowed=false`;
- **carregar a citação canônica** de cada chunk usado;
- aplicar **redaction** antes de qualquer chamada externa;
- registrar **logs** sem conteúdo sensível (campos de `AiCallLog` conforme
  ADR-004 / ADR-008);
- indicar **nível de confiança** e a **necessidade de revisão humana** no
  output;
- aplicar o **disclaimer estrutural** obrigatório (ADR-008);
- nunca decidir sobre conformidade, descarte, ato cartorário ou emissão de
  documento.

Qualquer divergência entre essas regras e a implementação proposta deve ser
tratada como bug do `ai_gateway`, não como exceção legítima.

---

## 18. Limitações Conhecidas

- Este blueprint **não valida conformidade jurídica**. Curadoria normativa
  exige revisão por profissional habilitado.
- O blueprint **não cria banco** nem persiste qualquer dado.
- **Não há ingestão real** nesta sprint — nem documentos, nem chunks, nem
  metadados foram persistidos.
- **Não há IA externa, embeddings, RAG, MCP ou agente** envolvido.
- O blueprint depende de **revisão futura das fontes oficiais** (texto exato
  do Provimento 213/2026, redação consolidada do Provimento 50/2015, etc.).
- Depende de **decisão futura** do delegatário e do gestor sobre quais
  documentos exatamente entram na base na Fase 1 (DHP-03 a DHP-07 da
  AI-LEGAL-0A).
- O blueprint **não substitui** as ADRs 004–008; é instrumento operacional
  delas.
- A categoria `INTERNAL_CONFIDENTIAL_DOC` permanece **fora da Fase 1** por
  default; a inclusão exige ADR específica.

---

## 19. Roadmap Incremental

> Detalhamento operacional em [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md).

| Fase | Escopo | Pré-requisitos |
|---|---|---|
| **KNOWLEDGE-BASE-0** (esta sprint) | Blueprint documental, sem código | ADRs 004–008 aprovadas conceitualmente |
| **KNOWLEDGE-BASE-1** | Modelo conceitual de dados e schemas documentais — **ainda sem migration** | KB-0 aceita |
| **KNOWLEDGE-BASE-2** | Implementação local mínima de registry de documentos, **sem IA** | KB-1 aceita; decisão sobre fontes iniciais (DHP-03 a DHP-07) |
| **KNOWLEDGE-BASE-3** | Implementação de chunks e citações canônicas | KB-2 operacional |
| **KNOWLEDGE-BASE-4** | Ingestão controlada de fontes públicas (Provimento 213, 50, CNPFE-GO) | KB-3 operacional; curadoria humana definida |
| **KNOWLEDGE-BASE-5** | Validações, checksums, versionamento, relatórios de curadoria | KB-4 operacional |
| **AI-GATEWAY-0** | Somente após base local estruturada e madura (ADR-005) | KB-5 operacional; aprovação humana formal |

**Nenhum prazo fixo** é estabelecido aqui. A passagem de fase depende de
maturidade, não de calendário.

---

## 20. Checklist de Validação Antes da Implementação

Checklist a ser revisado **antes de iniciar KNOWLEDGE-BASE-1 ou qualquer fase
posterior**:

- [ ] Fontes candidatas **classificadas** segundo a tabela da Seção 6.
- [ ] **Dados sensíveis excluídos** explicitamente das listas de ingestão.
- [ ] **Metadados de documento** definidos (Seção 11).
- [ ] **Metadados de chunk** definidos (Seção 12).
- [ ] **Citação canônica** definida para cada tipo de fonte (Seção 15).
- [ ] **Política local/API externa** definida e revisada (Seção 10, ADR-006).
- [ ] **ADRs 004–008** respeitadas integralmente.
- [ ] **Revisão humana** prevista nos pontos de curadoria, ingestão e uso.
- [ ] **Sem dependência do Atlas** — knowledge_base isolada.
- [ ] **Sem IA externa, embeddings, RAG, MCP, agentes** nesta fase.
- [ ] **Sem banco, migration, endpoint** sem decisão de fase explícita.
- [ ] **Sem dependências adicionadas** sem ADR específica.
- [ ] **Sem versionamento de arquivos sensíveis** (`_local_data`, PDFs com
      conteúdo confidencial, `.env`, banco local).

---

*Sprint KNOWLEDGE-BASE-0 — 2026-05-23.*
*Documento conceitual. Nenhum código implementado. Aguarda decisão humana
para iniciar KNOWLEDGE-BASE-1.*
