# Document Registry — Conceito do Módulo

**Sprint:** Document Registry-0
**Data:** 2026-05-07
**Status:** Conceitual — não há código associado nesta sprint
**Autores:** João + Claude Code

---

## 1. Problema que o módulo resolve

A serventia possui um conjunto extenso de livros, arquivos, pastas,
classificadores, sistemas e documentos esperados por norma (CNPFE-GO,
Provimento CNJ 50/2015, Provimento CNJ 213/2026, e ainda políticas
operacionais da INOVA LGPD).

Hoje, o sistema possui:

- `audit` — escaneia pastas do servidor e produz achados sobre arquivos,
  estrutura, permissões e duplicidades;
- `retention` — aplica temporalidade documental (Provimento 50);
- `lgpd` — aplica plano de proteção de dados pessoais;
- `compliance` — mapeia requisitos regulatórios e produz status indicativo.

**Não existe** um módulo que responda às perguntas:

1. Quais documentos a serventia **deveria possuir** segundo norma?
2. Os arquivos efetivamente encontrados pelo `audit` **correspondem** ao
   que a norma espera?
3. Quais lacunas documentais existem?
4. Quais arquivos estão em **localização inadequada**?
5. Quais são candidatos a **duplicidade** ou **versão desatualizada**?
6. Quais exigem **revisão humana**?

O módulo `document_registry` resolve essa lacuna conceitual, mantendo:

- a **matriz normativa** de documentos esperados (Document Registry-0
  produz a base documental dela; ver
  [`EXPECTED_DOCUMENTS_CNPFE_GO_INITIAL_MATRIX.md`](EXPECTED_DOCUMENTS_CNPFE_GO_INITIAL_MATRIX.md));
- o **inventário documental institucional** (lado normativo);
- a recepção dos **candidatos** observados pelo `audit`;
- a **conciliação** entre esperado e observado;
- o registro de **lacunas**, **duplicidades**, **localização inadequada**,
  **versão desatualizada** e itens que **exigem revisão humana**.

---

## 2. O que o módulo NÃO faz

A delimitação negativa é tão importante quanto a positiva:

- **Não move arquivos.** Nenhum candidato observado é movido, copiado,
  renomeado, deletado ou alterado por este módulo.
- **Não lê conteúdo sensível de forma automática.** A leitura, quando
  ocorrer, será sob política explícita do `audit` e somente de
  metadados/headings — análise de conteúdo é responsabilidade do `lgpd`.
- **Não declara conformidade.** Uma `MATCHED_REQUIRES_REVIEW` (ver §6)
  jamais significa "documento conforme". Significa apenas que o sistema
  encontrou um candidato compatível e que cabe à pessoa responsável
  revisá-lo.
- **Não substitui revisão humana**, **análise jurídica** ou
  **vistoria correicional**.
- **Não é dono dos achados técnicos do `audit`.** Achados como permissão
  de pasta, integridade de assinatura digital ou duplicidade de hash
  permanecem em `audit`. O `document_registry` recebe candidatos referenciados.
- **Não é dono das evidências regulatórias do `compliance`.** Uma
  correspondência (`DOCMATCH-*`) ou lacuna (`DOCGAP-*`) é apenas uma
  evidência candidata para o `compliance` consumir por referência fraca
  (ver ADR-003).
- **Não substitui o `retention`** na decisão de eliminação de documentos.
  Apenas oferece tipologia para o `retention` aplicar suas regras.

---

## 3. Fronteira com `audit`

O `audit` é o módulo que efetivamente toca o sistema de arquivos da
serventia (em modo somente-leitura, conforme
[`AUDIT_READ_ONLY_POLICY.md`](../AUDIT_READ_ONLY_POLICY.md)).

O `document_registry` **nunca** acessa diretamente o sistema de arquivos.
Ele **recebe** referências aos candidatos descobertos pelo `audit`:

```
audit  →  varre pastas, calcula hash, identifica metadados
            │
            ▼
        Produz candidatos com:
        - caminho relativo
        - metadados (mtime, tamanho, hash)
        - nome canônico, extensão
        - pasta-pai
        - flags de duplicidade já calculadas
            │
            ▼
document_registry  ←  recebe candidatos como referência fraca
                       (audit não conhece document_registry)
```

A integração é **unidirecional via referência fraca**: o `audit` produz
findings (DIAG-*, DUP-*, etc.). O `document_registry` lê esses findings
por seu próprio service, **não** importando modelos de `audit`. O `audit`
não precisa ser ciente de que existe matriz documental.

### Que tipo de candidato o audit produz para o document_registry

- arquivos individuais com nome significativo (ex.:
  `PSI_v2.pdf`);
- pastas inteiras quando representam um livro/arquivo institucional
  (ex.: `intimacoes/`);
- coleções marcadas pelo `audit` como duplicadas;
- estruturas de pastas com profundidade definida (não recursividade
  exaustiva).

### Que tipo de candidato o document_registry NÃO recebe

- conteúdo extraído de PDFs ou DOCXs;
- texto integral de documentos;
- dados pessoais ou conteúdo sensível.

---

## 4. Fronteira com `retention`

`retention` aplica temporalidade documental: prazos do Provimento 50,
classificação corrente / intermediária / permanente, eliminação,
descarte e destinação.

`document_registry` mantém **a tipologia normativa**: o que é "Livro de
Visitas", "DNV", "comprovante de despesa". `retention` consulta essa
tipologia para saber qual prazo aplicar.

```
document_registry  →  define a tipologia (ADM-001, RCPN-010 etc.)
            │
            ▼
retention  →  recebe a tipologia + a data de origem → aplica prazo
              do Provimento 50 ou regra de retenção customizada
```

`retention` **não** é dono da matriz. Ele consome a tipologia do
`document_registry`. `document_registry` **não** decide eliminação.

---

## 5. Fronteira com `lgpd`

`lgpd` cuida de privacidade: classificação de dados pessoais, plano de
ações, RIPD, ROPA, requisições de titular, gestão de incidentes.

`document_registry` apenas reconhece que **certos documentos contêm
dados pessoais** por categoria (ex.: DNV, declaração de óbito, RIPD)
e marca essa característica em metadados de tipo. Quando o `audit`
indicar que um candidato pode conter dados pessoais (por categoria
inferida), o `document_registry` pode rotular o candidato com
`PII_CANDIDATE = true` e cabe ao `lgpd` decidir.

`document_registry` **não** lê o conteúdo do arquivo para descobrir se
há dado pessoal. Confia na tipologia.

---

## 6. Fronteira com `compliance`

`compliance` é o agregador de requisitos regulatórios (Provimento 213
em primeiro plano, Provimento 50 e CNPFE-GO como complementares,
LGPD como base legal).

`compliance` consome do `document_registry` por **referência fraca**
(ver [ADR-003](../decisions/ADR-003-document-registry-ownership.md)):

```text
ComplianceEvidence(
  requirement_id = "REQ-PROV213-PSI-001",
  source_module  = "document_registry",
  source_type    = "expected_document_match",
  source_ref     = "DOCMATCH-000123",
  ...
)
```

Ou, para uma lacuna:

```text
ComplianceEvidence(
  requirement_id = "REQ-PROV213-PSI-001",
  source_module  = "document_registry",
  source_type    = "missing_expected_document",
  source_ref     = "DOCGAP-000045",
  ...
)
```

A correspondência ou a lacuna **não** declaram conformidade. São apenas
**evidências candidatas**. A consolidação regulatória cabe ao
`compliance`, com revisão humana, conforme já estabelecido no roadmap.

`compliance` **não** importa modelos de `document_registry`. A integração
é exclusivamente por referência fraca textual.

---

## 7. Entidades conceituais

As entidades abaixo são **conceituais**. Não há schema, não há tabela,
não há código nesta sprint. A definição final do schema será objeto de
Document Registry-1.

### 7.1 ExpectedDocument

Representa um item da matriz normativa.

Campos conceituais mínimos:

| Campo                | Tipo conceitual         | Origem                                                         |
|----------------------|-------------------------|----------------------------------------------------------------|
| `code`               | string estável          | Convenção (ex.: `ADM-001`)                                     |
| `title`              | string                  | Matriz normativa                                               |
| `specialty`          | enum                    | `COMUM`, `NOTAS`, `PROTESTO`, etc.                            |
| `category`           | enum                    | `LIVRO_OBRIGATORIO`, `POLITICA`, etc.                          |
| `kind`               | enum                    | `BOOK`, `ADMIN_BOOK`, `ARCHIVE`, etc.                          |
| `normative_source`   | string                  | Diploma                                                        |
| `normative_reference`| string                  | Artigo                                                         |
| `obligation_level`   | enum                    | `REQUIRED`, `CONDITIONAL`, `OPTIONAL`, `PENDING_NORMATIVE_REVIEW` |
| `expected_format`    | enum                    | `PHYSICAL`, `ELECTRONIC`, `PHYSICAL_OR_ELECTRONIC`, `HYBRID`, `UNSPECIFIED` |
| `suggested_folder`   | string (não vinculante) | Convenção institucional                                        |
| `requires_human_review` | boolean              |                                                                |
| `notes`              | string                  | Prazos do Provimento 50, condicionantes, observações           |

`ExpectedDocument` é **versionado**. Quando uma fonte normativa muda
(ex.: novo provimento que cria um livro), uma nova versão é criada. A
versão anterior **não é deletada**, em respeito ao princípio de
imutabilidade já adotado para `audit_findings` e `lgpd_actions`.

### 7.2 ObservedDocumentCandidate

Representa um arquivo / pasta efetivamente encontrado pelo `audit`.

Campos conceituais mínimos:

| Campo               | Tipo conceitual    | Observações                                                    |
|---------------------|--------------------|----------------------------------------------------------------|
| `code`              | string estável     | Ex.: `DOCCAND-000123`                                          |
| `audit_finding_ref` | referência fraca   | `DIAG-XYZ` ou similar; permite rastrear de volta ao `audit`    |
| `relative_path`     | string             | Caminho relativo a partir da raiz canônica                     |
| `file_type`         | string             | Extensão / tipo MIME                                           |
| `size`              | bigint             |                                                                |
| `hash`              | string             | SHA-256 calculado pelo `audit`                                 |
| `mtime`             | timestamp          |                                                                |
| `parent_folder_inferred` | string         | Pasta canônica inferida pelo `audit` (livro de notas etc.)     |
| `pii_candidate`     | boolean            | Sinalizado quando a categoria sugere conter dados pessoais     |
| `discovered_at`     | timestamp          |                                                                |

`ObservedDocumentCandidate` é **imutável** após criação. Não há "edit".
Para alterações, novo candidato é criado.

### 7.3 DocumentMatch

Vínculo entre um `ExpectedDocument` e um `ObservedDocumentCandidate`.

Campos conceituais mínimos:

| Campo                | Tipo conceitual                                                                                                       |
|----------------------|-----------------------------------------------------------------------------------------------------------------------|
| `code`               | `DOCMATCH-000123`                                                                                                     |
| `expected_code`      | FK lógica (não FK física) para `ExpectedDocument.code`                                                                 |
| `candidate_code`     | FK lógica para `ObservedDocumentCandidate.code`                                                                       |
| `match_status`       | enum (ver §8)                                                                                                          |
| `match_score`        | float ∈ [0, 1] — heurística inicial                                                                                   |
| `reasoning`          | string curta — base da heurística                                                                                      |
| `requires_human_review` | boolean                                                                                                            |
| `reviewed_by`        | string (após revisão humana)                                                                                           |
| `reviewed_at`        | timestamp                                                                                                              |
| `final_decision`     | enum: `CONFIRMED`, `REJECTED`, `PENDING`                                                                              |

`DocumentMatch` é versionável: revisões humanas geram nova versão,
preservando histórico de decisões.

### 7.4 DocumentGap

Representa um documento esperado para o qual **não há** candidato
satisfatório.

| Campo                | Tipo conceitual                                                                                                       |
|----------------------|-----------------------------------------------------------------------------------------------------------------------|
| `code`               | `DOCGAP-000045`                                                                                                       |
| `expected_code`      | FK lógica para `ExpectedDocument.code`                                                                                |
| `gap_status`         | enum (ver §8)                                                                                                          |
| `detected_at`        | timestamp                                                                                                              |
| `last_scan_id`       | referência fraca a `audit`                                                                                            |
| `closed_at`          | timestamp                                                                                                              |
| `closed_by`          | string                                                                                                                 |
| `close_reason`       | enum: `MATCH_FOUND`, `NORMATIVELY_NOT_APPLICABLE`, `HUMAN_REJECTED_AS_NOT_REQUIRED`, `OTHER`                          |

Gaps **não** são deletados ao serem fechados; apenas marcados, com data.

---

## 8. Status conceituais

Os status abaixo são propostos para uso futuro do módulo. Linguagem
estritamente conservadora: nenhum status implica conformidade automática.

### 8.1 Estados de DocumentMatch

| Status                          | Significado                                                                                                          |
|---------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `EXPECTED_NOT_OBSERVED`         | Documento esperado, nenhum candidato compatível encontrado. (Estado de `DocumentGap`.)                                |
| `CANDIDATE_FOUND`               | Há candidato encontrado, ainda não vinculado a um esperado.                                                          |
| `POSSIBLE_MATCH`                | Heurística sugere correspondência, com `match_score < limiar_alto`. Exige revisão humana.                            |
| `MATCHED_REQUIRES_REVIEW`       | Correspondência alta confiança automatizada. **Ainda assim**, exige revisão humana antes de uso regulatório.         |
| `DUPLICATE_CANDIDATE`           | Múltiplos candidatos apontam para o mesmo esperado. Triagem necessária.                                               |
| `WRONG_LOCATION`                | Candidato está fora da pasta sugerida. Indicação operacional, não declaração de irregularidade.                       |
| `OUTDATED_VERSION`              | Há candidato, mas há indícios de versão mais nova esperada (data, hash diferente, número de revisão).                 |
| `UNEXPECTED_RELEVANT_DOCUMENT`  | Candidato com aparência relevante, sem `ExpectedDocument` na matriz. Sinaliza ampliação da matriz por revisão humana. |
| `NEEDS_HUMAN_REVIEW`            | Estado fallback. Qualquer dúvida vai para aqui.                                                                      |
| `HUMAN_CONFIRMED`               | Revisão humana confirmou a correspondência.                                                                           |
| `HUMAN_REJECTED`                | Revisão humana rejeitou a correspondência.                                                                            |

### 8.2 Estados de DocumentGap

| Status                       | Significado                                                                                          |
|------------------------------|------------------------------------------------------------------------------------------------------|
| `OPEN`                       | Lacuna ativa.                                                                                        |
| `IN_INVESTIGATION`           | Equipe está investigando se o documento existe em outro lugar.                                       |
| `RESOLVED_MATCH_FOUND`       | Lacuna fechada porque um candidato compatível foi encontrado.                                        |
| `RESOLVED_NOT_APPLICABLE`    | Revisão humana confirmou que o item não se aplica à atribuição atual da serventia.                   |
| `RESOLVED_HUMAN_DECISION`    | Outras decisões humanas (ex.: aceito como pendente até prazo).                                       |

`OPEN` não significa irregularidade. Significa que a serventia ainda não
forneceu evidência clara da existência do documento. A interpretação
regulatória cabe ao `compliance` por revisão humana.

---

## 9. Endpoints futuros possíveis (não implementar nesta sprint)

Os endpoints abaixo são uma **proposta conceitual** para Document
Registry-1 e seguintes. Esta sprint **não** os implementa.

### Somente leitura (Document Registry-1)

| Método | Caminho                                  | Propósito                                                              |
|--------|------------------------------------------|------------------------------------------------------------------------|
| GET    | `/api/document-registry/expected`        | Lista itens da matriz normativa                                        |
| GET    | `/api/document-registry/expected/{code}` | Detalha um item da matriz                                              |
| GET    | `/api/document-registry/expected?specialty=NOTAS` | Filtra por especialidade                                       |
| GET    | `/api/document-registry/expected/by-source?source=CNPFE-GO` | Filtra por fonte normativa                            |

### Conciliação (Document Registry-2)

| Método | Caminho                                  | Propósito                                                              |
|--------|------------------------------------------|------------------------------------------------------------------------|
| GET    | `/api/document-registry/candidates`      | Lista candidatos recebidos do `audit`                                  |
| GET    | `/api/document-registry/matches`         | Lista correspondências (com filtro por status)                         |
| GET    | `/api/document-registry/matches/{code}`  | Detalha uma correspondência                                            |
| POST   | `/api/document-registry/matches/{code}/review` | Revisão humana (CONFIRMED / REJECTED / PENDING)                  |
| GET    | `/api/document-registry/gaps`            | Lista lacunas abertas                                                  |
| POST   | `/api/document-registry/gaps/{code}/close` | Fecha lacuna (com motivo e responsável)                              |

### Importação da matriz (Document Registry-1)

| Método | Caminho                                       | Propósito                                                       |
|--------|-----------------------------------------------|------------------------------------------------------------------|
| POST   | `/api/document-registry/expected/seed`        | Carga inicial idempotente da matriz a partir do markdown / JSON  |
| POST   | `/api/document-registry/expected/{code}/version` | Cria nova versão a partir de mudança normativa                |

Todos os endpoints respeitam o padrão dos demais módulos: paginação,
filtragem, autorização por papel, idempotência onde aplicável.

---

## 10. Regras de segurança

1. **Acesso somente-leitura aos arquivos do servidor.** Reforça-se o
   princípio do `AUDIT_READ_ONLY_POLICY`: o `document_registry` confia
   no `audit`. Mesmo que um operador peça ao `document_registry` para
   "buscar" um arquivo, a busca ocorre via `audit`, com sua política
   somente-leitura.
2. **Vedado mover, renomear, deletar arquivos.** Nenhum endpoint do
   `document_registry`, presente ou futuro, deve invocar `os.rename`,
   `os.remove`, `shutil.move` ou semelhantes.
3. **Vedado registrar conteúdo sensível.** Apenas metadados, hash e
   classificação. Texto integral nunca entra em uma tabela do
   `document_registry`.
4. **Trilha de auditoria obrigatória.** Cada criação, vinculação,
   revisão humana ou fechamento de gap deve gerar evento auditável,
   nos moldes já adotados pelos demais módulos.
5. **Imutabilidade de candidatos e gaps.** Não há `DELETE`. Mudanças
   geram nova versão.
6. **Revisão humana obrigatória** antes de promover qualquer
   correspondência a evidência regulatória no `compliance`.

---

## 11. Regra de não movimentar, renomear, deletar ou alterar arquivos

Esta regra é tão importante que aparece em seção própria.

> **O módulo `document_registry` é estritamente leitor. Em nenhuma
> circunstância — agora ou no futuro — ele deve mover, copiar, renomear,
> deletar, sobrescrever, alterar permissões ou modificar metadados de
> arquivos no servidor da serventia. Operações de qualquer espécie sobre
> o sistema de arquivos cartorial são vedadas.**

Eventuais operações de organização documental devem ser propostas como
**recomendações operacionais** ao operador humano, jamais executadas
pelo sistema. O sistema **propõe**, o humano **decide**.

---

## 12. Relação futura com relatórios operacionais

O `document_registry` alimenta dois tipos de relatórios futuros:

### 12.1 Relatórios operacionais (equipe interna)

- "Documentos esperados não observados" — checklist por especialidade.
- "Candidatos em localização inadequada" — apoio à organização.
- "Versões desatualizadas" — sinalização para revisão.
- "Duplicidades candidatas" — apoio à triagem.

Esses relatórios usam linguagem conservadora: "exige revisão humana",
"sinalização indicativa", "não substitui validação documental".

### 12.2 Relatórios gerenciais (diretoria)

- "Cobertura inicial da matriz normativa" — % de itens com correspondência
  candidata, com nota explícita de que a cobertura **não** equivale a
  conformidade.
- "Lacunas críticas para o Provimento 213 (TIC-*)" — alimenta o painel
  CNJ 213 do `compliance`.
- "Lacunas críticas para LGPD (POL-*)" — alimenta o painel LGPD.

Esses relatórios **não** declaram conformidade. Toda métrica deve vir
acompanhada da nota: *"Sinalização indicativa. Não substitui revisão
humana, vistoria correicional ou análise jurídica."*

---

## 13. Como a sprint atual (Document Registry-0) prepara o terreno

Esta sprint produz:

1. **Blueprint normativo** — regras de hierarquia de fontes, critérios
   de classificação, cuidados de linguagem.
   ([`CNPFE_GO_NORMATIVE_MATRIX_BLUEPRINT.md`](CNPFE_GO_NORMATIVE_MATRIX_BLUEPRINT.md))
2. **Matriz inicial** — ~120 itens com referência normativa explícita.
   ([`EXPECTED_DOCUMENTS_CNPFE_GO_INITIAL_MATRIX.md`](EXPECTED_DOCUMENTS_CNPFE_GO_INITIAL_MATRIX.md))
3. **Conceito do módulo** — este documento.
4. **ADR-003** — decisão de propriedade arquitetural (matriz é do
   `document_registry`, não do `compliance`).
   ([`../decisions/ADR-003-document-registry-ownership.md`](../decisions/ADR-003-document-registry-ownership.md))

Não há código, não há tabela, não há migration. Document Registry-1 será a
sprint que poderá iniciar implementação, **se e somente se** o blueprint
e a matriz forem revisados e aprovados.

---

## 14. Limitações do conceito

1. O conceito não cobre, intencionalmente, o caso de **arquivos
   binários proprietários** (ex.: livro eletrônico em formato Engegraph).
   O tratamento desses arquivos como `BOOK` exige revisão de
   interoperabilidade, fora do escopo desta sprint.
2. O conceito **não** define como serão registrados os termos de
   abertura e encerramento de livros eletrônicos. Isso será detalhado
   conforme o vendor (Engegraph, MHR) expor metadados.
3. O conceito **não** define heurísticas concretas para
   `match_score`. Heurísticas serão objeto de Document Registry-2,
   após validação da matriz.
4. O conceito **não** cobre internacionalização. A matriz é em
   português brasileiro, ancorada em norma estadual de Goiás.
