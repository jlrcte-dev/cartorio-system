# Perguntas Críticas para INOVA LGPD

> **Objetivo:** Refinar roadmap do módulo LGPD com base em respostas jurídicas/operacionais.  
> **Prazo para resposta:** 1 semana (até 2026-05-12)  
> **Destinatário:** INOVA LGPD (assessoria jurídica)

Última atualização: 2026-05-05  
Versão: 1.0

---

## Grupo A — Críticas (bloqueiam decisões)

Estas perguntas **devem** ser respondidas antes de refinar design ou iniciar implementação.

---

### A-01 — Designação do DPO

**Pergunta:** A serventia Cartório Costa Teixeira **precisa nomear um DPO/Encarregado formal** conforme LGPD? Sim, a propriainova foi contratada como DPO as a service da serventia.

**Contexto:**
- AC-15 (Nomeação do DPO) está **7+ meses atrasada** (data prevista: 2023-03-10)
- AC-16 (Divulgação do DPO no site) depende desta designação
- Plataforma INOVA mostra como "Pendente" desde início do projeto

**Por que importa:**
1. Requisito LGPD (Art. 5, II)
2. Pré-requisito para CNJ 213 (Bloco G — Governança)
3. Afeta design: se não precisa nomear, AC-15/16 saem do escopo

**Qual decisão depende:**
- Sprint LGPD-1: incluir ou não DpoRecord (futura entidade)
- Se não obrigatório: marcar AC-15/16 como "Não Aplicável" e alocar espaço

**Impacto no módulo LGPD:**
- Se **Sim:** criar `DpoRecord` em Sprint 3 para rastrear designação
- Se **Não:** simplificar; remover AC-15/16 do escopo

---

### A-02 — Atividades com Ausência de Base Legal

**Pergunta:** Das **38 atividades de tratamento** mapeadas no RAT/ROPa (plataforma INOVA), qual é exatamente a situação das **2 atividades com "ausência de base legal"**? Teremos que revisar junto a gestão da serventia.

**Contexto:**
- Imagem 1 do dashboard INOVA mostra: "2 atividades com ausência de base legal"
- Risco crítico de não-conformidade com LGPD
- Nenhuma informação sobre quais atividades ou qual é a ação necessária

**Por que importa:**
1. Impossível validar conformidade LGPD enquanto houver "base legal ausente"
2. Podem exigir mudança operacional ou reinterpretação jurídica
3. Afeta relatório de conformidade (não podemos afirmar "100% conforme")

**Qual decisão depende:**
- Design do módulo: incluir ou não "legal_basis_status" em ProcessingActivity
- Se houver risco crítico: sinalizar em dashboard como "bloqueador"

**Impacto no módulo LGPD:**
- Sprint LGPD-6 (ProcessingActivity): incluir campo para status de base legal
- Relatórios: destacar atividades sem base legal como **CRÍTICA**

---

### A-03 — Erro de Integração da Plataforma INOVA

**Pergunta:** Qual é exatamente o **status do erro** "Chave de integração da plataforma de privacidade não foi configurada"? Será investigado e informado posteriormente.

**Contexto:**
- Imagem 1 do dashboard INOVA mostra erro crítico
- AC-20 (Gestão de titulares) está bloqueado
- AC-25 (Plano de Resposta a Incidentes) pode também depender

**Por que importa:**
1. Determina se integração plataforma INOVA é viável em Sprint LGPD-6
2. Se não for viável, módulo LGPD funciona independente (design já prevê isso)
3. Afeta timeline: esperar resolução INOVA vs. implementar standalone

**Qual decisão depende:**
- Sprint LGPD-6: integração direta com INOVA ou importação manual?
- MVP: ProcessingActivity importada via CSV ou por API INOVA?

**Impacto no módulo LGPD:**
- Se **não resolver logo:** módulo LGPD importa via CSV; integração fica para futuro
- Se **resolver em junho:** possibilitar API integration em Sprint LGPD-6

---

### A-04 — Consentimento de Colaboradores (AC-10)

**Pergunta:** AC-10 (Gestão de Consentimento de Colaboradores) exige qual **forma legal** de coleta? Termo de ciência, os termos ja foram assinados pelos colaboradores.

**Opções esperadas:**
1. Aditivo ao contrato de trabalho (genérico, uma única vez)
2. Formulário eletrônico (específico por atividade, periodicamente)
3. Termo de ciência (documento, com assinatura)
4. Plataforma externa (qual?)

**Por que importa:**
1. Design do módulo LGPD: apenas registrar consentimento ou gerenciar coleta?
2. Se registrar, precisa de entidade `ConsentRecord` (futura)
3. MVP não inclui AC-10 completo (deixamos para Sprint 4)

**Qual decisão depende:**
- Sprint LGPD-4: escopo de ConsentRecord
- Timing: se forma simples, pode vir em Sprint 3; se complexa, Sprint 4+

**Impacto no módulo LGPD:**
- Sprint LGPD-4: criar `ConsentRecord` com campos apropriados
- Relatórios: demonstrar coleta formal para vistoria

---

### A-05 — Plano de Resposta a Incidentes (AC-25)

**Pergunta:** Existe **template ou procedimento padrão** que INOVA recomenda para AC-25? Será verificado com a equipe de acessoria.

**Contexto:**
- AC-25 está meses atrasada
- Crítica para CNJ 213 (comunicação de incidente em até 72h)
- Módulo LGPD precisa rastrear execução (registro formal)

**Opções esperadas:**
1. INOVA forneceu template genérico
2. Recomenda template público (NIST, CNJ, etc.)
3. Customizar conforme estrutura Cartório
4. Usar parcialmente: só comunicação, não análise completa

**Por que importa:**
1. Determina campos de `PrivacyIncident` (entidade futura)
2. Design: registro simples (data, descrição, comunicado?) ou completo (análise, ações)?
3. MVP não inclui AC-25 completo; Sprint 3+ apenas suporte básico

**Qual decisão depende:**
- Sprint LGPD-4: escopo de PrivacyIncident
- Documentação: estrutura esperada do plano

**Impacto no módulo LGPD:**
- Sprint LGPD-3: AC-25 marcada como "pronto para validação"
- Sprint LGPD-4: PrivacyIncident com campos baseados em template

---

## Grupo B — Importantes (refinam roadmap)

Estas perguntas **devem** ser respondidas antes de finalizarem design. Não bloqueiam decisão "vai/não vai".

---

### B-01 — Responsáveis pelas Ações (AC-01..25)

**Pergunta:** Das 25 ações do Plano de Ação, quantas são **responsabilidade de INOVA** vs. **cliente (Cartório)**? Todas as entregas são de responsabilidade do cartório para prosseguir com o projeto de adequação.

**Contexto:**
- Plano de Ação lista 25 ações
- Responsáveis: InovaLGPD (7 ações), Cliente (18 ações)
- Algumas dependem de decisão cliente; outras são pura assessoria

**Por que importa:**
1. Accountability: quem faz o quê?
2. Timing: INOVA depende do cliente; vice-versa
3. Design do módulo: suportar "owner" interno e "owner" externo?

**Qual decisão depende:**
- Sprint LGPD-1: criar LgpdActionOwner com "external_party" para INOVA?
- Relatórios: separar ações INOVA vs. Cliente?

**Impacto no módulo LGPD:**
- Se separação importante: adicionar campo `responsible_entity` (internal, inova, hybrid)
- Relatórios: breakdown por responsável externo

---

### B-02 — Avaliação de Fornecedores (AC-13)

**Pergunta:** AC-13 (Avaliação de Fornecedores e Parceiros) — qual é o **status atual** e quem executa? Avaliação de fornecedores é feita pela Inova, como ja foi feita a algum tempo revisar os contratos e solicitar nova auditoria.

**Contexto:**
- AC-13 está pendente
- INOVA pode estar conduzindo análise de contratos
- Cartório pode precisar executar avaliação operacional

**Por que importa:**
1. Determina escopo de Sprint LGPD-5 (VendorAssessment)
2. Se INOVA conclui, Cartório só documenta resultado
3. Se Cartório executa, módulo LGPD precisa ser ferramenta de execução

**Qual decisão depende:**
- Sprint LGPD-5: VendorAssessment é "registro de resultado" ou "ferramenta de análise"?
- Timeline: aguardar conclusão INOVA antes de Sprint LGPD-5?

**Impacto no módulo LGPD:**
- Sprint LGPD-5: criar `VendorAssessment` com campos apropriados
- Integração: AC-13 vinculada a documentos de análise?

---

### B-03 — Política de Retenção (AC-24)

**Pergunta:** AC-24 (Política de Retenção de Dados) — é baseada na **planilha de Ciclo de Vida** (CART_98) que já existe? Existe um provimento do CNJ com as determinações e prazos de retenção, será anexado a nossa base de dados posteriormente.

**Contexto:**
- Ciclo de Vida já foi elaborado e publicado
- AC-24 está pendente (próximo passo é Política formal)
- Pergunta: reutilizar Ciclo de Vida ou elaborar política separada?

**Por que importa:**
1. Determina se AC-24 é "documentação" ou "mudança operacional"
2. Design do módulo: armazenar Ciclo de Vida como PolicyDocument?
3. Sprint LGPD-2: importar como uma das 14 políticas?

**Qual decisão depende:**
- Sprint LGPD-2: AC-24 tem documento próprio ou usa Ciclo de Vida?
- Relatórios: sincronizar com Ciclo de Vida?

**Impacto no módulo LGPD:**
- Sprint LGPD-2: incluir Ciclo de Vida como PolicyDocument se separado
- Sprint LGPD-6: ProcessingActivity vinculada a "retention_period" do Ciclo de Vida

---

### B-04 — Treinamento e Conscientização (AC-11)

**Pergunta:** AC-11 (Programa de Treinamento e Conscientização) — qual é o plano atual para **2026**? Já existe documento e cronograma de treinamentos para 2026.

**Contexto:**
- Plano de Ação menciona "cronograma de disponibilidades para 2023"
- Estamos em maio/2026; contexto é diferente
- AC-11 é crítica para CNJ 213 (capacitação documentada)

**Opções esperadas:**
1. Reciclagem anual obrigatória (todos os colaboradores)
2. Campanhas pontuais por departamento
3. Treinamento inicial + retraining periódico
4. INOVA fornecerá conteúdo?

**Por que importa:**
1. Determina frequência de `TrainingRecord`
2. Design do módulo: registrar planejado vs. executado?
3. Relatórios: "% colaboradores treinados" ou "horas de treinamento"?

**Qual decisão depende:**
- Sprint LGPD-2: TrainingRecord com campos apropriados
- Relatórios: formato esperado do relatório de capacitação

**Impacto no módulo LGPD:**
- Sprint LGPD-2: TrainingRecord com campos: training_name, date, participant, duration, certificate
- Sprint LGPD-3: relatório de capacitação mostrando % cobertura

---

### B-05 — Análises de Legítimo Interesse e RIPD (AC-22, AC-23)

**Pergunta:** AC-22 (Procedimento RIPD) e AC-23 (Procedimento LI) — há **templates prontos** que o módulo deve armazenar? Será verificado comunicado a serventia.

**Contexto:**
- Ambas as ações estão concluídas (procedimentos existem)
- Pergunta: são documentos que devem ser evidência em LgpdEvidence?
- Ou são procedimentos "vivos" que serão aplicados caso a caso?

**Por que importa:**
1. Se procedimentos "vivos": criar tabelas `RipdAssessment`, `LiAssessment` (futuro)
2. Se apenas templates: armazenar como PolicyDocument
3. Afeta Sprint LGPD-2 (políticas) vs. Sprint LGPD-5+ (assessments)

**Qual decisão depende:**
- Sprint LGPD-2: AC-22/23 como PolicyDocument ou esperar Sprint 5+?
- Futuro: necessidade de rastrear aplicação desses procedimentos?

**Impacto no módulo LGPD:**
- Sprint LGPD-2: incluir Proc. RIPD e Proc. LI como PolicyDocument (14 totais)
- Sprint LGPD-5+: criar `RipdRecord` e `LiAssessment` se necessário rastrear aplicação

---

## Grupo C — Operacionais (refinam execução)

Estas perguntas **podem** ser respondidas em paralelo. Úteis para documentação e treinamento.

---

### C-01 — Conformidade com CNJ 213

**Pergunta:** Ao elaborar o Plano de Ação LGPD, INOVA considerou os **requisitos técnicos** do Provimento CNJ nº 213/2026? Sim, todo o projeto é desenhado com base na Lei Geral de Proteção de Dados Pessoais (LGPD), nº 13.709/2018, e sob os pilares do provimento 74 e posteriormente o provimento 213 que o substituiu e atualizou.

**Contexto:**
- CNJ 213 tem 45+ requisitos técnicos (rede, backup, acesso, trilhas)
- Plano LGPD tem 25 ações (jurídicas/operacionais)
- Pergunta: há cobertura cruzada ou são roadmaps separados?

**Por que importa:**
1. Design do módulo: matriz de rastreabilidade (ação LGPD → requisito CNJ)
2. Relatórios de conformidade: integrar ambos os frameworks
3. Vistoria: demonstrar alinhamento LGPD + CNJ 213

**Qual decisão depende:**
- Sprint LGPD-3: matriz de conformidade (`lgpd_conformity_cnj213.csv`)

**Impacto no módulo LGPD:**
- Sprint LGPD-3: relatório de conformidade integra LGPD + CNJ 213

---

### C-02 — Evidências Esperadas para Vistoria

**Pergunta:** Para o vistoriador CNJ, qual é o **nível de detalhe** e **formato** esperado das evidências? Relatórios: principalmente relatórios + algumas evidências de suporte

**Contexto:**
- Vistoria acontecerá em breve (±agosto/2026)
- Preciso saber: vistoriador quer ver arquivo original ou apenas hash + metadados?
- Documentação jurídica vs. técnica: qual é a proporção esperada?

**Opções esperadas:**
1. Dossiê físico: todos os documentos originais + índice com hashes
2. Dossiê eletrônico: links para documentos + hashes verificáveis
3. Amostra: evidência de alguns itens; resto por amostragem
4. Relatórios: principalmente relatórios + algumas evidências de suporte

**Por que importa:**
1. Design da estrutura `_VISTORIA/`: organização de pasta
2. Módulo LGPD: qual é o minimal viável para evidência?
3. Integração com Audit: formatação de dossiê

**Qual decisão depende:**
- Sprint LGPD-2: padrão de armazenamento em `_VISTORIA/`
- Sprint LGPD-7: consolidação do dossiê integrado (Audit + LGPD)

**Impacto no módulo LGPD:**
- Sprint LGPD-2: estrutura `_VISTORIA/01_Evidencias_LGPD/` otimizada para vistoria
- Sprint LGPD-3: geração de índice pronto para dossiê

---

### C-03 — Qual Parte Executa Cada Ação

**Pergunta:** Das 25 ações, qual é a **divisão de trabalho** esperada entre:
- INOVA LGPD - assessoria juridica, treinamentos, modelos de documentos, analise de fornecedores
- Cartório (gestor, TI, RH, jurídico) - implementação das politicas e procedimentos, organização de relatórios de situação e informações específicas da serventia
- Terceiros externos - como engegraph - suporte ao sistema de automação da serventia, suporte de TI basico do servidor. JAG - assessoria de contabilidade. APRESEG - assessoria de segurança do trabalho.

**Contexto:**
- Plano lista "Responsável Executante" mas pode haver detalhe insuficiente
- Exemplo: AC-12 (Análise de Contratos) — INOVA analisa; Cartório negocia aditivos?
- Exemplo: AC-13 (Fornecedores) — quem avalia?

**Por que importa:**
1. Accountability clara
2. Timing: quem precisa fazer o quê, quando
3. Módulo LGPD: rastrear "aguardando ação de INOVA" vs. "ação local"

**Qual decisão depende:**
- Sprint LGPD-1: campo `assigned_to_entity` (internal, inova, hybrid)?
- Relatórios: breakdown por responsável?

**Impacto no módulo LGPD:**
- Sprint LGPD-1: LgpdAction com campo `responsible_entity` se necessário
- Sprint LGPD-3: relatório separando "ações Cartório" vs. "ações INOVA"

---

### C-04 — Integração Futura: O que Esperar do Atlas

**Pergunta:** Há **orientações preliminares** sobre o que o Atlas (se existir) esperaria receber do Cartório System? Será avaliado depois.

**Contexto:**
- Atlas é futuro (fora do escopo LGPD-0 a LGPD-3)
- Mas é útil saber agora se há expectativas
- Exemplo: relatórios estruturados em JSON? Métricas de conformidade?

**Por que importa:**
1. Design de exports: qual formato é mais útil?
2. Independência: Cartório System deve ser autossuficiente (não depender de Atlas)
3. Integração futura: se Atlas tiver requisitos, já preparar data models

**Qual decisão depende:**
- Sprint LGPD-3: formato de `exports/lgpd/summary_for_atlas.json`

**Impacto no módulo LGPD:**
- Sprint LGPD-3: relatório pronto para exportação para Atlas (futuro)

---

## Modelo de Resposta Esperada

Idealmente, INOVA responderia com:

```markdown
## Resposta INOVA LGPD

### A-01 — DPO
Sim, é obrigatório nomear DPO. Critério: serventia com ≥20 colaboradores OU processamento em escala.
Cartório Costa Teixeira atende critério (≥20 colaboradores).
Recomendação: Nomear até 30/06/2026.

### A-02 — Base Legal
As 2 atividades são: [atividade X] e [atividade Y].
Situação: Precisam ser reclassificadas sob legítimo interesse (análise em andamento).
ETA: 15/05/2026.

### A-03 — Integração INOVA
Erro é de configuração de API key. Suporte INOVA está resolvendo.
ETA: 20/05/2026. Cartório deve aguardar suporte contato.

...

### C-01 — Conformidade CNJ
Sim, Plano LGPD foi alinhado com CNJ 213.
Mapeamento incluído em [arquivo X].

...
```

---

---

## Status das Respostas Recebidas

**Data de Atualização:** 2026-05-05  
**Respostas Consolidadas:** 14 perguntas (9 claras, 5 vagas)

### Resumo por Grupo

#### Grupo A — Críticas

| Pergunta | Resposta | Status | Clareza |
| --- | --- | --- | --- |
| **A-01 DPO** | "INOVA foi contratada como DPO as a service da serventia" | ✅ Respondida | ⚠️ Parcial |
| **A-02 Base Legal** | "Teremos que revisar junto a gestão da serventia" | ⏳ Pendente | ❌ Vaga |
| **A-03 Integração INOVA** | "Será investigado e informado posteriormente" | ⏳ Pendente | ❌ Vaga |
| **A-04 Consentimento** | "Termo de ciência, os termos já foram assinados pelos colaboradores" | ✅ Respondida | ✅ Clara |
| **A-05 Plano Resposta** | "Será verificado com a equipe de assessoria" | ⏳ Pendente | ❌ Vaga |

#### Grupo B — Importantes

| Pergunta | Resposta | Status | Clareza |
| --- | --- | --- | --- |
| **B-01 Responsáveis** | "Todas as entregas são de responsabilidade do cartório para prosseguir com o projeto de adequação" | ✅ Respondida | ✅ Clara |
| **B-02 Fornecedores** | "Avaliação de fornecedores é feita pela Inova... revisar os contratos e solicitar nova auditoria" | ✅ Respondida | ✅ Clara |
| **B-03 Retenção** | "Existe um provimento do CNJ com as determinações... será anexado a nossa base de dados posteriormente" | ✅ Respondida | ✅ Clara |
| **B-04 Treinamento** | "Já existe documento e cronograma de treinamentos para 2026" | ✅ Respondida | ✅ Clara |
| **B-05 RIPD/LI** | "Será verificado comunicado a serventia" | ⏳ Pendente | ⚠️ Vaga |

#### Grupo C — Operacionais

| Pergunta | Resposta | Status | Clareza |
| --- | --- | --- | --- |
| **C-01 CNJ 213** | "Sim, todo o projeto é desenhado com base na LGPD... e sob os pilares do Provimento 213" | ✅ Respondida | ✅ Clara |
| **C-02 Evidências** | "Relatórios: principalmente relatórios + algumas evidências de suporte" | ✅ Respondida | ✅ Clara |
| **C-03 Divisão Trabalho** | Detalhado: INOVA (assessoria, modelos), Cartório (implementação), Terceiros (suporte) | ✅ Respondida | ✅ Clara |
| **C-04 Atlas** | "Será avaliado depois" | ⏳ Pendente | ⚠️ Vaga |

### Impacto no MVP

**Resultado da análise:** ✅ **Nenhuma alteração no escopo da Sprint LGPD-1**

- Respostas claras consolidam design MVP (DPO, Consentimento, Responsáveis, Fornecedores)
- Respostas vagas confirmam abordagem standalone (Integração INOVA fora MVP)
- Nenhuma funcionalidade entra ou sai da LGPD-1

**Recomendação:** ✅ **Proceeder com LGPD-1 conforme planejado**

---

## Perguntas de Follow-up (F-01 a F-03)

Estas 3 perguntas refinam respostas vagas recebidas em A-01, A-02 e B-05. Devem ser enviadas à INOVA dentro de 48h.

---

### F-01 — Nomeação do DPO / AC-15 e AC-16

**Pergunta:** A INOVA já foi contratada como DPO as a service. Para considerar AC-15 (Nomeação do DPO) e AC-16 (Divulgação do DPO no site) **concluídas**, basta registrar formalmente essa contratação ou o **Cartório ainda precisa executar alguma ação operacional**, como publicar os dados do DPO (nome, email, contato) no site ou canal oficial?

**Por que importa:**
1. Define status final de AC-15 e AC-16 (concluídas vs. em progresso)
2. Determina se há evidência a registrar em LgpdEvidence
3. Afeta timeline de conclusão do Plano de Ação

**Qual decisão depende:**
- Validação de AC-15 e AC-16 em Sprint LGPD-1
- Marcação de status: "Concluída" ou "Em Progresso"

**Impacto no módulo LGPD:**
- ✅ Não altera escopo da LGPD-1
- ⏳ Afeta apenas registro de evidência (AC-15/16 como ações do Plano)

---

### F-02 — Identificação das 2 Atividades sem Base Legal

**Pergunta:** Em A-02, respondeu-se "Teremos que revisar junto a gestão da serventia". Por favor, **identifique quais são as 2 atividades de tratamento** indicadas com "ausência de base legal" (segundo dashboard INOVA) **e qual é o prazo recomendado** para revisão/reclassificação? Há base legal a ser adicionada ou estas atividades precisam ser removidas?

**Por que importa:**
1. Identifica risco jurídico-operacional crítico
2. Permite planejamento de ação correctiva
3. Necessário para relatório de conformidade (não podemos afirmar "100% conforme" enquanto houver atividades sem base legal)

**Qual decisão depende:**
- Priorização de ação: Quando revisar?
- Design de ProcessingActivity: Incluir campo legal_basis_status?

**Impacto no módulo LGPD:**
- ✅ Não altera escopo da LGPD-1
- ⏳ Impacta futura modelagem de ProcessingActivity (Sprint LGPD-6)
- ⏳ Pode afetar relatório de conformidade (Sprint LGPD-3)

---

### F-03 — Natureza de AC-22 (RIPD) e AC-23 (Legítimo Interesse)

**Pergunta:** Os documentos **AC-22 (Procedimento para Elaboração do RIPD)** e **AC-23 (Procedimento para Análise de Legítimo Interesse)** devem ser tratados como:

**Opção A:** Templates/políticas documentais a armazenar como `PolicyDocument` (entidade única, estática) — neste caso, importaríamos em Sprint LGPD-2 junto às outras 14 políticas.

**Opção B:** Procedimentos vivos a serem aplicados caso a caso por diferentes departamentos — neste caso, esperaríamos entidades próprias futuras (`RipdRecord`, `LegitimateInterestAssessment`) a partir de Sprint LGPD-5+.

**Por que importa:**
1. Define se AC-22/23 entram no MVP ou em futuro
2. Afeta design do modelo de domínio
3. Impacta timeline de Sprint LGPD-2 vs. Sprint LGPD-5+

**Qual decisão depende:**
- Sprint LGPD-2: Incluir AC-22/23 como PolicyDocument (políticas estáticas)?
- Sprint LGPD-5+: Criar RipdRecord/LegitimateInterestAssessment (procedimentos vivos)?

**Impacto no módulo LGPD:**
- ✅ Não altera escopo da LGPD-1
- ⏳ Define tratamento em Sprint LGPD-2 (políticas) vs. Sprint LGPD-5+ (assessments)

---

## Próximas Ações

1. **Hoje (2026-05-05):** ✅ Consolidar respostas INOVA recebidas (conclusão desta seção)
2. **Próximas 48h:** ⏳ Enviar perguntas de follow-up F-01, F-02, F-03 para INOVA
3. **Até 2026-05-12:** ⏳ Coletar respostas aos follow-ups
4. **2026-05-15:** ⏳ Reunião João + INOVA + Engenharia (decisão final sobre timing)
5. **A partir de 2026-05-20:** ⏳ Fase 1 (preparação) → Sprint LGPD-1 (implementação)

---

**Preparado por:** Claude Code  
**Data:** 2026-05-05  
**Versão:** 1.1 (Com Status das Respostas)  
**Destinatário:** INOVA LGPD + Time Técnico  
**Próximo Prazo de Resposta:** 2026-05-12 (follow-ups F-01, F-02, F-03)
