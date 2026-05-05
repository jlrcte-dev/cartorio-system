# DocumentDiagnosis — app/modules/audit/diagnosis/

> **Sprint 3 concluída.** Análise baseada exclusivamente em metadados do inventário.
> Nenhum arquivo original é acessado.

Última atualização: 2026-05-04

---

## Objetivo

O `DocumentDiagnosis` analisa o `file_inventory.json` produzido pelo scanner e
identifica **candidatos a achados documentais** com base exclusivamente em:

- nomes e caminhos de arquivos
- extensões
- tamanhos (bytes)
- datas de modificação e criação

**Nunca abre, lê, move, renomeia ou altera qualquer arquivo do acervo.**

---

## Relação com o scanner

```
Scanner (Sprint 1)                   DocumentDiagnosis (Sprint 3)
─────────────────────────────────    ─────────────────────────────
os.walk() no servidor/acervo    →    lê file_inventory.json
coleta: nome, path, tamanho,         aplica 7 regras de metadados
        data, extensão               gera DiagnosisCandidate[]
gera: file_inventory.json            gera 4 artefatos no output_dir
```

O `DocumentDiagnosis` **não acessa o servidor diretamente**. Ele recebe o
`file_inventory.json` como entrada e opera sobre dados já coletados.

---

## Diferença entre candidato e achado

| | `DiagnosisCandidate` | `AuditFinding` |
|---|---|---|
| **Status** | `CANDIDATE` (fixo) | `OPEN`, `IN_PROGRESS`, `RESOLVED`… |
| **Criação** | automática, por regra de metadados | manual, após revisão humana |
| **Base** | nome, path, tamanho, data | evidência validada pelo gestor |
| **Banco de dados** | não usa banco | tabela `audit_findings` |
| **Certeza** | sugestão para revisão | achado confirmado |

**Fluxo correto:** candidato → revisão humana → `AuditFinding` (se confirmado).

---

## Decisão arquitetural D-23

> O `DocumentDiagnosis` recebe como entrada o `file_inventory.json` — nunca um
> caminho de disco ou servidor diretamente.

Razões:
1. **Separação de responsabilidades:** scanner acessa o servidor; diagnóstico analisa dados já coletados.
2. **Rastreabilidade:** o inventory tem hash registrado no manifest; o diagnóstico é reproduzível.
3. **Segurança:** o diagnóstico nunca precisa de permissão de acesso ao servidor.
4. **Testabilidade:** testes usam inventories sintéticos, sem caminhos reais.

Ver `docs/decisions.md` (D-23) e `docs/AUDIT_DEPLOYMENT_AND_OPERATION.md` (seção 12).

---

## Regras implementadas na Sprint 3

| ID | Nome | O que detecta | Severidade | Prioridade |
|----|------|---------------|------------|------------|
| `DIAG-001` | `credential_by_name` | Nome/caminho contendo: login, senha, password, token, engegraph, sefaz, ecac… | HIGH | SEVEN_DAYS |
| `DIAG-002` | `executable_by_extension` | Extensões `.exe .bat .cmd .ps1 .vbs .scr .msi` | HIGH | THIRTY_DAYS |
| `DIAG-003` | `temp_folder` | Arquivos em caminhos contendo Temp/Temporário | MEDIUM | THIRTY_DAYS |
| `DIAG-004a` | `large_pdf` | PDFs acima de `--large-pdf-mb` (padrão 10 MB) | MEDIUM | NINETY_DAYS |
| `DIAG-004b` | `large_video` | Arquivos `.mp4 .mov .avi .mkv` | LOW | BACKLOG |
| `DIAG-004c` | `large_other` | Arquivos (não-PDF/vídeo) acima de `--large-file-mb` (padrão 50 MB) | LOW | BACKLOG |
| `DIAG-005` | `generic_name` | Nomes genéricos: `documento.pdf`, `scan.pdf`, `sem título`, `-arquivo`… | LOW | BACKLOG |
| `DIAG-006` | `financial_archive` | Caminhos com: `financeiro`, `emolumentos`, `boletos`, `sefaz`… — **agregado por pasta** | MEDIUM | THIRTY_DAYS |
| `DIAG-007` | `old_policy_docs` | Arquivos em pastas de política/LGPD/POP não modificados há `--old-file-years` anos (padrão 5) | MEDIUM | NINETY_DAYS |

**Candidatos `BACKLOG` são excluídos por padrão.** Use `--include-low-priority` para incluí-los.

---

## Como executar a CLI

```powershell
# Análise padrão (candidatos MEDIUM+ e HIGH)
python -m app.modules.audit.diagnosis.cli `
    --inventory "C:\Audit_Reports\2026-05-04\scan-cartorios-full\file_inventory.json" `
    --manifest  "C:\Audit_Reports\2026-05-04\scan-cartorios-full\scan_manifest.json" `
    --output-dir "C:\Audit_Reports\2026-05-04\diagnosis-cartorios-full" `
    --run-name "diagnosis-cartorios-full"

# Incluindo candidatos de baixa prioridade
python -m app.modules.audit.diagnosis.cli `
    --inventory "C:\Audit_Reports\2026-05-04\scan\file_inventory.json" `
    --output-dir "C:\Audit_Reports\2026-05-04\diagnosis-full" `
    --include-low-priority

# Com thresholds customizados
python -m app.modules.audit.diagnosis.cli `
    --inventory "..." `
    --output-dir "..." `
    --old-file-years 3 `
    --large-file-mb 100 `
    --large-pdf-mb 5
```

### Parâmetros

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--inventory` | (obrigatório) | Caminho para `file_inventory.json` |
| `--manifest` | (opcional) | Caminho para `scan_manifest.json` |
| `--output-dir` | (obrigatório) | Diretório de saída |
| `--run-name` | (auto) | Nome da execução de diagnóstico |
| `--old-file-years` | `5` | Anos sem modificação para flagear documentos de política |
| `--large-file-mb` | `50` | Limite em MB para arquivos genéricos grandes |
| `--large-pdf-mb` | `10` | Limite em MB para PDFs grandes |
| `--include-low-priority` | `false` | Incluir candidatos de prioridade BACKLOG |
| `--fail-fast` | `false` | Abortar no primeiro erro de carregamento |

---

## Arquivos gerados

| Arquivo | Descrição |
|---|---|
| `document_diagnosis.json` | Todos os candidatos em JSON estruturado |
| `document_diagnosis.csv` | Versão tabular para análise em planilha (UTF-8 BOM) |
| `document_diagnosis.md` | Relatório legível com candidatos agrupados por regra |
| `diagnosis_manifest.json` | Metadados da execução + SHA-256 dos artefatos gerados |

### Conteúdo do manifest

```json
{
  "diagnosis_id": "uuid",
  "run_name": "...",
  "generated_at": "...",
  "scanner_run_id": "...",
  "diagnosis_version": "1.0.0",
  "read_only": true,
  "content_read": false,
  "original_files_accessed": false,
  "counts": { "total_files_analyzed": ..., "total_candidates": ... },
  "output_files": { "...": { "filename": "...", "sha256": "..." } }
}
```

---

## Limitações desta Sprint 3

- Análise baseada **exclusivamente em metadados** (nome, path, tamanho, data).
- Sem leitura de conteúdo de arquivos.
- Sem detecção de duplicatas por hash de conteúdo.
- Sem análise semântica de texto.
- Sem integração automática com `AuditFinding` — candidatos requerem revisão humana.
- Regras de nome genérico cobrem padrões definidos — não são exaustivas.
- Candidatos são sugestões, não afirmações de irregularidade.

---

## Próximos passos — Sprint 3.5

| Item | Escopo |
|---|---|
| Hardening das regras | Adicionar padrões de nomenclatura da serventia real (após execução inicial) |
| Execução real | Rodar sobre `_local_data/serventia_docs/` no ambiente do gestor |
| Validação de candidatos | Gestor revisa e promove candidatos a `AuditFinding` |
| Documentar falsos positivos | Refinar regras com base nos resultados reais |
| Deduplicação por nome+tamanho | Identificar prováveis duplicatas sem hash de conteúdo |
| Relatório de cobertura | Comparar candidatos vs. achados registrados |

---

## Estrutura de arquivos

```
app/modules/audit/diagnosis/
├── __init__.py
├── models.py      # DiagnosisCandidate, DiagnosisResult
├── rules.py       # 7 regras DIAG-001 a DIAG-007
├── analyzer.py    # DocumentAnalyzer — carrega inventory, executa regras
├── report.py      # write_json, write_csv, write_markdown, write_manifest, write_all
└── cli.py         # Entry point: python -m app.modules.audit.diagnosis.cli
```
