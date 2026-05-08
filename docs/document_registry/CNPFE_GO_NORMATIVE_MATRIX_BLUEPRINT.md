# CNPFE-GO — Blueprint da Matriz Normativa de Documentos Esperados

**Sprint de origem:** Document Registry-0 — Normative Matrix Blueprint
**Data:** 2026-05-07
**Status:** Documental — não há código associado nesta sprint
**Autores:** João + Claude Code

---

## 1. Objetivo

Estabelecer a base normativa, conceitual e arquitetural para a futura matriz de
documentos esperados de uma serventia extrajudicial do Estado de Goiás.

A matriz é normativa: define **quais livros, acervos, arquivos, pastas,
classificadores, sistemas, políticas e evidências documentais a serventia
deveria possuir** segundo o regramento aplicável.

A matriz **não declara conformidade**, **não substitui revisão humana**,
**não substitui auditoria correicional**, e **não autoriza qualquer ação
automática sobre arquivos físicos ou eletrônicos da serventia**.

A matriz é o ponto de ancoragem para o futuro módulo `document_registry`,
que comparará os achados do módulo `audit` (arquivos efetivamente encontrados
em pastas do servidor) com a matriz normativa, e produzirá:

- documentos esperados não observados (lacunas);
- documentos candidatos encontrados (possíveis correspondências);
- documentos com localização inadequada;
- duplicidades candidatas;
- alertas de versão desatualizada;
- itens que exigem revisão humana.

---

## 2. Hierarquia de fontes

A matriz adota uma hierarquia explícita e auditável de fontes normativas. O
objetivo é evitar que documentos auxiliares ou políticas operacionais sejam
tratados como obrigação legal cartorial, ou que requisitos regulatórios de
TIC/segurança sejam confundidos com livros e acervo cartorial.

### Hierarquia oficial

| Nível | Fonte                                                            | Papel                                                                              |
|-------|------------------------------------------------------------------|------------------------------------------------------------------------------------|
| 1     | **CNPFE-GO** (Código de Normas e Procedimentos do Foro Extrajudicial) | Fonte **principal** para livros, acervo, escrituração, arquivos e estrutura cartorial |
| 2     | **Provimento CNJ nº 50/2015**                                    | Fonte **complementar** para temporalidade, guarda, eliminação e destinação documental |
| 3     | **Provimento CNJ nº 213/2026**                                   | Fonte **complementar** para TIC, segurança, continuidade, evidências e dossiê técnico |
| 4     | **INOVA LGPD** (matriz de políticas e procedimentos da consultoria) | Fonte **auxiliar operacional** — modelos de políticas, RIPD, ciclo de vida de dados |

### Regras de precedência

1. Quando houver conflito entre uma fonte auxiliar (INOVA, relatório de
   maturidade, guia operacional) e o CNPFE-GO, **prevalece o CNPFE-GO**.
2. Itens do Provimento 213/2026 não devem ser misturados, na matriz, com a
   tipologia de livros cartoriais. Devem ser marcados explicitamente como
   `TECHNICAL_EVIDENCE` ou `POLICY` originados do Provimento 213.
3. Itens do Provimento 50/2015 não criam novos livros — atuam sobre o
   **ciclo de vida** dos itens já previstos no CNPFE-GO. Sua menção na matriz
   deve aparecer no campo "Observações" do item correspondente, e não como item
   próprio, salvo nos casos em que o Provimento 50 prevê documentos próprios
   (ex.: termos de eliminação).
4. Os modelos da INOVA são **traduções operacionais auxiliares**. Sua
   utilidade é fornecer um catálogo de evidências candidatas para requisitos
   regulatórios, especialmente do Provimento 213 e da LGPD. **Não criam por si
   sós obrigação legal.**
5. Quando uma fonte primária é silente ou ambígua em relação a um item, o item
   deve ser marcado como `PENDING_NORMATIVE_REVIEW` e nunca declarado como
   obrigatório.

### Por que CNPFE-GO é a fonte principal

A serventia objeto do projeto está sujeita à fiscalização da
Corregedoria-Geral da Justiça do Estado de Goiás. O CNPFE-GO consolida, em um
único corpo normativo:

- regras de escrituração de livros (físicos e eletrônicos);
- livros obrigatórios por especialidade;
- regras de acervo, conservação e eliminação;
- termos de abertura, encerramento, índices e classificadores;
- arquivos institucionais (intimações, editais, mandados);
- sistemas obrigatórios (SEE, SSE, SDC, SIRCON, BATE);
- regras de identificação da serventia, fachada, página na internet;
- fundamentos correicionais e de visita correicional.

Por essa razão, qualquer item incluído na matriz como `REQUIRED` deve estar
ancorado em um artigo do CNPFE-GO ou em um diploma legal por ele referenciado.

### Por que Provimento 50 entra como complementar

O Provimento CNJ nº 50/2015 trata da **temporalidade documental**: prazos de
guarda em fase corrente, intermediária e permanente, critérios de eliminação,
destinação final, e a Tabela de Temporalidade aplicável às serventias
extrajudiciais. Ele não cria livros próprios da serventia — ele determina por
quanto tempo cada documento, livro ou arquivo deve ser conservado e em que
condições pode ser eliminado.

Na matriz, o Provimento 50 aparece nas observações dos itens, e seus produtos
documentais próprios (ex.: termo de eliminação documental, relação de
documentos eliminados) podem ser incluídos como itens do tipo
`SYSTEM_RECORD` ou `LEGAL_REFERENCE`.

### Por que Provimento 213 entra como complementar

O Provimento CNJ nº 213/2026 dispõe sobre TIC, segurança da informação,
continuidade operacional, dossiê técnico, RPO/RTO, trilhas de auditoria,
backup e governança. Trata de **evidências regulatórias de TIC e governança**,
não de livros cartoriais. Itens originados do Provimento 213 entram na matriz
como `TECHNICAL_EVIDENCE` ou `POLICY` — nunca como `BOOK` ou `ADMIN_BOOK`.

A serventia foco deste projeto é Classe 3 (RPO ≤ 4h, RTO ≤ 8h), conforme
registrado no roadmap CNJ 213.

### Por que INOVA é fonte auxiliar operacional

A INOVA forneceu à serventia um conjunto de políticas, procedimentos,
contratos, planilhas de ciclo de vida e treinamentos. Esses artefatos são
**traduções operacionais** de exigências regulatórias (Provimento 213, LGPD).
A INOVA, por si só, não é uma autoridade normativa para serventias
extrajudiciais; sua matriz é útil para mapear evidências candidatas de
políticas e procedimentos, mas não cria obrigação por sua própria existência.

A pasta `_local_data/LGPD - inova` contém:

- 16 modelos de políticas (PSI, Backup, Privacidade, Descarte, Mesa Limpa,
  BYOD, Privacy by Design etc.);
- 2 procedimentos (RIPD, Análise de Legítimo Interesse);
- planilha de ciclo de vida de dados (Cartório Terezópolis de Goiás);
- contratos com fornecedores (Cofre Digital, Engegraph, MHR, APRESEG);
- guia de uso das políticas;
- matriz de correlação Provimento 213 ↔ Políticas (V1);
- relatório inicial de nível de maturidade.

Na matriz, esses itens entram como `POLICY` ou `TECHNICAL_EVIDENCE` com
`source_module = "external"` quando referenciados como evidências candidatas
para requisitos regulatórios.

---

## 3. Critérios de classificação dos itens

Cada item na matriz inicial recebe os seguintes campos, todos auditáveis e
rastreáveis a uma fonte primária:

### 3.1 Code

Identificador estável e legível (ex.: `ADM-001`, `TN-001`, `TP-002`,
`RCPN-003`, `RI-001`, `SEE-001`, `TIC-001`, `POL-001`). O code não é
sequencial em sentido absoluto: é um **prefixo + número** que indica o
domínio do item. Ele é destinado a ser referenciado por evidências e
findings em outros módulos. Não é uma chave técnica.

Convenção de prefixos:

| Prefixo  | Domínio                                                         |
|----------|-----------------------------------------------------------------|
| `COM`    | Disposições comuns a todas as serventias                        |
| `ADM`    | Livros administrativos                                          |
| `TN`     | Tabelionato de Notas                                            |
| `TP`     | Tabelionato de Protesto                                         |
| `RCPN`   | Registro Civil das Pessoas Naturais                             |
| `RCPJ`   | Registro Civil das Pessoas Jurídicas                            |
| `RTD`    | Registro de Títulos e Documentos                                |
| `RI`     | Registro de Imóveis                                             |
| `SEE`    | Sistemas e bases obrigatórias (SEE, SSE, SDC, SIRCON, BATE)     |
| `TIC`    | Evidências regulatórias de TIC (Provimento 213)                 |
| `POL`    | Políticas e procedimentos institucionais                        |
| `ARQ`    | Arquivos institucionais e classificadores                       |

> **Nota sobre prefixos operacionais (não integram a matriz normativa).**
> Os prefixos acima identificam itens da matriz normativa
> (`ExpectedDocument`). Identificadores internos de outros artefatos do
> futuro `document_registry` seguem convenção própria e **não** integram
> a matriz:
>
> - `DOCCAND-*` — identificador interno de candidato observado
>   (`ObservedDocumentCandidate`), recebido por referência fraca a partir
>   do `audit`.
> - `DOCMATCH-*` — identificador de correspondência (`DocumentMatch`)
>   entre um candidato e um item da matriz.
> - `DOCGAP-*` — identificador de lacuna documental (`DocumentGap`)
>   referente a um item esperado sem candidato satisfatório.
>
> Esses prefixos operacionais são detalhados em
> [`DOCUMENT_REGISTRY_MODULE_CONCEPT.md`](DOCUMENT_REGISTRY_MODULE_CONCEPT.md)
> e a convenção definitiva (formato numérico, padding, separador) será
> decidida em Document Registry-1A. Eles são também a base da referência
> fraca que o `compliance` consumirá, conforme
> [ADR-003](../decisions/ADR-003-document-registry-ownership.md).

### 3.2 Especialidade

Indica a atribuição cartorial à qual o item se vincula. Valores possíveis:

`COMUM`, `NOTAS`, `PROTESTO`, `RCPN`, `RCPJ`, `RTD`, `IMOVEIS`,
`ADMINISTRATIVO`, `TIC`, `LGPD`, `CORREICIONAL`.

Itens que se aplicam à serventia inteira recebem `COMUM` ou
`ADMINISTRATIVO`.

### 3.3 Categoria

Subdivisão do tipo, útil para relatórios:

- `LIVRO_OBRIGATORIO`
- `LIVRO_FACULTATIVO_DESDOBRAMENTO`
- `LIVRO_ADMINISTRATIVO`
- `ARQUIVO_OBRIGATORIO`
- `INDICE`
- `CLASSIFICADOR`
- `EVIDENCIA_TECNICA`
- `POLITICA`
- `PROCEDIMENTO`
- `CONTRATO`
- `SISTEMA_OBRIGATORIO`
- `PASTA_INSTITUCIONAL`
- `OUTRO`

### 3.4 Tipo

Como definido no escopo da sprint:

`BOOK`, `ADMIN_BOOK`, `ARCHIVE`, `FOLDER`, `CLASSIFIER`, `INDEX`,
`POLICY`, `TECHNICAL_EVIDENCE`, `LEGAL_REFERENCE`, `SYSTEM_RECORD`, `OTHER`.

### 3.5 Fonte normativa e Referência

Fonte primária explícita. Exemplos:

- `CNPFE-GO Art. 96`
- `CNPFE-GO Art. 165, I`
- `CNPFE-GO Art. 220, I`
- `Provimento CNJ 213/2026 Art. 11`
- `Provimento CNJ 50/2015 Art. 3º + Anexo I`
- `Lei nº 6.015/1973 Art. 132`
- `INOVA — Modelo PSI v.X`

A referência **deve** apontar a artigo, capítulo, anexo ou item específico,
nunca apenas ao nome do diploma.

### 3.6 Nível de obrigatoriedade

| Valor                       | Significado                                                                  |
|-----------------------------|-------------------------------------------------------------------------------|
| `REQUIRED`                  | Obrigatório por norma vigente, sem condicionante                              |
| `CONDITIONAL`               | Obrigatório quando a serventia exerce determinada atribuição ou volume        |
| `OPTIONAL`                  | Permitido / facultado pela norma; não cria obrigação                          |
| `PENDING_NORMATIVE_REVIEW`  | Identificado, mas a obrigatoriedade depende de revisão humana especializada   |

### 3.7 Formato esperado

| Valor                       | Significado                                                                |
|-----------------------------|-----------------------------------------------------------------------------|
| `PHYSICAL`                  | Apenas físico, conforme a norma                                            |
| `ELECTRONIC`                | Apenas eletrônico, conforme a norma                                        |
| `PHYSICAL_OR_ELECTRONIC`    | Norma admite qualquer dos dois, exclusivamente                              |
| `HYBRID`                    | Norma exige existência simultânea ou materialização do eletrônico em físico |
| `UNSPECIFIED`               | Norma silente quanto ao formato                                            |

### 3.8 Pasta sugerida

Caminho de pasta institucional **sugerido** para armazenamento. Não é
obrigatório; serve como referência para conciliação futura entre o que o
módulo `audit` encontra e o que a matriz espera. As convenções iniciais
sugeridas:

```
/serventia/
├── 01_administracao/
│   ├── livros/
│   │   ├── visitas_correicoes/
│   │   ├── deposito_previo/
│   │   └── diario_auxiliar/
│   ├── correicoes/
│   ├── portarias/
│   └── prestacao_contas/
├── 02_notas/
│   ├── livros/
│   │   ├── protocolo/
│   │   ├── escrituras/
│   │   ├── testamento/
│   │   └── procuracoes/
│   ├── arquivo_atos/
│   └── arquivo_procuracoes_externas/
├── 03_protesto/
│   ├── livros/
│   ├── arquivo_intimacoes/
│   ├── arquivo_editais/
│   └── arquivo_pagamentos/
├── 04_rcpn/
│   ├── livros/
│   ├── arquivo_habilitacao/
│   └── arquivo_proclamas/
├── 05_rcpj/
│   ├── livros/
│   └── arquivo_atos/
├── 06_rtd/
│   ├── livros/
│   └── arquivo_documentos/
├── 07_ri/
│   ├── livros/
│   ├── matriculas/
│   └── arquivo_documentos/
├── 08_tic/
│   ├── politicas/
│   ├── pcn_prd/
│   ├── backup/
│   ├── trilhas_auditoria/
│   ├── incidentes/
│   ├── inventario_ativos/
│   └── dossie_tecnico/
├── 09_lgpd/
│   ├── ropa/
│   ├── ripd/
│   ├── titulares/
│   └── politicas_privacidade/
└── 10_acervo_eletronico/
    ├── digitalizacoes/
    └── indices/
```

A pasta sugerida **não é vinculante**. Serventias podem manter outra
estrutura. A matriz apenas declara qual seria a pasta canônica preferida pelo
sistema, para fins de conciliação de achados do `audit`.

### 3.9 Revisão humana

Booleano (`SIM` / `NÃO`). Indica se o item, ainda que claramente identificado
na matriz, exige revisão humana antes de ser tratado como obrigação ou
evidência. Itens com `SIM`:

- têm interpretação não trivial;
- dependem da especialidade ou do volume da serventia;
- envolvem regras de transição (provimentos com prazos);
- envolvem desdobramentos facultativos não automáticos.

### 3.10 Observações

Texto livre, breve. Cita prazos do Provimento 50 (quando aplicável), regras
de desdobramento, condicionantes (ex.: "obrigatório apenas se o serviço
admitir depósito prévio"), e referências cruzadas entre artigos.

---

## 4. Categorias documentais mapeadas

A matriz inicial cobre as seguintes categorias, sempre na ordem do CNPFE-GO:

1. **Disposições comuns** — acervo geral, identificação, acervo eletrônico,
   livros físicos vs. eletrônicos, escrituração geral.
2. **Sistemas obrigatórios** — SEE, SSE, SDC, SIRCON, BATE, malote digital,
   centrais (CENPROT, CRC, CENSEC referenciadas pelo CNPFE-GO).
3. **Livros administrativos** — Visitas e Correições; Controle de Depósito
   Prévio; Diário Auxiliar da Receita e da Despesa.
4. **Tabelionato de Notas** — Protocolo de Notas; Escrituras; Testamento;
   Procurações; arquivo de procurações de outras serventias; classificadores
   de documentos pessoais; impressos de segurança.
5. **Tabelionato de Protesto** — Protocolo de Títulos; Registro de Protesto;
   Registro de Pagamento; arquivos de intimações, editais, mandados,
   ordens de cancelamento, certidões diárias.
6. **Registro Civil das Pessoas Naturais** — Livros A, B, B-Auxiliar, C,
   C-Auxiliar, D, E, Protocolo; arquivos de habilitação, atestados, DNV/DO,
   mandados.
7. **Registro Civil das Pessoas Jurídicas** — Protocolo, Livro A, Livro B;
   arquivos de atos constitutivos; índices; livros contábeis das pessoas
   jurídicas registradas.
8. **Registro de Títulos e Documentos** — Livros A, B, C, D; arquivos de
   notificações; classificador de cópias.
9. **Registro de Imóveis** — Livros 1 a 5; Livro de Aquisição de Imóveis
   Rurais por Estrangeiros; matrículas; arquivos de REURB, usucapião,
   indisponibilidades.
10. **Evidências regulatórias do Provimento 213** — PCN, PRD, PSI,
    inventário de ativos, trilhas de auditoria, registros de incidentes,
    plano de gestão de vulnerabilidades, dossiê técnico, declarações de
    conformidade.
11. **Políticas e procedimentos LGPD/INOVA** — políticas (PSI, Backup,
    Privacidade, Descarte, Mesa Limpa, BYOD, Privacy by Design, Uso de
    Imagem, Uso de Celulares, Compartilhamento, Retenção); procedimentos
    (RIPD, Análise de Legítimo Interesse); registros operacionais
    (resposta a titular, ROPA).
12. **Contratos e governança institucional** — termo de DPO, contratos de
    fornecedores críticos (cofre digital, software notarial, software
    registral, segurança do trabalho, conectividade).

A lista completa, com codes, está em
[`EXPECTED_DOCUMENTS_CNPFE_GO_INITIAL_MATRIX.md`](EXPECTED_DOCUMENTS_CNPFE_GO_INITIAL_MATRIX.md).

---

## 5. Diferença entre documento esperado, candidato encontrado, possível correspondência e lacuna

A linguagem da matriz é estrita por design. As distinções abaixo orientam
toda a comunicação futura entre `audit`, `document_registry` e `compliance`:

| Conceito                          | Significado                                                                                                                  |
|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| **Documento esperado**            | Item da matriz normativa. A serventia deveria possuí-lo (REQUIRED ou CONDITIONAL atendido). Não implica que ele exista.        |
| **Candidato encontrado**          | Arquivo, livro ou pasta efetivamente identificado pelo `audit` no servidor. Antes da conciliação, é apenas um candidato.       |
| **Possível correspondência**      | Vínculo provisório entre um candidato encontrado e um documento esperado, sugerido por heurística (nome, pasta, metadados).    |
| **Correspondência confirmada**    | Vínculo entre candidato e esperado revisto por humano e marcado como válido. Estado terminal positivo.                         |
| **Lacuna documental**             | Documento esperado para o qual não foi encontrado candidato após varredura. Pode indicar ausência real ou má organização.      |
| **Duplicidade candidata**         | Mais de um candidato apontando para o mesmo esperado. Requer triagem.                                                          |
| **Localização inadequada**        | Candidato cuja pasta de origem não corresponde à pasta sugerida. Indicação operacional, não automática de irregularidade.      |
| **Versão desatualizada**          | Candidato existente, mas com indícios (data, hash, número de revisão) de que existe versão mais nova esperada.                 |
| **Documento relevante inesperado**| Arquivo encontrado pelo `audit` que parece ter relevância documental cartorial e não está mapeado na matriz. Sinaliza revisão. |
| **Exige revisão humana**          | Qualquer estado em que o sistema não consegue afirmar com segurança e a decisão final é humana.                                |

Nenhum desses termos pode ser substituído por "conforme", "regular" ou
"comprovado". Linguagem desse tipo é proibida no `document_registry`.

---

## 6. Limitações da matriz inicial

A matriz inicial é **não exaustiva** por escolha consciente. Assume-se:

1. A leitura do CNPFE-GO foi feita sobre o consolidado disponível
   (`_local_data/serventia_docs/.../CNPFE - Consolidado - Ate Provimento n
   182-2026.pdf`). Provimentos posteriores podem alterar artigos
   referenciados.
2. Itens que dependem da atribuição efetiva da serventia recebem
   `CONDITIONAL`. Isto evita declarar como obrigatório aquilo que só seria
   exigido em outra especialidade.
3. Itens facultativos por desdobramento (ex.: Livro de Substabelecimentos
   como desdobramento do Livro de Procurações) entram como
   `LIVRO_FACULTATIVO_DESDOBRAMENTO`, com `OPTIONAL`.
4. Quando o Código permite arquivamento eletrônico ou físico
   alternativamente, o formato esperado é `PHYSICAL_OR_ELECTRONIC`. Quando
   exige a manutenção do físico mesmo havendo eletrônico, é `HYBRID`.
5. Itens cuja interpretação demanda apoio jurídico-correicional recebem
   `PENDING_NORMATIVE_REVIEW` e `Revisão humana = SIM`. Estes itens **não**
   alimentam relatórios automáticos sem revisão.
6. A matriz não cobre, intencionalmente, item por item, todos os
   classificadores de Registro de Imóveis (REURB, usucapião, alienação
   fiduciária, parcelamento do solo). O detalhamento por sub-procedimento
   será objeto de Document Registry-1+, com base na utilização real da
   serventia.
7. Itens operacionais de auditoria correicional do Diretor do Foro (ex.:
   formulário de correição) são citados, mas o detalhamento permanece
   a cargo da Corregedoria. A matriz adota o que está no CNPFE-GO sem
   reproduzir conteúdo correicional.

---

## 7. Próximos passos — Document Registry-1

A próxima sprint, ainda não autorizada para implementação, deverá:

1. Validar com revisão humana (jurídica e correicional) a matriz inicial.
2. Decidir se a primeira atribuição efetiva da serventia (Notas + Registro
   Civil de Pessoas Naturais, conforme contratos da INOVA com Engegraph e
   MHR) altera a marcação `CONDITIONAL` de itens de outras especialidades.
3. Especificar o formato do `ExpectedDocument` em código (entidade
   conceitual descrita em
   [`DOCUMENT_REGISTRY_MODULE_CONCEPT.md`](DOCUMENT_REGISTRY_MODULE_CONCEPT.md)).
4. Decidir a convenção definitiva dos prefixos (`DOCMATCH-*`, `DOCGAP-*`)
   para que o `compliance` possa referenciar via referência fraca, conforme
   [`ADR-003-document-registry-ownership.md`](../decisions/ADR-003-document-registry-ownership.md).
5. Definir como a matriz inicial será carregada (seed idempotente,
   inspirado no padrão da Matriz INOVA V1 do `compliance`).
6. Definir os endpoints somente-leitura iniciais (lista, detalhe, busca por
   especialidade) sem alterar nada na fonte de arquivos.

A matriz inicial **não é instalada como código nesta sprint**.

---

## 8. Cuidados de linguagem (obrigatório)

A documentação produzida nesta sprint, e qualquer comunicação futura sobre
a matriz, **não deve**:

- declarar que um documento encontrado comprova conformidade;
- usar "conforme", "aprovado", "certificado", "validado", "regular",
  "cumprido" ou "validado como conforme" para descrever um achado, salvo
  em texto que esteja explicitamente proibindo o uso desses termos;
- afirmar que a matriz é exaustiva;
- afirmar que o módulo `document_registry`, mesmo após implementado,
  substitui revisão humana.

A documentação **deve** preferir:

- "documento esperado";
- "candidato encontrado";
- "possível correspondência";
- "lacuna documental";
- "exige revisão humana";
- "evidência candidata";
- "referência normativa";
- "status operacional";
- "sinalização indicativa";
- "matriz normativa inicial";
- "não substitui validação documental";
- "não representa declaração automática de conformidade";
- "depende de revisão humana".

---

## 9. Relação com os demais módulos

A matriz, e o futuro `document_registry`, integram-se aos módulos existentes
exclusivamente por **referência fraca** (ver
[ADR-002](../decisions/ADR-002-weak-references-between-regulatory-modules.md)
e [ADR-003](../decisions/ADR-003-document-registry-ownership.md)).

```
audit  →  encontra arquivos, pastas, metadados, duplicidades, localização inadequada
            │
            ▼
document_registry  →  compara com a matriz; produz DOCMATCH / DOCGAP / status operacional
            │
            ├─→ retention   →  consulta para aplicar temporalidade (Provimento 50)
            │
            ├─→ lgpd        →  consulta para avaliar privacidade do conteúdo (quando aplicável)
            │
            └─→ compliance  →  consulta lacunas e correspondências como evidência candidata
                                 sem declarar conformidade automática
```

Diretrizes:

1. `document_registry` **não** importa modelos de `audit`, `compliance`,
   `lgpd`, `retention`. A integração ocorre por referência fraca.
2. `compliance` **não** se torna dono da matriz. Ele apenas consulta o
   `document_registry` por `source_module="document_registry"` +
   `source_type="expected_document_match"` ou
   `"missing_expected_document"`.
3. `retention` aplica suas regras a itens que tenham natureza documental,
   usando a matriz como referência conceitual de tipo de documento. Não há
   relação de domínio inversa.
4. `lgpd` é consultado quando o conteúdo do candidato encontrado contiver
   dados pessoais. A análise de privacidade **não** ocorre no
   `document_registry`.

---

## 10. Limitações desta sprint (Document Registry-0)

Esta sprint **não**:

- implementa código;
- cria tabelas;
- cria endpoints;
- cria migrations;
- move arquivos;
- renomeia arquivos;
- deleta arquivos;
- lê conteúdo sensível de forma automática;
- declara documento como evidência definitiva;
- declara conformidade;
- substitui revisão humana;
- substitui análise jurídica, administrativa ou correicional.

Esta sprint produz **apenas documentação** e **não realiza commit**.
