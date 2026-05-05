# Roadmap do Módulo de Auditoria — Cartório System

> **Aviso:** Este documento é um plano de desenvolvimento e planejamento. Nenhuma
> das funcionalidades descritas aqui está implementada, exceto quando indicado
> com ✅. Não inclui dados pessoais, credenciais ou informações sensíveis.

Última atualização: 2026-05-04

---

## 1. Sumário executivo

O Cartório System passa a priorizar o **Módulo de Auditoria da Serventia** como
frente principal de desenvolvimento.

O módulo tem finalidade prática imediata: diagnosticar vulnerabilidades, inventariar
arquivos e pastas, analisar infraestrutura, documentar riscos, gerar evidências e
preparar a serventia para vistoria do Provimento CNJ nº 213/2026 (Classe 3).

A construção é incremental: cada fase entrega valor utilizável ao final do seu
desenvolvimento. A fase inicial é estritamente read-only — o sistema lê, analisa e
reporta; nunca modifica, move ou exclui nada.

O módulo financeiro (`app/modules/finance/`) é preservado integralmente como está e
rebaixado para backlog futuro. Ele não será expandido enquanto o módulo de auditoria
não estiver em uso operacional real pela serventia.

---

## 2. Mudança de prioridade

### O que muda

| Antes | Depois |
| ------- | -------- |
| Finance é o módulo central | Auditoria é o módulo central |
| Monthly Closing era próxima etapa | Scanner Read-Only é a próxima sprint |
| Auditoria era preparatória ao financeiro | Auditoria é o produto principal agora |
| Coleta técnica era "Etapa G, muito depois" | Coleta read-only é a Sprint 1 |

### O que permanece

- O módulo financeiro (Finance Core v1.2) é mantido sem alterações
- Os 48 testes passando continuam válidos
- As regras de domínio financeiro não mudam
- A arquitetura modular (`app/modules/<nome>/`) continua a mesma
- A independência do Atlas é preservada
- A adequação ao Provimento CNJ 213/2026 permanece como eixo paralelo

### Por que essa mudança

A serventia será vistoriada em breve e classificada como Classe 3. O risco imediato
não é a ausência de software financeiro — é a ausência de:

- inventário do que existe no servidor e nos arquivos;
- diagnóstico do estado real da infraestrutura;
- evidências documentadas para a vistoria;
- identificação de riscos de dados, backup e acesso;
- rastreabilidade das condições atuais.

Um scanner read-only entrega isso em horas de uso. Um CRUD financeiro expandido, não.

---

## 3. Princípios do módulo de auditoria

1. **Read-only first.** A primeira fase não modifica nenhum dado, arquivo ou
   configuração do ambiente analisado.
2. **Diagnóstico antes de intervenção.** O sistema entende antes de recomendar;
   recomenda antes de agir; nunca age sozinho na fase inicial.
3. **Nenhuma alteração em arquivos do servidor.** O scanner percorre, coleta
   metadados e sai. Não abre, renomeia, move, copia, exclui nem escreve nada no
   servidor analisado.
4. **Geração de evidências.** Cada execução produz artefatos rastreáveis com
   timestamp, hash e identificação do executor.
5. **Rastreabilidade.** Toda execução é registrada: quando, quem, o que foi
   analisado, com quais parâmetros.
6. **Mínimo privilégio.** O scanner solicita apenas leitura (read). Erros de
   permissão são registrados, não contornados.
7. **Proteção de dados sensíveis.** Conteúdo de arquivos nunca é lido na fase
   inicial. Apenas metadados (nome, tamanho, data, extensão, hash do nome).
   Nenhum dado pessoal entra nos relatórios.
8. **Compatibilidade com Provimento CNJ 213/2026 Classe 3.** Os relatórios gerados
   são formatados para uso como evidência no dossiê técnico da vistoria.
9. **Uso prático ao final de cada sprint.** Nenhuma fase é "preparatória" sem
   entregável. Cada sprint produz algo utilizável pelo gestor.
10. **Separação clara de ambientes.** O scanner nunca é executado automaticamente
    em produção sem autorização explícita do gestor. A primeira execução é sempre
    manual e monitorada.

---

## 4. Roadmap por fases

### Fase 0 — Reposicionamento e documentação ✅

**Objetivo:** Atualizar a visão estratégica do projeto e documentar o novo foco.

**Entradas:** Roadmap anterior, decisão estratégica, Provimento CNJ 213/2026.

**Processamento:** Revisão e criação de documentação.

**Saídas:**

- `docs/AUDIT_MODULE_ROADMAP.md` (este documento)
- `docs/AUDIT_READ_ONLY_POLICY.md`
- `docs/CNJ_213_ALIGNMENT.md`
- `docs/RISK_REGISTER_MODEL.md`
- `docs/OPERATING_FLOWS_AUDIT_PLAN.md`
- `docs/VISITATION_READINESS_PLAN.md`
- `docs/roadmap.md` atualizado
- `docs/modules/audit.md` atualizado

**Valor prático imediato:** Base documental para iniciar Sprint 1 com critérios claros.

**Riscos:** Documentação pode ficar desatualizada — revisar mensalmente.

**Limitações:** Nenhum código produzido ainda.

**Próximo passo:** Iniciar Sprint 1 (Fase 1).

---

### Fase 1 — Scanner read-only da estrutura de arquivos ✅ (Sprint 1 concluída e validada em ambiente real)

**Objetivo:** Percorrer a estrutura de pastas e arquivos do servidor de forma
segura, sem alterar nada, e gerar relatórios estruturados para o gestor.

**Entradas:**

- Caminho raiz configurável (env var `AUDIT_ROOT_PATH` ou argumento CLI)
- Lista de caminhos a excluir (opcional, env var `AUDIT_EXCLUDE_PATHS`)
- Profundidade máxima (opcional, env var `AUDIT_MAX_DEPTH`)
- Nome da execução (para rastreabilidade, ex.: `scan-servidor-2026-05-04`)

**Processamento:**

- `os.walk()` recursivo com tratamento de erros de permissão
- Coleta de metadados: nome, caminho relativo, extensão, tamanho (bytes),
  data de criação, data de modificação
- Sem abertura de conteúdo de arquivos
- Registro de erros de permissão como `ACCESS_DENIED` no relatório
- Cálculo de agregados: total de arquivos, total de pastas, tamanho total,
  distribuição por extensão, maiores arquivos, pastas mais pesadas

**Saídas:**

| Arquivo | Formato | Conteúdo |
| --------- | --------- | ---------- |
| `inventory.json` | JSON | Lista completa de arquivos com metadados |
| `inventory.csv` | CSV | Versão tabular para análise em planilha |
| `report.md` | Markdown | Relatório legível com resumo e achados |
| `manifest.json` | JSON | Metadados da execução: quem, quando, parâmetros, hash |
| `errors.json` | JSON | Caminhos com acesso negado ou erros de leitura |

**Destino dos artefatos:** `exports/audit/<scan-name>/`

**Valor prático imediato:**

- O gestor sabe exatamente o que existe no servidor
- Identifica pastas pesadas que explicam o espaço em disco crítico
- Identifica arquivos antigos, arquivos soltos na raiz e extensões suspeitas
- Gera evidência para o dossiê técnico da vistoria

**Riscos:**

- Varredura em diretório muito grande pode ser lenta — limitar profundidade se necessário
- Caminhos com caracteres especiais no Windows precisam de tratamento
- Não executar na VM de produção sem autorização do gestor

**Limitações:**

- Não abre conteúdo de arquivos (sem busca por palavras-chave internamente)
- Não detecta duplicatas por conteúdo (apenas por nome/tamanho nesta fase)
- Não acessa sistemas remotos — apenas caminhos locais ou UNC mapeados

**Validação em ambiente real:** execução `scan-docs-cartorio` (2026-05-04) varreu
1.539 arquivos em 0,428 s, sem erros de acesso, em Windows com caminhos contendo
espaços e caracteres especiais. Identificou 5 achados preliminares para a Sprint 2.
Ver [`docs/modules/audit_file_scanner.md`](../modules/audit_file_scanner.md) —
seções "Execução real validada" e "Achados preliminares para Sprint 2".

**Próximo passo:** Fase 2 — análise semântica dos metadados coletados.

---

### Fase 1b — AuditFinding CRUD ✅ (Sprint 2 concluída)

**Implementado:** `app/modules/audit/findings/` com enums, model, rules, schemas,
service, router e migration Alembic reversível. 36 testes específicos passando.
Ver [`docs/modules/audit_findings.md`](../modules/audit_findings.md).

---

### Fase 1c — Procedimento Operacional Read-Only ✅ (Sprint 2.5 concluída)

**Objetivo:** Documentar como executar o scanner em uso operacional real —
modos de execução, sequência de profundidade, checklists, fluxo de evidências
e a decisão arquitetural sobre o DocumentDiagnosis.

**Saídas produzidas:**

- [`docs/AUDIT_DEPLOYMENT_AND_OPERATION.md`](AUDIT_DEPLOYMENT_AND_OPERATION.md) —
  procedimento completo: modos A/B, sequência depth2→depth4→full, checklists
  pré/pós execução, fluxo scanner→artefatos→diagnóstico→candidatos→AuditFinding→dossiê,
  política de segurança, DA-23.
- `decisions.md` (D-23) — decisão arquitetural: DocumentDiagnosis analisa
  artefatos do scanner, nunca o servidor diretamente.
- [`docs/modules/audit.md`](../modules/audit.md) — fluxo operacional atualizado.
- [`docs/modules/audit_file_scanner.md`](../modules/audit_file_scanner.md) —
  sequência depth2→depth4→full documentada.

**Valor prático imediato:** o gestor tem um manual operacional completo para
executar o scanner no servidor real, arquivar evidências e registrar AuditFindings,
sem precisar de suporte técnico para cada execução.

**Nenhum código foi alterado nesta sprint.**

---

### Fase 2 — Diagnóstico documental inicial ✅ (Sprint 3 concluída + Sprint 3.5 hardening)

**Sprint 3 objetivo:** Analisar o inventário coletado na Fase 1 e identificar padrões
problemáticos: nomes genéricos, arquivos antigos, extensões suspeitas, pastas
desorganizadas, possíveis duplicatas.

**Decisão arquitetural (D-23):** O `DocumentDiagnosis` analisa o
`file_inventory.json` — nunca acessa o servidor ou caminhos de disco diretamente.
Ver [`docs/decisions.md`](decisions.md) (D-23) e
[`docs/AUDIT_DEPLOYMENT_AND_OPERATION.md`](AUDIT_DEPLOYMENT_AND_OPERATION.md) (seção 12).

**Sprint 3 entradas:** `inventory.json` da Fase 1

**Sprint 3 processamento:**

- Análise de nomes: identificar padrões genéricos (`cópia`, `backup`, `novo`,
  `versão final`, `final2`, `temp`, `lixo`, `antigo`, `draft`)
- Análise de datas: arquivos sem modificação há mais de X dias (configurável)
- Análise de extensões: identificar tipos de arquivo incomuns ou suspeitos
  (`.tmp`, `.bak`, `.old`, `.~`, executáveis em pastas de documentos)
- Análise de localização: arquivos soltos na raiz de pastas compartilhadas
- Detecção de prováveis duplicatas por nome + tamanho (sem hash de conteúdo)
- Análise de profundidade: pastas muito profundas ou muito rasas
- Inconsistências de nomenclatura: mistura de padrões (maiúsculas, separadores,
  idiomas, datas no nome)

**Sprint 3 saídas (implementadas com 7 regras de diagnóstico — DIAG-001 a DIAG-007):**

| Arquivo | Conteúdo |
| --------- | ---------- |
| `document_diagnosis.json` | Candidatos estruturados em JSON |
| `document_diagnosis.csv` | Versão tabular para Excel |
| `document_diagnosis.md` | Relatório legível com achados por regra |
| `diagnosis_manifest.json` | Metadados: scanner_run_id, SHA-256, flags de segurança |

**Sprint 3.5 — Operational Hardening & Validation:**

Transformou o módulo de "implementado" para "operacionalmente validado":

- ✅ Auditoria completa de conformidade com contrato de segurança (metadata-only)
- ✅ Melhoria de rastreabilidade: `evidence_reference` consistency em todas as regras
- ✅ Documentação operacional completa: [`docs/modules/audit_document_diagnosis_execution.md`](../modules/audit_document_diagnosis_execution.md)
  - Checklists pré e pós-execução
  - Guia de validação de integridade
  - Separação de candidatos para revisão humana
  - Template de relatório de execução real
  - Troubleshooting
  - Conformidade CNJ 213/2026
- ✅ Validação: 29/29 testes passando, ruff aprovado, segurança mantida
- ✅ Commit: `6e3a39f` com documentação operacional


**Valor prático imediato:**

- Candidatos organizados por severidade (HIGH, MEDIUM, LOW) e regra
- Guia prático para execução real controlada em ambiente do gestor
- Separação clara: candidatos → revisão humana → AuditFinding (nunca automático)
- Evidência de conformidade de segurança para dossiê técnico

**Riscos:** Falsos positivos em nomes genéricos — sempre requer revisão humana.

**Limitações:** 
- Sem análise de conteúdo interno dos arquivos
- Sem integração automática com AuditFinding (fluxo manual obrigatório)
- Sem deduplicação por hash (apenas nome + tamanho)

**Próximo passo:** Execução Real Controlada + Sprint 4 (Human Review Workflow).

---

### Fase 2.5 — Execução Real Controlada do DocumentDiagnosis ✅

**Status:** ✅ Concluída (2026-05-04)

**Objetivo:** Executar DocumentDiagnosis em dados reais da serventia, validar candidatos
e iniciar revisão humana.

**Pré-requisitos:**

- `file_inventory.json` gerado pelo scanner (Fase 1)
- Diretório externo (fora do repositório Git) para artefatos
- Acesso à documentação: [`docs/modules/audit_document_diagnosis_execution.md`](../modules/audit_document_diagnosis_execution.md)

**Execução:**

```powershell
python -m app.modules.audit.diagnosis.cli \
    --inventory "C:\Audit_Reports\<data>\scan\file_inventory.json" \
    --manifest "C:\Audit_Reports\<data>\scan\scan_manifest.json" \
    --output-dir "C:\Audit_Reports\<data>\diagnosis" \
    --run-name "diagnosis-real"
```

**Saídas (mantidas fora do Git):**

- `document_diagnosis.json`, `.csv`, `.md`, `.manifest.json`
- Relatório de execução (template: seção VII do guia operacional)

**Validação:**

1. Gestor revisa `document_diagnosis.md` (report legível)
2. Abre `document_diagnosis.csv` em Excel
3. Filtra por Severity (HIGH → MEDIUM → LOW)
4. Decisão humana: candidato é achado real?
5. Se SIM: criar AuditFinding (via API ou interface)
6. Se NÃO: registrar como "falso positivo"


**Valor prático imediato:**

- Linha de base de candidatos documentais
- Refinamento de regras com padrões reais
- Primeiros AuditFindings baseados em diagnóstico

**Riscos:**

- Falsos positivos exigem revisão cuidadosa — não automatizar
- Documentação privada (outputs reais) pode ficar desatualizada

**Próximo passo após conclusão:** Sprint 3.6 (Calibração de Regras).

---

### Sprint 3.6 — Calibração de Regras após Validação Real ✅ (Em andamento — 2026-05-05)

**Status:** Implementação em andamento

**Objetivo:** Refinar as regras de diagnóstico com base na validação humana real de 44 candidatos,
reduzindo falsos positivos e melhorando qualidade futura.

**Entrada:** Relatório de revisão humana `revisao_humana_candidatos_auditoria_preenchida.md`

**Ajustes implementados:**

1. **DIAG-001 calibrada:** Contextuais (engegraph, sefaz) só geram candidato fora de contexto financeiro legítimo
   - Redução esperada: ~30 falsos positivos (comprovantes/repasses)
   - Termos críticos (senha, token, login, certificado) continuam sendo detectados sempre

2. **DIAG-008 criada:** Detecta documentos pessoais/operacionais em pasta financeira
   - Cobre achado real: "VALIDA EM TODO O TERRITORIO NACIONAL", "AUTORIZAÇÃO DE ESCRITURA" em Gerenciamento_financeiro
   - Indica erro de classificação documental ou violação potencial de LGPD

3. **DIAG-002, 004a, 006, 007 melhorados:** Descrições atualizadas, linguagem menos alarmista,
   recomendações mais claras para revisão formal

**Saídas:**

- Testes novos cobrindo calibração
- Documentação atualizada (audit_document_diagnosis.md, audit_document_diagnosis_execution.md)
- Nova execução real comparativa (antes vs. depois)
- Commit com todas as mudanças

**Validação:**

- ✅ ruff aprovado (sem erros de formatação)
- ✅ pytest aprovado (testes novos + regressão)
- ✅ Execução comparativa: redução de DIAG-001, novos DIAG-008 detectados
- ✅ Segurança mantida: metadata-only, read-only, sem acesso a documentos originais

**Próximo passo:** Sprint 4 (Human Review Workflow) ou Nova execução controlada comparativa.

---

### Sprint 4 — Human Review Workflow (recomendado)

**Status:** Planejado

**Objetivo:** Formalizar o fluxo de revisão humana e integração com AuditFinding.

**Escopo (recomendado):**

- Interface web para revisar candidatos
- Workflow: CANDIDATE → REVIEWING → ACCEPTED/REJECTED → AUDIT_FINDING
- Rastreabilidade: quem revisou, quando, decisão e motivo
- Batch processing: revise múltiplos candidatos de uma execução
- Comparação com execuções anteriores (para detectar mudanças)

**Não incluir:** Automação da criação de AuditFinding — sempre manual.


---

### Fase 3 — Auditoria de discos e armazenamento

**Objetivo:** Coletar dados de uso de disco e identificar riscos de esgotamento.

**Entradas:** Configuração do sistema (caminhos dos volumes a analisar)

**Processamento:**

- `shutil.disk_usage()` por volume/partição
- Cruzamento com inventário da Fase 1: quais pastas mais consomem espaço
- Tendência de crescimento (se houver histórico de scans anteriores)
- Identificação de maiores arquivos e maiores pastas no contexto do uso total

**Saídas:** `disk_report.md`, `disk_usage.json`

**Valor prático imediato:** Confirmar o estado crítico dos discos e priorizar ação.

**Limitações:** Sem acesso a SMART ou saúde do disco físico (requer ferramentas
de SO ou hardware). Dados de saúde do disco devem ser coletados manualmente.

**Próximo passo:** Fase 4 — auditoria de backup.

---

### Fase 4 — Auditoria de backup

**Objetivo:** Analisar logs e artefatos de backup para identificar falhas,
ausências e inconsistências sem tocar nos backups em si.

**Entradas:**

- Caminho da pasta de logs do Cobian Gravity (somente leitura)
- Configuração: quais sistemas devem ter backup (Engegraph, fileserver, CartorioSystem)
- Data esperada do último backup bem-sucedido

**Processamento:**

- Leitura dos arquivos de log do Cobian (somente leitura, sem parsear binários)
- Verificação de presença dos arquivos de backup esperados (por data e nome)
- Identificação de lacunas: dias sem backup bem-sucedido registrado
- Verificação de tamanho: backup muito menor que o esperado pode indicar falha parcial
- Nunca executar restauração — apenas leitura dos metadados de backup

**Saídas:** `backup_audit_report.md`, `backup_log_summary.json`

**Valor prático imediato:** Confirmar ou refutar se o backup está funcionando.
Evidência crítica para a vistoria.

**Limitações:** Não testa restauração (isso é operação manual documentada em ata).
Não acessa dumps de banco diretamente.

**Próximo passo:** Fase 5 — auditoria de segurança local.

---

### Fase 5 — Auditoria de segurança local

**Objetivo:** Coletar informações sobre usuários, grupos e configurações básicas
de segurança do ambiente Windows, sem alterar nada.

**Entradas:** Acesso de leitura ao ambiente Windows local (Event Log, usuários locais)

**Processamento (read-only, somente coleta de metadados):**

- Listar usuários locais e seu status (ativo/inativo) via `net user` ou WMI
- Listar grupos locais e membros via `net localgroup`
- Verificar data do último logon por usuário
- Verificar se há conta "Administrator" ativa sem renomeação
- Verificar política de senha básica (via `net accounts`)
- Verificar se Windows Update tem atualizações críticas pendentes (via API WUA)
- Verificar status do Windows Defender (via cmdlet PowerShell, somente leitura)
- **Nunca** ler senhas, credenciais ou hashes

**Saídas:** `security_local_report.md`, `users_inventory.json`,
`groups_inventory.json`, `security_gaps.json`

**Valor prático imediato:** Inventário de usuários e gaps de segurança locais.

**Limitações:** Requer execução local no servidor (não remota). Dados de política
de senha são básicos — análise profunda requer ferramentas especializadas.

**Próximo passo:** Fase 6 — auditoria de rede.

---

### Fase 6 — Auditoria de rede interna

**Objetivo:** Coletar informações sobre a topologia e configuração de rede visíveis
localmente, sem escanear ativamente a rede ou alterar configurações.

**Entradas:** Configuração de rede do servidor (interfaces, rotas, ARP cache)

**Processamento (read-only):**

- Listar interfaces de rede ativas e seus endereços (IP, máscara, gateway)
- Verificar tabela de rotas (`route print`)
- Verificar ARP cache (dispositivos recentemente comunicados)
- Verificar portas abertas locais (`netstat -an`, somente leitura)
- Verificar se RDP (porta 3389) está ouvindo externamente
- Verificar regras de firewall Windows (somente leitura via `netsh advfirewall`)
- **Sem** port scan de outros dispositivos na rede
- **Sem** captura de pacotes

**Saídas:** `network_local_report.md`, `open_ports.json`, `network_interfaces.json`

**Valor prático imediato:** Identificar portas expostas e verificar se RDP está
acessível externamente — risco crítico atual.

**Próximo passo:** Fase 7 — auditoria documental de políticas.

---

### Fase 7 — Auditoria de POPs, políticas e documentos internos

**Objetivo:** Inventariar e classificar os documentos normativos e procedimentais
existentes na serventia.

**Entradas:** Inventário de arquivos da Fase 1 + entrevista com o gestor

**Processamento (análise de metadados + checklist manual):**

- Identificar documentos do tipo PSI, PCN, PRD, POP, contrato, licença por
  padrão de nome e localização
- Verificar data de última modificação (documento atualizado ou antigo?)
- Aplicar checklist: quais documentos obrigatórios existem, quais estão ausentes
- Não abrir conteúdo — apenas metadados e checklist

**Saídas:** `policies_inventory.md`, `missing_documents_checklist.md`

**Valor prático imediato:** Lista exata do que existe e do que está faltando para
a vistoria.

**Próximo passo:** Fase 8 — auditoria de fluxos.

---

### Fase 8 — Auditoria de fluxos operacionais

**Objetivo:** Documentar e diagnosticar os fluxos internos da serventia, identificando
ausências, inconsistências e riscos operacionais.

**Entradas:** Entrevistas, observação, documentos existentes (Fase 7)

**Processamento (análise estruturada com formulário):**

- Mapeamento de cada fluxo: entrada → processamento → saída → responsável
- Verificação de cobertura: há POP para este fluxo? Ele está atualizado?
- Identificação de pontos de falha: onde o fluxo depende de uma única pessoa?
- Identificação de riscos de dados: onde dados sensíveis transitam sem controle?

**Fluxos prioritários:**

- Entrada e protocolo de documentos
- Qualificação e análise jurídica
- Geração de documentos (atos notariais e de registro)
- Assinatura e autenticação
- Arquivamento físico e digital
- Digitalização: onde, como, para onde vai
- Documentos suspeitos/falsos: como são tratados hoje
- Fluxo financeiro: emolumentos, repasses, ISS
- Obrigações externas: CNJ, ONR, ARPEN, SEDI

**Saídas:** `flows_diagnosis.md`, `flows_risk_matrix.md`

**Valor prático imediato:** Diagnóstico real dos fluxos para POPs prioritários.

**Próximo passo:** Fase 9 — motor de riscos.

---

### Fase 9 — Motor de riscos e recomendações

**Objetivo:** Consolidar todos os achados das fases anteriores em uma matriz de
riscos estruturada e um plano de ação priorizado.

**Entradas:** Saídas de todas as fases anteriores + `RISK_REGISTER.md`

**Processamento:**

- Importar achados dos relatórios anteriores
- Aplicar modelo de risco (ver seção 9 deste documento)
- Calcular prioridade: severidade × probabilidade × impacto
- Gerar recomendações por área
- Ordenar por prioridade

**Saídas:** `risk_matrix.md`, `risk_matrix.csv`, `action_plan.md`

**Valor prático imediato:** Plano de ação concreto para o gestor executar.

**Próximo passo:** Fase 10 — dossiê técnico.

---

### Fase 10 — Dossiê técnico e prontidão para vistoria

**Objetivo:** Consolidar todos os artefatos em um dossiê técnico estruturado
com hashes, índice e evidências para a vistoria.

**Entradas:** Todos os artefatos das fases anteriores

**Processamento:**

- Calcular SHA-256 de cada artefato
- Gerar `dossier_index.json` com hash e metadados de cada documento
- Gerar `dossier_report.md` — relatório executivo do dossiê
- Verificar completude: quais itens do `VISITATION_READINESS_CHECKLIST.md`
  têm evidência disponível

**Saídas:** `dossier_index.json`, `dossier_report.md`, `completeness_check.md`

**Valor prático imediato:** Dossiê pronto para apresentar ao vistoriador.

**Próximo passo:** Fase 11 — automação futura.

---

### Fase 11 — Automação assistida futura

**Objetivo:** Automatizar execuções periódicas dos scanners com aprovação prévia
do gestor, alertas automáticos e comparação com execuções anteriores.

> Esta fase é planejada. Não implementar antes das Fases 1-10 estarem validadas.

**Funcionalidades planejadas:**

- Agendamento de scans com janela de execução aprovada
- Comparação de inventários entre execuções (diff)
- Alertas por e-mail ou notificação em caso de novos riscos
- Dashboard de evolução dos riscos ao longo do tempo
- Exportação automática para Atlas (unidirecional, sem acoplamento)

**Pré-requisito:** Autenticação multiusuário implementada no sistema.

---

## 5. Sprints completadas

### Sprint 1 ✅ — Scanner Read-Only de Arquivos

**Status:** Concluída e validada em ambiente real  
**Entrega:** Fase 1 — Scanner read-only  
**Evidência:** 72 testes passando, scan de 1.539 arquivos em 0,428s  

---

### Sprint 2 ✅ — AuditFinding CRUD

**Status:** Concluída  
**Entrega:** Fase 1b — AuditFinding CRUD com enums, modelos, service, router, migration  
**Evidência:** 36 testes, reversible Alembic migration  

---

### Sprint 2.5 ✅ — Procedimento Operacional Read-Only

**Status:** Concluída  
**Entrega:** Fase 1c — Documentação operacional completa  
**Evidência:** [`docs/AUDIT_DEPLOYMENT_AND_OPERATION.md`](AUDIT_DEPLOYMENT_AND_OPERATION.md), D-23  

---

### Sprint 3 ✅ — DocumentDiagnosis Core v1

**Status:** Concluída  
**Entrega:** Fase 2 — DocumentDiagnosis com 7 regras (DIAG-001 a DIAG-007)  
**Evidência:** 29 testes passando, ruff aprovado, metadata-only contract validado  

---

### Sprint 3.5 ✅ — DocumentDiagnosis Operational Hardening & Validation

**Status:** Concluída  
**Entrega:** Documentação operacional + validação de segurança + hardening  
**Evidência:**
- Commit: `6e3a39f`
- Documentação: [`docs/modules/audit_document_diagnosis_execution.md`](../modules/audit_document_diagnosis_execution.md)
- Testes: 29/29 passando
- Segurança: contrato validado (metadata-only, no file access, no AuditFinding creation)

---

## 6. Sprint 1 — Scanner Read-Only de Arquivos (Detalhes)


### Objetivo da sprint

Implementar um scanner CLI (ou endpoint interno) que percorra a estrutura de
pastas de um caminho configurável, colete metadados de todos os arquivos e
gere relatórios JSON, CSV e Markdown — sem modificar nenhum arquivo.

### Localização no código

```text
app/modules/audit/
├── scanner/
│   ├── __init__.py
│   ├── file_scanner.py     # lógica principal de varredura
│   ├── models.py           # dataclasses/Pydantic para FileEntry, ScanResult
│   ├── report.py           # geração de JSON, CSV, Markdown
│   └── cli.py              # entry point CLI (argparse ou typer)
└── (outros submódulos futuros)
```

### Interface do scanner

```bash
# Via CLI
python -m app.modules.audit.scanner.cli \
    --root "C:\Dados\Servidor" \
    --exclude "C:\Dados\Servidor\Sistema" \
    --max-depth 8 \
    --output-dir "exports/audit/scan-2026-05-04" \
    --run-name "scan-inicial"

# Via variáveis de ambiente
AUDIT_ROOT_PATH=C:\Dados\Servidor
AUDIT_EXCLUDE_PATHS=C:\Dados\Servidor\Sistema,C:\Dados\Servidor\Temp
AUDIT_MAX_DEPTH=8
AUDIT_OUTPUT_DIR=exports/audit/scan-2026-05-04
```

### Metadados coletados por arquivo

| Campo | Tipo | Fonte |
| ------- | ------ | ------- |
| `path_relative` | str | Relativo ao caminho raiz |
| `name` | str | `os.path.basename` |
| `extension` | str | `os.path.splitext` |
| `size_bytes` | int | `os.stat().st_size` |
| `created_at` | datetime | `os.stat().st_ctime` |
| `modified_at` | datetime | `os.stat().st_mtime` |
| `depth` | int | Profundidade a partir da raiz |
| `is_directory` | bool | `os.path.isdir` |
| `access_error` | str | None ou mensagem de erro |

### Estrutura de saída

```text
exports/audit/<run-name>/
├── inventory.json          # lista completa de arquivos
├── inventory.csv           # versão tabular
├── report.md               # relatório legível
├── manifest.json           # metadados da execução
└── errors.json             # caminhos com acesso negado
```

### manifest.json (rastreabilidade)

```json
{
  "run_name": "scan-inicial",
  "run_id": "uuid-aqui",
  "executed_at": "2026-05-04T10:00:00Z",
  "executed_by": "gestor",
  "root_path": "[REDACTED - caminho absoluto removido do log]",
  "excluded_paths_count": 2,
  "max_depth": 8,
  "total_files": 12543,
  "total_directories": 876,
  "total_size_bytes": 45678901234,
  "total_errors": 3,
  "duration_seconds": 42.1,
  "system_version": "cartorio-system-0.1.0",
  "sha256_inventory_json": "abc123..."
}
```

### Relatório Markdown (report.md) — seções

1. **Resumo executivo** — totais, data, parâmetros
2. **Top 10 maiores arquivos**
3. **Top 10 pastas mais pesadas**
4. **Distribuição por extensão** (tabela)
5. **Arquivos antigos** (sem modificação há mais de 365 dias)
6. **Arquivos soltos na raiz** (diretamente no caminho raiz)
7. **Extensões suspeitas** (`.tmp`, `.bak`, `.old`, executáveis em locais inesperados)
8. **Erros de acesso** (caminhos bloqueados)
9. **Recomendações iniciais** (geradas automaticamente)

### Critérios de aceite da Sprint 1

- [ ] Scanner percorre diretórios recursivamente sem modificar nenhum arquivo
- [ ] Erros de permissão são registrados em `errors.json` e não interrompem a varredura
- [ ] Caminhos excluídos são respeitados (configurável)
- [ ] Profundidade máxima é respeitada quando configurada
- [ ] `inventory.json` contém todos os metadados definidos
- [ ] `inventory.csv` é legível no Excel/LibreOffice sem erro de encoding
- [ ] `report.md` contém todas as 9 seções
- [ ] `manifest.json` contém hash SHA-256 do `inventory.json`
- [ ] Caminhos Windows com espaços e caracteres especiais funcionam corretamente
- [ ] Testes unitários cobrem: diretório vazio, diretório com permissão negada,
  diretório profundo, arquivo sem extensão, arquivo com extensão suspeita
- [ ] Testes usam diretórios temporários (`tempfile.mkdtemp`) — nunca o servidor real
- [ ] `ruff check` e `ruff format --check` passam
- [ ] Nenhum caminho absoluto do servidor entra em logs ou relatórios de forma não filtrada
- [ ] O conteúdo interno de nenhum arquivo é lido

---

## 7. Diagnóstico documental — implementado em Sprint 3 (Fase 2)

Após o inventário, o sistema identifica padrões problemáticos nos metadados coletados:

### Padrões de nomes a detectar

| Padrão | Exemplo | Risco |
| -------- | --------- | ------- |
| Nome genérico | `novo.docx`, `copia.pdf`, `versão final 2.odt` | Organização deficiente |
| Backup no nome | `arquivo_backup.pdf`, `contrato_bkp.docx` | Pode ser desatualizado |
| Data no nome mal-formatada | `doc01052026.pdf`, `contrato_01_05_26.docx` | Inconsistência |
| Prefixo incremental manual | `relatorio_v3_final_revisado.pdf` | Controle de versão inadequado |
| Extensão dupla | `documento.pdf.pdf` | Possível malware ou erro |
| Extensão executável em pasta de documentos | `app.exe`, `script.bat` | Risco de segurança |
| Arquivo `.tmp` ou `.bak` solto | `~lock.tmp`, `backup.bak` | Resíduo de aplicação |

### Critérios de arquivos antigos

- Sem modificação há > 365 dias: alerta
- Sem modificação há > 3 anos: risco de obsolescência
- Criado há > 5 anos sem acesso: candidato a arquivo morto

### Pastas a inspecionar especialmente

- Pastas com `backup`, `antigo`, `2018`, `velho` no nome
- Pastas com 0 arquivos (exceto se intencionalmente vazias)
- Pastas com mais de 500 arquivos na raiz (sem subpastas)
- Pastas duplicadas (mesmo nome em paths distintos)

---

## 8. Auditoria técnica — escopo futuro (Fases 3-6)

| Área | Método de coleta | Limitação da fase inicial |
| ------ | ----------------- | -------------------------- |
| Espaço em disco | `shutil.disk_usage()` | Sem SMART/saúde do disco |
| Backup | Leitura de logs Cobian | Sem teste de restauração |
| Antivírus | `Get-MpComputerStatus` (PowerShell) | Somente status básico |
| Firewall | `netsh advfirewall show` | Sem alteração de regras |
| RDP/acesso remoto | `netstat -an` + check porta 3389 | Sem bloqueio automático |
| VPN | Verificar interfaces VPN ativas | Sem configuração |
| Permissões | `Get-Acl` (PowerShell) | Listagem apenas, sem alteração |
| Usuários | `net user`, `Get-LocalUser` | Sem alteração ou bloqueio |
| Rede local | Interfaces + ARP cache | Sem port scan ativo |

---

## 9. Auditoria operacional — escopo futuro (Fases 7-8)

### Fluxos a auditar

| Fluxo | Método | Entregável |
| ------- | -------- | ----------- |
| Entrada e protocolo | Entrevista + observação | Mapa do fluxo + achados |
| Qualificação jurídica | Entrevista + POP existente | Gap analysis |
| Geração de documentos | Observação do Engegraph | Dependências identificadas |
| Assinatura e autenticação | Entrevista | Riscos de delegação |
| Arquivamento físico | Observação | Riscos de perda |
| Digitalização | Observação + inventário | Padronização necessária |
| Documentos suspeitos/falsos | Entrevista | Fluxo atual documentado |
| Financeiro | Planilhas + Cartório System | Reconciliação pendente |
| Obrigações externas | Checklist CNJ/ARPEN/SEDI | Prazos e gaps |

### Documentos normativos a auditar

| Documento | Obrigatório | Situação esperada |
| ----------- | ------------ | ------------------- |
| PSI — Política de Segurança da Informação | Sim | Ausente — criar |
| PCN — Plano de Continuidade de Negócios | Sim | Rascunho — formalizar |
| PRD — Plano de Recuperação de Desastres | Sim | Ausente — criar |
| POPs por fluxo operacional | Sim | Parcialmente existentes |
| Plano de backup | Sim | Informalmente existente — formalizar |
| Política de acesso e permissões | Sim | Ausente — criar |
| Plano de resposta a incidentes | Sim | Ausente — criar |

---

## 10. Modelo de matriz de riscos

> Usar este modelo ao registrar achados no módulo `AuditFinding`.

| Campo | Tipo | Descrição |
| ------- | ------ | ----------- |
| `id` | str | Ex.: `RI-01`, `RS-03` |
| `category` | enum | INFRASTRUCTURE / BACKUP / SECURITY / NETWORK / ACCESS / DOCUMENT / LGPD / CONTINUITY / OPERATIONAL / SYSTEM |
| `title` | str | Título curto do risco |
| `description` | str | Descrição detalhada |
| `evidence` | str | O que comprova o risco (fonte, log, screenshot) |
| `origin` | enum | SCANNER / MANUAL / TECHNICAL_REPORT / CHECKLIST / INTERVIEW / CNJ_MAPPING / BACKUP_LOG / DISK_SCAN / NETWORK_REVIEW / POLICY_REVIEW / OTHER |
| `cnj_requirement` | str | Requisito do Provimento 213/2026 relacionado (ex.: "B-01: RPO ≤4h") |
| `severity` | enum | CRITICAL / HIGH / MEDIUM / LOW / INFO |
| `probability` | enum | HIGH / MEDIUM / LOW |
| `impact` | enum | HIGH / MEDIUM / LOW |
| `priority` | enum | URGENT / HIGH / MEDIUM / LOW (derivado dos três anteriores) |
| `recommendation` | str | Ação recomendada (o que fazer) |
| `owner` | str | Responsável sugerido |
| `due_date` | date | Prazo sugerido |
| `status` | enum | OPEN / IN_PROGRESS / RESOLVED / ACCEPTED / CLOSED |
| `identified_at` | datetime | Data de identificação |
| `reviewed_at` | datetime | Data da última revisão |
| `notes` | str | Observações adicionais |

---

## 11. Padrão de entregáveis

Todos os artefatos produzidos pelo módulo de auditoria seguem este padrão:

### Estrutura de diretórios de saída

```text
exports/audit/
├── <run-name>/
│   ├── manifest.json        # rastreabilidade: quem, quando, parâmetros, hash
│   ├── inventory.json       # dados estruturados completos
│   ├── inventory.csv        # versão tabular para análise
│   ├── report.md            # relatório legível em Markdown
│   ├── errors.json          # erros de acesso (se houver)
│   └── [artefatos extras por fase]
└── catalog.csv              # índice de todas as execuções
```

### Padrão do manifest.json

```json
{
  "run_name": "string",
  "run_id": "uuid",
  "phase": "1|2|3|...",
  "executed_at": "ISO 8601",
  "executed_by": "string",
  "parameters": {},
  "totals": {},
  "duration_seconds": 0.0,
  "system_version": "string",
  "sha256_of_inventory_json": "string"
}
```

### Padrão do catalog.csv (índice de execuções)

```csv
run_id,run_name,phase,executed_at,executed_by,total_items,sha256
```

### Regras de saída

1. Paths absolutos do servidor nunca aparecem em logs ou relatórios exportados — apenas caminhos relativos
2. Dados pessoais de clientes nunca entram em nenhum artefato
3. Credenciais nunca são coletadas ou registradas
4. Cada artefato tem hash SHA-256 registrado no manifest
5. O Markdown usa formatação compatível com GitHub Flavored Markdown
6. O CSV usa UTF-8 com BOM para compatibilidade com Excel no Windows
7. O JSON usa indentação de 2 espaços para legibilidade
