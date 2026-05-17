# AI-LEGAL-0 — Investigação sobre Ferramentas Jurídicas Claude e Aplicação ao Cartório System

> **Aviso:** Este documento é um relatório de investigação técnica e não constitui
> declaração de conformidade regulatória. Recomendações aqui apresentadas são sujeitas
> a validação humana antes de qualquer implementação. Nenhuma ação de IA deve ser
> executada em produção sem as salvaguardas descritas neste documento.
>
> Produzido em: 2026-05-16  
> Sprint: AI-LEGAL-0 (investigação — sem código implementado)  
> Status: Entregue para revisão e decisão humana

---

## 1. Sumário Executivo

Em maio de 2026, a Anthropic lançou formalmente 12 plugins de prática jurídica e
mais de 20 conectores MCP, consolidando sua entrada no mercado jurídico. Essas
ferramentas são relevantes, sofisticadas e endereçam casos de uso de Big Law e
departamentos jurídicos corporativos — mas **não foram projetadas para cartórios
brasileiros**, nem para o contexto regulatório do CNJ 213/2026.

A aplicação ao Cartório System exige adaptação cuidadosa, governança rigorosa e
implementação incremental. A hipótese inicial analisada — começar com base normativa
interna e AI Gateway controlado antes de MCP e agentes avançados — é **válida e
recomendada**, com os ajustes descritos neste documento.

**Conclusão central:** O Cartório System deve iniciar pela organização normativa
sem IA (Fase 1), avançar para um AI Gateway controlado com prompts versionados
e revisão humana (Fase 2), e só considerar MCP e agentes autônomos após maturidade
de governança, logs, base documental e redaction. O risco principal não é técnico:
é o uso de IA gerando parecer indevido, violando sigilo ou provocando confusão entre
rascunho e decisão oficial.

---

## 2. Objetivo da Investigação

Avaliar se e como as ferramentas de IA da Anthropic/Claude — especialmente as
voltadas ao setor jurídico — podem ser aplicadas ao Cartório System, e produzir
um plano arquitetural para a futura camada de inteligência normativa do sistema.

Esta sprint **não implementa código**, não modifica banco de dados, não conecta
APIs reais e não expõe dados sensíveis. É exclusivamente documental e decisional.

---

## 3. Fontes Consultadas

### 3.1 Fontes Internas

| Arquivo | Conteúdo analisado |
|---------|-------------------|
| [CLAUDE.md](../../CLAUDE.md) | Regras operacionais, proibições permanentes, fluxo de trabalho |
| [docs/roadmap.md](../roadmap.md) | Roadmap técnico geral e estado das sprints |
| [docs/regulatory/cnj_213/roadmap.md](../regulatory/cnj_213/roadmap.md) | Roadmap de adequação CNJ 213/2026 Classe 3 |
| [docs/regulatory/cnj_213/alignment.md](../regulatory/cnj_213/alignment.md) | Alinhamento do módulo de auditoria com o Provimento |
| [docs/regulatory/cnj_213/regulatory_integration_blueprint.md](../regulatory/cnj_213/regulatory_integration_blueprint.md) | Blueprint de integração dos módulos regulatórios |
| [docs/modules/compliance.md](../modules/compliance.md) | Módulo de compliance: sprints, entidades, endpoints |
| [docs/decisions/ADR-001-compliance-evidence-ownership.md](../decisions/ADR-001-compliance-evidence-ownership.md) | Decisão sobre ownership de evidências regulatórias |
| [docs/decisions/ADR-002-weak-references-between-regulatory-modules.md](../decisions/ADR-002-weak-references-between-regulatory-modules.md) | Decisão sobre referências fracas entre módulos |
| [docs/architecture.md](../architecture.md) | Stack, estrutura de diretórios, princípios de design |
| Memory Index do projeto | Contexto histórico das sprints e decisões passadas |

### 3.2 Fontes Externas

| Fonte | URL | Tipo | Status |
|-------|-----|------|--------|
| Anthropic — Claude for Legal Deployment Guide | https://www-cdn.anthropic.com/files/4zrzovbb/website/4b29cc317c727542642b5056e412cf8e779e13d8.pdf | Oficial | Consultado (PDF) |
| Anthropic — Introducing Agent Skills | https://www.anthropic.com/news/skills | Oficial | Consultado |
| Anthropic — Introducing Model Context Protocol | https://www.anthropic.com/news/model-context-protocol | Oficial | Consultado |
| Anthropic — Connectors Directory | https://claude.com/partners/mcp | Oficial | Consultado |
| Anthropic — MCP Connector API Docs | https://docs.anthropic.com/de/docs/agents-and-tools/mcp-connector | Oficial | Consultado (completo) |
| GitHub — claude-for-legal README | https://github.com/anthropics/claude-for-legal | Oficial | Consultado |
| Anthropic Privacy Center — ZDR | https://privacy.anthropic.com/en/articles/8956058-i-have-a-zero-retention-agreement-with-anthropic-what-products-does-it-apply-to | Oficial | Consultado |
| Anthropic Privacy Center — Enterprise Retention | https://privacy.anthropic.com/en/articles/10440198-custom-data-retention-controls-for-claude-enterprise | Oficial | Consultado |
| LawSites/LawNext — Anthropic Goes All-In on Legal | https://www.lawnext.com/2026/05/anthropic-goes-all-in-on-legal-releasing-more-than-20-connectors-and-12-practice-area-plugins-for-claude.html | Secundária | Consultado — não usar como base central de decisão técnica |
| Stanford — Legal RAG Hallucinations (2025) | https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf | Acadêmica | Referenciado |
| National Center for State Courts — AI & Hallucinations | https://www.ncsc.org/resources-courts/legal-practitioners-guide-ai-hallucinations | Acadêmica | Referenciado |
| IBA — AI-generated evidence: The Brazilian landscape | https://www.ibanet.org/AI-generated-evidence-Brazil | Secundária | Referenciado — contexto brasileiro, não usar como base jurídica primária |
| CNJ — Resolução 615/2025 | Fonte específica pendente de confirmação | Oficial (pendente) | Referenciado — URL oficial específica não localizada; não usar como fundamento central sem confirmação |

> **Nota sobre fontes:** Fontes secundárias e acadêmicas (LawNext, IBA, Stanford, NCSC) foram usadas como contexto e suporte. Decisões técnicas e de governança baseiam-se prioritariamente em fontes oficiais da Anthropic. A Resolução CNJ 615/2025 é mencionada como contexto regulatório, mas a URL exata do ato normativo não foi confirmada — verificar no Portal CNJ antes de usar como fundamento formal.

---

## 4. O que a Anthropic/Claude lançou para o setor jurídico

### 4.1 Contexto do lançamento (maio 2026)

Em maio de 2026, a Anthropic realizou seu maior movimento no mercado jurídico até
então, anunciando simultaneamente:

- **12 plugins de prática jurídica** específicos por área de atuação
- **Mais de 20 conectores MCP** para os sistemas que escritórios e departamentos
  jurídicos já utilizam
- Um **guia de deployment prático** para equipes jurídicas ("Claude for the Legal
  Industry: A Practical Deployment Guide")
- Um **repositório open source** (`anthropics/claude-for-legal` no GitHub)
  com código, skills, agentes e hooks para as 12 práticas
- Uma linha de **acesso subsidiado** para organizações de acesso à justiça, clínicas
  jurídicas e defensores públicos

Segundo pesquisa FTI Consulting/Relativity (2026), 87% dos General Counsels reportam
uso de IA generativa em seus times — comparado a 44% no ano anterior.

### 4.2 Os 12 plugins de prática jurídica

| Plugin | Área de atuação |
|--------|----------------|
| `commercial-legal` | Revisão de MSAs, NDAs, SaaS; renovações; escalações |
| `corporate-legal` | M&A diligence, closing checklists, board consents, entity compliance |
| `employment-legal` | Revisão de contratação/rescisão, classificação de trabalhadores, investigações |
| `privacy-legal` | Revisão de DPAs, resposta a DSARs, geração de PIAs, triagem de privacidade |
| `product-legal` | Revisão de lançamentos, verificação de claims de marketing, avaliação de features |
| `regulatory-legal` | Monitoramento regulatório, diff de políticas, tracking de gaps |
| `ai-governance-legal` | Triagem de casos de uso de IA, impact assessments, revisão de fornecedores |
| `ip-legal` | Clearance de marca, FTO triage, drafting de C&Ds, DMCA, claims de patente |
| `litigation-legal` | Gestão de matter, demandas, prep de depoimento, claim charts |
| `legal-clinic` | Intake de clientes, tracking de prazos, scaffolds de memos |
| `law-student` | Drilling socrático, grading IRAC, prep para bar exam |
| `legal-builder-hub` | Descoberta e instalação de skills com trust gates |

**Observação crítica:** Nenhum desses plugins foi projetado para cartórios brasileiros,
Registros de Imóveis, o sistema do CNJ, o Provimento 213/2026 ou a estrutura
extrajudicial brasileira. São ferramentas voltadas para Big Law americano e
departamentos jurídicos corporativos anglo-saxões.

### 4.3 Os 20+ conectores MCP para uso jurídico

| Categoria | Conectores |
|-----------|-----------|
| Pesquisa jurídica | CourtListener, Trellis, Descrybe, CoCounsel (Thomson Reuters), Midpage, Legal Data Hunter |
| CLM/DMS | Ironclad, iManage, NetDocuments, DocuSign |
| E-discovery | Relativity, Everlaw, Consilio/Aurora |
| Data rooms | Box, Datasite |
| IA jurídica | Harvey, Solve Intelligence (patentes) |
| Produtividade | Slack, Google Drive, Linear, Jira, Asana |

**Observação:** Nenhum dos conectores integra com Engegraph, ONR, e-Notariado,
sistemas CNJ, SREI, IERI, SIG-RI ou qualquer sistema específico brasileiro.

### 4.4 Princípios do claude-for-legal (relevantes para governança)

O repositório oficial declara explicitamente:

> "All outputs are drafts for attorney review, not legal advice. Every tool
> includes guardrails reflecting this (source attribution, conservative defaults
> on privilege, explicit gates before filing)."

E ainda:

> "The lawyer using the plugin — not the plugin and not Anthropic — takes
> professional responsibility for the work product."

Esses princípios são diretamente aplicáveis ao Cartório System: qualquer saída
de IA deve ser rascunho sujeito a revisão humana. O responsável pelo ato é o
tabelião ou registrador — não o sistema.

---

## 5. Conceitos Técnicos Fundamentais

### 5.1 Claude Legal Plugins

**O que são:** Plugins são pacotes de skills, agentes, hooks e um perfil de prática
(`CLAUDE.md`) que especializam o Claude em uma área jurídica específica. Cada
plugin inclui:
- Skills (arquivos `.md` com metodologias, checklists e instruções de domínio)
- Agentes (workflows agendados ou orientados a evento)
- Hooks (pré/pós-processamento de chamadas de ferramentas)
- Perfil de prática (plain English com playbooks específicos da organização)

**Como funcionam:** O plugin realiza uma "cold-start interview" — uma entrevista
de configuração inicial (10-20 min) que aprende os playbooks, práticas, estilo
e escalações da equipe. Todas as skills subsequentes leem esse perfil.

**Plataformas:** Claude Cowork (visual), Claude Code (CLI), Managed Agents API
(headless/automação).

**Limitações:**
- Não fornecem aconselhamento jurídico nem conclusões legais
- Não substituem revisão de advogado
- Sem verificação de citações sem conector de pesquisa (marcadas `[verify]`)
- Não executam ações críticas (filing, envio) sem aprovação explícita
- Não foram projetados para cartórios brasileiros

**Disponibilidade:** Repositório open source no GitHub (`anthropics/claude-for-legal`).
A disponibilidade concreta em cada ambiente, plano ou produto da Anthropic (Claude Code,
Claude Cowork, API, Pro, Max, Team, Enterprise) pode variar conforme plano contratado,
configuração beta, região e termos vigentes. Antes de qualquer implementação, confirmar
disponibilidade em documentação oficial atualizada e/ou contrato aplicável.

### 5.2 Claude Skills

**O que são:** Agent Skills são pastas organizadas contendo instruções, scripts e
recursos que o Claude pode descobrir e carregar dinamicamente para realizar tarefas
especializadas. Uma skill é essencialmente um diretório com um arquivo `SKILL.md`
que descreve as capacidades e instruções.

**Como funcionam:**
- O Claude escaneia as skills disponíveis e identifica quais são relevantes
- Apenas as informações mínimas necessárias são carregadas quando precisas
- Multiple skills trabalham juntas (composabilidade)
- São portáveis entre plataformas Claude

**Quem pode criar:**
- Usuários de planos Claude que suportem essa funcionalidade (a disponibilidade exata por
  plano — Pro, Max, Team, Enterprise — pode variar; confirmar na documentação oficial)
- Desenvolvedores via API
- Existe uma "skill-creator" skill que guia o processo de criação

**Distribuição:**
- Claude apps diretamente (conforme suporte do plano)
- Claude Developer Platform
- Claude Code via marketplace `anthropics/skills`
- Diretório de skills de parceiros

> **Aviso de disponibilidade:** A disponibilidade concreta de criação e uso de skills
> por plano, ambiente (Claude Code, Claude Web, API) e região pode variar conforme
> configuração, beta e termos vigentes da Anthropic. Confirmar antes de implementar.

**Para o Cartório System:** Skills internas são a forma mais simples e controlável
de implementar conhecimento normativo. É possível criar skills específicas para
o Provimento CNJ 213/2026, CNPFE-GO, Provimento 50/2015, InovaLGPD, etc.

### 5.3 MCP — Model Context Protocol

**O que é:** O Model Context Protocol (MCP) é um protocolo aberto — agora doado
ao Agentic AI Foundation (AAIF) sob a Linux Foundation — que padroniza a forma como
aplicações de IA se conectam a sistemas externos de dados e ferramentas.

**Analogia:** MCP é para IA o que USB-C é para periféricos — um conector
padronizado que permite conectar qualquer cliente a qualquer servidor sem
configuração ad-hoc.

**Arquitetura:**
- **MCP Server**: expõe ferramentas (tools), recursos (resources) e prompts
- **MCP Client**: consome o servidor (pode ser Claude, Claude Code, ou qualquer app)
- **Transport**: HTTP/SSE (remoto) ou stdio (local)

**Estado atual:** Mais de 75 conectores no diretório oficial; 97 milhões de
downloads mensais de SDK (Python e TypeScript).

**Para o Cartório System:** O MCP permitiria criar um servidor próprio que expõe
os dados normativos do sistema para o Claude consultar de forma estruturada. É uma
evolução futura — requer maturidade de infraestrutura e governança.

### 5.4 MCP Connectors

**O que são:** Conectores MCP são implementações prontas do protocolo MCP para
sistemas específicos (Google Drive, Slack, iManage, etc.), disponíveis no diretório
de parceiros da Anthropic. Diferente de criar um servidor MCP próprio, os conectores
são terceirizados e apenas configurados.

**Status técnico (documentação oficial):**
- Requerem o beta header `"anthropic-beta": "mcp-client-2025-11-20"`
- Suportam apenas Tool Calls (não prompts ou recursos MCP)
- O servidor MCP deve ser publicamente acessível via HTTP (não stdio local)
- **Não são elegíveis para Zero Data Retention (ZDR)**
- Dados trafegados via MCP Connector são retidos conforme política padrão da Anthropic

**Limitação crítica para cartórios:** O MCP Connector envia dados para a Anthropic
durante o processamento. Isso cria risco de LGPD e sigilo profissional se dados
sensíveis forem incluídos nos prompts/contexto.

### 5.5 Integração via API

**O que é:** Integração direta com a Anthropic API (REST/SDK), sem MCP, sem plugins.
O sistema envia prompts estruturados e recebe respostas, implementando toda a lógica
de contexto, redaction e governança localmente.

**Vantagens:**
- Controle total sobre o que é enviado à Anthropic
- Permite implementar redaction antes de qualquer chamada
- Mais simples de auditar
- Sem dependência de beta features

**Desvantagens:**
- Requer implementação de toda a orquestração no lado do cliente
- Sem ferramentas de descoberta dinâmica de tools
- Maior esforço de manutenção

**Para o Cartório System:** A integração via API direta é o ponto de entrada mais
seguro e controlável. É o que deve ser implementado no AI Gateway (Fase 2).

### 5.6 RAG / Knowledge Base Interna

**O que é:** Retrieval Augmented Generation (RAG) é uma técnica que recupera
informações relevantes de uma base de conhecimento e as inclui no contexto antes
de enviar ao modelo. Resulta em respostas mais precisas, com citações verificáveis.

**Como funciona:**
1. Documentos são indexados e transformados em embeddings
2. Na consulta, o sistema recupera os trechos mais relevantes
3. Os trechos são inseridos no prompt junto à pergunta
4. O modelo responde com base no contexto fornecido (com citações)

**Técnica de Contextual Retrieval (Anthropic, 2026):** Combina embeddings semânticos
com BM25 (busca por palavras-chave), reduzindo falhas de recuperação em 49% e, com
reranking, em 67%.

**Para o Cartório System:** A base normativa interna (Provimento 213, CNPFE-GO,
Provimento 50/2015, políticas InovaLGPD) é candidata natural a uma knowledge base
para RAG. A vantagem é que os documentos são normativos — sem PII, sem dados
operacionais — e podem ser indexados com menor risco regulatório.

### 5.7 Diferenças práticas entre plugin, skill, MCP, agente e RAG

| Conceito | O que é | Quem controla | Onde roda | Dados enviados à Anthropic | Complexidade |
|----------|---------|---------------|-----------|---------------------------|--------------|
| **Plugin** | Pacote de skills + agentes + hooks especializados | Criador do plugin + Anthropic | Claude Code / Cowork / API | Prompts e contexto | Alta |
| **Skill** | Arquivo SKILL.md com instruções de domínio | Criador da skill | Claude Code / Apps | Prompts e contexto | Baixa |
| **MCP Connector** | Integração pronta com sistema externo via MCP | Parceiro / Anthropic | Remoto (HTTP) | Tudo — sem ZDR | Alta |
| **MCP Server próprio** | Servidor MCP implementado pelo projeto | O próprio sistema | Local ou cloud própria | Apenas o que o servidor expõe | Alta |
| **Agente** | Workflow autônomo com múltiplos passos e ferramentas | Desenvolvedor | API / Managed Agents | Prompts e resultados intermediários | Muito Alta |
| **RAG** | Retrieval de documentos + geração com citações | Desenvolvedor | Local + API | Apenas trechos relevantes (sem PII se bem implementado) | Média |
| **Integração via API** | Chamadas REST diretas ao Claude | Desenvolvedor | Local | Apenas o que o código envia (redaction possível) | Média |

---

## 6. Aderência ao Contexto do Cartório Costa Teixeira

### 6.1 O que é específico do contexto

O Cartório Costa Teixeira é uma **serventia extrajudicial de Registro de Imóveis**,
classificada como **Classe 3** pelo Provimento CNJ nº 213/2026. Isso implica:

- **Prazo de adequação:** 24 meses a partir da publicação do Provimento
- **RPO máximo:** 4 horas
- **RTO máximo:** 8 horas
- **Contexto regulatório:** CNJ, TJGO, CNPFE-GO, Provimento 50/2015, LGPD
- **Dado sensível:** matrículas, documentos com CPFs, valores de emolumentos,
  atos de registro, georreferenciamento rural (INCRA)
- **Sigilo profissional:** os atos praticados pelo registrador têm natureza
  pública (registros são públicos), mas dados pessoais envolvidos são protegidos
  pela LGPD

### 6.2 O que os plugins da Anthropic NÃO cobrem

- Nenhum plugin foi desenvolvido para cartórios brasileiros
- Nenhum conector integra com ONR, e-Notariado, SREI, IERI, SIG-RI, Engegraph
- Nenhum plugin conhece o Provimento 213/2026, CNPFE-GO ou o Código de Normas de Goiás
- Nenhum plugin entende a estrutura de Registro de Imóveis brasileiro (matrículas,
  atos, folhas, livros, protocolos)
- Os plugins americanos operam sob common law — inaplicável à estrutura cartorária brasileira

### 6.3 O que pode ser aproveitado

- **Princípio de governança:** outputs sempre como rascunhos sujeitos a revisão humana
- **Estrutura de skills:** formato portável, composável e versionável — adaptável
  para normativas brasileiras
- **RAG com citações:** técnica aplicável à base normativa interna
- **MCP como padrão de integração futuro:** quando o sistema for maduro o suficiente
- **AI Gateway pattern:** camada intermediária que controla o que é enviado ao modelo
- **Prompt registry versionado:** boa prática independente de plataforma

---

## 7. Aderência ao Cartório System

### 7.1 O que o Cartório System já tem que se relaciona com inteligência normativa

| Módulo existente | Relação com inteligência futura |
|-----------------|--------------------------------|
| `compliance` — Matriz INOVA V1 | Base normativa já estruturada em dados; candidata natural a knowledge base |
| `compliance` — ComplianceEvidence | Evidências regulatórias que poderiam ser geradas com apoio de IA |
| `compliance` — ComplianceRequirementStatus | Status indicativo que poderia ser explicado em linguagem natural |
| `audit` — AuditFinding | Achados que poderiam ser correlacionados com requisitos por IA |
| `audit` — DocumentDiagnosis | Diagnósticos que poderiam ser narrados automaticamente |
| `retention` — RetentionRule | Regras do Provimento 50/2015 já em estrutura consultável |
| `lgpd` — LgpdAction | Ações que poderiam ser priorizadas com apoio de IA |

### 7.2 O que ainda não existe e seria necessário

- Nenhuma camada de IA foi implementada
- Não existe redaction de dados sensíveis
- Não existe prompt registry
- Não existe log de chamadas a APIs externas de IA
- Não existe feature flag para habilitar/desabilitar IA
- Não existe modo dry-run para IA
- Não existe separação formal entre dados normativos (seguros) e dados operacionais (sensíveis)

### 7.3 Princípios existentes que protegem a implementação futura

A arquitetura atual do Cartório System já implementa princípios que facilitam
uma integração de IA segura:

- **Módulos independentes com referências fracas:** uma camada de IA pode ser
  adicionada como novo módulo sem modificar os existentes
- **Linguagem conservadora obrigatória:** padrão já estabelecido — aplicável a
  outputs de IA
- **Nunca declara conformidade automaticamente:** princípio crítico, aplicável a
  qualquer resposta de IA no contexto regulatório
- **Revisão humana como etapa obrigatória:** padrão de workflow já existente
- **Módulos read-only first:** padrão que se aplica à camada de IA inicialmente

---

## 8. Oportunidades de Uso

### 8.1 Análise de conformidade CNJ 213

**Oportunidade:** O módulo `compliance` já tem 32 requisitos, 30 políticas e
75 vínculos da Matriz INOVA V1. Uma camada de IA poderia:
- Explicar cada requisito em linguagem simples para o gestor
- Sugerir próximas evidências a coletar
- Gerar rascunhos de justificativas para status de cada requisito
- Narrar o gap atual entre evidências disponíveis e requisitos pendentes

**Risco:** IA não pode declarar conformidade nem substituir validação jurídica.

**Nível de risco dos dados:** Baixo — dados normativos da matriz são públicos;
os metadados de evidências (sem arquivos binários) são internos mas não contêm PII.

### 8.2 Dossiê técnico de evidências

**Oportunidade:** Geração assistida de narrativas para o dossiê técnico da
vistoria da corregedoria (Fase 10 do módulo de auditoria). A IA poderia
organizar e sumarizar os artefatos do scanner, diagnóstico e achados.

**Risco:** Rascunho gerado por IA não pode ser submetido sem revisão. O tabelião
assina e é responsável pelo conteúdo.

**Nível de risco dos dados:** Médio — inventários de arquivos podem conter nomes
de caminhos reveladores. Redaction necessária antes de enviar ao modelo.

### 8.3 Minutas de resposta à Corregedoria / PROAD

**Oportunidade:** Com a base de evidências estruturadas e o contexto do PROAD
(prazo ~10/06/2026), a IA poderia gerar rascunhos de manifestação usando os
documentos em `docs/proad/resposta_ieri_2026/` como contexto.

**Risco:** Alto. Documentos do PROAD podem conter informações processuais sensíveis.
Apenas versões anonimizadas ou normativas devem ser enviadas ao modelo.

**Nível de risco dos dados:** Alto — requer redaction rigorosa antes do uso.

### 8.4 Apoio à LGPD e PSI

**Oportunidade:** Geração de rascunhos de políticas, análise de gaps entre políticas
InovaLGPD e implementação atual, orientação sobre mapeamento de dados pessoais.

**Risco:** Médio. Políticas da InovaLGPD são documentos normativos (não PII).
A análise de gaps pode revelar ausências — que são informação interna sensível.

**Nível de risco dos dados:** Médio.

### 8.5 Retenção documental — Provimento 50/2015

**Oportunidade:** Explicação das regras de retenção em linguagem simples para
colaboradores, geração de alertas sobre documentos próximos do prazo de descarte.
O módulo `retention` já possui as 24 regras do Provimento em estrutura consultável.

**Risco:** Baixo para consulta de regras. Alto se IA emitir recomendação de
descarte sem supervisão humana. **Toda decisão de descarte é humana — sem exceções.**

**Nível de risco dos dados:** Baixo (regras normativas) a Alto (decisão de descarte).

### 8.6 Organização documental e auditoria interna

**Oportunidade:** Análise do inventário de arquivos (`file_inventory.json`) para
identificar padrões problemáticos, sugerir nomenclatura padronizada, detectar
prováveis duplicatas. Complementa a Sprint 3 do módulo de auditoria (DocumentDiagnosis).

**Risco:** O inventário contém nomes de arquivos e caminhos — potencialmente
reveladores de processos internos. Redaction de caminhos absolutos necessária.

**Nível de risco dos dados:** Médio.

### 8.7 Apoio a matrículas rurais e Registro de Imóveis

**Oportunidade:** Consulta sobre regras do CNPFE-GO para tipos específicos de
atos de registro; verificação de requisitos para georreferenciamento rural (INCRA);
orientação sobre o pipeline IERI/SIG-RI.

**Risco:** Alto. Dados de matrícula envolvem CPF, valores de imóveis, dados de
proprietários — PII stricto sensu. **Fase inicial não deve incluir dados de matrícula real.**

**Nível de risco dos dados:** Alto. Apenas base normativa (CNPFE-GO, Leis,
Provimentos) pode ser usada nesta fase.

---

## 9. Riscos e Limitações

### 9.1 Riscos de dados e privacidade

| Risco | Descrição | Severidade | Mitigação |
|-------|-----------|-----------|-----------|
| **Envio de dados sensíveis** | CPF, nomes, valores, dados de matrículas enviados ao Claude API | Crítica | Redaction obrigatória antes de qualquer chamada; fase inicial sem dados operacionais |
| **Violação de LGPD** | Dados pessoais de clientes/partes do cartório transmitidos sem base legal adequada | Crítica | Só dados normativos em fases iniciais; consentimento ou base legal explícita antes de dados operacionais |
| **Quebra de sigilo** | Informações de atos em fase de qualificação/análise transmitidas externamente | Alta | Feature isolada, modo dry-run, nenhum dado de ato em andamento |
| **Logs da API vazam dados** | Prompts e respostas logados por ferramentas de observabilidade com dados PII | Alta | Redaction antes do envio; logs de IA separados com acesso restrito |
| **MCP Connector sem ZDR** | MCP Connector não é elegível para Zero Data Retention | Alta | Não usar MCP Connector com dados sensíveis; servidor MCP próprio quando necessário |
| **Armazenamento de prompts** | Prompts com dados sensíveis retidos por Anthropic conforme política padrão | Média | ZDR via API (configuração enterprise) para dados operacionais; apenas normativos em fases iniciais |

### 9.2 Riscos de qualidade e responsabilidade jurídica

| Risco | Descrição | Severidade | Mitigação |
|-------|-----------|-----------|-----------|
| **Hallucination** | Claude inventa citações, prazos ou requisitos inexistentes | Crítica | Toda saída é rascunho; citação de fontes obrigatória; RAG com base normativa verificada |
| **Parecer jurídico indevido** | IA emite conclusão legal que parece definitiva | Crítica | Disclaimer obrigatório em toda saída; formato "rascunho para revisão" |
| **Confusão rascunho/decisão** | Documento gerado por IA usado sem revisão como documento oficial | Crítica | Marca d'água "RASCUNHO - GERADO POR IA - REQUER REVISÃO"; workflow de aprovação humana |
| **Citação desatualizada** | IA usa versão anterior de normativa | Alta | RAG com base normativa versionada; data de atualização explícita em toda consulta |
| **Erro de jurisdição** | IA aplica norma de outro Estado ou jurisdição | Alta | Base normativa específica: CNPFE-GO, não regras de outros Estados |
| **Responsabilidade do registrador** | O tabelião/registrador responde pelos atos — não a IA | Estrutural | Governança clara: IA apenas apoia, não decide |

### 9.3 Riscos de arquitetura e fornecedor

| Risco | Descrição | Severidade | Mitigação |
|-------|-----------|-----------|-----------|
| **Acoplamento prematuro** | Sistema dependente de API da Anthropic antes de maturidade interna | Alta | AI Gateway como camada de abstração; interface agnóstica de fornecedor |
| **Dependência de fornecedor** | Mudança de preço, política ou disponibilidade da Anthropic | Média | Contrato enterprise se viável; design portável; alternativas documentadas |
| **Execução automática de ações** | Agente autônomo executa descarte, comunicação ou modificação sem revisão | Crítica | Nenhuma ação crítica executada automaticamente; toda ação requer confirmação humana |
| **Falta de rastreabilidade** | Impossível saber qual prompt gerou qual saída | Alta | Prompt registry versionado; log de cada chamada com prompt_hash e response_hash |
| **Modelo desatualizado** | Claude usa dados de treinamento anteriores às normativas atuais | Média | RAG com base normativa local sempre atualizada; mencionar data de treinamento nos disclaimers |
| **Custo imprevisível** | Chamadas de API em volume elevado geram custo não planejado | Baixa | Modo dry-run; limites de uso; monitoramento de tokens |

### 9.4 Riscos específicos para o contexto brasileiro/cartorário

| Risco | Descrição |
|-------|-----------|
| **Inexistência de plugins específicos** | Nenhum plugin da Anthropic cobre o cartório extrajudicial brasileiro |
| **Lacuna normativa** | CNJ Resolução 615/2025 regula IA no Judiciário — extrajudicial tem lacuna formal ainda |
| **Validade de evidências geradas por IA** | Pesquisa IBA (2025) aponta que evidências geradas por IA estão sendo questionadas no Judiciário brasileiro |
| **Responsabilidade funcional** | O delegatário (tabelião/registrador) responde pessoalmente pelos atos — a IA não mitiga responsabilidade |
| **Stanford Legal RAG (2025)** | Pesquisa encontrou taxas de erro de 17% (Lexis+ AI) e 34% (Westlaw AI) — ferramentas especializadas com base jurídica americana |

---

## 10. Regras de Governança Recomendadas

### 10.1 Regras absolutas (nunca violar)

```
NÃO enviar CPF, dados de partes, valores de contratos ou dados de matrículas reais
    ao Claude API sem anonimização prévia e base legal LGPD explícita
NÃO usar output de IA como documento oficial sem revisão humana registrada
NÃO executar ação irreversível (descarte, comunicação oficial) automaticamente
NÃO declarar conformidade regulatória com base em saída de IA
NÃO usar MCP Connector com dados sensíveis (não elegível para ZDR)
NÃO confiar em citação de normativa gerada por IA sem verificação na fonte
NÃO habilitar IA em produção sem feature flag e modo dry-run testado
NÃO logar prompts com dados sensíveis em sistemas sem acesso controlado
NÃO usar IA como substituto de consulta jurídica especializada
```

### 10.2 Regras operacionais obrigatórias

| Regra | Implementação |
|-------|--------------|
| **Feature flag desabilitada por padrão** | `AI_GATEWAY_ENABLED=false` no `.env`; requer ativação explícita |
| **Modo dry-run** | Toda funcionalidade de IA deve operar em dry-run antes de produção |
| **Revisão humana obrigatória** | Toda saída de IA marcada como `[RASCUNHO - REQUER REVISÃO]`; workflow de aprovação |
| **Classificação de saídas** | Toda resposta classificada: `INFORMATIVO`, `RASCUNHO`, `REQUER_VALIDACAO_JURIDICA` |
| **Trilha de auditoria** | Log de cada chamada: `timestamp`, `prompt_hash`, `model`, `tokens`, `response_hash`, `reviewed_by` |
| **Anonimização/redaction** | Pipeline de redaction antes de qualquer chamada; verificação de CPF, nomes, valores |
| **Proibição de dados operacionais em fase inicial** | Apenas base normativa (Provimentos, CNPFE-GO, políticas INOVA) nas primeiras fases |
| **Separação normativo/operacional** | Dados normativos em `knowledge_base/normative/`; dados operacionais nunca misturados |
| **Controle de permissões** | Apenas perfis autorizados podem acionar funcionalidades de IA |
| **Prompt registry versionado** | Todos os prompts versionados em `app/modules/ai_gateway/prompts/`; sem prompts ad-hoc em produção |
| **Modelos de saída estruturados** | Toda resposta em formato padronizado com campos: `content`, `disclaimer`, `sources`, `review_status` |
| **Disclaimers internos obrigatórios** | Texto padrão em toda saída de IA: adaptação do disclaimer do compliance |
| **Limitação de escopo** | IA responde apenas sobre base normativa explicitamente indexada; recusa tópicos fora de escopo |
| **Auditabilidade de modelos** | Registrar qual modelo, versão e data de treinamento foi usado em cada chamada |

### 10.3 Matriz de risco para uso de IA

> **Tese central:** Ausência de PII não significa automaticamente autorização para
> envio a API externa. Documentos internos podem ser confidenciais por estratégia,
> contrato, segurança ou governança — independentemente de conterem ou não dados pessoais.

#### Classificação por categoria de dado

| Categoria | Exemplos | Knowledge Base local | API externa | Observação |
|-----------|----------|---------------------|-------------|------------|
| **Norma pública** | Provimento CNJ 213, Provimento 50/2015, CNPFE-GO, Código de Normas público | Permitido | Permitido com cautela | Baixo risco; documentos disponíveis publicamente |
| **Documento interno sem PII** | ADRs, documentação técnica, roadmaps internos | Permitido | Somente após revisão de conteúdo | Pode revelar estratégia interna, mesmo sem dados pessoais |
| **Documento interno confidencial** | Relatórios técnicos, diagnósticos, planos de ação; documentos da InovaLGPD se houver restrição contratual | Permitido com controle de acesso | Evitar nas fases iniciais | Ausência de PII não elimina confidencialidade |
| **Metadados operacionais** | Nomes de arquivos, caminhos, achados de auditoria sem PII, inventários de arquivos | Permitido com redaction | Somente com redaction validada | Pode revelar estrutura interna e processos sensíveis |
| **Dados pessoais / sensíveis** | CPF, nomes de partes, proprietários, valores de imóveis, matrículas, atos em qualificação, dados de titulares LGPD | Não usar nas fases iniciais | Proibido nas fases iniciais | Exige base legal LGPD, anonimização, contrato enterprise/ZDR e aprovação formal |

#### Referência rápida por dado operacional

| Dado | Fase 1 | Fase 2 | Requer |
|------|--------|--------|--------|
| Texto dos Provimentos CNJ / CNPFE-GO | Sim | Sim | — |
| Políticas InovaLGPD (texto normativo) | Sim | Sim | Confirmação de ausência de restrição contratual |
| ADRs e documentação técnica interna | Sim | Sim | Revisão de conteúdo antes do uso externo |
| Inventário de arquivos (nomes/metadados) | Não | Sim (com redaction de caminhos) | Redaction validada |
| AuditFinding sem dados de partes | Não | Sim (anonimizado) | Anonimização verificada |
| LgpdAction sem dados de titulares | Não | Sim (anonimizado) | Anonimização verificada |
| CPF, nomes, proprietários | Não | Não | Base legal LGPD + ZDR + anonimização + aprovação formal |
| Dados de matrículas, valores de imóveis | Não | Não | Base legal LGPD + contrato enterprise + Fase 3+ |
| Dados de atos em qualificação | Não | Não | Análise jurídica prévia + aprovação formal |

---

## 11. Arquitetura Recomendada

### 11.1 Visão de alto nível

```
┌─────────────────────────────────────────────────────────┐
│                    Cartório System                       │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ finance  │ │  audit   │ │compliance│ │   lgpd   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                         │                               │
│              ┌──────────▼──────────┐                   │
│              │   ai_gateway        │ ← feature flag     │
│              │  (app/modules/      │   desabilitada     │
│              │   ai_gateway/)      │   por padrão       │
│              └──────────┬──────────┘                   │
│                         │                               │
│              ┌──────────▼──────────┐                   │
│              │  knowledge_base     │                   │
│              │  (normativa local)  │                   │
│              │  - Provimento 213   │                   │
│              │  - CNPFE-GO         │                   │
│              │  - Prov. 50/2015    │                   │
│              │  - Políticas INOVA  │                   │
│              └─────────────────────┘                   │
│                                                          │
└──────────────────────┬──────────────────────────────────┘
                       │ (apenas dados normativos sem PII)
                       ▼
              ┌─────────────────┐
              │  Anthropic API  │
              │  (Claude)       │
              │                 │
              │  Fase 1: NÃO    │
              │  Fase 2: Sim    │
              │  (via Gateway)  │
              └─────────────────┘
```

### 11.2 Módulos sugeridos

#### `app/modules/ai_gateway/`

O módulo central de controle de IA. Responsável por:
- Verificar feature flag antes de qualquer chamada
- Executar pipeline de redaction
- Selecionar e versionar prompts do registry
- Fazer chamada à API (ou retornar mock em dry-run)
- Logar a chamada de forma auditável
- Formatar a resposta com disclaimer e metadados
- Classificar o tipo de saída

Estrutura sugerida:
```
app/modules/ai_gateway/
├── __init__.py
├── enums.py          # OutputType, ResponseStatus, RiskLevel
├── models.py         # AiCallLog (rastreabilidade persistida)
├── schemas.py        # AiRequest, AiResponse (estruturados)
├── service.py        # gateway_service (orquestra tudo)
├── redaction.py      # pipeline de anonimização/redaction
├── router.py         # endpoints (somente leitura em Fase 2)
└── prompts/          # prompt registry versionado
    ├── compliance_summary_v1.md
    ├── requirement_explanation_v1.md
    └── audit_narrative_v1.md
```

#### `app/modules/knowledge_base/`

Base normativa interna estruturada. Responsável por:
- Indexar documentos normativos (sem PII)
- Fornecer busca semântica e por palavras-chave
- Retornar trechos relevantes com referência à fonte
- Funcionar como pipeline de RAG local (sem IA em Fase 1)

Estrutura sugerida:
```
app/modules/knowledge_base/
├── __init__.py
├── models.py         # NormativeDocument, DocumentChunk
├── schemas.py        # DocumentSearchRequest, SearchResult
├── service.py        # indexer + search
├── router.py         # GET /search, GET /documents
└── normative/        # documentos indexados (texto limpo)
    ├── provimento_213_2026.md
    ├── cnpfe_go_extrato.md
    ├── provimento_50_2015.md
    └── politicas_inova/
```

**Nota:** Em Fase 1, o `knowledge_base` funciona sem IA — apenas indexação e busca
local. Em Fase 4, conecta-se ao AI Gateway para RAG com citações.

### 11.3 Fluxo de dados recomendado

```
Fase 1 — Knowledge Base sem IA:
Usuário → consulta normativa → knowledge_base → resultado local com fonte → Usuário

Fase 2 — AI Gateway com prompts fixos:
Usuário → ai_gateway [verifica flag + redaction + seleciona prompt] 
        → knowledge_base [recupera contexto] 
        → Anthropic API [prompt estruturado] 
        → ai_gateway [valida, formata, loga] 
        → Usuário [com disclaimer e status RASCUNHO]

Fase 4 — RAG com citações:
Usuário → ai_gateway → knowledge_base [retrieval semântico] 
        → Anthropic API [prompt + contexto + instrução de citação] 
        → ai_gateway [extrai citações, valida referências] 
        → Usuário [com fontes citadas e verificáveis]
```

### 11.4 Fronteiras com Atlas

A integração com o Atlas continua por dados estruturados em `exports/atlas/`.
O módulo `ai_gateway` **não é compartilhado com o Atlas**. Se o Atlas precisar
de IA, implementa sua própria camada independentemente.

No futuro, outputs estruturados do AI Gateway (análises, narrativas, rascunhos)
podem ser exportados como artefatos para o Atlas via `exports/atlas/ai_outputs/`
— nunca via banco compartilhado ou chamada direta.

### 11.5 Fronteiras com Engegraph

O Engegraph não é, e não deve ser, conectado à camada de IA. O Engegraph é o
sistema crítico de produção — não é gerenciado pelo Cartório System e não deve
ter sua estabilidade impactada por experimentos de IA.

Dados provenientes do Engegraph (ex.: emolumentos via `EntrySource=ENGEGRAPH_EXPORT`)
só poderão ser usados na camada de IA após:
1. Anonimização dos dados de partes
2. Base legal LGPD explícita
3. Contrato enterprise com ZDR
4. Fase mínima 3 de maturidade do AI Gateway

---

## 12. Comparação de Alternativas Arquiteturais

| Alternativa | Descrição | Vantagens | Riscos | Complexidade | Recomendação |
|-------------|-----------|-----------|--------|--------------|--------------|
| **1. Prompts manuais fora do sistema** | Gestor digita perguntas diretamente no Claude.ai | Zero implementação; imediato | Sem controle, sem log, sem redaction; dados sensíveis podem vazar por descuido | Nenhuma | Não recomendada para uso recorrente |
| **2. Knowledge base interna sem IA** | Documentos normativos indexados e buscáveis localmente | Sem risco de API; funciona offline; sem custo de modelo | Não gera narrativas; não responde perguntas em linguagem natural | Baixa | **Recomendada para Fase 1** |
| **3. AI Gateway com prompts versionados** | Camada intermediária que controla chamadas à API com prompts fixos e redaction | Controle total; auditável; evolutivo; base para todas as fases seguintes | Requer implementação inicial cuidadosa; custo de API | Média | **Recomendada para Fase 2** |
| **4. RAG com citações e base normativa** | AI Gateway + retrieval semântico de base normativa indexada | Respostas com fontes verificáveis; reduz hallucination; linguagem natural | Requer indexação e atualização da base; custo de embeddings | Média-Alta | **Recomendada para Fase 4** |
| **5. MCP Server próprio do Cartório System** | Servidor MCP que expõe os dados do sistema para Claude consultar | Integração rica com compliance, audit, retention; padrão aberto | Alta complexidade; requer infraestrutura pública acessível; segurança crítica | Alta | Considerar somente em Fase 5+ |
| **6. Agente consultivo completo** | Agente autônomo com múltiplos steps, tools e decisões | Capacidade máxima de automação | Risco muito alto de ação indevida; rastreabilidade complexa; sem precedente operacional | Muito Alta | Somente após Fase 5, com governança madura |

---

## 13. Roadmap Recomendado

### Fase 0 — Investigação e decisão arquitetural (atual)

**Objetivo:** Entender o ecossistema, definir arquitetura, estabelecer governança.  
**Entregável:** Este documento (AI_LEGAL_TOOLS_INVESTIGATION.md).  
**Duração estimada:** 1 sprint (concluída).  
**Pré-requisito para avançar:** Aprovação do gestor e definição do nome do módulo.

### Fase 1 — Knowledge Base Normativa (sem IA)

**Objetivo:** Organizar, indexar e tornar consultáveis os documentos normativos
do Cartório System em uma base local estruturada e versionada.

**Atividades:**
- Criar `app/modules/knowledge_base/` com modelos, schemas, service e router
- Extrair e indexar (texto limpo, sem PII) os documentos normativos:
  - Provimento CNJ 213/2026 (extratos relevantes)
  - CNPFE-GO (extratos por tipo de ato)
  - Provimento CNJ 50/2015 (regras de retenção)
  - Políticas InovaLGPD (textos normativos)
- Implementar busca por palavras-chave (sem embeddings nesta fase)
- Endpoint `GET /knowledge-base/search?q=...` retorna trechos com fonte

**O que NÃO fazer:** Nenhuma chamada a API de IA. Nenhum dado operacional.  
**Testes:** 95%+ cobertura; sem mocks de API externa.

### Fase 2 — AI Gateway

**Objetivo:** Implementar a camada de controle para chamadas à API da Anthropic,
com feature flag, redaction, prompt registry, log auditável e disclaimers.

**Atividades:**
- Criar `app/modules/ai_gateway/` com a estrutura descrita na seção 11.2
- Implementar feature flag `AI_GATEWAY_ENABLED` (padrão: `false`)
- Implementar modo dry-run (retorna mock sem chamar API)
- Implementar pipeline de redaction (CPF, nomes comuns, valores, caminhos)
- Implementar prompt registry versionado
- Implementar modelo `AiCallLog` (persistido, imutável, com hash)
- Primeiros prompts: `requirement_explanation_v1` e `compliance_summary_v1`
- Endpoint inicial: `POST /ai-gateway/explain-requirement/{code}` (dry-run default)

**Dado de entrada autorizado:** apenas `ComplianceRequirement.text` + contexto normativo.  
**Custo estimado de API:** muito baixo (prompts curtos, poucas chamadas por sessão).

### Fase 3 — Skills Internas para Normativas

**Objetivo:** Criar skills específicas para o contexto do cartório, instaláveis via
Claude Code, cobrindo o Provimento 213, CNPFE-GO e Provimento 50/2015.

**Atividades:**
- Criar `skills/cartorio_compliance/SKILL.md` (Provimento 213 + InovaLGPD)
- Criar `skills/registro_imoveis/SKILL.md` (CNPFE-GO por tipo de ato)
- Criar `skills/retencao_documental/SKILL.md` (Provimento 50/2015)
- Documentar o formato e processo de atualização das skills
- Testar com consultas reais do gestor

**Benefício imediato:** O gestor pode usar o Claude Code com as skills instaladas
para consultas normativas assistidas, sem depender de chamadas à API do sistema.

### Fase 4 — RAG com Citações

**Objetivo:** Adicionar retrieval semântico à knowledge base para gerar respostas
em linguagem natural com citações verificáveis.

**Atividades:**
- Adicionar indexação vetorial à knowledge base (ex.: SQLite-VSS ou ChromaDB local)
- Implementar pipeline de RAG no AI Gateway: retrieve → augment → generate → cite
- Validar qualidade das citações contra a base normativa
- Testar com perguntas frequentes do gestor sobre requisitos do Provimento 213

**Pré-requisito:** Fase 2 operacional e validada com dados normativos.

### Fase 5 — MCP Server Próprio

**Objetivo:** Expor os dados do Cartório System via protocolo MCP, permitindo que
o Claude consulte compliance, audit findings e requirements de forma estruturada.

**Atividades:**
- Implementar MCP server em `app/mcp_server/`
- Expor tools read-only: `get_requirement`, `list_evidences`, `search_findings`
- Implementar autenticação e autorização rigorosa
- Infraestrutura: servidor acessível via HTTPS (não stdio)
- Testes de segurança: nenhum dado sensível acessível via MCP

**Pré-requisito:** Autenticação multiusuário implementada; infraestrutura de produção (Postgres + VM).

### Fase 6 — Agente Consultivo Controlado

**Objetivo:** Implementar um agente com múltiplos steps para tarefas específicas
e de baixo risco: geração de narrativa do status de conformidade para o gestor.

**Atividades:**
- Definir escopo restrito: apenas consulta e narração — sem ações
- Implementar com aprovação humana em cada step crítico
- Testar exaustivamente em ambiente isolado

**Pré-requisito:** Fase 5 validada; governança de IA madura; responsável técnico treinado.

### Fase 7 — Integração futura com Atlas

**Objetivo:** Exportar outputs estruturados da camada de IA para o Atlas.

**Mecanismo:** arquivos JSON em `exports/atlas/ai_outputs/` consumidos pelo Atlas
de forma assíncrona. Nunca banco compartilhado. Nunca chamada direta.

---

## 14. Decisões Arquiteturais Propostas

### DAR-001 — Nome do módulo de IA

**Decisão proposta:** `app/modules/ai_gateway/`  
**Contexto:** Foram avaliados: `intelligence/`, `ai_gateway/`, `knowledge_base/`,
`legal_assistant/`, `normative_intelligence/`. O nome `ai_gateway` é o mais preciso
para a função primária do módulo (controlar chamadas de IA), enquanto `knowledge_base/`
é um submódulo com responsabilidade distinta.  
**Opções consideradas:**
- `normative_intelligence/`: preciso semanticamente, mas mistura knowledge base e gateway
- `legal_assistant/`: evocativo, mas pode criar expectativa de "assistente jurídico"
- `ai_gateway/`: preciso tecnicamente; descreve a função de controle e não a funcionalidade
**Escolha recomendada:** `ai_gateway/` para o gateway de controle + `knowledge_base/` como módulo separado.  
**Consequências:** Dois módulos distintos, cada um com responsabilidade clara.  
**Riscos:** Maior superfície de código inicial; mitigado pela separação de responsabilidades.  
**Requer decisão humana antes de implementar.**

---

### DAR-002 — Dado inicial autorizado para uso na API de IA

**Decisão proposta:** Apenas texto dos Provimentos e CNPFE-GO são autorizados sem
ressalvas na Fase 2. Trechos normativos das políticas InovaLGPD são candidatos
condicionais — dependem de confirmação de ausência de restrição contratual (DHP-05).
Nenhum dado operacional, nenhum PII, nenhum dado de matrícula.  
**Contexto:** O risco de LGPD e quebra de sigilo é real e imediato. Documentos da
InovaLGPD podem ter restrição contratual mesmo sem conterem PII — a ausência de
dados pessoais não implica autorização automática para uso em API externa. A base
normativa pública é suficiente para os primeiros casos de uso (explicação de
requisitos, orientação sobre documentos esperados, narrativa de conformidade).  
**Escolha recomendada:** Fase 2 restrita a dados normativos públicos confirmados;
documentos InovaLGPD somente após validação de ausência de restrição contratual;
dados operacionais só após Fase 3+ com redaction validado e base legal LGPD explícita.  
**Consequências:** Casos de uso iniciais limitados, mas seguros.  
**Riscos:** Capacidade reduzida nas fases iniciais; expectativa de gestão com o gestor.

---

### DAR-003 — Uso do MCP Connector da Anthropic

**Decisão proposta:** Não usar MCP Connector da Anthropic nas primeiras fases.  
**Contexto:** O MCP Connector (beta) não é elegível para Zero Data Retention.
Dados trafegados via MCP Connector são retidos conforme política padrão.
Para dados normativos (sem PII), o risco é aceitável, mas o ganho é baixo comparado
ao custo de implementação e risco de acoplamento.  
**Escolha recomendada:** Integração via API direta (Fase 2) e MCP Server próprio (Fase 5).
O MCP Connector pode ser avaliado pontualmente apenas para conectar com sistemas como
iManage ou Relativity, se a serventia os adotar no futuro.  
**Riscos:** Não aproveitar conectores prontos; mitigado pela base normativa que não
depende de sistemas externos.

---

### DAR-004 — Zero Data Retention

**Decisão proposta:** Contratar ZDR com a Anthropic antes de usar dados operacionais na API.  
**Contexto:** ZDR está disponível para clientes enterprise via API e Claude Code (commerce terms).
O MCP Connector explicitamente não é elegível para ZDR.  
**Escolha recomendada:** Avaliar custo/benefício do plano enterprise da Anthropic quando
a Fase 3 for atingida e dados operacionais forem candidatos a uso na API.  
**Requer decisão humana antes de implementar dados operacionais.**

---

### DAR-005 — Responsabilidade por outputs de IA

**Decisão proposta:** Toda saída de IA é marcada explicitamente como rascunho para revisão.
O responsável pela validação e pelo uso do output é o operador humano — nunca o sistema.  
**Contexto:** O titular/delegatário/responsável pela serventia é pessoalmente responsável
pelos atos. A IA não pode transferir, mitigar ou diluir essa responsabilidade.  
**Escolha recomendada:** Disclaimer estrutural em toda saída; campo `review_status` obrigatório;
log de quem revisou e quando; impossibilidade técnica de usar output sem marcar revisão.

---

### Rastreabilidade: DARs → ADRs formais

Os DARs desta seção são decisões informais propostas na sprint AI-LEGAL-0.
Os ADRs a seguir são o registro formal dessas decisões — são a fonte autoritativa.

| DAR | Tema | ADR relacionado | Status |
|-----|------|----------------|--------|
| DAR-001 | Separação entre Knowledge Base e AI Gateway | [ADR-004](../decisions/ADR-004-separacao-knowledge-base-ai-gateway.md) | Proposto |
| DAR-002 | Ordem das fases e dados iniciais autorizados | [ADR-005](../decisions/ADR-005-knowledge-base-antes-de-ia-externa.md) + [ADR-006](../decisions/ADR-006-dados-permitidos-e-proibidos-para-ia.md) | Proposto |
| DAR-003 | MCP Connector e agentes autônomos | [ADR-007](../decisions/ADR-007-mcp-e-agentes-fora-das-fases-iniciais.md) | Proposto |
| DAR-004 | Zero Data Retention | [ADR-006](../decisions/ADR-006-dados-permitidos-e-proibidos-para-ia.md) + decisão específica futura | Pendente |
| DAR-005 | Responsabilidade por outputs de IA | [ADR-008](../decisions/ADR-008-saida-de-ia-e-rascunho-sujeito-a-revisao.md) | Proposto |

> Os DARs **não substituem** os ADRs — são o rascunho de análise. Qualquer referência
> futura deve citar o ADR, não o DAR.

---

## 15. Requisitos mínimos antes de qualquer IA em produção

Nenhuma funcionalidade de IA deve ser habilitada em ambiente de produção antes que
**todos** os itens abaixo estejam implementados e validados:

- [ ] Feature flag `AI_GATEWAY_ENABLED` implementada e testada (padrão: `false`)
- [ ] Modo dry-run funcional com mocks verificáveis
- [ ] Pipeline de redaction validado contra exemplos reais de dados internos
- [ ] Prompt registry com ao menos 2 prompts versionados e revisados
- [ ] Modelo `AiCallLog` com os campos mínimos abaixo — o log **não deve armazenar
  conteúdo sensível bruto**; preferir hashes, referências, classificações e metadados
  seguros quando o dado original puder violar LGPD ou sigilo:
  - Identidade e rastreabilidade: `id`, `created_at`, `actor_user_id`, `actor_role`
  - Contexto de origem: `source_module`, `use_case`
  - Classificação: `input_classification`, `output_classification`
  - Prompt: `prompt_template_id`, `prompt_template_version`, `prompt_hash`
  - Modelo: `model_provider`, `model_id`, `model_version_or_snapshot`
  - Consumo: `tokens_in`, `tokens_out`
  - Fontes usadas: `source_document_ids`, `source_chunk_ids`
  - Redaction: `redaction_applied`, `redaction_report_hash`
  - Controles: `external_call_performed`, `dry_run`
  - Resposta: `response_hash`
  - Revisão humana: `human_review_required`, `human_review_status`, `human_reviewed_by`, `human_reviewed_at`
  - Retenção: `retention_policy`
  - Erros: `error_code`, `error_message_sanitized`
- [ ] Disclaimer obrigatório implementado em toda saída
- [ ] Campo `output_classification` em toda resposta de IA (`INFORMATIVO`, `RASCUNHO`, `REQUER_VALIDACAO_JURIDICA`)
- [ ] Testes automatizados com mock da API (sem chamadas reais em pytest)
- [ ] Documentação de quais dados podem e não podem ser enviados (conforme Seção 10.3)
- [ ] Aprovação explícita do gestor (registro em ADR formal)
- [ ] Autenticação multiusuário implementada (para registrar `reviewed_by`)
- [ ] Backup da base normativa indexada (garantia de auditabilidade futura)

---

## 16. Itens fora de escopo neste momento

Os seguintes itens estão **explicitamente fora de escopo** para as Fases 1 e 2:

- Conexão com dados de matrículas, CPFs ou dados de partes
- Integração com Engegraph via IA (qualquer forma)
- Geração de documentos oficiais ou assinados por IA
- Automação de comunicações com a corregedoria ou partes externas
- Agentes autônomos com capacidade de execução de ações
- MCP Connector com dados não-normativos
- Upload de PDFs de processos ou matrículas para a API da Anthropic
- Análise de documentos em qualificação ou em processamento
- Integração com sistemas externos (ONR, e-Notariado, SREI, SIG-RI)
- Substituição de qualquer funcionalidade do Engegraph
- Qualquer forma de "decisão automática" sobre registros, qualificações ou pareceres

---

## 17. Conclusão

### 17.1 Vale a pena criar um módulo de IA no Cartório System?

**Sim, mas na sequência correta e com governança rigorosa.**

O Cartório System tem uma base sólida: módulos regulatórios estruturados, base
normativa em dados, princípios de linguagem conservadora e revisão humana já
implementados. Isso cria condições mais favoráveis do que a maioria dos sistemas
para uma integração de IA responsável.

O setor jurídico como um todo está adotando IA de forma acelerada — 87% dos GCs
em 2026 vs. 44% no ano anterior. Para cartórios brasileiros, a adoção será mais
gradual por ausência de frameworks regulatórios específicos, mas a direção é clara.

### 17.2 O que esperar nas primeiras fases

As primeiras fases **não vão parecer IA avançada**. A knowledge base normativa
(Fase 1) é uma melhoria de organização, não uma feature de "IA". O AI Gateway
(Fase 2) vai permitir que o gestor faça perguntas em linguagem natural sobre os
requisitos do Provimento 213 — algo que já é possível manualmente no Claude.ai,
mas que agora será controlado, auditável e integrado ao sistema.

O valor das primeiras fases é **governança e fundação**, não capacidade técnica.

### 17.3 Validação da hipótese inicial

A hipótese inicial era:

> O Cartório System deve iniciar com uma base normativa interna e um AI Gateway
> controlado, usando prompts/skills versionadas para gerar análises, relatórios
> e minutas com revisão humana obrigatória. MCP e agentes mais avançados devem
> ficar para fases posteriores, após maturidade de permissões, logs, base
> documental, redaction e governança.

**Veredito: VÁLIDA, com dois ajustes:**

1. **A knowledge base normativa (Fase 1) deve preceder o AI Gateway (Fase 2)**
   — não apenas acompanhá-lo. A base precisa existir e ser validada antes de
   qualquer chamada de IA.

2. **Skills internas (Fase 3) devem ser desenvolvidas em paralelo ao AI Gateway**,
   não apenas antes do MCP. As skills para Claude Code são de baixo custo e
   permitem que o gestor já se beneficie do contexto normativo estruturado nas
   consultas manuais ao Claude.

O restante da hipótese está correto: MCP, agentes e dados operacionais ficam
para fases posteriores com governança madura.

---

## 18. Decisões Humanas Pendentes

As questões abaixo **não foram decididas neste documento** e requerem posicionamento
explícito do gestor/delegatário antes de qualquer implementação de código ou integração
com APIs externas. Cada item deve ser registrado como ADR formal quando decidido.

| # | Decisão pendente | Impacto se não decidida |
|---|-----------------|------------------------|
| DHP-01 | Aprovar ou rejeitar criação dos módulos `knowledge_base` e `ai_gateway` | Nenhuma implementação pode avançar sem essa aprovação |
| DHP-02 | Confirmar que `knowledge_base` (sem IA) precede qualquer chamada real à API de IA | Risco de pular etapa de governança e expor dados prematuramente |
| DHP-03 | Definir quais documentos podem entrar na base normativa local | Base pode incluir documentos inadequados ou excluir documentos necessários |
| DHP-04 | Definir quais documentos podem ser usados em chamadas à API externa | Risco de LGPD e quebra de sigilo se não houver limite claro |
| DHP-05 | Confirmar política sobre documentos da InovaLGPD (restrição contratual?) | Uso indevido de documentos com restrição contratual pode gerar passivo |
| DHP-06 | Definir se a Fase 1 usará exclusivamente normas públicas | Escopo da base normativa inicial depende dessa decisão |
| DHP-07 | Definir se haverá avaliação/contratação de ZDR ou plano Enterprise antes do uso de dados operacionais | Sem ZDR, dados operacionais não podem ir para a API |
| DHP-08 | Definir o responsável humano pela revisão das saídas de IA | Campo `human_reviewed_by` no AiCallLog exige pessoa designada |
| DHP-09 | Definir se o projeto criará skills internas para Claude Code (Fase 3) | Fase 3 só deve iniciar após essa decisão |
| DHP-10 | Definir quando o tema MCP será reavaliado (e quais pré-requisitos de maturidade exigir) | Sem critério, risco de adoção prematura de MCP antes da governança estar pronta |

> **Como registrar as decisões:** Cada item acima deve gerar ou atualizar um ADR em
> `docs/decisions/` quando a decisão for tomada. Os ADRs ADR-004 a ADR-008 documentam
> as **recomendações técnicas propostas**; as decisões humanas acima são o que transforma
> recomendações em decisões formalmente aceitas.

---

## 19. Próximos passos recomendados

1. **Decisão humana sobre nome dos módulos** (DAR-001): aprovar `ai_gateway/` + `knowledge_base/`
   ou propor alternativa.

2. **Decisão humana sobre ordem de prioridade** (DAR-002): confirmar que Fase 1
   (knowledge base sem IA) precede qualquer chamada à API da Anthropic.

3. **Sprint Knowledge-Base-0 (documentação):** Mapear todos os documentos normativos
   a indexar, definir formato de extração (texto limpo, sem PII) e estrutura de
   dados. Exclusivamente documental — sem código.

4. **Sprint Knowledge-Base-1:** Implementar `app/modules/knowledge_base/` com
   indexação e busca local. Sem IA. Sem API externa.

5. **Sprint AI-Gateway-0:** Implementar estrutura do gateway: feature flag,
   dry-run, prompt registry, AiCallLog. **Sem chamadas reais** ao início.

6. **Criar ADR formal para cada DAR desta seção** antes de iniciar código.

7. **Avaliar custo/benefício do plano enterprise Anthropic** quando a Fase 3
   for planejada (ZDR).

---

*Documento produzido na Sprint AI-LEGAL-0 — 2026-05-16*  
*Nenhum código foi alterado. Nenhuma migration executada. Nenhuma API conectada.*  
*Revisar antes de usar como base para decisões de implementação.*
