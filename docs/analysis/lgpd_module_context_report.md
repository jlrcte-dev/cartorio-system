# Relatório Técnico-Estratégico: Módulo LGPD do Cartório System

> **Aviso:** Este é um relatório de análise técnico-operacional, não parecer jurídico.  
> A serventia mantém contrato ativo com INOVA LGPD para assessoria jurídica.  
> Este documento apoia decisões de engenharia e gestão operacional.

**Data:** 2026-05-05  
**Versão:** 1.0  
**Estado:** Análise Completa — Pronto para Decisão

---

## 1. Sumário Executivo

A serventia Cartório Costa Teixeira está em processo de adequação LGPD conduzido pela INOVA LGPD desde fevereiro de 2023. Até agora, 11 de 25 ações do plano foram concluídas (44%), com 14 pendentes e 15 sem data confirmada.

**Situação atual:**
- ✅ **11 políticas e procedimentos** elaborados e versionados pela INOVA
- ✅ **38 atividades de tratamento (RAT/ROPa)** mapeadas
- ✅ **Plataforma LGPD da INOVA** parcialmente configurada (integração com erro — bloqueio crítico)
- ❌ **15 ações críticas em atraso** — principalmente relacionadas a implementação, implantação, treinamento e resposta a incidentes
- ❌ **Sem sistema de gestão integrado** para rastrear ações, evidências e conformidade
- ❌ **Sem responsável formal designado** para executar o plano
- ❌ **Sem registro estruturado** de evidências e documentos

**Recomendação executiva:** O Cartório System deve incluir um módulo LGPD dedicado para **capturar, rastrear, evidenciar e reportar** a execução do plano de adequação. O módulo deve:

1. Integrar-se ao módulo de Auditoria existente (Etapa B em andamento)
2. Permitir registro de ações, evidências, documentos e conformidade
3. Gerar relatórios para INOVA, gestor e futura vistoria CNJ
4. Não duplicar estruturas jurídicas — apoiar, não substituir

**Escopo inicial recomendado (MVP):**
- Importação/registro do Plano de Ação LGPD
- Gestão de evidências (uploadde documentos, rastreabilidade)
- Dashboard de status das ações
- Geração de relatórios de conformidade

**Timing:** Criação é possível em paralelo com Sprint 2 (AuditFinding CRUD) a partir de junho/2026, com implementação em 2 a 3 sprints.

---

## 2. Fontes Analisadas

| Fonte | Tipo | Data | Observação |
|-------|------|------|-----------|
| Plano de Ação.csv | Estrutura operacional | 2023-2025 | 25 ações; status variable |
| Situação atual — Imagens 1, 2, 3 | Dashboard executivo | 2026-05 | Estado da plataforma INOVA |
| 14 Políticas/procedimentos .docx | Documentação jurídica | 2023-2026 | Elaboradas pela INOVA |
| Ciclo de Vida e Retenção | Documentação técnica | 2026 | Tabela de temporalidade |
| Contratos e Aditivos | Documentação jurídica | 2023-2026 | Adequação contratual |
| Treinamentos PDF | Registros de capacitação | 2023-2026 | 20+ certificados de treinamento |
| Relatórios técnicos (se existirem) | Análise diagnóstica | — | Não encontrados em _local_data |
| docs/architecture.md | Arquitetura do sistema | 2026-05 | Estrutura FastAPI + SQLAlchemy |
| docs/modules/audit.md | Módulo de Auditoria | 2026-05 | Sprint 1 concluído; Sprint 2 próximo |
| docs/CNJ_213_COMPLIANCE_PLAN.md | Conformidade regulatória | 2026-05 | Classe 3; 6 trilhas paralelas |
| docs/TECHNICAL_DOSSIER_STRUCTURE.md | Estrutura de evidências | 2026-05 | Índice para vistoria |
| Memory — Audit Module | Contexto operacional | 2026-05 | Decisões técnicas anteriores |

---

## 3. Situação Atual do Projeto LGPD/INOVA

### 3.1 Timeline de execução

```
FEV 2023          MAR 2023             ...           MAY 2026         JUN 2026 (projetado)
    |                |                                   |                |
Contratação    Políticas elaboradas     Paralisação?   Análise deste     Decisão sobre
de INOVA         (AC-03, AC-04, etc.)    Stagnação?    relatório         módulo LGPD
```

### 3.2 Plano de Ação: status consolidado

**Total de 25 ações (100%):**

| Status | Contagem | % | Categoria |
|--------|----------|---|-----------|
| ✅ Finalizada | 11 | 44% | Governança (políticas, privacybydesign, mesa limpa, backup, RIPD, LI) |
| ⏳ Pendente | 14 | 56% | Implantação, preparação, recomendações |
| 📅 Sem data | 15 | 60% | Overlap: algumas pendentes também sem data |

**Ações finalizadas (11):**
- AC-03: Política de Descarte
- AC-04: Política de Segurança da Informação (PSI)
- AC-05: Política de Privacidade
- AC-09: Privacy by Design
- AC-14: Política de Backup
- AC-17: Inventário de Dados Pessoais (RAT/ROPa)
- AC-19: Política de Mesa Limpa/Tela Limpa
- AC-21: Plataforma de Privacidade (configuração básica)
- AC-22: Procedimento para Elaboração do RIPD
- AC-23: Procedimento para Análise de Legítimo Interesse

**Ações críticas pendentes (14):**
- AC-01: Banco de dados não estrutural (TI — Governança)
- AC-02: Descarte de currículo (RH — Preparação)
- AC-06: Política de Cookies (jurídica — Governança)
- AC-07: Dados do DPO no site (implantação)
- AC-08: Programa de Governança (implantação — alta prioridade)
- AC-10: Gestão de Consentimento de Colaboradores (governança)
- AC-11: Programa de Treinamento e Conscientização (governança, alta)
- AC-12: Análise de Contratos (jurídica — INOVA demandou)
- AC-13: Avaliação de Parceiros e Fornecedores (INOVA demandou)
- AC-15: Nomeação do Encarregado de Proteção de Dados (DPO — implantação)
- AC-16: Divulgação do DPO no site (implantação)
- AC-18: Ferramenta de Gestão de Titulares (implantação — platform)
- AC-20: Base de dados dos titulares (implantação — integração)
- AC-24: Política de Retenção (governança)
- AC-25: Plano de Resposta a Incidentes (governança, crítica para CNJ 213)

### 3.3 Situação da Plataforma LGPD da INOVA (imagens)

**Imagem 1 — Dashboard geral:**
- 38 atividades de tratamento (RAT/ROPa) mapeadas ✅
- 2 com "ausência de base legal" (ATENÇÃO — requer análise jurídica)
- 15 ações em atraso ⚠️
- **Integração indisponível:** "Chave de integração da plataforma de privacidade não foi configurada" (erro crítico)
- 0 documentos de "Ciclo de Vida" registrados

**Imagem 2 — Ações pendentes de edição:**
- Programa de Governança (pendente)
- Gestão de Consentimento de Colaboradores (pendente)
- Programa de Treinamento (pendente)
- Análise de Contratos (pendente)
- Avaliação de Parceiros/Fornecedores (pendente)
- Encarregado de Proteção de Dados (pendente)
- Divulgação do DPO (pendente)
- Ferramenta de Gestão de Titulares (pendente)
- Titulares de Dados Pessoais (pendente)
- Política de Retenção (pendente)
- Plano de Resposta a Incidentes (pendente)

**Imagem 3 — Execução e conformidade:**
- **Meta geral: 100%**
- **Execução atual: 44%** (11 de 25 ações concluídas)
- **Breakdown:** 11 conclusivas, 14 pendentes, 15 sem data confirmada
- **Status de questionários:** alguns no nível "Bom", alguns em crítico

### 3.4 Documentação jurídica/normativa elaborada

**Políticas (16 documentos .docx):**
1. Aviso de Privacidade (versão web)
2. Política BYOD (dispositivos pessoais)
3. Política de Backup
4. Política de Compartilhamento de dados
5. Política de Descarte de Documentos
6. Política de Mesa e Tela Limpa
7. Política de Privacidade (geral)
8. Política de Retenção de Dados
9. Política de Segurança da Informação (PSI)
10. Política de Uso de Celulares — Cartórios (x2 versões)
11. Política de Uso de Imagem
12. Política Privacy by Design
13. Procedimento para Análise de Legítimo Interesse
14. Procedimento para Elaboração do RIPD
15. Registro de resposta-ocorrência do Titular do Dado
16. Ciclo de Vida (planilhas XLSX)

**Status:** Documentos existem, têm versionamento, mas **execução é parcial** — faltam comunicação, treinamento, responsáveis designados.

### 3.5 Conformidade com Provimento 213/2026

O Plano de Ação LGPD da INOVA conecta-se com o Provimento CNJ nº 213/2026 em múltiplos pontos:

| Bloco CNJ 213 | Ação LGPD relacionada | Status |
|---|---|---|
| **G — Governança e Políticas** | AC-04 PSI, AC-05 Privacidade, AC-06 Cookies, AC-08 Prog. Gov. | Parcial |
| **A — Controle de Acesso** | AC-10 Consentimento, AC-16 DPO divulgado | Pendente |
| **C — Backup** | AC-14 Política de Backup | ✅ Concluído |
| **T — Trilhas de Auditoria** | AC-11 Treinamento, AC-22 RIPD, AC-23 LI | Parcial |
| **I — Gestão de Incidentes** | AC-25 Plano de Resposta | Pendente ⚠️ |
| **D — Dossiê Técnico** | Todas as ações geram evidências | Parcial |

**Lacuna crítica:** O Plano de Ação LGPD não cobre explicitamente alguns requisitos CNJ 213:
- Auditoria de infraestrutura (RTO/RPO — arcabouço técnico, não jurídico)
- Segmentação de rede e controle de acesso técnico
- Antivírus e proteção de endpoints
- Auditoria de acesso remoto do suporte

Isso é esperado — LGPD é jurídico-operacional; CNJ 213 é técnico-regulatório. Ambos devem ser coordenados.

---

## 4. Leitura Estruturada do Plano de Ação.csv

### Estrutura do CSV

**Colunas:**
- ID Ação (AC-01 a AC-25)
- Atividade/Entregável (título descritivo)
- Categoria (Governança, Preparação, Implantação)
- Ações (descrição HTML)
- Justificativa da ação
- Departamento/Unidade (TI, RH, ***, Cliente, InovaLGPD)
- Tipo de Ação (Obrigatório, Recomendação)
- Nível de Prioridade (Alta, Média)
- Responsável Executante (InovaLGPD, Cliente)
- Data Passagem (quando foi passada para execução)
- Data Previsão (data alvo original)
- Data Conclusão (data real de conclusão, se houver)
- Status (Pendente, Finalizada)
- Observação / Detalhe da ação

### Padrões observados

1. **Ações finalizadas:** todas têm "Data Passagem", "Data Previsão" e "Data Conclusão" preenchidas → rastreabilidade clara
2. **Ações pendentes:** têm "Data Passagem" e "Data Previsão", mas **sem Data Conclusão** → falta execução
3. **15 ações sem data:** não têm sequer "Data Passagem" preenchida → ainda não foram atribuídas
4. **Responsáveis:**
   - InovaLGPD: 7 ações (assessoria jurídica)
   - Cliente (Cartório): 18 ações (execução interna)
5. **Tipos:**
   - Obrigatório: 13 ações (LGPD ou CNJ exige)
   - Recomendação: 12 ações (boas práticas)

### Mapeamento por categoria

**Governança (14 ações):**
- AC-03, AC-04, AC-05, AC-06, AC-08, AC-09, AC-10, AC-11, AC-14, AC-19, AC-22, AC-23, AC-24, AC-25
- Foco: políticas, procedimentos, programas de consciência, gestão

**Preparação (2 ações):**
- AC-02, AC-01
- Foco: identificação e levantamento

**Implantação (9 ações):**
- AC-07, AC-15, AC-16, AC-17, AC-18, AC-20, AC-21, AC-12, AC-13
- Foco: colocar em operação; exigem ação técnica e/ou administrativa

---

## 5. Status dos Principais Entregáveis

### 5.1 Entregáveis jurídicos/documentais

| Entregável | Status | Versão | Localização | Obs. |
|---|---|---|---|---|
| Política de Privacidade | ✅ Concluído | 1.0 | LGPD-inova/Politicas | Publicada |
| Política de Segurança da Informação | ✅ Concluído | 1.0 | LGPD-inova/Politicas | PSI base |
| Política de Descarte de Documentos | ✅ Concluído | 1.0 | LGPD-inova/Politicas | Operacional |
| Aviso de Privacidade (web) | ✅ Concluído | 1.0 | LGPD-inova/Politicas | Para site |
| Ciclo de Vida / Tabela de Temporalidade | ✅ Concluído | 1.0 | LGPD-inova/Ciclo Vida | Planilha |
| RIPD — Procedimento | ✅ Concluído | 1.0 | LGPD-inova/Politicas | Template |
| Legítimo Interesse — Procedimento | ✅ Concluído | 1.0 | LGPD-inova/Politicas | Template |
| Inventário de Dados Pessoais (RAT/ROPa) | ✅ Concluído | 1.0 | Plataforma INOVA | 38 atividades |
| **DPO — Nomeação formal** | ❌ Pendente | — | — | AC-15 — crítica |
| **DPO — Divulgação no site** | ❌ Pendente | — | — | AC-16 — crítica |
| **Programa de Governança** | ❌ Pendente | — | — | AC-08 — estruturante |
| **Programa de Treinamento** | ❌ Pendente | — | — | AC-11 — crítica |
| **Plano de Resposta a Incidentes** | ❌ Pendente | — | — | AC-25 — cnj213 |
| **Política de Cookies** | ❌ Pendente | — | — | AC-06 — obrigatória |
| **Política de Retenção** | ❌ Pendente | — | — | AC-24 — obrigatória |
| **Contratos (análise LGPD)** | ⏳ Em avaliação | — | LGPD-inova/Contratos | AC-12 — INOVA |
| **Parecer Final de Contratos** | ✅ Parecer emitido | 1.0 | LGPD-inova/Contratos | INOVA completou |
| **Aditivos contratuais (operador)** | 🟡 Parcial | 1.0 | LGPD-inova/Contratos | Negociação |
| **Avaliação de Fornecedores** | ❌ Pendente | — | — | AC-13 — INOVA |
| **Base de Titulares** | ❌ Pendente | — | — | AC-20 — implantação |
| **Plataforma de Privacidade (integração)** | ❌ Bloqueada | Beta | Plataforma INOVA | Erro de chave |

### 5.2 Informações já disponíveis que podem ser importadas

1. ✅ **Plano de Ação completo** — estruturado, com datas, responsáveis, status
2. ✅ **14 Políticas/procedimentos** — .docx versionados, prontos para gestão
3. ✅ **Ciclo de Vida** — tabela de retenção por tipo de documento
4. ✅ **Contratos analisados** — aditivos, pareceres, análise de conformidade
5. ✅ **38 Atividades de Tratamento** — mapeadas na plataforma INOVA (exportar por API?)
6. ✅ **Treinamentos** — 20+ certificados, listas de presença
7. ⏳ **Plataforma LGPD da INOVA** — aguardando resolução de integração

### 5.3 Lacunas e o que precisa ser revisado

| Item | Situação | Ação necessária |
|---|---|---|
| **DPO designado** | Não designado formalmente | Enviar para gestor/jurídico |
| **Responsáveis pelas ações** | Parcialmente atribuído | Revisar AC-01..25; designar ownership |
| **Datas de conclusão** | 15 ações sem data | Estimativa de timing com gestor |
| **Evidências de execução** | Políticas existem; implementação desconhecida | Auditar departamentos (RH, TI, etc.) |
| **Comunicação de políticas** | Não há registro formal | Criar trilha de comunicação/ciência |
| **Integração plataforma INOVA** | Bloqueada — erro de chave | Contato com suporte INOVA |

---

## 6. Relação entre LGPD, Provimento 213 e Auditoria Técnica

### 6.1 Matriz de correlação

```
LGPD (jurídico-operacional)
  ↓
Plano de Ação da INOVA (25 ações)
  ↓
Conformidade técnica
  ↓
Provimento CNJ 213/2026 (técnico-regulatório)
  ↓
Cartório System (instrumentalização)
  ↓
Dossiê Técnico para Vistoria
```

### 6.2 Áreas de intersecção crítica

| Área | Demanda LGPD | Demanda CNJ 213 | Cartório System |
|---|---|---|---|
| **Auditoria de dados** | AC-17: Inventário RAT/ROPa | Bloco T: Trilhas de Auditoria | Módulo Audit: scanners + findings |
| **Segurança de acesso** | AC-10: Consentimento | Bloco A: Autenticação + MFA | Auth multiusuário (Etapa C) |
| **Incidentes** | AC-25: Plano de resposta | Bloco I: Comunicação 72h | AuditAction: registro formal |
| **Backup** | AC-14: Política | Bloco B: RPO ≤4h, RTO ≤8h | Infraestrutura (fora do Sistema) |
| **Retenção** | AC-24: Política de Retenção | Bloco D: Dossiê ≥5 anos | Módulo LGPD: rastreabilidade |
| **Documentação** | Todas — evidência | Bloco D: Dossiê com hashes | Módulo Audit + LGPD: manifest |
| **Conformidade** | Todas — demonstração | Bloco F: Vistoria | Dashboard integrado (Audit + LGPD) |

### 6.3 Lições da Auditoria Técnica (diagnóstico maio/2026)

Riscos identificados que **conectam com LGPD:**

1. **Backup sem dump consistente do Engegraph**
   - LGPD: AC-14 exige política de backup
   - CNJ 213: B-04 exige dump transacional
   - **PROBLEMA:** Cobian copia arquivos; dados pessoais podem estar corrompidos em restauração

2. **Ausência de VPN; acesso remoto do suporte Engegraph sem auditoria**
   - LGPD: AC-10, AC-23 exigem rastreabilidade
   - CNJ 213: A-06, T-01, T-04 exigem auditoria de acesso
   - **PROBLEMA:** Suporte remoto pode acessar dados pessoais sem trilha

3. **Disco D em situação crítica; sem monitoramento**
   - LGPD: AC-24 retenção exige espaço; AC-14 backup exige espaço
   - CNJ 213: B-06 monitoramento de backup
   - **PROBLEMA:** Falta de espaço pode causar interrupção de backup

4. **Sem controle de acesso formal; permissões NTFS não configuradas**
   - LGPD: AC-01, AC-10 exigem segregação
   - CNJ 213: A-05, T-01 exigem matriz de acesso
   - **PROBLEMA:** Dados pessoais podem ser acessados por pessoa não autorizada

---

## 7. Mapa de Lacunas Atuais

### 7.1 Lacunas entre Plano de Ação LGPD e Execução

| Categoria | Lacuna | Impacto | Módulo LGPD pode ajudar? |
|---|---|---|---|
| **Rastreabilidade de ações** | Nenhum sistema registra quem fez o quê, quando | Impossível auditar; perda de evidência | ✅ Sim — centralizar evidências |
| **Acompanhamento de prazos** | 15 ações sem data; 14 pendentes sem owner claro | Paralisia; falta de accountability | ✅ Sim — trilha de status |
| **Evidências documentais** | Políticas existem; mas implementação não é registrada | INOVA não tem prova de execução | ✅ Sim — upload + metadados |
| **Comunicação de políticas** | Não há registro de "ciência" dos colaboradores | Risco jurídico; não comprovável | ✅ Sim — termo de ciência |
| **Consentimento de colaboradores** | AC-10 exige coleta; mas sem ferramenta | Sem base legal; não exportável | ⏳ Depois — integração com plataforma |
| **Integração com plataforma INOVA** | Chave de integração não funciona; isolamento | Dados não sincronizados | ❌ Não — problema operacional INOVA |
| **Relação AC ↔ Políticas** | CSV lista ações; políticas são documentos soltos | Sem vinculação; difícil rastrear dependências | ✅ Sim — matriz de rastreabilidade |
| **Conformidade CNJ 213** | Plano LGPD não mapeia explicitamente requisitos CNJ | Dois roadmaps separados; desalinhados | ✅ Sim — dashboard integrado |

### 7.2 Lacunas entre Cartório System e Necessidades LGPD

| Necessidade LGPD | Situação Cartório System | Gap | Módulo LGPD resolve? |
|---|---|---|---|
| **Rastreabilidade de operações** | Módulo Audit (findings) — não de dados pessoais | Trilhas não coletam dados sensíveis | ✅ Sim — logs segregados |
| **Auditoria de acesso** | Auth ainda não implementada (Etapa C) | Sem trilha de quem acessou quê | ⏳ Depois — depende de Auth |
| **Retenção de dados** | Sem política de purge de dados obsoletos | Dados antigos podem permanecer | ⏳ Depois — módulo de governance |
| **Portabilidade** | Exports existem (`exports/atlas/`); mas sem manifest | Sem checksum; não rastreável | ⏳ Depois — integração com Audit |
| **Incidentes** | AuditAction (CRUD de ações) — não específico LGPD | Sem formulário de "incidente de privacidade" | ✅ Sim — entidade específica |
| **Dossier integrado** | Audit gera manifests; LGPD geraria políticas | Documentos separados; sem índice único | ✅ Sim — no LgpdReport |

---

## 8. Proposta de Criação do Módulo LGPD

### 8.1 Objetivo do módulo

O módulo LGPD do Cartório System é a **ferramenta de operacionalização, rastreamento e evidenciação** do Plano de Ação LGPD.

**Funções principais:**
1. Centralizar o Plano de Ação em banco estruturado
2. Registrar evidências de execução (documentos, screenshots, atestados)
3. Rastrear responsáveis, prazos e status de cada ação
4. Gerar relatórios de conformidade para INOVA, gestor e vistoria
5. Integrar-se ao módulo Audit para criar um **dossiê técnico unificado**

**O módulo NÃO substitui:**
- Assessoria jurídica (papel da INOVA)
- Elaboração de políticas (papel da INOVA)
- Decisões de negócio (papel do gestor)

**O módulo APOIA:**
- Organização e centralização de documentos
- Rastreamento de quem faz o quê e quando
- Geração de relatórios de status
- Preparação para auditorias e vistoria

### 8.2 Princípios de design

1. **Segregação clara:** módulo LGPD não toca dados operacionais; apenas políticas, ações, evidências
2. **Compatibilidade com Audit:** ambos alimentam o dossiê técnico (Fase 10 do módulo Audit)
3. **Read-only para dados sensíveis:** LGPD captura metadados apenas; nunca nomes de titulares ou dados pessoais
4. **Imutabilidade de ações:** uma ação criada não pode ser deletada; apenas seu status muda
5. **Rastreabilidade completa:** quem criou, quando, qual versão de politica, qual evidência
6. **Independência de INOVA:** funciona mesmo se integração com plataforma INOVA estiver bloqueada
7. **Conformidade com CNJ 213:** todos os artefatos gerados contêm hash, timestamp, responsável

### 8.3 Relação com o módulo Audit

```
Cartório System — Módulos de Governança

app/modules/
├── audit/                           # Sprint 1 ✅, Sprint 2 próximo
│   ├── scanner/                     # file inventory read-only
│   ├── findings/                    # AuditFinding CRUD
│   ├── diagnosis/                   # DocumentDiagnosis (Sprint 3)
│   └── (fases futuras)
│
└── lgpd/                            # Proposto — paralelo com Audit Sprint 2
    ├── actions/                     # LgpdAction CRUD (plano)
    ├── evidences/                   # LgpdEvidence (documentos)
    ├── policies/                    # PolicyDocument (referência)
    ├── processing_records/          # ProcessingActivity (RAT/ROPa)
    ├── training/                    # TrainingRecord (capacitação)
    ├── vendors/                     # VendorAssessment (fornecedores)
    ├── incidents/                   # PrivacyIncident (resposta)
    └── reports/                     # LgpdReport (dashboard + export)

Integração no dossiê (Fase 10):
  Audit artifacts + LGPD artifacts → _VISTORIA/ (estrutura única)
```

---

## 9. Escopo Inicial Recomendado (MVP)

O MVP do módulo LGPD deve ser **mínimo, coeso, implementável em 2-3 sprints**.

### 9.1 Sprint LGPD-1: Importação e Rastreamento de Ações

**Objetivo:** Trazer o Plano de Ação LGPD para banco estruturado e criar interface de acompanhamento.

**Entidades:**
- `LgpdAction` (importação do CSV; vinculação a políticas)
- `LgpdActionOwner` (responsável, departamento, contato)

**Funcionalidades:**
- POST/GET/UPDATE `LgpdAction` (criar, ler, atualizar status)
- GET `/api/v1/lgpd/actions?status=pending` (filtrar por status)
- GET `/api/v1/lgpd/actions/summary` (resumo de execução: 11/25 concluídas, etc.)
- GET `/api/v1/lgpd/actions/{id}/timeline` (linha do tempo: criação → conclusão)

**Saídas esperadas:**
- Relatório `lgpd_actions_status.csv` (exportável para planilha)
- Dashboard simples (% concluído, próximos prazos, atrasadas)
- Logs de mudança de status (quem, quando, motivo)

**Testes:**
- CRUD de ações
- Validação de transições de status (pending → in_progress → completed)
- Exportação CSV com metadados
- Filtros por categoria, prioridade, responsável

**Critério de pronto:**
- 100% dos 25 itens do Plano de Ação importados
- Dashboard mostra 44% de conclusão (11/25)
- Relatório exportável em CSV
- Testes passando; ruff limpo

### 9.2 Sprint LGPD-2: Gestão de Evidências

**Objetivo:** Permitir upload e rastreamento de documentos, políticas e evidências de execução.

**Entidades:**
- `LgpdEvidence` (tipo: policy, screenshot, ata, certificado, parecer, etc.)
- `PolicyDocument` (referência para políticas já elaboradas)
- `TrainingRecord` (registros de capacitação: data, participantes, certificado)

**Funcionalidades:**
- POST `/api/v1/lgpd/evidences` (upload de arquivo + metadados)
- GET `/api/v1/lgpd/policies` (lista de políticas versionadas)
- GET `/api/v1/lgpd/evidences?action_id=AC-15` (evidências de uma ação)
- GET `/api/v1/lgpd/training` (relatório de treinamentos)

**Saídas esperadas:**
- Pasta `_VISTORIA/01_Evidencias_LGPD/` com cópias organizadas
- Manifesto `lgpd_evidence_manifest.json` (arquivo, hash, tipo, ação vinculada)
- Relatório `lgpd_training_report.csv` (participantes, datas, certificados)

**Testes:**
- Upload de arquivo (validação de tamanho, tipo)
- Cálculo de hash SHA-256
- Vinculação de evidência a ação
- Exportação de manifesto
- Validação de política versionada

**Critério de pronto:**
- 14 políticas importadas e versionadas
- Mínimo 2 evidências por ação finalizada
- Manifesto gerado com hashes
- Dashboard mostra "evidências por ação"

### 9.3 Sprint LGPD-3: Relatórios de Conformidade

**Objetivo:** Gerar relatórios de status, conformidade e rastreabilidade.

**Relatórios:**
1. `lgpd_status_summary.md` — panorama geral (11/25 concluídas, 14 pendentes, etc.)
2. `lgpd_action_detail.md` — detalhe por ação (descrição, responsável, prazos, evidências)
3. `lgpd_conformity_report.csv` — matriz de ações vs. requisitos CNJ 213
4. `lgpd_training_summary.xlsx` — consolidação de treinamentos (participantes, datas, certificados)

**Funcionalidades:**
- GET `/api/v1/lgpd/reports/status` → JSON com dashboard
- GET `/api/v1/lgpd/reports/export?format=pdf` → relatório formatado
- GET `/api/v1/lgpd/reports/conformity?mapping=cj213` → matriz de conformidade

**Saídas esperadas:**
- Relatórios em Markdown, CSV, JSON para fácil integração
- Dashboard em JSON para frontend futura
- Preparação para dossiê técnico (Fase 10 do Audit)

**Testes:**
- Geração de todos os formatos
- Validação de números (totais batem)
- Verificação de hashes nos manifests
- Conformidade com estrutura do dossiê

**Critério de pronto:**
- 4 relatórios principais gerados
- Números validados
- Dashboard integrado a `/api/v1/`

---

## 10. Não-Escopo Inicial

**Essas funcionalidades ficam para fases posteriores:**

1. ❌ **Integração com plataforma INOVA** — Bloqueia por erro de chave (problema operacional)
2. ❌ **Coleta de consentimento de colaboradores (AC-10)** — Requer ferramenta especializada; deixar em fase 2
3. ❌ **Monitoramento de titulares (AC-20)** — Requer integração com banco de titulares externo
4. ❌ **Dashboard visual/gráfico** — Focar em relatórios estruturados (CSV, JSON); UI vem depois
5. ❌ **Avaliação de fornecedores (AC-13)** — Ainda em andamento com INOVA; deixar para phase 2
6. ❌ **Incidentes de privacidade** — Fases iniciais não precisam de CRUD completo; deixar para Sprint 4
7. ❌ **Auditoria de processamento (RIPD detalhado)** — Depende de rastreamento operacional (Etapa D)
8. ❌ **Integração com módulo de Auditoria** — Ambos geram manifests separados (unificação em Fase 10)
9. ❌ **Autenticação multiusuário** — Usa autenticação futura do Cartório System (Etapa C)
10. ❌ **Export para ANPD/autoridades** — Deixar para fase de maturidade

---

## 11. Modelo de Domínio Sugerido

### 11.1 Entidades candidatas (fase 1-3)

```
LgpdAction ─────────┬───── LgpdActionOwner
   (ação do plano)  │      (responsável)
                    ├───── LgpdEvidence
                    │      (documentos)
                    └───── LgpdActionStatus
                           (histórico de status)

PolicyDocument
   (políticas versionadas)
   ├─── Relationships: linked_to_actions
   └─── Versioning: policy_version

TrainingRecord
   (capacitação de colaboradores)
   ├─── participant: name
   ├─── training_date: date
   └─── certificate_hash: sha256

ProcessingActivity (RAT/ROPa)
   (38 atividades de tratamento de dados)
   ├─── activity_name: str
   ├─── purpose: str
   ├─── data_categories: list
   ├─── legal_basis: enum
   └─── linked_policy: FK→PolicyDocument
```

### 11.2 Entidades para fases posteriores

```
PrivacyIncident (Sprint 4+)
   ├── incident_date
   ├── type: enum (breach, unauthorized_access, etc.)
   ├── affected_data_count
   ├── response_actions: list
   └── reported_to_authorities: bool

VendorAssessment (Sprint 4+)
   ├── vendor_name
   ├── risk_level: enum
   ├── contract_reviewed: bool
   ├── compliance_status
   └── last_assessment_date

DpoRecord (Sprint 5+)
   ├── dpo_name
   ├── contact_email
   ├── designation_date
   └── published_on_website: bool

LegitimateInterestAssessment (Sprint 5+)
   ├── assessment_name
   ├── purpose
   ├── risk_level
   └── approval_date
```

### 11.3 Campos mínimos por entidade (fase 1-3)

#### LgpdAction

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| id | UUID | Sim | Identificador único |
| action_code | string | Sim | AC-01, AC-02, etc. (única) |
| activity_name | string | Sim | Título (ex.: "Nomeação do DPO") |
| category | enum | Sim | Governança, Preparação, Implantação |
| description | text | Sim | Descrição detalhada |
| action_type | enum | Sim | Obrigatório, Recomendação |
| priority | enum | Sim | Alta, Média |
| responsible_department | string | Não | TI, RH, Jurídica, etc. |
| owner_id | FK | Não | Responsável (LgpdActionOwner) |
| status | enum | Sim | Pendente, Em Progresso, Concluída |
| date_created | datetime | Sim | Quando foi criada |
| date_planned | date | Não | Data alvo original |
| date_completed | date | Não | Data real de conclusão |
| notes | text | Não | Observações |
| created_by | string | Sim | Quem registrou (gestor) |
| updated_by | string | Sim | Último a atualizar |
| updated_at | datetime | Sim | Último update |

#### LgpdEvidence

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| id | UUID | Sim | Identificador único |
| action_id | FK | Sim | Ação à qual pertence |
| evidence_type | enum | Sim | policy, screenshot, ata, certificado, parecer, email, etc. |
| file_name | string | Sim | Nome do arquivo original |
| file_path | string | Não | Caminho relativo em `_VISTORIA/` |
| file_hash | string | Não | SHA-256 do arquivo |
| description | string | Não | O que é a evidência |
| collected_date | date | Sim | Quando foi coletada |
| collected_by | string | Sim | Quem coletou |
| confidentiality_level | enum | Não | Public, Internal, Restricted, Confidential |
| linked_policy | FK | Não | PolicyDocument, se aplicável |
| created_at | datetime | Sim | Timestamp |

#### PolicyDocument

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| id | UUID | Sim | Identificador único |
| policy_code | string | Sim | PSI, Privacidade, Cookies, etc. |
| policy_name | string | Sim | Nome completo |
| current_version | string | Sim | 1.0, 1.1, 2.0, etc. |
| file_path | string | Sim | Caminho ao .docx original |
| published_date | date | Não | Quando foi publicada |
| next_review_date | date | Não | Próxima data de revisão |
| legal_requirement | string | Não | LGPD Art. X, CNJ 213 Bloco Y, etc. |
| approval_by | string | Não | Quem aprovou (gestor/jurídico) |
| linked_actions | list[FK] | Não | Ações que dependem dessa política |
| created_at | datetime | Sim | Timestamp |

#### TrainingRecord

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| id | UUID | Sim | Identificador único |
| training_name | string | Sim | "LGPD para colaboradores", "Segurança de dados", etc. |
| training_date | date | Sim | Quando foi realizado |
| participant_name | string | Sim | Nome do participante |
| certificate_hash | string | Não | SHA-256 do certificado |
| certificate_file | string | Não | Caminho ao arquivo |
| duration_minutes | int | Não | Duração em minutos |
| trainer | string | Não | Quem ministrou |
| action_id | FK | Não | AC-11 (Treinamento e Conscientização) |
| created_at | datetime | Sim | Timestamp |

---

## 12. Entidades Candidatas — Avaliação de Necessidade

| Entidade | Finalidade | Campos | Prioridade | MVP? | CNJ 213 | Audit | Plano |
|---|---|---|---|---|---|---|---|
| **LgpdAction** | Rastreamento do Plano de Ação | id, code, name, status, owner, dates | **Crítica** | ✅ Sprint 1 | Sim (conformidade) | Sim (findings) | AC-01..25 |
| **LgpdEvidence** | Gestão de documentos/políticas | id, action_id, type, file, hash, date | **Crítica** | ✅ Sprint 2 | Sim (dossiê) | Sim (manifest) | Políticas |
| **ProcessingActivity** | Inventário RAT/ROPa | id, activity, purpose, data_types, legal_basis | **Alta** | ⏳ Sprint 3 | Sim (A-01) | Não | AC-17 |
| **PolicyDocument** | Referência de políticas | id, code, version, path, approval | **Alta** | ✅ Sprint 2 | Sim (gov) | Não | Todas as políticas |
| **TrainingRecord** | Registro de capacitação | id, date, participant, certificate, duration | **Alta** | ✅ Sprint 2 | Sim (treinamento) | Não | AC-11 |
| **DataSubjectRequest** | Solicitações de titulares | id, request_type, date, response_date, status | **Média** | ⏳ Sprint 4 | Sim (direitos) | Não | AC-20 |
| **VendorAssessment** | Avaliação de fornecedores | id, vendor, risk_level, reviewed, assessment_date | **Média** | ⏳ Sprint 4 | Sim (terceiros) | Não | AC-13 |
| **PrivacyIncident** | Incidentes de privacidade | id, date, type, affected_count, response, reported | **Média** | ⏳ Sprint 4 | Sim (incidentes) | Sim (findings) | AC-25 |
| **DpoRecord** | Registro do DPO | id, name, email, designation_date, published | **Média** | ⏳ Sprint 3 | Sim (DPO) | Não | AC-15/16 |
| **LegitimateInterestAssessment** | Avaliações de LI | id, assessment, purpose, risk, approval_date | **Baixa** | ⏳ Sprint 5 | Não | Não | AC-23 |
| **RipdRecord** | Registros de RIPD | id, assessment_name, date, risk_level, approval | **Baixa** | ⏳ Sprint 5 | Não | Não | AC-22 |
| **ComplianceReport** | Relatórios agregados | id, report_type, generated_date, data, hash | **Alta** | ✅ Sprint 3 | Sim (dossiê) | Sim (manifest) | Todas |

**Legenda:**
- ✅ Sprint 1/2/3: Incluir no MVP
- ⏳ Sprint 4/5: Deixar para depois
- **Prioridade:** Crítica (MVP absoluto), Alta (importante), Média (desejável), Baixa (futuro)
- **CNJ 213:** Requisito do Provimento
- **Audit:** Integração com módulo Audit
- **Plano:** Relação com ações do Plano LGPD

---

## 13. Use Cases Candidatos

### 13.1 Use cases do MVP (Sprint 1-3)

#### UC-LGPD-01: Importar Plano de Ação

**Ator:** Gestor ou administrador do sistema

**Pré-condições:** Plano de Ação.csv disponível

**Fluxo principal:**
1. Usuário faz POST `/api/v1/lgpd/actions/import` com CSV
2. Sistema valida: 25 linhas, colunas esperadas, sem duplicatas
3. Sistema cria 25 registros LgpdAction
4. Sistema retorna relatório de importação: "25 ações importadas com sucesso"

**Pós-condições:** Dashboard mostra 11 concluídas, 14 pendentes

#### UC-LGPD-02: Atualizar Status de Ação

**Ator:** Gestor ou responsável pela ação

**Pré-condições:** Ação AC-XX existe; status = pending

**Fluxo principal:**
1. Usuário acessa GET `/api/v1/lgpd/actions/AC-15` (DPO)
2. Sistema mostra: "Status: Pendente | Responsável: [vazio] | Prazos: original 30/03, atual [vazio]"
3. Usuário faz PATCH `/api/v1/lgpd/actions/AC-15` { status: "in_progress", owner: "Gestor", due_date: "2026-06-15" }
4. Sistema registra mudança com timestamp
5. Dashboard atualiza: AC-15 agora "Em Progresso"

**Pós-condições:** Log de mudança criado; auditável

#### UC-LGPD-03: Anexar Evidência a Ação

**Ator:** Gestor

**Pré-condições:** Ação AC-XX existe; arquivo disponível (policy .docx, screenshot, ata)

**Fluxo principal:**
1. Usuário acessa ação AC-04 (PSI)
2. Usuário clica "Anexar Evidência"
3. Sistema POST `/api/v1/lgpd/actions/AC-04/evidences` { file: "98 - Politica_Seguranca_Informacao.docx", type: "policy", collected_date: "2023-03-10" }
4. Sistema calcula SHA-256; armazena em `_VISTORIA/01_Evidencias_LGPD/AC-04/`
5. Sistema retorna: "Evidência anexada: 98 - Politica...docx (hash: abc123...)"

**Pós-condições:** Evidência rastreável; manifesto atualizado

#### UC-LGPD-04: Gerar Relatório de Conformidade

**Ator:** Gestor (prepara para INOVA ou vistoria)

**Pré-condições:** Mínimo 11 ações marcadas como concluídas

**Fluxo principal:**
1. Usuário acessa GET `/api/v1/lgpd/reports/status`
2. Sistema retorna JSON: { total_actions: 25, completed: 11, pending: 14, no_date: 15 }
3. Usuário acessa GET `/api/v1/lgpd/reports/export?format=pdf`
4. Sistema gera PDF com:
   - Sumário executivo (44% concluído)
   - Tabela de ações (status, responsável, prazos, evidências)
   - Diagrama de Gantt (timeline visual)
   - Hashes de todos os arquivos anexados
5. Sistema salva em `_VISTORIA/04_Relatorios_LGPD/lgpd_compliance_report_20260505.pdf`

**Pós-condições:** Relatório assinado com data; pronto para submissão

#### UC-LGPD-05: Consultar Políticas e Procedimentos

**Ator:** Colaborador; Gestor

**Pré-condições:** Políticas importadas

**Fluxo principal:**
1. Usuário acessa GET `/api/v1/lgpd/policies`
2. Sistema retorna lista: PSI v1.0, Privacidade v1.0, Descarte v1.0, etc.
3. Usuário clica em "Privacidade v1.0"
4. Sistema mostra: arquivo, versão, data de publicação, próxima revisão, link para download
5. Usuário faz download do .docx original

**Pós-condições:** Política acessível; rastreável

### 13.2 Use cases secundários (Sprint 3+)

#### UC-LGPD-06: Registrar Treinamento Realizado

**Ator:** Gestor (RH ou responsável)

**Pré-condições:** Ação AC-11 (Treinamento) existe

**Fluxo principal:**
1. Usuário POST `/api/v1/lgpd/training` { training_name: "LGPD para RH", training_date: "2026-05-15", participants: ["João", "Maria"], certificate_hash: "def456..." }
2. Sistema vincula ao AC-11
3. Sistema cria 2 registros TrainingRecord (um por participante)
4. Dashboard mostra: "AC-11: 2 de N colaboradores treinados"

#### UC-LGPD-07: Mapear RAT/ROPa (Inventário de Atividades)

**Ator:** Gestor ou TI (preparação para AC-17)

**Pré-condições:** ProcessingActivity importada da plataforma INOVA (38 atividades)

**Fluxo principal:**
1. Sistema GET `/api/v1/lgpd/processing-activities?status=all`
2. Retorna lista: "Abertura de protocolo", "Recepção de documentos", etc. (38 registros)
3. Usuário clica em uma atividade
4. Sistema mostra: dados envolvidos, legal basis, política vinculada, risco
5. Dashboard gera mapa: atividades por tipo, distribuição de risco, conformidade por atividade

#### UC-LGPD-08: Registrar Incidente de Privacidade

**Ator:** Gestor ou responsável de segurança (para AC-25)

**Pré-condições:** Incidente ocorreu; necessário registro formal

**Fluxo principal:**
1. Usuário POST `/api/v1/lgpd/incidents` { incident_type: "unauthorized_access", date: "2026-05-10", description: "...", affected_records: 5 }
2. Sistema cria PrivacyIncident
3. Sistema avalia: "Notificação ANPD necessária? Sim (critério 48h úteis)"
4. Sistema marca AC-25 (Plano de Resposta) como testado
5. Dashboard mostra: "Incidente #1 em progresso | Prazo ANPD: 2026-05-13"

---

## 14. Relatórios Candidatos

### 14.1 Relatórios do MVP (Sprint 1-3)

#### R-01: Resumo de Execução (Dashboard JSON)

**Gerado por:** `GET /api/v1/lgpd/reports/status`

**Conteúdo:**
```json
{
  "report_date": "2026-05-05",
  "total_actions": 25,
  "completed": 11,
  "in_progress": 0,
  "pending": 14,
  "no_date": 15,
  "completion_percentage": 44,
  "actions_by_category": {
    "Governança": { "total": 14, "completed": 10 },
    "Preparação": { "total": 2, "completed": 0 },
    "Implantação": { "total": 9, "completed": 1 }
  },
  "actions_by_priority": {
    "Alta": { "total": 13, "completed": 6, "pending": 7 },
    "Média": { "total": 12, "completed": 5, "pending": 7 }
  },
  "overdue_actions": [
    { "code": "AC-15", "name": "Nomeação do DPO", "original_due": "2023-03-10", "days_overdue": 787 },
    ...
  ],
  "next_milestones": [
    { "code": "AC-08", "name": "Programa de Governança", "estimated_due": "2026-06-15" },
    ...
  ]
}
```

#### R-02: Plano de Ação Estruturado (CSV)

**Gerado por:** `GET /api/v1/lgpd/actions/export?format=csv`

**Colunas:**
- action_code, activity_name, category, priority, status, owner, date_planned, date_completed, evidence_count, notes

#### R-03: Matriz de Conformidade (CSV)

**Gerado por:** `GET /api/v1/lgpd/reports/conformity?mapping=cj213`

**Mapeamento:**
- AC-XX → CNJ 213 Bloco (G/A/C/T/I/D) → Status (✅/❌/⏳)

#### R-04: Inventário de Evidências (JSON Manifest)

**Gerado por:** `GET /api/v1/lgpd/evidences/manifest`

**Conteúdo:**
```json
{
  "generated_date": "2026-05-05T10:30:00Z",
  "total_evidences": 22,
  "evidences": [
    {
      "id": "ev-001",
      "action_id": "AC-04",
      "file_name": "98 - Politica_Seguranca_Informacao.docx",
      "file_path": "_VISTORIA/01_Evidencias_LGPD/AC-04/98-PSI.docx",
      "file_hash": "sha256:abc123...",
      "evidence_type": "policy",
      "collected_date": "2023-03-10",
      "collected_by": "InovaLGPD"
    },
    ...
  ]
}
```

#### R-05: Relatório de Treinamentos (CSV)

**Gerado por:** `GET /api/v1/lgpd/training/report?export=csv`

**Colunas:**
- training_name, training_date, participant_name, certificate_hash, duration, trainer

### 14.2 Relatórios secundários (Sprint 3+)

- **R-06:** Consolidação de Incidentes (histórico, status, resposta)
- **R-07:** Avaliação de Fornecedores (nível de risco, conformidade, pendências)
- **R-08:** Rastreamento de RAT/ROPa (38 atividades, distribuição de risco)
- **R-09:** Status do Dossiê Técnico (preparação para vistoria)
- **R-10:** Relatório de DPO (nomeação, contato, publicação)

---

## 15. Evidências e Dossiê Técnico

### 15.1 Tipos de evidências que o módulo captura

| Tipo | Exemplo | Armazenamento | Hash? |
|---|---|---|---|
| **Policy** | 98-PSI.docx | `_VISTORIA/01_Evidencias/AC-04/` | Sim |
| **Screenshot** | ac-15-dpo-site.png | `_VISTORIA/01_Evidencias/AC-16/` | Sim |
| **Ata** | ata_reuniao_governanca_20260505.pdf | `_VISTORIA/01_Evidencias/AC-08/` | Sim |
| **Certificado** | certificado_lgpd_joao_20260501.pdf | `_VISTORIA/04_Treinamentos/` | Sim |
| **Parecer jurídico** | parecer_contratos_final.docx | `_VISTORIA/01_Evidencias/AC-12/` | Sim |
| **Email formal** | email_designacao_dpo_20260505.eml | `_VISTORIA/01_Evidencias/AC-15/` | Sim |
| **Planilha** | ciclo_vida_v1.xlsx | `_VISTORIA/02_Documentacao/` | Sim |
| **Configuração** | screenshot_mfa_ativo.png | `_VISTORIA/Seguranca/` | Sim |

### 15.2 Integração com módulo Audit

O módulo LGPD gera artefatos estruturados que alimentam o dossiê técnico:

```
Fase 10 — Dossiê Técnico (Audit module)

_VISTORIA/
├── 00_Indice_Hashes.xlsx       ← Índice mestre de TODOS os docs
├── 01_Governanca/
│   ├── PSI/
│   ├── Politicas/              ← LGPD fornece aqui
│   └── ...
├── 01_Evidencias_LGPD/         ← LGPD fornece aqui
│   ├── AC-04/
│   │   ├── 98-PSI.docx
│   │   └── manifest.json
│   ├── AC-15/
│   │   ├── email_designacao.eml
│   │   └── manifest.json
│   └── ...
├── 04_Auditoria/               ← Audit module fornece aqui
│   ├── scanner_inventory.json
│   ├── findings.csv
│   └── diagnosis.json
├── 04_Relatorios_LGPD/         ← LGPD fornece aqui
│   ├── lgpd_status_20260505.pdf
│   ├── lgpd_conformity.csv
│   └── lgpd_training_summary.xlsx
└── 00_Indice_Master.md         ← Audit consolida tudo aqui
```

### 15.3 Padrão de armazenamento e rastreabilidade

Cada artefato LGPD segue:

1. **Armazenamento:** `_VISTORIA/<seção>/<ação ou tipo>/<arquivo>`
2. **Hash:** SHA-256 calculado automaticamente
3. **Manifesto local:** `<ação>/manifest.json` com detalhes
4. **Índice global:** `00_Indice_Hashes.xlsx` com todos os hashes
5. **Versionamento:** arquivo leva timestamp ou versão (v1.0, v1.1, etc.)
6. **Imutabilidade:** uma vez armazenado, nunca modificado (cópia para alterações)

---

## 16. Integração com Auditoria Interna

### 16.1 Como se conectam

```
Cartório System — Arquitetura de Governança

app/modules/audit/                  app/modules/lgpd/
├── Scanner                         ├── LgpdAction
├── AuditFinding                    ├── LgpdEvidence
├── DocumentDiagnosis              ├── PolicyDocument
└── (Fases 3-10 futuras)           ├── TrainingRecord
                                    └── Reports

         ↓↓ Integração no dossiê ↓↓

exports/audit/
└── <run-name>/manifest.json        exports/lgpd/
                                    └── <date>/manifest.json

         ↓↓ Consolidação (Fase 10) ↓↓

_VISTORIA/
├── 01_Governanca/          (LGPD)
├── 02_Inventario/          (Audit + LGPD)
├── 04_Auditoria/           (Audit)
├── 04_Evidencias_LGPD/     (LGPD)
├── 01_Relatorios/          (Audit + LGPD)
└── 00_Indice_Master.xlsx   (Audit consolida)
```

### 16.2 Dados que o Audit passa para LGPD

| Dado | Origem Audit | Uso em LGPD |
|---|---|---|
| File inventory | Scanner | AC-01 (banco de dados não estrutural); AC-04 (classificação de dados) |
| DocumentDiagnosis candidatos | Diagnosis | AC-01 (diretórios controlados); diagnosticar documentação obsoleta |
| AuditFinding (access control) | Findings | AC-10 (consentimento); AC-16 (DPO publicado) |
| AuditEvidence | Findings | Alimentar evidências de conformidade de AC-XX |

### 16.3 Dados que LGPD passa para Audit

| Dado | Origem LGPD | Uso em Audit |
|---|---|---|
| Políticas | PolicyDocument | Contexto normativo para achados técnicos |
| Ações pendentes | LgpdAction | Identificar riscos técnicos suporte à ação (ex.: AC-25 plano de incidente) |
| Evidências de treinamento | TrainingRecord | Validar requisito CNJ 213 (capacitação formal) |
| RAT/ROPa | ProcessingActivity | Mapear dados pessoais para proteção na auditoria |

---

## 17. Integração Futura com Atlas

**Escopo:** Fora do MVP. Deixar para Fase 7 (Etapa E do Roadmap CNJ 213).

**Previsão:**
- Atlas consumirá exports estruturados de `exports/lgpd/` (JSON, CSV)
- Cartório System permanece independente (nenhuma importação do Atlas)
- Integração unidirecional: Cartório → Atlas, via arquivo, sem acoplamento
- Dados compartilhados: resumos de conformidade, métricas, não dados pessoais

**Formato previsto:** `exports/lgpd/summary_for_atlas.json`

---

## 18. Roadmap Incremental Proposto

### Fase 0 — Análise e Planejamento (ATUAL — maio/2026)

✅ **Concluído:** Este relatório

**Entregáveis:**
- Este documento (relatório técnico-estratégico)
- Proposta de módulo LGPD
- Roadmap (este)
- Decisão de "vai/não vai"

**Próximo passo:** Validação com João e INOVA sobre timing e escopo

---

### Fase 1 — Preparação (junho/2026 — 1 semana)

**Objetivo:** Preparar base para implementação; não há código novo.

**Atividades:**
- [ ] Criar pasta `app/modules/lgpd/` com `__init__.py`
- [ ] Documentar `docs/modules/lgpd.md` (similar a `docs/modules/audit.md`)
- [ ] Validar estrutura do CSV do Plano de Ação
- [ ] Organizar políticas em versionamento (criar `docs/lgpd_policies/`)
- [ ] Criar fixtures de teste (CSV pequeno com 5 ações de exemplo)

**Saídas:**
- Estrutura de diretórios pronta
- Documentação inicial
- Fixtures de teste

**Testes:** Nenhum código novo.

---

### Fase 2 — Sprint LGPD-1: Importação e Rastreamento (junho/2026 — 2 semanas)

**Objetivo:** Trazer Plano de Ação para banco estruturado.

**Implementação:**
```
app/modules/lgpd/
├── __init__.py
├── enums.py           # LgpdActionStatus, LgpdActionCategory, etc.
├── models.py          # LgpdAction, LgpdActionOwner
├── schemas.py         # Create, Update, Read (Pydantic)
├── service.py         # CRUD + import_from_csv()
├── router.py          # POST/GET/PATCH endpoints
├── rules.py           # Validações de transições de status
└── cli.py             # CLI para importar CSV
```

**Endpoints:**
- `POST /api/v1/lgpd/actions/import` — importar CSV
- `GET /api/v1/lgpd/actions` — listar com filtros
- `GET /api/v1/lgpd/actions/{id}` — detalhe
- `PATCH /api/v1/lgpd/actions/{id}` — atualizar status
- `GET /api/v1/lgpd/actions/summary` — resumo de execução

**Testes:**
- Import de CSV (validação, duplicatas)
- CRUD de ações
- Transições de status
- Filtros (categoria, prioridade, status)
- Exportação CSV

**Critério de pronto:**
- 100% dos 25 itens do Plano importados
- Dashboard mostra 44% (11/25 concluídas)
- Relatório CSV exportável
- 20+ testes passando; ruff limpo

**Estimativa:** 2 semanas (1 dev)

---

### Fase 3 — Sprint LGPD-2: Gestão de Evidências (julho/2026 — 2 semanas)

**Objetivo:** Permitir upload e rastreamento de documentos.

**Implementação:**
```
app/modules/lgpd/
├── evidences/         # Submodule (similar a findings/)
│   ├── models.py      # LgpdEvidence, PolicyDocument
│   ├── schemas.py
│   ├── service.py
│   ├── router.py
│   └── storage.py     # Salvar em _VISTORIA/
├── training/
│   ├── models.py      # TrainingRecord
│   ├── schemas.py
│   ├── service.py
│   └── router.py
└── ...
```

**Endpoints:**
- `POST /api/v1/lgpd/evidences` — upload (multipart)
- `GET /api/v1/lgpd/evidences?action_id=AC-04` — listar por ação
- `GET /api/v1/lgpd/policies` — listar políticas
- `POST /api/v1/lgpd/training` — registrar treinamento
- `GET /api/v1/lgpd/training/report` — relatório

**Armazenamento:**
- Evidências: `_VISTORIA/01_Evidencias_LGPD/AC-XX/arquivo`
- Hash SHA-256 calculado e armazenado
- Manifesto local: `AC-XX/manifest.json`

**Testes:**
- Upload de arquivo
- Cálculo de hash
- Vinculação a ação
- Exportação de manifesto
- Validação de políticas versionadas

**Critério de pronto:**
- 14 políticas importadas
- Mínimo 2 evidências por ação finalizada (22 evidências)
- Manifesto gerado com hashes
- 25+ testes novos; ruff limpo

**Estimativa:** 2 semanas (1 dev)

---

### Fase 4 — Sprint LGPD-3: Relatórios de Conformidade (julho/2026 — 1-2 semanas)

**Objetivo:** Gerar relatórios estruturados.

**Implementação:**
```
app/modules/lgpd/
├── reports/
│   ├── __init__.py
│   ├── generator.py   # Lógica de geração
│   ├── router.py      # Endpoints de report
│   └── exports/       # Templates de Markdown/CSV/JSON
│   │   ├── status_summary.md
│   │   ├── action_detail.md
│   │   ├── conformity_matrix.csv
│   │   └── ...
└── ...
```

**Endpoints:**
- `GET /api/v1/lgpd/reports/status` → JSON (dashboard)
- `GET /api/v1/lgpd/reports/export?format=pdf|csv|json` → arquivo
- `GET /api/v1/lgpd/reports/conformity?mapping=cnj213` → matriz

**Relatórios gerados:**
1. `lgpd_status_summary.md` — panorama geral
2. `lgpd_action_detail.md` — detalhe por ação
3. `lgpd_conformity_report.csv` — matriz CNJ 213
4. `lgpd_training_summary.xlsx` — capacitação

**Armazenamento:** `_VISTORIA/04_Relatorios_LGPD/`

**Testes:**
- Geração de todos os formatos
- Validação de números
- Verificação de hashes
- Formatação de saída

**Critério de pronto:**
- 4 relatórios gerando corretamente
- Números validados
- Dashboard integrado a `/api/v1/`
- 15+ testes novos; ruff limpo

**Estimativa:** 1-2 semanas (1 dev)

---

### Fase 5 — Validação e Preparação para Produção (agosto/2026 — 1 semana)

**Atividades:**
- [ ] Teste integrado: importar CSV → adicionar evidências → gerar relatórios
- [ ] Validação com INOVA: estrutura atende necessidades?
- [ ] Validação com gestor: usabilidade OK?
- [ ] Documentação de operação: como usar em produção
- [ ] Plano de migração de dados (dados existentes para novo módulo)

**Saídas:**
- Teste integrado E2E passando
- Documentação operacional
- Aprovação para produção

---

### Fase 6 — Implantação em Produção (setembro/2026)

**Atividades:**
- [ ] Implantar módulo LGPD em produção
- [ ] Importar dados históricos (políticas, evidências existentes)
- [ ] Treinamento rápido para gestor
- [ ] Monitoramento de primeira semana

---

### Fases 7+ (futuro — após MVP estar operacional)

#### Fase 7 — Sprint LGPD-4: Incidentes e Resposta

Entidades: `PrivacyIncident`, melhorias de `AuditAction` para suportar AC-25

#### Fase 8 — Sprint LGPD-5: Avaliação de Fornecedores

Entidades: `VendorAssessment` para AC-13

#### Fase 9 — Sprint LGPD-6: RAT/ROPa Estruturado

Entidades: `ProcessingActivity` (importar das 38 atividades da INOVA)

#### Fase 10 — Integração com Audit para Dossiê Técnico

Consolidação de `_VISTORIA/` com ambos os módulos

#### Fase 11+ — Integração com futuro Atlas, automação assistida

---

## 19. Riscos de Implementação

### 19.1 Riscos técnicos

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| **Dados pessoais vazam em logs** | Crítica | Política de logs segregados; nunca nomes, CPF, contatos de titulares |
| **Hash incorreto prejudica dossiê** | Alta | Validação automática ao upload; teste com arquivos conhecidos |
| **Importação CSV com dados corrompidos** | Alta | Validação rigorosa; relatório de erro; rollback se necessário |
| **Armazenamento em _VISTORIA/ é acessível por demais** | Alta | Permissões NTFS restritivas; auditoria de acesso |
| **Perda de arquivo anexado** | Média | Backup de _VISTORIA/ incluído no PRD; replicação off-site |
| **Relatórios lentos com muitos dados** | Baixa | Cache; paginação; queries otimizadas |
| **Integração com Audit quebra** | Média | Ambos geram manifests independentes; unificação em Fase 10 |

### 19.2 Riscos de negócio / operacional

| Risco | Severidade | Mitigação |
|---|---|---|
| **Gestor não usa o módulo (acredita que INOVA é suficiente)** | Alta | Demonstração: relatórios de conformidade que INOVA não fornece |
| **INOVA demanda integração obrigatória** | Média | Ter argumento: módulo é independente; integração é nice-to-have |
| **Chave de integração INOVA continua quebrada** | Média | Módulo funciona sem integração; resolver depois com INOVA |
| **Vistoria CNJ acontece antes do MVP estar pronto** | Alta | Usar módulo Audit primeiro (já em produção); LGPD como suporte |
| **Escopo cresce durante implementação** | Alta | Rigor no MVP; tudo fora é "Fase 7+" |
| **Responsável pela ação sai da serventia** | Média | Vincular ação a departamento, não pessoa; ter backup |

### 19.3 Riscos regulatórios

| Risco | Severidade | Mitigação |
|---|---|---|
| **LGPD exige mais que está no Plano de Ação da INOVA** | Média | Usar como primeira aproximação; revisar com INOVA a cada trimestre |
| **Conformidade técnica (CNJ 213) e jurídica (LGPD) divergem** | Alta | Dashboard integrado (Audit + LGPD) para visibilidade |
| **Vistoriador questiona evidências geradas pelo módulo** | Média | Toda evidência tem hash, timestamp, responsável — auditável |

---

## 20. Perguntas Críticas para INOVA LGPD

Antes de começar a implementação, enviar estas perguntas à assessoria jurídica:

1. **DPO:** A serventia precisa nomear um DPO formal? Há critérios legais (porte, ramo, etc.)?
   - **Por quê:** AC-15 está meses atrasada; impacta AC-16

2. **Base Legal:** Qual é a situação das "2 atividades com ausência de base legal" (plataforma INOVA)?
   - **Por quê:** Risco crítico para conformidade; requer ação legal

3. **Integração Plataforma:** Qual é a causa do erro de "chave de integração"? Há ETA?
   - **Por quê:** Bloqueia AC-20 (gestão de titulares); afeta roadmap

4. **Consentimento de Colaboradores:** AC-10 exige coleta de consentimento. Qual é a forma legal preferida? (aditivo, formulário, platform?)
   - **Por quê:** Afeta design do módulo LGPD (não inclui em MVP)

5. **Avaliação de Fornecedores:** AC-13 está pendente. Qual é o procedimento legal? Quem executa (INOVA ou Cliente)?
   - **Por quê:** Impacta ownership das ações

6. **Plano de Resposta a Incidentes:** AC-25 está meses atrasada. Há template pronto? Pode ser baseado em procedimento genérico?
   - **Por quê:** Crítica para CNJ 213 (comunicação 48h úteis)

7. **Responsáveis pelas Ações:** Das 25 ações, quantas INOVA fará vs. quantas o Cliente fará?
   - **Por quê:** Definir accountability; estimar esforço

8. **Política de Retenção:** AC-24 está pendente. É baseada na tabela de ciclo de vida que já existe (CART_98)?
   - **Por quê:** Afeta design de purge de dados

9. **Treinamento e Conscientização:** AC-11 pede "cronograma de disponibilidades para 2023"; estamos em 2026. Qual é o plano atual?
   - **Por quê:** Entender se é reciclagem anual ou campanhas pontuais

10. **Documentação de Análises de LI e RIPD:** Há templates prontos? Devem ser anexados ao módulo como evidência?
    - **Por quê:** Afeta armazenamento de documentos

11. **Conformidade com CNJ 213:** INOVA considerou os requisitos técnicos do Provimento ao elaborar o Plano de Ação LGPD?
    - **Por quê:** Verificar alinhamento entre dois roadmaps

12. **Teste de Integração com Vistoria:** Como você recomenda preparar evidências para o vistoriador? Qual é o nível de detalhe esperado?
    - **Por quê:** Informar design do dossiê técnico

---

## 21. Próximos Passos Recomendados

### Imediato (próximas 48h)

1. **Enviar este relatório para João (gestor)**
   - Com convite para validação
   - Pedir feedback em 1 semana

2. **Enviar questionário (seção 20) para INOVA LGPD**
   - Prazo: 1 semana para respostas
   - Usar para refinar roadmap

3. **Apresentar ao time técnico**
   - Sprint planning inicial
   - Validar estimativas de Fase 2-4

### Semana 1 (29/05 — 05/06/2026)

4. **Reunião João + INOVA + Engenharia**
   - Decisão de "vai/não vai"
   - Timing (imediato vs. após Sprint 2 do Audit)
   - Alocação de dev (1 dev em paralelo com Audit Sprint 2?)

5. **Se aprovado:**
   - Iniciar Fase 1 (preparação)
   - Criar épicas no backlog
   - Estimar Fases 2-4 com mais precisão

### Semana 2+ (06/06 em diante)

6. **Início de Fase 2 (Sprint LGPD-1)**
   - Implementar importação de CSV
   - Dashboard básico
   - Testes

---

## 22. Recomendação Final

### Devemos criar o módulo LGPD agora?

**Resposta:** ✅ **Sim, mas em paralelo com Sprint 2 do Audit (AuditFinding CRUD).**

**Justificativa:**

1. **Ganho rápido:** 2-3 sprints entregam MVP funcional
2. **Suporte operacional:** Gestor ganha ferramenta para rastrear Plano de Ação
3. **Preparação para vistoria:** Evidências centralizadas em dossiê estruturado
4. **Independência da INOVA:** Não bloqueia por integração que está quebrada
5. **Sem conflito com Audit:** Ambos são ortogonais; podem ser paralelos
6. **Timing:** Juntos, Audit + LGPD formam "dossiê técnico" em Fase 10 (ago/2026)

**Timing proposto:**

```
Junho 2026          Julho 2026            Agosto 2026
    |                  |                      |
Audit Sprint 2     Audit Fase 3+         Vistoria em breve?
LGPD Sprint 1      LGPD Sprint 2-3
LGPD Sprint 1      LGPD Sprint 3
                   (paralelo, OK)        (ambos prontos)
```

**Condições:**

- ✅ Aprovação de João (escopo + timing)
- ✅ Resposta de INOVA (questões críticas)
- ✅ Alocação de 1 dev em paralelo (Audit Sprint 2 já tem alguém?)
- ✅ Validação que não duplica estruturas jurídicas da INOVA

---

## 23. Resumo Executivo (10 linhas)

1. O Plano de Ação LGPD da INOVA tem 44% de conclusão (11/25 ações); 14 pendentes, 15 sem data.
2. Políticas e procedimentos estão elaborados; implementação e evidenciação estão descentralizadas.
3. Não há sistema integrado para rastrear ações, evidências e conformidade.
4. O Cartório System deve incluir módulo LGPD para centralizar, rastrear e evidenciar.
5. MVP em 3 sprints (junho-julho): importação de ações, gestão de evidências, relatórios.
6. Módulo integra-se ao módulo Audit existente; ambos alimentam dossiê técnico para vistoria.
7. Risco crítico: 2 atividades com "ausência de base legal"; requer revisão INOVA.
8. Timing: paralelo com Sprint 2 do Audit (não há conflito).
9. Decisão esperada: semana de 29/05.
10. Próximo: validação com João + INOVA; refinamento de roadmap.

---

## 24. Decisões que João Precisa Tomar

| # | Decisão | Opções | Impacto | Urgência |
|---|---------|--------|--------|----------|
| D-01 | **Criar módulo LGPD?** | Sim agora / Adiar / Não | Conformidade LGPD; preparação para vistoria | Crítica |
| D-02 | **Timing:** Quando iniciar? | Junho/2026 (imediato) / Após Audit Sprint 2 / Depois da vistoria | Paralelo vs. sequencial | Alta |
| D-03 | **Allocation:** 1 dev tem capacidade? | Sim / Não / Terceirizar | Velocidade; risco de atraso | Alta |
| D-04 | **DPO:** Nomear formal? | Sim / Não / Consultar INOVA | AC-15 pode avançar | Alta |
| D-05 | **Base Legal:** Das 2 atividades com "ausência", qual é o risco? | Risco alto / Médio / Baixo | Prioridade de ação | Crítica |
| D-06 | **Responsáveis:** Definir owners para AC-01..25 | Gestor / TI / RH / Híbrido | Accountability; velocidade | Alta |
| D-07 | **Escopo:** Incluir incidentes (AC-25) no MVP? | Sim / Adiar para Sprint 4 | Completude vs. velocidade | Média |
| D-08 | **Integração INOVA:** Priorizar resolução do erro de chave? | Sim imediato / Deixar para depois | Bloqueia AC-20; afeta roadmap | Média |

---

## 25. Matriz de Rastreabilidade: Plano LGPD ↔ Cartório System

| Ação LGPD | Tipo | Status | Cartório System | Audit? | LGPD? |
|---|---|---|---|---|---|
| AC-01 | Governança | ⏳ | Banco estruturado | Sim (scanner) | Sim (ProcessingActivity) |
| AC-02 | Preparação | ⏳ | RH registra descarte | Não | Não (futuro) |
| AC-03 | Governança | ✅ | Política publicada | Não | Sim (PolicyDocument) |
| AC-04 | Governança | ✅ | PSI em efeito | Sim (findings) | Sim (PolicyDocument) |
| AC-05 | Governança | ✅ | Privacidade publicada | Não | Sim (PolicyDocument) |
| AC-06 | Governança | ⏳ | Cookies no site | Não | Sim (PolicyDocument) |
| AC-07 | Implantação | ⏳ | DPO divulgado no site | Sim (findings) | Sim (DpoRecord) |
| AC-08 | Implantação | ⏳ | Programa de Governança | Sim (findings) | Sim (LgpdAction) |
| AC-09 | Governança | ✅ | Privacy by Design em políticas | Não | Sim (PolicyDocument) |
| AC-10 | Governança | ⏳ | Consentimento de colaboradores | Não | Não (futuro) |
| AC-11 | Governança | ⏳ | Treinamento registrado | Sim (findings) | Sim (TrainingRecord) |
| AC-12 | Governança | ⏳ | Contratos analisados | Não | Sim (Evidence) |
| AC-13 | Governança | ⏳ | Fornecedores avaliados | Não | Sim (VendorAssessment) |
| AC-14 | Governança | ✅ | Backup em operação | Sim (findings) | Sim (PolicyDocument) |
| AC-15 | Implantação | ⏳ | DPO nomeado | Sim (findings) | Sim (DpoRecord) |
| AC-16 | Implantação | ⏳ | DPO divulgado | Sim (findings) | Sim (DpoRecord) |
| AC-17 | Implantação | ✅ | 38 atividades mapeadas | Sim (scanner) | Sim (ProcessingActivity) |
| AC-18 | Implantação | ⏳ | Ferramenta de titulares | Não | Não (futuro) |
| AC-19 | Governança | ✅ | Política de mesa limpa | Sim (findings) | Sim (PolicyDocument) |
| AC-20 | Implantação | ⏳ | Base de titulares | Não | Não (futuro) |
| AC-21 | Implantação | ✅ | Plataforma INOVA (configurada) | Não | Não (integração bloqueada) |
| AC-22 | Governança | ✅ | Procedimento RIPD elaborado | Sim (findings) | Sim (PolicyDocument) |
| AC-23 | Governança | ✅ | Procedimento LI elaborado | Sim (findings) | Sim (PolicyDocument) |
| AC-24 | Governança | ⏳ | Política de Retenção | Sim (findings) | Sim (PolicyDocument) |
| AC-25 | Governança | ⏳ | Plano de resposta a incidentes | Sim (findings) | Sim (PrivacyIncident) |

---

## Conclusão

A serventia Cartório Costa Teixeira tem um plano LGPD estruturado (INOVA), mas falta **operacionalização, rastreamento e evidenciação** de execução. O Cartório System deve incluir um módulo LGPD que:

1. **Centraliza** ações, evidências e conformidade em banco estruturado
2. **Rasteia** quem faz o quê, quando, com qual evidência
3. **Gera** relatórios de status para gestor, INOVA e vistoria
4. **Integra** ao módulo Audit para formar dossiê técnico unificado
5. **Permanece independente** da assessoria jurídica (qual é sua função)

O MVP é viável em **2-3 sprints** (junho-julho/2026), em paralelo com Sprint 2 do Audit, sem conflito de arquitetura.

**Recomendação:** Proceder com implementação, sujeito a aprovação de escopo e timing por João.

---

**Documento preparado por:** Claude Code  
**Data:** 2026-05-05  
**Versão:** 1.0 — Análise Completa  
**Status:** Pronto para Decisão

---

### Anexos

*Archivos são referenciados inline; não há anexos separados.*

**Referências cruzadas recomendadas:**
- `docs/modules/audit.md` — módulo Audit (paralelo)
- `docs/CNJ_213_COMPLIANCE_PLAN.md` — conformidade Provimento
- `docs/TECHNICAL_DOSSIER_STRUCTURE.md` — estrutura do dossiê
- `_local_data/LGPD - inova/Plano de Ação.csv` — fonte original

---

**FIM DO RELATÓRIO**
