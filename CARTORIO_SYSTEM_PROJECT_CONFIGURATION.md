# CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md

Documento de governança técnica, metodológica e operacional do **Cartório System**.
Este arquivo é a referência principal para Claude Code, agentes de IA e fluxos de desenvolvimento.

> **Versão:** 1.0 — Maio/2026
> **Mantido por:** João (gestor/desenvolvedor) + Claude Code
> **Arquivo operacional resumido:** [`CLAUDE.md`](CLAUDE.md)

---

## 1. Identidade do projeto

O **Cartório System** é o backend independente da serventia **Cartório Costa Teixeira**.

- Sistema interno, não é um produto SaaS, não é público.
- Não substitui o **Engegraph** (ERP cartorial existente, núcleo operacional de atos, livros e selos).
- Não compartilha código, banco, credenciais ou dependências com outros sistemas.
- Preenche a camada que o Engegraph não cobre: gestão financeira, auditoria interna, conformidade regulatória, organização documental, rastreabilidade e geração de evidências.
- O **Atlas** poderá ser integrado futuramente, mas **nunca deve ser dependência operacional**. A integração ocorrerá por dados estruturados (JSON/CSV) em `exports/atlas/` ou por chamadas explícitas a APIs — nunca por banco ou código compartilhado.

---

## 2. Hierarquia de fontes e resolução de conflitos

Em caso de conflito entre instruções ou documentos, a ordem de prioridade é:

| Nível | Fonte | Descrição |
|-------|-------|-----------|
| 1 | **Segurança, integridade e proibições permanentes** | Regras que nunca podem ser violadas (Seção 8) |
| 2 | **Escopo explícito da tarefa atual** | O que foi pedido na conversa corrente |
| 3 | **Este documento** (`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`) | Governança técnica e operacional |
| 4 | **ADRs em `docs/decisions/`** | Decisões arquiteturais formalizadas |
| 5 | **Documentação dos módulos em `docs/modules/`** | Especificação e estado de cada módulo |
| 6 | **Roadmaps, planos de sprint e relatórios técnicos** | `docs/roadmap.md`, `docs/audit/module_roadmap.md`, etc. |
| 7 | **Sugestões inferidas pelo Claude** | Nunca sobrepõem as fontes acima |

**Regra crítica:** se houver conflito entre os níveis 1–4, o Claude **deve parar, reportar o conflito e aguardar decisão** antes de implementar qualquer coisa.

---

## 3. Stack tecnológica

| Componente | Tecnologia |
|------------|------------|
| Linguagem | Python 3.12.x (pinado em `>=3.12,<3.13`) |
| API HTTP | FastAPI |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic (única fonte de DDL; nunca `create_all` em runtime) |
| Validação | Pydantic v2 + pydantic-settings |
| Testes | Pytest |
| Lint/format | Ruff |
| Banco (dev) | SQLite (`cartorio.db`) |
| Banco (prod) | PostgreSQL (previsto) |

---

## 4. Arquitetura

### 4.1 Princípios centrais

1. **Monólito modular.** Módulos são autocontidos: `enums`, `models`, `rules`, `schemas`, `service`, `router`. Nenhum módulo importa diretamente de outro (regra de referência fraca via `source_module + source_type + source_ref`).
2. **Clean Architecture pragmática.** Domínio protegido; regras cruzadas centralizadas em `rules.py` por módulo.
3. **Alembic é a única fonte de DDL.** `Base.metadata.create_all` nunca é chamado em runtime — apenas em fixtures de teste in-memory.
4. **Validação primeiro no Pydantic.** Constraints de banco apenas para invariantes universais (`amount > 0`). Regras de negócio ficam em Pydantic e `rules.py`.
5. **Imutabilidade contábil.** Campos-chave de classificação (`entry_type`, `competence_month`) não mudam após criação. Para corrigir: cancelar e recriar.
6. **Read-only first para módulos que analisam dados externos.** O scanner nunca modifica arquivos do servidor analisado.
7. **Uso prático ao final de cada sprint.** Nenhuma sprint é preparatória sem entregável verificável.

### 4.2 Estrutura de diretórios

```text
cartorio-system/
├── alembic/                  # migrations versionadas (única fonte de DDL)
│   └── versions/
├── alembic.ini
├── app/
│   ├── core/                 # config, logging, errors (transversal)
│   ├── db/                   # session, base
│   ├── modules/
│   │   ├── finance/          # Finance Core v1.2 (backlog futuro)
│   │   ├── audit/            # Módulo de Auditoria (foco principal)
│   │   ├── lgpd/             # Módulo LGPD
│   │   ├── retention/        # Módulo de Retenção Documental
│   │   └── compliance/       # Módulo de Conformidade Regulatória
│   ├── interfaces/api/v1/    # router HTTP
│   └── main.py
├── tests/                    # testes automatizados
├── docs/                     # documentação técnica, operacional e regulatória
│   ├── decisions/            # ADRs formalizados
│   ├── modules/              # especificação de cada módulo
│   └── ...
├── exports/
│   ├── audit/                # artefatos do módulo de auditoria
│   └── atlas/                # exports estruturados para integração futura
├── _local_data/              # dados locais — nunca versionar conteúdo real
├── .env.example
├── pyproject.toml
├── CLAUDE.md                 # instrução operacional resumida para Claude Code
└── README.md
```

### 4.3 Módulo dono de cada entidade

| Entidade | Módulo dono |
|----------|-------------|
| `FinancialEntry`, `FinancialCategory` | `finance` |
| `AuditFinding`, `Scanner` | `audit` |
| `LgpdAction`, `LgpdDataElement` | `lgpd` |
| `RetentionRule`, `RetentionSchedule` | `retention` |
| `ComplianceRequirement`, `ComplianceEvidence`, `ComplianceStatus`, `RequirementFindingLink` | `compliance` |

---

## 5. Política de ambientes e dados reais

### 5.1 Desenvolvimento

- Usar exclusivamente dados fictícios ou anonimizados.
- O banco de desenvolvimento é `cartorio.db` (SQLite local) — **nunca versionar**.
- Fixtures de teste devem ser sintéticas (geradas no código, não extraídas de dados reais).
- `pytest` nunca deve tocar `cartorio.db` (garantido por `test_isolation.py`).

### 5.2 Homologação

- Pode usar amostras controladas, preferencialmente anonimizadas.
- Qualquer dado de homologação com origem real exige autorização explícita, backup prévio e registro da origem.

### 5.3 Produção

- **Nunca acessada por scripts experimentais.**
- Nunca rodar migrations em produção sem: autorização explícita do usuário, backup verificado, revisão do diff da migration.
- Dados reais de produção não devem ser enviados para Claude, GitHub, chats, documentação pública ou anexados em issues.
- Dumps reais não devem ser versionados, enviados por IA, incluídos em relatórios ou expostos em qualquer canal digital.

### 5.4 Dados sensíveis — regras absolutas

- Logs não devem expor: CPF, documentos, nomes completos, valores sensíveis, tokens, secrets ou informações cartorárias sigilosas sem necessidade técnica justificada.
- Nenhuma fixture de teste deve conter dados reais de clientes, atos, documentos ou finanças da serventia.
- Importações de dados reais exigem: autorização explícita, backup prévio e registro da origem no commit/ADR.
- O diretório `_local_data/` é local — nunca deve ir ao repositório com conteúdo real.

---

## 6. Política de ADR (Architecture Decision Records)

ADRs vivem em `docs/decisions/` e seguem o formato: `ADR-NNN-titulo-curto.md`.

### 6.1 ADR é obrigatório quando

- Um módulo passa a ser dono oficial de uma entidade antes sem dono.
- Uma tabela crítica muda de estrutura de forma não-trivial.
- Uma regra de retenção documental é adotada.
- Uma integração com Engegraph, Atlas, Google Drive, Microsoft, KIP ou qualquer sistema externo é definida.
- Uma decisão reduz ou aumenta rastreabilidade do sistema.
- Uma operação passa a afetar dados reais.
- Uma regra legal, normativa ou regulatória é interpretada em lógica de sistema.
- Uma decisão altera contratos públicos de API, schemas, eventos ou exports.
- Uma decisão afeta backup, restore, auditoria, LGPD, segurança, continuidade ou evidência regulatória.
- Uma mudança cria dependência entre módulos antes independentes.
- Uma migration altera estrutura de tabela com dados em produção (ou previsão de produção).

### 6.2 ADR não é necessário para

- Implementação de endpoint dentro de módulo existente e seguindo padrão estabelecido.
- Adição de campo opcional em schema Pydantic sem impacto no banco.
- Ajustes de lint, formatação ou nomenclatura.
- Novas fixtures de teste.

### 6.3 Campos mínimos de um ADR

```markdown
# ADR-NNN — Título

## Status
Proposto | Aceito | Descartado | Substituído

## Contexto
## Decisão
## Consequências positivas
## Consequências negativas
## Alternativas consideradas
## Referências
```

---

## 7. Validações de qualidade

### 7.1 Obrigatórias — sempre

```bash
pytest
ruff check .
```

### 7.2 Obrigatórias — quando houver tipagem configurada

```bash
mypy .
```

### 7.3 Obrigatórias — quando houver migration

```bash
alembic current
alembic history
alembic upgrade head
```

Antes de executar: revisar o diff da migration. Nunca executar migration em produção sem autorização explícita e backup verificado.

### 7.4 Recomendadas — para mudanças sensíveis

```bash
bandit -r app      # análise estática de segurança Python
pip-audit          # vulnerabilidades em dependências
gitleaks detect --source .   # secrets acidentais no repositório
```

Usar especialmente quando a mudança envolve: autenticação, autorização, LGPD, banco de dados, migrations, manipulação de arquivos, documentos, integrações externas, variáveis de ambiente, secrets, deploy, infraestrutura, módulos de auditoria ou financeiros.

---

## 8. Proibições permanentes

As seguintes ações são **absolutamente proibidas** em qualquer modo, ambiente ou circunstância, a menos que haja autorização explícita, formal e documentada do gestor:

- Alterar `.env` ou qualquer arquivo de configuração sensível.
- Executar migrations em produção sem autorização, backup verificado e diff revisado.
- Fazer `git push` sem autorização explícita do usuário na conversa corrente.
- Fazer `git push --force` em `main` ou `master`.
- Apagar diretórios ou arquivos fora do escopo explícito da tarefa.
- Executar comandos destrutivos (`rm -rf`, `DROP TABLE`, `DELETE FROM` sem `WHERE`) fora do repositório ou em dados reais.
- Versionar: `cartorio.db`, dumps reais, arquivos `.env`, secrets, tokens ou credenciais.
- Expor dados sensíveis (CPF, documentos, valores, tokens) em logs, outputs ou relatórios.
- Modificar dados reais sem autorização formal.
- Sobrescrever documentação crítica (`CLAUDE.md`, `CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`, ADRs) sem diff explícito e revisão.
- Misturar múltiplas sprints ou escopos no mesmo commit.
- Alterar arquivos fora do repositório `cartorio_system`.
- Rodar scripts contra produção sem autorização formal.
- Acessar, copiar ou transmitir credenciais de qualquer sistema.

---

## 9. Uso de `claude --dangerously-skip-permissions`

Este modo é autorizado **exclusivamente** em ambiente local/controlado (máquina do desenvolvedor) e com escopo claro e previamente definido.

Mesmo com `--dangerously-skip-permissions` ativo, todas as proibições permanentes da Seção 8 se mantêm sem exceção. O modo não concede autorização implícita para nenhuma ação destrutiva, acesso a dados reais, push automático ou alteração de configuração sensível.

---

## 10. Política de Git — commit e push

### 10.1 Commit pode ser preparado quando

- A mudança estiver dentro do escopo explícito da tarefa.
- Testes relevantes (`pytest`) tiverem sido executados e passado.
- Lint (`ruff check .`) estiver limpo.
- `git status` tiver sido revisado — sem arquivos inesperados.
- O commit não contiver: secrets, dumps, `cartorio.db`, dados reais.
- Documentação necessária tiver sido atualizada.
- A mensagem de commit seguir o padrão: `tipo(escopo): descrição` (conventional commits).

### 10.2 Push — somente com autorização explícita

O Claude **nunca executa `git push` automaticamente**, mesmo que o commit esteja preparado.

Antes de qualquer push, o Claude deve apresentar ao usuário:

1. Branch atual
2. Hash do commit
3. Mensagem do commit
4. Lista de arquivos alterados
5. Testes executados e resultado
6. Validações executadas
7. Confirmação de ausência de secrets/dados reais
8. Destino do push (remote + branch)

Somente após confirmação explícita do usuário o push pode ser executado.

### 10.3 Padrão de mensagem de commit

```
tipo(escopo): descrição curta em português

# Tipos: feat, fix, refactor, test, docs, chore, style
# Exemplos:
feat(compliance): adiciona endpoint de RequirementFindingLink
fix(finance): corrige validação de payment_date em PATCH
docs(decisions): adiciona ADR-004 sobre autenticação multiusuário
test(audit): adiciona testes de scan com inventories sintéticos
```

---

## 11. Política de banco de dados e migrations

- **Alembic é a única fonte de DDL.** Nunca usar `Base.metadata.create_all` em runtime.
- Toda migration deve ser revisada antes de executar — verificar o diff gerado pelo `autogenerate`.
- Nunca executar migration em produção sem: autorização explícita + backup verificado + diff revisado.
- Nunca alterar banco manualmente sem registro (ALTER TABLE direto = never).
- **Não usar `float` para valores monetários.** Usar `Decimal`/`Numeric(14, 2)`.
- Regras críticas devem ser protegidas por validação de domínio (`rules.py`) e, quando cabível, constraints de banco.
- Operações financeiras, documentais e regulatórias devem ser **transacionais**.
- Integridade e rastreabilidade têm prioridade sobre conveniência.

### 11.1 Tratamento de `IntegrityError`

Após `IntegrityError` no SQLAlchemy:
- **Não continuar usando a mesma transação** como se nada tivesse ocorrido.
- Executar rollback adequado antes de qualquer operação subsequente.
- Isolar a operação problemática ou usar `savepoint` conforme o caso.
- Expor erro claro ao chamador (HTTP 409 Conflict ou 422 Unprocessable Entity, conforme o caso).

### 11.2 Operações concorrentes

- Preferir padrões seguros: `UNIQUE constraint + retry controlado`.
- Usar `SELECT FOR UPDATE` quando necessário para exclusão mútua.
- Preferir **idempotência** e **transações curtas**.
- Evitar locks longos que bloqueiem outras operações.

### 11.3 Migrations — padrão para coluna NOT NULL

Ao adicionar coluna NOT NULL em tabela existente:
1. Adicionar como nullable.
2. Fazer backfill explícito com regra documentada.
3. Apertar para NOT NULL via `batch_alter_table`.

(Ver D-17 em `docs/decisions/technical_decisions.md` e migração `b377f12ba37a` como referência.)

---

## 12. Política para integrações futuras

Integrações com Atlas, Engegraph, Google Drive, Microsoft, KIP ou outros sistemas devem seguir:

- **Contratos explícitos:** schemas, formatos e versões documentados antes da implementação.
- **Camada anticorrupção:** quando houver diferença de modelo de domínio, proteger o Cartório System com uma camada de tradução.
- **Exports versionados:** quando fizer sentido, incluir versão no nome do arquivo ou no cabeçalho.
- **Sem compartilhamento direto de banco:** cada sistema tem seu próprio banco.
- **Sem dependência de runtime desnecessária:** o Cartório System opera mesmo que o sistema externo esteja indisponível.
- **Segregação de credenciais:** cada integração tem suas próprias credenciais, sem compartilhamento.
- **Logs auditáveis:** toda interação com sistema externo deve ser registrada com timestamp, origem e resultado.
- **Testes de contrato:** quando possível, validar o formato do payload antes de consumir ou produzir.
- **ADR obrigatório:** quando a integração afetar arquitetura, governança ou dependências do sistema.

---

## 13. Módulo de auditoria — regras especiais

O módulo `audit` opera em modo read-only nos dados que analisa:

- O scanner **nunca modifica** arquivos do servidor analisado.
- O diagnóstico recebe como entrada o `file_inventory.json` gerado pelo scanner — nunca um caminho de disco ou servidor diretamente.
- Findings são **imutáveis após criação** — apenas status evolui.
- Não há `DELETE` físico de findings.
- Evidências de auditoria que viram evidências regulatórias são referenciadas por **referência fraca** no módulo `compliance` (ver ADR-001 e ADR-002).

---

## 14. Conformidade regulatória — postura correta

O sistema **não deve declarar conformidade regulatória plena** sem validação jurídica, técnica e documental formal.

O sistema:
- Gera evidências estruturadas.
- Registra achados e ações corretivas.
- Mapeia requisitos normativos (CNJ 213/2026 — Classe 3).
- Calcula status indicativo (não definitivo) de conformidade.
- Produz dossiê técnico para apoiar decisões jurídicas e técnicas.

A responsabilidade por declarar conformidade é da serventia e de seus assessores jurídicos/técnicos, não do sistema.

**Metas mínimas Classe 3 (Provimento CNJ 213/2026):** RPO ≤ 4h | RTO ≤ 8h | Prazo global: 24 meses.

---

## 15. Postura crítica do Claude

O Claude **não deve concordar automaticamente** com decisões técnicas, arquiteturais ou operacionais.

O Claude deve apontar ativamente:
- Riscos de segurança (OWASP Top 10, exposição de dados, autenticação inadequada).
- Riscos regulatórios (LGPD, CNJ 213/2026, outras normas aplicáveis).
- Riscos arquiteturais (acoplamento indevido, violação de separação de módulos, referência direta entre módulos que devem ser independentes).
- Riscos operacionais (dados reais sem backup, migrations sem rollback, scripts destrutivos).
- Inconsistências com ADRs existentes.
- Escopo excessivo (gold plating, over-engineering).
- Ausência de testes para mudanças críticas.

Quando identificar risco relevante, reportar **antes** de implementar.

---

## 16. Checklist — antes e depois de cada tarefa crítica

### 16.1 Antes de implementar

- [ ] Entendi o escopo completo da tarefa?
- [ ] Identifiquei o módulo dono das entidades afetadas?
- [ ] Existe ADR ou documentação relacionada que devo consultar?
- [ ] Há risco regulatório, financeiro, LGPD ou de dados reais?
- [ ] Há migration? Se sim, revisei o impacto em dados existentes?
- [ ] Há impacto em contrato de API, schema, evento ou export?
- [ ] Há risco de acoplamento indevido entre módulos?
- [ ] Preciso registrar uma nova ADR antes de implementar?
- [ ] Preciso atualizar documentação em `docs/modules/` ou `docs/decisions/`?
- [ ] Há risco técnico que devo reportar antes de prosseguir?

### 16.2 Depois de implementar

- [ ] Rodei `pytest` — todos passando?
- [ ] Rodei `ruff check .` — sem erros?
- [ ] Rodei `mypy .` (se configurado)?
- [ ] Rodei `alembic current` + `alembic upgrade head` (se houver migration)?
- [ ] Revisei `git diff` — sem surpresas?
- [ ] Revisei `git status` — sem arquivos inesperados?
- [ ] Atualizei documentação necessária (`docs/modules/`, roadmap, ADR)?
- [ ] Confirmei ausência de secrets, dumps ou dados reais no commit?
- [ ] Preparei relatório final para o usuário?

---

## 17. Referências e documentos relacionados

| Documento | Propósito |
|-----------|-----------|
| [`CLAUDE.md`](CLAUDE.md) | Instrução operacional resumida para Claude Code |
| [`README.md`](README.md) | Visão geral, setup e links principais |
| [`docs/README.md`](docs/README.md) | Índice da documentação por domínio |
| [`docs/architecture.md`](docs/architecture.md) | Arquitetura, stack, camadas e princípios |
| [`docs/decisions/technical_decisions.md`](docs/decisions/technical_decisions.md) | Decisões técnicas D-01 a D-23 |
| [`docs/decisions/`](docs/decisions/) | ADRs formalizados (ADR-001, ADR-002, ADR-003) |
| [`docs/roadmap.md`](docs/roadmap.md) | Prioridade atual, etapas concluídas e backlog |
| [`docs/audit/module_roadmap.md`](docs/audit/module_roadmap.md) | Roadmap do módulo de auditoria (12 fases) |
| [`docs/regulatory/cnj_213/roadmap.md`](docs/regulatory/cnj_213/roadmap.md) | Adequação ao Provimento CNJ 213/2026 |
| [`docs/modules/`](docs/modules/) | Especificação de cada módulo |
| [`docs/operations/local_data_policy.md`](docs/operations/local_data_policy.md) | Política de dados locais |
| [`docs/operations/how_to_run.md`](docs/operations/how_to_run.md) | Instalação, banco, servidor, testes |
| [`docs/quality/testing.md`](docs/quality/testing.md) | Fixtures, isolamento e cobertura por área |

---

## 18. Evolução deste documento

Este documento deve ser atualizado quando:
- Uma decisão estrutural mudar a arquitetura, governança ou política do projeto.
- Uma nova seção de governança for necessária e não coberta aqui.
- Uma instrução aqui entrar em conflito com a realidade do projeto.

Atualizações devem ser feitas de forma cirúrgica — preservando o que está correto, corrigindo o que está desatualizado, adicionando o que está faltando. Nunca reescrever do zero sem necessidade.
