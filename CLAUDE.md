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
# Sempre
pytest
ruff check .

# Se tipagem configurada
mypy .

# Se houver migration
alembic current
alembic history
alembic upgrade head

# Para mudanças sensíveis (auth, LGPD, banco, integração, secrets, infra)
bandit -r app
pip-audit
gitleaks detect --source .
```

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

| Módulo | Estado |
|--------|--------|
| `finance` | Finance Core v1.2 — preservado, backlog futuro |
| `audit` | Foco principal — Sprint 1 (Scanner) e Sprint 2 (Findings) concluídas |
| `lgpd` | Sprint LGPD-1 implementada |
| `retention` | Sprint retention-1A/1B implementada |
| `compliance` | Compliance-1 a Compliance-4 implementadas (status indicativo) |

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
