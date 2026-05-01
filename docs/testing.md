# Testes

## Estado atual

**48 testes passando** em 3 arquivos:

| Arquivo                              | Quantidade | Foco                                |
|--------------------------------------|------------|-------------------------------------|
| `tests/test_health.py`               | 2          | Healthcheck                         |
| `tests/test_finance_entries.py`      | 44         | Finance Core (CRUD, regras, summary)|
| `tests/test_isolation.py`            | 2          | Isolamento de DB e logging 500      |

## Como rodar

```bash
pytest tests/ -v
```

Filtrar por arquivo ou padrão:

```bash
pytest tests/test_finance_entries.py -v
pytest -k "monthly_summary" -v
pytest -k "payment_date" -v
```

## Fixtures

Todas em `tests/conftest.py`, com **escopo de função** (isolamento total
entre testes).

### `test_engine`
Cria um engine SQLite **in-memory** com `StaticPool` (única conexão
compartilhada — necessário para in-memory funcionar com SQLAlchemy ORM).
Popula o schema via `Base.metadata.create_all`. Descarta ao final.

```python
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
```

### `db_session`
Sessão SQLAlchemy bound ao `test_engine`, fornecida diretamente para testes
que querem manipular o ORM sem passar pela API.

### `client`
`TestClient` do FastAPI com `app.dependency_overrides[get_db]` apontando
para uma sessão sobre o `test_engine`. Toda requisição feita por esse
client usa o banco in-memory.

```python
@pytest.fixture(scope="function")
def client(test_engine):
    TestingSessionLocal = sessionmaker(bind=test_engine, ...)
    def override_get_db():
        session = TestingSessionLocal()
        try: yield session
        finally: session.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
```

## Isolamento contra `cartorio.db`

`tests/test_isolation.py` contém o teste
`test_lifespan_does_not_touch_production_db`, que:

1. Captura `mtime_ns` de `cartorio.db` (se existir) **antes** de subir o
   `TestClient`.
2. Sobe `TestClient(app)` (dispara o lifespan), faz uma chamada de
   healthcheck.
3. Verifica que o `mtime_ns` não mudou (ou que o arquivo não foi criado, se
   não existia).

Esse teste impede regressão da decisão D-04 (Alembic é a única fonte de
DDL). Se algum dia alguém adicionar `Base.metadata.create_all` de volta no
lifespan, este teste falha.

Validação manual (opcional, mas recomendada antes de commit):

```bash
rm -f cartorio.db
pytest tests/ -v
test ! -f cartorio.db && echo "OK: testes não tocaram cartorio.db"
```

## Cobertura por área (resumo das 48 asserções)

### Healthcheck (2)
- `GET /api/v1/health` retorna 200.
- Body contém `status="ok"`, `app`, `version`.

### Finance Core — Criação básica (12)
- Receita default (source `MANUAL`, direction `INFLOW`, audit `gestor`).
- Despesa força `OUTFLOW`. Repasse força `OUTFLOW`. Receita força `INFLOW`.
- Receita com `direction=OUTFLOW` → 422. Direction inválida → 422.
- Ajuste com `INFLOW` e com `OUTFLOW`. Ajuste sem direction → 422.
- Source explícita aceita; source inválida → 422.
- `created_by` explícito espelha em `updated_by`.

### Finance Core — Validação de tipo/status/amount/competência (7)
- Entry type inválido → 422.
- Amount negativo → 422. Amount zero → 422.
- Competência mal formatada → 422.
- Status `PAID` em RECEITA → 422. Status `RECEIVED` em DESPESA → 422.
- Status `TO_REVIEW` permitido em DESPESA.

### Finance Core — Regra `payment_date × status` (5)
- `PAID` sem `payment_date` → 422.
- `RECEIVED` sem `payment_date` → 422.
- `PENDING` com `payment_date` → 422.
- `TO_REVIEW` com `payment_date` → 422.
- `CANCELLED` com `payment_date` → 422.

### Finance Core — Listagem e GET (3)
- Filtro por competência. Filtro composto por tipo + área. GET inexistente
  → 404.

### Finance Core — Update / Imutabilidade (10)
- PATCH `PENDING → PAID` com `payment_date` válido.
- PATCH com status inconsistente → 422.
- PATCH `→ PAID` sem `payment_date` → 422. PATCH `→ RECEIVED` sem
  `payment_date` → 422.
- PATCH com `entry_type` → 422 (`extra="forbid"`). PATCH com
  `competence_month` → 422.
- PATCH com `amount: null` → 422. PATCH sem `amount` mantém valor.
- PATCH com `amount` positivo atualiza. PATCH com `amount=0`/negativo →
  422.
- PATCH atualiza `updated_by`.

### Finance Core — Monthly summary (5)
- Cálculo completo com 8 lançamentos cobrindo receita, despesa, repasse,
  ajuste in/out, cancelado, to_review, e uma competência diferente que fica
  fora.
- Cancelados excluídos de `result_estimate`.
- TO_REVIEW excluídos de `result_estimate`.
- Mês vazio retorna estrutura zerada.
- Competência mal formatada na query → 422.

### Isolamento (2)
- Lifespan não toca `cartorio.db`.
- Handler 500 emite `logger.exception` com traceback ao receber exceção
  não tratada.

## Round-trip Alembic

Não é teste pytest (seria caro de manter), mas faz parte do bloco de
validação manual:

```bash
rm -f cartorio.db
alembic upgrade head        # aplica todas as 3 revisões
alembic downgrade base      # reverte tudo
alembic upgrade head        # reaplica tudo
```

Saída esperada (cada `INFO` corresponde a uma revisão):

```
Running upgrade  -> 8857af05ac59, initial finance core
Running upgrade 8857af05ac59 -> b377f12ba37a, finance core hardening...
Running upgrade b377f12ba37a -> 455f4efec848, drop competence_month glob check
Running downgrade 455f4efec848 -> b377f12ba37a, ...
Running downgrade b377f12ba37a -> 8857af05ac59, ...
Running downgrade 8857af05ac59 -> , initial finance core
Running upgrade  -> 8857af05ac59, ...
Running upgrade 8857af05ac59 -> b377f12ba37a, ...
Running upgrade b377f12ba37a -> 455f4efec848, ...
```

## Lacunas conhecidas

- **Sem `pytest-cov`** ainda. Cobertura objetiva fica para etapa futura.
- **Sem `mypy`/`pyright`**. Tipos em `Mapped[...]` ficam só na confiança.
- **Sem teste de carga / volume** — não há como prever performance da
  função `compute_monthly_summary` em 10 mil lançamentos. Adequado para
  hoje (volume da serventia).
- **Sem teste programático de migração** (apenas validação manual).
- **Sem teste de comportamento concorrente** — não há concorrência hoje
  (gestor solo).
