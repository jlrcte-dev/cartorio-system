# 01 — Inventário do Repositório

> Sprint **CARTORIO-REPOSITORY-REBASELINE-1** — 2026-07-09.
> Documento de diagnóstico. Somente leitura; nenhum arquivo preexistente foi alterado.
> Dados brutos completos em [`inventory_files.csv`](inventory_files.csv).

---

## 1. Baseline do Git

| Item | Valor |
|------|-------|
| Raiz do repositório | `C:\Users\João\Documents\cartorio_system` |
| Nome do projeto | `cartorio-system` (pyproject.toml, v0.1.0) |
| Branch atual | `main` |
| HEAD | `6ed62cb2c9f62d3eb69331007e4a3894094fda0e` |
| Mensagem do HEAD | `docs(knowledge_base): add governance blueprint and Phase 1 allowlist` (2026-05-25) |
| Remoto | `origin` → `https://github.com/jlrcte-dev/cartorio-system.git` |
| Divergência com remoto | Nenhuma detectada (`main...origin/main` sem ahead/behind no momento da leitura; sem `fetch` executado) |
| Tags | Nenhuma |
| Branches locais | Apenas `main` |
| Stashes | Nenhum |
| Arquivos versionados | 242 |
| Arquivos untracked | 2 |
| Arquivos modificados não commitados | 12 (todos em `docs/proad/`) |
| Arquivos staged | 0 |

### 1.1 Working tree — trabalho não commitado

**Modificados (12):** `docs/proad/RESPOSTA_PROAD_ADEQUACAO_PROVIMENTO_213.md` e os 11 documentos `docs/proad/resposta_ieri_2026/00…10` (total: +328/−415 linhas).

**Untracked (2):**
- `docs/modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md`
- `docs/proad/resposta_ieri_2026/11_relatorio_parcial_atualizacao_ieri_sig_ri.md`

**Observação de risco:** o HEAD é de 2026-05-25; as alterações locais correspondem a sprints documentais posteriores (harmonização PROAD, plano de ação simplificado, relatório parcial). Há ~6 semanas de trabalho documental sem commit. Ver TD-05 no registro de dívidas.

**Observação de EOL:** `git diff` emite `warning: LF will be replaced by CRLF` para os 12 arquivos PROAD — os arquivos do working tree estão com LF sob `core.autocrlf=true`; `.gitattributes` só normaliza `tests/golden/**`. Ver TD-15.

### 1.2 Últimos 30 commits

Faixa `6ed62cb` (2026-05-25) ← `2e329e0`. Padrão consistente de conventional commits (`feat(notas):`, `docs(compliance):`, `fix(notas):`), commits pequenos e temáticos, 1 sprint por commit. Sem commits de merge. Cadência: ~30 commits entre 2026-05-04 e 2026-05-25; **nenhum commit desde 2026-05-25**.

### 1.3 Presenças relevantes fora do versionamento (ignoradas corretamente)

| Item | Tipo | Tamanho | Risco | Situação |
|------|------|---------|-------|----------|
| `cartorio.db` | Banco SQLite local (dev) | 385 KB | Alto se versionado | Ignorado (`*.db`) ✅ |
| `_local_data/` | Documentos reais da serventia (LGPD-INOVA, PROAD, RI, Notas, serventia_docs) | **582 MB / ~1.944 arquivos** | Alto (PII/documentos reais) | Ignorado ✅ |
| `outputs/` | Saídas manuais do gerador de minutas | pequeno | Médio | Ignorado ✅ |
| `.ai_tmp/` | Artefatos de sessões de IA (sprint_5b, veiculo_base) | pequeno | Médio | Ignorado ✅ |
| `apresentacao_executiva_cartorio_system_mvp.html` | Artefato gerado (raiz) | 79 KB | Baixo | Ignorado ✅ |
| `docs/reports/RELATORIO_EXECUTIVO_CARTORIO_SYSTEM_DIRETORIA.pdf` | PDF gerado | — | Baixo | Ignorado ✅ |
| `cartorio_system.egg-info/`, caches, `.venv/`, `.claude/`, `.vscode/` | Build/caches/estado local | — | Baixo | Ignorados ✅ |

**Nenhuma credencial versionada foi encontrada.** `.env.example` contém apenas chaves de configuração não sensíveis (nomes de app, URL SQLite local, prefixo de API); `.env` real não existe no repositório e está no `.gitignore`.

---

## 2. Distribuição dos arquivos versionados

### 2.1 Por diretório de topo (242 arquivos)

| Diretório | Qtde | Conteúdo |
|-----------|------|----------|
| `app/` | 91 | Código de produção (8 módulos ativos + 6 placeholders) |
| `docs/` | 74 | Documentação (técnica, normativa, operacional, histórica) |
| `tests/` | 46 | 40 arquivos de teste + conftest + 6 golden files |
| `alembic/` | 13 | 10 migrations + env.py + mako + (alembic.ini na raiz) |
| `scripts/` | 8 | 7 ferramentas locais RI + 1 gerador de PDF |
| raiz | 10 | READMEs, governança, configuração |

### 2.2 Por extensão

`.py` 147 · `.md` 80 · `.yaml` 2 · `.json` 2 (golden) · `.toml` 1 · `.j2` 1 · `.ini` 1 · `.mako` 1 · `.css` 1 · outros 6.

### 2.3 Linhas de código (aprox., sem `__pycache__`)

| Área | LOC | Observação |
|------|-----|------------|
| `app/modules/compliance` | 4.155 | inclui seed `matriz_v1.py` (50 KB) |
| `app/modules/audit` | 3.786 | scanner + findings + diagnosis |
| `app/modules/notas` | 2.119 | layout hexagonal (domain/application/infrastructure/interfaces) |
| `app/modules/lgpd` | 1.022 | |
| `app/modules/retention` | 916 | |
| `app/modules/finance` | 679 | |
| `app/core` + `app/db` + `app/interfaces` | 158 | fundação enxuta |
| **`scripts/` (total)** | **7.366** | **maior "módulo" do repositório — ver §4** |
| `tests/` | 12.802 | |

### 2.4 Maiores arquivos versionados

| Arquivo | Tamanho | Categoria |
|---------|---------|-----------|
| `docs/document_registry/EXPECTED_DOCUMENTS_CNPFE_GO_INITIAL_MATRIX.md` | 69 KB | doc normativa (blueprint) |
| `docs/analysis/lgpd_module_context_report.md` | 64 KB | relatório histórico |
| `docs/ai/AI_LEGAL_TOOLS_INVESTIGATION.md` | 62 KB | relatório histórico |
| `scripts/local_tools/extract_ri_rural_inventory.py` | 60 KB | ferramenta local |
| `docs/regulatory/cnj_213/regulatory_integration_blueprint.md` | 50 KB | blueprint |
| `app/modules/compliance/seed_data/matriz_v1.py` | 49 KB | seed de dados |
| `scripts/local_tools/analyze_ri_real_json.py` | 48 KB | ferramenta local |
| `docs/reports/RELATORIO_EXECUTIVO_..._DIRETORIA.md` | 43 KB | relatório histórico |

Nenhum arquivo binário grande versionado. Nenhum arquivo acima de 100 KB.

---

## 3. Duplicatas, órfãos e inconsistências de nomenclatura

- **Duplicatas exatas (hash MD5 sobre os 244 arquivos):** nenhuma.
- **Duplicata conceitual:** a minuta de inventário existe em duas formas — `renderer.py` (fonte executável) e `app/modules/notas/inventarios/infrastructure/templates/inventario_extrajudicial_padrao.md.j2` (espelho declarado, não consumido em runtime — não há `jinja2` no venv nem import). Decisão consciente documentada, mas cria risco de divergência silenciosa (TD-12).
- **Referências órfãs:** `docs/operations/engegraph.md` é referenciado por `docs/architecture.md:151`, `docs/modules/audit.md:323` e `docs/quality/risk_register_model.md:162`, **mas não existe** no repositório (TD-03).
- **Nomenclatura:** convenção mista — `snake_case` minúsculo em docs técnicos vs `SCREAMING_CASE` em docs normativos/relatórios (`RESPOSTA_PROAD_...`, `KNOWLEDGE_BASE_BLUEPRINT`). Aceitável se formalizado; hoje é implícito. Não foram encontrados sufixos problemáticos (“final”, “v2”, “novo”) em arquivos versionados.
- **Artefato gerado versionado:** `docs/reports/generated/relatorio_pdf.css` — insumo do gerador de PDF, versionado numa pasta chamada `generated/` (nome sugere saída, conteúdo é insumo). Menor, mas confuso.
- **Documento operacional dentro de área de código:** não encontrado — separação `app/` × `docs/` respeitada.

---

## 4. Achado principal do inventário

**O pipeline de Registro de Imóveis (RI) vive inteiro em `scripts/local_tools/` (7 ferramentas, ~7,3 mil LOC) com 6 arquivos de teste dedicados (~334 testes), sem pertencer a `app/modules/`.** É código de produção de fato (testado, com contratos anti-PII), mas fora da arquitetura modular declarada em `docs/architecture.md`. O doc `docs/modules/registro_imoveis.md` declara o módulo como "Pré-implementação — análise e base sanitizada apenas", o que descreve corretamente a ausência de `app/modules/registro_imoveis/`, mas subrepresenta o volume de código já existente. Ver `02_DIAGNOSTICO_ARQUITETURAL.md` §5 e TD-06.

---

## 5. Categorias (resumo do CSV)

| Categoria | Qtde aprox. |
|-----------|-------------|
| Código de produção (`app/` + `scripts/`) | 105 |
| Testes | 41 |
| Golden files | 6 |
| Migrations | 10 |
| Configuração | 9 |
| Interface/API | 4 |
| Domínio (notas) | 3 |
| ADR/decisão arquitetural | 12 |
| Documentação técnica | 18 |
| Documentação normativa/compliance | 19 |
| Documentação operacional | 12 |
| Documentação funcional (blueprints sem código) | 8 |
| Relatório histórico | 9 |
| Artefato gerado versionado | 2 |
| Placeholder (pacotes vazios) | 6 |

(Contagens derivadas de `inventory_files.csv`; categorias atribuídas por heurística de caminho + leitura amostral — classificações individuais podem ser refinadas.)
