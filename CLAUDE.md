# CLAUDE.md — Cartório System

Instrução operacional para Claude Code. Leia antes de executar qualquer tarefa.
Documento completo de governança: [`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md)

---

## 1. Identidade do projeto

- **Cartório System** é o backend interno e independente da serventia Cartório Costa Teixeira.
- Não substitui o **Engegraph** (ERP cartorial). Coexiste com ele.
- O **Atlas** é integração futura — nunca dependência operacional. Integração ocorre por exports estruturados em `exports/atlas/`, nunca por banco ou código compartilhado.
- O sistema executa, registra, organiza, audita e gera evidências estruturadas.
- Lida com dados sensíveis: financeiros, cartorários, documentais e regulatórios.

---

## 2. Regras permanentes — nunca violar

```
NÃO alterar .env ou arquivos de configuração sensível
NÃO versionar cartorio.db, dumps reais ou credenciais
NÃO expor dados sensíveis (CPF, documentos, tokens, valores)
NÃO executar migrations em produção sem autorização explícita + backup
NÃO fazer git push sem autorização explícita do usuário
NÃO fazer git push --force em main
NÃO apagar diretórios fora do escopo explícito da tarefa
NÃO alterar arquivos fora do repositório cartorio_system
NÃO misturar múltiplas sprints no mesmo commit
NÃO acessar ou transmitir credenciais de nenhum sistema
NÃO rodar scripts contra produção sem autorização formal
NÃO declarar conformidade regulatória plena — o sistema gera evidências e registros
NÃO concordar automaticamente com decisões que apresentem risco técnico, regulatório ou de dados
```

---

## 3. Hierarquia de fontes (em caso de conflito)

1. Segurança, integridade e proibições permanentes (acima)
2. Escopo explícito da tarefa atual
3. `CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`
4. ADRs em `docs/decisions/`
5. Documentação dos módulos em `docs/modules/`
6. Roadmaps e relatórios técnicos
7. Sugestões inferidas pelo Claude

**Conflito crítico entre 1–4 → parar, reportar, aguardar decisão.**

---

## 4. Fluxo padrão de trabalho

### Antes de implementar

1. Rodar `git status` — entender estado atual do repositório.
2. Ler contexto: `docs/roadmap.md`, `docs/modules/<módulo>.md`, `docs/audit/` (se módulo audit), ADR relacionado em `docs/decisions/`.
3. Identificar módulo dono da entidade afetada.
4. Verificar se há risco: regulatório, financeiro, LGPD, dados reais, migration, acoplamento.
5. Reportar qualquer risco antes de prosseguir.

### Durante

- Fazer mudança mínima eficaz — sem over-engineering.
- Preservar arquitetura: domínio protegido, módulos independentes.
- Referências entre módulos via referência fraca (`source_module + source_type + source_ref`), nunca FK direta.
- Evitar acoplamento com Atlas, Engegraph ou outros sistemas externos.
- Atualizar testes e documentação quando necessário.
- Não adicionar comentários óbvios — apenas o "por quê" quando for não-óbvio.

### Depois de implementar

1. `pytest` — todos passando?
2. `ruff check .` — limpo?
3. `mypy .` — se configurado.
4. `alembic current` + `alembic upgrade head` — se houver migration.
5. Validações de segurança — se mudança sensível (ver abaixo).
6. `git diff` — revisar o que mudou.
7. `git status` — sem arquivos inesperados.
8. Atualizar documentação necessária.
9. Produzir relatório final para o usuário.

---

## 5. Comandos de validação

```bash
# Sempre — os mesmos três comandos que o CI executa
pytest
ruff check .
ruff format --check .

# Se tipagem configurada (mypy não está instalado hoje)
mypy .

# Se houver migration — nunca contra cartorio.db
alembic current
alembic heads
alembic check
DATABASE_URL="sqlite:///./_tmp_check.db" alembic upgrade head && rm -f _tmp_check.db

# Para mudanças sensíveis (auth, LGPD, banco, integração, secrets, infra)
bandit -r app
pip-audit
gitleaks detect --source .
```

> **Estado das ferramentas (2026-09-03):** `pytest`, `ruff` e `alembic` estão
> instalados e rodam automaticamente em [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
> `mypy`, `bandit`, `pip-audit` e `gitleaks` **não estão instalados** — a
> exigência acima permanece válida, mas hoje não é executável. Endereçar isso é
> a dívida TD-10, prevista para sprint própria. Enquanto isso, mudanças
> sensíveis exigem revisão humana explícita no lugar da verificação automática.

---

## 6. Política de push

O Claude **nunca executa `git push` automaticamente**.

Antes de qualquer push, apresentar ao usuário:
- Branch atual e hash do commit
- Mensagem do commit
- Arquivos alterados
- Testes e validações executadas
- Confirmação de ausência de secrets/dados reais
- Destino do push

Push somente após confirmação explícita do usuário.

---

## 7. Banco de dados — regras essenciais

- Alembic é a única fonte de DDL — nunca `Base.metadata.create_all` em runtime.
- Revisar diff da migration antes de executar.
- Nunca executar migration em produção sem autorização + backup.
- Usar `Decimal`/`Numeric(14, 2)` para valores monetários — nunca `float`.
- Operações financeiras e regulatórias devem ser transacionais.
- Após `IntegrityError`: fazer rollback antes de qualquer operação — nunca continuar na mesma transação.

---

## 8. ADR — quando é obrigatório

Criar ADR em `docs/decisions/ADR-NNN-titulo.md` quando:
- Um módulo passar a ser dono de uma entidade.
- Uma tabela crítica mudar de estrutura.
- Uma integração externa for definida.
- Uma regra legal ou normativa for interpretada em código.
- Uma decisão alterar contratos de API, schema, exports ou eventos.
- Uma mudança afetar backup, auditoria, LGPD, segurança ou continuidade.
- Uma mudança criar dependência entre módulos antes independentes.

---

## 9. Módulos e estado atual

Baseline: 2026-09-03. Detalhamento e evidências em
[`docs/roadmap.md`](docs/roadmap.md) e no
[rebaseline estratégico](docs/reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md).

| Módulo | Interface | Estado |
|--------|-----------|--------|
| `notas/inventarios` | CLI | **Maduro e em uso real** — minuta-base de inventário extrajudicial; 6 casos reais entre 05 e 08/2026; golden files byte a byte; ADR-009 |
| `audit/scanner` | CLI | Maduro — inventário read-only com SHA-256; validado em ambiente real |
| `audit/diagnosis` | CLI | Maduro — 7 regras DIAG-* + 3 TEMP-*; calibrado após execução real |
| `audit/findings` | REST | Funcional — CRUD sem DELETE físico; sem uso real ainda |
| `compliance` | REST | Funcional — Compliance-1 a 4; seed da Matriz INOVA **ainda não aplicado** |
| `lgpd` | REST | Funcional — Sprint LGPD-1; 25 ações importadas do plano INOVA |
| `retention` | sem router | Parcial — regras e seed prontos; consumido por `audit/diagnosis`; tabela vazia ⇒ TEMP-* inativos |
| `finance` | REST | Finance Core v1.2 — preservado, **backlog futuro; não expandir** |
| Pipeline RI (`scripts/local_tools/`) | CLI | Funcional, **fora de `app/`** — inventário sanitizado de matrículas; base do dossiê PROAD. Promoção a módulo é decisão em aberto (DH-1) |
| `clients` `documents` `exports` `protocols` `reports` `tasks` | — | Placeholders vazios, intencionais |
| Autenticação, trilha transversal | — | **Não iniciados** — exigências do Provimento CNJ 213 |
| Knowledge Base / IA, Document Registry, Atlas | — | Apenas blueprint; bloqueados por decisão humana |

---

## 10. Modo `--dangerously-skip-permissions`

```bash
claude --dangerously-skip-permissions
```

Usar **apenas** em ambiente local/controlado, com escopo explícito e previamente definido.

Todas as proibições permanentes da Seção 2 se mantêm — inclusive sem push automático e sem acesso a dados reais.

---

## 11. Documento completo de governança

Para políticas detalhadas de: ambientes, dados reais, ADR, segurança, migrations, integrações futuras e checklist completo:

**[`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md)**
