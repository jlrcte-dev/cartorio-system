# Relatório Executivo — Cartório System

## Cartório Costa Teixeira

---

**Versão:** 1.0  
**Data:** 06 de maio de 2026  
**Classificação:** Confidencial — Uso Interno  
**Elaborado por:** Engenharia do Cartório System  
**Branch analisada:** `main` (commit `90a9788`)

---

## 1. Sumário Executivo

O Cartório Costa Teixeira está desenvolvendo um sistema próprio de gestão interna denominado **Cartório System**. Trata-se de uma plataforma técnica independente, construída especificamente para a serventia, sem vínculo direto com o Engegraph (ERP cartorial atual). O objetivo central é criar uma camada própria de controle, rastreabilidade e evidência — um ativo que a serventia detém e opera com autonomia.

A serventia foi classificada como **Classe 3** no âmbito do Provimento CNJ nº 213/2026, a categoria mais exigente da norma. Isso impõe obrigações específicas de infraestrutura, segurança, continuidade, governança e auditoria, com prazos mais curtos e metas mais rigorosas de recuperação (RPO máximo de 4 horas e RTO máximo de 8 horas). O Cartório System nasceu para apoiar diretamente esse processo de adequação.

O sistema começou com foco financeiro e evoluiu estrategicamente para incluir diagnóstico, inventário, auditoria técnica, controle de LGPD, temporalidade documental e registro de conformidade regulatória. Essa ampliação de escopo não foi uma dispersão — foi uma resposta racional ao diagnóstico de riscos críticos reais identificados na infraestrutura atual da serventia.

Até esta data, o repositório conta com **15 commits**, **376 testes automatizados** todos aprovados, código limpo validado por ferramenta de análise estática (Ruff), e cinco módulos funcionais: Auditoria, Financeiro, Conformidade Regulatória (Compliance), LGPD e Temporalidade Documental (Retention). Complementa essa entrega um conjunto robusto de documentação regulatória com roadmaps, matrizes, planos e checklists estruturados para a vistoria.

O projeto se encontra em estágio de desenvolvimento ativo, ainda em ambiente local. Antes de ser operado por colaboradores em produção, serão necessários: autenticação multiusuário, banco de dados de produção (PostgreSQL) e infraestrutura mínima de segurança. O software, por si só, não resolve os riscos críticos de infraestrutura — esses dependem de decisões e investimentos físicos que precisam ocorrer em paralelo.

A diretoria deve compreender que o Cartório System **aumenta a capacidade de gestão e evidência**, mas não substitui VPN, backup transacional, segmentação de rede, política formal de segurança ou contrato de contingência do Engegraph. Esses itens são urgentes e independem do software.

A continuidade do projeto é recomendada. As próximas etapas prioritárias são: consolidar evidências para vistoria, implementar autenticação básica e migrar para ambiente controlado de produção. A diretoria precisa aprovar esse cronograma, designar responsáveis e autorizar os investimentos mínimos de infraestrutura.

O Cartório System representa uma transformação: sair do diagnóstico feito em planilhas e conversas informais para um sistema rastreável, auditável e documentado. Esse é o tipo de evidência que a Corregedoria espera encontrar em uma vistoria de Classe 3.

---

## 2. O que é o Cartório System

O **Cartório System** é um sistema de informação próprio do Cartório Costa Teixeira, desenvolvido internamente, com código e banco de dados exclusivos da serventia. Ele **não substitui o Engegraph** e não compartilha dados, credenciais ou código com nenhum outro sistema.

O sistema foi concebido para ser a camada de gestão, rastreabilidade e evidência que o Engegraph — como software cartorial focado em produção documental — não oferece. Enquanto o Engegraph produz atos notariais e registrais, o Cartório System organiza, diagnostica, registra e comprova como a serventia opera.

As principais funções do sistema são:

| Função | O que faz na prática |
|--------|---------------------|
| **Gestão financeira** | Registra lançamentos, categorias, competências e gera resumos financeiros gerenciais |
| **Auditoria interna** | Varre estrutura de arquivos, identifica riscos, gera inventários e relatórios documentados |
| **Diagnóstico técnico** | Analisa o ambiente e aponta problemas de organização, temporalidade e conformidade documental |
| **Controle de LGPD** | Operacionaliza o Plano de Ação de LGPD (ações AC-01 a AC-25) com histórico de status |
| **Temporalidade documental** | Aplica as regras normativas de guarda, prazo e descarte documental (Prov. CNJ 50/2015) |
| **Conformidade regulatória** | Mapeia os requisitos do Provimento CNJ 213/2026, registra evidências e vincula achados |
| **Relatórios e exportações** | Gera artefatos rastreáveis para dossiê técnico, relatórios executivos e vistoria |
| **Apoio à governança** | Suporta inventário de riscos, planos de ação e tomada de decisão baseada em dados |
| **Preparação para vistoria** | Produz evidências documentadas no formato exigido para dossiê técnico Classe 3 |

O sistema está em desenvolvimento e ainda não está em ambiente de produção. Integrações futuras com outros sistemas (ex.: Atlas AI) ocorrerão exclusivamente por exportações estruturadas e APIs explícitas — nunca por acesso direto ao banco ou compartilhamento de credenciais.

---

## 3. Por que o sistema foi criado

A decisão de criar o Cartório System partiu de um conjunto de problemas reais identificados na operação da serventia:

**Controles financeiros fragmentados.** As informações financeiras estavam distribuídas em planilhas sem estrutura padronizada, sem histórico de alterações e sem rastreabilidade. Qualquer auditoria financeira dependia de reconstrução manual.

**Baixa rastreabilidade e ausência de trilha de auditoria.** Não havia registro formal de quem fez o quê, quando e por quê. Decisões operacionais, ajustes de lançamentos e ações corretivas não deixavam rastro verificável.

**Dificuldade de produzir evidências estruturadas.** O Provimento CNJ 213/2026 exige que a serventia comprove suas ações com evidências documentadas e datadas. Essa produção de evidências não estava estruturada em nenhum sistema — dependia de registros manuais, e-mails e planilhas.

**Necessidade urgente de diagnóstico técnico.** O diagnóstico da infraestrutura revelou riscos críticos: disco de backup em estado crítico, sem VPN, sem MFA, sem dump transacional do banco do Engegraph, rede sem segmentação. Para transformar esse diagnóstico em ação gerenciável, era preciso um sistema que registrasse, priorizasse e acompanhasse cada risco.

**Classificação como Classe 3 e vistoria iminente.** A Corregedoria vistoriará a serventia. A Classe 3 é a mais exigente do Provimento. Sem documentação, sem evidências e sem sistemas de rastreabilidade, a serventia não tem como demonstrar ao vistoriador que adotou as medidas exigidas.

**Dependência exclusiva de processos manuais.** Controles feitos apenas por memória, costume ou planilha não resistem a vistoria, rotatividade de pessoal ou falha de infraestrutura.

**Necessidade de autonomia em relação ao Engegraph.** A serventia não possui contingência formal para o caso de falha do Engegraph. O Cartório System não depende do Engegraph, garantindo que funções gerenciais e de governança continuem operando mesmo em cenário de falha do ERP.

---

## 4. Estado atual do repositório

### 4.1 Stack tecnológica

| Componente | Tecnologia | Versão mínima |
|-----------|-----------|--------------|
| Linguagem | Python | 3.12 |
| Framework web | FastAPI | 0.115.0 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | 1.13.0 |
| Validação de dados | Pydantic v2 | 2.7.0 |
| Servidor web | Uvicorn | 0.30.0 |
| Banco de dados (dev) | SQLite | — |
| Banco de dados (produção) | PostgreSQL | a definir |
| Lint / formatação | Ruff | 0.5.0+ |
| Testes | pytest | 8.2.0+ |

### 4.2 Estrutura geral do projeto

```
cartorio-system/
├── alembic/            # 9 migrations de banco de dados
├── app/
│   ├── core/           # configuração, logging, tratamento de erros
│   ├── db/             # sessão e base de dados
│   ├── modules/
│   │   ├── audit/      # módulo de auditoria (foco atual)
│   │   ├── compliance/ # conformidade regulatória CNJ 213/2026
│   │   ├── finance/    # financeiro (backlog futuro)
│   │   ├── lgpd/       # plano de ação LGPD
│   │   └── retention/  # temporalidade documental
│   ├── interfaces/api/v1/ # rotas HTTP REST
│   └── main.py
├── tests/              # 26 arquivos de teste, 376 testes
├── docs/               # documentação técnica e regulatória
│   ├── modules/        # documentação por módulo
│   ├── decisions/      # ADRs (registros de decisão arquitetural)
│   ├── analysis/       # análises LGPD e domínio
│   └── architecture/   # arquitetura-alvo de infraestrutura
└── scripts/            # geração de relatórios PDF
```

### 4.3 Módulos implementados

| Módulo | Estado | Descrição resumida |
|--------|--------|-------------------|
| `audit` | Ativo — foco principal | Scanner read-only, diagnóstico documental, CRUD de achados |
| `compliance` | Ativo — 3 sprints entregues | Matriz INOVA V1, evidências regulatórias, vínculos req↔achado |
| `lgpd` | Ativo | Plano de ação LGPD com 25 ações, histórico, filtros, export CSV |
| `retention` | Ativo — integrado ao audit | Regras de temporalidade documental (Prov. CNJ 50/2015) |
| `finance` | Preservado — backlog futuro | Finance Core v1.2 com lançamentos, categorias, resumo mensal |

### 4.4 Migrations de banco de dados

| Migration | Data | Descrição |
|-----------|------|-----------|
| `20260501_1045` | 01/05/2026 | Finance Core inicial |
| `20260501_1336` | 01/05/2026 | Finance Core hardening |
| `20260501_1413` | 01/05/2026 | Ajuste de constraint |
| `20260504_0900` | 04/05/2026 | Tabela de achados de auditoria |
| `20260505_1000` | 05/05/2026 | Módulo LGPD — ações e histórico |
| `20260505_1100` | 05/05/2026 | Módulo retention — regras de temporalidade |
| `20260506_1000` | 06/05/2026 | Módulo compliance — tabelas base |
| `20260506_1500` | 06/05/2026 | Evidências regulatórias reais |
| `20260506_1600` | 06/05/2026 | Vínculos requisito↔achado |

### 4.5 Documentação regulatória existente

| Documento | Conteúdo |
|-----------|----------|
| `ROADMAP_CNJ213.md` | 6 trilhas, plano emergencial, planos 7/30/90/180 dias |
| `CNJ_213_COMPLIANCE_PLAN.md` | 45 requisitos Classe 3 com gaps e evidências exigidas |
| `CNJ_213_ALIGNMENT.md` | Mapeamento do módulo de auditoria × requisitos CNJ |
| `CNJ_213_REGULATORY_INTEGRATION_BLUEPRINT.md` | Fronteiras e roadmap de integração entre módulos |
| `INFRASTRUCTURE_ROADMAP.md` | Situação atual, VMs sugeridas, VLANs, plano de virtualização |
| `RISK_REGISTER_MODEL.md` | Modelo de registro de riscos com enums e regras |
| `VISITATION_READINESS_CHECKLIST.md` | Checklist de 73 itens para prontidão à vistoria |
| `VISITATION_READINESS_PLAN.md` | Plano semana a semana para a vistoria |
| `TECHNICAL_DOSSIER_STRUCTURE.md` | Estrutura do dossiê técnico com modelos de ata |
| `OPERATING_FLOWS_AUDIT_PLAN.md` | Plano de auditoria de fluxos operacionais |
| `architecture/target_infrastructure.md` | Arquitetura-alvo de virtualização |

### 4.6 Resultados dos comandos executados

| Comando | Resultado |
|---------|-----------|
| `git status` | Branch `main` limpa — nenhuma alteração pendente |
| `git log --oneline -10` | 10 commits listados; 15 commits totais no projeto |
| `ruff check .` | **Aprovado** — sem erros de lint |
| `ruff format --check .` | 6 arquivos precisam de reformatação (não é erro de código) |
| `pytest tests/ -v` | **376 aprovados, 1 ignorado** — em 12,76 segundos |

---

## 5. O que já foi implementado

### 5.1 Fundação técnica

O projeto foi estruturado desde o início com boas práticas de engenharia de software. Isso não é detalhe técnico — é garantia de que o sistema pode crescer sem reescritas, ser auditado sem surpresas e ser entregue a um novo desenvolvedor sem paralisia.

A fundação inclui:

- **FastAPI** com estrutura modular — cada módulo é independente, com suas próprias rotas, schemas, serviços e modelos de banco
- **SQLAlchemy 2.0** como camada de acesso a dados — com suporte a SQLite (desenvolvimento) e PostgreSQL (produção futura)
- **Alembic** como única fonte de verdade para estrutura do banco — todas as 9 migrations são rastreáveis, reversíveis e documentadas
- **Pydantic v2** para validação de dados — todas as entradas são validadas antes de persistir
- **Configuração por ambiente** — variáveis de configuração separadas por ambiente, sem credenciais no código
- **Logging estruturado** — com tratamento de exceções centralizado
- **Healthcheck** — endpoint `/api/v1/health` confirma que o sistema está em operação
- **Isolamento de banco em testes** — os testes nunca tocam o banco de produção; cada teste roda em banco isolado e limpo
- **Ruff** para lint e formatação — código padronizado e sem erros de estilo

### 5.2 Finance Core (v1.2)

O módulo financeiro foi a primeira frente de desenvolvimento. Ele está **completo como MVP**, preservado, e será retomado quando a prioridade regulatória estiver estabilizada.

O que foi implementado:
- Lançamentos financeiros com categorias, tipos (receita/despesa) e status (rascunho, confirmado, cancelado)
- Competências mensais para organização contábil
- Validações de negócio (ex.: impedimento de excluir lançamentos confirmados)
- Resumo mensal consolidado
- Hardening pós-auditoria interna (regras calibradas, constraints revisadas)
- Testes automatizados cobrindo os principais fluxos financeiros

O Finance Core representa o que o sistema entregará operacionalmente ao gestor financeiro: uma visão gerencial rastreável, que hoje depende de planilhas manuais.

### 5.3 Módulo de Auditoria

É o módulo de maior prioridade desde maio de 2026. Seu objetivo é ser a ferramenta de diagnóstico técnico e preparação para vistoria.

**Princípio central:** o módulo é estritamente **read-only** na fase atual — nenhum arquivo do servidor é modificado, movido ou excluído pelo sistema.

O que foi implementado:

- **Scanner de arquivos (`file_scanner`)** — varre pastas do servidor, coleta metadados (nome, extensão, tamanho, data, caminho) e gera inventário JSON rastreável com timestamp e hash
- **Diagnóstico documental (`DocumentDiagnosis`)** — analisa o inventário gerado pelo scanner e emite achados técnicos (DIAG-001 a DIAG-007) sobre problemas de organização, segurança e conformidade
- **Regras de temporalidade (`TEMP-001/002/003`)** — integradas ao diagnóstico, emitem alertas conservadores sobre documentos sem classificação ou em prazos suspeitos
- **CRUD de achados (`AuditFinding`)** — permite registrar manualmente achados técnicos, com campos de categoria, severidade, probabilidade, impacto, prioridade, evidência e recomendação; tudo alinhado ao modelo de risco do Provimento CNJ 213/2026
- **CLI operacional** — interface de linha de comando para executar scans e diagnósticos sem necessidade de interface gráfica

Os relatórios gerados pelo scanner e pelo diagnóstico são artefatos rastreáveis que podem compor o dossiê técnico exigido para vistoria.

### 5.4 Módulo de Conformidade Regulatória (Compliance)

Três sprints entregues que constroem progressivamente a camada de conformidade:

**Sprint 1 — Fundação read-only:**
- Implementação da Matriz INOVA V1 do Provimento CNJ 213/2026 em banco de dados
- 32 requisitos normativos, 30 políticas indicadas, 75 vínculos requisito↔política, 96 prazos por classe, 131 evidências sugeridas
- Seed determinístico e idempotente — os dados são carregados sempre da mesma forma, com checksum SHA-256 para detecção de alterações
- Endpoints REST somente leitura para consulta e filtragem

**Sprint 2 — Evidências regulatórias reais (`ComplianceEvidence`):**
- Permite registrar evidências concretas vinculadas a requisitos normativos
- Cada evidência registra: tipo, status, módulo de origem, responsável, data de coleta, nota conservadora obrigatória
- Integração por referência fraca — não há dependência direta de outros módulos

**Sprint 3 — Vínculos requisito↔achado (`RequirementFindingLink`):**
- Permite vincular requisitos normativos a achados, sinais, ações ou fontes externas de qualquer módulo
- Unicidade garantida: o mesmo vínculo não pode ser registrado duas vezes
- Preserva isolamento modular — sem FK cruzada, sem import de outros módulos

Este módulo é o núcleo de rastreabilidade regulatória: conecta o que o Provimento exige com o que a serventia registrou como evidência.

### 5.5 Módulo LGPD

Operacionaliza o Plano de Ação de LGPD da serventia (ações AC-01 a AC-25):

- Importação do Plano de Ação a partir de CSV exportado da plataforma INOVA
- CRUD completo de ações com histórico de mudanças de status
- Filtros por status, categoria, prioridade, responsável, departamento
- Sumário executivo com contagens, percentual de conclusão e ações em atraso
- Exportação em CSV para relatórios externos
- 37 testes automatizados

### 5.6 Módulo de Temporalidade Documental (Retention)

Implementa as regras do Provimento CNJ 50/2015 (Tabela de Temporalidade de Documentos):

- Regras de guarda, prazo corrente, prazo intermediário, eliminação e guarda permanente
- Seed com cenários normativos obrigatórios
- Integração ao pipeline de diagnóstico do módulo de auditoria
- Princípio fundamental: **nenhuma decisão de descarte é automática** — toda saída é indicativa e exige validação humana e jurídica

### 5.7 Documentação regulatória

O repositório contém um conjunto robusto de documentos estruturados que constituem, por si mesmos, um ativo estratégico:

- Roadmap estratégico de adequação ao CNJ 213/2026 com 6 trilhas paralelas
- Matriz de conformidade Classe 3 com 45 requisitos mapeados, gaps identificados e evidências necessárias
- Registro de riscos com modelo padronizado e enums estruturados
- Checklist de 73 itens para prontidão à vistoria
- Plano semana a semana de preparação para vistoria
- Estrutura completa do dossiê técnico com modelos de ata e índice de hashes
- Plano de infraestrutura com VMs sugeridas, VLANs e estratégia de virtualização
- Blueprint de integração regulatória entre módulos (ADR-001 e ADR-002)

---

## 6. Mudança estratégica de foco

O Cartório System foi originalmente concebido com forte ênfase financeira e gerencial. O Finance Core foi a primeira entrega e ainda está preservado como backlog futuro. Essa origem é legítima: a serventia precisava de controle financeiro rastreável.

A mudança de prioridade ocorreu quando dois fatores se somaram:

**Fator 1 — O diagnóstico técnico revelou riscos críticos urgentes.** O disco de backup em estado crítico, a ausência de VPN, a falta de dump transacional do banco do Engegraph e a inexistência de segmentação de rede representam riscos que podem comprometer a operação da serventia antes mesmo de qualquer vistoria.

**Fator 2 — A classificação como Classe 3 tornou o prazo regulatório urgente.** A Classe 3 é a mais exigente do Provimento CNJ 213/2026. RPO de 4 horas e RTO de 8 horas são metas que a serventia ainda não atinge. A vistoria da Corregedoria não é hipotética — é iminente.

**A decisão foi correta.** Continuar com o foco exclusivo no módulo financeiro, enquanto riscos críticos de infraestrutura e conformidade regulatória permaneciam sem diagnóstico, representaria uma inversão de prioridades perigosa.

O que mudou:
- O **foco operacional** passou de lançamentos financeiros para auditoria técnica, conformidade e evidências
- A **prioridade de desenvolvimento** passou do Finance Core para os módulos `audit`, `compliance`, `lgpd` e `retention`
- O **horizonte de entrega** passou de melhorias gerenciais internas para preparação para vistoria regulatória

O que **não** mudou:
- O Finance Core está preservado integralmente — não foi descartado, apenas postergado
- A arquitetura modular permite retomar o financeiro sem impactar os demais módulos
- O valor gerencial do sistema financeiro continua válido e será retomado quando a urgência regulatória estiver controlada

---

## 7. Valor estratégico para a diretoria

| Área | Problema atual | Como o Cartório System ajuda | Benefício para a diretoria |
|------|---------------|------------------------------|---------------------------|
| **Auditoria interna** | Nenhum sistema de registro formal de achados técnicos | Módulo `audit` com scanner, diagnóstico e CRUD de achados | Rastreabilidade de problemas; evidência de que a serventia diagnosticou e agiu |
| **Riscos** | Riscos identificados informalmente, sem registro padronizado | Modelo de risco padronizado (categoria, severidade, probabilidade, impacto, status) | Decisões baseadas em risco priorizado; histórico auditável |
| **Evidências** | Evidências dependem de registros manuais e e-mails | Módulo `compliance` com `ComplianceEvidence` vinculada a requisitos CNJ | Dossiê técnico estruturado; evidências com metadata e rastreabilidade |
| **Financeiro** | Lançamentos em planilhas sem histórico de alterações | Finance Core v1.2 com categorias, tipos, status e resumo mensal | Controle gerencial rastreável; base para relatórios financeiros |
| **Infraestrutura** | Riscos de disco, VPN e backup documentados apenas em e-mails | Inventário e diagnóstico automatizados; documentação de gaps | Visão clara da situação atual para decisão de investimento |
| **Documentos** | Arquivos sem organização formal; duplicatas; sem temporalidade | Scanner de arquivos + regras de temporalidade documental | Diagnóstico do acervo digital; base para organização e conformidade |
| **Governança** | PSI, PCN e PRD inexistentes ou não formalizados | Templates, checklists e roadmap estruturados para criação dessas políticas | Aceleração da formalização de políticas obrigatórias |
| **Vistoria** | Nenhum dossiê técnico estruturado; sem checklist formal | Checklist de 73 itens + plano semana a semana + estrutura do dossiê | Preparação sistemática e documentada para a vistoria da Corregedoria |
| **Continuidade operacional** | Dependência crítica do Engegraph sem plano formal | Módulo de auditoria independente do Engegraph; documentação de dependências | Operação gerencial continua mesmo em falha do Engegraph |
| **Tomada de decisão** | Decisões baseadas em percepções, não em dados estruturados | Relatórios, sumários e exports gerados pelo sistema | Diretoria com informações organizadas para decisões de prioridade e investimento |

---

## 8. Alinhamento com o Provimento CNJ nº 213/2026

O Provimento CNJ nº 213/2026 exige que serventias extrajudiciais demonstrem conformidade técnica, operacional e documental em seis grandes áreas. A tabela abaixo apresenta como o Cartório System apoia cada área:

| Área exigida pelo Provimento | Como o Cartório System apoia |
|-----------------------------|------------------------------|
| **Inventário de ativos** | Scanner de arquivos gera inventário documentado com metadata e hash; modelo de ativos no registro de riscos |
| **Registro de riscos** | Módulo `audit` com `AuditFinding` — 12 categorias de risco, enums de severidade/probabilidade/impacto, status de tratamento |
| **Dossiê técnico** | Template completo do dossiê (`TECHNICAL_DOSSIER_STRUCTURE.md`) + artefatos exportáveis com timestamp; estrutura definida para 12 seções obrigatórias |
| **Trilhas de auditoria** | Cada execução do scanner e diagnóstico gera artefato rastreável; `AuditFinding` registra achado, evidência, responsável e status |
| **Gestão de evidências** | `ComplianceEvidence` vincula evidências reais a requisitos normativos; `RequirementFindingLink` conecta achados a requisitos CNJ |
| **Backup e continuidade** | Diagnóstico de gaps de backup documentado; template de ata de teste de restauração; mapeamento de RPO/RTO atual × meta Classe 3 |
| **Controle de acesso** | Scanner documenta permissões inadequadas; checklist de 73 itens inclui controle de acesso como bloco obrigatório |
| **Governança** | Roadmap com 6 trilhas; matriz de conformidade com 45 requisitos; templates de políticas; plano semana a semana |
| **LGPD** | Módulo `lgpd` operacionaliza o Plano de Ação com 25 ações, histórico e export; módulo `retention` aplica temporalidade |
| **Preparação para fiscalização** | Checklist de 73 itens; plano de prontidão para vistoria; estrutura do dossiê técnico; alinhamento de cada fase ao checklist |

> **Aviso obrigatório:** O Cartório System apoia a conformidade, mas **não substitui** políticas formais aprovadas, infraestrutura segura implementada, contratos com fornecedores, controles técnicos de rede e acesso, parecer jurídico especializado ou validação da Corregedoria. Nenhuma funcionalidade do sistema equivale a declaração de conformidade com o Provimento CNJ nº 213/2026.

---

## 9. Riscos que o software não resolve sozinho

O Cartório System é uma ferramenta de diagnóstico, registro e evidência. Alguns riscos críticos dependem de ação física, infraestrutura e governança que estão fora do escopo de qualquer software:

| Risco crítico | Por que o software não resolve | Ação necessária |
|---------------|-------------------------------|-----------------|
| **Backup sem dump transacional do Engegraph** | O sistema pode diagnosticar e registrar o gap, mas não executa o backup | Contatar Engegraph para confirmar procedimento oficial de backup; implementar dump SQL agendado |
| **Disco de dados e backup em estado crítico** | O scanner informa o problema, mas não libera espaço | Limpeza física de arquivos duplicados; expansão de armazenamento |
| **Ausência de VPN** | O sistema documenta o risco, mas não instala VPN | Escolher e implantar solução de VPN (WireGuard, OpenVPN ou comercial) antes de qualquer acesso remoto |
| **MFA inexistente** | O checklist lista o item, mas MFA é configurado no SO/sistema externo | Implantar MFA para todos os acessos administrativos ao servidor e sistemas |
| **Permissões NTFS inadequadas** | O diagnóstico aponta o problema, mas NTFS é configurado no servidor | Configurar permissões por grupo/perfil; criar pasta restrita para documentos sigilosos |
| **Segmentação de rede inexistente** | O sistema documenta o gap, mas não configura switches ou APs | Implantar VLANs: rede administrativa separada da rede de clientes |
| **Nobreaks com baixa autonomia e sem gerador** | O inventário registra o risco, mas não fornece energia | Avaliar substituição de baterias; avaliar viabilidade de gerador |
| **Plano de continuidade não formalizado (PCN/PRD)** | O sistema fornece templates, mas a aprovação e assinatura são humanas | Redigir, revisar juridicamente, aprovar e comunicar PCN e PRD |
| **Contingência do Engegraph não contratada** | O sistema documenta a dependência, mas não cria contrato | Definir SLA formal com o fornecedor Engegraph; planejar contingência operacional |
| **PSI inexistente ou adaptada de terceiros** | O roadmap guia a criação, mas a PSI é um documento jurídico-organizacional | Redigir PSI própria, aprovada pela diretoria e assinada por todos os colaboradores |
| **Treinamento de colaboradores não documentado** | O checklist lista o item, mas o treinamento é presencial/organizacional | Realizar capacitação, gerar atas e registros de presença |

---

## 10. Próximos desenvolvimentos recomendados

### 10.1 Prioridade imediata — 0 a 7 dias

| Ação | Objetivo |
|------|----------|
| Executar scanner de arquivos no servidor da serventia | Gerar primeiro inventário real — linha de base para o dossiê |
| Registrar achados prioritários no módulo `audit` | Transformar diagnóstico informal em registros rastreáveis |
| Validar e preencher checklist de 73 itens | Identificar gaps críticos antes da vistoria |
| Iniciar pasta `_VISTORIA/` na rede local | Centralizar evidências para o dossiê técnico |
| Fotografar estado atual de discos, backup e usuários | Evidência do ponto de partida — obrigatória para dossiê |
| Rodar todos os testes e confirmar ambiente estável | Garantir que o sistema está pronto para uso |
| Revisar documentação regulatória gerada | Confirmar que reflete a realidade atual da serventia |

### 10.2 Curto prazo — 30 dias

| Ação | Objetivo |
|------|----------|
| Registrar todos os riscos identificados no módulo `audit` | Base de dados de riscos rastreável com prioridades |
| Vincular evidências coletadas a requisitos CNJ | Preencher `ComplianceEvidence` com evidências reais |
| Iniciar autenticação multiusuário | Pré-requisito para uso do sistema por colaboradores |
| Gerar relatório executivo de conformidade | Visão consolidada do estado da adequação para a diretoria |
| Acompanhar Plano de Ação LGPD via módulo `lgpd` | Manter rastreabilidade das ações AC-01 a AC-25 |
| Confirmar procedimento de backup do Engegraph com fornecedor | Risco crítico que não pode esperar |
| Iniciar rascunho da PSI própria da serventia | Documento obrigatório para Classe 3 |

### 10.3 Médio prazo — 90 dias

| Ação | Objetivo |
|------|----------|
| Painel de prontidão para vistoria (status do checklist) | Visão executiva do percentual de preparação |
| Dossiê técnico consolidado e exportável | Artefato principal para a vistoria da Corregedoria |
| Relatório de `ComplianceStatus` por requisito | Visão do estado de cada requisito CNJ 213/2026 |
| Histórico de ações corretivas por achado | Comprovação de que os riscos foram tratados |
| Migrar para banco PostgreSQL em ambiente controlado | Produção com backup, monitoramento e RPO definido |
| Integração inicial com rotinas de backup | Cartório System incluído explicitamente no PRD |
| Revisão das evidências com responsável técnico | Validação humana antes da vistoria |

### 10.4 Longo prazo — 180 dias

| Ação | Objetivo |
|------|----------|
| Dashboards executivos de conformidade e riscos | Visão gerencial contínua para a diretoria |
| Retomada do módulo financeiro (Finance Core) | Controle gerencial financeiro rastreável |
| Exportações com checksum, manifest e timestamp | Relatórios com evidência de geração e integridade |
| Importação histórica de lançamentos financeiros | Base histórica financeira no sistema próprio |
| Módulo de obrigações e relatórios CNJ | Apoio a obrigações periódicas com a Corregedoria |
| Relatórios periódicos automáticos de conformidade | Acompanhamento contínuo da adequação ao Provimento |
| Integração controlada com Atlas por exports | Dados estruturados sem acoplamento direto |

---

## 11. Decisões recomendadas à diretoria

A continuidade e o sucesso do Cartório System dependem de decisões formais da diretoria. Abaixo estão as decisões prioritárias, ordenadas por urgência:

| # | Decisão | Urgência | Impacto se não decidida |
|---|---------|----------|------------------------|
| **D-01** | Aprovar a continuidade do Cartório System como projeto estratégico interno da serventia | Alta | Projeto perde prioridade e funding; adequação regulatória fica sem ferramenta de suporte |
| **D-02** | Confirmar que a prioridade atual é o módulo de auditoria e conformidade (Finance Core como backlog) | Alta | Risco de dispersão de esforço em funcionalidades não urgentes |
| **D-03** | Autorizar execução imediata do plano emergencial de infraestrutura (discos, backup, VPN, MFA) | Crítica | Riscos críticos permanecem abertos; RPO/RTO inatingíveis; vulnerabilidade de acesso remoto |
| **D-04** | Designar responsável interno formal pelo dossiê técnico da vistoria | Alta | Nenhum artefato do dossiê avança sem responsável com autoridade para coletar e assinar evidências |
| **D-05** | Designar responsável técnico formal de TI (conforme exigência Classe 3) | Crítica | Requisito G-06 do Provimento sem responsável designado — gap obrigatório para a vistoria |
| **D-06** | Aprovar orçamento mínimo para: solução de backup off-site, VPN, switches gerenciáveis para VLANs e avaliação de nobreaks | Crítica | Sem investimento em infraestrutura, o software não pode compensar os riscos físicos |
| **D-07** | Confirmar data estimada de vistoria e aprovar cronograma de 7, 30, 90 e 180 dias | Alta | Sem prazo firme, as ações do plano emergencial não têm urgência real |
| **D-08** | Definir política de uso interno do sistema (quem acessa, o que cada perfil pode fazer) | Média | Necessária antes de habilitar acesso de colaboradores |
| **D-09** | Decidir quando o sistema migra de ambiente de desenvolvimento para ambiente controlado de produção | Média | A migração exige: banco PostgreSQL, backup do banco, autenticação e servidor dedicado |

---

## 12. Roadmap executivo consolidado

| Horizonte | Objetivo estratégico | Entregas esperadas | Responsável sugerido | Dependências | Resultado para a diretoria |
|-----------|---------------------|-------------------|---------------------|-------------|---------------------------|
| **0 a 7 dias** | Primeiro diagnóstico real e evidências emergenciais | Inventário de arquivos; registro de achados críticos; checklist preenchido; pasta `_VISTORIA/` criada; fotografias de estado atual | TI + Gestor | Acesso ao servidor para execução do scanner | Linha de base documentada do estado atual da serventia |
| **30 dias** | Conformidade básica documentada e riscos registrados | Registro de riscos completo no sistema; evidências vinculadas a requisitos CNJ; PSI v1.0 rascunhada; confirmação do backup do Engegraph; autenticação básica iniciada | TI + Gestor + Jurídico | Decisão sobre responsável técnico (D-05); orçamento de infraestrutura (D-06) | Visão gerencial do gap entre situação atual e exigências do Provimento |
| **90 dias** | Dossiê técnico inicial e infraestrutura crítica corrigida | Dossiê técnico v1.0 com evidências; VPN implantada; backup com dump do Engegraph testado; PostgreSQL em produção; `ComplianceStatus` por requisito | TI + Gestor | Infraestrutura de VPN, switches e backup contratada | Dossiê técnico disponível para vistoria; infraestrutura crítica corrigida |
| **180 dias** | Conformidade consolidada e sistema em produção estável | Todas as VMs do plano de virtualização em operação; trilha de auditoria com retenção de 5 anos; Finance Core retomado; primeiro relatório periódico de conformidade | TI + Gestor | Hardware de virtualização aprovado; todos os planos formalizados | Serventia operando com governança estruturada e sistema próprio em produção |
| **12 meses** | Maturidade operacional e auditabilidade plena | Exports com checksum e manifest; dashboards de conformidade; integração futura com Atlas por exports; relatórios CNJ versionados; simulação de desastre documentada | TI + Gestor | Todos os itens de 90 e 180 dias concluídos | Serventia com nível de maturidade compatível com Classe 3 para as próximas vistorias |
| **24 meses** | Alta disponibilidade e conformidade sustentada | HA para sistemas críticos; pentest ou metodologia equivalente realizado; logs centralizados e imutáveis; portabilidade e reversibilidade do acervo testadas; PSI revisada anualmente | TI + Gestor + Jurídico + Auditoria externa | Todos os horizontes anteriores cumpridos | Conformidade sustentada com o Provimento CNJ 213/2026 para horizonte de longo prazo |

---

## 13. Conclusão executiva

O Cartório System construiu, em 15 commits e aproximadamente duas semanas de desenvolvimento intensivo, uma fundação técnica relevante e uma documentação regulatória que a maioria das serventias não possui de forma estruturada. Os 376 testes automatizados aprovados, o código limpo e os cinco módulos funcionais evidenciam um projeto com disciplina de engenharia — não apenas um protótipo.

A mudança de foco do financeiro para a auditoria e conformidade foi estratégica e correta. O diagnóstico revelou que os riscos regulatórios e operacionais eram mais urgentes do que o controle financeiro gerencial. Essa decisão preserva o valor já entregue (Finance Core) enquanto direciona o esforço para onde a serventia mais precisa agora: rastreabilidade, evidências e preparação para vistoria.

O sistema aumenta genuinamente a capacidade de gestão da diretoria. Com o Cartório System, é possível saber quais riscos existem, com qual severidade, quem é o responsável pelo tratamento e qual evidência comprova a ação tomada. Esse nível de rastreabilidade não existia antes.

O sistema, porém, não elimina a necessidade de corrigir a infraestrutura. VPN, backup transacional do Engegraph, segmentação de rede, MFA e PSI própria precisam acontecer. São ações físicas, contratuais e organizacionais que nenhum software substitui. O risco mais grave da serventia hoje não é a ausência de um sistema de gestão — é a vulnerabilidade da infraestrutura crítica.

A recomendação final é clara: **aprovar a continuidade do Cartório System** como projeto estratégico da serventia, **aprovar o plano emergencial de infraestrutura** como prioridade paralela e imediata, e **formalizar o cronograma de 7, 30, 90 e 180 dias** com responsáveis designados e metas mensuráveis. Essas três decisões, tomadas conjuntamente, são o passo mais importante que a diretoria pode dar hoje para posicionar o Cartório Costa Teixeira de forma sólida para a vistoria da Corregedoria.

---

## 14. Anexo — Evidências do repositório

### 14.1 Principais arquivos analisados

| Arquivo | Tipo | Relevância |
|---------|------|-----------|
| `README.md` | Documentação | Visão geral, stack, foco atual, estrutura |
| `pyproject.toml` | Configuração | Stack, dependências, versão Python, configuração de lint e testes |
| `docs/ROADMAP_CNJ213.md` | Regulatório | 6 trilhas, 13 riscos mapeados, plano de virtualização |
| `docs/CNJ_213_COMPLIANCE_PLAN.md` | Regulatório | 45 requisitos Classe 3 com gaps e evidências |
| `docs/CNJ_213_ALIGNMENT.md` | Regulatório | Mapeamento módulo audit × requisitos CNJ |
| `docs/INFRASTRUCTURE_ROADMAP.md` | Infraestrutura | Situação atual, VMs sugeridas, VLANs |
| `docs/RISK_REGISTER_MODEL.md` | Governança | Modelo de registro de riscos com enums |
| `docs/VISITATION_READINESS_CHECKLIST.md` | Vistoria | 73 itens de prontidão para vistoria |
| `docs/TECHNICAL_DOSSIER_STRUCTURE.md` | Vistoria | Estrutura do dossiê técnico em 12 seções |
| `docs/CNJ_213_REGULATORY_INTEGRATION_BLUEPRINT.md` | Arquitetura | Blueprint de integração entre módulos regulatórios |
| `docs/decisions/ADR-001` | Decisão | Ownership de evidências regulatórias |
| `docs/decisions/ADR-002` | Decisão | Referências fracas entre módulos |
| `docs/modules/audit.md` | Técnico | Princípios, áreas, fases do módulo de auditoria |
| `docs/modules/compliance.md` | Técnico | Estado das 3 sprints implementadas |
| `docs/modules/lgpd.md` | Técnico | Endpoints, modelo e enums do módulo LGPD |
| `docs/modules/retention.md` | Técnico | Princípios e integração do módulo de temporalidade |
| `alembic/versions/*.py` | Banco | 9 migrations rastreáveis e reversíveis |
| `tests/*.py` | Qualidade | 26 arquivos, 376 testes automatizados |

### 14.2 Comandos executados e resultados

| Comando | Resultado completo |
|---------|-------------------|
| `git status` | `On branch main` / `nothing to commit, working tree clean` |
| `git log --oneline` (todos) | 15 commits no histórico |
| `git log --oneline -10` | 10 commits recentes exibidos (ver seção 4.4) |
| `ruff check .` | `All checks passed!` — sem erros de lint |
| `ruff format --check .` | 6 arquivos precisam de reformatação (formatação pendente; não são erros de lógica ou segurança) |
| `pytest tests/ -v` | `376 passed, 1 skipped in 12.76s` — suíte completa aprovada |

### 14.3 Resultado dos testes por módulo

| Arquivo de teste | Cobertura |
|-----------------|-----------|
| `test_health.py` | Healthcheck da API |
| `test_isolation.py` | Isolamento de banco em testes |
| `test_finance_entries.py` | Lançamentos financeiros — Finance Core |
| `test_audit_findings.py` | CRUD de achados de auditoria |
| `test_file_scanner.py` | Scanner read-only de arquivos |
| `test_document_diagnosis.py` | Diagnóstico documental |
| `test_temp_diagnosis_rules.py` | Regras de temporalidade TEMP-001/002/003 |
| `test_retention_rules.py` | Regras de temporalidade documental |
| `test_retention_seed.py` | Seed determinístico de temporalidade |
| `test_diagnosis_retention_integration.py` | Integração diagnóstico × temporalidade |
| `test_lgpd_actions.py` | Módulo LGPD — 25 ações, import, histórico |
| `test_compliance_models.py` | Modelos do módulo compliance |
| `test_compliance_routes.py` | Endpoints REST do compliance |
| `test_compliance_seed.py` | Seed da Matriz INOVA V1 |
| `test_compliance_isolation.py` | Isolamento do módulo compliance |
| `test_compliance_evidence_models.py` | Modelo de evidências regulatórias |
| `test_compliance_evidence_routes.py` | Endpoints de evidências regulatórias |
| `test_compliance_evidence_service.py` | Serviço de evidências regulatórias |
| `test_compliance_finding_link_models.py` | Modelo de vínculos requisito↔achado |
| `test_compliance_finding_link_routes.py` | Endpoints de vínculos |
| `test_compliance_finding_link_service.py` | Serviço de vínculos |

### 14.4 Limitações desta análise

- A análise foi realizada em ambiente local de desenvolvimento (SQLite). O sistema ainda não opera em banco de produção (PostgreSQL).
- O scanner de arquivos não foi executado contra o servidor real da serventia durante esta análise — o inventário real precisa ser gerado em campo.
- Os 6 arquivos indicados pelo `ruff format --check` precisam de reformatação — não representam erros de lógica, segurança ou funcionalidade, mas devem ser corrigidos antes do próximo release.
- O relatório não inclui análise de performance, carga ou segurança de endpoints — esses testes não fazem parte do escopo atual.
- O módulo `finance` foi preservado mas não foi objeto de análise aprofundada neste relatório, pois está em backlog.

### 14.5 Pontos pendentes identificados

| Ponto | Impacto |
|-------|---------|
| 6 arquivos com formatação pendente (ruff format) | Baixo — apenas estilo de código |
| Autenticação multiusuário não implementada | Alto — necessária antes de uso em produção por colaboradores |
| Banco PostgreSQL de produção não configurado | Alto — necessário para migração de dev para produção |
| Scanner não executado contra servidor real | Médio — o inventário real ainda não existe |
| `ComplianceStatus` por requisito não implementado | Médio — próxima sprint planejada (Compliance-4) |
| Módulo financeiro em backlog | Baixo (atual) — retomada planejada para horizonte de 180 dias |
| Arquivo `RISK_REGISTER.md` referenciado no README mas não localizado como preenchido | Médio — o modelo está criado; o registro efetivo precisa ser preenchido |

---

*Documento elaborado com base na análise completa do repositório `cartorio-system` branch `main`, commit `90a9788`, em 06 de maio de 2026.*

*Este relatório não constitui declaração de conformidade com o Provimento CNJ nº 213/2026 nem com qualquer outra norma regulatória. A adequação formal da serventia depende de validação humana, jurídica e administrativa, e de ações de infraestrutura que estão fora do escopo deste sistema.*
