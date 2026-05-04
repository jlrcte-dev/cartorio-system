# Sprint 2.5 — Procedimento Operacional de Auditoria Read-Only

> **Mini-sprint documental.** Documenta como executar o módulo de auditoria
> em ambiente real, com base na sequência testada e validada em
> `G:\Meu Drive\Cartórios` (2026-05-04).

Última atualização: 2026-05-04

---

## 1. Objetivo operacional

O módulo de auditoria é usado neste estágio como **coletor read-only de
diagnóstico**, não como agente permanente. A execução é manual, monitorada e
segue uma sequência progressiva de três passos:

```
depth2 → depth4 → full
  │          │       │
  │          │       └─ inventário completo para diagnóstico e dossiê
  │          └─────── análise intermediária para verificar tamanho e tempo
  └────────────────── mapeamento inicial da estrutura de pastas (rápido)
```

Cada execução gera artefatos rastreáveis com hash SHA-256 e `read_only: true`
no manifest — prontos para servir como evidência no dossiê técnico CNJ 213/2026.

---

## 2. Modos de execução

### Modo A — Notebook com Google Drive (validado ✅)

**Quando usar:** acervo sincronizado com o Google Drive mapeado localmente como
letra de unidade (`G:\`) ou pasta do Drive for Desktop.

| Aspecto | Detalhe |
|---------|---------|
| **Vantagens** | Ambiente já configurado; sem acesso direto ao servidor de produção; validado em 2026-05-04 |
| **Riscos** | Latência de sync pode exibir arquivos desatualizados; Drive for Desktop pode omitir arquivos não sincronizados localmente |
| **Limitações** | Apenas arquivos disponíveis offline são varridos; arquivos "online only" têm tamanho 0 ou erro |
| **Pré-requisitos** | Google Drive for Desktop mapeado; arquivos relevantes com disponibilidade offline ativada |

```powershell
python -m app.modules.audit.scanner.cli `
    --root "G:\Meu Drive\Cartórios" `
    --output-dir "exports\audit\scan-cartorios-full" `
    --run-name "scan-cartorios-full"
```

---

### Modo B — Notebook via caminho de rede (UNC)

**Quando usar:** pastas compartilhadas na rede local do cartório acessíveis via
`\\servidor\share`, sem instalar nada no servidor de produção.

| Aspecto | Detalhe |
|---------|---------|
| **Vantagens** | Nada instalado no servidor; ambiente de dev já pronto no notebook |
| **Riscos** | Interrupção de rede aborta o scan; UNC path exige autenticação prévia |
| **Limitações** | Não acessa discos locais do servidor não compartilhados; não lê logs do sistema |
| **Pré-requisitos** | `Test-Path "\\servidor\share"` retorna `True`; usuário com leitura mapeado |

```powershell
Test-Path "\\servidor\Acervo"   # validar antes

python -m app.modules.audit.scanner.cli `
    --root "\\servidor\Acervo" `
    --output-dir "exports\audit\scan-acervo-rede-2026-05-04" `
    --run-name "scan-acervo-rede-2026-05-04"
```

---

### Modo C — Servidor local (Python instalado no servidor)

**Quando usar:** discos locais, logs do sistema, pastas de backup, volumes não
compartilhados em rede. Requer execução direta na máquina servidora.

| Aspecto | Detalhe |
|---------|---------|
| **Vantagens** | Acesso a discos não compartilhados, logs e caminhos locais |
| **Riscos** | Requer Python instalado no servidor; erro com perfil admin tem maior blast radius |
| **Limitações** | Não é o modo padrão para o início — usar apenas após validação via notebook |
| **Pré-requisitos** | Python 3.12 + venv do projeto instalados; output_dir em disco separado do analisado |

```powershell
# No servidor, com projeto instalado em C:\CartorioSystem\
cd C:\CartorioSystem
.venv\Scripts\Activate.ps1
python -m app.modules.audit.scanner.cli `
    --root "D:\Dados" `
    --output-dir "C:\Audit_Reports\2026-05-04\scan-dados-local" `
    --run-name "scan-dados-local-2026-05-04"
```

---

### Modo D — Executável standalone (futuro, não implementar)

**Quando usar:** quando o servidor não tiver Python instalado e o gestor precisar
executar sem dependências.

Não está implementado. Requer Fases 1–10 validadas, PyInstaller/Nuitka e
assinatura digital. Manter como backlog Fase 11+.

---

### Modo E — Agente/serviço local (futuro, não implementar)

**Quando usar:** quando o sistema exigir monitoramento contínuo e comparação
automática entre execuções.

Não está implementado. Requer autenticação multiusuário implementada como
pré-requisito. Manter como backlog Fase 11.

---

## 3. Procedimento recomendado: depth2 → depth4 → full

A sequência de três passos progressivos é a abordagem validada. Ela evita
surpresas em pastas grandes, valida permissões precocemente e permite estimar
tempo e tamanho antes da varredura completa.

### Passo 1 — Mapeamento inicial com depth2

**Objetivo:** entender a estrutura de pastas de primeiro e segundo nível.
Rápido (< 1 s para a maioria dos acervos). Identifica se há pastas inesperadas
ou acessos negados antes de investir tempo no scan completo.

```powershell
python -m app.modules.audit.scanner.cli `
    --root "<caminho>" `
    --output-dir "C:\Audit_Reports\<AAAA-MM-DD>\scan-<nome>-depth2" `
    --run-name "scan-<nome>-depth2" `
    --max-depth 2
```

**O que verificar no manifest:**
- `errors_count` — algum ACCESS DENIED esperado? Se não, suspeito.
- `total_directories` — quantas pastas principais existem?
- `total_size_bytes` — ordem de grandeza correta para o acervo?

**Resultado real (scan-cartorios-depth2, 2026-05-04):**

| Métrica | Valor |
|---------|-------|
| `total_files` | 52 |
| `total_directories` | 27 |
| `total_size_bytes` | 41.069.970 (≈ 39 MB) |
| `duration_seconds` | 0,189 s |
| `errors_count` | 0 |
| `run_id` | `1a40ba52-38e7-4821-9631-757bfb6717a3` |

Observações: 27 pastas visíveis na raiz e no primeiro nível. Tamanho total de
39 MB no depth2 — indicou que a maioria dos arquivos estava em subpastas mais
profundas (confirmado nos passos seguintes).

---

### Passo 2 — Análise intermediária com depth4

**Objetivo:** aprofundar até 4 níveis para capturar a maior parte dos arquivos
sem varrer a profundidade máxima. Identifica extensões, maiores arquivos e
riscos já nesta fase.

```powershell
python -m app.modules.audit.scanner.cli `
    --root "<caminho>" `
    --output-dir "C:\Audit_Reports\<AAAA-MM-DD>\scan-<nome>-depth4" `
    --run-name "scan-<nome>-depth4" `
    --max-depth 4 `
    --exclude "$RECYCLE.BIN" `
    --exclude "System Volume Information"
```

**O que verificar no scan_summary.md:**
- Top 10 maiores arquivos — há vídeos, dumps ou arquivos inesperados?
- Distribuição por extensão — o perfil de extensões é o esperado para um acervo?
- Extensões suspeitas — `.exe`, `.bat`, `.ps1` em pastas de documentos?
- Arquivos antigos — arquivos sem modificação há mais de 2 anos?

**Resultado real (scan-cartorios-depth4, 2026-05-04):**

| Métrica | Valor |
|---------|-------|
| `total_files` | 524 |
| `total_directories` | 92 |
| `total_size_bytes` | 4.548.611.304 (≈ 4,24 GB) |
| `duration_seconds` | 1,893 s |
| `errors_count` | 0 |
| `excluded_count` | 8 |
| `run_id` | `380dfce5-07c8-46f0-bebc-4f7146daff4c` |

Observações: o salto de 39 MB (depth2) para 4,24 GB (depth4) confirmou que
o acervo é profundo. 524 arquivos já capturados. Tempo de 1,9 s indicou que
o full scan seria viável sem impacto de I/O significativo.

---

### Passo 3 — Inventário completo (full)

**Objetivo:** varredura sem limite de profundidade para inventário completo.
Gera o `file_inventory.json` que será a entrada do `DocumentDiagnosis` na
Sprint 3.

```powershell
python -m app.modules.audit.scanner.cli `
    --root "<caminho>" `
    --output-dir "C:\Audit_Reports\<AAAA-MM-DD>\scan-<nome>-full" `
    --run-name "scan-<nome>-full" `
    --exclude "$RECYCLE.BIN" `
    --exclude "System Volume Information" `
    --exclude "__pycache__"
```

**O que verificar ao final:**
- `read_only: true` confirmado no manifest.
- Hash SHA-256 dos artefatos presente e íntegro.
- `errors_count` — ACCESS DENIED em pastas sensíveis é esperado e correto.
- `scan_summary.md` — revisar achados antes de registrar no AuditFinding.

**Resultado real (scan-cartorios-full, 2026-05-04):**

| Métrica | Valor |
|---------|-------|
| `total_files` | 1.830 |
| `total_directories` | 154 |
| `total_size_bytes` | 4.858.739.068 (≈ 4,53 GB) |
| `duration_seconds` | 5,35 s |
| `errors_count` | 0 |
| `excluded_count` | 17 |
| `run_id` | `21ce7025-28a3-43ba-a6ad-0a4085af2c09` |

**Distribuição por extensão (scan-cartorios-full):**

| Extensão | Quantidade | Observação |
|----------|-----------|------------|
| `.pdf` | 1.359 | Principal formato documental |
| `.odt` | 200 | Documentos de texto (LibreOffice) |
| `.ods` | 184 | Planilhas (LibreOffice) — acervo financeiro |
| `.xlsx` | 21 | Planilhas Excel |
| `.docx` | 12 | Documentos Word |
| `.mp4` / vídeos | poucos | ~2,7 GB em LGPD/Treinamentos |

---

## 4. Estrutura recomendada de saída

### Organização dos artefatos

```
C:\Audit_Reports\
├── 2026-05-04\
│   ├── scan-cartorios-depth2\
│   │   ├── file_inventory.json
│   │   ├── file_inventory.csv
│   │   ├── scan_summary.md
│   │   └── scan_manifest.json
│   ├── scan-cartorios-depth4\
│   │   └── [mesmos 4 artefatos]
│   └── scan-cartorios-full\
│       └── [mesmos 4 artefatos]
├── 2026-06-01\
│   └── [próxima campanha]
└── catalog.csv              ← índice de todas as campanhas
```

### Regra obrigatória

> **O diretório de saída (`--output-dir`) nunca pode estar dentro do caminho
> raiz analisado (`--root`).**

| Configuração | Status |
|-------------|--------|
| `--root "G:\Meu Drive\Cartórios"` + `--output-dir "C:\Audit_Reports\..."` | ✅ correto |
| `--root "D:\Dados"` + `--output-dir "D:\Dados\audit_resultado"` | ❌ proibido |
| `--root "\\servidor\Acervo"` + `--output-dir "\\servidor\Acervo\scan"` | ❌ proibido |

### Nomenclatura de campanha

Padrão recomendado: `scan-<escopo>-<profundidade>` com `--run-name` idêntico ao
nome da pasta, para rastreabilidade direta entre pasta e manifest.

```
scan-cartorios-depth2
scan-cartorios-depth4
scan-cartorios-full
scan-servidor-dados-full
scan-servidor-backup-depth4
```

---

## 5. Checklist pré-execução

Preencher antes de cada campanha de scan em ambiente real.

```
IDENTIFICAÇÃO
[ ] Data: ____________________  Executor: ____________________
[ ] Caminho raiz analisado: __________________________________
[ ] Nome da campanha (run-name): _____________________________
[ ] output-dir definido fora do caminho raiz: ________________

AMBIENTE
[ ] venv ativo — python --version retorna 3.12.x
[ ] python -m app.modules.audit.scanner.cli --help executa sem erro
[ ] Espaço livre em output-dir: _____ GB disponíveis
[ ] Caminho raiz acessível: Test-Path "<root>" retorna True

SEGURANÇA
[ ] Usuário atual tem permissão de LEITURA no caminho raiz
[ ] Usuário atual NÃO tem escrita no caminho raiz (ideal — verificar)
[ ] follow_symlinks não foi alterado manualmente (default=false)
[ ] Nenhum script destrutivo (del, rm, Move-Item) na sessão

PLANEJAMENTO
[ ] Sequência planejada: [ ] depth2  [ ] depth4  [ ] full
[ ] Exclusões definidas: _____________________________________
[ ] Horário: [ ] fora de pico  [ ] usuários informados se necessário
[ ] Passo depth2 será feito ANTES do depth4 e do full

REGISTRO
[ ] Comando depth2 registrado aqui:
    _________________________________________________________
[ ] Comando depth4 registrado aqui:
    _________________________________________________________
[ ] Comando full registrado aqui:
    _________________________________________________________
```

---

## 6. Checklist pós-execução

Preencher após a conclusão de cada etapa e ao final da campanha.

```
DEPTH2
[ ] scan_manifest.json gerado
[ ] read_only: true confirmado
[ ] errors_count: _____  (esperado: _____  — ACCESS DENIED previsíveis?)
[ ] total_directories: _____  (estrutura de pastas compreensível?)
[ ] Observações: ____________________________________________

DEPTH4
[ ] scan_manifest.json gerado
[ ] read_only: true confirmado
[ ] errors_count: _____
[ ] Extensões inesperadas no scan_summary.md? [ ] Sim  [ ] Não
[ ] Arquivos > 100 MB identificados? [ ] Sim  [ ] Não
[ ] Executáveis em pastas de documentos? [ ] Sim  [ ] Não
[ ] Observações: ____________________________________________

FULL
[ ] scan_manifest.json gerado
[ ] read_only: true confirmado
[ ] errors_count: _____  excluded_count: _____
[ ] SHA-256 verificado manualmente? [ ] Sim  [ ] Não
[ ] scan_summary.md revisado pelo executor
[ ] Achados preliminares identificados: ______________________
[ ] ________________________________________________________

ARQUIVAMENTO
[ ] Artefatos copiados para C:\Audit_Reports\<AAAA-MM-DD>\
[ ] catalog.csv atualizado com os 3 run_ids desta campanha
[ ] AuditFindings registrados no sistema: ___ criados
[ ] Observações finais: _____________________________________
```

---

## 7. Como arquivar evidências

### Estrutura de arquivamento permanente

Os artefatos gerados em `exports\audit\` são artefatos de trabalho. Para fins
de dossiê técnico e evidência formal, copiar para `C:\Audit_Reports\`:

```powershell
# Copiar campanha completa após validação
$data = "2026-05-04"
New-Item -ItemType Directory -Path "C:\Audit_Reports\$data" -Force

Copy-Item -Recurse `
    "exports\audit\scan-cartorios-depth2" `
    "C:\Audit_Reports\$data\scan-cartorios-depth2"

Copy-Item -Recurse `
    "exports\audit\scan-cartorios-depth4" `
    "C:\Audit_Reports\$data\scan-cartorios-depth4"

Copy-Item -Recurse `
    "exports\audit\scan-cartorios-full" `
    "C:\Audit_Reports\$data\scan-cartorios-full"
```

### Verificar integridade após cópia

```powershell
# Verificar que o hash do inventory foi preservado
$manifest = Get-Content `
    "C:\Audit_Reports\2026-05-04\scan-cartorios-full\scan_manifest.json" `
    | ConvertFrom-Json

$hash = (Get-FileHash `
    "C:\Audit_Reports\2026-05-04\scan-cartorios-full\file_inventory.json" `
    -Algorithm SHA256).Hash

if ($hash -eq $manifest.output_files.file_inventory_json.sha256) {
    Write-Host "Hash OK — cópia íntegra"
} else {
    Write-Host "DIVERGÊNCIA DE HASH — investigar antes de arquivar"
}
```

### Índice de campanhas (catalog.csv)

Manter `C:\Audit_Reports\catalog.csv` com uma linha por execução:

```csv
run_id,run_name,max_depth,executed_at,total_files,total_size_bytes,errors_count,sha256_inventory
1a40ba52-...,scan-cartorios-depth2,2,2026-05-04T...,52,41069970,0,<hash>
380dfce5-...,scan-cartorios-depth4,4,2026-05-04T...,524,4548611304,0,<hash>
21ce7025-...,scan-cartorios-full,,2026-05-04T...,1830,4858739068,0,<hash>
```

### O que NÃO arquivar

- Conteúdo de documentos do acervo (jamais copiar para o sistema).
- Caminhos absolutos completos do servidor expostos em texto livre.
- Dados pessoais de clientes identificados na análise.

---

## 8. Como registrar AuditFindings a partir dos relatórios

### Fluxo de conversão: candidato → achado formal

```
scan_summary.md
    │
    │  executor lê e identifica padrões relevantes
    ▼
Lista de candidatos
    │
    │  revisão humana: é um achado real? qual severidade?
    ▼
POST /api/v1/audit/findings
    │
    │  vinculado via scanner_run_id
    ▼
AuditFinding status=OPEN
```

### Campos obrigatórios ao criar um achado a partir de scan

```json
{
  "title": "<título curto e específico>",
  "description": "<o que foi observado, com base nos metadados>",
  "category": "<categoria adequada>",
  "origin": "SCANNER",
  "severity": "<CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL>",
  "probability": "<HIGH|MEDIUM|LOW>",
  "impact": "<CRITICAL|HIGH|MEDIUM|LOW>",
  "priority": "<IMMEDIATE|SEVEN_DAYS|THIRTY_DAYS|NINETY_DAYS|BACKLOG>",
  "evidence_summary": "Identificado no scan '<run_name>' (run_id: <uuid>). <detalhe>.",
  "recommended_action": "<ação concreta para o responsável>",
  "scanner_run_id": "<uuid do scan que originou — do scan_manifest.json>",
  "evidence_artifact_path": "exports/audit/<run-name>/file_inventory.json",
  "evidence_hash": "<sha256 do file_inventory.json — do scan_manifest.json>"
}
```

### Onde encontrar o scanner_run_id e o hash

Ambos estão no `scan_manifest.json` de cada execução:

```json
{
  "run": { "run_id": "21ce7025-28a3-43ba-a6ad-0a4085af2c09", ... },
  "output_files": {
    "file_inventory_json": {
      "sha256": "<hash para evidence_hash>"
    }
  }
}
```

### Regra: só registrar o que metadados confirmam

O scanner nunca abre arquivos. Os achados do scan são sempre baseados em:
nome, extensão, tamanho, data de modificação, caminho relativo. Nunca afirmar
algo sobre o conteúdo de um arquivo — apenas sobre seus metadados.

**Certo:**
> "Arquivo `Login Onvio.pdf` identificado em pasta compartilhada. Nome sugere
> possíveis credenciais armazenadas. Conteúdo não lido. Requer investigação."

**Errado:**
> ~~"Arquivo contém senha do Onvio."~~ (nunca — conteúdo não foi lido)

---

## 9. Achados candidatos observados no teste real

Estas são as observações identificadas na varredura `scan-cartorios-full`
(run_id: `21ce7025-28a3-43ba-a6ad-0a4085af2c09`) de `G:\Meu Drive\Cartórios`.

> **Todos são candidatos baseados em metadados.** Nenhum conteúdo foi lido.
> A classificação final exige revisão humana antes de registrar como AuditFinding.

---

### AC-001 — Possíveis arquivos de credenciais por nome

**Padrão detectado:** arquivos cujo nome contém palavras como `Login`, `Dados`,
`dados` associadas a sistemas críticos.

**Arquivos identificados (por nome):**
- `Login Onvio.pdf` (ou similar)
- `Login Engegraph.pdf`
- `Dados Onvio.pdf`
- `dados_sefaz.*`
- `dados ecac.*`
- `dados conta onmicrosoft.*`
- `Dados conta Caixa.*`

**Por que é candidato a achado:**
Arquivos com nomes sugestivos de credenciais em pastas compartilhadas ou
sincronizadas com o Google Drive representam risco de exposição. O conteúdo não
foi lido — pode ser manual de acesso ou planilha de login. Qualquer dos dois exige
controle mais restrito do que uma pasta de documentos gerais.

**AuditFinding sugerido:**

| Campo | Valor sugerido |
|-------|---------------|
| `category` | `ACCESS_CONTROL` |
| `severity` | `CRITICAL` |
| `probability` | `HIGH` |
| `impact` | `CRITICAL` |
| `priority` | `IMMEDIATE` |
| `cnj_requirement` | `E-04: gestão de credenciais; A-05: controle de acesso` |
| `recommended_action` | Identificar e revisar cada arquivo. Se contém credenciais: mover para cofre de senhas (ex.: Bitwarden), revogar e rotacionar credenciais expostas, remover do Drive compartilhado. |

---

### AC-002 — Vídeos de treinamento consumindo ~2,7 GB em LGPD/Treinamentos

**Padrão detectado:** arquivos `.mp4` (e possivelmente outros formatos de vídeo)
concentrados na pasta `LGPD/Treinamentos` (ou similar), com tamanho total
aproximado de 2,7 GB.

**Por que é candidato a achado:**
O acervo total é de 4,53 GB. Vídeos de treinamento representando ~60% do tamanho
total em uma pasta de documentos é um risco de gestão de espaço e não tem relação
com o fluxo documental cartorial. Se essa pasta estiver sincronizada com o Google
Drive, o espaço da conta também é consumido desnecessariamente.

**AuditFinding sugerido:**

| Campo | Valor sugerido |
|-------|---------------|
| `category` | `DOCUMENT_MANAGEMENT` |
| `severity` | `MEDIUM` |
| `probability` | `HIGH` |
| `impact` | `MEDIUM` |
| `priority` | `THIRTY_DAYS` |
| `recommended_action` | Avaliar necessidade de manter vídeos no acervo compartilhado. Se são materiais de treinamento, mover para repositório dedicado (YouTube, Google Classroom, pasta pessoal) e remover do acervo principal. |

---

### AC-003 — Pasta Temp com documentos cartorários reais

**Padrão detectado:** pasta com nome `Temp` (ou `temp`, `Temporários`,
`Rascunhos`) contendo arquivos com extensões documentais reais (`.pdf`, `.odt`,
`.docx`).

**Por que é candidato a achado:**
Pastas com nome `Temp` tendem a ser tratadas como descartáveis — são alvos
frequentes de limpeza manual ou automática. Documentos cartorários reais em uma
pasta `Temp` correm risco de exclusão não intencional. Além disso, indicam que
o fluxo de trabalho não tem destino definido para esses documentos — risco de
organização documental.

**AuditFinding sugerido:**

| Campo | Valor sugerido |
|-------|---------------|
| `category` | `DOCUMENT_MANAGEMENT` |
| `severity` | `HIGH` |
| `probability` | `HIGH` |
| `impact` | `HIGH` |
| `priority` | `SEVEN_DAYS` |
| `recommended_action` | Revisar conteúdo da pasta Temp e reclassificar cada documento para seu local correto. Nunca usar pasta Temp para documentos de serviço. Criar procedimento de destino para documentos em elaboração. |

---

### AC-004 — Documentos pessoais/nominais em pastas compartilhadas

**Padrão detectado:** arquivos com nomes sugestivos de dados pessoais de clientes
(orçamentos, contratos, recibos, modelos com possíveis nomes de pessoa no título)
em pastas sem controle de acesso verificado.

**Por que é candidato a achado:**
LGPD: dados pessoais de clientes em pastas sem controle de acesso configuram risco
regulatório. O scanner identificou pela estrutura de pastas e nomes — conteúdo não
foi lido. A confirmação exige revisão humana.

**AuditFinding sugerido:**

| Campo | Valor sugerido |
|-------|---------------|
| `category` | `COMPLIANCE` |
| `severity` | `HIGH` |
| `probability` | `MEDIUM` |
| `impact` | `HIGH` |
| `priority` | `THIRTY_DAYS` |
| `cnj_requirement` | `L-01: dados pessoais; L-02: base legal para tratamento` |
| `recommended_action` | Mapear quais pastas contêm documentos com dados pessoais. Verificar permissões NTFS dessas pastas. Avaliar se o acesso está restrito ao necessário. Documentar base legal para o tratamento. |

---

### AC-005 — POPs, políticas e SGCN sem vigência confirmada

**Padrão detectado:** pastas com nome `Procedimentos Operacionais Padrão`,
`Políticas`, `SGCN` contendo documentos cujas datas de modificação indicam
que não foram atualizados há mais de 1 ano (detalhamento exige análise depth).

**Por que é candidato a achado:**
Documentos de política e procedimento exigem vigência formal — data de aprovação,
responsável e data da próxima revisão. Documentos sem revisão confirmada desde
2019-2024 podem estar desalinhados com o Provimento CNJ 213/2026 e com a
operação atual da serventia.

**AuditFinding sugerido:**

| Campo | Valor sugerido |
|-------|---------------|
| `category` | `POLICY_DOCUMENT` |
| `severity` | `MEDIUM` |
| `probability` | `HIGH` |
| `impact` | `MEDIUM` |
| `priority` | `THIRTY_DAYS` |
| `cnj_requirement` | `G-08: capacitação e procedimentos documentados` |
| `recommended_action` | Inventariar todos os documentos de política e procedimento. Para cada um: verificar data de aprovação, responsável e alinhamento com operação atual. Criar calendário de revisão periódica. |

---

### AC-006 — Concentração financeira mensal sem escopo de backup confirmado

**Padrão detectado:** grande concentração de documentos financeiros organizados
por ano/mês (comprovantes, ISS, SEFAZ, boletos, recibos, fundos, taxas) — 184
arquivos `.ods` e 21 `.xlsx`, mais 1.359 PDFs que incluem comprovantes.

**Por que é candidato a achado:**
O histórico financeiro é um ativo crítico da serventia. A inclusão dessas pastas
no escopo de backup do Cobian Gravity não foi confirmada formalmente. Além disso,
a concentração de documentos financeiros no Google Drive levanta a questão de
qual é a cópia primária e qual é a cópia de segurança.

**AuditFinding sugerido:**

| Campo | Valor sugerido |
|-------|---------------|
| `category` | `BACKUP` |
| `severity` | `HIGH` |
| `probability` | `MEDIUM` |
| `impact` | `HIGH` |
| `priority` | `SEVEN_DAYS` |
| `cnj_requirement` | `B-03: backup completo; B-05: backup off-site` |
| `recommended_action` | Confirmar se as pastas financeiras estão incluídas no escopo do Cobian Gravity. Verificar RPO aplicado. Definir qual é a cópia primária (servidor local vs. Google Drive). Incluir no PRD como ativo crítico. |

---

### Resumo dos achados candidatos

| ID | Categoria | Título resumido | Severidade | Prioridade sugerida |
|----|-----------|-----------------|------------|---------------------|
| AC-001 | ACCESS_CONTROL | Possíveis credenciais por nome (7 arquivos) | CRITICAL | IMMEDIATE |
| AC-002 | DOCUMENT_MANAGEMENT | Vídeos ~2,7 GB em LGPD/Treinamentos | MEDIUM | THIRTY_DAYS |
| AC-003 | DOCUMENT_MANAGEMENT | Pasta Temp com documentos cartorários reais | HIGH | SEVEN_DAYS |
| AC-004 | COMPLIANCE | Docs pessoais/nominais sem controle confirmado | HIGH | THIRTY_DAYS |
| AC-005 | POLICY_DOCUMENT | POPs, políticas, SGCN sem vigência confirmada | MEDIUM | THIRTY_DAYS |
| AC-006 | BACKUP | Histórico financeiro sem escopo de backup confirmado | HIGH | SEVEN_DAYS |

---

## 10. Limitações da abordagem por metadados

O scanner coleta apenas metadados — nunca o conteúdo dos arquivos. Isso é uma
decisão de segurança intencional, mas implica limitações que o executor e o gestor
devem conhecer.

| Limitação | Consequência prática |
|-----------|---------------------|
| Não lê conteúdo de arquivos | Não confirma se um arquivo de "Login" realmente contém credenciais |
| Não detecta duplicatas por hash | Dois arquivos com mesmo nome e tamanho podem ter conteúdos diferentes |
| Não analisa versões de documentos | Um POP pode ter sido "atualizado" apenas com mudança de cabeçalho |
| Não verifica assinatura digital | Um PDF pode estar ou não assinado — metadados não dizem |
| Não acessa dados NTFS de permissão | Quem pode ler/escrever cada pasta requer Fase 5 (auditoria de segurança local) |
| Não lê logs do sistema | Acessos a arquivos, quem abriu, quando — requer Fase 5 |
| Não verifica integridade de backup | Confirmar que o arquivo de backup é restaurável requer teste manual |
| Drive for Desktop pode omitir arquivos | Arquivos "online only" não sincronizados aparecem com erro ou tamanho 0 |
| Arquivos com mesmo nome em pastas diferentes | Prováveis duplicatas por nome+tamanho — não garantido por conteúdo |

**Regra:** todo achado baseado em metadados é um **candidato** que requer revisão
humana antes de ser registrado como AuditFinding confirmado.

---

## 11. Regras calibradas para Sprint 3

Com base nos resultados reais do teste em `G:\Meu Drive\Cartórios`, as seguintes
regras de detecção foram calibradas para o `DocumentDiagnosis` da Sprint 3.

### Regra S3-01 — Possíveis credenciais por nome

**Padrão:** arquivo cujo nome contém qualquer das palavras (case-insensitive):
`login`, `senha`, `password`, `credencial`, `credenciais`, `acesso`, `dados `
(seguido de sistema conhecido).

**Limiar:** qualquer ocorrência é candidata — sem threshold mínimo.

**Contexto real:** 7 arquivos identificados no teste (Login Onvio, Login Engegraph,
Dados Onvio, dados_sefaz, dados ecac, dados conta onmicrosoft, Dados conta Caixa).

**Severidade default sugerida:** CRITICAL.

---

### Regra S3-02 — Arquivos grandes fora de contexto

**Padrão:** arquivo com `size_bytes > 50_000_000` (50 MB) em pasta sem contexto
de arquivos grandes esperados (ex.: pasta de vídeos/mídia explicitamente nomeada).

**Ajuste calibrado:** threshold de 50 MB (não 100 MB) para capturar documentos
PDF com muitas imagens embutidas além dos vídeos.

**Contexto real:** vídeos `.mp4` ~2,7 GB total em LGPD/Treinamentos.

---

### Regra S3-03 — Vídeos em pastas de documentos

**Padrão:** arquivo com extensão `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv` em pasta
que não seja explicitamente de mídia/treinamento.

**Ajuste calibrado:** sempre reportar como candidato independente de tamanho —
vídeos não pertencem ao acervo documental cartorial.

---

### Regra S3-04 — Pastas Temp com arquivos de documento

**Padrão:** pasta cujo nome (case-insensitive) contém `temp`, `tmp`,
`temporário`, `temporarios`, `rascunho`, `rascunhos`, `lixo` com arquivos de
extensão documental (`.pdf`, `.odt`, `.docx`, `.ods`, `.xlsx`).

**Limiar:** qualquer arquivo documental em pasta com nome de temporário é candidato.

**Severidade default sugerida:** HIGH.

---

### Regra S3-05 — Nomes genéricos

**Padrão:** arquivo cujo nome (sem extensão, case-insensitive) contém qualquer de:
`novo`, `nova`, `cópia`, `copia`, `final`, `final2`, `revisado`, `revisada`,
`versão`, `versao`, `draft`, `rascunho`, `temp`, `teste`, `antigo`, `antiga`,
`backup`, `bkp`, `bak`.

**Limiar sugerido:** reportar individualmente; agrupar por pasta no relatório.

---

### Regra S3-06 — Documentos pessoais/nominais

**Padrão:** arquivo cujo nome contém padrões sugestivos de dados pessoais:
- Sequência de 11 dígitos consecutivos (possível CPF sem pontuação)
- Sequência de 14 dígitos (possível CNPJ)
- Padrões como `_CPF_`, `_RG_`, `-cpf`, `-rg` no nome

**Nota:** o scanner não lê conteúdo — este padrão é de nome, não de conteúdo.
Falsos positivos são esperados (ex.: números em contratos). Requer revisão humana.

---

### Regra S3-07 — POPs e políticas com data de modificação antiga

**Padrão:** arquivo em pasta cujo caminho contém `procedimento`, `POP`, `politica`,
`política`, `manual`, `SGCN`, `PCN`, `PSI`, `PRD` com `modified_at` anterior a
`now() - 730 dias` (2 anos).

**Limiar:**
- `> 2 anos` sem modificação: candidato MEDIUM
- `> 4 anos` sem modificação: candidato HIGH

**Contexto real:** documentos com mtime de 2019/2020 identificados no teste.

---

### Regra S3-08 — Concentração financeira mensal

**Padrão:** pastas com estrutura `<ano>/<mês>` ou `<ano-mês>` em caminho que
contém `financ`, `emolumento`, `ISS`, `SEFAZ`, `boleto`, `recibo`, `fundo`.

**Objetivo:** identificar o volume do acervo financeiro histórico e sua extensão
temporal (anos cobertos) para priorização de backup e importação futura.

**Nota:** não é um achado de risco em si — é um inventário para tomada de decisão.

---

### Regra S3-09 — Extensões incomuns em pastas de documentos

**Padrão:** arquivo com extensão não esperada em pasta documental:
- `.exe`, `.bat`, `.ps1`, `.cmd`, `.vbs`, `.js` → risco SECURITY/HIGH
- `.tmp`, `.bak`, `.old`, `.~` → risco DOCUMENT/LOW-MEDIUM
- `.lnk` → atalho do Windows em pasta de documentos (verificar destino)
- Extensão dupla (`.pdf.pdf`, `.odt.odt`) → possível malware ou erro

**Severidade default:** `.exe` e similares = HIGH; `.tmp`/`.bak` = LOW.

---

## 12. Decisão arquitetural D-23 — DocumentDiagnosis v1

### Decisão

O `DocumentDiagnosis` (Sprint 3) analisa exclusivamente artefatos gerados pelo
scanner. Nunca acessa o servidor, disco ou Google Drive diretamente.

### Assinatura de entrada

```python
# Correto — entrada é o artefato do scanner
diagnosis = DocumentDiagnosis.from_inventory(
    inventory_path="exports/audit/scan-cartorios-full/file_inventory.json",
    manifest_path="exports/audit/scan-cartorios-full/scan_manifest.json"
)
report = diagnosis.run()

# Proibido — nunca acessa o servidor diretamente
diagnosis = DocumentDiagnosis.from_path("G:\\Meu Drive\\Cartórios")   # ❌
```

### Validação de integridade

Antes de processar, o `DocumentDiagnosis` deve:
1. Ler o `scan_manifest.json` do mesmo diretório.
2. Calcular o SHA-256 do `file_inventory.json`.
3. Comparar com o hash registrado no manifest.
4. Abortar com erro claro se houver divergência.

```python
# Fluxo de validação
manifest = load_manifest("scan_manifest.json")
actual_hash = sha256_file("file_inventory.json")
assert actual_hash == manifest.output_files.file_inventory_json.sha256, \
    f"Integrity check failed: inventory may have been tampered"
```

### Por que essa decisão é importante

| Benefício | Detalhe |
|-----------|---------|
| **Separação de fases** | Scanner acessa servidor; diagnóstico analisa dados coletados — nunca misturar |
| **Rastreabilidade** | O diagnóstico de um inventory específico é reproduzível e auditável por hash |
| **Segurança** | Diagnóstico não precisa de credencial ou acesso de rede |
| **Testabilidade** | Testes usam inventories sintéticos em memória — sem disco real |
| **Portabilidade** | O inventory pode ser copiado para outro ambiente e analisado offline |

Ver [`docs/decisions.md`](decisions.md) — D-23 para registro formal.

---

## 13. Próximo passo recomendado

Com a Sprint 2.5 concluída e o procedimento documentado, o próximo passo é:

**1. Registrar os 6 achados candidatos (AC-001 a AC-006) como AuditFindings formais.**

Cada achado já tem os campos mapeados na seção 9. Usar o `scanner_run_id` do
scan-cartorios-full (`21ce7025-28a3-43ba-a6ad-0a4085af2c09`).

**2. Executar o scanner no servidor de produção (Modos B ou C).**

Repetir a sequência depth2 → depth4 → full no servidor real antes de iniciar
a Sprint 3. O `file_inventory.json` resultante será a entrada do `DocumentDiagnosis`.

**3. Iniciar Sprint 3 — DocumentDiagnosis.**

Com inventory real do servidor em mãos, implementar o módulo `diagnosis/`
seguindo a decisão D-23: entrada é o artefato, não o servidor.

---

## 14. Relação com outros documentos

| Documento | Conteúdo |
|-----------|----------|
| [`AUDIT_DEPLOYMENT_AND_OPERATION.md`](AUDIT_DEPLOYMENT_AND_OPERATION.md) | Guia geral de deployment e operação (elaborado antes da Sprint 2.5) |
| [`modules/audit_file_scanner.md`](modules/audit_file_scanner.md) | Documentação técnica do scanner; inclui execuções reais validadas |
| [`modules/audit_findings.md`](modules/audit_findings.md) | Campos, endpoints e exemplos de AuditFinding |
| [`AUDIT_MODULE_ROADMAP.md`](AUDIT_MODULE_ROADMAP.md) | Roadmap das fases; Sprint 2.5 registrada como Fase 1c |
| [`decisions.md`](decisions.md) | D-23: DocumentDiagnosis analisa artefatos, não servidor |
