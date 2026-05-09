# Scanner de Arquivos — Guia de Uso

Módulo: `app/modules/audit/scanner/`
Versão: 1.0.0
Status: **implementado e testado** ✅

> **Princípio de segurança:** o scanner opera em modo estritamente somente leitura.
> Nenhum arquivo do servidor analisado é aberto, modificado, movido, renomeado
> ou excluído em nenhuma circunstância.

---

## Quando usar

Use este scanner para:

- Obter o inventário completo de arquivos e pastas de um caminho do servidor.
- Identificar os maiores arquivos e pastas que explicam o espaço em disco crítico.
- Detectar arquivos com extensões executáveis ou suspeitas.
- Encontrar arquivos muito antigos (candidatos a arquivamento).
- Gerar evidência documentada para o dossiê técnico da vistoria CNJ 213/2026.
- Apoiar diagnóstico antes de qualquer intervenção manual no servidor.

---

## Pré-requisitos

```bash
# 1. Ativar o venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # Linux/macOS

# 2. Variáveis de ambiente (copiar .env.example se ainda não existir)
cp .env.example .env
```

O scanner não usa banco de dados e não precisa de servidor FastAPI em execução.

---

## Uso via CLI

```
python -m app.modules.audit.scanner.cli --help
```

### Parâmetros

| Parâmetro | Obrigatório | Descrição |
|-----------|------------|-----------|
| `--root PATH` | Sim | Diretório raiz a varrer (somente leitura) |
| `--output-dir PATH` | Sim | Onde gravar os relatórios (nunca dentro de `--root`) |
| `--run-name NAME` | Não | Rótulo da execução (auto-gerado se omitido) |
| `--max-depth N` | Não | Profundidade máxima (sem limite se omitido) |
| `--exclude PATTERN` | Não | Nome, substring ou glob a excluir (repetível) |
| `--follow-symlinks` | Não | Seguir links simbólicos (desativado por padrão) |
| `--no-hidden` | Não | Excluir entradas cujo nome começa com `.` |
| `--fail-fast` | Não | Abortar no primeiro erro em vez de registrar e continuar |

### Semântica de `--max-depth`

| Valor | Comportamento |
|-------|--------------|
| omitido | Varredura completa, sem limite de profundidade |
| `0` | Apenas registra o diretório raiz; nenhum arquivo coletado |
| `1` | Coleta arquivos diretamente na raiz; lista subpastas mas não entra |
| `2` | Entra na primeira camada de subpastas; coleta seus arquivos |
| `N` | Entra até N níveis abaixo da raiz para coleta de arquivos |

---

## Sequência operacional recomendada

Para pastas desconhecidas ou grandes, nunca iniciar com varredura completa.
Usar a progressão depth2 → depth4 → full:

| Passo | `--max-depth` | Objetivo |
| ----- | ------------- | -------- |
| 1 — Rascunho | `2` | Ver estrutura de topo; estimar volume; validar permissões |
| 2 — Estimativa | `4` | Avaliar total de arquivos e tamanho antes de varrer tudo |
| 3 — Completo | omitido | Varredura sem limite após confirmar viabilidade |

```powershell
# Passo 1 — depth 2 (estrutura de topo)
python -m app.modules.audit.scanner.cli `
    --root "\\servidor\Acervo" `
    --output-dir "exports\audit\scan-rascunho" `
    --run-name "scan-rascunho" `
    --max-depth 2

# Passo 2 — depth 4 (estimativa)
python -m app.modules.audit.scanner.cli `
    --root "\\servidor\Acervo" `
    --output-dir "exports\audit\scan-estimativa" `
    --run-name "scan-estimativa" `
    --max-depth 4

# Passo 3 — completo (sem limite)
python -m app.modules.audit.scanner.cli `
    --root "\\servidor\Acervo" `
    --output-dir "exports\audit\scan-completo-2026-05-04" `
    --run-name "scan-completo-2026-05-04"
```

> Ver procedimento passo a passo completo em
> [`docs/audit/deployment_and_operation.md`](../audit/deployment_and_operation.md),
> seção 6.

---

## Exemplos

### Varredura completa de um diretório de teste

```bash
python -m app.modules.audit.scanner.cli \
    --root "C:\Teste" \
    --output-dir "exports\audit\scan-teste" \
    --run-name "scan-teste-inicial"
```

### Varredura do servidor limitada a 4 níveis de profundidade

```bash
python -m app.modules.audit.scanner.cli \
    --root "D:\Dados" \
    --output-dir "exports\audit\scan-servidor-2026-05-04" \
    --run-name "scan-servidor-2026-05-04" \
    --max-depth 4 \
    --exclude "$RECYCLE.BIN" \
    --exclude "System Volume Information" \
    --exclude "__pycache__"
```

### Varredura parcial para diagnóstico rápido de espaço

```bash
python -m app.modules.audit.scanner.cli \
    --root "D:\Dados\GED" \
    --output-dir "exports\audit\scan-ged" \
    --run-name "scan-ged-mai2026" \
    --no-hidden
```

### Via módulo Python (uso programático)

```python
from pathlib import Path
from app.modules.audit.scanner.file_scanner import scan
from app.modules.audit.scanner.report import write_all

result = scan(
    root_path=Path("C:/Teste"),
    run_name="scan-programatico",
    exclude_patterns=["$RECYCLE.BIN", "*.tmp"],
    max_depth=5,
    follow_symlinks=False,
)

artefacts = write_all(result, Path("exports/audit/scan-programatico"))

print(f"Arquivos: {result.total_files}")
print(f"Pastas  : {result.total_directories}")
print(f"Tamanho : {result.total_size_bytes:,} bytes")
print(f"Erros   : {result.errors_count}")
```

---

## Arquivos gerados

Todos os artefatos são gravados em `--output-dir`. O diretório é criado
automaticamente se não existir.

| Arquivo | Formato | Conteúdo |
|---------|---------|----------|
| `file_inventory.json` | JSON UTF-8 | Lista completa de arquivos e pastas com metadados |
| `file_inventory.csv` | CSV UTF-8 BOM | Versão tabular para Excel/LibreOffice |
| `scan_summary.md` | Markdown | Relatório legível com resumo, top 10, extensões, suspeitos |
| `scan_manifest.json` | JSON UTF-8 | Rastreabilidade: run_id, parâmetros, hashes SHA-256 dos artefatos |

### Estrutura do `file_inventory.json`

```json
{
  "metadata": {
    "run_id": "uuid",
    "run_name": "scan-servidor-2026-05-04",
    "root_path": "[root]",
    "started_at": "2026-05-04T10:00:00+00:00",
    "finished_at": "2026-05-04T10:00:42+00:00",
    "duration_seconds": 42.1,
    "total_files": 12543,
    "total_directories": 876,
    "total_size_bytes": 45678901234,
    "errors_count": 3,
    "excluded_count": 7
  },
  "parameters": { "max_depth": null, "follow_symlinks": false, ... },
  "files": [
    {
      "name": "contrato.pdf",
      "extension": ".pdf",
      "path_relative": "Contratos/2025/contrato.pdf",
      "parent_path": "Contratos/2025",
      "entry_type": "file",
      "depth": 3,
      "size_bytes": 245760,
      "modified_at": "2025-11-15T14:32:10+00:00",
      "created_at": "2025-11-15T14:32:10+00:00",
      "error": null
    }
  ],
  "directories": [ ... ],
  "errors": [ ... ]
}
```

### Colunas do `file_inventory.csv`

```
entry_type, name, extension, path_relative, parent_path, depth,
size_bytes, modified_at, created_at, direct_files, direct_subdirs,
total_size_bytes, error
```

O CSV usa **UTF-8 com BOM** (`utf-8-sig`) para abrir corretamente no Excel
no Windows sem precisar importar manualmente.

### `scan_manifest.json`

```json
{
  "manifest_id": "uuid",
  "generated_at": "2026-05-04T10:00:42+00:00",
  "scanner_version": "1.0.0",
  "read_only": true,
  "run": { "run_id": "...", "run_name": "...", "root_path": "[root]", ... },
  "counts": { "total_files": 12543, ... },
  "output_files": {
    "file_inventory_json": {
      "filename": "file_inventory.json",
      "size_bytes": 4567890,
      "sha256": "abc123..."
    },
    ...
  }
}
```

O campo `read_only: true` é imutável e serve como evidência para o dossiê técnico.

---

## Saída no terminal

```
Starting read-only scan…
  root        : D:\Dados
  output-dir  : exports\audit\scan-servidor-2026-05-04
  run-name    : scan-servidor-2026-05-04
  max-depth   : 4

Scan complete.
  files       : 12,543
  directories : 876
  errors      : 3
  excluded    : 7
  duration    : 42.10s

Output files:
  file_inventory_json            exports\audit\scan-servidor-2026-05-04\file_inventory.json
  file_inventory_csv             exports\audit\scan-servidor-2026-05-04\file_inventory.csv
  scan_summary_md                exports\audit\scan-servidor-2026-05-04\scan_summary.md
  scan_manifest_json             exports\audit\scan-servidor-2026-05-04\scan_manifest.json
```

---

## Execução real validada — scan-docs-cartorio

Esta seção registra a primeira execução real do scanner em um caminho controlado
(pasta `docs/` do Cartório System), validando o comportamento da ferramenta em
ambiente Windows real antes de ser aplicada ao servidor de produção da serventia.

### Parâmetros da execução

| Campo | Valor |
| ------- | ------- |
| `run_id` | `ef8139c3-07cb-400c-8c48-e319623dbacf` |
| `run_name` | `scan-docs-cartorio` |
| `scanner_version` | `1.0.0` |
| `read_only` | `true` |
| `exclude_patterns` (adicionais) | `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.git`, `.venv` |
| Data | 2026-05-04 |

### Métricas

| Métrica | Valor |
| ------- | ------- |
| Total de arquivos | 1.539 |
| Total de pastas | 134 |
| Tamanho total | 2,02 GB (2.169.948.182 bytes) |
| Duração | 0,428 s |
| Erros de acesso | 0 |
| Excluídos | 22 |

### Distribuição por extensão (principais)

| Extensão | Quantidade |
| ---------- | ------------ |
| `.pdf` | 1.168 |
| `.ods` | 159 |
| `.odt` | 120 |
| `.xlsx` | 22 |
| `.docx` | 16 |

### Achados identificados na varredura

#### 1 — Arquivo de vídeo de grande porte

Caminho: `LGPD/Treinamento IA nas Serventias.mp4`
Tamanho: ~1 GB — corresponde a aproximadamente 46% do total varrido.
Risco: se presente no servidor junto com documentos operacionais, consome espaço
crítico e não tem relação com o fluxo documental cartorial.
Ação sugerida: avaliar mover para armazenamento externo ou repositório de treinamento.

#### 2 — Arquivo executável em pasta de documentos financeiros

Caminho: `Gerenciamento_financeiro/2025/Março/Fundos e taxas/ExtensionModule.exe`
Extensão `.exe` em pasta de documentos — achado de segurança que exige investigação:
qual é a origem, qual a função, quando foi criado e se é necessário manter.
Risco: presença de executável não identificado em pasta de trabalho é padrão de risco
independente da probabilidade de ameaça.

#### 3 — POPs sem atualização confirmada desde 2019

- `Politicas, manuais e procedimentos/Procedimento Protesto.odt` (2019)
- `Politicas, manuais e procedimentos/Procedimento Protesto.pdf` (2019)
- `Procedimentos Operacionais Padrão/Como fazer um POP.odt` (2019)
POPs com mais de 6 anos sem revisão registrada. Devem ser avaliados quanto à
validade operacional atual e alinhamento com o Provimento CNJ 213/2026.

#### 4 — Acervo financeiro histórico extenso

Arquivos `.ods` e `.xlsx` desde 2016/2018 em `Gerenciamento_financeiro/`.
Representam o histórico a ser importado via `EntrySource = IMPORT_XLSX` (Etapa 6
do backlog financeiro). A pasta já está identificada e o volume é conhecido.

#### 5 — Documentação técnica e atos normativos presentes

Pastas `Estrutura tecnica` e `Atos Normativos e Administrativos` identificadas,
incluindo documentação do Provimento CNJ 213. Conteúdo relevante para compor o
dossiê técnico da vistoria — já existe material de base.

### Validação do comportamento real

| Garantia | Resultado |
| --------- | ----------- |
| Nenhum arquivo modificado | ✅ confirmado |
| `read_only: true` no manifest | ✅ confirmado |
| Caminhos Windows com espaços tratados | ✅ confirmado |
| Arquivos com caracteres especiais no nome | ✅ tratados sem erro |
| Erros de acesso | 0 (zero) |
| Duração para 1.539 arquivos | 0,428 s — performance adequada |

**Conclusão:** o scanner está pronto para ser executado no servidor de produção
da serventia. Recomenda-se rodar primeiro em uma pasta de menor risco (como
`D:\Dados\GED` ou `D:\Documentos`) antes de varrer o volume completo.

---

## Achados preliminares para Sprint 2 — AuditFinding v1

Os achados abaixo foram identificados na execução `scan-docs-cartorio` e estão
prontos para ser registrados como `AuditFinding` assim que a Sprint 2 estiver
implementada. Cada achado segue o modelo definido em
[`docs/quality/risk_register_model.md`](../quality/risk_register_model.md).

> **Importante:** estes são achados preliminares baseados em metadados (nome,
> extensão, data). Nenhum conteúdo de arquivo foi lido. A confirmação e a
> classificação final de cada achado requer revisão humana.

---

### AF-001 — Arquivo executável em pasta de documentos financeiros

| Campo | Valor |
| ------- | ------- |
| `id` | `AF-001` |
| `category` | `SECURITY` |
| `title` | Arquivo `.exe` identificado em pasta de gerenciamento financeiro |
| `severity` | `HIGH` |
| `probability` | `MEDIUM` |
| `impact` | `HIGH` |
| `priority` | `URGENT` |
| `origin` | `SCANNER` |
| `status` | `OPEN` |
| `evidence_summary` | Scanner identificou `ExtensionModule.exe` em `Gerenciamento_financeiro/2025/Março/Fundos e taxas/`. Metadados coletados: nome, caminho, extensão. Conteúdo não lido. |
| `recommendation` | Investigar origem, função e necessidade do arquivo. Se não for necessário, remover após autorização do gestor. Se for ferramenta legítima, documentar e mover para pasta controlada. |
| `owner` | Responsável TI |
| `cnj_requirement` | E-04: gestão de vulnerabilidades; G-04: classificação dos dados |

---

### AF-002 — Arquivo de vídeo de 1 GB consumindo espaço crítico em disco

| Campo | Valor |
| ------- | ------- |
| `id` | `AF-002` |
| `category` | `DOCUMENT` |
| `title` | Arquivo de vídeo de ~1 GB em pasta de documentos (LGPD) |
| `severity` | `MEDIUM` |
| `probability` | `HIGH` |
| `impact` | `MEDIUM` |
| `priority` | `HIGH` |
| `origin` | `SCANNER` |
| `status` | `OPEN` |
| `evidence_summary` | Scanner identificou `LGPD/Treinamento IA nas Serventias.mp4` com ~1 GB — ~46% do total varrido na pasta docs. |
| `recommendation` | Avaliar necessidade de manter o arquivo no servidor. Se for material de treinamento, mover para repositório externo (nuvem, disco externo) e remover do servidor de produção para liberar espaço. |
| `owner` | Gestor |
| `cnj_requirement` | RI-02: disco de dados com espaço crítico |

---

### AF-003 — POPs operacionais sem revisão confirmada desde 2019

| Campo | Valor |
| ------- | ------- |
| `id` | `AF-003` |
| `category` | `OPERATIONAL` |
| `title` | POPs de Protesto e modelo de POP sem atualização desde 2019 |
| `severity` | `MEDIUM` |
| `probability` | `HIGH` |
| `impact` | `MEDIUM` |
| `priority` | `HIGH` |
| `origin` | `SCANNER` |
| `status` | `OPEN` |
| `evidence_summary` | Scanner identificou `Procedimento Protesto.odt`, `Procedimento Protesto.pdf` e `Como fazer um POP.odt` com data de modificação de 2019 (mais de 6 anos). Conteúdo não lido — classificação baseada apenas em metadados. |
| `recommendation` | Revisar os POPs listados quanto à validade operacional atual. Atualizar ou criar nova versão com data de aprovação. Verificar alinhamento com o Provimento CNJ 213/2026. |
| `owner` | Gestor |
| `cnj_requirement` | RO: fluxos operacionais; G-08: capacitação documentada |

---

### AF-004 — Acervo financeiro histórico sem confirmação de backup estruturado

| Campo | Valor |
| ------- | ------- |
| `id` | `AF-004` |
| `category` | `BACKUP` |
| `title` | Planilhas financeiras históricas (2016–2026) sem confirmação de inclusão no backup |
| `severity` | `HIGH` |
| `probability` | `MEDIUM` |
| `impact` | `HIGH` |
| `priority` | `HIGH` |
| `origin` | `SCANNER` |
| `status` | `OPEN` |
| `evidence_summary` | Scanner identificou estrutura de pastas financeiras anuais desde 2016 com 159 arquivos `.ods` e 22 `.xlsx`. A inclusão desses arquivos no backup do Cobian Gravity não foi confirmada formalmente. |
| `recommendation` | Verificar se a pasta `Gerenciamento_financeiro/` está incluída no escopo do Cobian Gravity. Confirmar que esses arquivos estão cobertos pelo RPO. Incluir no PRD como ativo crítico. |
| `owner` | Responsável TI |
| `cnj_requirement` | B-03: backup completo; B-05: backup off-site |

---

### AF-005 — Ausência de confirmação de segregação de documentos sensíveis

| Campo | Valor |
| ------- | ------- |
| `id` | `AF-005` |
| `category` | `ACCESS` |
| `title` | Documentos de LGPD e atos normativos sem confirmação de controle de acesso |
| `severity` | `MEDIUM` |
| `probability` | `MEDIUM` |
| `impact` | `MEDIUM` |
| `priority` | `MEDIUM` |
| `origin` | `SCANNER` |
| `status` | `OPEN` |
| `evidence_summary` | Scanner identificou pasta `LGPD/` com material de treinamento e pasta `Atos Normativos e Administrativos/` com documentação regulatória. Permissões NTFS dessas pastas não foram auditadas nesta varredura (Fase 5 pendente). |
| `recommendation` | Auditar permissões NTFS das pastas `LGPD/`, `Atos Normativos e Administrativos/` e `Provimentos CNJ/`. Verificar quem tem acesso de leitura e escrita. Implementar controle por grupo/perfil conforme matriz de acesso. |
| `owner` | Responsável TI |
| `cnj_requirement` | A-05: controle de acesso por perfil; L-01: LGPD |

---

### Resumo dos achados preliminares

| ID | Categoria | Título resumido | Severidade | Prioridade |
| ---- | ----------- | ---------------- | ------------ | ------------ |
| AF-001 | SECURITY | Executável em pasta financeira | HIGH | URGENT |
| AF-002 | DOCUMENT | Vídeo de 1 GB consumindo disco | MEDIUM | HIGH |
| AF-003 | OPERATIONAL | POPs sem revisão desde 2019 | MEDIUM | HIGH |
| AF-004 | BACKUP | Histórico financeiro sem backup confirmado | HIGH | HIGH |
| AF-005 | ACCESS | Segregação de pastas sensíveis não auditada | MEDIUM | MEDIUM |

---

## Exclusões padrão

O scanner sempre exclui automaticamente (independente do `--exclude` do usuário):

```python
"$RECYCLE.BIN", "System Volume Information", "desktop.ini",
"Thumbs.db", ".Spotlight-V100", ".Trashes", ".fseventsd"
```

Para suprimir essas exclusões padrão, edite `DEFAULT_EXCLUDES` em
[`app/modules/audit/scanner/file_scanner.py`](../../app/modules/audit/scanner/file_scanner.py).

---

## Garantias de segurança

O scanner **nunca** realiza as seguintes operações no caminho analisado:

| Operação proibida | Como é garantido |
|-------------------|-----------------|
| Abrir conteúdo de arquivos | Apenas `os.stat()` e `os.path.*` — nunca `open()` |
| Modificar arquivos | Nenhuma chamada a `open(..., "w")` ou equivalente |
| Mover / renomear / excluir | Nenhuma chamada a `os.remove`, `shutil.move`, `os.rename` |
| Gravar dentro do diretório varrido | `validate_output_dir()` rejeita `--output-dir` dentro de `--root` |
| Calcular hash de arquivos do servidor | Hash é calculado apenas nos artefatos de saída (próprios) |
| Seguir symlinks fora da raiz | Desativado por padrão (`follow_symlinks=False`) |

Os testes `test_scan_does_not_modify_files` e `test_scan_does_not_create_files_in_root`
verificam automaticamente estas garantias a cada `pytest`.

---

## Limitações da Sprint 1

| Limitação | Nota |
|-----------|------|
| Não lê conteúdo interno de arquivos | Análise semântica vem na Sprint 2 (Fase 2) |
| Não detecta duplicatas por conteúdo | Requer hash de arquivo (proibido na fase 1) |
| Não acessa recursos de rede remotos | Apenas caminhos locais ou UNC já mapeados |
| Não coleta informações de SMART/saúde de disco | Requer ferramentas de SO — Fase 3 |
| Tamanho de pasta = soma dos arquivos diretos | Não é recursivo por design (simplicidade) |
| Não integra com banco de dados | Sem persistência de resultado — Fase posterior |
| Não tem endpoint HTTP | CLI apenas nesta sprint |
| Não compara com execuções anteriores | Diff entre scans vem na Fase 11 |

---

## Uso prático imediato

Após rodar o scanner no servidor da serventia, o gestor tem:

1. **`scan_summary.md`** — abrir no VS Code ou no browser; ver top 10 maiores arquivos
   e pastas, identificar o que consome espaço no disco crítico.
2. **`file_inventory.csv`** — abrir no Excel; filtrar por extensão, ordenar por tamanho
   ou data para identificar arquivos antigos e candidatos a arquivamento.
3. **`scan_manifest.json`** — guardar como evidência no dossiê técnico para a vistoria.
4. **`file_inventory.json`** — base para as próximas análises automatizadas (Sprint 2).

---

## Próximos passos — Sprint 2

A Sprint 2 implementa o **AuditFinding CRUD** em `app/modules/audit/findings/`:

- Modelo `AuditFinding` com migration Alembic
- Schemas Pydantic (Create / Update / Read)
- Service CRUD com regras de transição de status
- Endpoints em `/api/v1/audit/findings`
- Após o scanner identificar riscos, o gestor os registra formalmente como achados

Ver [`docs/audit/module_roadmap.md`](../audit/module_roadmap.md) para o roadmap completo.

---

## Estrutura do módulo

```text
app/modules/audit/
├── __init__.py
└── scanner/
    ├── __init__.py
    ├── models.py          # FileEntry, DirectoryEntry, ScanError, ScanResult
    ├── file_scanner.py    # função scan() — lógica principal read-only
    ├── report.py          # write_json / write_csv / write_markdown / write_manifest
    └── cli.py             # entry point: python -m app.modules.audit.scanner.cli

tests/
└── test_file_scanner.py  # 25 testes (24 passed, 1 skipped no Windows)

exports/audit/             # artefatos gerados (não versionados)
```
