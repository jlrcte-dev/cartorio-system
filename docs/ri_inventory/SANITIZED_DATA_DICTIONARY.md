# Dicionário de Dados — Base Sanitizada de Matrículas RI v3

**Módulo:** Registro de Imóveis (pré-implementação)

Este documento descreve duas bases sanitizadas:

- **Base PDF** — extraída dos relatórios do Engegraph (rurais apenas)
- **Base JSON** — extraída do Indicador Real completo (urbanos + rurais)

**Classificação:** Uso interno — base sanitizada sem PII

---

---

## Parte 1 — Base PDF (Engegraph, rurais)

**Arquivos de referência:**

- `_local_data/ri_inventory/sanitized/ri_rural_inventory_sanitized.csv`
- `_local_data/ri_inventory/db/ri_inventory.sqlite` → tabela `ri_matriculas_inventory`

**Script gerador:** `scripts/local_tools/extract_ri_rural_inventory.py`

---

## Campos PERMITIDOS na base sanitizada PDF (23 campos)

| Campo | Tipo | Descrição |
|---|---|---|
| `record_id` | inteiro | Identificador sequencial interno gerado pelo script |
| `tipo_registro` | string | Tipo do registro: M (Matrícula) ou T (Transcrição) |
| `matricula_numero` | inteiro | Número da matrícula ou transcrição (sem identificação pessoal) |
| `nome_imovel_sanitizado` | string ou null | Nome técnico do imóvel/fazenda extraído da linha principal (vazio se ambíguo) |
| `municipio` | string | Município do imóvel normalizado |
| `area_texto_original` | string ou null | Texto de área conforme extraído do PDF |
| `area_valor_normalizado` | float ou null | Valor numérico da área normalizado |
| `area_unidade` | string ou null | Unidade da área normalizada (ha, m2, alqueire, etc.) |
| `is_rural` | booleano | Sempre True nesta base |
| `tem_georreferenciamento` | booleano | Presença confirmada de georreferenciamento |
| `georreferenciamento_valor` | string ou null | Código técnico do georreferenciamento (INCRA/SIGEF) |
| `tem_incra` | booleano | Presença de código INCRA/SIGEF válido e não zerado |
| `incra_codigo` | string ou null | Código INCRA/SIGEF preservado no formato original |
| `tem_nirf` | booleano | Presença de código NIRF válido |
| `nirf_codigo` | string ou null | Código NIRF extraído |
| `tem_reserva` | booleano ou null | Reserva legal: True=Sim, False=Não, null=não informado |
| `reserva_valor` | string ou null | Valor literal: "Sim", "Não" ou null |
| `fonte_relatorio` | string | Nome do arquivo PDF de origem (sem caminho) |
| `pagina_origem` | inteiro | Página do PDF onde o bloco foi encontrado |
| `ordem_no_relatorio` | inteiro | Posição sequencial dentro do relatório |
| `hash_bloco_origem` | string | Hash SHA-256 prefixado "H-" (6 chars hex) — rastreabilidade |
| `status_extracao` | string | "ok", "needs_review" (nome ambíguo), "area_ambigua" |
| `observacoes_tecnicas_sem_pii` | string | Notas técnicas sem identificação pessoal |

### Valores válidos para `status_extracao`

| Valor | Significado |
|---|---|
| `ok` | Extração normal, sem alertas |
| `needs_review` | Nome na linha principal suspeito de ser pessoa — `nome_imovel_sanitizado` deixado vazio |
| `area_ambigua` | Área com formato ambíguo (ex: múltiplas vírgulas) — `area_valor_normalizado` pode ser null |

### Valores válidos para `observacoes_tecnicas_sem_pii`

Textos técnicos permitidos:

- `"area_ausente"` — campo área vazio no PDF
- `"area_extraida_da_caracteristica"` — área obtida da linha Caract., não da linha principal
- `"area_ambigua"` — formato de área não reconhecido inequivocamente
- `"nome_linha_principal_suspeito"` — texto da coluna Nome parecia nome de pessoa
- `"pii_descartada:3linhas"` — número de linhas PII descartadas no bloco

Textos **proibidos**: qualquer nome, CPF, CNPJ, RG, endereço ou identificação pessoal.

---

## Campos PROIBIDOS na base sanitizada

Os campos abaixo **nunca devem aparecer** em qualquer arquivo derivado ou exportado.

| Campo proibido | Motivo |
|---|---|
| Nome de proprietário | PII — LGPD art. 5º, I |
| Nome de cônjuge | PII — LGPD art. 5º, I |
| CPF | PII — dado sensível de identificação |
| CNPJ | Dado de pessoa jurídica vinculado a operação registral |
| RG ou documento de identidade | PII — documento pessoal |
| Nome de transmitente | PII — parte de negócio jurídico |
| Nome de adquirente | PII — parte de negócio jurídico |
| Endereço pessoal | PII — dado de localização pessoal |
| Texto livre com identificação pessoal | PII — qualquer forma de individualização de pessoa |

---

## Exemplos de registros VÁLIDOS (dados fictícios)

```json
[
  {
    "record_id": 1,
    "tipo_registro": "M",
    "matricula_numero": 1,
    "nome_imovel_sanitizado": "",
    "municipio": "Terezópolis de Goiás",
    "area_texto_original": "",
    "area_valor_normalizado": null,
    "area_unidade": null,
    "is_rural": true,
    "tem_georreferenciamento": false,
    "georreferenciamento_valor": null,
    "tem_incra": false,
    "incra_codigo": null,
    "tem_nirf": false,
    "nirf_codigo": null,
    "tem_reserva": false,
    "reserva_valor": "Não",
    "fonte_relatorio": "Relatorio_matriculas_rurais.pdf",
    "pagina_origem": 1,
    "ordem_no_relatorio": 1,
    "hash_bloco_origem": "H-a1b2c3",
    "status_extracao": "ok",
    "observacoes_tecnicas_sem_pii": "area_ausente"
  },
  {
    "record_id": 2,
    "tipo_registro": "M",
    "matricula_numero": 381,
    "nome_imovel_sanitizado": "Fazenda Alvorada",
    "municipio": "Terezópolis de Goiás",
    "area_texto_original": "174,2522 ha",
    "area_valor_normalizado": 174.2522,
    "area_unidade": "ha",
    "is_rural": true,
    "tem_georreferenciamento": true,
    "georreferenciamento_valor": "93018000018482",
    "tem_incra": true,
    "incra_codigo": "93018000018482",
    "tem_nirf": false,
    "nirf_codigo": null,
    "tem_reserva": false,
    "reserva_valor": "Não",
    "fonte_relatorio": "Relatorio_matriculas_rurais.pdf",
    "pagina_origem": 5,
    "ordem_no_relatorio": 381,
    "hash_bloco_origem": "H-d4e5f6",
    "status_extracao": "ok",
    "observacoes_tecnicas_sem_pii": ""
  }
]
```

---

## Exemplo de registro INVÁLIDO (não deve aparecer)

```json
{
  "matricula_numero": 12345,
  "proprietario": "NOME FICTICIO SILVA",   <- PROIBIDO
  "cpf": "000.000.000-00",                <- PROIBIDO
  "municipio": "Terezópolis de Goiás"
}
```

---

## Banco SQLite — Tabelas

### `ri_matriculas_inventory`

Tabela principal com todos os registros sanitizados.

- Constraint: `UNIQUE(fonte_relatorio, matricula_numero, hash_bloco_origem)`
- Índices: `matricula_numero`, `tipo_registro`, `tem_georreferenciamento`, `tem_incra`, `tem_nirf`

### `ri_inventory_runs`

Histórico de execuções do extrator. Cada PDF processado gera uma linha.

| Campo | Descrição |
|---|---|
| `run_id` | UUID curto único por execução |
| `fonte_relatorio` | Nome do PDF processado |
| `total_reportado` | Total indicado no PDF (quando detectado) |
| `total_blocos_detectados` | Blocos com padrão M/T + número encontrados |
| `total_registros_sanitizados` | Registros efetivamente salvos |
| `total_duplicidades` | Matrículas com ocorrência múltipla nesta execução |
| `status` | "completed" ou "error" |

### `ri_inventory_duplicates`

Duplicidades detectadas por execução.

| Campo | Descrição |
|---|---|
| `run_id` | Referência à execução |
| `matricula_numero` | Número da matrícula duplicada |
| `ocorrencias` | Quantas vezes aparece |
| `fontes` | PDFs onde foi encontrada (separados por ;) |

---

## Regras de qualidade implementadas no script

1. **Total reportado:** buscado por padrão `Total: N` nas primeiras 3 páginas do PDF.
2. **Alerta de divergência:** se total_extraído ≠ total_reportado, alerta técnico no relatório.
3. **Alerta crítico:** se total_extraído > 3.523 (total geral da serventia), alerta obrigatório.
4. **Duplicidades:** detectadas por `matricula_numero` dentro do mesmo conjunto de registros.
5. **Área ambígua:** "174,25,22 ha" (múltiplas vírgulas) → `area_valor_normalizado = null`, `status = area_ambigua`.
6. **Incra zerado:** código `0000000000` ou equivalente → `tem_incra = False`.
7. **Rótulo sem valor:** `Incra` sem código / `NIRF` sem código / `Georef.` sem `Sim` → indicador = False.
8. **Reserva:** "Reserva Não" → `tem_reserva=False, reserva_valor="Não"` (não é ausência de campo).
9. **PII:** linhas de proprietário/CPF/CI/SSP descartadas silenciosamente. Nunca impressas.
10. **Validação final:** `_validate_sanitized()` varre todos os campos da saída antes de salvar.

---

## Relacionamento com o Plano de Ação IERI-e/SIG-RI

| Indicador do Plano | Campo correspondente |
|---|---|
| IND-02 — Matrículas analisadas no diagnóstico | `matricula_numero` (contagem distinta) |
| IND-05 — Imóveis georreferenciados identificados | `tem_georreferenciamento = true` |
| IND-06 — Imóveis georreferenciados inseridos no SIG-RI | Controle externo — não nesta base |
| INCRA/SIGEF — Grupo A (prioridade SIG-RI) | `tem_incra = true` |

---

---

## Parte 2 — Base JSON (Indicador Real, urbanos + rurais)

**Sprint:** RI-REAL-JSON-1

**Arquivos de referência:**

- `_local_data/ri_inventory/sanitized/ri_real_json_inventory_sanitized.csv`
- `_local_data/ri_inventory/sanitized/ri_real_json_inventory_sanitized.json`
- `_local_data/ri_inventory/db/ri_inventory.sqlite` → tabela `ri_real_json_inventory`

**Script gerador:** `scripts/local_tools/analyze_ri_real_json.py`

**Fonte:** `_local_data/ri_inventory/raw/Indicador_Real` (JSON do ONR/Engegraph)

---

### Campos PERMITIDOS na base JSON (42 campos)

| Campo | Tipo | Descrição |
|---|---|---|
| `record_id` | UUID | Identificador único do registro gerado na extração |
| `cns` | string | Código da Serventia (CNS) extraído do JSON |
| `numero_registro` | string | Identificador técnico no formato CNS.LIVRO.MATRICULA-DV |
| `livro` | string | Número do livro (tipicamente "2") |
| `matricula_numero` | inteiro | Número da matrícula sem zeros à esquerda |
| `digito_verificador_onr` | string | Dígito verificador ONR do NUMERO_REGISTRO |
| `registro_tipo` | inteiro | Tipo de registro conforme JSON (geralmente 1) |
| `tipo_de_imovel` | inteiro | Tipo de imóvel conforme JSON (geralmente 1) |
| `localizacao_codigo` | inteiro | Código bruto de localização: 0=urbano, 1=rural |
| `natureza_imovel` | string | Classificação: "urbano", "rural" ou "indeterminado" |
| `natureza_imovel_fonte` | string | Critério usado: "localizacao_json" |
| `natureza_imovel_confidence` | string | "confirmado" ou "invalido" |
| `uf_codigo` | string | Código de UF (técnico, não PII) |
| `cidade_codigo` | string | Código de cidade (técnico, não PII) |
| `bairro_sanitizado` | string | Bairro sanitizado (vazio se suspeito de PII) |
| `cep_sanitizado` | string | CEP no formato 99999-999 (vazio se inválido) |
| `tem_quadra` | booleano | Quadra preenchida no JSON |
| `tem_lote` | booleano | Lote preenchido no JSON |
| `tem_loteamento` | booleano | Loteamento preenchido no JSON |
| `tem_condominio` | booleano | Condomínio preenchido no JSON |
| `tem_car` | booleano | CAR preenchido em RURAL |
| `car_codigo` | string | Código CAR preservado |
| `tem_nirf` | booleano | NIRF válido (não vazio, não só zeros) |
| `nirf_codigo` | string | Código NIRF extraído |
| `nirf_status` | string | "ausente", "placeholder_zeros", "valido" ou "ambiguo" |
| `tem_ccir` | booleano | CCIR preenchido em RURAL |
| `ccir_codigo` | string | Código CCIR preservado |
| `tem_numero_incra` | booleano | NUMERO_INCRA preenchido em RURAL |
| `numero_incra_codigo` | string | Código INCRA preservado |
| `tem_sigef` | booleano | SIGEF preenchido em RURAL |
| `sigef_codigo` | string | Código SIGEF preservado |
| `tem_denominacao_rural` | booleano | DENOMINACAORURAL preenchida em RURAL |
| `denominacao_rural_sanitizada` | string | Nome do imóvel rural sanitizado (vazio se suspeito de PII) |
| `tem_acidente_geografico` | booleano | ACIDENTEGEOGRAFICO preenchido em RURAL |
| `acidente_geografico_sanitizado` | string | Valor sanitizado (vazio se suspeito de PII) |
| `possui_georreferenciamento` | booleano | True se NUMERO_INCRA ou SIGEF preenchido |
| `georreferenciamento_criterio` | string | Critérios atendidos: "numero_incra", "sigef" ou ambos separados por pipe |
| `status_extracao` | string | "ok" ou alertas múltiplos separados por pipe |
| `status_revisao_ri` | string | "" ou "needs_manual_review" |
| `observacoes_tecnicas_sem_pii` | string | Alertas técnicos sem dados pessoais |
| `fonte_arquivo` | string | Nome do arquivo JSON de origem |
| `hash_registro_sanitizado` | string | Hash SHA-256 prefixado "H-" (10 chars) — rastreabilidade |

### Critério de georreferenciamento (JSON)

O campo `possui_georreferenciamento` é derivado exclusivamente dos campos estruturados do objeto `RURAL`:

- `RURAL.NUMERO_INCRA` preenchido → `tem_numero_incra=true` → contribui para `possui_georreferenciamento`
- `RURAL.SIGEF` preenchido → `tem_sigef=true` → contribui para `possui_georreferenciamento`

Este critério é **diferente** do usado nos PDFs (onde "Georef. Sim" explícito era o critério principal). Os dois critérios coexistem e não devem ser misturados.

### Valores válidos para `nirf_status`

| Valor | Significado |
|---|---|
| `ausente` | Campo NIRF vazio ou null |
| `placeholder_zeros` | Campo NIRF preenchido apenas com zeros ("00000000") |
| `valido` | NIRF com ao menos um dígito diferente de zero |
| `ambiguo` | Valor presente mas não reconhecível como válido ou placeholder |

### Campos PROIBIDOS na base JSON

Os mesmos campos proibidos da Base PDF aplicam-se aqui, com adição explícita:

| Campo proibido | Motivo |
|---|---|
| `CONTRIBUINTE` | PII — identificação do proprietário/contribuinte |
| Nome de proprietário | PII — LGPD art. 5º, I |
| CPF | PII — dado sensível de identificação |
| CNPJ | Dado de pessoa jurídica vinculado a operação registral |
| Endereço pessoal detalhado | PII — dado de localização pessoal |
| JSON bruto original | Contém CONTRIBUINTE e outros dados pessoais |

### Tabela SQLite — `ri_real_json_inventory`

Campos idênticos ao CSV sanitizado. Booleans armazenados como INTEGER (0/1).

### Tabela SQLite — `ri_real_json_runs`

Histórico de execuções do analisador JSON.

| Campo | Descrição |
|---|---|
| `run_id` | UUID único por execução |
| `fonte_arquivo` | Nome do arquivo JSON processado |
| `cns` | CNS identificado no arquivo |
| `total_registros` | Total processado |
| `total_urbano` | Urbanos classificados |
| `total_rural` | Rurais classificados |
| `total_indeterminado` | Indeterminados (LOCALIZACAO inválida) |
| `executed_at` | Timestamp ISO 8601 UTC |

---

## Campos PROIBIDOS (ambas as bases)

| Campo proibido | Motivo |
|---|---|
| Nome de proprietário | PII — LGPD art. 5º, I |
| Nome de cônjuge | PII — LGPD art. 5º, I |
| CPF | PII — dado sensível de identificação |
| CNPJ | Dado de pessoa jurídica vinculado a operação registral |
| RG ou documento de identidade | PII — documento pessoal |
| CONTRIBUINTE | PII — campo do Indicador Real com identificação pessoal |
| Nome de transmitente | PII — parte de negócio jurídico |
| Nome de adquirente | PII — parte de negócio jurídico |
| Endereço pessoal | PII — dado de localização pessoal |
| Texto livre com identificação pessoal | PII — qualquer forma de individualização |

---

*Documento atualizado em 2026-05-15 para v3 — adição da Base JSON (Indicador Real, sprint RI-REAL-JSON-1).*
*Revisar após validação dos totais com a equipe de RI.*
