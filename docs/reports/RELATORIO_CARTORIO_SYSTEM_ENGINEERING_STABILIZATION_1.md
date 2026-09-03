# Relatório — Estabilização de Engenharia do Cartório System

> Sprint **CARTORIO-SYSTEM-ENGINEERING-STABILIZATION-1** — executada em **2026-09-03**.
> Relatório autoritativo de entrada:
> [`RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md`](RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md).
> Sprint sem nova funcionalidade: nenhuma regra de negócio, schema funcional ou
> comportamento foi alterado. Os 903 testes verdes foram preservados em todas as etapas.

---

## 1. Veredito

```
CARTORIO_SYSTEM_ENGINEERING_STABILIZED
```

Todos os objetivos da sprint foram atingidos, incluindo o único que o escopo
admitia como possivelmente inalcançável (`alembic check`), obtido **sem migration
nova** e apenas por alinhamento das declarações ORM.

O gestor autorizou explicitamente a publicação ao final da sprint. Os **10
commits** foram publicados e `origin/main` convergiu com o HEAD local. O CI
**executou pela primeira vez na história do repositório** — falhou na primeira
tentativa, teve a causa-raiz identificada e corrigida, e ficou **verde em todos
os quatro gates** na segunda.

Por isso o veredito não é `..._STABILIZED_WITH_ALEMBIC_EXCEPTION` (não há exceção
de Alembic: o gate ficou verde) nem `..._STABILIZATION_BLOCKED` (nada permaneceu
bloqueado). O repositório está estabilizado **e publicado, com gate automático
comprovadamente funcional** — não apenas escrito.

### Placar da sprint

| Objetivo | Resultado |
|---|---|
| Salvaguarda dos commits locais | 🟢 Delta auditado, push **autorizado e executado**; `origin/main` convergido |
| Primeira execução do CI | 🟢 Verde na 2ª tentativa; falha da 1ª diagnosticada e corrigida |
| Correção do relatório de rebaseline | 🟢 4 inconsistências factuais corrigidas |
| Declaração do PyYAML | 🟢 TD-23 encerrada |
| `ruff format` como gate | 🟢 TD-25 encerrada — 25 arquivos, AST idêntica |
| `alembic check` verde | 🟢 TD-24 encerrada — sem migration nova |
| CI mínimo | 🟢 TD-09 encerrada |
| POP incorporado | 🟢 TD-27 encerrada — 17/17 links resolvem |
| Reconciliação documental | 🟢 TD-01, TD-02, TD-03, TD-04, TD-11, TD-16 encerradas |
| Preservação dos 903 testes | 🟢 903 passed, 1 skipped — inalterado em todas as etapas |

---

## 2. Baseline Git

### 2.1. Estado no início da sprint

| Item | Valor |
|---|---|
| Branch | `main` |
| HEAD | `dd5b3be5de65e86f27b04dd18a8b8dee207b1584` |
| `origin/main` | `6ed62cb2c9f62d3eb69331007e4a3894094fda0e` |
| Ahead / behind | **2 / 0** |
| Staged | *(vazio)* |
| Unstaged | *(vazio)* |
| Untracked | `docs/modules/notas_inventarios/` · `docs/reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md` |

```
git log -5 --oneline
dd5b3be docs(proad): consolidate IERI and SIG-RI response package
a0f96ca docs(audit): add repository rebaseline assessment
6ed62cb docs(knowledge_base): add governance blueprint and Phase 1 allowlist
ff09613 fix(notas): render ODT clauses as body text
a59df6f feat(notas): export inventory minuta to ODT
```

O estado real conferiu com o histórico esperado — mas foi **verificado, não
presumido**, conforme exigido pelo escopo. Os dois arquivos untracked previstos
estavam presentes.

---

## 3. Publicação dos commits anteriores

### 3.1. Auditoria do delta `origin/main..HEAD`

Os commits `a0f96ca` (rebaseline de julho) e `dd5b3be` (pacote PROAD consolidado)
foram auditados **antes** de qualquer alteração:

| Verificação | Resultado |
|---|---|
| Arquivos no delta | **23** |
| Linhas adicionadas | 1.657 |
| Extensões | 21 `.md` + 2 `.csv` |
| Todos sob `docs/`? | ✅ **100%** |
| `_local_data/` | ✅ ausente |
| `.env` / credenciais / tokens | ✅ ausente |
| Bancos (`.db`, `.sqlite`, `.duckdb`, `.dump`) | ✅ ausente |
| Temporários (`.ai_tmp`, `/tmp`) | ✅ ausente |
| Padrão de CPF (`000.000.000-00`) | ✅ 0 ocorrências |
| Padrão de CNPJ | ✅ 0 ocorrências |
| `password` / `senha:` / `api_key` / `secret` / `token:` | ✅ 0 ocorrências |
| Chave privada (`BEGIN RSA/OPENSSH/PRIVATE`) | ✅ 0 ocorrências |

**Lista exata dos 23 arquivos:**

```
A  docs/audits/repository_rebaseline_2026_07/00_SUMARIO_EXECUTIVO.md
A  docs/audits/repository_rebaseline_2026_07/01_INVENTARIO_REPOSITORIO.md
A  docs/audits/repository_rebaseline_2026_07/02_DIAGNOSTICO_ARQUITETURAL.md
A  docs/audits/repository_rebaseline_2026_07/03_GOVERNANCA_DOCUMENTAL.md
A  docs/audits/repository_rebaseline_2026_07/04_REGISTRO_DIVIDA_TECNICA.md
A  docs/audits/repository_rebaseline_2026_07/05_BLUEPRINT_REPOSITORIO_ALVO.md
A  docs/audits/repository_rebaseline_2026_07/06_ROADMAP_RECONCILIADO.md
A  docs/audits/repository_rebaseline_2026_07/07_PLANO_PROXIMAS_SPRINTS.md
A  docs/audits/repository_rebaseline_2026_07/inventory_files.csv
A  docs/audits/repository_rebaseline_2026_07/technical_debt_register.csv
M  docs/proad/RESPOSTA_PROAD_ADEQUACAO_PROVIMENTO_213.md
M  docs/proad/resposta_ieri_2026/00_README_CONTROLE_DOCUMENTAL.md
M  docs/proad/resposta_ieri_2026/01_relatorio_analitico_preliminar.md
M  docs/proad/resposta_ieri_2026/02_minuta_manifestacao_proad.md
M  docs/proad/resposta_ieri_2026/03_plano_acao_ieri_sig_ri.md
M  docs/proad/resposta_ieri_2026/04_minuta_portaria_designacao_ri.md
M  docs/proad/resposta_ieri_2026/05_pop_ri_001_alimentacao_ieri_sig_ri.md
M  docs/proad/resposta_ieri_2026/06_diagnostico_inicial_historico.md
M  docs/proad/resposta_ieri_2026/07_matriz_evidencias_controles.md
M  docs/proad/resposta_ieri_2026/08_checklist_juntada.md
M  docs/proad/resposta_ieri_2026/09_pendencias_alertas.md
M  docs/proad/resposta_ieri_2026/10_analise_manuais_ri_digital.md
A  docs/proad/resposta_ieri_2026/11_relatorio_parcial_atualizacao_ieri_sig_ri.md
```

**Conclusão da auditoria: o delta é seguro para publicação.**

### 3.2. Push — AUTORIZADO e EXECUTADO

O escopo condicionou o push a autorização explícita do gestor. A sprint foi
conduzida até o fim **sem push**, conforme a política permanente (CLAUDE.md § 6),
e a autorização foi solicitada ao término, com o delta já auditado. **O gestor
autorizou a publicação.**

```
git push origin main
To https://github.com/jlrcte-dev/cartorio-system.git
   6ed62cb..a3a28ea  main -> main
```

**Convergência comprovada nas três fontes:**

| Fonte | Valor |
|---|---|
| `git rev-parse HEAD` | `a3a28ea…` |
| `git rev-parse origin/main` | `a3a28ea…` |
| `git ls-remote origin refs/heads/main` | `a3a28ea…` |
| `git rev-list --left-right --count origin/main...HEAD` | `0  0` |

Um segundo push publicou a correção do CI descrita no § 8.2
(`a3a28ea..3200980`). **Risco RS-1 eliminado:** o dossiê PROAD, a auditoria de
julho e toda a estabilização deixaram de existir em uma única máquina.

---

## 4. Correção do relatório de rebaseline

Quatro inconsistências factuais internas foram corrigidas **antes** da
incorporação do relatório ao controle de versão. O diagnóstico, as evidências e
as recomendações permanecem inalterados; nada foi reescrito por estilo.

| # | Local | Problema | Correção |
|---|---|---|---|
| 1 | § 1 — leitura do veredito | Afirmava que as pendências eram "de cintura de engenharia e governança, **não de produto**", contradizendo o próprio § 12, que comprova quatro gaps funcionais em `notas/inventarios` | Passou a distinguir explicitamente **duas naturezas** de pendência: engenharia/governança e funcionais do módulo de valor (precisão percentual, fração ideal, saída fragmentada, texto limpo para Engegraph), com a ressalva de que nenhuma é dispensável |
| 2 | § 9.2 — cabeçalho | Declarava "4 achados novos (**TD-23 a TD-26**)"; a tabela contém 5 (TD-23 a TD-27) | Corrigido para 5 achados novos, 27 linhas ao todo |
| 3 | § 9.3 — síntese | Declarava **P2 = 11**; a lista da própria linha tinha 13 itens e a tabela do § 9.2 confirma 13. Recontagem programática: 5 células P1 (4 abertas + TD-05 resolvida), 13 P2, 6 P3, 3 P4 | **P2 = 13**; adicionadas linhas de total (26 abertas) e de TD-05 resolvida; incluída ressalva sobre o significado da linha P0 |
| 4 | § 5.2, § 8 e § 8.1 — contagem de testes | Compliance registrado como **198 testes (21,9%)**; a coleta real é **213 (23,6%)**. Com o valor errado, a tabela do § 5.2 somava 889 em vez de 904 | Corrigido nos 4 pontos; a soma agora fecha **exatamente em 904** |

O § 21.5 foi atualizado para refletir o `git status` real ao término da sprint
anterior (dois arquivos untracked, não um), e uma nota de rastreabilidade foi
adicionada ao próprio relatório registrando estas correções e sua data.

> A inconsistência nº 4 não constava do escopo desta sprint — foi descoberta ao
> conferir a coleta de testes para atualizar `docs/quality/testing.md`. Corrigi-la
> era necessário para não propagar o número errado ao documento de qualidade.

---

## 5. Dependência PyYAML

### 5.1. Confirmação

| Verificação | Resultado |
|---|---|
| `import yaml` em `app/` | `app/modules/notas/inventarios/infrastructure/loaders.py:22` |
| Declarada em `[project].dependencies` | ❌ ausente |
| Declarada em `[project.optional-dependencies].dev` | ❌ ausente |
| Presente no venv | ✅ 6.0.3 (transitivamente, por acaso) |

Varredura completa dos imports de terceiros em `app/` — `fastapi`, `pydantic`,
`pydantic_settings`, `sqlalchemy`, `yaml` — confirmou que **`yaml` era o único
não declarado**.

### 5.2. Correção

```toml
dependencies = [
    ...
    "python-multipart>=0.0.9",
    # Runtime do módulo notas/inventarios: loaders.py desserializa a entrada YAML.
    "pyyaml>=6.0",
]
```

Versão mínima `>=6.0` — compatível com a instalada (6.0.3) e sem forçar
atualização. **Nenhuma outra dependência foi adicionada ou atualizada. Nenhum
lockfile foi gerado.**

### 5.3. Verificação funcional

```
PyYAML instalado: 6.0.3
YAML carregado OK -> inventario_extrajudicial | herdeiros: 2 | bens: 2
YAML carregado OK -> inventario_extrajudicial | herdeiros: 3 | bens: 2
dependencies = [..., 'pyyaml>=6.0']
OK: PyYAML declarado como dependência produtiva
```

`load_inventario()` executado sobre os dois exemplos canônicos, e o contrato
relido do `pyproject.toml`. A partir de agora, uma instalação limpa a partir do
contrato declarado não depende de pacote presente por acaso — e o CI quebra se
essa regressão voltar.

---

## 6. Formatação

### 6.1. Baseline

`ruff format --check .` reprovava **25 de 147 arquivos** (`ruff check` já estava
limpo). Distribuição: 4 em `app/`, 2 migrations, 7 scripts do pipeline RI e 12
testes.

### 6.2. Prova de que a transformação é puramente textual

Antes de aplicar, a AST de cada um dos 25 arquivos foi capturada
(`ast.dump(tree, include_attributes=False)` → SHA-256). Após a formatação, a
comparação:

```
Arquivos comparados: 25
AST DIVERGENTE: 0
VEREDITO: PURAMENTE TEXTUAL — nenhuma alteração semântica
```

Isso cobre a exigência específica do escopo quanto às duas migrations antigas
(`20260506_1600`, `20260507_1000`): a transformação foi apenas de quebra de linha
e vírgulas finais, sem qualquer mudança de operação de schema.

### 6.3. Resultado

| Verificação | Antes | Depois |
|---|---|---|
| `ruff format --check` | 25 reprovados | ✅ 147 conformes |
| `ruff check` | limpo | ✅ limpo |
| `pytest` | 903 passed, 1 skipped | ✅ 903 passed, 1 skipped |
| `git diff --check` | — | ✅ sem problemas de whitespace |
| Diff | — | 25 arquivos, +1.437 / −931 |

O commit é **isolado**: não acompanha mudança de dependência, CI, documentação
ou lógica.

---

## 7. `alembic check`

### 7.1. Diagnóstico

`alembic check` reprovava com **6 operações**. Comparando modelo, migration e
DDL real do SQLite, a divergência era de **representação**, não de semântica — a
unicidade sempre existiu no banco:

| Coluna | O modelo declarava | O que a migration criou | Unicidade no banco |
|---|---|---|---|
| `compliance_requirements.code` | `unique=True, index=True` → só índice único `ix_*` | `UniqueConstraint` nomeada `uq_*` **+** índice único `ix_*` | ✅ existia |
| `compliance_policies.code` | idem | idem | ✅ existia |
| `compliance_seed_meta.seed_name` | idem | idem | ✅ existia |
| `lgpd_actions.action_code` | idem | `UniqueConstraint` nomeada `uq_*` **+** índice **não** único `ix_*` | ✅ existia |

### 7.2. Solução — apenas declarações ORM

- Adicionada `UniqueConstraint` nomeada ao `__table_args__` dos três modelos de
  compliance, mantendo `unique=True` na coluna.
- Em `LgpdAction`: adicionada a `UniqueConstraint` nomeada e removido
  `unique=True` da coluna, deixando o índice não único — **exatamente** como a
  migration criou.
- Importação de `UniqueConstraint` adicionada a `app/modules/lgpd/models.py`.

**Nenhuma migration nova. Nenhuma tabela recriada. Nenhuma operação destrutiva.
Nenhum filtro genérico de autogenerate** (`include_object`/`include_name` não
foram tocados — mascarar o problema era explicitamente vedado).

### 7.3. Prova de que a unicidade foi preservada

Comparação entre o DDL gerado por `Base.metadata` e o DDL real do SQLite:

```
COLUNA                                 ORM: UQ  ORM: idx único | BANCO: UQ  BANCO: idx único
----------------------------------------------------------------------------------------
OK compliance_policies.code            True     True           | True       True
OK compliance_requirements.code        True     True           | True       True
OK compliance_seed_meta.seed_name      True     True           | True       True
OK lgpd_actions.action_code            True     False          | True       False

Unicidade garantida no ORM em todas as 4 colunas: True
```

A constraint `uq_*` está presente nas quatro colunas, e a cardinalidade dos
índices bate exatamente com a do banco.

### 7.4. Resultado

```
alembic heads   -> f4a5b6c7d8e9 (head)     # head único
alembic current -> f4a5b6c7d8e9 (head)     # banco de dev no head
alembic check   -> No new upgrade operations detected.
```

Validação adicional: a cadeia completa foi aplicada **do zero** em banco
temporário (`<base>` → head) e o `check` também ficou verde ali — ou seja, o
alinhamento vale para um banco recém-migrado, não apenas para o banco de
desenvolvimento existente. O `cartorio.db` teve o mtime conferido antes e depois:
**inalterado**.

---

## 8. CI criado

Arquivo: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

| Aspecto | Decisão |
|---|---|
| Gatilhos | `push` e `pull_request` em `main`, mais `workflow_dispatch` |
| Runner | `ubuntu-latest`, timeout de 15 min |
| Permissões | `contents: read` (mínimo necessário) |
| Python | 3.12, com cache de pip ancorado em `pyproject.toml` |
| Instalação | `pip install -e ".[dev]"` — a partir do contrato declarado, sem requirements paralelo |
| Gates | `ruff format --check .` · `ruff check .` · `pytest -q` · `alembic upgrade head` + `current` + `heads` + `check` |

**Hermetismo do gate de migrations:** `DATABASE_URL` aponta para
`sqlite:///./ci_alembic_check.db`, criado do zero na execução e removido ao
final. Como proteção explícita, o passo **aborta** se `cartorio.db` estiver
presente no runner:

```bash
test ! -f cartorio.db || { echo "cartorio.db presente no runner — abortando"; exit 1; }
```

O banco de desenvolvimento é gitignorado e nunca chega ao CI; a verificação
transforma isso de premissa em garantia.

**Fora de escopo por decisão explícita:** `bandit`, `pip-audit`, `gitleaks` e
`mypy`. Continuam exigidos pelo CLAUDE.md § 5 para mudanças sensíveis e
permanecem como **TD-10**, para sprint própria.

### 8.1. Primeira execução — falhou

Publicado o workflow, o CI disparou pela primeira vez na história do repositório
(run `33711644836`) e **falhou no passo de formatação**:

```
✓ Set up job
✓ Checkout
✓ Configurar Python 3.12
✓ Instalar o projeto (runtime + dev)
X Formatação (ruff format)          <- falha
- Lint · Testes · Migrations         (não executados)
```

O CI reprovou `docs/analysis/lgpd_domain_model.md` e outros documentos —
arquivos que **nunca fizeram parte** do baseline de formatação desta sprint.

### 8.2. Causa-raiz — e não era a que eu previa

O relatório registrava como risco RS-2 uma provável divergência de EOL entre
Linux e Windows. **Não era isso.** A causa foi o piso aberto do contrato de
dependências:

| Ambiente | ruff instalado |
|---|---|
| Máquina de desenvolvimento | **0.15.12** |
| Runner do CI (`ruff>=0.5.0` resolvido para o mais recente) | **0.16.5** |

A partir da 0.16, o formatador do ruff passou a processar **blocos de código
Python dentro de arquivos Markdown**. O gate local, com 0.15, jamais tocava
documentação; o gate do CI, com 0.16, passou a exigir formatação de trechos
ilustrativos dentro dos documentos.

O problema de fundo é mais sério que os arquivos em si: **o ruff é o gate de
formatação**, então um piso aberto permite que "verde na máquina" e "verde no
CI" divirjam sem nenhuma mudança de código — exatamente o que o CI deveria
impedir.

### 8.3. Correção

Commit `3200980` — a faixa passou de `ruff>=0.5.0` para **`ruff>=0.15.0,<0.16`**,
a versão contra a qual o baseline de formatação foi efetivamente validado.

Optou-se por **fixar a faixa** em vez de reformatar a documentação porque:
(a) formatar código ilustrativo dentro de docs altera conteúdo documental, fora
do escopo desta sprint; (b) subir de faixa deve ser decisão deliberada,
acompanhada da reformatação correspondente; (c) a mudança mínima eficaz aqui é
tornar o gate determinístico, não expandir seu alcance.

### 8.4. Segunda execução — verde

Run `33711774766`, todos os passos aprovados em 39 s:

```
✓ Formatação (ruff format)        -> 147 files already formatted
✓ Lint (ruff check)               -> All checks passed!
✓ Testes (pytest)                 -> 904 passed, 2 warnings in 14.45s
✓ Migrations (banco temporário)   -> No new upgrade operations detected.
```

**Duas observações factuais dessa execução:**

1. **O CI roda 904 testes passando, contra 903 + 1 skip na máquina local.** Não
   é divergência: o único skip é o `chmod` do `test_file_scanner.py`, condicional
   ao Windows sem privilégios de administrador. **No Linux ele executa** — ou
   seja, a partir de agora esse teste tem cobertura real, que localmente nunca
   teve.
2. **Dois warnings aparecem só no CI**, vindos de versões mais novas resolvidas
   no runner (starlette 1.6.0 contra 1.0.0 local): `StarletteDeprecationWarning`
   sobre `httpx` no `testclient` e `DeprecationWarning` do alias
   `anyio.abc.BlockingPortal`. **Nenhum vem de código do projeto** — são sinais
   antecipados de deriva de dependências, a acompanhar, não defeitos a corrigir
   agora.

Anotação recorrente do runner: `actions/checkout@v4` e `actions/setup-python@v5`
apontam para Node.js 20, já depreciado, e são forçados a rodar em Node.js 24.
Não afeta o resultado; atualizar as actions fica como manutenção futura.

---

## 9. Documentação reconciliada

### 9.1. `docs/roadmap.md` — declarado autoritativo

- Cabeçalho declara explicitamente: **ROADMAP GERAL AUTORITATIVO**; os 5
  roadmaps de domínio passam a ser formalmente **subordinados**, com regra de
  precedência escrita (o geral prevalece quanto à prioridade; o de domínio,
  quanto ao detalhe interno da sua área). Encerra **TD-16**.
- Sprint 3 deixou de ser marcada como "🟡 próxima" — está concluída desde
  2026-05-04, com nota de correção registrando o erro anterior. Encerra **TD-02**.
- Adicionada tabela de estado atual por módulo, com a coluna decisiva **"uso real
  observado"**.
- Passam a constar as sprints de `notas/inventarios` e o pipeline RI, executadas
  em maio–junho/2026 **sem nunca aparecerem no roadmap** — com registro explícito
  dessa omissão.
- Apenas três horizontes (A concluído, B próximo, C futuro). Planejamento
  detalhado de longo prazo foi deliberadamente evitado.
- Novo princípio de evolução nº 7: nenhuma sprint entra no repositório sem
  constar do roadmap.

### 9.2. `docs/architecture.md` — alinhado ao código

- Removida a afirmação de que `finance` é o único módulo ativo. Encerra **TD-01**.
- Árvore de diretórios reescrita com os 7 módulos reais, os três submódulos de
  `audit`, o layout hexagonal de `notas/inventarios`, `scripts/local_tools/`,
  `tests/golden/` e o workflow de CI.
- Documentados os **dois padrões de layout** (flat × hexagonal) e o fato de que
  a escolha ainda não é governada por ADR.
- Registrado que nem todo módulo expõe HTTP e que **a API não tem autenticação**,
  com a autoria por default literal `"gestor"` (decisão D-08).
- Registrada a única dependência cruzada existente (`audit/diagnosis → retention`).
- Nova seção sobre o pipeline RI declarando seu status arquitetural com
  honestidade: *"essa localização é um fato, não uma decisão registrada"* —
  DH-1 permanece em aberto, **sem decidir a promoção**, como exigido pelo escopo.

### 9.3. `docs/quality/testing.md` — números reais com data

- "48 testes em 3 arquivos" → **904 coletados em 38 arquivos** (903 + 1 skip),
  com **data de baseline explícita** e a ressalva de que a contagem não é
  contrato. Encerra **TD-11**.
- Nova distribuição por área, conferida por coleta real.
- A seção "Cobertura por área (resumo das 48 asserções)" — 58 linhas enumerando
  apenas asserções do Finance da Etapa 1.2 — foi substituída por uma tabela de
  **intenção por área**, que não envelhece a cada sprint.
- Documentados os golden files e a razão do `eol=lf` no `.gitattributes`.
- **Instrução perigosa removida:** a seção de round-trip mandava `rm -f
  cartorio.db`. Substituída por procedimento em banco temporário via
  `DATABASE_URL`, com aviso explícito.
- Nova lacuna registrada: *"testes verdes não significam uso comprovado"* —
  compliance, retention, findings e finance têm suíte extensa e nenhum dado real.

### 9.4. Índices — `docs/README.md` e `docs/decisions/index.md`

- `docs/README.md`: adicionados `notas_inventarios`, o checklist humano, o POP,
  `registro_imoveis`, o dicionário sanitizado do RI, os diretórios `proad/` e
  `ai/`, a pasta `audits/` e os dois relatórios de setembro.
- `docs/decisions/index.md`: **ADR-009 adicionada** (estava ausente do índice).
- Encerram **TD-04**.

### 9.5. `CLAUDE.md`

- § 5: comandos alinhados ao que o CI executa (inclui `ruff format --check` e
  `alembic check`); `alembic upgrade head` passou a usar banco temporário.
  Adicionada nota de estado das ferramentas — `mypy`, `bandit`, `pip-audit` e
  `gitleaks` **não estão instalados**, a exigência continua válida mas hoje não é
  executável (TD-10), e nesse intervalo mudanças sensíveis exigem revisão humana
  explícita.
- § 9: tabela de 5 módulos substituída por mapa real de 12 linhas, com interface
  e estado de cada um, incluindo `notas/inventarios`, o pipeline RI, os
  placeholders e o que não foi iniciado.
- **As proibições permanentes da § 2 não foram tocadas.** Confirmado por
  inspeção do diff.

### 9.6. Referências órfãs a `docs/operations/engegraph.md`

O arquivo **nunca existiu**. O escopo vedava criá-lo apenas para satisfazer
links, então as três referências foram **redirecionadas para documentos reais**:

| Origem | Destino novo |
|---|---|
| `docs/architecture.md` | Tabela apontando para `infrastructure/infrastructure_roadmap.md`, `infrastructure/target_infrastructure.md` e `modules/audit.md`, com nota explicando que o arquivo nunca existiu |
| `docs/modules/audit.md` | `infrastructure/infrastructure_roadmap.md` |
| `docs/quality/risk_register_model.md` | Payload de exemplo passou a citar `infrastructure/infrastructure_roadmap.md` |

Encerra **TD-03**.

### 9.7. `README.md` (raiz)

Não constava da lista do escopo, mas afirmava que "o foco principal é o Módulo de
Auditoria" — o que criaria **nova contradição** com o roadmap recém-declarado
autoritativo. Ajuste mínimo: seção "Por onde começar" com 4 ponteiros, seção
"Duas frentes ativas" (notas em uso real + eixo regulatório), árvore de projeto
atualizada e comandos de validação alinhados ao CI.

### 9.8. Verificação de links

Varredura automatizada dos links relativos dos 9 documentos guarda-chuva:
**122 links verificados, 0 quebrados.**

---

## 10. POP de Inventários incorporado

Arquivo:
[`docs/modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md`](../modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md)
(675 linhas), untracked desde a sprint REB-A0/A1 por conter dois links quebrados.

**O documento não foi reescrito.** Única alteração — os dois links para a ADR-009:

| Linha | Antes | Depois |
|---|---|---|
| 332 | `](../decisions/ADR-009-…)` | `](../../decisions/ADR-009-…)` |
| 560 | `](../decisions/ADR-009-…)` | `](../../decisions/ADR-009-…)` |

O erro vinha de o arquivo estar um nível mais fundo (`docs/modules/notas_inventarios/`),
fazendo `../decisions/` resolver para `docs/modules/decisions/`, inexistente.

**Validação de todos os links relativos do POP:**

```
Links relativos verificados: 17
OK: 17
QUEBRADOS: 0
VEREDITO: TODOS OS LINKS RELATIVOS RESOLVEM
```

Encerra **TD-27**. O documento passa a ser versionado.

---

## 11. Quality gate final

| Gate | Comando | Resultado |
|---|---|---|
| Formatação | `ruff format --check .` | 🟢 **147 files already formatted** |
| Lint | `ruff check .` | 🟢 **All checks passed!** |
| Testes | `pytest -q` | 🟢 **903 passed, 1 skipped** |
| Head Alembic | `alembic heads` | 🟢 **f4a5b6c7d8e9 (head)** — único |
| Estado do banco | `alembic current` | 🟢 **f4a5b6c7d8e9 (head)** |
| Drift | `alembic check` | 🟢 **No new upgrade operations detected.** |

**No CI (Linux), os mesmos gates rodam com resultado equivalente**, com uma
diferença esperada e favorável: **904 passed**, porque o skip de `chmod` é
condicional ao Windows e no runner o teste executa de fato.

**A quantidade de testes não mudou: 904 coletados, 903 passando localmente +
1 skip condicional de plataforma — idêntico ao baseline de entrada.** Nenhum teste foi
adicionado, removido, renomeado ou desativado; esta sprint não alterou regra de
negócio nem comportamento. O gate foi executado após cada etapa (formatação,
PyYAML, alinhamento ORM, CI, documentação), sempre com o mesmo resultado.

---

## 12. Commits

Cinco commits temáticos, com staging **explícito por caminho** — sem `git add .`,
sem `--no-verify`, sem `--force`. `git diff` e `git diff --cached` foram
revisados antes de cada um.

| # | Hash | Mensagem | Arquivos | Dívida |
|---|---|---|---|---|
| 1 | `91d6e18` | `chore: align repository formatting baseline` | 25 (+1.437 / −931) | TD-25 |
| 2 | `90a6578` | `fix: declare notas yaml runtime dependency` | 1 (+2) | TD-23 (P1) |
| 3 | `987627f` | `fix: align orm metadata with migrated uniqueness` | 2 (+21 / −2) | TD-24 |
| 4 | `d47a640` | `ci: add repository quality gate` | 1 (+73, novo) | TD-09 (P1) |
| 5 | `cf99cef` | `docs: reconcile cartorio system current state` | 12 (+3.159 / −282) | TD-01, TD-02, TD-03, TD-04, TD-11, TD-16, TD-27 |

| 6 | `f4f572f` | `docs: correct commit hash in stabilization report` | 1 | — |
| 7 | `a3a28ea` | `docs: correct unpublished commit count in report` | 1 | — |
| 8 | `3200980` | `fix: pin ruff to the version range the gate was validated against` | 1 (+7 / −1) | corrige o CI |

Os commits 6 e 7 corrigem dados que só podiam ser conhecidos depois de escritos
(hash e contagem do próprio relatório). O commit 8 corrige a falha da primeira
execução do CI, descrita no § 8.2.

Nenhum arquivo sensível foi versionado em qualquer um deles.

---

## 13. Estado do `origin`

| Item | Valor |
|---|---|
| `origin/main` no início | `6ed62cb2c9f62d3eb69331007e4a3894094fda0e` |
| `origin/main` ao final | `3200980…` (mais o commit deste relatório) |
| Commits publicados nesta sprint | **10** — 2 anteriores + 8 desta sprint |
| Ahead / behind ao final | **0 / 0** — convergido |
| Push executado | ✅ **Sim**, com autorização explícita do gestor |
| CI executado | ✅ **Sim** — 1ª execução falhou, 2ª **verde** nos 4 gates |
| Runs | `33711644836` (failure) · `33711774766` (**success**, 39 s) |

---

## 14. Dívidas encerradas

| ID | Dívida | Prio. | Como foi encerrada |
|---|---|:--:|---|
| **TD-23** | PyYAML importada e não declarada | **P1** | Declarada em `[project].dependencies`; carga YAML verificada |
| **TD-09** | Ausência total de CI | **P1** | `.github/workflows/ci.yml` com 4 gates |
| **TD-01** | `architecture.md` contradiz o código | **P1** | Reescrito com os 7 módulos reais, layouts, isolamento e ausência de auth |
| **TD-02** | `roadmap.md` defasado | **P1** | Sprint 3 corrigida; estado real; 3 horizontes |
| **TD-24** | `alembic check` reprovando | P2 | Modelos alinhados; gate verde sem migration nova |
| **TD-25** | `ruff format` sem gate | P2 | Adotado como gate; 25 arquivos; AST idêntica |
| **TD-16** | Roadmaps sem hierarquia | P2 | `roadmap.md` declarado autoritativo, com regra de precedência |
| **TD-11** | `testing.md` com 48 testes | P2 | 904 com data de baseline; cobertura por intenção |
| **TD-04** | Índices documentais incompletos | P2 | `docs/README.md` e `decisions/index.md` completados (inclui ADR-009) |
| **TD-03** | Referências a `engegraph.md` inexistente | P2 | 3 referências redirecionadas para documentos reais |
| **TD-27** | POP com links quebrados, fora do git | P3 | 2 links corrigidos; 17/17 validados; versionado |

**Total: 11 dívidas encerradas — todas as 4 P1 abertas, 6 P2 e 1 P3.**

---

## 15. Dívidas remanescentes

Das 26 dívidas abertas registradas no rebaseline, **15 permanecem**, e esta
sprint descobriu **1 nova** (TD-28). Nenhuma é P0 ou P1.

| ID | Dívida | Prio. | Por que não foi tratada aqui |
|---|---|:--:|---|
| **TD-26** | Eixo regulatório construído e nunca ativado | P2 | Ativar seeds é **fora do escopo** desta sprint (§ 14 do escopo) — Horizonte B |
| **TD-06** | Pipeline RI fora da arquitetura | P2 | Depende da decisão humana DH-1 |
| **TD-10** | bandit / pip-audit / gitleaks / mypy ausentes | P2 | Explicitamente fora de escopo; sprint própria |
| **TD-13** | Relatórios sem política de arquivamento | P2 | Exige convenção de status a definir |
| **TD-22** | Backup de `_local_data` fora de governança | P2 | Externo ao repositório; depende de infraestrutura |
| **TD-18** | Autenticação multiusuário | P2 | Fora de escopo; Horizonte C |
| **TD-19** | Trilha de auditoria transversal | P2 | Fora de escopo; Horizonte C |
| **TD-12** | Fonte dupla `renderer.py` × `.j2` | P3 | Decisão DH-3 em aberto |
| **TD-08** | Dois layouts de módulo sem ADR | P3 | Documentado em `architecture.md`; ADR pendente |
| **TD-17** | `audit → retention` sem ADR | P3 | Documentado em `architecture.md`; ADR pendente |
| **TD-14** | Gerador de PDF one-off em `scripts/` | P3 | Depende do blueprint de repositório |
| **TD-15** | EOL indefinido fora de `tests/golden` | P3 | `.gitattributes` sem `text=auto`; mudança gera ruído — melhor isolar em sprint própria |
| **TD-07** | Seis placeholders vazios | P4 | Decisão consciente |
| **TD-20** | Sem task runner unificado | P4 | Melhoria futura |
| **TD-21** | Observabilidade limitada a stdout | P4 | Adequada ao estágio |
| **TD-28** 🆕 | Dependências sem lockfile — CI e máquina local resolvem versões diferentes | P2 | Descoberta pela falha da 1ª execução do CI. Mitigada para `ruff` (fixado); as demais seguem com piso aberto. Adotar lockfile exige decisão explícita, vedada nesta sprint |

**Gaps funcionais de `notas/inventarios`** (precisão percentual, fração ideal,
saída fragmentada, texto limpo para Engegraph) não são dívida técnica e
permanecem como **Horizonte B** do roadmap — explicitamente fora do escopo desta
sprint.

---

## 16. Riscos

| # | Risco | Prob. | Impacto | Situação após a sprint |
|---|---|:--:|:--:|---|
| **RS-1** | Commits em máquina única — dossiê PROAD, auditoria de julho e estabilização | média → **nula** | muito alto | 🟢 **ELIMINADO** — 10 commits publicados; `origin/main` convergido |
| **RS-2** | CI falhar na primeira execução por diferença de ambiente | média | baixo | 🟢 **MATERIALIZOU E FOI RESOLVIDO** — mas pela causa errada: não foi EOL, foi o piso aberto `ruff>=0.5.0` deixando o runner instalar 0.16.5 contra 0.15.12 local (§ 8.2). Corrigido no commit `3200980`; 2ª execução verde |
| **RS-3** | Regressão silenciosa em `main` | alta → baixa | alto | 🟢 **Mitigado e comprovado** — gate verde executando de fato no runner |
| **RS-4** | Instalação limpa quebrar em runtime | média → nula | alto | 🟢 **Eliminado** — TD-23 encerrada |
| **RS-5** | Decisão errada por documentação defasada | alta → baixa | médio | 🟢 **Mitigado** — 6 documentos reconciliados, 122 links verificados |
| **RS-6** | Backup de `_local_data` (582 MB) não confirmado | média | alto | 🔴 **Inalterado** — externo ao repositório (TD-22) |
| **RS-7** | Evidência regulatória envelhecendo (artefatos de maio/2026) | média | médio | 🔴 **Inalterado** — depende de TD-26, Horizonte B |
| **RS-8** | Capacidade construída e nunca validada em uso | média | médio | 🔴 **Inalterado** — depende de TD-26 |
| **RS-9** | 🆕 Deriva de dependências com pisos abertos | média | médio | 🟡 **Parcialmente mitigado** — `ruff` fixado por ser o gate; `pytest`, `fastapi`, `starlette` e outros seguem com piso aberto, e o runner já resolve versões bem mais novas que as locais (starlette 1.6.0 × 1.0.0), produzindo 2 warnings que não aparecem localmente. Um lockfile é a solução estrutural — exige decisão explícita |

---

## 17. Git status final

```
git status --short
(vazio — working tree limpo)
```

| Item | Início | Fim |
|---|---|---|
| HEAD | `dd5b3be` | commit deste relatório, sobre `3200980` |
| `origin/main` | `6ed62cb` | **convergido com o HEAD local** |
| Ahead / behind | 2 / 0 | **0 / 0** |
| Arquivos modificados não commitados | 0 | **0** |
| Arquivos untracked | 2 | **0** |
| Commits publicados | — | **10** |

> Nota de autorreferência: um relatório não pode conter o hash do commit que o
> introduz. Os identificadores citados aqui são os dos commits **anteriores** ao
> desta atualização; o `git log` é sempre a fonte da verdade. Esta seção já
> passou por duas correções (`f4f572f`, `a3a28ea`) justamente por conter dados
> antecipados que não corresponderam à realidade — registro mantido por
> transparência.

**Conformidade com o escopo:**

| Restrição | Cumprida |
|---|:--:|
| Nenhuma funcionalidade nova | ✅ |
| Nenhum redesign | ✅ |
| Nenhuma alteração de regra de negócio | ✅ |
| Nenhuma alteração de schema funcional | ✅ |
| Nenhuma migration nova | ✅ |
| 903 testes preservados | ✅ |
| `_local_data` intocado | ✅ |
| Nenhuma PII reproduzida | ✅ |
| Staging explícito, sem `git add .` | ✅ |
| Sem `--no-verify`, sem `--force` | ✅ |
| Commits pequenos e temáticos | ✅ 5 commits |
| Push somente com autorização | ✅ **executado após autorização explícita** |

---

*Fim do relatório — `CARTORIO-SYSTEM-ENGINEERING-STABILIZATION-1` · 2026-09-03.*
