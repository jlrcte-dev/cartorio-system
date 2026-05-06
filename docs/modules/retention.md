# Módulo `retention` — Temporalidade Documental

**Sprint atual:** retention-1B — integração read-only com o DocumentDiagnosis.
**Fonte normativa:** Provimento CNJ nº 50/2015 (anexo: Tabela de Temporalidade de Documentos).

## Posição no ecossistema

```text
audit      → encontra problemas, riscos e achados técnicos/documentais
retention  → aplica temporalidade, guarda, descarte e guarda permanente
lgpd       → organiza obrigações de proteção de dados
compliance → consolida requisitos, evidências, ações e relatórios executivos
```

O módulo `retention` é a **base de linguagem ubíqua** para o domínio
documental. Ele padroniza conceitos como classe documental, código da
tabela, fase corrente, fase intermediária, guarda permanente,
eliminação, digitalização, microfilmagem, documento candidato à revisão,
avaliação humana obrigatória, vedação de descarte automático, fundamento
normativo, evidência de descarte e comunicação semestral ao juízo
competente.

A partir da Sprint retention-1B, o módulo é consumido pelo pipeline
principal de auditoria documental para emitir achados conservadores de
temporalidade. O módulo `lgpd` e o futuro módulo `compliance` consumirão
essa mesma base nos próximos passos.

## Princípio fundamental

**Temporalidade documental neste sistema NÃO autoriza descarte automático.**

O módulo apenas:

- representa regras normativas (`RetentionRule`);
- avalia documentos contra essas regras (em memória, sem persistir);
- emite findings TEMP-* indicativos para revisão humana.

A decisão de eliminar documentos é sempre humana e exige, no mínimo:

1. Desfiguração irreversível (Provimento 50/2015, art. 2º).
2. Comunicação semestral ao juízo competente (art. 3º).
3. Validação com responsável jurídico/administrativo da serventia.

Nenhuma rotina automática lê conteúdo de arquivo, move, renomeia ou
exclui qualquer documento. Os testes plugam um *fixture* que bloqueia
chamadas a `os.remove`, `os.unlink`, `os.rename`, `os.replace`,
`shutil.move`, `shutil.rmtree`, `Path.unlink`, `Path.rename` e
`Path.replace` — qualquer uso dessas APIs no caminho do código retention
faz a suíte falhar.

## Linguagem obrigatória nas saídas

Toda mensagem emitida pelo módulo `retention` ou pelas regras `TEMP-*` usa:

- "candidato à revisão de temporalidade";
- "exige avaliação humana";
- "não executar descarte automático";
- "validar com responsável jurídico/administrativo".

Adicionalmente, recomenda-se manter linguagem indicativa nas
recomendações: "possivelmente", "candidato à revisão", "exige validação
humana", "não autoriza descarte automático", "validar com responsável
jurídico/documental".

## Escopo entregue por sprint

### Sprint retention-1A (anterior)

- domínio interno (enums, modelo, schemas, repository, service, heurísticas);
- seed inicial enxuto, idempotente, somente com linhas de legibilidade
  confirmada no PDF compilado (24 regras);
- regras `TEMP-001`, `TEMP-002` e `TEMP-003` como funções puras em
  `app/modules/audit/diagnosis/temp_rules.py`;
- testes unitários completos.

### Sprint retention-1B (atual)

- integração das regras `TEMP-001/002/003` no pipeline principal de
  `DocumentDiagnosis` por **injeção opcional** de uma lista de
  `RetentionRule` no construtor do `DocumentAnalyzer`;
- *flag* de CLI `--with-retention-rules` que carrega as regras do banco
  em modo somente leitura (a sessão é aberta, lida e fechada — não há
  escrita) e injeta a lista no analyzer;
- testes de integração TEMP-* ↔ pipeline em
  `tests/test_diagnosis_retention_integration.py`;
- garantia estrutural de que o módulo analyzer continua sem qualquer
  símbolo `Session`, `AsyncSession`, `get_db` ou `SessionLocal` em seu
  *namespace*;
- nenhuma rota pública nova, nenhuma tabela nova, nenhum workflow de
  descarte introduzido.

### Fora do escopo desta sprint (backlog)

- router/API pública para `retention`;
- persistência de `RetentionEvaluation` (tabela `retention_evaluations`);
- regras `TEMP-004`, `TEMP-005`, `TEMP-008`;
- workflow formal de descarte;
- relatório semestral ao juízo competente;
- integração com módulo LGPD;
- criação do módulo `compliance`.

## Como o pipeline principal usa retention

Diagrama lógico:

```text
file_inventory.json  ─┐
                      ├─►  DocumentAnalyzer  ─►  DiagnosisResult
list[RetentionRule] ──┘     (rules.py + temp_rules.py)
```

Detalhamento:

1. O scanner (módulo `audit/scanner`) gera `file_inventory.json` com
   metadados de arquivos — sem conteúdo.
2. O `DocumentAnalyzer` carrega o inventário e, **se** o chamador
   fornecer uma lista de `RetentionRule` via parâmetro
   `retention_rules`, chama as três funções TEMP-* em `temp_rules.py`.
3. Quando o parâmetro é `None`, nenhum finding TEMP-* é emitido — o
   pipeline continua se comportando como antes da Sprint retention-1B.
4. As regras retention apenas **inspecionam metadados** (nome, caminho,
   timestamps, *flags* opcionais como `legal_hold`). Nada é gravado
   no disco e nenhuma sessão de banco é aberta dentro do analyzer.
5. A CLI carrega as regras do banco em modo *read-only* quando o
   operador passa `--with-retention-rules`.

### Findings TEMP-*

| Código     | Disparo                                                                                | Severidade | Prioridade  |
|------------|----------------------------------------------------------------------------------------|------------|-------------|
| `TEMP-001` | Arquivo em diretório aparentemente documental, sem regra retention casada              | LOW        | BACKLOG     |
| `TEMP-002` | Arquivo casado com regra de fase corrente DURATION e prazo aparentemente vencido       | MEDIUM     | NINETY_DAYS |
| `TEMP-003` | Arquivo casado com regra de guarda permanente, mas em diretório suspeito (ex: `_old/`) | HIGH       | THIRTY_DAYS |

Como `TEMP-001` tem prioridade `BACKLOG`, ele é filtrado por padrão
quando a CLI/analyzer roda sem `--include-low-priority`. Os findings
`TEMP-002` e `TEMP-003` são incluídos por padrão.

Cada finding registra, sempre que possível: o código TEMP, a regra
`retention` casada, o status de temporalidade implícito, o destino
previsto, o fundamento normativo (via `RetentionRule.source_*`) e uma
observação conservadora explícita exigindo avaliação humana.

## Limitações normativas conhecidas

Estas limitações **devem** ser preservadas até validação jurídica formal:

- A origem da compilação do PDF base está marcada como `COMPILADO_LOCAL`.
  A redação consolidada exige validação jurídica antes de uso definitivo.
- O *seed* inicial contém apenas 24 linhas de legibilidade confirmada;
  classes documentais não cobertas geram `TEMP-001` (sem classificação)
  em vez de inferência arriscada.
- A heurística de classificação (`match_rule`) é puramente lexical,
  baseada em nome e caminho — sem leitura de conteúdo, sem OCR.
- Falsos positivos e falsos negativos são esperados; toda saída exige
  revisão humana.
- O art. 2º do Provimento 50/2015 (desfiguração irreversível antes de
  descarte) ainda **não** tem suporte técnico no sistema.
- O art. 3º do Provimento 50/2015 (comunicação semestral ao juízo)
  ainda **não** tem suporte técnico no sistema.
- O módulo **não** executa, **não** recomenda e **não** automatiza
  descarte. Toda decisão é humana.

## Procedência (`source_*`)

Cada regra carrega:

- `source_norm = "PROVIMENTO_CNJ_50_2015"`
- `source_version = "COMPILADO_LOCAL"`
- `source_file = "_local_data/.../Provimento 50-2015-compilado.pdf"`
- `source_code` — mesmo valor de `codigo`
- `source_notes` — alerta de que a compilação local deve ser validada
  antes de uso jurídico definitivo.

A escolha por `COMPILADO_LOCAL` (em vez de identificador formal de
provimento de compilação) é deliberada: o cabeçalho do PDF lido não
declara explicitamente qual provimento o consolidou.

## Como rodar o seed

```bash
python -m app.modules.retention.seed
```

O seed é idempotente — pode ser executado múltiplas vezes sem duplicar
regras. Não roda automaticamente em `alembic upgrade`.

## Como rodar o diagnóstico com retention habilitado

```bash
python -m app.modules.audit.diagnosis.cli \
    --inventory  "C:\Audit_Reports\<run>\scan\file_inventory.json" \
    --output-dir "C:\Audit_Reports\<run>\diagnosis" \
    --run-name   "diagnosis-<data>" \
    --with-retention-rules
```

Sem `--with-retention-rules` o pipeline funciona exatamente como antes
da Sprint retention-1B; nenhum finding TEMP-* é emitido.

## Próximos passos recomendados

- **retention-1C**: persistência de `RetentionEvaluation` (somente
  leitura para revisão; sem ação automática), evidências de revisão
  humana e auditoria de classe documental por amostragem.
- **LGPD/Compliance-1**: consumir as classes documentais e os
  findings `TEMP-*` como insumo de mapeamento ROPA/bases legais e
  consolidar requisitos no novo módulo `compliance` (status,
  evidências, plano de ação, relatórios executivos).
