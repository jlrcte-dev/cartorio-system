# Auditoria — Implantação e Operação

> **Documento operacional e arquitetural.** Define como executar o módulo de
> auditoria no ambiente real da serventia, como organizar artefatos, como
> transformar relatórios em evidências e como preparar a Sprint 3 com segurança.

Última atualização: 2026-05-04

---

## 1. Objetivo operacional

O módulo de auditoria (`app/modules/audit/`) é usado, neste estágio, como
**coletor read-only de diagnóstico** — não como agente permanente, não como
serviço automático e não como sistema de monitoramento contínuo.

A missão atual é simples e precisa:

- varrer estruturas de pastas e gerar inventário de metadados;
- transformar esses artefatos em evidências rastreáveis;
- alimentar manualmente o `AuditFinding` com achados identificados na revisão;
- construir progressivamente o dossiê técnico da vistoria CNJ 213/2026.

Tudo começa com uma execução manual, monitorada pelo gestor, em ambiente
controlado. A automação e os agentes são backlog futuro — **não Sprint 3**.

---

## 2. Arquitetura operacional atual

### Componentes implementados

```
Cartório System — Módulo de Auditoria
├── scanner/          [Sprint 1 ✅]  varredura read-only, CLI
│   └── cli.py                      entry point: python -m app.modules.audit.scanner.cli
└── findings/         [Sprint 2 ✅]  CRUD de AuditFinding, endpoints REST
    └── router.py                   /api/v1/audit/findings
```

### Componentes planejados (Sprint 3+)

```
└── diagnosis/        [Sprint 3 🟡]  análise semântica do inventory.json
│   └── document_diagnosis.py       entrada: artefatos do scanner, não o servidor
└── evidence/         [futuro ⏳]    vínculo entre artefatos e AuditFinding
└── dossier/          [futuro ⏳]    consolidação para dossiê técnico
└── checklists/       [futuro ⏳]    checklists estruturados por área
```

### Fluxo de dados atual

```
Servidor/Acervo
    │
    │  (caminho de leitura via UNC ou local)
    ▼
scanner/cli.py
    │  (os.walk, sem open, sem escrita no servidor)
    ▼
exports/audit/<run-name>/
    ├── file_inventory.json     ← dados estruturados
    ├── file_inventory.csv      ← análise em planilha
    ├── scan_summary.md         ← relatório legível
    └── scan_manifest.json      ← rastreabilidade + SHA-256
    │
    │  (revisão humana)
    ▼
AuditFinding (banco local do Cartório System)
    │
    ▼
Dossiê técnico (futuro)
```

### Separação clara de ambientes

| Ambiente | Papel | O sistema escreve aqui? |
|----------|-------|------------------------|
| Servidor do cartório | Fonte de dados | **Nunca** |
| Cartório System (notebook/servidor) | Executor do scanner | Apenas em `exports/audit/` |
| `exports/audit/` | Diretório de saída | Sim — somente aqui |
| Banco `cartorio.db` | AuditFinding, Finance | Sim — CRUD de achados |

**Regra absoluta:** o scanner nunca escreve, move, renomeia ou exclui nada
no caminho raiz analisado.

---

## 3. Modos de execução

### Modo A — Execução direta no servidor (Python local)

**Quando usar:** análise de discos locais, pastas de backup, logs, pastas
que não são compartilhadas na rede e não acessíveis remotamente.

| Aspecto | Detalhe |
|---------|---------|
| **Vantagens** | Acesso total a discos locais; sem latência de rede; lê logs e caminhos não compartilhados |
| **Riscos** | Requer Python instalado no servidor; exige cuidado para não rodar como admin por padrão; erro no script pode afetar o processo no servidor |
| **Limitações** | O servidor de produção pode ter restrições de instalação de software |
| **Pré-requisitos** | Python 3.12 instalado no servidor; venv do Cartório System copiado ou instalado localmente; output_dir em disco diferente do analisado |

**Procedimento:**
1. Copiar o projeto Cartório System para o servidor (ex.: `C:\CartorioSystem\`).
2. Criar venv e instalar dependências: `pip install -e .`
3. Executar o scanner com `--root` apontando para o disco local.
4. Copiar os artefatos para `D:\Audit_Evidence\` ou drive externo ao final.

---

### Modo B — Execução no notebook via caminho de rede (UNC)

**Quando usar:** análise de pastas compartilhadas na rede local (acervo digital,
documentos, pastas compartilhadas), sem necessidade de instalar nada no servidor.

| Aspecto | Detalhe |
|---------|---------|
| **Vantagens** | Não instala nada no servidor; o notebook é o executor; ambiente de desenvolvimento já configurado |
| **Riscos** | Latência de rede aumenta o tempo de varredura; interrupção de rede aborta o scan; UNC paths precisam de autenticação prévia |
| **Limitações** | Não acessa discos locais do servidor não compartilhados; não lê logs do sistema fora do compartilhamento |
| **Pré-requisitos** | Pasta compartilhada acessível via `\\servidor\share`; usuário com permissão de leitura mapeado; `--follow-symlinks false` (padrão) |

**Procedimento:**
1. Mapear o compartilhamento via File Explorer ou `net use`.
2. Validar acesso: `dir \\servidor\share` no PowerShell.
3. Executar o scanner com `--root "\\servidor\share\Acervo"`.
4. Salvar artefatos localmente em `exports\audit\<run-name>\`.

---

### Modo C — Executável standalone (futuro, não implementar agora)

**Quando usar:** quando o gestor precisar executar o scanner sem Python instalado,
ou quando o servidor não tiver acesso à internet para pip.

| Aspecto | Detalhe |
|---------|---------|
| **Vantagens** | Zero dependência no servidor; executável assinado; portável via pendrive |
| **Riscos** | Requer build e assinatura digital; manutenção de versões; antivírus pode bloquear executável não assinado |
| **Limitações** | Não está implementado; requer PyInstaller/Nuitka; assinatura digital tem custo |
| **Pré-requisitos** | Sprints 1-10 validadas; definição de processo de build e release |

> **Decisão atual:** não implementar. Manter como backlog para Fase 11+.

---

### Modo D — Agente/serviço local (futuro, não implementar agora)

**Quando usar:** quando o sistema precisar de monitoramento contínuo,
comparação automática entre scans e alertas periódicos.

| Aspecto | Detalhe |
|---------|---------|
| **Vantagens** | Execução sem intervenção; histórico de evolução; alertas automáticos |
| **Riscos** | Serviço em background consome recursos; falha silenciosa é mais perigosa que falha interativa; requer autenticação implementada |
| **Limitações** | Não está implementado; requer autenticação multiusuário como pré-requisito |
| **Pré-requisitos** | Autenticação JWT implementada; aprovação explícita do gestor; Fases 1-10 validadas |

> **Decisão atual:** não implementar. Manter como backlog para Fase 11.

---

## 4. Recomendação de uso atual

### Para as primeiras análises (recomendado agora)

**Usar Modo B — notebook via caminho de rede.**

```
Notebook (Cartório System instalado)
    │
    │  \\servidor\Acervo  (UNC read-only)
    ▼
scanner/cli.py
    │
    ▼
exports\audit\scan-acervo-2026-05-04\
```

Razão: o ambiente de desenvolvimento já está pronto no notebook, nenhuma
instalação no servidor de produção é necessária, e as pastas compartilhadas
são exatamente o que precisa ser inventariado primeiro.

### Para análise de discos locais, logs e backups

**Usar Modo A — execução local no servidor.**

Fazer isso apenas após:
- validar o scanner com pelo menos uma execução bem-sucedida via notebook;
- ter um output_dir definido fora dos discos analisados;
- estar presente fisicamente no servidor ou com acesso remoto monitorado.

### O que não fazer agora

- Não criar agente ou serviço automático.
- Não agendar execução via Agendador de Tarefas do Windows.
- Não executar com conta de administrador de domínio sem necessidade.
- Não salvar artefatos dentro do acervo analisado.

---

## 5. Estrutura de diretórios recomendada

### No servidor de produção

```
C:\CartorioSystem\           ← projeto (código, banco, exports)
    exports\
        audit\
            scan-<data>\     ← artefatos de cada execução
                scan_manifest.json
                file_inventory.json
                file_inventory.csv
                scan_summary.md

D:\Audit_Evidence\           ← cópias arquivadas (disco separado, se disponível)
    2026-05-04\
        scan-acervo-inicial\
            [cópia dos artefatos]
```

### No notebook de desenvolvimento

```
C:\Users\<usuário>\Documents\cartorio_system\
    exports\
        audit\
            scan-<data>\
```

### Regra absoluta de output_dir

> **O diretório de saída (`output_dir`) nunca pode ficar dentro do caminho raiz
> analisado (`root`).**

Exemplos de configuração **correta**:

```
root:       \\servidor\Acervo
output_dir: C:\CartorioSystem\exports\audit\scan-2026-05-04   ✅

root:       D:\Dados
output_dir: C:\CartorioSystem\exports\audit\scan-dados        ✅

root:       C:\Acervo
output_dir: C:\CartorioSystem\exports\audit\scan-acervo       ✅
```

Exemplos de configuração **proibida**:

```
root:       C:\Acervo
output_dir: C:\Acervo\scan_resultado                          ❌ dentro do root

root:       \\servidor\Acervo
output_dir: \\servidor\Acervo\audit                           ❌ dentro do root
```

---

## 6. Procedimento operacional de execução

### Passo 0 — Preparar ambiente

```powershell
# Navegar até o projeto
cd C:\Users\<usuario>\Documents\cartorio_system

# Confirmar que o venv está ativo (deve aparecer no prompt)
.venv\Scripts\Activate.ps1

# Confirmar Python e versão do projeto
python --version          # deve ser 3.12.x
python -c "import app; print('OK')"
```

### Passo 1 — Validar versão do scanner

```powershell
python -m app.modules.audit.scanner.cli --help
```

Verificar que o help exibe os parâmetros esperados: `--root`, `--output-dir`,
`--run-name`, `--max-depth`, `--exclude`, `--follow-symlinks`.

### Passo 2 — Executar teste pequeno (obrigatório antes do scan completo)

Sempre executar um teste com uma subpasta pequena antes do scan completo.
Isso valida permissões, encoding de caminho e velocidade estimada.

```powershell
python -m app.modules.audit.scanner.cli `
    --root "\\servidor\Acervo\2024" `
    --output-dir "exports\audit\teste-2024" `
    --run-name "teste-2024" `
    --max-depth 3
```

Verificar: o `scan_manifest.json` foi gerado? `errors_count` é o esperado?
`read_only` está `true`?

### Passo 3 — Executar com max-depth para estimativa

Para pastas grandes, usar `--max-depth 4` primeiro para estimar tamanho e
tempo antes do scan completo.

```powershell
python -m app.modules.audit.scanner.cli `
    --root "\\servidor\Acervo" `
    --output-dir "exports\audit\scan-estimativa-2026-05-04" `
    --run-name "scan-estimativa-2026-05-04" `
    --max-depth 4
```

Avaliar: `total_files`, `total_size_bytes`, `duration_seconds`. Se razoável,
prosseguir com scan completo.

### Passo 4 — Executar scan completo

```powershell
python -m app.modules.audit.scanner.cli `
    --root "\\servidor\Acervo" `
    --output-dir "exports\audit\scan-acervo-2026-05-04" `
    --run-name "scan-acervo-2026-05-04" `
    --exclude "\\servidor\Acervo\Sistema" `
    --exclude "\\servidor\Acervo\Temp"
```

### Passo 5 — Conferir manifest

```powershell
# Exibir manifest para verificação
Get-Content "exports\audit\scan-acervo-2026-05-04\scan_manifest.json" | ConvertFrom-Json | Format-List
```

Verificar: `read_only: true`, `errors_count`, `total_files`, hash SHA-256 presente.

### Passo 6 — Revisar relatório

Abrir `scan_summary.md` em qualquer editor Markdown ou diretamente no VS Code.
Identificar achados preliminares para registrar no `AuditFinding`.

### Passo 7 — Arquivar artefatos

```powershell
# Copiar para pasta de evidências (se houver disco separado)
Copy-Item -Recurse `
    "exports\audit\scan-acervo-2026-05-04" `
    "D:\Audit_Evidence\2026-05-04\scan-acervo-2026-05-04"
```

Registrar no log manual: data, executor, caminho analisado, hash do manifest,
número de achados identificados.

---

## 7. Comandos de referência

### Pasta pequena (teste com dados locais da serventia)

> **Dados locais da serventia ficam em `_local_data/serventia_docs/`**, nunca em
> `docs/`. O diretório `_local_data/` está no `.gitignore` e nunca é commitado.
> Para outputs, use `C:\Audit_Reports\<data>\` ou `_local_data\audit_outputs\`.

```powershell
python -m app.modules.audit.scanner.cli `
    --root "C:\Users\João\Documents\cartorio_system\_local_data\serventia_docs" `
    --output-dir "C:\Audit_Reports\2026-05-04\scan-serventia-teste" `
    --run-name "scan-serventia-teste"
```

### Scan com max-depth (estimativa rápida)

```powershell
python -m app.modules.audit.scanner.cli `
    --root "D:\Dados" `
    --output-dir "exports\audit\scan-dados-raso" `
    --run-name "scan-dados-raso" `
    --max-depth 4
```

### Scan completo de disco local

```powershell
python -m app.modules.audit.scanner.cli `
    --root "D:\Dados" `
    --output-dir "exports\audit\scan-dados-completo-2026-05-04" `
    --run-name "scan-dados-completo-2026-05-04" `
    --exclude "D:\Dados\Temp" `
    --exclude "D:\Dados\Sistema"
```

### Scan via caminho de rede (UNC)

```powershell
# Validar acesso antes
Test-Path "\\servidor\Acervo"

# Executar scan
python -m app.modules.audit.scanner.cli `
    --root "\\servidor\Acervo" `
    --output-dir "exports\audit\scan-acervo-rede-2026-05-04" `
    --run-name "scan-acervo-rede-2026-05-04"
```

### Scan local no servidor (executar diretamente no servidor)

```powershell
# No servidor, com o projeto instalado em C:\CartorioSystem\
cd C:\CartorioSystem
.venv\Scripts\Activate.ps1
python -m app.modules.audit.scanner.cli `
    --root "C:\Acervo" `
    --output-dir "D:\Audit_Evidence\scan-acervo-local-2026-05-04" `
    --run-name "scan-acervo-local-2026-05-04"
```

### Verificar hash do manifest manualmente

```powershell
# Verificar integridade do inventory
$manifest = Get-Content "exports\audit\<run-name>\scan_manifest.json" | ConvertFrom-Json
$hash = (Get-FileHash "exports\audit\<run-name>\file_inventory.json" -Algorithm SHA256).Hash
if ($hash -eq $manifest.sha256_inventory) { "Hash OK" } else { "DIVERGÊNCIA!" }
```

---

## 8. Checklist pré-execução

Preencher antes de cada execução de scan em ambiente real.

```
[ ] Caminho raiz analisado confirmado: ____________________________
[ ] output_dir definido e fora do caminho raiz: ____________________
[ ] output_dir tem espaço livre suficiente (≥ 1 GB livre recomendado)
[ ] Usuário atual tem permissão de LEITURA no caminho raiz
[ ] Usuário atual NÃO tem permissão de escrita no caminho raiz (ideal)
[ ] Caminhos de exclusão definidos e corretos: _____________________
[ ] follow_symlinks está desabilitado (padrão — confirmar se não alterado)
[ ] Horário adequado: fora de pico operacional se scan for grande
[ ] Nenhum processo de backup ou replicação ativo no caminho analisado
[ ] Teste pequeno com subpasta limitada planejado antes do scan completo
[ ] Comando completo registrado neste checklist: ____________________
    _________________________________________________________________
[ ] Executor identificado: _________________________________________
[ ] Data/hora de início registrada: ________________________________
```

---

## 9. Checklist pós-execução

Preencher logo após a conclusão do scan.

```
[ ] scan_manifest.json gerado e acessível
[ ] read_only: true confirmado no manifest
[ ] errors_count revisado — erros esperados? ____ erros encontrados
[ ] excluded_count correto — caminhos excluídos conforme planejado
[ ] total_size_bytes razoável para o caminho analisado
[ ] Hash SHA-256 do inventory verificado (ver seção 7)
[ ] scan_summary.md aberto e revisado
[ ] Achados preliminares identificados: ___________________________
[ ] Artefatos arquivados em: ______________________________________
[ ] AuditFindings registrados no sistema: _________________________
[ ] Data/hora de término registrada: ______________________________
[ ] Anomalias ou observações: _____________________________________
```

---

## 10. Fluxo de evidências

O fluxo completo, do servidor ao dossiê técnico:

```
1. SCANNER
   python -m app.modules.audit.scanner.cli --root <caminho>
   └─ gera: file_inventory.json, file_inventory.csv, scan_summary.md, scan_manifest.json

2. ARTEFATOS
   exports/audit/<run-name>/
   └─ cada artefato tem hash SHA-256 registrado no manifest

3. MANIFEST + HASH
   scan_manifest.json
   └─ rastreabilidade: quem executou, quando, parâmetros, SHA-256 do inventory
   └─ evidência de integridade: o inventory não foi alterado após o scan

4. DIAGNÓSTICO (Sprint 3 — DocumentDiagnosis)
   entrada: file_inventory.json (artefato, não o servidor diretamente)
   └─ gera: diagnosis_report.md, listas de candidatos por categoria

5. CANDIDATOS
   arquivos com nomes genéricos, extensões suspeitas, datas antigas, etc.
   └─ lista de candidatos a achados, para revisão humana

6. REVISÃO HUMANA
   gestor/auditor revisa os candidatos identificados pelo diagnóstico
   └─ decide: é um achado? qual severidade? qual recomendação?

7. AUDITFINDING
   POST /api/v1/audit/findings
   └─ origin: SCANNER, evidence_summary: referência ao artefato e run_name
   └─ achado registrado com rastreabilidade para o scan que o originou

8. RESOLUÇÃO
   PATCH /api/v1/audit/findings/{id}/status
   └─ transições: OPEN → IN_PROGRESS → RESOLVED/ACCEPTED/CLOSED
   └─ nunca deletado — histórico preservado

9. DOSSIÊ TÉCNICO (Fase 10)
   consolidação de todos os artefatos + findings + evidências
   └─ dossier_index.json com hashes de cada documento
   └─ dossier_report.md para o vistoriador
```

### Vinculação entre artefatos e AuditFinding

Ao registrar um achado originado de um scan, preencher:

- `origin`: `SCANNER`
- `evidence_summary`: incluir o `run_name` e o arquivo de referência.
  Exemplo: `"Identificado no scan 'scan-acervo-2026-05-04'. Ver
  file_inventory.json: 234 arquivos com extensão .tmp soltos na raiz."`
- `recommendation`: ação sugerida para o responsável.

---

## 11. Política de segurança operacional

### O que o scanner pode fazer

- Ler nomes de arquivos, tamanhos, datas de criação e modificação.
- Registrar erros de permissão (ACCESS DENIED) sem interromper o scan.
- Escrever artefatos em `exports/audit/` (fora do caminho analisado).
- Gerar hashes SHA-256 dos artefatos gerados (não dos arquivos analisados).

### O que o scanner nunca faz

- Abrir o conteúdo de nenhum arquivo (`open(file)` proibido no scanner).
- Mover, renomear, copiar ou excluir qualquer arquivo do servidor.
- Escrever dentro do caminho analisado.
- Ler senhas, credenciais ou dados pessoais de clientes.
- Expor caminhos absolutos do servidor em logs ou relatórios exportados.

### Regras operacionais para o executor

| Regra | Justificativa |
|-------|---------------|
| Nunca rodar como administrador sem necessidade | Mínimo privilégio; erro com admin tem blast radius maior |
| Nunca salvar relatório dentro do acervo analisado | Evita contaminar o inventário com artefatos do próprio scan |
| Nunca rodar scan completo sem teste pequeno antes | Valida permissões, encoding, tempo estimado |
| Nunca rodar em horário de pico sem avaliação prévia | Scan em pasta grande consome I/O; pode afetar acesso dos usuários |
| Nunca compartilhar relatórios com dados de caminhos absolutos | Caminhos do servidor são internos; relatórios podem circular externamente |
| Nunca executar scripts adicionais sem revisão | Scripts destrutivos (`rm`, `del`, `Move-Item`) nunca na mesma sessão |
| Nunca assumir que erros de permissão são problema | ACCESS DENIED em pastas sensíveis é comportamento correto e esperado |

### Dados sensíveis — o que nunca entra nos relatórios

- Conteúdo de documentos (contratos, certidões, procurações).
- Dados pessoais de clientes (nomes, CPF, RG, endereços).
- Credenciais, senhas, tokens.
- Caminhos absolutos completos do servidor (aparecem apenas de forma relativa).

---

## 12. Decisão arquitetural para Sprint 3

### DA-23 — DocumentDiagnosis analisa artefatos, não o servidor diretamente

**Contexto:** A Sprint 3 implementará o `DocumentDiagnosis`, que analisa os
metadados coletados pelo scanner para identificar padrões problemáticos: nomes
genéricos, arquivos antigos, extensões suspeitas, prováveis duplicatas.

**Decisão:** O `DocumentDiagnosis` recebe como entrada o `file_inventory.json`
gerado pelo scanner — nunca um caminho de disco ou servidor diretamente.

**Arquitetura:**

```
# Correto
diagnosis = DocumentDiagnosis.from_inventory("exports/audit/scan-2026-05-04/file_inventory.json")
report = diagnosis.run()

# Proibido
diagnosis = DocumentDiagnosis.from_path("\\\\servidor\\Acervo")  # acessa servidor diretamente
```

**Por quê:**

1. **Separação de responsabilidades:** o scanner acessa o servidor; o diagnóstico
   analisa dados já coletados. São fases distintas e independentes.
2. **Rastreabilidade:** o inventory tem hash registrado no manifest. O diagnóstico
   de um inventory específico é reproduzível e auditável.
3. **Segurança:** o diagnóstico nunca precisa de permissão de acesso ao servidor.
   Pode rodar offline, em ambiente isolado, com o inventory copiado.
4. **Testabilidade:** testes do diagnóstico usam inventories sintéticos em memória,
   sem depender de caminhos de disco reais.
5. **Reversibilidade:** se o diagnóstico identificar falsos positivos, o inventory
   original permanece intacto e o diagnóstico pode ser reexecutado.

**Implicação para Sprint 3:** o módulo `diagnosis/` recebe o caminho para o
`file_inventory.json` como parâmetro, valida o hash via `scan_manifest.json`, e
opera exclusivamente sobre os dados já coletados.

---

## 13. Backlog futuro — o que não implementar agora

Os itens abaixo são planejados mas **não fazem parte da Sprint 3**. Registrados
aqui para que a Sprint 3 não os antecipe.

| Item | Fase | Por que esperar |
|------|------|-----------------|
| Build de executável standalone | Fase 11+ | Requer Fases 1-10 validadas; custo de manutenção |
| Assinatura digital do executável | Fase 11+ | Custo financeiro; pré-requisito: executável pronto |
| Agendamento automático de scans | Fase 11 | Requer autenticação multiusuário implementada |
| Agente/serviço em background | Fase 11 | Requer autenticação; risco de falha silenciosa |
| Dashboard de evolução de riscos | Fase 11 | Requer histórico de múltiplas execuções validadas |
| Alertas automáticos por e-mail | Fase 11 | Requer agente e autenticação |
| Exportação automática de dossiê | Fase 10 | Requer Fases 1-9 completas |
| Integração com Atlas | Fase 11+ | Independência é princípio do projeto |
| Comparação automática entre scans | Fase 11 | Requer histórico de scans; útil só depois de múltiplos scans |

---

## 14. Relação com outros documentos

| Documento | Conteúdo |
|-----------|----------|
| [`module_roadmap.md`](module_roadmap.md) | Roadmap das 12 fases com critérios de aceite |
| [`read_only_policy.md`](read_only_policy.md) | Política formal de operação read-only |
| [`../modules/audit.md`](../modules/audit.md) | Visão geral do módulo, princípios, estrutura de código |
| [`../modules/audit_file_scanner.md`](../modules/audit_file_scanner.md) | Documentação técnica do scanner (CLI, saídas, exemplos) |
| [`../modules/audit_findings.md`](../modules/audit_findings.md) | Documentação técnica dos AuditFindings (endpoints, campos) |
| [`../regulatory/cnj_213/alignment.md`](../regulatory/cnj_213/alignment.md) | Como o módulo apoia a adequação ao Provimento |
| [`../decisions/technical_decisions.md`](../decisions/technical_decisions.md) | Registro de decisões técnicas (ver D-23) |
| [`../roadmap.md`](../roadmap.md) | Roadmap geral do projeto com estado atual das sprints |
