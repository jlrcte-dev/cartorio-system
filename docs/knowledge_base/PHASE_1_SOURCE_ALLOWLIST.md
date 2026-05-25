# Phase 1 Source Allowlist — Knowledge Base

> Documento da Sprint **KNOWLEDGE-BASE-0.1** (2026-05-25).
> Define a lista **explícita** de fontes autorizadas para a Fase 1 da
> futura `knowledge_base`. Nenhum código foi implementado. Nenhuma fonte
> foi efetivamente ingerida.
>
> Subordinado a:
> - [`KNOWLEDGE_BASE_BLUEPRINT.md`](KNOWLEDGE_BASE_BLUEPRINT.md)
> - [`GOVERNANCE_DECISIONS.md`](GOVERNANCE_DECISIONS.md)
> - [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md)
> - [`CLAUDE.md`](../../CLAUDE.md)
> - [ADRs 004–008](../decisions/)

---

## 1. Objetivo

Registrar uma lista **explícita, controlada e revisável** das fontes
autorizadas para a Fase 1 da `knowledge_base`. A allowlist é o único
caminho legítimo de entrada de fontes na base durante a Fase 1 — substitui
qualquer "categoria genérica" implícita do blueprint.

A existência desta lista atende aos pré-requisitos:

- DHP-06 ("aprovar lista explícita de fontes da Fase 1");
- ADR-006, Seção "Próximos passos", item 2 ("criar lista de documentos
  autorizados para a knowledge base — lista explícita, não categoria
  genérica");
- Recomendação da Sprint KNOWLEDGE-BASE-0.

Esta lista **não é aprovação operacional**. Toda fonte aqui marcada como
`APPROVED_FOR_PHASE_1` ainda exige confirmação humana formal pelo
delegatário/gestor (ver [`GOVERNANCE_DECISIONS.md`](GOVERNANCE_DECISIONS.md)).

---

## 2. Regra Geral

**Nenhuma fonte fora desta allowlist** deve ser ingerida, indexada,
chunkada ou preparada para uso futuro pela knowledge_base sem revisão
humana e atualização explícita deste documento.

Regras absolutas:

- Toda nova fonte exige passagem pelo checklist da Seção 7.
- Toda alteração de status nesta tabela exige justificativa registrada na
  coluna "observações" ou em ADR específica.
- Fontes em `BLOCKED` permanecem bloqueadas até decisão formal em
  contrário.
- Fontes em `CANDIDATE_REQUIRES_REVIEW` **não** podem ser indexadas até
  promoção a `APPROVED_FOR_PHASE_1`.
- Materiais de consultoria **nunca** são promovidos a "fonte normativa
  oficial", independentemente do status.

### Status permitidos

| Status | Significado |
|---|---|
| `APPROVED_FOR_PHASE_1` | Autorizada para ingestão futura na Fase 1, sujeita a curadoria humana antes de marcar versão como vigente |
| `CANDIDATE_REQUIRES_REVIEW` | Fonte sob avaliação; aguarda revisão humana, confirmação de versão oficial, decisão contratual ou aprovação de ADR |
| `BLOCKED` | Vedada na Fase 1 sem exceção; revisão exige ADR específica |
| `DEFERRED` | Fora da Fase 1 por escolha estratégica; pode retornar em fase posterior |

---

## 3. Fontes Normativas Públicas Autorizadas

| source_id | Título | Categoria | Autoridade | Jurisdição | Status | Uso permitido | `local_index_allowed` | `external_api_allowed` | `requires_human_approval` | Observações |
|---|---|---|---|---|---|---|---|---|---|---|
| `cnj-prov-213-2026` | Provimento CNJ nº 213/2026 | `PUBLIC_NORMATIVE` | CNJ | Federal | `CANDIDATE_REQUIRES_REVIEW` | Norma oficial citável | true | true (futuro, com cautela) | true (curadoria editorial) | Texto público; confirmar redação oficial vigente antes de promover a `APPROVED_FOR_PHASE_1` (DHP-06) |
| `cnj-prov-50-2015` | Provimento CNJ nº 50/2015 (original) | `PUBLIC_NORMATIVE` | CNJ | Federal | `CANDIDATE_REQUIRES_REVIEW` | Norma oficial citável | true | true (futuro, com cautela) | true | Texto público; confirmar redação original como referência primária |
| `cnj-prov-50-2015-compilado` | Provimento CNJ nº 50/2015 — compilado | `PUBLIC_NORMATIVE` | CNJ | Federal | `CANDIDATE_REQUIRES_REVIEW` | Versão consolidada (rotular como compilado) | true | true (futuro, com cautela) | true | Marcar `version_label: compilado_*`; manter referência ao original; confirmar data e fonte da compilação |
| `cnpfe-go` | Código de Normas e Procedimentos do Foro Extrajudicial de Goiás (CNPFE-GO) | `PUBLIC_NORMATIVE` | TJGO / Corregedoria-Geral da Justiça de GO | Estadual (GO) | `CANDIDATE_REQUIRES_REVIEW` | Norma oficial citável, **somente capítulos selecionados** | true | true (futuro, com cautela) | true | Capítulos iniciais a definir (DHP-07); evitar ingestão integral antes da decisão |

> **Importante.** Nenhuma linha desta tabela está atualmente em
> `APPROVED_FOR_PHASE_1`. A promoção depende de: (i) confirmação da
> versão oficial vigente; (ii) decisão de capítulos no caso do CNPFE-GO;
> (iii) aprovação das ADRs 004–008 ou aceitação formal delas como
> premissas operacionais.

---

## 4. Documentação Interna Técnica Autorizável

Documentos internos só podem entrar se **não contiverem dados pessoais
reais** nem informação confidencial proibida. Categoria padrão:
`INTERNAL_TECHNICAL_DOC`, com `external_api_allowed=false`.

| source_id | Caminho | Categoria | Status | `local_index_allowed` | `external_api_allowed` | `requires_human_approval` | Observações |
|---|---|---|---|---|---|---|---|
| `cartorio-adr-004` | [`docs/decisions/ADR-004-separacao-knowledge-base-ai-gateway.md`](../decisions/ADR-004-separacao-knowledge-base-ai-gateway.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Status da ADR: **Proposto**. Promover apenas após decisão sobre o ADR |
| `cartorio-adr-005` | [`docs/decisions/ADR-005-knowledge-base-antes-de-ia-externa.md`](../decisions/ADR-005-knowledge-base-antes-de-ia-externa.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Status da ADR: **Proposto** |
| `cartorio-adr-006` | [`docs/decisions/ADR-006-dados-permitidos-e-proibidos-para-ia.md`](../decisions/ADR-006-dados-permitidos-e-proibidos-para-ia.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Status da ADR: **Proposto** |
| `cartorio-adr-007` | [`docs/decisions/ADR-007-mcp-e-agentes-fora-das-fases-iniciais.md`](../decisions/ADR-007-mcp-e-agentes-fora-das-fases-iniciais.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Status da ADR: **Proposto** |
| `cartorio-adr-008` | [`docs/decisions/ADR-008-saida-de-ia-e-rascunho-sujeito-a-revisao.md`](../decisions/ADR-008-saida-de-ia-e-rascunho-sujeito-a-revisao.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Status da ADR: **Proposto** |
| `cartorio-mod-compliance` | [`docs/modules/compliance.md`](../modules/compliance.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Verificar ausência de dado sensível antes de promover |
| `cartorio-mod-retention` | [`docs/modules/retention.md`](../modules/retention.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Verificar ausência de dado sensível |
| `cartorio-mod-lgpd` | [`docs/modules/lgpd.md`](../modules/lgpd.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Verificar ausência de dado pessoal real (AC-01..25 podem citar exemplos — confirmar fictícios) |
| `cartorio-mod-audit-file-scanner` | [`docs/modules/audit_file_scanner.md`](../modules/audit_file_scanner.md) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Verificar ausência de caminhos reais e dados de produção |
| `cartorio-reg-cnj-213` | [`docs/regulatory/cnj_213/`](../regulatory/cnj_213/) | `INTERNAL_TECHNICAL_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | false | true | Conjunto de docs internos sobre o Provimento 213. Indexação seletiva quando aplicável |

> ADRs em status "Proposto" **não devem** ser indexadas antes da decisão
> sobre seu status formal (ver `GOVERNANCE_DECISIONS.md`, decisões
> DHP-01..05).

---

## 5. Materiais de Consultoria

Materiais de terceiros entram **apenas** como
`THIRD_PARTY_CONSULTING_DOC`, jamais como norma oficial. Em qualquer
output futuro, devem ser explicitamente identificados como
interpretação/correlação.

| source_id | Título | Categoria | Status | `local_index_allowed` | `external_api_allowed` | `requires_human_approval` | `normative_authority` | Observações |
|---|---|---|---|---|---|---|---|---|
| `inovalgpd-matriz-prov213-v1` | Matriz de Correlação Provimento 213 × Políticas InovaLGPD | `THIRD_PARTY_CONSULTING_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | **false** | true | **false** | Material auxiliar de correlação e execução. **Não** é fonte normativa oficial. Uso sujeito à política contratual/licenciamento (DHP-08) |
| `inovalgpd-guia-politicas` | Guia de Uso das Políticas InovaLGPD | `THIRD_PARTY_CONSULTING_DOC` | `CANDIDATE_REQUIRES_REVIEW` | true | **false** | true | **false** | Material auxiliar de execução. Sujeito à política contratual (DHP-08). Sempre marcar `is_normative=false` |

**Observação fixa para toda fonte desta seção:**

> Material auxiliar de correlação e execução. Não é fonte normativa
> oficial. Uso sujeito à política contratual/licenciamento. Toda citação
> futura deve identificar o material como interpretação, nunca como
> prescrição normativa.

---

## 6. Fontes Expressamente Bloqueadas

As fontes abaixo estão `BLOCKED` por padrão em todas as fases iniciais.
Reentrada em pauta exige ADR específica e decisão formal do
delegatário/gestor.

| Item | Motivo |
|---|---|
| Matrículas reais | LGPD; sigilo registral; dados de partes |
| Documentos de clientes | LGPD; sigilo profissional |
| Nomes de partes (reais) | LGPD |
| CPF (real) | LGPD; risco PII alto |
| RG (real) | LGPD; risco PII alto |
| Endereços (reais) | LGPD |
| Valores financeiros reais (atos, emolumentos, movimentações) | Sigilo; risco operacional |
| Atos concretos praticados | Sigilo registral; responsabilidade do delegatário |
| Logs de produção com dados pessoais | LGPD; rastreabilidade vazada |
| Backups operacionais | Conteúdo pleno; risco massivo |
| Planilhas financeiras reais (incluindo séries históricas) | Sigilo; conteúdo identificável |
| Relatórios internos confidenciais | Estratégia; sigilo contratual |
| Documentos operacionais sensíveis | Risco de vazamento estratégico |
| Qualquer conteúdo sensível destinado a API externa | ADR-006; ADR-007 |

Estas exclusões valem **independentemente** de existir aprovação para
indexação local. Em dúvida: **bloquear**, nunca permitir.

---

## 7. Critérios para Adicionar Nova Fonte

Antes de incluir qualquer linha nova nas tabelas das Seções 3, 4 ou 5,
todos os itens abaixo devem ser satisfeitos e registrados:

- [ ] Fonte **identificada** (título, autoridade, jurisdição, versão).
- [ ] **Origem verificada** (URL oficial, caminho local controlado, ou
      arquivo de consultoria com proveniência clara).
- [ ] **Classificação** definida (categoria da Seção 6 do blueprint).
- [ ] **Confidencialidade** definida (`PUBLIC` / `INTERNAL` /
      `CONFIDENTIAL` / `RESTRICTED`).
- [ ] **Risco PII** definido (`NONE` / `LOW` / `MEDIUM` / `HIGH` /
      `PROHIBITED`).
- [ ] `local_index_allowed` definido com justificativa.
- [ ] `external_api_allowed` definido com justificativa
      (default seguro: `false`).
- [ ] **Aprovação humana** registrada (nome do responsável, data,
      decisão).
- [ ] **Checksum futuro previsto** (a fonte tem versão estável,
      checksum SHA-256 será calculado na ingestão).
- [ ] **Regra de citação** possível (formato canônico definido conforme
      Seção 15 do blueprint).

Falhar em qualquer item invalida a entrada na allowlist.

---

## 8. Pendências de Curadoria

Pendências abertas que bloqueiam a promoção de fontes a
`APPROVED_FOR_PHASE_1`:

1. **Confirmar texto oficial vigente do Provimento CNJ 213/2026**
   (incluindo eventuais alterações posteriores à publicação) — pré-
   requisito para `cnj-prov-213-2026`.
2. **Confirmar versão usada do Provimento CNJ 50/2015 compilado** — qual
   data de consolidação, qual fonte oficial, quais alterações.
3. **Definir capítulos iniciais do CNPFE-GO** (DHP-07) — escopo seletivo
   ou integral; quais livros/capítulos entram na Fase 1.
4. **Aprovar ou ajustar status das ADRs 004–008** — atualmente todas em
   "Proposto"; necessário decisão formal.
5. **Validar política contratual de uso dos materiais InovaLGPD**
   (DHP-08) — confirmar termos de uso, redistribuição interna e veto a
   envio externo.
6. **Confirmar capítulos/seções do CNPFE-GO relevantes** ao módulo de
   Notas, Registro de Imóveis e Foro Extrajudicial, para ingestão
   seletiva sem volume desnecessário.

Cada pendência resolvida deve produzir atualização desta tabela e da
correspondente em `GOVERNANCE_DECISIONS.md`.

---

*Sprint KNOWLEDGE-BASE-0.1 — 2026-05-25.*
*Documento conceitual. Nenhuma fonte foi ingerida. Nenhum código foi
implementado.*
