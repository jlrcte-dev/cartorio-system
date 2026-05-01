# Decisões técnicas

Registro das decisões estruturais tomadas até a Etapa 1.2. Cada decisão
inclui o **porquê** para que mudanças futuras saibam o contexto e possam
revisar com segurança.

---

## D-01 · Stack: Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2

**Decisão.** Backend em Python 3.12.x (pinado), FastAPI para HTTP,
SQLAlchemy 2 ORM, Pydantic v2 para validação, Alembic para migrations,
Pytest + Ruff para qualidade.

**Por quê.** Stack maduro, tipagem forte, ecosistema grande, fácil
contratação futura, facilita migração para Postgres sem reescrita.

---

## D-02 · Python 3.12 pinado em `>=3.12,<3.13`

**Decisão.** `requires-python = ">=3.12,<3.13"` no `pyproject.toml`,
`.python-version` com `3.12`.

**Por quê.** `StrEnum` (3.11+) e melhorias de tipagem; evitar surpresa com
3.13 ou 3.14 antes de testar; consistência local/CI/produção.

---

## D-03 · SQLite em desenvolvimento; Postgres planejado para produção

**Decisão.** `DATABASE_URL=sqlite:///./cartorio.db` por padrão. Schema
projetado para ser portável a Postgres sem mudança de modelos.

**Por quê.** SQLite zero-config para o gestor rodar localmente. Postgres é
o destino quando o sistema sair do laptop. Implicações:
- Enums sempre `native_enum=False` (armazenados como `VARCHAR`).
- `CheckConstraint` evitada para regras dialeto-específicas (ver D-09).
- `Numeric(14, 2)` e `DateTime(timezone=True)` portáveis.

---

## D-04 · Alembic é a única fonte de DDL

**Decisão.** `Base.metadata.create_all` **não é chamado em runtime** — nem
no lifespan da aplicação, nem em scripts. Setup de banco em
dev/CI/produção: `alembic upgrade head`. Setup de banco em testes:
`Base.metadata.create_all` em fixture sobre engine **in-memory**.

**Por quê.** Versionamento real do schema desde o início. Audit revelou que
o `create_all` no lifespan tocava `cartorio.db` durante `pytest` mesmo com
override de dependency — bug sutil de isolamento. A correção foi remover o
`create_all` do lifespan; o teste `test_lifespan_does_not_touch_production_db`
em `tests/test_isolation.py` impede regressão.

---

## D-05 · Finance-first em vez de Protocols-first

**Decisão.** O MVP começa pelo módulo `finance`, não pelo módulo
operacional (protocolos, clientes, documentos, tarefas).

**Por quê.** A análise documental ampla da serventia revelou que (a) o
gargalo do gestor é financeiro/fiscal, (b) o Engegraph já cobre o
operacional bem, e (c) há 10+ anos de planilhas isoladas que precisam ser
unificadas. O valor imediato vem do painel financeiro. As pastas
`clients/`, `protocols/`, `documents/`, `tasks/`, `reports/`, `exports/`
permanecem como placeholders para etapas futuras.

---

## D-06 · Sistema independente do Atlas

**Decisão.** Nenhum import, dependência, banco, credencial ou código é
compartilhado com o Atlas. A integração planejada é **unidirecional e
assíncrona**: o Sistema do Cartório gera arquivos estruturados em
`exports/atlas/`; o Atlas consome em outro processo.

**Por quê.** Acoplar dois sistemas em produção amplifica risco de cada
mudança. Independência absoluta neste estágio é o caminho mais seguro;
exports estruturados resolvem 100% dos casos de uso conhecidos.

---

## D-07 · Coexistência com Engegraph; sem substituição

**Decisão.** O Engegraph permanece como ERP cartorial; o Sistema do
Cartório **não duplica** atos, livros, folhas ou selos.

**Por quê.** Substituir um ERP em produção é caro e arriscado. A camada
financeira/fiscal/contábil/gerencial é a lacuna real do gestor — é onde o
valor está. Integração com Engegraph (ex.: importar emolumentos diários)
fica como Etapa futura via `EntrySource = ENGEGRAPH_EXPORT`.

---

## D-08 · Auditoria mínima sem autenticação

**Decisão.** Cada `FinancialEntry` guarda `created_by` e `updated_by`
(default `"gestor"`). Não há autenticação real ainda — os campos vêm do
payload.

**Por quê.** Usuário inicial é um único gestor rodando local. Autenticação
proporciona pouco valor agora e adiciona complexidade. Os campos já
existem para que, quando autenticação entrar, a transição seja trivial: o
middleware passa a preencher `created_by`/`updated_by` automaticamente.

---

## D-09 · Validação financeira no Pydantic + service, antes do banco

**Decisão.** Constraints de banco (CHECK) ficam apenas para invariantes
universais (`amount > 0`). Regras de formato (`competence_month` em
`YYYY-MM`) e regras cruzadas (status × tipo, direction × tipo,
`payment_date × status`) ficam em Pydantic e em
`app/modules/finance/rules.py`.

**Por quê.**
1. Erros de regra sobem como **422 com mensagem clara** em vez de erro
   genérico de banco.
2. Permite Postgres futuro sem reescrever CHECKs em sintaxe específica
   (`GLOB` é SQLite-only — foi removido na Etapa 1.2).
3. `rules.py` vira **single source of truth** reusável por schema e
   service.

---

## D-10 · `entry_type` e `competence_month` imutáveis após criação

**Decisão.** `FinancialEntryUpdate` usa `model_config = ConfigDict(extra="forbid")`
e **não declara** `entry_type` nem `competence_month`. Tentativa de PATCH
com esses campos retorna 422.

**Por quê.** São chaves de classificação contábil. Mudar o tipo de uma
receita para despesa, ou mover um lançamento para outro mês, destrói
trilha contábil e abre a porta para "reabrir" mês fechado de forma
silenciosa. A Etapa 2 (Monthly Closing) depende fortemente dessa
imutabilidade. Para corrigir um lançamento errado: cancelar (`status =
CANCELLED`) e recriar.

---

## D-11 · `amount` no PATCH: omitido OK, positivo OK, `null` proibido

**Decisão.** No `FinancialEntryUpdate`, `amount` é `Decimal | None = None`.
Um `model_validator(mode="after")` checa `model_fields_set` e rejeita
`amount: null` explícito com 422. Omitir o campo continua funcionando
(mantém valor atual). Valor positivo atualiza. Zero/negativo cai no
`Field(gt=0)`.

**Por quê.** Sem o validator, `null` passaria no schema e falharia depois
no banco com mensagem de constraint, expondo um erro 500 ou pouco
amigável. A regra elimina a borda silenciosa.

---

## D-12 · `payment_date × status` é regra dura

**Decisão.**
- `PAID` ou `RECEIVED` ⇒ `payment_date` obrigatório.
- `PENDING`, `TO_REVIEW`, `CANCELLED` ⇒ `payment_date` deve ser nulo.

**Por quê.** Pagamentos sem data não fecham mês. Pendências com data
preenchida confundem relatórios. A regra está aplicada em criação **e** em
update. Centralizada em
`rules.validate_payment_date_for_status`.

---

## D-13 · `CANCELLED` e `TO_REVIEW` ficam fora do `result_estimate`

**Decisão.** Ambos contam para `cancelled_count`/`to_review_count` e seus
buckets dedicados, mas **não entram** em `total_revenues`, `total_expenses`,
`total_repasses`, `total_adjustments_*`, nem em `result_estimate`.

**Por quê.** `CANCELLED` é "lixo contábil reconhecido". `TO_REVIEW` é
"lançamento de origem desconhecida ainda não classificado". Incluí-los no
total contamina o número que o gestor olha para decidir.

---

## D-14 · `result_estimate` inclui `PENDING` (é estimativa, não caixa)

**Decisão.** Lançamentos `PENDING` (recebimento previsto, despesa
prevista) entram em `total_revenues`/`total_expenses`/etc. e portanto no
`result_estimate`.

**Por quê.** O nome é literal: estimativa do mês. Para distinguir
formalmente "realizado" de "projetado", a Etapa 2 (Monthly Closing) vai
introduzir `realized_result` e `projected_result` no snapshot.

---

## D-15 · Direction obrigatória; rígida em RECEITA/DESPESA/REPASSE,
livre em AJUSTE

**Decisão.** `EntryDirection` é obrigatório no banco. Para `RECEITA` é
forçado `INFLOW`, para `DESPESA` e `REPASSE` é forçado `OUTFLOW`. Para
`AJUSTE`, o cliente **deve** escolher `INFLOW` ou `OUTFLOW`.

**Por quê.** Receita/despesa/repasse têm sinal natural; ajuste depende do
caso (estorno favorável vs reclassificação contábil). A regra é centralizada
em `rules.resolve_direction` e rejeita conflito explícito (ex.: tentar
criar `RECEITA` com `direction=OUTFLOW`).

---

## D-16 · Logging em stdout; handler 500 com `logger.exception`

**Decisão.** `setup_logging()` configura StreamHandler em stdout com
formatador `%(asctime)s | %(levelname)s | %(name)s | %(message)s`.
`unhandled_exception_handler` chama `logger.exception(...)` com
`request.method` e `request.url.path` antes de devolver
`{"detail": "Erro interno do servidor."}`.

**Por quê.** Sem `logger.exception`, qualquer 500 silencioso ficaria
invisível — primeira coisa que vai aparecer em produção real precisa ter
sinal. `httpx` e `httpcore` foram silenciados (`WARNING`) porque poluíam
saída de testes.

---

## D-17 · Migrations com backfill explícito ao adicionar coluna NOT NULL

**Decisão.** Coluna NOT NULL é adicionada como nullable, recebe `UPDATE`
de backfill com regra explícita, e só então é apertada para NOT NULL via
`batch_alter_table`.

**Por quê.** Autogenerate do Alembic não cria backfill; adicionar coluna
NOT NULL diretamente quebra em qualquer banco com dados. A migration
`b377f12ba37a` segue esse padrão para `direction` (backfill por
`entry_type`).

---

## D-18 · Não usar `from __future__ import annotations` em `schemas.py`

**Decisão.** O módulo `app/modules/finance/schemas.py` **não** importa
`__future__.annotations`. Em vez disso, `import datetime as _dt` e usa
`_dt.date`/`_dt.datetime` para evitar shadowing.

**Por quê.** Pydantic v2 quebra quando o nome do campo (ex.: `date`)
sombreia o tipo importado e o módulo está com PEP 563 ativo. Foi um
problema real durante a Etapa 1 (`TypeError: unsupported operand type(s)
for |: 'NoneType' and 'NoneType'`). A solução por alias evita o conflito
de forma definitiva.

---

## D-19 · Catálogo `FinancialCategory` existe mas não é exposto

**Decisão.** A tabela existe; `FinancialEntry.category` é `String` livre,
**sem FK**. Catálogo controlado fica como Etapa 7.

**Por quê.** Bloquear cadastro por catálogo agora travaria a entrada de
dados pelo gestor. Estabelecer o catálogo certo exige observar dados
reais — vamos consolidar em uma etapa dedicada, com seed baseado nas
categorias visíveis nos dados existentes (energia, internet, Engegraph,
ISS, etc.).

---

## D-20 · Testes em SQLite in-memory + StaticPool

**Decisão.** `tests/conftest.py` cria engine `sqlite:///:memory:` com
`StaticPool` em fixture function-scoped, popula com `Base.metadata.create_all`,
e injeta como override de `get_db`.

**Por quê.** Function-scope garante isolamento entre testes. `StaticPool`
+ in-memory garante que o mesmo "banco" sobreviva às múltiplas conexões
dentro de uma requisição. `Base.metadata.create_all` no fixture é seguro
porque o engine é descartado ao fim do teste.
