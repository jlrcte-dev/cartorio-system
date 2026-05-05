# Execução Real — DocumentDiagnosis v1

> **Objetivo:** Guia prático para executar o DocumentDiagnosis em ambiente controlado, garantindo rastreabilidade, conformidade de segurança e preparação para revisão humana.

**Data:** 2026-05-04 (Sprint 3.5)  
**Status:** Pronto para execução real  
**Versão:** 1.0.0

---

## I. Pré-requisitos

### 1. Acesso aos artefatos do scanner

Você deve ter:
- `file_inventory.json` gerado pelo scanner (obrigatório)
- `scan_manifest.json` (opcional, mas recomendado para rastreabilidade)

**Localização típica:**
```
C:\Audit_Reports\<YYYY-MM-DD>\<scan-run-id>\
├── file_inventory.json
├── file_inventory.csv
├── scan_manifest.json
├── scan_summary.md
└── errors.json
```

### 2. Variáveis de ambiente

```powershell
# Verifique que Python e pytest estão disponíveis
python --version
pytest --version
```

### 3. Ambiente isolado para outputs

Crie um diretório **FORA do repositório do Cartório System** para armazenar outputs reais:

```powershell
# Exemplo (OBRIGATÓRIO usar local externo)
mkdir "C:\Audit_Reports\2026-05-04\diagnosis-cartorios-full"
```

**Regra crítica:** Os outputs do diagnóstico NUNCA devem entrar no Git do projeto.

---

## II. Checklist Pré-Execução

Antes de executar o diagnóstico, valide:

```markdown
- [ ] `file_inventory.json` existe e é válido JSON
- [ ] `scan_manifest.json` existe (confirmar scanner_run_id)
- [ ] Diretório de output existe e está vazio ou isolado fora do Git
- [ ] Nenhum arquivo original será acessado (verificar contrato de segurança)
- [ ] Documentar data, operador e parâmetros da execução
```

---

## III. Comando de Execução

### Execução Padrão (recomendado para maioria dos casos)

```powershell
cd "C:\Users\João\Documents\cartorio_system"

python -m app.modules.audit.diagnosis.cli `
    --inventory "C:\Audit_Reports\2026-05-04\scan-cartorios-full\file_inventory.json" `
    --manifest "C:\Audit_Reports\2026-05-04\scan-cartorios-full\scan_manifest.json" `
    --output-dir "C:\Audit_Reports\2026-05-04\diagnosis-cartorios-full" `
    --run-name "diagnosis-cartorios-full"
```

**Resultado esperado:**
- 4 arquivos gerados no `output-dir`
- Execução completa em < 10 segundos (1000+ arquivos)

### Execução com Todos os Candidatos (incluindo BACKLOG)

Se quiser incluir vídeos, nomes genéricos e outros arquivos grandes de prioridade baixa:

```powershell
python -m app.modules.audit.diagnosis.cli `
    --inventory "C:\Audit_Reports\2026-05-04\scan\file_inventory.json" `
    --output-dir "C:\Audit_Reports\2026-05-04\diagnosis-completo" `
    --run-name "diagnosis-com-backlog" `
    --include-low-priority
```

### Execução com Parâmetros Customizados

Ajuste limites de tamanho e idade conforme necessário:

```powershell
python -m app.modules.audit.diagnosis.cli `
    --inventory "..." `
    --output-dir "..." `
    --run-name "..." `
    --old-file-years 3 `
    --large-file-mb 100 `
    --large-pdf-mb 5
```

| Parâmetro | Padrão | Uso |
|---|---|---|
| `--old-file-years` | `5` | Idade mínima para flagear documentos de política/LGPD |
| `--large-file-mb` | `50` | Limite para outros arquivos grandes |
| `--large-pdf-mb` | `10` | Limite específico para PDFs |
| `--include-low-priority` | `false` | Incluir candidatos BACKLOG (videos, genéricos) |
| `--fail-fast` | `false` | Parar no primeiro erro vs. continuar |

---

## IV. Arquivos de Saída

O diagnóstico gera **4 artefatos** no `output-dir`:

| Arquivo | Tipo | Uso | Tamanho típico |
|---|---|---|---|
| `document_diagnosis.json` | JSON estruturado | Integração, análise programática | 50 KB–1 MB |
| `document_diagnosis.csv` | CSV UTF-8 BOM | Análise em Excel | 30 KB–500 KB |
| `document_diagnosis.md` | Markdown | Leitura legível, relatório | 20 KB–200 KB |
| `diagnosis_manifest.json` | JSON metadados | Rastreabilidade + SHA-256 | < 5 KB |

### Estrutura do `diagnosis_manifest.json`

```json
{
  "diagnosis_id": "uuid-único-da-execução",
  "run_name": "diagnosis-cartorios-full",
  "generated_at": "2026-05-04T14:30:00+00:00",
  "scanner_run_id": "scan-id-do-scanner",
  "diagnosis_version": "1.0.0",
  "read_only": true,
  "content_read": false,
  "original_files_accessed": false,
  "counts": {
    "total_files_analyzed": 1539,
    "total_candidates": 42
  },
  "output_files": {
    "document_diagnosis_json": {
      "filename": "document_diagnosis.json",
      "size_bytes": 123456,
      "sha256": "abcdef..."
    },
    ...
  }
}
```

**Campos de segurança obrigatórios:**
- `read_only: true` — nenhum arquivo foi modificado
- `content_read: false` — nenhum conteúdo foi lido
- `original_files_accessed: false` — nenhum arquivo original foi acessado

---

## V. Validação Pós-Execução

### 1. Verificar integridade dos outputs

```powershell
# Confirmar que os 4 arquivos existem
Get-ChildItem "C:\Audit_Reports\2026-05-04\diagnosis-cartorios-full\"

# Validar JSON (testar parseable)
cat "C:\Audit_Reports\2026-05-04\diagnosis-cartorios-full\diagnosis_manifest.json" | ConvertFrom-Json
```

### 2. Validar manifest

```powershell
# Verificar flags de segurança
$manifest = Get-Content "....\diagnosis_manifest.json" | ConvertFrom-Json
$manifest.read_only      # deve ser: true
$manifest.content_read   # deve ser: false
$manifest.original_files_accessed  # deve ser: false
```

### 3. Verificar hashes dos outputs

```powershell
# Calcular SHA-256 real do JSON gerado
$file = "C:\Audit_Reports\2026-05-04\diagnosis-cartorios-full\document_diagnosis.json"
$hash = (Get-FileHash -Path $file -Algorithm SHA256).Hash

# Comparar com manifest
$manifest.output_files.document_diagnosis_json.sha256
# Devem ser idênticos
```

### 4. Revisar `document_diagnosis.md`

```markdown
## Checklist de validação do relatório:

- [ ] Título contém run_name correto
- [ ] Seção "AVISO IMPORTANTE" está presente (metadados-only)
- [ ] Distribuição de severidade está correta
- [ ] Candidatos estão agrupados por regra (DIAG-001 a DIAG-007)
- [ ] Cada candidato tem:
  - [ ] Título descritivo
  - [ ] Descrição clara
  - [ ] Evidence summary
  - [ ] Caminho do arquivo ou pasta
  - [ ] Ação recomendada
  - [ ] Nível de confiança
- [ ] Aviso de segurança operacional está no rodapé
- [ ] Nenhuma path absoluta do servidor real aparece
```

### 5. Revisar `document_diagnosis.csv`

Abra em Excel:

```markdown
- [ ] Cabeçalhos estão corretos (candidate_id, rule_id, category, severity, priority, etc.)
- [ ] Todas as linhas têm dados válidos
- [ ] Severidades são: CRITICAL, HIGH, MEDIUM, LOW ou INFORMATIONAL
- [ ] Prioridades são: URGENT, SEVEN_DAYS, THIRTY_DAYS, NINETY_DAYS, BACKLOG
- [ ] Confiança está entre 0 e 1
- [ ] Caminhos fazem sentido (relativo ao root analisado)
```

### 6. Revisar `document_diagnosis.json`

```powershell
$json = Get-Content "....\document_diagnosis.json" | ConvertFrom-Json

# Verificar contagem de candidatos
$json.total_candidates

# Verificar que nenhum candidate tem status diferente de "CANDIDATE"
$json.candidates | Select-Object -Unique status
# Esperado: ["CANDIDATE"]

# Verificar que nenhum candidate tem relacionment a database IDs
$json.candidates | Where-Object { $_.candidate_id -NotMatch '^[a-f0-9\-]{36}$' }
# Esperado: nenhum resultado (todos UUIDs válidos)
```

---

## VI. Separação de Candidatos para Revisão Humana

Após validar os outputs, os candidatos estão prontos para revisão gerencial.

### Organizando candidatos por severidade

```powershell
# Abrir CSV em Excel
Invoke-Item "C:\Audit_Reports\2026-05-04\diagnosis-cartorios-full\document_diagnosis.csv"

# Filtros recomendados (Excel):
1. Severity = HIGH → revisar primeiro (credenciais, executáveis)
2. Severity = MEDIUM → revisar segundo (financeiro, temp folders, docs antigos)
3. Severity = LOW → revisar após (genéricos, vídeos)
```

### Fluxo de validação

```
Candidato (DiagnosisCandidate)
    ↓
Revisão humana (gestor da serventia)
    ↓
Validado?
    ├─ SIM → AuditFinding (POST /api/v1/audit/findings)
    └─ NÃO → Descartar ou registrar como "falso positivo"
```

**Regra crítica:** Nenhum candidato vira `AuditFinding` sem revisão humana explícita.

---

## VII. Relatório de Execução Real

Use este template para documentar cada execução:

### Seção: Execução do DocumentDiagnosis — [DATA]

```markdown
## Execução do DocumentDiagnosis — 2026-05-04

### Metadados da execução

| Campo | Valor |
|---|---|
| **Data/Hora** | 2026-05-04 14:30:00 UTC |
| **Operador** | [NOME] |
| **Scanner Run ID** | scan-cartorios-full |
| **Diagnosis ID** | [UUID] |
| **Caminho do inventory** | C:\Audit_Reports\2026-05-04\scan-cartorios-full\file_inventory.json |
| **Caminho de outputs** | C:\Audit_Reports\2026-05-04\diagnosis-cartorios-full |
| **Run name** | diagnosis-cartorios-full |

### Parâmetros de diagnóstico

| Parâmetro | Valor |
|---|---|
| `--old-file-years` | 5 |
| `--large-file-mb` | 50 |
| `--large-pdf-mb` | 10 |
| `--include-low-priority` | false |

### Resultados

| Métrica | Valor |
|---|---|
| Arquivos analisados | 1539 |
| Candidatos identificados | 42 |
| CRITICAL | 0 |
| HIGH | 12 |
| MEDIUM | 18 |
| LOW | 10 |
| BACKLOG | 2 (excluídos) |

### Distribuição por regra

| Regra | ID | Candidatos |
|---|---|---|
| Credenciais por nome | DIAG-001 | 3 |
| Executáveis/scripts | DIAG-002 | 2 |
| Pastas temporárias | DIAG-003 | 5 |
| PDFs grandes | DIAG-004a | 8 |
| Vídeos | DIAG-004b | 0 |
| Outros arquivos grandes | DIAG-004c | 0 |
| Nomes genéricos | DIAG-005 | 12 (excluído/BACKLOG) |
| Acervo financeiro | DIAG-006 | 8 |
| Docs antigos de política | DIAG-007 | 4 |

### Validação de segurança

- [ ] `read_only: true` no manifest ✓
- [ ] `content_read: false` no manifest ✓
- [ ] `original_files_accessed: false` no manifest ✓
- [ ] Nenhum arquivo original foi acessado ✓
- [ ] Nenhum hash de conteúdo foi calculado ✓
- [ ] Nenhum arquivo foi movido/deletado/modificado ✓
- [ ] Nenhum AuditFinding foi criado automaticamente ✓
- [ ] Outputs estão **fora do repositório Git** ✓

### Próximos passos

1. [ ] Compartilhar document_diagnosis.md com gestor
2. [ ] Gestor revisa candidatos HIGH (12 itens)
3. [ ] Gestor valida candidatos MEDIUM (18 itens)
4. [ ] Criar AuditFinding para achados confirmados
5. [ ] Atualizar roadmap com lições aprendidas
6. [ ] Agendar execução periódica (se confirmado o padrão)

### Notas operacionais

[Observações livres do operador sobre a execução, falsos positivos confirmados, padrões encontrados, etc.]
```

---

## VIII. Segurança: O Que NÃO Fazer

### ❌ PROIBIDO

```markdown
- [ ] NÃO abrir PDFs, DOCXs, XLSXs ou documentos originais
- [ ] NÃO calcular hash SHA-256 dos arquivos originais
- [ ] NÃO mover, renomear, deletar ou copiar arquivos do acervo
- [ ] NÃO armazenar outputs **dentro** do repositório Git
- [ ] NÃO versionar data real, senhas ou PII nos outputs
- [ ] NÃO criar AuditFinding automaticamente (sempre revisar manual)
- [ ] NÃO usar IA externa ou OCR para análise de conteúdo
- [ ] NÃO integrar com Atlas ou outras ferramentas sem validação

Violação destes itens invalida o contrato de segurança e compromete a 
conformidade com o Provimento CNJ 213/2026 Classe 3.
```

---

## IX. Troubleshooting

### Erro: "Inventory file not found"

```
Causa: Caminho incorreto ou arquivo não existe
Solução:
  1. Verificar se file_inventory.json existe
  2. Usar caminho absoluto completo
  3. Confirmar que scanner foi executado
```

### Erro: "Invalid JSON in inventory"

```
Causa: arquivo corrompido ou malformado
Solução:
  1. Validar JSON: cat arquivo.json | jq .
  2. Comparar com hash do manifest: file_inventory.json.sha256
  3. Reexecutar scanner se necessário
```

### Erro: "Permission denied" na saída

```
Causa: output-dir não tem permissão de escrita
Solução:
  1. Verificar permissões: icacls "C:\Audit_Reports\..."
  2. Usar local externo ao repositório
  3. Confirmar que .gitignore bloqueia diretório
```

### Output muito grande (> 10 MB)

```
Causa: inventory com muitos arquivos (> 100.000)
Solução:
  1. Executar com parâmetros customizados para reduzir volume
  2. Filtrar por tipo de arquivo ou pasta no scanner
  3. Executar em múltiplas rodadas (por pasta)
```

---

## X. Próximas Execuções — Ciclo Operacional

Após validar a primeira execução, estabeleça um ciclo:

| Frequência | Triggerização | Caso de Uso |
|---|---|---|
| **Inicial** | Manual | Linha de base + familiarização |
| **Semanal** | Manual | Monitoramento de acervo novo |
| **Mensal** | Automática | Validação contínua + conformidade |
| **Trimestral** | Manual + review | Consolidação de aprendizados |

---

## XI. Conformidade CNJ 213/2026 — Classe 3

Este workflow apoia os requisitos:

| Requisito CNJ | Como atendido |
|---|---|
| **Inventário de arquivos** | file_inventory.json do scanner |
| **Rastreabilidade de acesso** | diagnosis_manifest.json com SHA-256 |
| **Read-only operacional** | Confirmado em manifest |
| **Evidências de conformidade** | Relatórios (MD, CSV, JSON) |
| **Dossiê técnico** | Outputs armazenados organizados por data |

---

## XII. Suporte e Documentação

| Tópico | Referência |
|---|---|
| Scanner (Sprint 1) | `docs/modules/audit_file_scanner.md` |
| Decisão arquitetural | `docs/decisions.md` (D-23) |
| Roadmap módulo auditoria | `docs/AUDIT_MODULE_ROADMAP.md` |
| Política read-only | `docs/AUDIT_READ_ONLY_POLICY.md` |
| Deployment e operação | `docs/AUDIT_DEPLOYMENT_AND_OPERATION.md` |

---

**Versão:** 1.0.0  
**Último update:** 2026-05-04 (Sprint 3.5 — Hardening operacional)  
**Status:** Pronto para execução real controlada
