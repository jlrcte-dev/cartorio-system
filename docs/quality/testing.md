# Testes

## Estado atual

> **Baseline: 2026-09-03.** Números conferidos por coleta real
> (`pytest --collect-only -q`). Este documento descreve **como** os testes são
> organizados; a contagem exata muda a cada sprint e não deve ser tratada como
> contrato — a fonte da verdade é sempre a coleta do momento.

Na data do baseline: **904 testes coletados em 38 arquivos** — 903 passando e
1 skip condicional de plataforma. Zero warnings.

O único skip é `tests/test_file_scanner.py`, que simula permissões via `chmod`
e é pulado no Windows sem privilégios de administrador. Não é um teste
desativado: ele roda no CI (Linux).

### Distribuição por área

| Área | Testes | Arquivos | % |
|---|---:|---:|---:|
| Pipeline RI (`test_ri_*`) | 334 | 6 | 36,9% |
| Compliance (`test_compliance_*`) | 213 | 14 | 23,6% |
| Notas / Inventários (`test_notas_*`) | 136 | 7 | 15,0% |
| Audit — scanner, diagnosis, findings | 114 | 4 | 12,6% |
| Finance | 44 | 1 | 4,9% |
| LGPD | 37 | 1 | 4,1% |
| Retention (+ integração com diagnosis) | 22 | 3 | 2,4% |
| Infraestrutura (health, isolamento) | 4 | 2 | 0,4% |
| **Total** | **904** | **38** | |

Observação estrutural: a maior fatia de testes cobre o **pipeline RI**, que vive
em `scripts/local_tools/` e não em `app/` — ver
[`../architecture.md`](../architecture.md), seção "Ferramentas fora de `app/`".

### Golden files

`tests/golden/notas_inventarios/` contém 6 artefatos (minuta, resumo e JSON de
validação para os dois exemplos canônicos) comparados **byte a byte**. O
`.gitattributes` fixa `eol=lf` nesse diretório — sem isso, um checkout no
Windows converteria para CRLF e quebraria a comparação.

O procedimento de regeneração dos golden está em
[`../modules/notas_inventarios.md`](../modules/notas_inventarios.md), § 7.

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

## O que cada área cobre

Descrição por intenção, não por contagem de asserções — a lista anterior
enumerava as 48 asserções da Etapa 1.2 e ficou obsoleta em poucas sprints.

| Área | O que os testes garantem |
|---|---|
| **Infraestrutura** | `GET /api/v1/health` responde 200 com `status`, `app` e `version`; o lifespan não executa DDL; o handler 500 loga traceback |
| **Finance** | Regras de `direction` por `entry_type`; regra `payment_date × status`; imutabilidade de `entry_type` e `competence_month` no PATCH; rejeição de `amount: null`; `compute_monthly_summary` |
| **Audit — scanner** | Contrato read-only sobre o acervo; inventário com SHA-256; manifesto; travessia de diretórios e tratamento de permissões |
| **Audit — diagnosis** | As 7 regras DIAG-* sobre inventários sintéticos em memória, sem caminhos reais; regras TEMP-* de temporalidade |
| **Audit — findings** | CRUD sem `DELETE` físico; transições de status; arquivamento; histórico |
| **LGPD** | Importação do CSV INOVA; CRUD de ações; histórico append-only; exportação CSV; sumário |
| **Retention** | Regras de temporalidade; seed; integração que injeta as regras no `DocumentAnalyzer` |
| **Compliance** | Seed idempotente com checksum; evidências; vínculos requisito↔achado por referência fraca; status indicativo e seu histórico; **isolamento entre módulos** (`test_compliance_isolation.py`) |
| **Notas / Inventários** | Aritmética `Decimal` do calculator; as 11 regras do validator; contrato Pydantic de entrada; política de destino do `--output-dir`; redação da minuta cláusula a cláusula; exportador ODT determinístico; ausência de PII nas saídas; **golden files byte a byte** |
| **Pipeline RI** | Extração sanitizada de matrículas; classificação de natureza; reconciliação CSV × JSON × SQLite; relatórios de revisão; contratos anti-PII (a extração aborta se detectar dado pessoal na saída) |

## Migrations

Desde 2026-09-03 as migrations são verificadas **automaticamente no CI**
(`.github/workflows/ci.yml`), em banco SQLite temporário criado do zero:

```bash
alembic upgrade head    # aplica as 10 revisões a partir de <base>
alembic current         # confirma o head
alembic heads           # confirma que o head é único
alembic check           # confirma que Base.metadata bate com o schema migrado
```

Para reproduzir localmente **sem tocar o banco de desenvolvimento**, aponte
`DATABASE_URL` para um arquivo descartável:

```bash
DATABASE_URL="sqlite:///./_tmp_check.db" python -m alembic upgrade head
DATABASE_URL="sqlite:///./_tmp_check.db" python -m alembic check
rm -f _tmp_check.db
```

> **Nunca** apague `cartorio.db` para testar migrations. Versões anteriores
> deste documento sugeriam `rm -f cartorio.db` antes do round-trip — instrução
> perigosa e agora desnecessária, já que o ciclo roda em banco temporário.

O round-trip completo (`upgrade head` → `downgrade base` → `upgrade head`)
continua sendo validação manual, executada apenas em banco descartável.

## Lacunas conhecidas

- **Sem cobertura objetiva.** `pytest-cov` não está instalado; adotar cobertura
  exige decisão sobre meta e sobre o custo no CI.
- **Sem `mypy`/`pyright`.** Os tipos em `Mapped[...]` ficam na confiança.
- **Sem verificação de segurança automatizada.** `bandit`, `pip-audit` e
  `gitleaks` são exigidos pelo CLAUDE.md § 5 para mudanças sensíveis, mas não
  estão instalados nem no CI (dívida TD-10, sprint própria).
- **Sem teste de carga / volume.** Adequado ao volume atual da serventia.
- **Sem teste de concorrência.** Não há concorrência hoje — uso monousuário.
- **Testes verdes não significam uso comprovado.** Compliance, retention,
  audit/findings e finance têm suíte extensa e **nenhum dado real** no banco.
  A suíte prova corretude do código, não adequação ao uso operacional.
