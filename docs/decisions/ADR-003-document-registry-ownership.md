# ADR-003 — Document Registry como módulo dono da matriz e do inventário documental

## Status

Proposto — aguarda aprovação antes de implementação

Data: 2026-05-07
Autores: João + Claude Code
Sprint de origem: Document Registry-0 — Normative Matrix Blueprint

---

## Contexto

O sistema Cartório possui hoje quatro módulos regulatórios consolidados:

- `audit` — diagnóstico técnico de pastas, arquivos e estrutura no servidor;
- `retention` — temporalidade documental (Provimento CNJ 50/2015);
- `lgpd` — plano de proteção de dados pessoais e ações;
- `compliance` — mapeamento normativo (Matriz INOVA V1, requisitos do
  Provimento CNJ 213/2026, requisitos LGPD), com `ComplianceEvidence`
  (ADR-001), referência fraca entre módulos (ADR-002),
  `RequirementFindingLink` e `ComplianceStatus` indicativo (Sprints
  Compliance-2/3/4).

A próxima frente identificada no roadmap é uma **matriz normativa de
documentos esperados** da serventia: livros, acervo, arquivos, pastas,
classificadores, sistemas e evidências documentais. A matriz precisa:

1. existir como modelo conceitual de "o que a serventia deveria possuir
   por norma" — base normativa: CNPFE-GO, Provimento 50/2015, Provimento
   213/2026, com INOVA LGPD como insumo operacional;
2. receber candidatos descobertos pelo `audit` (arquivos efetivos no
   servidor) e conciliar com a matriz;
3. produzir lacunas, possíveis correspondências, candidatos em
   localização inadequada, duplicidades e itens que exigem revisão humana;
4. alimentar o `compliance` com **evidências candidatas** sem que o
   `compliance` se torne dono do inventário documental.

A questão arquitetural central é: **qual módulo é dono dessa matriz**?

Há três candidatos naturais:

1. **Compliance como dono** — a matriz vira sub-domínio de `compliance`
   (extensão da Matriz INOVA V1).
2. **Novo módulo `document_registry` como dono** — matriz vira domínio
   próprio, separado do `compliance`.
3. **Matriz embutida em `audit`** — o `audit` ganharia conhecimento
   normativo do que esperar.

A decisão impacta: separação de domínios, capacidade do `compliance` de
permanecer focado em requisitos regulatórios (não em inventário
documental), evolução independente do inventário documental, capacidade
de `audit` permanecer puramente técnico, e a linguagem regulatória
(documento esperado vs. requisito normativo).

---

## Decisão

**O módulo `document_registry` (a ser implementado em sprint futura) é o
dono exclusivo:**

1. **da matriz normativa de documentos esperados** (`ExpectedDocument`);
2. **do inventário documental institucional** (referências aos candidatos
   observados);
3. **da conciliação entre esperado e observado** (`DocumentMatch`,
   `DocumentGap`);
4. **do registro de status operacionais documentais** — duplicidade,
   localização inadequada, versão desatualizada, exige revisão humana.

**O módulo `compliance` não será dono dessa matriz.** Compliance consome
correspondências e lacunas exclusivamente por **referência fraca**, no
mesmo padrão estabelecido por ADR-002:

```
ComplianceEvidence(
  source_module = "document_registry",
  source_type   = "expected_document_match"      ou
                  "missing_expected_document",
  source_ref    = "DOCMATCH-000123"              ou
                  "DOCGAP-000045",
  ...
)
```

Os prefixos `DOCMATCH-*` e `DOCGAP-*` são propostos como convenção
inicial. A convenção definitiva será decidida em Document Registry-1,
mas **não** implica FK física para o `compliance`.

**O módulo `audit` permanece puramente técnico.** Ele continua a
produzir achados (`DIAG-*`, duplicidade etc.). O `audit` **não** importa
modelos de `document_registry`. O `document_registry` lê os achados do
`audit` por seu próprio service (sem import cruzado de modelos), via
referência fraca.

---

## Consequências positivas

### 1. Separação clara de domínios

`compliance` continua sendo responsável por **requisitos normativos**.
`document_registry` cuida da **tipologia documental**. `audit`
permanece **leitor técnico** da estrutura do servidor. Essa separação
reduz acoplamento e facilita manutenção independente.

### 2. Compliance não vira repositório de inventário

Hoje, a Matriz INOVA V1 contém ~32 requisitos, ~30 políticas, ~75
vínculos, ~96 prazos e ~131 evidências sugeridas (ver memória da
Sprint Compliance-1). Adicionar mais ~120 itens documentais cartoriais
ao `compliance` poluiria seu domínio com tipologia que não é
estritamente regulatória — ex.: "Livro de Procurações" não é um
requisito, é um insumo cartorial.

### 3. Linguagem conservadora preservada

`document_registry` usa "documento esperado", "candidato encontrado",
"lacuna documental", "exige revisão humana" — linguagem operacional.
`compliance` usa "requisito", "evidência regulatória", "status
indicativo" — linguagem regulatória. Cada módulo no seu próprio
vocabulário, sem ambiguidade.

### 4. Evolução independente

A matriz documental cresce e evolui com base no CNPFE-GO e seus
provimentos. A matriz regulatória do `compliance` cresce com base em
provimentos CNJ e LGPD. Mudanças em uma **não** disparam migrations na
outra. Isso é importante para o roadmap CNJ 213 / LGPD-2 / Compliance-5+.

### 5. Permite consumir candidatos heterogêneos

Um `ExpectedDocument` pode receber candidatos de múltiplas fontes:
`audit` (arquivos no servidor), uploads manuais de operadores, sistemas
externos (Engegraph, MHR). Hospedar esse processo no `compliance`
forçaria que `compliance` conhecesse o modelo de cada fonte —
indesejável.

### 6. Mantém isolamento testado

O projeto possui testes de isolamento entre módulos. Manter
`document_registry` como módulo separado preserva a invariante: cada
módulo tem seus próprios models, schemas, services e migrations,
sem imports cruzados. A integração se dá apenas por referência fraca
e por services com injeção.

### 7. Reaproveita infraestrutura já validada

O padrão referência-fraca + `source_module/source_type/source_ref` já
está estabelecido (ADR-002). `document_registry` adota o mesmo padrão
sem inventar mecanismo novo.

### 8. `audit` segue puro

`audit` é o mais sensível dos módulos: ele toca o sistema de arquivos
da serventia. Manter `audit` puramente técnico, sem conhecimento
normativo, reduz a superfície de mudança e mantém a regra
[`AUDIT_READ_ONLY_POLICY`](../AUDIT_READ_ONLY_POLICY.md) intacta.

---

## Consequências negativas

### 1. Mais um módulo para manter

Adicionar `document_registry` aumenta a contagem de módulos
regulatórios de 4 para 5. Cada módulo tem custo: model, schema,
service, router, testes, migration, isolation tests.

**Mitigação:** o módulo é coeso; sua existência elimina sobrecarga em
`compliance` (que não precisará ganhar 120+ entradas de tipologia
documental). O custo total do sistema **diminui** com a separação.

### 2. Integração extra entre `audit` e `document_registry`

`document_registry` precisa consumir achados do `audit` por referência
fraca. Isso adiciona um caminho de integração que hoje não existe.

**Mitigação:** o caminho é unidirecional (audit → registry, nunca o
inverso). A integração é por service (não por FK). É o mesmo padrão
já validado no ADR-002 entre `compliance` e `audit/lgpd`.

### 3. Risco de "duplicação aparente" com `compliance`

A pessoa não familiar com a arquitetura pode achar que matriz
documental e Matriz INOVA V1 são "a mesma coisa".

**Mitigação:** o blueprint
([`CNPFE_GO_NORMATIVE_MATRIX_BLUEPRINT.md`](../document_registry/CNPFE_GO_NORMATIVE_MATRIX_BLUEPRINT.md))
explicita a distinção: matriz documental é **inventário esperado**;
Matriz INOVA V1 é **catálogo de requisitos regulatórios**.

### 4. Convenção de prefixos a ser definida

`DOCMATCH-*` e `DOCGAP-*` são propostas. A definitiva precisa ser
decidida em Document Registry-1.

**Mitigação:** a decisão é local e reversível antes da implementação.

---

## Alternativas consideradas

### Alternativa A — Compliance é dono da matriz documental

A matriz documental seria modelada como sub-tabela ou extensão de
`compliance`, ao lado de `ComplianceRequirement` e `ComplianceEvidence`.

**Por que descartada:**

1. **Mistura semântica.** Um "Livro de Notas" não é um requisito
   normativo; é um insumo documental. Tratá-lo como entrada de
   `compliance` confunde o domínio.
2. **Inflação do `compliance`.** O `compliance` é o módulo mais visível
   do sistema (alimenta o painel CNJ 213, dossiê técnico, declarações
   anuais). Carregá-lo com tipologia documental aumenta a superfície
   sem ganho regulatório.
3. **Acoplamento aumentado.** Cada vez que o CNPFE-GO ganhar um livro
   novo, `compliance` precisaria de migration. Hoje, mudanças no CNPFE
   estão dispersas em provimentos do CNJ Goiás — a frequência não é
   trivial.
4. **Linguagem regulatória se contamina.** "Livro de Procurações em
   localização inadequada" não é uma evidência regulatória; é um
   sinal operacional. Hospedar isso em `compliance` força o módulo a
   ter linguagem mista.
5. **Bloqueia evolução de tipologia.** Tipologia documental
   (BOOK, ADMIN_BOOK, ARCHIVE, FOLDER, CLASSIFIER, INDEX, POLICY,
   TECHNICAL_EVIDENCE) é estranha ao vocabulário de requisitos. Isso
   gera enums acoplados em `compliance`.

### Alternativa B — Matriz embutida em `audit`

`audit` ganharia conhecimento normativo: ele saberia que
`/serventia/02_notas/livros/protocolo/` é o "Livro de Protocolo de
Notas".

**Por que descartada:**

1. **Quebra a pureza do `audit`.** Hoje `audit` é puramente técnico:
   tamanho, hash, mtime, duplicidade, permissão. Adicionar
   conhecimento normativo (artigo do CNPFE-GO) viola a separação que
   permite, por exemplo, rodar `audit` em outra serventia (de outro
   estado) sem reescrever a matriz.
2. **Risco de leitura de conteúdo.** Para identificar "Livro de
   Protocolo de Notas", `audit` poderia ser tentado a abrir o
   arquivo. Isso quebra a `AUDIT_READ_ONLY_POLICY` de só ler metadados.
3. **Reuso bloqueado.** A matriz precisa ser consumível por relatórios
   gerenciais e por `compliance`. Esses consumidores não devem importar
   `audit`. Hospedar a matriz em `audit` força import cruzado.
4. **Sobrecarga de migrations.** Toda atualização da matriz exigiria
   migration em `audit`, módulo crítico de produção.

### Alternativa C — Módulo utilitário compartilhado `documents` consumido por todos

Um módulo "utilitário" `documents` traria entidades genéricas de
documento que `audit`, `retention`, `lgpd`, `compliance` consumiriam
todos juntos.

**Por que descartada:**

1. **Acoplamento centralizado.** Qualquer mudança em `documents`
   afetaria todos os módulos. Isso é exatamente o oposto do princípio
   adotado em ADR-001 / ADR-002.
2. **Não há ganho de reuso real.** A maior parte do "modelo de
   documento" só é usada por `document_registry`; os demais módulos
   consomem por referência fraca.
3. **Sem precedente.** O projeto não possui módulo utilitário
   compartilhado. Introduzir um vai contra o padrão existente.

### Alternativa D — Não criar módulo; deixar a matriz como documentação estática

A matriz ficaria apenas como markdown nos `docs/` e revisões humanas
fariam a conciliação com base nos achados do `audit` em planilhas
fora do sistema.

**Por que descartada:**

1. **Desperdiça os achados do `audit`.** O `audit` já produz os
   candidatos; faltaria automação para vincular.
2. **Bloqueia o painel gerencial.** O `compliance` precisa de
   evidências candidatas estruturadas para alimentar seu painel
   indicativo. Sem o `document_registry`, evidências documentais
   ficariam soltas.
3. **Não escala com mudanças normativas.** Um novo provimento que
   altere um livro exigiria edição manual em N planilhas.

---

## Critérios para revisitar a decisão

A decisão deve ser revisitada se **qualquer** dos critérios abaixo for
atendido:

1. A matriz documental ficar abaixo de ~30 itens consolidados após
   revisão humana — nesse caso, hospedar em `compliance` pode ficar
   mais barato.
2. A integração `audit` → `document_registry` exigir importação
   bidirecional de modelos — nesse caso, mover para um único módulo
   pode ser o caminho.
3. O `document_registry` precisar tomar decisões regulatórias por si
   mesmo — sinal de que o domínio se aproximou demais de `compliance`.
4. O custo de manutenção de 5 módulos regulatórios começar a
   prejudicar entregas — nesse caso, consolidar é uma opção válida.

Nenhum desses critérios é atendido hoje (matriz inicial tem ~120 itens;
integração é unidirecional; o registry permanece operacional sem
declarar conformidade; o time absorve novos módulos com regularidade).

---

## Relação com ADR-001 e ADR-002

### ADR-001 — ComplianceEvidence é dono das evidências regulatórias

ADR-003 **reforça** ADR-001. Uma `ComplianceEvidence` que tenha origem
em `document_registry` permanece sob propriedade de `compliance`. A
referência ao `DocumentMatch` ou `DocumentGap` é fraca (textual), e o
`compliance` mantém autoridade sobre o significado regulatório.

### ADR-002 — Referências fracas entre módulos regulatórios

ADR-003 **estende** ADR-002 para incluir `document_registry` como
fonte legítima de referência fraca:

| `source_module`        | `source_type`                                   | Exemplo `source_ref` |
|------------------------|--------------------------------------------------|----------------------|
| `audit`                | `finding`                                        | `DIAG-004`           |
| `retention`            | `temp_signal`                                    | `TEMP-002`           |
| `lgpd`                 | `lgpd_action`                                    | `AC-15`              |
| **`document_registry`**| **`expected_document_match`**                    | **`DOCMATCH-000123`**|
| **`document_registry`**| **`missing_expected_document`**                  | **`DOCGAP-000045`**  |
| **`document_registry`**| **`unexpected_relevant_document`**               | **(opcional)**       |
| `external`             | `document` / `other`                             | `ata_dpo.pdf`        |
| `manual`               | `other`                                          |                      |

Os critérios de validação no service de `compliance` permanecem os
mesmos: enum `source_module` aceita `"document_registry"` como valor
adicional; regex de `source_ref` aceita os novos padrões.

---

## Impacto no Compliance

- **Sem migration imediata.** O schema atual de `ComplianceEvidence` já
  aceita `source_module` como string. A inclusão de
  `"document_registry"` é uma extensão de enum, decidida em
  Document Registry-2 (não nesta sprint).
- **Sem impacto em `ComplianceRequirement` e `ComplianceStatus`.** A
  matriz documental **não** cria requisitos novos. Continua existindo
  apenas a Matriz INOVA V1 como matriz de requisitos.
- **Aumento de evidências candidatas.** Quando `document_registry` for
  implementado, o `compliance` ganhará nova fonte de evidências sem
  ganhar tabelas novas.
- **Painel CNJ 213.** Evidências de `document_registry` para
  requisitos de TIC (PSI, PCN, PRD, dossiê técnico) reforçam o painel
  já existente. A linguagem do painel **não muda**: continua
  indicativa, com nota explícita de que não substitui revisão humana.

---

## Impacto no Audit

- **Sem mudança imediata.** `audit` permanece puramente técnico.
- **Eventualmente, novo tipo de finding "documento candidato".**
  Document Registry-1 poderá especificar um tipo `DOCCAND-*` em
  `audit` para representar um arquivo identificado como possível
  candidato documental. Isso é decisão de Document Registry-1, não
  desta sprint.
- **Sem violação da `AUDIT_READ_ONLY_POLICY`.** Apenas metadados
  passam para o `document_registry`.
- **Sem import cruzado.** `audit` continua sem importar modelos de
  outros módulos.

---

## Impacto no Retention

- **Sem mudança imediata.**
- **Eventualmente, consulta da tipologia.** `retention` poderá, em
  sprint futura, consultar `document_registry` para descobrir o tipo
  documental ao aplicar prazo do Provimento 50. Hoje, `retention` usa
  tipologia interna; futuramente poderá unificar via referência
  fraca.
- **Sem dependência reversa.** `document_registry` não consulta
  `retention` para tomar decisões; apenas mantém `notes` com prazos
  do Provimento 50 como informação de contexto.

---

## Impacto no LGPD

- **Sem mudança imediata.**
- **Eventualmente, consulta da categoria de dados pessoais.** Quando
  `audit` sinalizar `pii_candidate = true` em um candidato,
  `document_registry` o marca em metadados; o `lgpd` pode consultar
  para priorizar análises.
- **Sem import cruzado.** Integração apenas por referência fraca.

---

## Plano de adoção

1. **Document Registry-0 (esta sprint)** — produz blueprint, matriz
   inicial, conceito do módulo e ADR-003. **Sem código.**
2. **Document Registry-1A — Validação e normalização da matriz.**
   Revisão humana (jurídica e correicional) dos itens `CONDITIONAL` e
   `PENDING_NORMATIVE_REVIEW`; reconciliação quantitativa por
   especialidade; confirmação da atribuição efetiva da serventia
   (cumulações, desdobramentos); convenção definitiva dos prefixos
   operacionais (`DOCCAND-*`, `DOCMATCH-*`, `DOCGAP-*`). **Sem
   código.**
3. **Document Registry-1B — Implementação somente-leitura.**
   Especificação técnica do módulo (`ExpectedDocument` versionado,
   schemas, migration); endpoints somente-leitura (lista, detalhe,
   filtro por especialidade); seed idempotente da matriz validada em
   1A. Sem conciliação ainda.
4. **Document Registry-2** — implementação de conciliação:
   `ObservedDocumentCandidate`, `DocumentMatch`, `DocumentGap`;
   integração com `audit` por referência fraca; revisão humana de
   correspondências; relatórios operacionais.
5. **Document Registry-3** — exposição de `document_registry` para
   `compliance` por referência fraca; novo `source_module =
   "document_registry"` em `ComplianceEvidence`; relatórios
   gerenciais.
6. **Sprints subsequentes** — heurísticas de match score; alertas de
   versão desatualizada; integração com vendors (Engegraph, MHR).

Cada sprint depende explicitamente da aprovação humana da anterior. A
matriz **não é instalada como código nesta sprint**.

---

## Referências

- [Blueprint de Integração Regulatória](../CNJ_213_REGULATORY_INTEGRATION_BLUEPRINT.md)
- [ADR-001 — ComplianceEvidence como entidade central](ADR-001-compliance-evidence-ownership.md)
- [ADR-002 — Referências fracas entre módulos regulatórios](ADR-002-weak-references-between-regulatory-modules.md)
- [Blueprint da Matriz Normativa](../document_registry/CNPFE_GO_NORMATIVE_MATRIX_BLUEPRINT.md)
- [Matriz Inicial CNPFE-GO](../document_registry/EXPECTED_DOCUMENTS_CNPFE_GO_INITIAL_MATRIX.md)
- [Conceito do módulo Document Registry](../document_registry/DOCUMENT_REGISTRY_MODULE_CONCEPT.md)
- [`AUDIT_READ_ONLY_POLICY`](../AUDIT_READ_ONLY_POLICY.md)
