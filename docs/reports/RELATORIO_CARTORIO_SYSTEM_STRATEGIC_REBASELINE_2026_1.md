# Relatório — Rebaseline Estratégico do Cartório System

> Sprint **CARTORIO-SYSTEM-STRATEGIC-REBASELINE-2026-1** — executada em **2026-09-02**.
> Auditoria **somente-leitura** de `C:\Users\João\Documents\cartorio_system`.
> Baseline histórico a validar: auditoria **CARTORIO-REPOSITORY-REBASELINE-1** (2026-07-09,
> `docs/audits/repository_rebaseline_2026_07/`) — utilizada apenas como referência a
> confirmar, nunca como descrição presumida do estado atual.
> Nenhum código, teste, migration, documento antigo ou dado sensível foi alterado.
> Única escrita desta sprint: **este arquivo**.

---

## 1. Veredito

```
CARTORIO_SYSTEM_HEALTHY_VALUE_CONCENTRATED_IN_NOTAS_STABILIZATION_PENDING
```

**Leitura do veredito em uma frase:** o sistema está tecnicamente saudável e verificável
(903 testes verdes, lint limpo, cadeia de migrations linear, isolamento modular quase
perfeito, zero dados sensíveis versionados), o **valor operacional real está comprovadamente
concentrado em um único módulo** — `notas/inventarios`, com seis casos reais entre
2026-05-23 e 2026-08-29 — e as pendências se distribuem em **duas naturezas distintas**:

- **Pendências de cintura de engenharia e governança** — o que impede a retomada segura:
  ausência total de CI, gate de formatação não aplicado, dependência de runtime não
  declarada, `alembic check` vermelho e documentos guarda-chuva congelados em maio/2026.
- **Pendências funcionais no próprio módulo de valor** — comprovadas por casos reais e
  detalhadas no § 12: perda de precisão na representação percentual (`3,125% → 3,12%`),
  ausência de fração ideal, ausência de saída fragmentada das §§ 10 e 11 e ausência de saída
  em texto limpo para o Engegraph. **Não são hipóteses:** a primeira forçou uma minuta 100%
  manual em 2026-07-09 e as duas últimas foram supridas à mão em todos os casos recentes.

A distinção importa para a priorização: a primeira natureza é pré-requisito de método; a
segunda é o produto propriamente dito. Nenhuma das duas é dispensável.

Os quatro vereditos de formato sugeridos no escopo foram considerados e descartados por
imprecisão factual: `..._COMPLETE` descreveria a sprint, não o sistema;
`..._VALUE_DIRECTION_UNCLEAR` é falso — a direção de valor está clara e é mensurável;
`..._READY_FOR_VALUE_PRIORITIZATION` omite as pendências de estabilização;
`..._STABILIZATION_REQUIRED` isoladamente omite a evidência de valor encontrada.

---

## 2. Executive summary

### O que mudou desde a auditoria de julho/2026

| Fato | Julho/2026 (baseline) | Setembro/2026 (hoje) |
|---|---|---|
| HEAD | `6ed62cb` (2026-05-25) | `dd5b3be` (2026-07-13) |
| Trabalho PROAD | 12 arquivos modificados + 2 untracked, **não commitados** | **Commitado** (`a0f96ca`, `dd5b3be`) — TD-05 resolvida |
| Working tree | 14 arquivos pendentes | **1 arquivo untracked** (POP de notas) |
| Testes | 903 + 1 skip | 903 + 1 skip (**idêntico**) |
| Commits desde então | — | **zero em 51 dias** |
| Uso real do gerador de inventário | 2 casos conhecidos (maio) | **6 casos** (último em 2026-08-29) |
| CI | inexistente | **inexistente** |

### Os cinco fatos que definem o estado atual

1. **O código parou; o uso não.** Não há um único commit desde 2026-07-13, mas há três
   casos reais de inventário processados em agosto/2026 (dias 02, 13 e 29) e um em julho
   (dia 09). O sistema entrou em regime de **operação sem desenvolvimento** — o oposto do
   risco habitual.
2. **O valor está concentrado e é mensurável.** `notas/inventarios` é o único módulo com
   evidência **V4** (uso repetido com benefício observado). Todos os módulos persistentes
   com API REST — finance, audit/findings, compliance, retention — têm **zero linhas** no
   banco de desenvolvimento; apenas `lgpd_actions` (25 linhas, importação única de maio)
   tem dados.
3. **O padrão de uso real difere do produto entregue.** Os três casos de agosto consumiram
   **fragmentos** da minuta (`clausulas_*.md`, §§ 10 e 11) montados a partir da saída
   completa, e o caso de julho produziu um `04_TEXTO_LIMPO_ENGEGRAPH.md` também manual. O
   gerador entrega um documento inteiro; a serventia consome duas cláusulas.
4. **Uma limitação de renderização já forçou rota manual em caso real.** Em 2026-07-09, um
   inventário de veículo com quinhões de 1/32 exigiu minuta manual: `_fmt_pct` trunca
   `3,125%` para `3,12%` e o renderer não grafa frações ideais. Demonstrado nesta auditoria
   (§ 12.4): num cenário de 9 herdeiros, os percentuais exibidos somam **100,04%** enquanto
   a aritmética interna permanece exata.
5. **A cintura de engenharia continua descoberta.** Zero CI, zero hooks, zero cobertura;
   `ruff format --check` reprova **25 arquivos**; `PyYAML` é importado por `app/` mas não
   está declarado no `pyproject.toml`; `alembic check` retorna **FAILED**.

### Recomendação preliminar em uma linha

Uma sprint curta de estabilização (**CI mínimo + declaração de dependência + gate de
formatação + 2 links quebrados do POP**), seguida da frente de maior retorno medido —
**saída fragmentada de cláusulas para o Engegraph** — e só então a correção de precisão de
frações. Autenticação e trilha transversal permanecem corretas como direção estrutural, mas
não são o próximo passo: nenhum uso multiusuário real as demanda hoje.

---

## 3. Baseline Git

### 3.1. Estado autoritativo

| Item | Valor |
|---|---|
| Diretório raiz | `C:\Users\João\Documents\cartorio_system` |
| Branch | `main` |
| HEAD | `dd5b3be5de65e86f27b04dd18a8b8dee207b1584` |
| HEAD — data/autor/assunto | 2026-07-13 15:20:14 −0300 · jlrcte-dev · `docs(proad): consolidate IERI and SIG-RI response package` |
| Remote | `origin` → `https://github.com/jlrcte-dev/cartorio-system.git` |
| `origin/main` | `6ed62cb2c9f62d3eb69331007e4a3894094fda0e` (2026-05-25) |
| Ahead / behind | **2 à frente**, 0 atrás (`git rev-list --left-right --count origin/main...HEAD` → `0  2`) |
| Total de commits | 34 |
| Primeiro commit | `b01c0db` (2026-05-01) — `feat: add finance core v1 with audit hardening` |
| Tags | **nenhuma** |
| Stashes | **nenhum** |
| Branches | `main` (local), `remotes/origin/main`, `remotes/origin/HEAD` |
| Dias desde o último commit | **51** (2026-07-13 → 2026-09-02) |

> **Atenção operacional:** os dois commits mais recentes (`a0f96ca` rebaseline, `dd5b3be`
> pacote PROAD) **existem apenas localmente**. Um push não foi executado — e não será
> executado por esta sprint. Enquanto isso não ocorrer, o dossiê PROAD consolidado e a
> auditoria de julho vivem em uma única máquina, com o mesmo risco de perda que a TD-05
> apontava, apenas deslocado do working tree para o repositório local.

### 3.2. Working tree

```
git status --short
?? docs/modules/notas_inventarios/
```

| Categoria | Conteúdo |
|---|---|
| Staged | *(vazio)* |
| Unstaged | *(vazio)* |
| Untracked | `docs/modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md` (675 linhas) |

**Arquivo pré-existente protegido:** o POP acima **já estava untracked antes desta sprint**
e permanece exatamente como estava. Nenhuma movimentação, correção ou commit foi realizada
sobre ele. É o mesmo arquivo bloqueado na sprint REB-A0/A1 por conter dois links quebrados
(§ 10.3 deste relatório).

### 3.3. Commits desde a auditoria anterior

A auditoria de julho fotografou `HEAD = 6ed62cb`. Desde então, **dois commits**:

| Hash | Data | Assunto | Natureza |
|---|---|---|---|
| `a0f96ca` | 2026-07-13 | `docs(audit): add repository rebaseline assessment` | Salvaguarda: preserva a própria auditoria (REB-A0) |
| `dd5b3be` | 2026-07-13 | `docs(proad): consolidate IERI and SIG-RI response package` | Salvaguarda: commita o dossiê PROAD (REB-A1) |

**Nenhum commit de código desde 2026-05-25** (`6ed62cb`). O último commit que tocou `app/`
foi `ff09613` (2026-05-22, `fix(notas): render ODT clauses as body text`).

### 3.4. Histórico relevante

| Hash | Data | Assunto |
|---|---|---|
| `dd5b3be` | 2026-07-13 | docs(proad): consolidate IERI and SIG-RI response package |
| `a0f96ca` | 2026-07-13 | docs(audit): add repository rebaseline assessment |
| `6ed62cb` | 2026-05-25 | docs(knowledge_base): add governance blueprint and Phase 1 allowlist |
| `ff09613` | 2026-05-22 | fix(notas): render ODT clauses as body text |
| `a59df6f` | 2026-05-22 | feat(notas): export inventory minuta to ODT |
| `c1e2bb1` | 2026-05-22 | feat(notas): add pydantic input schema and golden regression tests |
| `e8fe4cc` | 2026-05-21 | feat(notas): mature inventory minuta with checklist |
| `47956cc` | 2026-05-21 | feat(notas): render inventory minuta-base in Markdown |
| `308699f` | 2026-05-21 | docs(decisions): add ADR-009 inventory cent rounding policy |
| `e4a2dea` | 2026-05-20 | feat(notas): add inventory calculation module |
| `c3ab90d` | 2026-05-18 | docs(proad): consolidate IERI SIG-RI response documents |
| `8005a02` | 2026-05-17 | docs(ai): document AI governance investigation and architecture ADRs |
| `cdd6650` | 2026-05-16 | docs: structure PROAD/IERI evidence base and RI module pipeline |
| `8ca05f2` | 2026-05-08 | docs: reorganize documentation structure by domain |
| `d782013` | 2026-05-07 | feat(compliance): add requirement status indicative |
| `c588bc2` | 2026-05-06 | feat(compliance): add requirement finding links |
| `4ccf50c` | 2026-05-06 | feat(compliance): add compliance evidence MVP |
| `fc5ef6e` | 2026-05-06 | feat(compliance): add INOVA matriz V1 read-only foundation module |
| `646b59b` | 2026-05-06 | feat(retention): add document temporalidade rules and diagnosis integration |
| `ebade5d` | 2026-05-05 | feat(lgpd): add action tracking module |
| `441a33e` | 2026-05-05 | feat(audit): calibrate DocumentDiagnosis rules after real validation |
| `2e329e0` | 2026-05-04 | feat: implement DocumentDiagnosis Core v1 (Sprint 3) with 7 diagnosis rules |
| `e2f616e` | 2026-05-04 | feat(audit): implement read-only audit foundation |
| `b01c0db` | 2026-05-01 | feat: add finance core v1 with audit hardening |

*(commits intermediários exclusivamente documentais omitidos; log completo via `git log`.)*

**Observação de ritmo:** todo o código do sistema foi escrito em **22 dias** (2026-05-01 a
2026-05-22). Os 103 dias seguintes foram exclusivamente documentais e operacionais.

---

## 4. Baseline do ambiente

### 4.1. Runtime e gerenciamento de dependências

| Item | Valor | Observação |
|---|---|---|
| Python (venv) | **3.12.8** | `.venv/Scripts/python.exe` |
| Python (sistema) | 3.12.8 | idêntico |
| `.python-version` | `3.12` | consistente |
| `requires-python` | `>=3.12,<3.13` | pin respeitado |
| Ambiente virtual | `.venv/` na raiz | gitignorado |
| Gerenciador | **pip + setuptools** (`build-backend = setuptools.build_meta`) | instalação editável (`-e`) |
| Lockfile | **inexistente** | não há `requirements.txt`, `poetry.lock`, `uv.lock` ou `pip-tools` |
| Pacote instalado | `cartorio_system @ dd5b3be…` (editable) | pin do egg reflete o HEAD atual |

### 4.2. Bibliotecas centrais (versões efetivamente instaladas)

| Biblioteca | Declarada no `pyproject` | Instalada | Situação |
|---|---|---|---|
| FastAPI | `>=0.115.0` | **0.136.1** | OK |
| SQLAlchemy | `>=2.0.0` | **2.0.49** | OK |
| Alembic | `>=1.13.0` | **1.18.4** | OK |
| Pydantic | `>=2.7.0` | **2.13.3** | OK |
| pydantic-settings | `>=2.3.0` | 2.14.0 | OK |
| uvicorn[standard] | `>=0.30.0` | 0.46.0 | OK |
| python-multipart | `>=0.0.9` | 0.0.27 | OK |
| pytest | `>=8.2.0` (dev) | **9.0.3** | OK |
| pytest-asyncio | `>=0.23.0` (dev) | 1.3.0 | OK |
| httpx | `>=0.27.0` (dev) | 0.28.1 | OK |
| Ruff | `>=0.5.0` (dev) | **0.15.12** | OK |
| **PyYAML** | **NÃO DECLARADA** | 6.0.3 | 🔴 **importada por `app/`** |
| lxml, pdfplumber, PyMuPDF, pypdf, pypdfium2, fpdf2, Pillow, cryptography, defusedxml | NÃO DECLARADAS | instaladas | 🟡 usadas por `scripts/` |

🔴 **Achado P1 (novo — não consta do registro de dívidas de julho):**
`app/modules/notas/inventarios/infrastructure/loaders.py:24` executa `import yaml`. `PyYAML`
não consta em `[project].dependencies` nem em `[project.optional-dependencies].dev`. Uma
instalação limpa a partir do `pyproject.toml` produz um `app/` que **quebra em runtime** ao
carregar qualquer inventário `.yaml` — exatamente o caminho usado nos seis casos reais. O
mesmo vale, com menor gravidade, para as bibliotecas de PDF do pipeline RI.

### 4.3. Automação, hooks e gates

| Item | Situação | Evidência |
|---|---|---|
| CI (GitHub Actions) | 🔴 **inexistente** | diretório `.github/` não existe |
| Outro CI (GitLab, Jenkins, Azure) | 🔴 inexistente | nenhum arquivo de pipeline no repositório |
| `pre-commit` | 🔴 inexistente | `.pre-commit-config.yaml` ausente |
| Git hooks | 🔴 nenhum ativo | `.git/hooks/` contém apenas `*.sample` |
| Task runner (Makefile/justfile) | 🔴 inexistente | comandos vivem só em `docs/operations/how_to_run.md` |
| Cobertura | 🔴 não configurada | `pytest-cov`/`coverage` não instalados; sem `[tool.coverage]` |
| mypy | 🔴 não instalado | CLAUDE.md § 5 o cita como "se configurado" |
| bandit / pip-audit / gitleaks | 🔴 não instalados | CLAUDE.md § 5 os **exige** para mudanças sensíveis |
| Configuração local | `.claude/settings.json`, `.vscode/settings.json` | ambos gitignorados |
| `.gitattributes` | 🟢 presente | fixa `eol=lf` para `tests/golden/notas_inventarios/**` |

**Conclusão da seção:** a qualidade do repositório depende hoje inteiramente de disciplina
manual em uma única máquina. Não existe nenhum mecanismo automático que impeça um commit
vermelho de entrar em `main`.

---

## 5. Quality gate

### 5.1. Resultados executados nesta sprint

| Gate | Comando | Resultado |
|---|---|---|
| Testes | `python -m pytest -q` | 🟢 **903 passed, 1 skipped** |
| Testes (warnings ligados) | `python -m pytest -q -W default` | 🟢 **0 warnings** |
| Lint | `python -m ruff check .` | 🟢 **All checks passed!** |
| Formatação | `python -m ruff format --check .` | 🔴 **25 arquivos seriam reformatados** (122 conformes) |
| Migrations — heads | `python -m alembic heads` | 🟢 `f4a5b6c7d8e9 (head)` — head único |
| Migrations — history | `python -m alembic history` | 🟢 cadeia linear de 10 revisões |
| Migrations — estado do banco | `python -m alembic current` | 🟢 `f4a5b6c7d8e9 (head)` |
| Migrations — drift | `python -m alembic check` | 🔴 **FAILED** — 6 operações detectadas |
| Cobertura | — | ⚪ **não executável** — ferramenta não instalada |
| bandit / pip-audit / gitleaks | — | ⚪ **não executáveis** — não instalados |

### 5.2. Detalhamento dos testes

```
903 passed, 1 skipped in 79.52s   (primeira execução, cache frio)
903 passed, 1 skipped in 43.87s   (segunda execução)
903 passed, 1 skipped in 20.00s   (terceira execução, cache quente)
```

| Métrica | Valor |
|---|---|
| Coletados | **904** |
| Passaram | **903** |
| Falharam | **0** |
| Skipped | **1** |
| Warnings | **0** |
| Duração | 20 s – 80 s conforme cache |
| Arquivos de teste | 38 |
| LOC de teste | 12.802 |

**Único skip (legítimo, de plataforma):** `tests/test_file_scanner.py:202` — *"chmod
permission simulation unreliable on Windows without admin"*. É um `@pytest.mark.skipif`
condicional, não um teste desativado.

**Distribuição por área (casos coletados):**

| Área | Testes | % |
|---|---:|---:|
| Pipeline RI (`test_ri_*`) | **334** | 36,9% |
| Compliance (`test_compliance_*`) | 213 | 23,6% |
| Notas/Inventários (`test_notas_*`) | **136** | 15,0% |
| Audit (findings, diagnosis, scanner, temp) | 114 | 12,6% |
| Finance | 44 | 4,9% |
| LGPD | 37 | 4,1% |
| Retention + integração diagnosis↔retention | 22 | 2,4% |
| Infra (health, isolation) | 4 | 0,4% |

Observação relevante: **o maior bloco de testes do repositório (36,9%) cobre código que não
está em `app/`** — o pipeline RI vive em `scripts/local_tools/`.

### 5.3. Formatação — os 25 arquivos reprovados

```
alembic/versions/20260506_1600_add_compliance_requirement_finding_links.py
alembic/versions/20260507_1000_add_compliance_requirement_status.py
app/modules/audit/diagnosis/rules.py
app/modules/compliance/models.py
app/modules/compliance/router.py
app/modules/compliance/service.py
scripts/local_tools/analyze_ri_real_json.py
scripts/local_tools/audit_ri_inventory_reconciliation.py
scripts/local_tools/classify_ri_property_nature.py
scripts/local_tools/consolidate_ri_real_json_reports.py
scripts/local_tools/export_ri_inventory_review_report.py
scripts/local_tools/extract_ri_rural_inventory.py
scripts/local_tools/query_ri_real_json_inventory.py
tests/test_compliance_finding_link_models.py
tests/test_compliance_finding_link_service.py
tests/test_compliance_isolation.py
tests/test_compliance_requirement_status_routes.py
tests/test_compliance_requirement_status_service.py
tests/test_document_diagnosis.py
tests/test_ri_inventory_extractor.py
tests/test_ri_inventory_reconciliation.py
tests/test_ri_inventory_review_report.py
tests/test_ri_property_nature_classifier.py
tests/test_ri_real_json_analyzer.py
tests/test_ri_real_json_consolidated_report.py
```

**Interpretação:** `ruff check` (lint) está limpo, mas `ruff format` **nunca foi adotado como
gate** — 4 arquivos de `app/` (três de compliance + `diagnosis/rules.py`), 2 migrations, 7
scripts RI e 12 testes divergem do formatador. Não é defeito funcional; é um gate implícito
pelo uso de Ruff e nunca fechado. **Decisão humana necessária:** adotar `ruff format` como
gate (reformatando de uma vez) ou declarar explicitamente que apenas `ruff check` é
obrigatório.

### 5.4. Gates que não puderam ser executados — e por quê

| Gate | Motivo |
|---|---|
| Cobertura de testes | `pytest-cov`/`coverage` não instalados; instalar violaria a proibição de instalar/atualizar dependências |
| `bandit -r app` | não instalado; idem |
| `pip-audit` | não instalado; idem |
| `gitleaks detect` | não instalado; idem |
| `mypy .` | não instalado e não configurado; CLAUDE.md § 5 já o condiciona a "se configurado" |
| `alembic upgrade head` | proibido pelo escopo (§ 4: não executar upgrade/downgrade) — apenas `current`/`heads`/`history`/`check`, todos read-only |

Nenhum teste executado toca dados reais: `tests/test_isolation.py` garante
programaticamente que a suíte não cria nem altera `cartorio.db` — verificado, o banco
permanece idêntico antes e depois das três execuções.

---

## 6. Banco e migrations

### 6.1. Cadeia Alembic

**Head único, linear, sem branches, sem merges, sem gaps, sem órfãs:**

```
<base>
  → 8857af05ac59  initial finance core
  → b377f12ba37a  finance core hardening - direction source audit
  → 455f4efec848  drop competence_month glob check
  → c3d9a1b2e4f5  add audit findings
  → a7f1c2d3e4b5  add lgpd actions
  → b8e2d3f4a6c7  add retention rules
  → c1d2e3f4b5a6  add compliance tables
  → d2e3f4a5b6c7  add compliance evidences
  → e3f4a5b6c7d8  add compliance requirement finding links
  → f4a5b6c7d8e9  add compliance requirement status   (head)
```

| Verificação | Resultado |
|---|---|
| Heads | 1 (`f4a5b6c7d8e9`) |
| Revisões | 10 |
| Arquivos em `alembic/versions/` | 10 (+ `__pycache__`) — 1:1 com a cadeia |
| Branches / merges | nenhum |
| Gaps / migrations órfãs | nenhum |
| Banco local (`cartorio.db`) | em `f4a5b6c7d8e9` — **no head** |
| `Base.metadata.create_all` em runtime | ausente (verificado em `app/main.py`) |

### 6.2. Divergência código × banco

| Comparação | Resultado |
|---|---|
| Tabelas em `Base.metadata` | 16 |
| Tabelas no banco | 17 |
| Em metadata e não no banco | **nenhuma** |
| No banco e não em metadata | `alembic_version` (esperado) |

🔴 **`alembic check` retorna FAILED** com 6 operações. A leitura do DDL real mostra
**divergência de representação, não de semântica**:

| Objeto | O modelo declara | O que a migration criou no banco | Unicidade garantida? |
|---|---|---|---|
| `compliance_policies.code` | `unique=True, index=True` (→ índice único `ix_…`) | `CONSTRAINT uq_compliance_policies_code UNIQUE` **+** `CREATE UNIQUE INDEX ix_…` | sim (duplamente) |
| `compliance_requirements.code` | idem | idem | sim (duplamente) |
| `compliance_seed_meta.seed_name` | idem | idem | sim (duplamente) |
| `lgpd_actions.action_code` | idem | `CONSTRAINT uq_lgpd_actions_action_code UNIQUE` **+** `CREATE INDEX ix_…` (**não único**) | sim (pela constraint `uq_`) |

**Impacto funcional: nenhum.** A unicidade está efetivamente aplicada nas quatro colunas.
**Impacto de governança: relevante.** Enquanto essa divergência existir, `alembic check`
**não pode servir de gate de CI** — ele reprova um banco correto, o que treina a equipe a
ignorar o sinal. Duas saídas: (a) alinhar as declarações dos modelos ao que as migrations
criaram; (b) registrar a divergência em ADR e excluir `alembic check` dos gates
obrigatórios. Ambas são decisões humanas; nenhuma foi tomada aqui.

### 6.3. Ocupação real do banco de desenvolvimento

```
     1  alembic_version
     0  audit_findings
     0  compliance_evidence_templates
     0  compliance_evidences
     0  compliance_policies
     0  compliance_requirement_deadlines
     0  compliance_requirement_finding_links
     0  compliance_requirement_status_history
     0  compliance_requirement_statuses
     0  compliance_requirements
     0  compliance_seed_meta
     0  financial_categories
     0  financial_entries
     1  lgpd_action_status_history
    25  lgpd_actions
     0  retention_rules
```

🟠 **Este é o achado mais consequente da auditoria para a priorização estratégica.**
De sete módulos com persistência, **um único** tem dados: `lgpd` (25 ações importadas do CSV
INOVA), e mesmo esse registrou **uma única** mudança de status desde então. Em particular:

- `compliance_*` — quatro sprints (4.155 LOC, 17 endpoints, 213 testes) e o **seed
  `matriz_v1` nunca foi aplicado a este banco**. A camada consultiva existe, é testada e
  nunca respondeu a uma pergunta real.
- `retention_rules = 0` — a integração `audit/diagnosis → retention` (TEMP-001/002/003)
  carrega regras via `load_rules(session)`. Com a tabela vazia, **nenhum finding TEMP-\*
  pode ser emitido**: a integração está implementada, testada e **silenciosamente inativa**.
- `audit_findings = 0` — o CRUD REST da Sprint 2 nunca recebeu um achado; os achados do
  diagnóstico real de maio nunca foram promovidos a findings persistidos.
- `financial_entries = 0` — coerente com a decisão de congelar finance.

Nenhum outro banco de aplicação existe. O único outro banco encontrado é
`_local_data/ri_inventory/ri_inventory.sqlite` (3,9 MB, 2026-05-15), pertencente ao pipeline
RI, não ao `app/`. **Não há banco de produção.**

---

## 7. Arquitetura atual

### 7.1. Topologia real (descoberta por varredura, não por documentação)

```
cartorio_system/
├── app/                                   88 arquivos .py · ~12,9k LOC
│   ├── core/          (88 LOC)            config · errors · logging
│   ├── db/            (44 LOC)            Base declarativa · session · _register_models()
│   ├── interfaces/    (26 LOC)            api/v1/router.py — agrega 4 routers + /health
│   ├── main.py                            FastAPI + lifespan sem DDL
│   └── modules/
│       ├── audit/       3.786 LOC   scanner/ · diagnosis/ · findings/
│       ├── compliance/  4.155 LOC   models · router · service · seed · seed_data/matriz_v1
│       ├── notas/       2.119 LOC   inventarios/{domain,application,infrastructure,interfaces}
│       ├── lgpd/        1.022 LOC   models · router · rules · service
│       ├── retention/     916 LOC   models · repository · rules · seed · service (SEM router)
│       ├── finance/       679 LOC   models · router · rules · service
│       └── clients/ documents/ exports/ protocols/ reports/ tasks/   (0 LOC — placeholders)
├── scripts/
│   ├── local_tools/     6.605 LOC   7 ferramentas do pipeline RI
│   └── gerar_relatorio_pdf.py  761 LOC   gerador one-off de PDF
├── tests/              12.802 LOC   38 arquivos · 904 casos · golden/notas_inventarios/
├── alembic/versions/                10 migrations
├── docs/                            87 arquivos em 23 diretórios
├── exports/atlas/                   apenas .gitkeep (integração Atlas nunca ativada)
├── outputs/            gitignorado  saídas reais do gerador de inventário
├── .ai_tmp/            gitignorado  área de trabalho de casos reais e sprints
└── _local_data/        gitignorado  ~582 MB de documentos reais da serventia
```

### 7.2. Superfície HTTP

**41 rotas registradas** — 37 de negócio + 4 de documentação automática.

| Prefixo | Rotas | Módulo |
|---|---:|---|
| `/api/v1/compliance/*` | 17 | compliance |
| `/api/v1/lgpd/actions/*` | 7 | lgpd |
| `/api/v1/audit/findings/*` | 6 | audit/findings |
| `/api/v1/finance/*` | 5 | finance |
| `/api/v1/health` | 1 | infra |

🔴 **Zero autenticação.** Nenhuma rota usa `Depends` de segurança, `HTTPBearer`, `OAuth2` ou
API key — o único `Depends` presente é `get_db`. A atribuição de autoria é feita por
**defaults literais**: `created_by`/`updated_by` = `"gestor"` em `finance` e `lgpd`. Isso é
coerente com a decisão D-08 (auditoria mínima sem auth na fase MVP) e permanece adequado
enquanto o uso for monousuário — mas é o gap estrutural do Provimento CNJ 213 (§ 13).

**Módulos sem superfície HTTP:** `retention` (models + service + seed, consumido apenas por
`audit/diagnosis`) e `notas/inventarios` (CLI puro). `audit/scanner` e `audit/diagnosis`
também são CLIs.

### 7.3. Isolamento entre módulos

Varredura completa de `from app.modules.X import …` dentro de `app/modules/`:

```
audit -> retention  (5 imports)
```

**Uma única dependência cruzada em todo o sistema**, em
`app/modules/audit/diagnosis/temp_rules.py`, que importa `retention.rules`,
`retention.enums` e `retention.models` para emitir os findings TEMP-*. É a exceção conhecida
(TD-17, ainda sem ADR) ao princípio de referência fraca da ADR-002. Todo o resto —
compliance ↔ audit, compliance ↔ lgpd, notas ↔ tudo — respeita o isolamento por
`source_module + source_type + source_ref`, sem FK cruzada. Nenhuma dependência circular.

### 7.4. Dois padrões de layout coexistindo

| Padrão | Módulos | Forma |
|---|---|---|
| **Flat** | finance, lgpd, retention, compliance, audit/findings | `enums · models · rules · schemas · service · router` no mesmo nível |
| **Hexagonal** | notas/inventarios | `domain/ · application/ · infrastructure/ · interfaces/` |

Nenhum ADR governa a escolha (TD-08, aberta). Registro factual: o módulo hexagonal é
justamente o de maior valor operacional comprovado e o de maior densidade de testes por LOC
(136 testes / 2.119 LOC = 1 teste a cada 15,6 linhas, contra 1 a cada 21 no compliance).

---

## 8. Matriz de módulos

Legenda: **MADURO** (funcional + testado + usado em caso real) · **FUNCIONAL** (completo e
testado, sem uso real comprovado) · **PARCIAL** (implementado com lacuna estrutural ou
inativo) · **EXPERIMENTAL** · **AUSENTE** · **LEGACY/ABANDONADO**.

| # | Módulo | Caminho | LOC | Testes | Persistência | Interface | Estado | Evidência da classificação |
|---|---|---|---:|---:|---|---|---|---|
| 1 | **notas/inventarios** | `app/modules/notas/inventarios/` | 2.119 | 136 | nenhuma (stateless) | CLI (`--render-minuta`, `--export-odt`) | **MADURO** | 6 casos reais 05→08/2026; 6 golden files byte-a-byte; exportador ODT stdlib-only; schema Pydantic `extra="forbid"`; ADR-009 própria |
| 2 | **audit/scanner** | `app/modules/audit/scanner/` | ~900 | 25 | arquivos (`file_inventory.json/csv`, manifest SHA-256) | CLI | **MADURO** | `module_roadmap.md` Fase 1: "concluída e validada em ambiente real"; contrato read-only formalizado |
| 3 | **audit/diagnosis** | `app/modules/audit/diagnosis/` | ~2.100 | 46 | arquivos (`document_diagnosis.*`) | CLI | **MADURO** | Fase 2.5 "Execução Real Controlada"; commit `441a33e` calibra regras **após** validação real; 7 regras DIAG-* + 3 TEMP-* |
| 4 | **compliance** | `app/modules/compliance/` | 4.155 | 213 | 8 tabelas | REST (17 rotas) | **FUNCIONAL** | 4 sprints, ADR-001/002, seed idempotente com checksum — porém **0 linhas**: nunca semeado, nunca consultado em caso real |
| 5 | **lgpd** | `app/modules/lgpd/` | 1.022 | 37 | 2 tabelas | REST (7 rotas) | **FUNCIONAL** | único módulo com dados reais (25 ações INOVA); apenas **1** transição de status desde a importação de maio |
| 6 | **audit/findings** | `app/modules/audit/findings/` | ~800 | 43 | 1 tabela | REST (6 rotas) | **FUNCIONAL** | CRUD completo, sem DELETE físico, histórico de status — **0 linhas** |
| 7 | **finance** | `app/modules/finance/` | 679 | 44 | 2 tabelas | REST (5 rotas) | **FUNCIONAL (congelado)** | Finance Core v1.2 com `Numeric(14,2)`, regras status×tipo, imutabilidade de `entry_type` — **0 linhas**; congelamento é decisão explícita |
| 8 | **retention** | `app/modules/retention/` | 916 | 22 | 1 tabela | **nenhuma** (consumido por audit) | **PARCIAL** | regras e seed implementados e testados; **sem router** (não documentado como intencional); `retention_rules = 0` ⇒ integração TEMP-* **inativa na prática** |
| 9 | **Pipeline RI** | `scripts/local_tools/` (7 arquivos) | 6.605 | **334** | SQLite próprio em `_local_data/` | CLI | **FUNCIONAL — fora da arquitetura** | maior bolsão de lógica e de testes do repositório; produziu a base do dossiê PROAD; `docs/modules/registro_imoveis.md` ainda declara "Pré-implementação"; `app/modules/registro_imoveis/` **não existe** |
| 10 | **core / db / interfaces** | `app/core`, `app/db`, `app/interfaces` | 158 | 4 | — | FastAPI | **MADURO (para o escopo)** | DDL exclusivo do Alembic verificado; teste de isolamento do banco de dev; handlers de erro; logging |
| 11 | `clients` `documents` `exports` `protocols` `reports` `tasks` | `app/modules/*` | 0 | 0 | — | — | **AUSENTE** | apenas `__init__.py` vazio; documentados como intencionais em `architecture.md` (TD-07, P4) |
| 12 | **auth / identidade** | — | 0 | 0 | — | — | **AUSENTE** | nenhum código; exigência estrutural do Prov. CNJ 213 (TD-18) |
| 13 | **Trilha de auditoria transversal** | — | 0 | 0 | — | — | **AUSENTE** | históricos append-only existem por módulo; não há trilha de mutações do sistema (TD-19) |
| 14 | **knowledge_base / ai_gateway** | `docs/knowledge_base/`, `docs/ai/` | 0 | 0 | — | — | **AUSENTE (blueprint)** | 5 documentos + ADR-004..008 em estado *Proposto*; bloqueado por DHP-01..10 — bloqueio correto |
| 15 | **document_registry** | `docs/document_registry/` | 0 | 0 | — | — | **AUSENTE (blueprint)** | ADR-003 aceito; sem código |
| 16 | **Integração Atlas** | `exports/atlas/` | 0 | 0 | — | — | **AUSENTE** | apenas `.gitkeep`; nenhum export jamais gerado — consistente com a regra de isolamento |
| 17 | `gerar_relatorio_pdf.py` | `scripts/` | 761 | 0 | — | script | **LEGACY** | gerador one-off do relatório da diretoria (maio/2026); sem testes; consome `docs/reports/generated/relatorio_pdf.css` |

### 8.1. Distribuição de esforço × distribuição de valor

| Módulo | % do código de negócio | % dos testes | Uso real |
|---|---:|---:|---|
| Pipeline RI | 33,8% | 36,9% | ✅ dossiê PROAD |
| compliance | 21,3% | 23,6% | ❌ nunca semeado |
| audit (3 submódulos) | 19,4% | 12,6% | ✅ execução real (maio) |
| notas/inventarios | 10,8% | 15,0% | ✅ **6 casos reais** |
| lgpd | 5,2% | 4,1% | 🟡 importação única |
| retention | 4,7% | 2,4% | ❌ tabela vazia |
| finance | 3,5% | 4,9% | ❌ congelado |
| scripts one-off | 3,9% | 0% | 🟡 uso único |

**Leitura:** o módulo com maior valor operacional comprovado consome 10,8% do código. O
módulo com o segundo maior volume de código (compliance, 21,3%) nunca foi usado.

---

## 9. Dívida técnica

### 9.1. Marcadores de código

Varredura de `TODO · FIXME · HACK · XXX · deprecated · legacy · temporary · not implemented ·
pass · skip · xfail` em `app/`, `scripts/` e `tests/`:

| Marcador | Ocorrências reais | Observação |
|---|---:|---|
| `TODO` | **0** | as 5 ocorrências textuais são falsos positivos: a string `"VALIDA EM TODO O TERRITORIO NACIONAL"` (regra DIAG-008) |
| `FIXME` | **0** | — |
| `HACK` | **0** | — |
| `XXX` | **0** | 1 falso positivo: `"Georef. Incra XXXXX NIRF"` (padrão de extração RI) |
| `deprecated` | **0** | — |
| `not implemented` / `NotImplementedError` | **0** | — |
| `xfail` | **0** | — |
| `pytest.skip` / `skipif` | **1** | o skip legítimo de plataforma (Windows/chmod) |
| `pass` isolado em `app/` | **2** | `db/base.py:5` (classe `Base` declarativa) e `lgpd/rules.py:114` — ambos idiomáticos, não stubs |

**Conclusão:** o código não carrega dívida sinalizada. A dívida do projeto é **estrutural e
documental**, não de implementação inacabada.

### 9.2. Registro consolidado

Estado das 22 dívidas do registro de julho (`technical_debt_register.csv`) + 5 achados novos
desta sprint (**TD-23 a TD-27**) — 27 linhas ao todo.

| ID | Dívida | Prio. | Estado hoje | Evidência |
|---|---|:--:|---|---|
| **TD-23** 🆕 | **`PyYAML` importada por `app/` e não declarada no `pyproject.toml`** | **P1** | **ABERTA (nova)** | `loaders.py:24` faz `import yaml`; ausente de `dependencies` e de `dev` |
| **TD-09** | **Ausência total de CI** | **P1** | **ABERTA — inalterada** | `.github/` não existe; nenhum hook; nenhum pre-commit |
| **TD-01** | `docs/architecture.md` contradiz o código | **P1** | **ABERTA — inalterada** | linha 45: "finance — único módulo ativo"; linha 87: "Hoje apenas `finance` está implementado". Existem 8 módulos |
| **TD-02** | `docs/roadmap.md` defasado | **P1** | **ABERTA — inalterada** | Sprint 3 marcada 🟡 "(próxima)"; concluída em `2e329e0` (2026-05-04). Contagens 48/72/108 vs 903 |
| **TD-05** | Trabalho PROAD não commitado | P1 | ✅ **RESOLVIDA** | commits `a0f96ca` e `dd5b3be` (2026-07-13) |
| **TD-24** 🆕 | **`alembic check` reprova (drift de representação de unicidade)** | **P2** | **ABERTA (nova)** | 6 operações detectadas; unicidade efetivamente garantida no banco; impede uso de `alembic check` como gate |
| **TD-25** 🆕 | **`ruff format` não adotado como gate — 25 arquivos divergentes** | **P2** | **ABERTA (nova)** | inclui 4 arquivos de `app/` e 2 migrations |
| **TD-26** 🆕 | **Eixo regulatório implementado e nunca ativado** | **P2** | **ABERTA (nova)** | `compliance_*`, `audit_findings`, `retention_rules`, `financial_entries` = 0 linhas; seed `matriz_v1` nunca aplicado; TEMP-* inativos por tabela vazia |
| **TD-16** | 5 roadmaps sem hierarquia de autoridade | P2 | **ABERTA — agravada** | agora são **6** com `docs/audits/repository_rebaseline_2026_07/06_ROADMAP_RECONCILIADO.md` |
| **TD-11** | `testing.md` declara 48 testes | P2 | **ABERTA — inalterada** | `docs/quality/testing.md:5` — "**48 testes passando** em 3 arquivos"; reais: 904 em 38 arquivos |
| **TD-06** | Pipeline RI (6.605 LOC) fora da arquitetura | P2 | **ABERTA — inalterada** | `docs/modules/registro_imoveis.md`: "Status: Pré-implementação"; DH-1 sem decisão |
| **TD-10** | bandit/pip-audit/gitleaks exigidos e ausentes | P2 | **ABERTA — inalterada** | CLAUDE.md § 5 os exige; nenhum instalado |
| **TD-04** | Índices documentais incompletos | P2 | **ABERTA — parcialmente agravada** | `docs/README.md` § 3 não lista notas nem registro_imoveis; § 8 lista só ADR-001..003; `decisions/index.md` omite **ADR-009**; CLAUDE.md § 9 omite notas e RI |
| **TD-13** | Relatórios de sprint sem política de arquivamento | P2 | **ABERTA — agravada** | `docs/reports/`, `docs/analysis/`, `docs/ai/`, `docs/audits/` acumulam fotografias de época sem marcação de vigência |
| **TD-22** | Backup de `_local_data` fora de governança | P2 | **ABERTA — não confirmável** | 582 MB em 5 subárvores; rotina de backup externa não verificável do repositório |
| **TD-18** | Autenticação multiusuário não iniciada | P2 | **ABERTA — inalterada** | zero `Depends` de segurança em 37 rotas |
| **TD-19** | Trilha de auditoria transversal não iniciada | P2 | **ABERTA — inalterada** | históricos por módulo existem; trilha de sistema não |
| **TD-03** | Referências quebradas a `docs/operations/engegraph.md` | P2 | **ABERTA — inalterada** | `architecture.md:151` e `modules/audit.md:323` |
| **TD-27** 🆕 | **POP de notas com 2 links quebrados, bloqueado fora do git** | **P3** | **ABERTA (nova/derivada)** | `POP_USO_GERADOR_MINUTA_INVENTARIO.md` linhas 332 e 560 apontam `../decisions/ADR-009…` (correto: `../../decisions/…`) |
| **TD-12** | Fonte dupla renderer.py × template `.j2` | P3 | **ABERTA — mitigada por teste** | existe `test_minuta_template_j2_referencia_renderer_como_fonte_executavel`; não há verificação de sincronia de conteúdo |
| **TD-08** | Dois padrões de layout sem ADR | P3 | **ABERTA — inalterada** | flat × hexagonal |
| **TD-17** | Dependência `audit.diagnosis → retention` sem ADR | P3 | **ABERTA — inalterada** | 5 imports; única exceção ao isolamento |
| **TD-14** | Gerador de PDF one-off em `scripts/` | P3 | **ABERTA — inalterada** | 761 LOC, 0 testes |
| **TD-15** | Normalização de EOL indefinida fora de `tests/golden` | P3 | **ABERTA — atenuada** | os 12 docs PROAD que geravam warning foram commitados; `.gitattributes` continua cobrindo só golden files |
| **TD-07** | Seis placeholders vazios | P4 | decisão consciente | inalterada |
| **TD-20** | Sem task runner unificado | P4 | ABERTA | inalterada |
| **TD-21** | Observabilidade limitada a stdout | P4 | ABERTA | adequada ao estágio |

### 9.3. Síntese por prioridade

Contagem conferida item a item contra a tabela do § 9.2 (27 linhas: **26 abertas + 1
resolvida**).

| Prio. | Qtd. abertas | Itens |
|:--:|---:|---|
| **P0** | **0** | nenhum risco crítico ativo — nenhum segredo versionado, nenhum dado pessoal no git, nenhum defeito de implementação conhecido no código |
| **P1** | **4** | TD-23 (PyYAML), TD-09 (CI), TD-01 (architecture), TD-02 (roadmap) |
| **P2** | **13** | TD-24, TD-25, TD-26, TD-16, TD-11, TD-06, TD-10, TD-04, TD-13, TD-22, TD-18, TD-19, TD-03 |
| **P3** | **6** | TD-27, TD-12, TD-08, TD-17, TD-14, TD-15 |
| **P4** | **3** | TD-07, TD-20, TD-21 |
| — | **26** | **total de dívidas abertas** |
| ✅ | 1 | TD-05 (P1) — **resolvida** pelos commits `a0f96ca` e `dd5b3be` |

> Ressalva sobre a linha P0: "nenhum defeito conhecido" refere-se a defeitos de
> implementação no código. As limitações funcionais de `notas/inventarios` descritas no § 12
> (precisão percentual, fração ideal, saída fragmentada, texto limpo) são **lacunas de
> escopo declaradas e testadas**, não defeitos — mas produzem efeito real no documento
> gerado e estão contabilizadas como oportunidades F1 e F2, não como dívida técnica.

### 9.4. Código morto, órfãos e duplicação

| Verificação | Resultado |
|---|---|
| Dependências circulares | **nenhuma** |
| Módulos órfãos (código sem consumidor) | 6 placeholders vazios; `gerar_relatorio_pdf.py` (one-off) |
| Duplicação relevante | `renderer.py` × `inventario_extrajudicial_padrao.md.j2` (TD-12) — espelho textual não interpretado em runtime |
| Imports incomuns | nenhum; `import yaml` é legítimo mas não declarado (TD-23) |
| Configurações contraditórias | CLAUDE.md § 5 exige ferramentas de segurança inexistentes (TD-10); CLAUDE.md § 9 lista 5 módulos, existem 8 + pipeline RI |
| Interfaces incompletas | `retention` sem router (TD do julho, ainda sem decisão registrada) |
| Warnings de execução | **zero** |
| Caminhos críticos sem teste | nenhum caminho de `app/` sem cobertura de teste identificado; **o gap real é o inverso**: caminhos testados que nunca rodaram em produção (TD-26) |

---

## 10. Documentação e roadmap

### 10.1. Inventário documental

87 arquivos em 23 diretórios: `ai` · `analysis` · `architecture` · `audit` · `audits` ·
`decisions` · `document_registry` · `infrastructure` · `knowledge_base` · `modules` ·
`operations` · `proad` · `quality` · `readiness` · `regulatory/cnj_213` · `reports` ·
`ri_inventory` · `security` + raiz.

### 10.2. Matriz previsto × realizado

| Classificação | Itens |
|---|---|
| **PREVISTO E CONCLUÍDO** | Etapa 0 (Fundação FastAPI) · Etapa 0.1 (pin 3.12) · Etapa 1/1.1/1.2 (Finance Core v1.2) · Audit Sprint 1 (Scanner) · Sprint 2 (Findings) · Sprint 2.5 (POP read-only) · Sprint 3 + 3.5 + 3.6 (DocumentDiagnosis) · LGPD-1 · retention-1A/1B · Compliance-1 a 4 · ADR-001/002/003 |
| **PREVISTO E PARCIAL** | Eixo regulatório CNJ 213: **implementado no código, nunca ativado no banco** (TD-26) · `retention` sem router · Fases 3–10 do `module_roadmap.md` (disco, backup, segurança, rede, políticas, fluxos, risco, dossiê) não iniciadas |
| **PREVISTO E NÃO INICIADO** | Autenticação multiusuário (TD-18) · Trilha de auditoria transversal (TD-19) · Exports com checksum/timestamp/usuário · Finance Etapas 2–7 (congeladas por decisão) · Protocolos/GED (adiados por decisão) · KB-1+ (bloqueado por DHP-01..10) · Document Registry (ADR-003 aceito, sem código) · Integração Atlas |
| **IMPLEMENTADO FORA DO ROADMAP** | 🔴 **`notas/inventarios`** (2.119 LOC, 136 testes, 6 casos reais, ADR-009) — **não consta de `docs/roadmap.md`** · 🔴 **Pipeline RI** (6.605 LOC, 334 testes) — `docs/roadmap.md` silencia; `docs/modules/registro_imoveis.md` diz "Pré-implementação" · **Dossiê PROAD/IERI** (11 documentos + pacote ODT) |
| **OBSOLETO** | `docs/quality/testing.md` ("48 testes em 3 arquivos") · `docs/architecture.md` ("finance é o único módulo ativo") · contagens de teste em `roadmap.md` (48/72/108) |
| **ABANDONADO/ADIADO** | Monthly Closing (Etapa 2, rebaixada) · Obligations/Reports · importação de planilhas históricas 2016-2026 · MCP e agentes autônomos (ADR-007) |
| **CONTRADITÓRIO COM O CÓDIGO** | `roadmap.md`: Sprint 3 "🟡 (próxima)" × concluída em 2026-05-04 · `architecture.md`: 1 módulo × 8 reais · `testing.md`: 48 testes × 904 · `registro_imoveis.md`: "sem rotas, migrations ou banco" (verdadeiro) mas "Pré-implementação" (falso — há 6.605 LOC e um SQLite operacional) · `CLAUDE.md` § 9: tabela de 5 módulos, faltam notas e RI |

### 10.3. Links quebrados verificados

| Origem | Alvo | Situação |
|---|---|---|
| `docs/architecture.md:151` | `docs/operations/engegraph.md` | 🔴 arquivo inexistente |
| `docs/modules/audit.md:323` | `docs/operations/engegraph.md` | 🔴 arquivo inexistente |
| `POP_USO_GERADOR_MINUTA_INVENTARIO.md:332` | `../decisions/ADR-009-inventory-cent-rounding-policy.md` | 🔴 resolve para `docs/modules/decisions/…` (correto: `../../decisions/…`) |
| `POP_USO_GERADOR_MINUTA_INVENTARIO.md:560` | idem | 🔴 idem |

Os demais 9 links relativos do POP (`../notas_inventarios.md`,
`../notas_inventarios_checklist.md`, `../../../CLAUDE.md`, etc.) **resolvem corretamente** —
apenas os dois links para ADR-009 estão errados. É a única razão técnica pela qual o
documento permanece fora do controle de versão.

### 10.4. Hierarquia de roadmaps — agravamento

Existiam 5 roadmaps sem precedência declarada; agora são **6**:

1. `docs/roadmap.md` — geral (**defasado**)
2. `docs/audit/module_roadmap.md` — módulo de auditoria (**atualizado**)
3. `docs/regulatory/cnj_213/roadmap.md` — regulatório
4. `docs/knowledge_base/IMPLEMENTATION_ROADMAP.md` — KB (bloqueado)
5. `docs/infrastructure/infrastructure_roadmap.md` — infraestrutura
6. `docs/audits/repository_rebaseline_2026_07/06_ROADMAP_RECONCILIADO.md` — 🆕 reconciliado
   pela auditoria de julho (**não aprovado**)

Nenhum declara precedência sobre os outros. O estado real do projeto só é reconstituível
cruzando os seis com o `git log` e com o conteúdo de `.ai_tmp/` — como esta auditoria fez.

---

## 11. Auditoria de valor

Escala de evidência: **V0** hipótese · **V1** plausível pelo domínio · **V2** testado
internamente · **V3** usado em caso real · **V4** usado repetidamente com benefício
observado. *Onde não há dado de uso, o campo é marcado explicitamente como desconhecido.*

| Módulo | Problema resolvido | Usuário | Frequência observada | Trabalho manual substituído | Redução de erro | Evidência | **Nível** |
|---|---|---|---|---|---|---|:--:|
| **notas/inventarios** | Redigir cláusulas de patrimônio e partilha de escritura de inventário a partir de valores do ITCD | Escrevente / tabeliã | **6 casos em 99 dias** (~1 a cada 16 dias) | transcrição e cálculo manual de quinhões bem a bem | cálculo `Decimal` determinístico + detecção de resíduo de centavos | 6 diretórios de caso datados (05-23, 05-25, 07-09, 08-02, 08-13, 08-29), o mais recente **4 dias antes desta auditoria** | **V4** |
| **Pipeline RI** | Inventariar e sanear o acervo de matrículas para IERI-e/SIG-RI (PROAD) | Oficial registradora / equipe RI | 1 ciclo intenso (05→06/2026), 127 PDFs brutos processados | levantamento manual de 3.534 matrículas | reconciliação CSV×JSON×SQLite com auditoria de divergência | dossiê PROAD de 11 documentos + pacote ODT derivados dessa base | **V3** (V4 se o ciclo mensal IERI-e for confirmado) |
| **audit/diagnosis** | Diagnosticar problemas do acervo digital sem abrir os documentos | Gestor | 1 execução real conhecida (05/2026) | triagem manual de milhares de arquivos | regras calibradas **após** confronto com o resultado real (`441a33e`) | Fase 2.5 "Execução Real Controlada" no `module_roadmap.md` | **V3** |
| **audit/scanner** | Inventariar arquivos do servidor com hash, sem alterá-los | Gestor | 1 execução real conhecida (05/2026) | inventário manual | manifest com SHA-256 e `read_only: true` | Fase 1 "concluída e validada em ambiente real" | **V3** |
| **lgpd** | Rastrear as 25 ações do plano INOVA | Gestor / DPO | 1 importação (05/2026) + **1** atualização de status | planilha de acompanhamento | histórico append-only | 25 linhas em `lgpd_actions`, 1 em `lgpd_action_status_history` | **V2→V3** (importado de fonte real; acompanhamento posterior **não observado**) |
| **compliance** | Consultar requisitos × políticas × prazos × evidências da matriz INOVA V1 | Gestor | **nenhuma** | — | — | **0 linhas** em 8 tabelas; seed nunca aplicado | **V1** |
| **audit/findings** | Registrar e acompanhar achados de auditoria | Gestor | **nenhuma** | — | — | **0 linhas** | **V1** |
| **retention** | Aplicar tabela de temporalidade a documentos | Gestor | **nenhuma** | — | — | **0 linhas** ⇒ TEMP-* inativos | **V1** |
| **finance** | Gestão financeira da serventia | Gestor | **nenhuma** | — | — | **0 linhas**; congelado por decisão | **V1** |
| **Doações (nova frente)** | Redigir cláusula de doação a partir do demonstrativo de ITCD | Escrevente | **1 caso** (2026-06-23) | redação integral manual | — | `_local_data/Notas/Doações/001/` com 6 imagens de ITCD + relatório sanitizado + proposta de cláusula — **produzidos sem nenhum código** | **V3 para o problema, V0 para a solução em código** |
| **KB / IA** | Consulta normativa assistida | — | nenhuma | — | — | apenas blueprints | **V0** |
| **Atlas (export)** | Interoperabilidade futura | — | nenhuma | — | — | `exports/atlas/` só tem `.gitkeep` | **V0** |

### 11.1. Achados de valor que mudam a priorização

**1. O uso sobreviveu à parada do desenvolvimento.** Quatro dos seis casos de inventário
(07-09, 08-02, 08-13, 08-29) são **posteriores ao último commit de código** (2026-05-22).
O módulo entrega valor sem manutenção — o sinal mais forte possível de aderência ao
problema real.

**2. A unidade de consumo real não é a minuta inteira.** Os artefatos dos três casos de
agosto são `clausulas_heranca_partilha.md` e `clausulas_patrimonio_partilha.md` —
**fragmentos das §§ 10 e 11**, extraídos da saída completa e reempacotados manualmente com
um cabeçalho de aviso. O caso de julho produziu ainda um `04_TEXTO_LIMPO_ENGEGRAPH.md`
(21,5 KB), também manual. O gerador produz `inventario_minuta.md` (17–24 KB) e a serventia
usa 2 seções dele. **Essa transformação é hoje 100% manual e se repete a cada caso.**

**3. Os casos reais estão ficando maiores.** 2 herdeiros/2 bens (maio) → 10 ordens/1 bem
(julho) → 8 herdeiros/2 bens (agosto/02) → **2 herdeiros/12 bens** (agosto/13) → 8
herdeiros/1 bem (agosto/29). O caso de 12 bens movimentou R$ 3.820.546,86.

**4. O alerta de centavos aparece na maioria dos casos reais.** Dois dos três casos de
agosto registraram divergência de R$ 0,01 exigindo decisão do tabelião — no caso de 12 bens,
a divergência é visível na própria minuta (§ 10.2 declara R$ 955.136,72; as alíneas do § 11
somam R$ 955.136,71). A política da ADR-009 está funcionando como projetada (alerta, não
correção silenciosa), mas a fricção é recorrente.

**5. Surgiu uma família de atos vizinha, tratada sem código.** `_local_data/Notas/Doações/001/`
(2026-06-23) contém 6 capturas do demonstrativo de ITCD, um relatório sanitizado e uma
proposta de cláusula de doação — o mesmo fluxo do inventário, aplicado a **doação**, e
resolvido inteiramente à mão.

---

## 12. Auditoria especial — Inventários

### 12.1. Arquitetura

Layout hexagonal, 2.119 LOC, 136 testes (15,0% da suíte), zero dependência de framework no
domínio.

| Camada | Arquivo | LOC | Papel |
|---|---|---:|---|
| **domain** | `models.py` | 90 | `Inventario`, `Herdeiro`, `Bem`, `Distribuicao`, `QuinhaoBem`, `ResumoBem`, `ResumoInventario` — todos `@dataclass(frozen=True)`; enum `TipoBem` |
| | `errors.py` | 23 | `InventarioError` → `InventarioInputError`, `InventarioValidationError` (agrega lista de mensagens) |
| **application** | `calculator.py` | 110 | `InventarioCalculator.compute()` · `quantize_money()` (`ROUND_HALF_EVEN`) · `DECIMAL_TOLERANCIA = 0.01` |
| | `validator.py` | 165 | `InventarioValidator` — 11 regras de negócio; devolve `ValidationResult` com lista de erros |
| | `renderer.py` | **799** | `render_minuta_markdown()` (**fonte executável**, §§ 1–20 + encerramento + campo de revisão) e `render_resumo_markdown()` (resumo técnico) |
| **infrastructure** | `loaders.py` | 61 | YAML/JSON → mapping → schema |
| | `output_dir.py` | 71 | política de destino: só `outputs/`, `tmp/`, `.ai_tmp/` dentro do repo |
| | `exporters/odt_exporter.py` | 288 | ODT determinístico com `zipfile` + `xml.sax.saxutils` — **sem dependência externa**; data fixa 1980-01-01 |
| | `templates/…md.j2` | (13 KB) | **espelho textual**, não interpretado em runtime (Jinja2 nem está instalado) |
| **interfaces** | `schemas.py` | 194 | Pydantic v2, `extra="forbid"`, `SafeDecimal` (float → str antes de `Decimal`; bool rejeitado) |
| | `cli.py` | 240 | `--input`, `--output-dir`, `--render-minuta`, `--export-odt`; exit 0/1/2 |
| **fixtures** | `examples/*.yaml` | 2 arquivos | `inventario_simples` (meeiro + 2 herdeiros + 2 bens) e `inventario_sem_meeiro` (3 herdeiros + 2 bens) |
| **golden** | `tests/golden/notas_inventarios/` | 6 arquivos | minuta + resumo + validação, para os 2 exemplos, comparados **byte a byte** (`eol=lf` fixado no `.gitattributes`) |

**Testes por arquivo:** renderer 45 · odt_exporter 21 · output_dir 20 · schemas 18 ·
validator 17 · calculator 11 · golden 4 = **136**.

### 12.2. Entradas suportadas

| Entrada | Situação | Evidência |
|---|:--:|---|
| **YAML** (`.yaml`, `.yml`) | ✅ **IMPLEMENTADO** | `loaders.py:_YAML_EXTS`; ambos os exemplos canônicos; usado em todos os casos reais |
| **JSON** (`.json`) | ✅ **IMPLEMENTADO** | `loaders.py:_JSON_EXTS`; usado em `.ai_tmp/…/veiculo_base/_cross_check/input.json` |
| **Mapping em memória** | ✅ **IMPLEMENTADO** | `inventario_from_mapping()` — porta de entrada programática |
| Entrada manual (formulário/prompt) | ❌ **NÃO EXISTENTE** | sem CLI interativo, sem rota HTTP |
| **CSV** | ❌ **NÃO EXISTENTE** | nenhuma referência |
| **PDF** | ❌ **NÃO EXISTENTE** | nenhum parser de PDF no módulo |
| **Imagem** (print do ITCD) | ❌ **NÃO EXISTENTE** *(mas é a fonte real)* | os casos reais partem de capturas do demonstrativo de ITCD, transcritas manualmente para YAML — ver `01_RELATORIO_ANALISE_INVENTARIO_VEICULO.md` § 3 "Leitura da imagem (fonte única de entrada)" |
| **ITCD estruturado** | ❌ **NÃO EXISTENTE** | não há contrato, parser nem schema de ITCD |
| Estrutura intermediária declarada | 🟡 **PARCIAL** | `InventarioInputSchema` é o contrato de entrada; não há um formato intermediário entre ITCD e ele |

🔴 **Lacuna central:** a **única** fonte de dados real (demonstrativo de ITCD, em imagem) não
tem nenhum caminho automatizado até o schema de entrada. Todo caso real exige transcrição
manual valor a valor.

### 12.3. Cenários sucessórios — suporte verificado por código + teste

*Nada foi classificado como suportado sem evidência executável.*

| Cenário | Suporte | Evidência executável |
|---|:--:|---|
| **Com meeiro** | ✅ **SUPORTADO** | `possui_meeiro=True` + `percentual_meacao`; `test_patrimonio_e_meacao_com_meeiro`, `test_minuta_com_meeiro_contem_secao_de_meacao`, golden `inventario_simples_*` |
| **Sem meeiro** | ✅ **SUPORTADO** | `test_inventario_sem_meeiro_nao_atribui_meacao`, `test_minuta_sem_meeiro_nao_contem_secao_10_1_meacao`, `test_minuta_sem_meeiro_nao_inclui_linha_de_assinatura_de_meeiro`, golden `inventario_sem_meeiro_*` |
| **Um herdeiro** | ✅ **SUPORTADO** (por construção) | validador exige ≥ 1 herdeiro; nenhum teste dedicado ao caso N=1 — **lacuna de teste** |
| **Vários herdeiros** | ✅ **SUPORTADO** | exemplos com 2 e 3; casos reais com 8, 9 e 10 beneficiários |
| **Quinhões iguais** | ✅ **SUPORTADO** | `inventario_simples` (50/50); caso real 12,50% × 8 |
| **Quinhões diferentes** | ✅ **SUPORTADO** | `inventario_sem_meeiro` (33,33/33,33/33,34); caso real com quinhão integral e meio quinhão |
| **Múltiplos bens** | ✅ **SUPORTADO** | ambos os exemplos (2 bens); caso real com **12 bens** |
| **Imóvel** | ✅ **SUPORTADO** — com redação específica | `renderer.py:325` emite bloco de procedência com matrícula, RI, comarca, CIT, selo digital; `test_minuta_referencia_matricula_por_bem_imovel` |
| **Veículo** | 🟡 **PARCIAL** | `TipoBem.VEICULO` existe e calcula corretamente; a **redação** cai no bloco genérico "[PROCEDÊNCIA_…] — preencher pelo Engegraph (placa, etc.)"; `test_minuta_bem_nao_imovel_usa_bloco_generico_de_procedencia` |
| **Dinheiro / Direito / Outro** | 🟡 **PARCIAL** | mesmos enums e mesmo bloco genérico |
| **Débitos do espólio** | ❌ **NÃO SUPORTADO** | `renderer.py:346` emite cláusula fixa de inexistência + aviso: "Esta minuta-base **NÃO** calcula débitos automaticamente" |
| **Cessão de direitos** | ❌ **NÃO EXISTENTE** | zero ocorrências de "cessão" em `app/` e em `tests/` |
| **Cessão parcial** | ❌ **NÃO EXISTENTE** | idem |
| **Adjudicação** | ❌ **NÃO EXISTENTE** | zero ocorrências |
| **Renúncia** | ❌ **NÃO EXISTENTE** | zero ocorrências |
| **Representação / estirpe** | ❌ **NÃO EXISTENTE** | o relatório do caso real de julho registra explicitamente: "**Não** se concluiu representação, estirpe, substituição ou pré-morte" |
| **Usufruto** | ❌ **NÃO EXISTENTE** | zero ocorrências |
| **Sobrepartilha** | ❌ **NÃO EXISTENTE** | o POP a lista como fora do escopo do MVP |
| **Múltiplos falecidos** | ❌ **NÃO EXISTENTE** | POP § 3: fora do escopo |
| **Testamento** | ❌ **NÃO SUPORTADO** | § 4 emite cláusula fixa de **inexistência** de testamento |
| **Herdeiro incapaz / nascituro** | ❌ **NÃO EXISTENTE** | inventário extrajudicial pressupõe capazes; sem validação explícita |
| **Doação** | ❌ **NÃO EXISTENTE** | `tipo_ato` é `Literal["inventario_extrajudicial"]`; um caso real foi resolvido manualmente |

**Resumo:** o módulo suporta **com/sem meeiro × N herdeiros × N bens × percentuais
arbitrários**. Toda a álgebra sucessória qualitativa (renúncia, cessão, representação,
adjudicação, usufruto) está fora — e essa é uma fronteira **declarada e testada**, não uma
omissão silenciosa.

### 12.4. Matemática — auditoria de precisão

**O que está correto:**

| Aspecto | Implementação | Verificação |
|---|---|---|
| Tipo monetário | `Decimal` em 100% dos campos monetários e percentuais | nenhum `float` no domínio |
| Arredondamento | `ROUND_HALF_EVEN` (banker's) em `quantize_money()` | `test_quantize_money_arredonda_para_duas_casas` |
| Proteção contra `float` | `SafeDecimal` converte `float`→`str` antes de `Decimal`; `bool` rejeitado | `test_calculator_nao_aceita_float_implicito` |
| Invariante de meação | `valor_meacao = 0` quando `possui_meeiro=False` | `test_inventario_sem_meeiro_nao_atribui_meacao` |
| Invariante de soma | Σ percentuais herdeiros = 100 ± 0,01 · Σ distribuição por bem = 100 ± 0,01 · Σ bens = patrimônio ± 0,01 | 3 checagens no validador |
| Resíduo | `divergencia_centavos = |patrimônio − Σ distribuído|`, sempre exposto | ADR-009; alerta em JSON + resumo + minuta + stderr |
| Determinismo do ODT | data fixa `1980-01-01` em todas as entradas do ZIP | `test_notas_inventarios_odt_exporter` |

**Onde a exatidão pode se perder — três pontos, todos de *representação*, nenhum de cálculo:**

🔴 **P-1 — `_fmt_pct` trunca em 2 casas (renderer.py:51).**
```python
def _fmt_pct(value: Decimal) -> str:
    return f"{value:.2f}%".replace(".", ",")
```
Demonstração executada nesta auditoria:

| Entrada | Exibido | Perda |
|---|---|---|
| `3.125` | `3,12%` | 1/32 deixa de ser representável |
| `5.5556` | `5,56%` | — |
| `0.005` | `0,00%` | participação some da minuta |

**Consequência quantificada:** num cenário meeira 1/2 + 9 herdeiros (100/9 cada), a minuta
exibe `50,00%` + 9 × `5,56%` = **100,04%**, enquanto o cálculo interno permanece exato e o
`divergencia_centavos` acusa apenas R$ 0,03. **O documento cartorário exibe percentuais que
não fecham 100%.** Este é o defeito que forçou a rota manual no caso real de 2026-07-09.

🟠 **P-2 — o mesmo truncamento no JSON de validação (cli.py:`_decimal_str`).**
```python
def _decimal_str(value: Decimal) -> str:
    return f"{value:.2f}"
```
Aplica-se também a `percentual`, de modo que o `inventario_validacao.json` — artefato de
conferência — não conserva a precisão original da entrada.

🟡 **P-3 — frações ideais não são representadas.** O domínio só conhece percentuais
(`Decimal`). Não existe tipo, campo ou renderização para `1/2`, `1/16`, `1/32` — a forma
convencional de grafar quinhões em escritura. Nada no código as calcula ou imprime.

🟢 **Não é defeito:** o resíduo de centavos em si. `33,33% × 3 = 99,99%` gera resíduo por
natureza da base decimal; a ADR-009 decide conscientemente **alertar e não corrigir**, e a
implementação cumpre a decisão em quatro canais (JSON, resumo, minuta, stderr).

**Estado dos critérios de revisão da ADR-009** (declarados na própria ADR):

| Critério | Situação observada |
|---|---|
| 1. Mais de 5 inventários/mês com alerta exigindo reescrita manual | **NÃO atingido** — frequência real ≈ 1–2/mês (2 dos 3 casos de agosto tiveram alerta) |
| 2. Fonte passa a fornecer distribuição por valor absoluto | **NÃO atingido** — entrada continua percentual |
| 3. Normativa explícita sobre centavo residual | não observado |
| 4. Alerta sendo ignorado pelo tabelião | **NÃO** — os artefatos reais mostram o alerta lido e destacado no topo dos fragmentos |
| 5. 12 meses desde a aprovação | ADR aprovada em 2026-05-21 → **revisão programada para 2027-05** |

**Conclusão:** a ADR-009 **não precisa ser revista agora**. O problema de precisão (P-1/P-2/P-3)
é **independente** dela — trata de formatação e de representação fracionária, não da política
de resíduo.

### 12.5. Renderização

| Aspecto | Estado |
|---|---|
| Separação cálculo × texto | 🟢 **completa** — `InventarioCalculator` devolve `ResumoInventario`; o renderer só formata. Nenhuma aritmética no renderer além de `_fmt_money`/`_fmt_pct` |
| Regras condicionais | 🟢 presentes e testadas: § 1.2/1.3 (meeiro ou advogado), § 10.1/10.2 (numeração muda sem meeiro), § 11 (bloco do meeiro), assinaturas, alerta de centavos, procedência imóvel × genérica |
| Placeholders | 🟢 explícitos e padronizados: `[QUALIFICAÇÃO DO …]`, `[DATA_LAVRATURA]`, `[MATRÍCULA DO IMÓVEL …]`, `[SELO_DIGITAL_…]`, `[EMOLUMENTOS]`, `[PREENCHER]` — verificados por `test_minuta_contem_placeholders_obrigatorios` |
| Anti-PII | 🟢 4 testes dedicados garantem ausência de PII em exemplos, template e saída renderizada |
| Estrutura | 🟢 §§ 1–20 + encerramento + assinaturas + campo de revisão humana (tabela de 5 etapas) — `test_minuta_contem_todas_as_secoes_de_1_a_20` |
| § 11 apenas alíneas | 🟢 decisão da serventia respeitada e testada (`test_minuta_secao_11_usa_apenas_alineas_sem_tabela`, `…_nao_contem_cabecalho_de_tabela`) |
| Templates | 🟡 **fonte dupla** — `renderer.py` é executável; o `.j2` é espelho não interpretado (Jinja2 não instalado). Há teste de referência cruzada, **não** de sincronia de conteúdo (TD-12) |
| Campos ausentes | 🟢 `descricao_generica` vazia cai em `[DESCRIÇÃO COMPLETA DO BEM …]`; beneficiário sem participação recebe "— sem participação em bens nesta partilha" |
| **Geração parcial** | 🔴 **INEXISTENTE** — não há como pedir apenas §§ 10 e 11. É exatamente o que os três casos de agosto precisaram e montaram à mão |
| Geração integral | 🟢 `inventario_minuta.md` (17–24 KB conforme o caso) |
| **Saída para o Engegraph** | 🔴 **INEXISTENTE como funcionalidade** — o caso de julho produziu `04_TEXTO_LIMPO_ENGEGRAPH.md` (21,5 KB) manualmente. O Markdown com `**negrito**`, `` `crase` `` e tabelas não é colável no ERP |
| ODT | 🟢 exportador próprio, stdlib-only, determinístico; cláusulas numeradas como corpo (estilo `CartorioBody` + `ClauseLabel`), não como headings — espelha o padrão da serventia (`ff09613`) |
| DOCX | 🔴 **INEXISTENTE** |
| PDF | 🔴 inexistente no módulo (os PDFs em `.ai_tmp/` foram gerados por ferramenta externa) |

### 12.6. Produto futuro — avaliação técnica do pipeline hipotético

Avaliação de cada elo da cadeia
`ITCD → extração → validação → classificação do cenário → cálculo → partilha → cláusulas →
minuta → saída Engegraph/ODT/DOCX`.
Classificação: **EP** extensão pequena · **EM** extensão moderada · **NC** nova capacidade ·
**RD** redesign de domínio.

| Elo | Existe hoje? | Esforço | Análise técnica |
|---|:--:|:--:|---|
| **ITCD → extração estruturada** | ❌ | **NC** | Fonte real é imagem/PDF do demonstrativo. Exige OCR ou parser de PDF, mapeamento de colunas ("Herança Legal", "Herança Recebida", "Excedente") e um schema de ITCD inexistente. **Risco alto:** documento fiscal com dados pessoais — colide com ADR-006 (dados permitidos para IA) e exige processamento estritamente local. **Nada disso está resolvido.** |
| **Validação da extração** | 🟡 parcial | **EM** | O validador atual cobre o `Inventario`; validar a *extração* (soma das ordens = total declarado, ordens sem lacuna, coluna correta) é camada nova. O caso real de agosto/02 já registrou divergência de R$ 0,01 entre o total declarado no ITCD e a soma das linhas — exatamente o tipo de checagem necessária. |
| **Classificação do cenário sucessório** | ❌ | **RD** | Inferir meeiro, representação, meio quinhão ou pré-morte a partir de valores é **interpretação jurídica**. O relatório do caso de julho recusa deliberadamente essa inferência ("não se concluiu representação, estirpe, substituição ou pré-morte"). Automatizar isso muda a natureza do produto: de determinístico para inferencial — exigiria ADR própria e colide com o princípio de que o sistema não decide silenciosamente. **Não recomendado.** |
| **Cálculo determinístico** | ✅ **PRONTO** | — | `InventarioCalculator`, 11 testes, `Decimal`/`ROUND_HALF_EVEN`. |
| **Partilha** | ✅ **PRONTO** | — | Distribuição bem a bem com totais por beneficiário e resíduo explícito. |
| **Cláusulas** | ✅ **PRONTO** | — | §§ 1–20 completos com redação cartorária referenciada (Res. 35 CNJ, Prov. 46/2020 CGJ-GO, Prov. 134/2022 CNJ, IN SRFB 1.112/2010). |
| **Precisão de frações e percentuais** | ❌ | **EP** | `_fmt_pct` com precisão configurável + campo opcional de fração ideal. Toca renderer, `_decimal_str` da CLI, resumo e os 6 golden files. Sem mudança de domínio. **É a menor correção de maior impacto documentado.** |
| **Saída fragmentada (§§ 10 e 11)** | ❌ | **EP** | Flag do tipo `--only-sections 10,11` ou `--fragment partilha`. O renderer já monta as seções em blocos independentes; o custo é de recorte e de contrato de CLI. **Substitui trabalho manual observado em 3 de 3 casos de agosto.** |
| **Saída "texto limpo" para o Engegraph** | ❌ | **EM** | Variante sem Markdown (sem `**`, sem `` ` ``, sem tabelas), pronta para colar no ERP. Já existe precedente manual (`04_TEXTO_LIMPO_ENGEGRAPH.md`) e o `odt_exporter` já resolve metade do problema (`_limpar_inline`). |
| **DOCX** | ❌ | **EM** | O ODT foi feito com `zipfile` + XML da stdlib; DOCX é análogo em esforço. **Só vale se houver demanda declarada** — nenhuma foi observada nos casos reais (o ODT abre no Writer e no Word). |
| **Doação como novo `tipo_ato`** | ❌ | **NC** | `tipo_ato` é `Literal` de um valor; o domínio (`Herdeiro`, `meação`, `monte partilhável`) é específico de sucessão. Suportar doação exige generalizar o domínio ou criar um módulo irmão em `notas/`. 1 caso real observado (2026-06-23). |

**Síntese do § 9.6 do escopo:** dos nove elos do pipeline hipotético, **três já estão prontos**
(cálculo, partilha, cláusulas), **três são extensões pequenas/moderadas de alto retorno**
(precisão de frações, saída fragmentada, texto limpo), **dois são capacidades novas de risco
alto** (extração de ITCD, doação) e **um não deveria ser implementado** (classificação
automática do cenário sucessório — é interpretação jurídica).

---

## 13. Compliance e infraestrutura

Auditoria estritamente técnica da relação existente entre o sistema e as exigências já
documentadas. **Nenhuma interpretação jurídica nova.** Legenda: **IS** implementado no
sistema · **DA** documentado apenas · **PE** processo externo · **RI** responsabilidade de
infraestrutura · **NE** não endereçado.

| Dimensão | Situação | Classificação | Evidência |
|---|---|:--:|---|
| **Autenticação individualizada** | Zero rotas protegidas; autoria por default literal `"gestor"` | **NE** | 37 rotas sem `Depends` de segurança |
| **Trilhas de auditoria (aplicação)** | Históricos append-only por módulo: `lgpd_action_status_history`, `compliance_requirement_status_history`, `created_by`/`updated_by` | **IS (parcial)** | 2 tabelas de histórico + campos de autoria |
| **Trilha transversal de mutações** | Não existe | **NE** | nenhum interceptador, nenhuma tabela de audit log global |
| **Retenção de trilhas ≥ 5 anos** | Nenhuma política de expurgo implementada (append-only, portanto retido) | **DA** | requisito descrito em `regulatory/cnj_213/roadmap.md` |
| **Backup (RPO ≤ 4 h / RTO ≤ 8 h)** | Nenhum código de backup; `_local_data` (582 MB) depende de rotina externa não verificável do repositório | **RI** | `docs/infrastructure/*`; TD-22 |
| **Continuidade (PCN/PRD)** | O módulo diagnostica a ausência e fornece modelo; não executa | **DA + PE** | `alignment.md` "Limitações do módulo" |
| **Evidências estruturadas** | `ComplianceEvidence` implementado (ADR-001) com POST/GET/PATCH | **IS — inativo** | tabela com **0 linhas** |
| **Vínculo requisito ↔ achado** | `RequirementFindingLink` implementado (ADR-002, referência fraca) | **IS — inativo** | **0 linhas** |
| **Status indicativo de requisito** | `ComplianceStatus` + histórico + recompute idempotente | **IS — inativo** | **0 linhas**; a própria camada declara-se *indicativa*, não declaratória de conformidade |
| **Retenção documental (temporalidade)** | Regras TEMP-001/002/003 implementadas e testadas | **IS — inativo** | `retention_rules = 0` ⇒ nenhum finding TEMP-* é emitido |
| **Inventário de ativos (G-02)** | `audit/scanner` com hash SHA-256 e manifest read-only — **executado em ambiente real** | **IS ✅** | `module_roadmap.md` Fase 1 |
| **Diagnóstico documental** | 7 regras DIAG-*, calibradas após execução real | **IS ✅** | commit `441a33e` |
| **Segurança de dados sensíveis** | 582 MB de documentos reais integralmente fora do git; `.gitignore` com 6 blocos dedicados; contratos anti-PII nos scripts RI (abortam se detectarem PII na saída) | **IS ✅** | verificado nesta auditoria |
| **Segmentação de rede, MFA, VPN, off-site** | Diagnosticados; não executáveis pelo sistema | **RI** | `alignment.md` |
| **Interoperabilidade / exports** | `exports/atlas/` vazio; exports com checksum/timestamp/usuário previstos e não implementados | **NE** | apenas `.gitkeep` |
| **Exportação de dados (LGPD)** | `GET /lgpd/actions/export.csv` implementado | **IS ✅** | rota ativa |
| **Documentação de conformidade** | Extensa: 45 requisitos Classe 3 mapeados, 73 itens de checklist de vistoria, dossiê de 12 seções, 11 documentos PROAD | **DA ✅** | `docs/regulatory/`, `docs/readiness/`, `docs/proad/` |
| **Prov. CNJ 195/2025 (IERI-e / SIG-RI)** | Base sanitizada e pacote de resposta produzidos pelo pipeline RI | **IS + PE** | dossiê PROAD; envio ao PROAD **não comprovável pelo repositório** |
| **Ferramentas de verificação de segurança** | bandit / pip-audit / gitleaks exigidos pelo CLAUDE.md § 5 e **não instalados** | **NE** | TD-10 |

**Nota metodológica exigida pelo próprio projeto:** nada nesta seção declara conformidade
regulatória. O sistema **gera evidências e registros**; a conformidade é aferida por quem
de direito.

**Observação crítica de § 13:** o eixo regulatório está na condição incomum de ter
**capacidade construída e inativa**. Ativá-lo (aplicar o seed `matriz_v1`, semear
`retention_rules`, promover a findings os achados do diagnóstico real) custa uma sprint
pequena e transforma 4.155 + 916 + 800 LOC já pagos de V1 para V3.

---

## 14. Oportunidades identificadas

Cada oportunidade está ancorada em um problema, uma capacidade existente ou uma evidência
observada nesta auditoria. Nenhuma é desconectada do domínio.

| # | Oportunidade | Ancoragem factual | Tipo |
|---|---|---|:--:|
| **F1** | **Precisão de frações e percentuais na minuta** (`NOTAS-FRACOES-1`) | Caso real 2026-07-09 exigiu minuta 100% manual; demonstrado: percentuais exibidos somam 100,04% | EP |
| **F2** | **Saída fragmentada de cláusulas + texto limpo para o Engegraph** | 3 de 3 casos de agosto montaram `clausulas_*.md` à mão; caso de julho produziu `04_TEXTO_LIMPO_ENGEGRAPH.md` à mão | EP + EM |
| **F3** | **Ingestão estruturada do demonstrativo de ITCD** | Fonte única real é imagem; transcrição manual em todos os 6 casos | NC |
| **F4** | **Doação como segundo tipo de ato notarial** | `_local_data/Notas/Doações/001/` (2026-06-23) — mesmo fluxo, resolvido sem código | NC |
| **F5** | **CI mínimo + declaração de dependências + gate de formatação** | TD-09, TD-23, TD-25; zero automação em 34 commits | EP |
| **F6** | **Reconciliação documental** (architecture, roadmap, testing, índices, POP) | TD-01, TD-02, TD-04, TD-11, TD-16, TD-27 | EP |
| **F7** | **Autenticação multiusuário** | TD-18; exigência estrutural CNJ 213 | NC |
| **F8** | **Trilha de auditoria transversal** | TD-19; depende de F7 | NC |
| **F9** | **Ativação operacional do eixo regulatório** (seed compliance + retention + promover achados a findings + re-executar scanner) | TD-26: 5.871 LOC prontos com 0 linhas de dados | EP |
| **F10** | **Promover pipeline RI a `app/modules/registro_imoveis/`** | TD-06 / DH-1; 6.605 LOC e 334 testes fora da arquitetura declarada | EM |
| **F11** | **Ciclo recorrente IERI-e / SIG-RI** | Prov. 195/2025 exige alimentação mensal; o pipeline já produz a base | EM |
| **F12** | **Knowledge Base normativa / IA** | ADR-004..008 *Propostos*; DHP-01..10 pendentes | RD |
| **F13** | **Retomada do painel financeiro** | Finance Core v1.2 completo e congelado; 0 linhas | EM |
| **F14** | **Backup verificável de `_local_data` (582 MB)** | TD-22; risco operacional externo ao código | PE |
| **F15** | **Push dos 2 commits locais para `origin/main`** | Dossiê PROAD e auditoria existem só nesta máquina | trivial |

---

## 15. Matriz estratégica

Notas de 0 a 5. **Atenção à polaridade:** em *Esforço* e *Risco técnico*, **5 = maior
esforço / maior risco** (pior). As oito primeiras colunas são "quanto maior, melhor".

| Frente | Valor oper. | Freq. | Econ. tempo | Red. erro | Urgência | Alavanc. | Evid. valor | Fundação | **Esforço** | **Risco** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **F2** Fragmentos + texto limpo Engegraph | 5 | 5 | 5 | 3 | 4 | 3 | 4 | 5 | **2** | **1** |
| **F5** CI + deps + formatação | 3 | 5 | 2 | 4 | 4 | 5 | 3 | 4 | **1** | **1** |
| **F1** Precisão de frações/percentuais | 4 | 4 | 4 | 5 | 4 | 3 | 4 | 5 | **2** | **2** |
| **F6** Reconciliação documental | 3 | 3 | 2 | 3 | 4 | 4 | 3 | 5 | **2** | **1** |
| **F9** Ativação do eixo regulatório | 4 | 2 | 3 | 3 | 3 | 3 | 3 | 5 | **1** | **1** |
| **F3** Ingestão estruturada do ITCD | 5 | 4 | 5 | 4 | 3 | 4 | 4 | 2 | **4** | **4** |
| **F11** Ciclo IERI-e / SIG-RI | 4 | 4 | 4 | 3 | 4 | 3 | 3 | 4 | **3** | **3** |
| **F4** Doação como novo ato | 4 | 2 | 3 | 3 | 2 | 4 | 2 | 3 | **4** | **3** |
| **F13** Painel financeiro | 2 | 2 | 2 | 2 | 1 | 2 | 1 | 4 | **3** | **2** |
| **F10** Promover RI a módulo | 2 | 1 | 1 | 2 | 2 | 3 | 3 | 4 | **4** | **3** |
| **F7** Autenticação multiusuário | 3 | 1 | 0 | 2 | 3 | 5 | 1 | 2 | **4** | **3** |
| **F8** Trilha transversal | 3 | 1 | 0 | 2 | 3 | 4 | 1 | 2 | **4** | **3** |
| **F12** Knowledge Base / IA | 3 | 2 | 3 | 2 | 1 | 4 | 0 | 1 | **5** | **5** |

### 15.1. Score agregado (fórmula explícita)

```
score = (valor + frequência + economia + redução_erro + urgência
         + alavancagem + evidência + fundação)          [0..40]
        − (esforço + risco)                              [0..10]

faixa possível: −10 … +40
```

A fórmula é intencionalmente simples e sem pesos: pesos exigiriam uma decisão humana sobre
prioridades que esta auditoria não pode tomar. **A tabela detalhada acima permanece a fonte
primária** — o score é apenas uma ordenação de leitura rápida.

| Pos. | Frente | Soma positiva | Penalidade | **Score** |
|:--:|---|:--:|:--:|:--:|
| 1 | **F2** Fragmentos + texto limpo Engegraph | 34 | 3 | **31** |
| 2 | **F5** CI + deps + formatação | 30 | 2 | **28** |
| 3 | **F1** Precisão de frações/percentuais | 29 | 4 | **25** |
| 4 | **F6** Reconciliação documental | 27 | 3 | **24** |
| 4 | **F9** Ativação do eixo regulatório | 26 | 2 | **24** |
| 6 | **F3** Ingestão estruturada do ITCD | 31 | 8 | **23** |
| 6 | **F11** Ciclo IERI-e / SIG-RI | 29 | 6 | **23** |
| 8 | **F4** Doação | 23 | 7 | **16** |
| 9 | **F13** Painel financeiro | 16 | 5 | **11** |
| 9 | **F10** Promover RI a módulo | 18 | 7 | **11** |
| 11 | **F7** Autenticação | 17 | 7 | **10** |
| 12 | **F8** Trilha transversal | 16 | 7 | **9** |
| 13 | **F12** Knowledge Base / IA | 16 | 10 | **6** |

**Leituras que a tabela detalhada revela e o score sozinho esconderia:**

- **F3** tem a **maior soma positiva depois de F2** (31) e cai para 6º lugar apenas pela
  penalidade de esforço/risco (8). É a frente de maior potencial, não a de maior retorno
  imediato.
- **F7** (autenticação) tem **alavancagem 5** — a mais alta da tabela junto com F5 — mas
  evidência de valor 1 e frequência 1. É estruturalmente certa e operacionalmente prematura.
- **F9** custa **esforço 1** e converte 5.871 LOC já pagos de V1 para V3. É a melhor razão
  retorno/custo da tabela.
- **F12** é a única frente com evidência de valor **0** e as duas penalidades no máximo.

---

## 16. Cenários estratégicos

### Cenário A — "Fechar a cintura" (estabilização de engenharia e governança)

| | |
|---|---|
| **Objetivo** | Tornar a qualidade verificável por máquina e a documentação confiável, antes de qualquer nova funcionalidade |
| **Frentes** | F5 (CI + PyYAML + gate de formatação) · F6 (architecture, roadmap, testing, índices, POP) · F15 (push) · decisão sobre `alembic check` (TD-24) |
| **Módulos envolvidos** | nenhum módulo de negócio — apenas `pyproject.toml`, `.github/`, `docs/` |
| **Benefício** | Elimina os 4 P1 e 2 dos P2; qualquer contribuição futura passa a ser verificada automaticamente; o próximo leitor do repositório para de precisar de arqueologia em `.ai_tmp/` para entender o estado |
| **Custo** | 1 sprint pequena |
| **Dependências** | 3 decisões humanas: adotar ou não `ruff format` como gate; alinhar modelos ou dispensar `alembic check`; autorizar o push |
| **Riscos** | Reformatar 25 arquivos gera um diff grande e ruidoso — deve ser um commit isolado, sem mistura com outras mudanças (CLAUDE.md § 2) |
| **Efeito de adiar** | Cada sprint futura carrega o mesmo risco de regressão silenciosa; o dossiê PROAD segue em máquina única |
| **Primeiros passos** | 1) declarar `PyYAML` no `pyproject`; 2) workflow com `pytest` + `ruff check`; 3) decidir formatação; 4) corrigir os 2 links do POP e commitá-lo |

### Cenário B — "Industrializar o que já dá valor" (aprofundar Inventários)

| | |
|---|---|
| **Objetivo** | Eliminar o trabalho manual que se repete em **todos** os casos reais |
| **Frentes** | F2 (fragmentos §§ 10–11 + saída texto limpo) → F1 (precisão de frações e percentuais) |
| **Módulos envolvidos** | `notas/inventarios` (renderer, cli, schemas, golden files) — nenhum outro |
| **Benefício** | Substitui trabalho manual **observado em 4 de 4 casos recentes**; remove a única limitação que já forçou rota 100% manual; mantém o determinismo e a política ADR-009 intactos |
| **Custo** | 2 sprints pequenas (F2 e F1 são independentes entre si e podem ser feitas em qualquer ordem) |
| **Dependências** | F1 exige regenerar os 6 golden files (procedimento já documentado em `notas_inventarios.md` § 7) e provavelmente uma ADR sobre representação de fração ideal |
| **Riscos** | Baixos e contidos: módulo stateless, sem banco, sem API, com 136 testes e golden byte-a-byte. O maior risco é de **regressão de redação** — mitigado pelos próprios golden files |
| **Efeito de adiar** | A cada ~16 dias, a serventia repete manualmente o recorte de cláusulas; casos com frações não convencionais (1/16, 1/32) continuam saindo do sistema |
| **Primeiros passos** | 1) especificar o contrato de `--fragment`/`--only-sections` a partir dos `clausulas_*.md` reais já existentes; 2) ADR de precisão/fração; 3) implementar; 4) regenerar golden |

### Cenário C — "Acender o que já está construído" (ativação do eixo regulatório)

| | |
|---|---|
| **Objetivo** | Converter 5.871 LOC de capacidade dormente em evidência regulatória viva |
| **Frentes** | F9 (aplicar seed `matriz_v1`; semear `retention_rules`; promover achados do diagnóstico real a `audit_findings`; re-executar scanner+diagnosis sobre o acervo atual) · F11 (ciclo IERI-e) |
| **Módulos envolvidos** | compliance, retention, audit (findings/scanner/diagnosis), pipeline RI |
| **Benefício** | O maior ganho de valor por linha de código nova (praticamente zero código novo); produz evidências datadas e rastreáveis para a vistoria CNJ 213 e para o ciclo do Prov. 195/2025 |
| **Custo** | 1 sprint pequena para a ativação (F9); esforço recorrente moderado para F11 |
| **Dependências** | Autorização para executar seeds no banco local; janela para re-executar o scanner sobre o acervo real (contrato read-only já formalizado) |
| **Riscos** | Baixo no código (tudo idempotente e testado); **médio no operacional** — re-executar o diagnóstico sobre 582 MB exige janela e disciplina de `--output-dir` |
| **Efeito de adiar** | Os artefatos de evidência mais recentes continuam sendo de maio/2026; numa vistoria, evidência de 4 meses atrás pesa menos que evidência do mês corrente |
| **Primeiros passos** | 1) rodar `python -m app.modules.compliance.seed`; 2) rodar o seed de retention; 3) re-executar scanner + diagnosis; 4) promover os achados relevantes a findings |

### Cenário D — "Fundação de identidade" (auth + trilha transversal)

| | |
|---|---|
| **Objetivo** | Endereçar as duas exigências estruturais do Prov. CNJ 213 ainda não iniciadas |
| **Frentes** | F7 (autenticação multiusuário) → F8 (trilha transversal de mutações) |
| **Módulos envolvidos** | novo módulo de identidade + migration + refit de todas as 37 rotas + substituição do default `"gestor"` |
| **Benefício** | Remove o gap estrutural mais visível numa vistoria; habilita uso por colaboradores |
| **Custo** | 2–3 sprints médias; a maior mudança transversal já feita no sistema |
| **Dependências** | Cenário A (mudança desse porte sem CI é imprudente); decisão sobre modelo de identidade (local × diretório da serventia); ADR obrigatória |
| **Riscos** | Os mais altos do conjunto: toca todos os módulos com API, muda semântica de autoria em dados já existentes (25 ações LGPD), e exige migration de backfill |
| **Efeito de adiar** | Enquanto o uso for monousuário e o valor estiver na CLI de notas (que não tem API), o gap é **regulatório e documental**, não operacional. O prazo global de 24 meses da Classe 3 corre desde a classificação |
| **Primeiros passos** | ADR de modelo de identidade; decidir se a trilha transversal usa interceptador SQLAlchemy ou middleware |

### Cenário E — "Nova família de atos" (doação)

| | |
|---|---|
| **Objetivo** | Estender o gerador para escrituras de doação a partir do mesmo demonstrativo de ITCD |
| **Frentes** | F4 |
| **Módulos envolvidos** | `notas/` — módulo irmão ou generalização do domínio de `inventarios` |
| **Benefício** | Replica o padrão de valor já comprovado em uma família vizinha; há 1 caso real documentado |
| **Custo** | 1–2 sprints médias |
| **Dependências** | Cenário B primeiro (a generalização deve partir de um `inventarios` já estabilizado, não de um em movimento); confirmação da frequência real de doações na serventia — **hoje desconhecida** |
| **Riscos** | Generalizar cedo demais o domínio (`Herdeiro`, `meação`, `monte partilhável` não existem em doação) pode degradar o módulo maduro. Alternativa mais segura: módulo irmão com domínio próprio |
| **Efeito de adiar** | Doações continuam sendo redigidas manualmente — custo real desconhecido, pois a frequência não foi medida |
| **Primeiros passos** | Medir a frequência de doações; decidir entre módulo irmão e generalização; ADR de fronteira |

### 16.1. Comparação e recomendação

| Cenário | Score médio das frentes | Custo | Risco | Evidência de valor |
|---|:--:|---|---|---|
| **A** — Cintura | 26,0 | 1 sprint pequena | muito baixo | indireta (dívida registrada) |
| **B** — Inventários | 28,0 | 2 sprints pequenas | baixo | **direta, V4** |
| **C** — Ativação regulatória | 23,5 | 1 sprint pequena + recorrente | baixo/médio | indireta (capacidade ociosa) |
| **D** — Identidade | 9,5 | 2–3 sprints médias | alto | nenhuma |
| **E** — Doação | 16,0 | 1–2 sprints médias | médio | 1 caso |

**Recomendação que decorre das evidências: A → B, com C em frente operacional paralela.**

O raciocínio, explicitamente: **A** primeiro porque é a mais barata do conjunto e porque
fazer **B** sem CI significa mexer no único módulo em uso produtivo sem rede de proteção
automatizada. **B** em seguida porque é a única frente com evidência **V4** e porque ataca
trabalho manual que se repetiu em 100% dos casos recentes. **C** em paralelo porque não
compete por código com B (módulos distintos) e porque tem a melhor razão retorno/custo do
conjunto. **D** fica para depois — não por ser menos importante, mas porque nenhum uso real
a demanda hoje, e o custo de fazê-la sem CI e sobre uma documentação defasada é
desproporcional. **E** depende de um dado que ninguém mediu: a frequência de doações.

Registre-se explicitamente, conforme exigido pelo escopo: **Inventários não foi escolhido
por ser o módulo favorito nem por sugestão prévia** — foi escolhido porque é o único com
seis casos reais datados, o único cujo uso sobreviveu a 3 meses sem desenvolvimento, e o
único cujas lacunas estão documentadas em relatórios de caso real produzidos pela própria
serventia. E registre-se também que **a primeira recomendação não é Inventários, e sim
estabilização** — porque a evidência mostra 34 commits sem nenhuma verificação automática.

---

## 17. Roadmap recomendado

> **Este roadmap NÃO altera `docs/roadmap.md` nem nenhum outro roadmap oficial.** É uma
> recomendação preliminar contida neste relatório, sujeita a aprovação humana.

### HORIZONTE A — ESTABILIZAÇÃO *(próxima sprint)*

| # | Item | Dívida | Esforço |
|---|---|---|---|
| A.1 | Declarar `PyYAML` em `[project].dependencies` | TD-23 (P1) | trivial |
| A.2 | CI mínimo: `pytest` + `ruff check` em push/PR | TD-09 (P1) | pequeno |
| A.3 | Decidir e aplicar o gate de `ruff format` (commit isolado) | TD-25 (P2) | pequeno |
| A.4 | Decidir sobre `alembic check`: alinhar modelos **ou** ADR + exclusão dos gates | TD-24 (P2) | pequeno |
| A.5 | Corrigir os 2 links de ADR-009 no POP e commitá-lo | TD-27 (P3) | trivial |
| A.6 | Reescrever `architecture.md` e `roadmap.md` a partir deste relatório | TD-01, TD-02 (P1) | médio |
| A.7 | Atualizar `testing.md` (48 → 904), `docs/README.md`, `decisions/index.md` (+ADR-009), CLAUDE.md § 9 | TD-11, TD-04 | pequeno |
| A.8 | Push dos 2 commits locais para `origin/main` **mediante autorização explícita** | risco de perda | trivial |

**Critério de saída:** CI verde em `main`; zero P1 aberto; `docs/architecture.md` e
`docs/roadmap.md` descrevendo o sistema que existe.

### HORIZONTE B — PRÓXIMA GERAÇÃO DE VALOR *(2 a 4 sprints seguintes)*

| # | Item | Ancoragem | Esforço |
|---|---|---|---|
| B.1 | `NOTAS-FRAGMENTOS-1` — saída seletiva de cláusulas (§§ 10 e 11) | 3 de 3 casos de agosto montaram isso à mão | EP |
| B.2 | `NOTAS-ENGEGRAPH-1` — variante "texto limpo" sem Markdown | `04_TEXTO_LIMPO_ENGEGRAPH.md` manual (julho) | EM |
| B.3 | `NOTAS-FRACOES-1` — precisão configurável + fração ideal opcional (+ ADR) | caso real 2026-07-09 forçou minuta manual | EP |
| B.4 | `REG-ATIVACAO-1` — seeds de compliance e retention; promoção de achados a findings; re-execução de scanner+diagnosis *(frente operacional paralela)* | TD-26: 5.871 LOC com 0 dados | EP |

**Critério de saída:** um caso real de inventário produzido de ponta a ponta **sem etapa
manual de recorte**; tabelas de compliance e retention povoadas com evidência datada.

### HORIZONTE C — EVOLUÇÃO ESTRUTURAL *(depois de B, com decisão humana explícita)*

| # | Item | Pré-requisito |
|---|---|---|
| C.1 | Ingestão estruturada do demonstrativo de ITCD (parser + validação de extração, processamento estritamente local) | ADR própria; compatibilidade com ADR-006 |
| C.2 | Decisão DH-1: promover pipeline RI a `app/modules/registro_imoveis/` ou formalizar camada `tools/` | blueprint de julho aprovado |
| C.3 | Ciclo recorrente IERI-e / SIG-RI | C.2 |
| C.4 | Autenticação multiusuário + trilha transversal | Horizonte A completo; ADR de identidade |
| C.5 | Doação como família de atos (módulo irmão) | medição da frequência real; Horizonte B concluído |

**Fora de horizonte (mantidos bloqueados, corretamente):** Knowledge Base / IA (DHP-01..10
pendentes), Document Registry, integração Atlas, Finance Etapas 2–7.

---

## 18. Bloqueadores

| # | Bloqueador | Natureza | Impede |
|---|---|---|---|
| **BL-1** | Decisão sobre adotar `ruff format` como gate | humana | A.3 |
| **BL-2** | Decisão sobre `alembic check` (alinhar modelos × dispensar o gate) | humana | A.4 e o uso de migrations como gate de CI |
| **BL-3** | Autorização explícita para `git push` (regra permanente do CLAUDE.md § 6) | humana | A.8 |
| **BL-4** | DH-1 — destino do pipeline RI (6.605 LOC) | humana | C.2, C.3 |
| **BL-5** | DHP-01..10 — governança de Knowledge Base / IA | humana | toda a frente F12 |
| **BL-6** | Frequência real de doações na serventia | **dado inexistente** | dimensionar F4/C.5 |
| **BL-7** | Status do protocolo PROAD (prazo estimado era 2026-06-10; hoje é 2026-09-02) | externa | avaliar urgência de F11 |
| **BL-8** | Existência e periodicidade do backup de `_local_data` (582 MB) | externa / infraestrutura | mitigar RS-2 |
| **BL-9** | Aprovação do roadmap reconciliado e do blueprint da auditoria de julho | humana | C.2 |
| **BL-10** | Decisão sobre representação de fração ideal (ADR) | humana | B.3 |

---

## 19. Riscos

| # | Risco | Prob. | Impacto | Evidência | Mitigação sugerida |
|---|---|:--:|:--:|---|---|
| **RS-1** | **Regressão silenciosa em `main`** — sem CI, a única barreira é a disciplina de uma pessoa em uma máquina | alta | alto | 34 commits, zero verificação automática | A.2 |
| **RS-2** | **Perda do dossiê PROAD e da auditoria** — 2 commits existem só localmente; 582 MB de `_local_data` dependem de rotina externa não verificável | média | **muito alto** | `origin/main` 2 commits atrás; TD-22 | A.8 + confirmar backup |
| **RS-3** | **Instalação limpa quebra em runtime** — `PyYAML` não declarada; o caminho `.yaml` é o usado em 100% dos casos reais | média | alto | TD-23 | A.1 |
| **RS-4** | **Decisão errada por documentação defasada** — `architecture.md` afirma "finance é o único módulo ativo"; existem 8 | alta | médio | TD-01, TD-02 | A.6 |
| **RS-5** | **Erro de redação em escritura por percentual mal exibido** — a minuta pode apresentar percentuais que somam 100,04% | média | **alto** (documento público) | demonstrado no § 12.4 | B.3 (mitigação parcial hoje: revisão humana obrigatória + checklist de 18 blocos) |
| **RS-6** | **Fadiga do recorte manual** — a cada caso, alguém extrai §§ 10 e 11 à mão; erro de cópia é plausível | média | médio | 3 de 3 casos de agosto | B.1 |
| **RS-7** | **Evidência regulatória envelhecendo** — os artefatos de auditoria mais recentes são de maio/2026 | média | médio | nenhum `file_inventory.json` recente no ambiente | B.4 |
| **RS-8** | **Capacidade construída e nunca validada em uso** — 4.155 LOC de compliance sem uma única linha de dado real; o primeiro uso pode revelar lacunas de modelagem | média | médio | § 6.3 | B.4 |
| **RS-9** | **Conhecimento tácito fora do git** — as lacunas mais precisas do módulo de notas estão em `.ai_tmp/` (gitignorado), não em `docs/` | alta | médio | `01_RELATORIO_ANALISE_INVENTARIO_VEICULO.md` § 14 propõe `NOTAS-INVENTARIO-FRACOES-1`, que **não existe em nenhum documento versionado** | promover a proposta a documento versionado |
| **RS-10** | **Degradação do módulo maduro ao generalizar para doação** | baixa | médio | domínio de `inventarios` é específico de sucessão | preferir módulo irmão a generalização |
| **RS-11** | **Gap regulatório na vistoria** (auth e trilha transversal ausentes) | média | alto | TD-18, TD-19 | C.4, dentro do prazo de 24 meses |

---

## 20. Próximas decisões requeridas

| # | Decisão | Quem decide | Bloqueia | Recomendação técnica desta auditoria |
|---|---|---|---|---|
| **D-A** | Adotar `ruff format` como gate obrigatório? | gestor/tech | A.3 | **Sim** — em commit isolado, sem misturar com mudanças funcionais |
| **D-B** | `alembic check`: alinhar declarações dos modelos **ou** registrar exceção em ADR? | gestor/tech | A.4, CI de migrations | **Alinhar os modelos** — mantém o gate utilizável a custo baixo |
| **D-C** | Autorizar `git push` dos 2 commits locais para `origin/main`? | **gestor** | A.8, RS-2 | **Sim, com urgência** — é a mitigação mais barata do maior risco |
| **D-D** | Qual a próxima frente funcional: B (Inventários), C (ativação regulatória) ou D (identidade)? | gestor | Horizonte B | **B, com C em paralelo** — evidência V4 × capacidade ociosa; D quando houver uso multiusuário |
| **D-E** | Aprovar o contrato de saída fragmentada (quais seções, qual formato)? | tabeliã + gestor | B.1 | Partir dos `clausulas_*.md` reais já existentes como especificação |
| **D-F** | Aprovar ADR de precisão de percentual e fração ideal | gestor/tech | B.3 | Precisão configurável (default 2 casas, ≥3 quando necessário) + fração opcional; sem quebrar o contrato atual |
| **D-G** | DH-1: promover pipeline RI a módulo? | gestor | C.2, C.3 | Promover — 6.605 LOC e 334 testes não deveriam viver em `scripts/` |
| **D-H** | Qual roadmap tem precedência entre os 6 existentes? | gestor | TD-16 | `docs/roadmap.md` como único autoritativo; os demais como anexos por domínio |
| **D-I** | Medir a frequência real de doações na serventia | gestor | C.5 | Dado inexistente hoje — sem ele, F4 não é dimensionável |
| **D-J** | Confirmar rotina de backup de `_local_data` (582 MB) | gestor/infra | RS-2 | Fora do escopo do repositório; requer confirmação externa |
| **D-K** | Qual o status atual do protocolo PROAD? | gestor | avaliação de urgência de F11 | O repositório não tem essa informação |
| **D-L** | DHP-01..10 (Knowledge Base / IA) | gestor | F12 | Manter bloqueado — a decisão de bloquear continua correta |

---

## 21. Apêndice de evidências

### 21.1. Comandos executados (todos read-only)

```
git rev-parse --abbrev-ref HEAD ; git rev-parse HEAD ; git rev-parse origin/main
git rev-list --left-right --count origin/main...HEAD
git status --short ; git diff --name-only ; git diff --cached --name-only
git ls-files --others --exclude-standard ; git tag ; git stash list ; git branch -a
git log -40 --format=... ; git rev-list --count HEAD
.venv/Scripts/python.exe --version ; -m pip freeze
.venv/Scripts/python.exe -m pytest -q --tb=short
.venv/Scripts/python.exe -m pytest -q -rs --tb=no -p no:cacheprovider
.venv/Scripts/python.exe -m pytest -q -W default -p no:cacheprovider
.venv/Scripts/python.exe -m pytest --collect-only -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m alembic heads | history | current | check
.venv/Scripts/python.exe -c "<comparação Base.metadata × sqlite_master>"
.venv/Scripts/python.exe -c "<contagem de linhas por tabela>"
.venv/Scripts/python.exe -c "<demonstração de _fmt_pct e do cenário 9 herdeiros>"
find / grep sobre app, scripts, tests, docs, outputs, .ai_tmp, _local_data (metadados)
```

**Nenhum comando de escrita foi executado**, exceto a criação deste arquivo. Nenhum
`alembic upgrade`/`downgrade`. Nenhuma instalação ou atualização de dependência. Nenhum
`git add`, `commit` ou `push`. Nenhuma alteração em `_local_data/`.

### 21.2. Evidência de uso real do gerador de inventário

Diretórios de caso encontrados (metadados de arquivo; **nenhum conteúdo pessoal reproduzido**):

| Data | Diretório | Caso | Divergência de centavos |
|---|---|---|---|
| 2026-05-22 | `outputs/…/manual/simples`, `.../sem_meeiro` | validação dos 2 exemplos canônicos | — |
| 2026-05-23 | `outputs/…/manual/inventario_real_001` + `.ai_tmp/…/inventario_real_001/` | **caso real 001** | — |
| 2026-05-25 | `.ai_tmp/…/inventario_real_002/` | **caso real 002** | — |
| 2026-07-09 | `.ai_tmp/…/veiculo_base/` (7 artefatos, incl. ODT, PDF e texto Engegraph) | **caso real — veículo, 10 ordens, R$ 16.374,00** | R$ 0,03 (frações 1/16 e 1/32) |
| 2026-08-02 | `.ai_tmp/…/meeira_8_herdeiros/` | **caso real — meeira + 8 herdeiros, 2 bens, R$ 137.000,80** | **R$ 0,01** |
| 2026-08-13 | `.ai_tmp/…/meeira_2_herdeiros/` | **caso real — meeira + 2 herdeiros, 12 bens, R$ 3.820.546,86** | **R$ 0,01** |
| 2026-08-29 | `.ai_tmp/…/sem_meeiro_8_herdeiros/` | **caso real — sem meeiro, 8 herdeiros, R$ 150.000,00** | nenhuma |

Em cada um dos três casos de agosto existe um arquivo `clausulas_*.md` — **fragmento
manual** das §§ 10 e 11 extraído da minuta completa.

### 21.3. Demonstração executável da perda de precisão (§ 12.4)

```
_fmt_pct(Decimal("3.125"))   → "3,12%"     # 1/32 deixa de ser representável
_fmt_pct(Decimal("5.5556"))  → "5,56%"
_fmt_pct(Decimal("0.005"))   → "0,00%"     # participação desaparece

Cenário: meeira 50% + 9 herdeiros (100/9 cada), 1 veículo de R$ 16.374,00
  patrimônio        = 16374.00
  meação            =  8187.00
  monte partilhável =  8187.00
  divergencia_centavos = 0.03
  percentual exibido por herdeiro = "5,56%"
  SOMA DOS PERCENTUAIS EXIBIDOS   = 50,00 + 9 × 5,56 = 100,04 %
```

### 21.4. Arquivos sensíveis identificados (tipo · caminho · função · risco)

Registrados conforme § 10 do escopo — **sem reprodução de conteúdo**.

| Tipo | Caminho | Função | Risco |
|---|---|---|---|
| Acervo documental real | `_local_data/serventia_docs/` (477 MB) | documentos operacionais da serventia | alto — PII; **gitignorado**, nunca lido nesta auditoria |
| Base LGPD/INOVA | `_local_data/LGPD - inova/` (28 MB) | políticas, certificados, avaliações de fornecedores | alto — **gitignorado** |
| Base RI | `_local_data/ri_inventory/` (71 MB; 127 PDFs brutos + SQLite 3,9 MB) | matrículas e indicadores reais | alto — **gitignorado**; pipeline aborta se detectar PII na saída |
| Pacote PROAD | `_local_data/proad_final_package/` (6,1 MB) | pacote ODT/PDF de resposta à Corregedoria | médio/alto — **gitignorado** |
| Caso de doação | `_local_data/Notas/Doações/001/` (312 KB; 6 imagens de ITCD) | demonstrativo fiscal + proposta de cláusula | alto — **gitignorado**; apenas nomes de arquivo lidos |
| Banco de desenvolvimento | `cartorio.db` (385 KB) | 25 ações LGPD de fonte real | médio — **gitignorado**; apenas contagens lidas |
| Áreas de trabalho de caso | `.ai_tmp/notas_inventarios/*` | insumos e saídas dos casos reais | médio — **gitignorado**; os artefatos gerados declaram-se sem PII |
| Configuração de ambiente | `.env.example` (versionado), `.env` (ausente/ignorado) | configuração | baixo |
| Credenciais / tokens | **nenhum encontrado** | — | — |

**Verificação de higiene:** nenhum segredo, credencial, dump ou dado pessoal foi encontrado
sob controle de versão. O `.gitignore` possui 6 blocos dedicados a dados sensíveis (banco,
`_local_data`, exports de auditoria, artefatos RI, padrões `*_matriculas*`/`*_ieri*`/
`*_sanitized*`, temporários). Este relatório não reproduz nenhum dado pessoal, nenhum
conteúdo de escritura e nenhum trecho de documento real.

### 21.5. Estado final do Git

**Estado no início da sprint:**

```
git status --short
?? docs/modules/notas_inventarios/
```

**Estado ao término da sprint** (após a criação deste próprio relatório):

```
git status --short
?? docs/modules/notas_inventarios/
?? docs/reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md
```

`HEAD` permaneceu em `dd5b3be5de65e86f27b04dd18a8b8dee207b1584`; `git diff --name-only` e
`git diff --cached --name-only` retornaram vazio. A única diferença entre os dois estados é
o arquivo criado por esta sprint.

**Confirmação explícita de arquivos pré-existentes:**
`docs/modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md` **já estava untracked
antes desta sprint** e não foi modificado, movido, corrigido nem commitado.

> **Nota de rastreabilidade (adendo de 2026-09-03).** Três correções factuais foram
> aplicadas a este relatório no início da sprint `CARTORIO-SYSTEM-ENGINEERING-STABILIZATION-1`,
> antes de sua incorporação ao controle de versão: (a) § 1 — a leitura do veredito passou a
> distinguir pendências de engenharia de pendências funcionais do módulo de notas; (b) § 9.2
> e § 9.3 — a contagem de achados novos foi corrigida de 4 para 5 (TD-23 a TD-27) e o total
> de P2 de 11 para 13, conferido item a item; (c) § 21.5 — a evidência de `git status` passou
> a refletir o estado real ao término da sprint. O diagnóstico, as evidências e as
> recomendações permanecem inalterados.

### 21.6. Conformidade com o escopo da sprint

| Restrição | Cumprida |
|---|:--:|
| Nenhuma funcionalidade implementada | ✅ |
| Nenhum refactor | ✅ |
| Nenhum bug corrigido | ✅ |
| Nenhum roadmap atualizado | ✅ |
| Nenhuma documentação existente alterada | ✅ |
| Nenhum commit | ✅ |
| Nenhum push | ✅ |
| Nenhum código, teste ou migration alterado | ✅ |
| Nenhum arquivo sensível alterado | ✅ |
| Nenhum dado pessoal reproduzido | ✅ |
| Nenhum arquivo enviado a API externa | ✅ |
| `_local_data` inalterado | ✅ |
| Única escrita: este relatório | ✅ |

---

*Fim do relatório — `CARTORIO-SYSTEM-STRATEGIC-REBASELINE-2026-1` · 2026-09-02.*
