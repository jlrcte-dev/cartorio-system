# ADR-011 — Captura local somente leitura de fontes do Google Drive do cartório

- **Status:** Proposto — implementado localmente e testado offline; aceite depende de
  revisão humana e do smoke real com a fonte piloto
- **Data:** 2026-10-19
- **Sprint:** `CARTORIO-DRIVE-READONLY-1`
- **Módulo:** `app/modules/drive_capture/`
- **Guia e contrato operacional:** [`docs/modules/drive_capture.md`](../modules/drive_capture.md)

---

## Contexto

Os colaboradores mantêm planilhas e relatórios diários no Google Drive do cartório
(gerenciamento financeiro, protestos, documentos/serviços em andamento, relatos da
equipe). A limitação atual não é interpretar essas fontes, e sim lê-las de forma
reproduzível, sem depender de cópia manual nem de amostra anonimizada preparada à mão.

A arquitetura alvo é:

```text
Drive do cartório → coletor local do Cartório System → capturas privadas + relatório
técnico sanitizado → (futuro) consolidado gerencial → (futuro) consumidor no Atlas
```

Restrições que a decisão precisa respeitar: o Cartório System é independente (§ 1 e
§ 12 da configuração do projeto); credenciais são segregadas por sistema; dados reais
não vão a modelo, GitHub, VPS nem ao Atlas; a origem nunca é modificada.

## Decisão

1. **Identidade própria do cartório: service account com chave JSON**, criada num
   projeto Google Cloud do cartório, **sem nenhum papel de IAM** e **sem delegação de
   domínio**, recebendo acesso de **Leitor** só na fonte escolhida — no piloto, um
   único arquivo. O alcance efetivo da identidade é o que lhe foi compartilhado
   diretamente **mais** o que ela herda (pasta-pai compartilhada com ela, participação
   em Shared Drive) ou alcança por link aberto; por isso ela não recebe acesso a mais
   nada. Em Shared Drive o compartilhamento é **do arquivo**, nunca participação como
   membro do drive, que daria acesso ao drive inteiro; se a política impedir
   compartilhar com não membros, o impedimento é registrado e o acesso não é ampliado.
   `shared_drive_id` na config só ativa `supportsAllDrives` nas leituras — não concede
   nem restringe acesso. É o único método de autenticação desta etapa. Não há OAuth de
   usuário, nem token do Atlas, do Derivativos ou de conta pessoal.
2. **Escopo único `https://www.googleapis.com/auth/drive.readonly`**, conferido no
   código. `drive.file` não é somente leitura; `drive.metadata.readonly` não entrega
   conteúdo.
3. **A fronteira é a soma de três travas independentes**: (a) as permissões efetivas
   da identidade, diretas e herdadas; (b) a allowlist da configuração local não versionada — IDs
   explícitos de arquivo e pastas autorizadas cujos filhos **diretos** entram por tipo
   e padrão de nome opcional; (c) o transporte, que só emite `GET` e só aceita os
   caminhos `about`, `files`, `files/{id}` e `files/{id}/export`. Escopo de leitura
   sozinho não restringe a fronteira.
4. **Sem varredura**: não há listagem global filtrada localmente. Listagens usam
   `'<pasta>' in parents and trashed = false`, paginadas e com teto; teto atingido
   gera cobertura parcial, nunca completa. Atalhos não são seguidos. Subpastas exigem
   entrada própria. Recursão é recusada pela configuração.
5. **Aquisição sem interpretação**: Google Planilhas → exportação XLSX (CSV de uma aba
   não representa a planilha); Google Documentos → exportação DOCX; arquivo armazenado
   (XLSX/ODS/CSV/DOCX/PDF) → download dos bytes **somente** se o tipo for aceito
   explicitamente na configuração. Qualquer outro tipo, atalho, pasta ou download
   bloqueado vira estado explícito. Não há parser de domínio, OCR, LLM, comentários,
   histórico de revisões ou automação de navegador.
6. **Consistência por fonte**: metadados lidos antes e depois da aquisição
   (`version`, `modifiedTime`, `md5Checksum`, `size`, MIME). Divergência gera **uma**
   nova tentativa; persistindo, a geração não é promovida. Pertencimento ao recorte é
   revalidado antes de baixar e antes de promover. Não há transação entre fontes.
7. **Publicação atômica e retenção limitada**: cada captura nasce em `staging-*`, vira
   `gen-*` imutável e só passa a valer quando `state.json` da fonte é trocado por
   `os.replace`. São mantidas só a geração atual e a anterior. Falha preserva a última
   geração válida e nunca renova a data do último sucesso.
8. **Identidade local estável**: chave local por ID do Drive (registro privado);
   renomear não cria outra fonte. Caminhos usam só aliases/chaves locais, nunca
   títulos remotos. Títulos nem são solicitados, exceto quando a pasta usa padrão de
   nome — e então ficam só em memória.
9. **Relatório sanitizado com contrato versionado**
   (`cartorio_system.drive_capture.report` v1.0) em
   `exports/atlas/cartorio_drive_capture_report.json`, mais Markdown no diretório
   privado. Contém aliases, famílias, datas, contagens, bytes, versão/`modifiedTime` do
   Drive e códigos controlados. Exclui IDs, URLs, títulos, nomes, conteúdo, valores,
   hashes de conteúdo e caminhos locais. **Nenhum consumidor do Atlas lê esse arquivo
   nesta etapa.**
10. **Execução manual e opt-in**: `python -m app.modules.drive_capture.cli check|collect`.
    Sem scheduler, serviço, envio às 08h/17h, HTTP, VPS ou banco.
11. **Dependência isolada**: `google-auth[requests]` no extra `[drive]` do
    `pyproject.toml`, importado só quando a CLI monta o transporte real. Importar o
    módulo ou rodar a suíte não autentica, não abre rede e não coleta.

## Consequências positivas

- Leitura reproduzível das fontes reais sem tocar na origem e sem identidade pessoal.
- A revogação é simples e do lado do cartório: remover o compartilhamento ou
  desativar/excluir a chave.
- Cobertura honesta: listagem vazia, falha de acesso, teto e alteração durante a
  captura são estados distintos.
- O formato do relatório permite a etapa seguinte (consolidado e Atlas) sem expor
  dados reais.

## Consequências negativas

- **Chave de service account é segredo de longa duração.** Exige guarda fora do
  repositório com ACL restrita e rotação/revogação deliberadas.
- **Políticas da conta podem impedir o método**: organizações Google Workspace
  recentes bloqueiam por padrão a criação de chaves
  (`iam.disableServiceAccountKeyCreation`), e o domínio pode bloquear compartilhamento
  com contas externas. Nesse caso o método falha de forma explícita e a alternativa
  exige nova decisão — não se contorna.
- Quem tem permissão de edição numa pasta autorizada pode colocar arquivos nela; a
  regra de tipo/padrão reduz, mas não elimina, esse vetor.
- Exportação XLSX/DOCX não carrega comentários, histórico nem todos os recursos do
  documento original; `version` do Drive pode mudar sem alteração visível; o hash da
  exportação não é digest semântico de células — variação isolada de hash entre duas
  coletas não prova mudança de negócio nem reprova a coleta.
- Capturas reais ficam no disco local: a proteção depende da ACL **conferida** da pasta
  da chave, da própria chave e do diretório de capturas, e da criptografia do disco —
  não do `.gitignore`. Remover herança não elimina ACEs explícitas de outros
  principais, e mover um arquivo no mesmo volume preserva a ACL de origem; por isso o
  guia exige verificação antes de conteúdo real. ACL verificada não prova criptografia.
- Duas gerações por fonte não limitam o volume acumulado quando uma pasta de diários
  gera fontes novas; habilitar pastas exige rever a retenção total.

## Alternativas consideradas

| Alternativa | Motivo da recusa nesta etapa |
|---|---|
| OAuth de usuário (app desktop) | Credencial atrelada a uma pessoa, consentimento e refresh token pessoais; risco de reaproveitar conta pessoal |
| Delegação de domínio | Concede à service account a capacidade de agir como usuários do domínio — vedado pela sprint |
| `google-api-python-client` | Dependência maior, baseada em discovery; o REST direto com só `GET` torna a trava de escrita verificável por teste |
| Pasta sincronizada pelo Drive para desktop | Depende de cliente de sincronização e da máquina; não é reproduzível nem auditável por fonte |
| Apps Script no Drive | Executa dentro da conta de origem, com capacidade de escrita |
| Automação de navegador | Vedada; frágil e sem fronteira verificável |
| Amostra manual anonimizada | Substituída por esta sprint: não resolve a leitura recorrente |

## Referências

- Sprint `CARTORIO-DRIVE-READONLY-1` (2026-10-19).
- [`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](../../CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md) § 5, § 6.1, § 12.
- Google Drive API v3: escopos, `files.get`/`files.list` (pesquisa por pasta,
  `corpora`/`driveId` para Shared Drives), `files.export` (limite documentado de
  10 MB), download com `alt=media`, campos `version`, `modifiedTime`, `md5Checksum`,
  `capabilities.canDownload`.
- Google Cloud IAM: service accounts e compartilhamento direto; política
  `iam.disableServiceAccountKeyCreation`.
