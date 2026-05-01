# Finance Core (v1.2)

## Objetivo

Núcleo financeiro do sistema, focado no apoio direto ao gestor da serventia:
registro de receitas, despesas, repasses e ajustes, com regras de domínio
suficientes para fundamentar fechamento mensal, relatórios obrigatórios e
exports para a contabilidade nas etapas seguintes.

A regra orientadora desta fase é **auditabilidade, clareza e conferência** —
não automação tributária complexa.

## Entidades

### `FinancialEntry` (`financial_entries`)

Lançamento financeiro individual. Campos:

| Campo | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | autoincrement |
| `entry_type` | `EntryType` | imutável após criação |
| `direction` | `EntryDirection` | derivado de `entry_type` em RECEITA/DESPESA/REPASSE; obrigatório em AJUSTE |
| `competence_month` | `String(7)` | formato `YYYY-MM`; **imutável após criação** |
| `date` | `Date` | data do lançamento |
| `description` | `String(500)` | obrigatório |
| `category` | `String(64)` nullable | slug livre; ainda não há FK para `FinancialCategory` |
| `service_area` | `ServiceArea` | default `GERAL` |
| `amount` | `Numeric(14, 2)` | CHECK `amount > 0` |
| `status` | `EntryStatus` | default `PENDING` |
| `payment_date` | `Date` nullable | regra `payment_date × status` aplicada |
| `source` | `EntrySource` | default `MANUAL` |
| `notes` | `String(2000)` nullable | livre |
| `created_by` | `String(64)` | default `gestor` |
| `updated_by` | `String(64)` | espelha `created_by` na criação |
| `created_at` | `DateTime(tz=True)` | server_default `now()` |
| `updated_at` | `DateTime(tz=True)` | onupdate `now()` |

**Índices:** `entry_type`, `competence_month`, `service_area`, `status`,
`category`, `direction` e composto `(competence_month, entry_type)`.

### `FinancialCategory` (`financial_categories`)

Catálogo de categorias (`slug`, `name`, `description`). **Existe como tabela
mas ainda não é exposto via API e não é referenciado por FK em
`FinancialEntry`** — `category` continua sendo string livre. Catálogo
controlado é Etapa 5 do roadmap.

## Enums

### `EntryType`
`RECEITA`, `DESPESA`, `REPASSE`, `AJUSTE`.

### `EntryStatus`
`PENDING`, `PAID`, `RECEIVED`, `CANCELLED`, `TO_REVIEW`.

### `ServiceArea`
`RI`, `RC`, `NOTAS`, `PROTESTO`, `RTD`, `GERAL`.

### `EntrySource`
`MANUAL`, `IMPORT_XLSX`, `ENGEGRAPH_EXPORT`, `BANK_STATEMENT`,
`ACCOUNTING`, `OTHER`. Default: `MANUAL`.

### `EntryDirection`
`INFLOW`, `OUTFLOW`.

## Regras de domínio

Centralizadas em [`app/modules/finance/rules.py`](../app/modules/finance/rules.py)
— **single source of truth**. São aplicadas tanto no schema Pydantic
(criação) quanto no service (atualização parcial).

### Status × Tipo

| `entry_type` | Status permitidos |
|---|---|
| `RECEITA` | `PENDING`, `RECEIVED`, `CANCELLED`, `TO_REVIEW` |
| `DESPESA` | `PENDING`, `PAID`, `CANCELLED`, `TO_REVIEW` |
| `REPASSE` | `PENDING`, `PAID`, `CANCELLED`, `TO_REVIEW` |
| `AJUSTE`  | `PENDING`, `PAID`, `RECEIVED`, `CANCELLED`, `TO_REVIEW` |

Status inválido para o tipo retorna **422**.

### Direction obrigatória por tipo

- `RECEITA` ⇒ `INFLOW` (forçado; tentativa de `OUTFLOW` = 422)
- `DESPESA` ⇒ `OUTFLOW` (forçado)
- `REPASSE` ⇒ `OUTFLOW` (forçado)
- `AJUSTE`  ⇒ obrigatório, pode ser `INFLOW` ou `OUTFLOW` (omitir = 422)

### `payment_date × status`

- `PAID` ou `RECEIVED` ⇒ `payment_date` **obrigatório**
- `PENDING`, `TO_REVIEW`, `CANCELLED` ⇒ `payment_date` **deve ser nulo**

Violar a regra retorna **422**, em criação e em update.

### Campos imutáveis após criação

- `entry_type`
- `competence_month`

`FinancialEntryUpdate` usa `extra="forbid"`. Tentativa de PATCH com esses
campos retorna **422**. Para corrigir: cancelar (`status=CANCELLED`) e
recriar.

### `amount` no PATCH

- Pode ser **omitido** (mantém o valor atual)
- Pode ser **positivo** (atualiza)
- **Não pode ser `null` explícito** (422)
- Não pode ser `0` ou negativo (`Field(gt=0)` retorna 422)

### `amount > 0`

Constraint CHECK no banco + `Field(gt=0)` no Pydantic.

### CANCELLED e TO_REVIEW no `result_estimate`

Nenhum dos dois entra no `result_estimate` nem em `total_revenues`,
`total_expenses`, `total_repasses`, `total_adjustments_*`. Aparecem apenas
em buckets dedicados (`*.cancelled`, `*.to_review`) e nos contadores
`cancelled_count`/`to_review_count`.

## Endpoints

Todos sob `/api/v1/finance`.

### `POST /entries` → 201

Cria lançamento. Payload obrigatório:
- `entry_type`, `competence_month`, `date`, `description`, `amount`.

Opcionais com defaults:
- `direction` (forçado para RECEITA/DESPESA/REPASSE; obrigatório em AJUSTE)
- `service_area` (`GERAL`), `status` (`PENDING`), `source` (`MANUAL`),
  `created_by` (`gestor`)
- `category`, `payment_date`, `notes` (livres)

### `GET /entries`

Lista lançamentos. Filtros opcionais:
- `competence_month` (regex `^\d{4}-(0[1-9]|1[0-2])$`)
- `entry_type`, `service_area`, `status` (alias do query param `status`)
- `limit` (1–1000, default 200), `offset` (≥0, default 0)

Ordem: `date DESC, id DESC`.

### `GET /entries/{entry_id}` → 200 ou 404

### `PATCH /entries/{entry_id}` → 200

Update parcial. Aceita: `description`, `category`, `service_area`, `amount`,
`status`, `payment_date`, `source`, `notes`, `date`, `direction`,
`updated_by`. Rejeita qualquer outro campo (incluindo `entry_type` e
`competence_month`) com 422.

### `GET /monthly-summary?competence_month=YYYY-MM` → 200

Resumo calculado em memória — **não há tabela de fechamento ainda**. A
estrutura retornada está em `MonthlySummary` (ver
[`schemas.py`](../app/modules/finance/schemas.py)).

## Cálculo do `monthly-summary`

Para cada lançamento da competência:

1. Se `status == CANCELLED`: contabiliza em `bucket.cancelled` e
   `cancelled_count`. **Não entra** em totais nem em `result_estimate`.
2. Se `status == TO_REVIEW`: contabiliza em `bucket.to_review` e
   `to_review_count`. **Não entra** em totais nem em `result_estimate`.
3. Caso contrário (`PENDING`, `PAID` ou `RECEIVED`): soma em
   `bucket.valid_total`, em `bucket.pending` ou `bucket.settled` (conforme o
   status), no total agregado correspondente ao tipo
   (`total_revenues`/`total_expenses`/`total_repasses`/`total_adjustments_*`),
   e na célula correspondente de `by_service_area`.

Fórmula final:

```
result_estimate = total_revenues
                + total_adjustments_inflow
                - total_expenses
                - total_repasses
                - total_adjustments_outflow
```

`result_estimate` inclui valores `PENDING` (é uma **estimativa**, não caixa
realizado). A distinção `realized_result × projected_result` ficou para a
Etapa 2 (Monthly Closing).

## Limitações conhecidas

1. **Sem catálogo de categorias controlado.** `category` é string livre.
2. **`payment_date` não tem regra cruzada com `date`.** É possível ter
   `payment_date < date` (pagamento antecipado registrado depois) ou muito
   posterior; é aceito.
3. **`AJUSTE` somado/subtraído mesmo em `PENDING`.** Como receitas e
   despesas, ajustes pendentes entram no `result_estimate`. Se o gestor
   quiser reservar um ajuste só para o resultado realizado, deve criá-lo
   como `PAID`/`RECEIVED` — a Etapa 2 vai resolver formalmente.
4. **Sem soft-delete.** Cancelar = `status=CANCELLED`. Não há `DELETE`
   exposto.
5. **Sem autenticação.** `created_by`/`updated_by` vêm do payload. Auditoria
   real é etapa futura.
6. **`competence_month` é string** (`YYYY-MM`). Filtro por intervalo
   (`competence_month_from`/`to`) ainda não foi implementado.
7. **Listagem não filtra por `direction`, `source` ou `category`.** Será
   adicionado conforme demanda da Etapa 2.
8. **`compute_monthly_summary` carrega todos os lançamentos do mês em
   memória** — adequado para o volume atual da serventia, sem agregação SQL.

## Status atual

- **48 testes passando** cobrindo criação, validações cruzadas, listagem,
  PATCH (incluindo imutabilidade e regra `amount`), monthly-summary
  (incluindo mês vazio) e isolamento de DB.
- **Ruff check + format**: limpo.
- **Migrations**: 3 revisões, round-trip (`downgrade base → upgrade head`)
  validado.
