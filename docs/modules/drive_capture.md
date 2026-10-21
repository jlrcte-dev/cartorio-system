# Coletor somente leitura do Drive do cartório (`drive_capture`)

**Estado (2026-10-21):** implementado e testado com Drive sintético; **acesso real
validado em smoke local** (20/10/2026) sobre uma única fonte piloto, com `check` e duas
coletas íntegras e a origem inalterada. ADR-011 segue *Proposta* — o smoke não a aceita.
Não há monitoramento diário, análise de fluxos nem integração com o Atlas.

Decisão de acesso e alternativas: [ADR-011](../decisions/ADR-011-drive-readonly-capture.md).
Consumidor local da planilha piloto: [retrato de serviços](services_snapshot.md).

---

## 1. O que faz e o que não faz

| Faz | Não faz |
|---|---|
| Lê só IDs explícitos e filhos diretos de pastas autorizadas | Varrer o Drive, seguir atalhos, entrar em subpastas |
| Exporta Google Planilhas → XLSX e Documentos → DOCX | Interpretar células, OCR, LLM, comentários, histórico |
| Baixa arquivo armazenado só se o tipo for aceito na config | Converter formato não suportado |
| Guarda captura atual + anterior com manifesto de procedência | Acumular versões ou coletar histórico retroativo |
| Gera relatório sanitizado de cobertura e sinais técnicos | Concluir que um serviço avançou, parou ou tem erro |
| Roda quando o operador manda | Agendar, publicar HTTP, enviar à VPS ou ao Atlas |

Nenhuma chamada escreve no Drive: o transporte só emite `GET` em `about`, `files`,
`files/{id}` e `files/{id}/export` (verificado por teste).

---

## 2. Configuração — roteiro do operador

Os passos 1–4 e 6 são do operador, na conta Google do cartório. O coletor nunca cria
credencial nem muda permissões no Drive. **Não cole a chave, a config real nem IDs reais
em chat.** Se uma política impedir um passo, **pare e reporte** — não troque de conta nem
amplie acesso para contornar.

1. **Projeto do cartório.** Em `console.cloud.google.com`, crie (ou use) um projeto
   **do cartório** — não o do Atlas nem o do Derivativos.
2. **Ative a API.** *APIs e serviços → Biblioteca → Google Drive API → Ativar.*
3. **Crie a service account.** *IAM e administrador → Contas de serviço → Criar*
   (ex.: `leitor-drive`). **Não conceda papéis** no projeto e não dê acesso a
   usuários. Delegação em todo o domínio: **não**.
4. **Gere a chave JSON.** Na conta de serviço → *Chaves → Adicionar chave → JSON*.
   Bloqueio por `iam.disableServiceAccountKeyCreation` → pare e reporte.
5. **Proteja os caminhos privados antes de colocar segredo ou dado real neles**
   (PowerShell, a partir da raiz do repositório; sem recursão, só estes dois
   diretórios):

   ```powershell
   $sid = ([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value
   foreach ($d in "$env:USERPROFILE\.cartorio_drive", ".\_local_data\drive_capture") {
       New-Item -ItemType Directory -Force $d | Out-Null
       # usuário atual (por SID) + SYSTEM + Administradores — preserva administração e recuperação
       icacls $d /inheritance:r /grant:r "*${sid}:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F"
   }
   ```

   Mova o JSON baixado para `.cartorio_drive\` (ex. `service-account.json`). **Mover no
   mesmo volume preserva a ACL de origem** (ex.: a de Downloads), então redefina a do
   arquivo para herdar a da pasta:
   `icacls "$env:USERPROFILE\.cartorio_drive\service-account.json" /reset`.

   **Confira** as duas pastas e a chave. `/inheritance:r` remove a herança, mas não
   remove ACEs explícitas de outros principais que já existissem:

   ```powershell
   function Test-AclPiloto([string]$p) {
       $sid = ([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value
       $ok = @($sid, 'S-1-5-18', 'S-1-5-32-544')
       $acl = Get-Acl -LiteralPath $p
       $acl.Access | ForEach-Object {
           $s = $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
           '{0,-8} {1,-12} herdada={2}' -f $(if ($ok -contains $s) {'OK'} else {'REVISAR'}), $_.FileSystemRights, $_.IsInherited
       }
       'heranca_bloqueada={0}' -f $acl.AreAccessRulesProtected
   }
   Test-AclPiloto "$env:USERPROFILE\.cartorio_drive"
   Test-AclPiloto "$env:USERPROFILE\.cartorio_drive\service-account.json"
   Test-AclPiloto ".\_local_data\drive_capture"
   ```

   Esperado: só linhas `OK`; `heranca_bloqueada=True` nas pastas e `False` na chave,
   que herda da pasta. Qualquer `REVISAR` → remova a ACE com
   `icacls <caminho> /remove:g *<SID>` só nesse caminho e confira de novo. A saída não
   mostra SIDs nem nomes e pode ser compartilhada. ACL conferida **não** prova
   criptografia de disco (BitLocker), que é verificação à parte.
6. **Compartilhe só a planilha piloto, como Leitor.** No Drive, abra o arquivo →
   *Compartilhar* → e-mail da service account (`...@...iam.gserviceaccount.com`) →
   **Leitor** → desmarque *Notificar*.
   - **Drive compartilhado (Shared Drive):** compartilhe **o arquivo** como Leitor.
     **Não** adicione a service account como membro do Shared Drive: ser membro dá
     acesso ao drive inteiro, muito além da fonte escolhida. Se a política do Shared
     Drive impedir compartilhar arquivos com quem não é membro, **registre o
     impedimento e pare**. Para arquivo em Shared Drive, preencha também
     `shared_drive_id`: ele só faz o coletor enviar `supportsAllDrives=true` nas
     leituras — não concede nem restringe acesso.
   - **Alcance efetivo.** A identidade enxerga o que foi compartilhado com ela
     diretamente **e** o que herda (pasta-pai compartilhada com ela, participação em
     Shared Drive) ou alcança por link aberto (*qualquer pessoa com o link*). A
     fronteira do **programa** é a allowlist da config somada a essas permissões
     efetivas — por isso a service account não deve receber acesso a mais nada.
   - Se o dono desativou *"Leitores podem baixar, imprimir e copiar"*, a fonte aparece
     como `download_restricted` — não contorne.
   - Arquivos diários (fora do piloto) exigirão compartilhar uma pasta; essa decisão
     será revista junto com a retenção total (ver § 5).
7. **Extra instalado** no venv do Cartório System. Confira com
   `python -m pip show google-auth`; só se faltar, `pip install -e ".[drive]"`.
8. **Config local do piloto.** Copie
   [`drive_capture.config.example.yaml`](drive_capture.config.example.yaml) para
   `_local_data/drive_capture/config.yaml` (já protegido no passo 5) e deixe **uma**
   fonte:
   - `credentials_file`: caminho da chave do passo 5;
   - `expected_identity`: e-mail da service account;
   - `files`: um item com `alias` neutro (ex. `servicos_andamento_piloto`, nunca nome de
     cliente, colaborador ou título), `family` correspondente (ex.
     `documentos_em_andamento`) e `file_id` — o trecho entre `/d/` e `/edit` na URL;
   - `folders: []` e `limits: {max_sources: 1}`;
   - `shared_drive_id` só se o arquivo estiver num Shared Drive (passo 6).

Revogar o acesso: remova o compartilhamento da service account no arquivo, ou
desative/exclua a chave no console. Sem isso, a chave continua válida.

---

## 3. Uso

A partir da raiz do repositório, com o venv ativo:

```bash
python -m app.modules.drive_capture.cli check     # identidade, escopo, fronteira; sem download
python -m app.modules.drive_capture.cli collect   # 1ª captura
python -m app.modules.drive_capture.cli collect   # 2ª captura — conferir os sinais observados
```

Opções: `--config <caminho>` (padrão `_local_data/drive_capture/config.yaml`);
`--report-json <caminho>` em `collect` (padrão
`exports/atlas/cartorio_drive_capture_report.json`). O JSON e o `reports/latest.md` são
sobrescritos a cada coleta: para guardar a evidência de cada run, use um `--report-json`
distinto por coleta e copie o `latest.md` logo em seguida.

**Segunda coleta — como ler os sinais.** A primeira captura não tem base anterior
(sinais `null`). Na segunda, registre os valores efetivamente observados de
`version_changed`, `modified_time_changed` e `content_hash_changed`. São metadados
técnicos: `version` e `modifiedTime` do Drive podem mudar sem alteração visível, e o
hash de um XLSX/DOCX **exportado** não é digest semântico — a exportação pode variar
byte a byte sem mudança de célula. Variação isolada de hash não prova mudança de negócio
nem reprova a coleta; o que reprova é resultado diferente de `captured` ou código de
falha.

Códigos de saída: `0` completa · `1` parcial · `2` falhou / configuração ou credencial
inválida. Se os acentos aparecerem trocados no Git Bash, use `PYTHONUTF8=1`.

**O que pode ser compartilhado para revisão** (sanitizado): a saída do terminal, o JSON
do relatório e `reports/latest.md`. **Nunca** o conteúdo de `sources/`, o
`registry.json` ou os `state.json`/`manifest.json`, que contêm IDs reais.

---

## 4. Diretório privado (`data_dir`)

```text
registry.json                    ID do Drive → chave local estável
run.lock                         exclusão mútua (removê-lo à mão só se nenhuma coleta estiver rodando)
reports/latest.md                relatório sanitizado da última coleta
sources/<chave>/state.json       PONTO DE COMMIT da fonte
sources/<chave>/gen-<...>/       geração imutável: content.<xlsx|docx|...> + manifest.json
sources/<chave>/staging-<...>/   em montagem — nunca consumir
```

`<chave>` é o `alias` da fonte explícita ou `<alias_da_pasta>-NNNN` para arquivo
diário. **Consumidor futuro:** ler `state.json` → `current.generation` e abrir só essa
geração. Diretórios `gen-*` não referenciados são lixo de uma falha e são removidos na
próxima publicação daquela fonte.

`state.json` separa: `last_attempt` (quando, resultado, código), `last_success_at`,
`current`/`previous` (geração, bytes, sha256, `drive_modified_time`, `drive_version`,
método) e `eligibility` (`eligible` ou `suspended`). Falha nunca altera
`last_success_at` nem `current`.

`manifest.json` registra: ID e MIME de origem, MIME exportado, método, `modifiedTime`,
`version`, `size`/`md5Checksum` quando o Drive informa, instante da captura, bytes e
SHA-256.

**Proteção local — obrigatória antes de conteúdo real.** O `.gitignore` não protege
acesso. No Windows, o `data_dir` e a pasta da chave recebem a ACL do passo 5 do § 2,
**conferida** com `Test-AclPiloto`; arquivos criados pelo coletor herdam essa ACL. ACL
não substitui criptografia de disco (BitLocker), verificada à parte. Em Linux/macOS o
coletor cria diretórios `0700` e arquivos `0600`.

---

## 5. Fronteira — regras

- **Arquivo fixo:** só o ID explícito. Fica autorizado onde quer que esteja.
- **Pasta de diários:** só filhos diretos, com tipo em `include.mime_types` e,
  opcionalmente, `include.name_pattern` (curinga, sem distinção de maiúsculas). Nome
  parecido não é autorização: a regra é a pasta mais o tipo/padrão.
- **Pasta mista:** prefira IDs explícitos até existir recorte seguro.
- **Atalhos** nunca são seguidos; **subpastas** exigem entrada própria; `recursive` é
  recusado.
- **Deduplicação** pelo ID do Drive: renomear não cria fonte nova; arquivo presente
  como ID explícito e numa pasta é capturado uma vez.
- **Saída do recorte:** se uma listagem **completa** da pasta não traz mais um filho
  conhecido, ele é marcado `out_of_boundary` e suspenso. O arquivo ausente **não** é
  consultado (seria ler fora do recorte), então movido, removido ou sem acesso não se
  distinguem. Mover entre duas pastas autorizadas não suspende.
- **Teto:** sob limite de páginas ou de fontes, a seleção é por `modifiedTime` do
  Drive (nunca por título), e a cobertura é declarada `partial`.
- **Retenção total:** duas gerações **por fonte** não limitam, sozinhas, o volume
  acumulado quando uma pasta de diários gera fontes novas todo dia. Habilitar pastas
  exige rever essa retenção antes.

---

## 6. Relatório — contrato `cartorio_system.drive_capture.report` v1.0

Campos de topo: `contract`, `contract_version`, `generated_at`, `notice`, `run`
(`run_id`, `mode`, `started_at`, `finished_at`, `status`
`complete|partial|failed`, `identity_verified`, `global_code`), `totals`, `families`,
`folders`, `sources`.

- `families[]`: uma entrada por família (`gerenciamento_financeiro`, `protestos`,
  `documentos_em_andamento`, `relatorios_colaboradores`) com `status`
  `not_configured | empty_listing | complete | partial | failed`.
- `folders[]`: listagem `complete|partial|failed`, código e contagens (vistos,
  elegíveis, subpastas, atalhos, outro tipo, fora do padrão, já cobertos, saíram).
- `sources[]`: `alias`, `family`, `origin` (`file|folder`), `folder_alias`, `result`
  (`captured|failed|skipped`), `code`, `attempt_at`, `last_success_at`,
  `drive_modified_time`, `drive_version`, `bytes`, `method`, `consistency_retry`,
  `signals` (`version_changed`, `modified_time_changed`, `content_hash_changed`; `null`
  na primeira captura).

Exclui: IDs/URLs do Drive, títulos, nomes de pessoas, conteúdo, valores, hashes de
conteúdo, caminhos locais e mensagens remotas. Todas as datas estão em UTC.

**Leitura correta dos sinais.** São técnicos. `version` do Drive muda até sem alteração
visível; o hash de uma exportação não é digest de células; a última modificação não
prova o período coberto; ausência de atualização não prova ausência de trabalho;
`not_found`/`permission_denied` significam *indisponível para esta identidade*, não
exclusão. O relatório de colaboradores é fonte complementar.

---

## 7. Códigos de falha

| Código | Significado |
|---|---|
| `config_invalid`, `credentials_missing`, `credentials_invalid`, `dependency_missing` | Configuração local — corrigir antes de qualquer acesso |
| `identity_mismatch` | Credencial ou Drive indicam identidade diferente de `expected_identity`; nada é lido |
| `run_locked` | Outra coleta em andamento |
| `auth_failed` | Credencial recusada ou revogada |
| `not_found`, `permission_denied` | Fonte indisponível para a identidade (não implica exclusão) |
| `download_restricted`, `export_size_limit` | Bloqueio do dono ou limite de 10 MB da exportação — sem contorno |
| `rate_limited`, `quota_exceeded`, `server_error`, `network_error`, `timeout` | Transitórios; até `max_retries` novas tentativas com espera crescente |
| `unsupported_mime`, `shortcut_not_followed`, `is_folder`, `not_a_folder`, `trashed` | Fonte fora do que o piloto captura |
| `out_of_boundary` | Saiu da pasta autorizada; leituras suspensas |
| `size_limit_exceeded`, `run_budget_exhausted`, `source_cap_reached` | Tetos do perfil piloto; cobertura parcial, nunca truncamento |
| `source_changed_during_capture` | Mudou duas vezes durante a captura; geração anterior preservada |
| `integrity_mismatch`, `unexpected_response`, `store_error`, `unexpected_error` | Captura descartada; geração anterior preservada |

---

## 8. Testes

`tests/test_drive_capture_*.py` usam um Drive sintético em memória
(`tests/drive_capture_support.py`). Cobrem: fronteira (IDs, pastas, atalhos,
subpastas, padrão de nome, arquivo movido), paginação e tetos, arquivo diário novo,
renomeação e deduplicação, consistência antes/depois, promoção atômica, retenção de
duas gerações, preservação em falha, retries limitados, identidade, trava de execução,
sanitização do relatório e da CLI, e ausência de chamadas de escrita. Um teste monta o
transporte real offline e é **pulado** se o extra `[drive]` não estiver instalado (o
CI instala só `.[dev]`). **Teste offline não comprova acesso real.**
