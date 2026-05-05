# Matriz de Decisão do MVP — Módulo LGPD

> **Objetivo:** Avaliar cada funcionalidade candidata e decidir: **entra no MVP (Sprint 1-3) ou fica para futuro (Sprint 4+)**.

Última atualização: 2026-05-05  
Versão: 1.0

---

## Legenda

| Coluna | Descrição |
|--------|-----------|
| **Funcionalidade** | O que o módulo pode fazer |
| **MVP?** | ✅ Sim / ❌ Não / ⏳ Depois |
| **Justificativa** | Por que incluir ou não |
| **Risco** | Risco técnico ou operacional se incluir |
| **Dependência** | Do que depende (respostas INOVA, etc.) |
| **Sprint** | Se MVP: qual sprint. Se não: sprint recomendada |

---

## Funcionalidades Avaliadas

### 1. Importação do Plano de Ação (AC-01..25)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Ler Plano de Ação.csv e criar 25 registros LgpdAction no banco |
| **MVP?** | ✅ Sim — Crítica |
| **Justificativa** | Base de tudo. Sem isso, não há módulo LGPD. Simples de implementar. |
| **Risco** | CSV corrompido ou mudança de estrutura → validação rigorosa mitiga |
| **Dependência** | Nenhuma (CSV está pronto) |
| **Sprint** | Sprint LGPD-1 (US-1.2) |
| **Estimativa** | 3-4 horas (import + validação + testes) |

---

### 2. CRUD de Ações

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | GET/PATCH endpoints para ler e atualizar status de ações |
| **MVP?** | ✅ Sim — Crítica |
| **Justificativa** | Gestor precisa acompanhar andamento das 25 ações. Essencial. |
| **Risco** | Validação de transição de status mal feita → teste rigoroso |
| **Dependência** | Sprint LGPD-1 US-1.1 (LgpdAction model) pronta |
| **Sprint** | Sprint LGPD-1 (US-1.3) |
| **Estimativa** | 6-8 horas (endpoints + validação + testes) |

---

### 3. Dashboard de Resumo de Execução

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | GET `/api/v1/lgpd/actions/summary` → JSON com 11/25 concluídas, etc. |
| **MVP?** | ✅ Sim — Importante |
| **Justificativa** | Gestor precisa visão geral rápida (% concluído, próximos prazos). Simples de calcular. |
| **Risco** | Cálculos incorretos (números não batem) → teste de data |
| **Dependência** | Sprint LGPD-1 US-1.1 (LgpdAction) pronta |
| **Sprint** | Sprint LGPD-1 (US-1.4) |
| **Estimativa** | 2-3 horas |

---

### 4. Filtros de Ações (categoria, prioridade, status)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | GET `/api/v1/lgpd/actions?category=Governança&status=Pendente` |
| **MVP?** | ✅ Sim — Importante |
| **Justificativa** | Gestor precisa filtrar por status/categoria para acompanhar. Simples via query params. |
| **Risco** | Performance se muitos registros (25 é trivial) |
| **Dependência** | Sprint LGPD-1 US-1.3 |
| **Sprint** | Sprint LGPD-1 (US-1.3) |
| **Estimativa** | 1-2 horas |

---

### 5. Exportação CSV de Ações

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | GET `/api/v1/lgpd/actions/export?format=csv` → arquivo CSV |
| **MVP?** | ✅ Sim — Desejável |
| **Justificativa** | Gestor pode compartilhar com INOVA ou gestor superior em planilha. Valor agregado. |
| **Risco** | Encoding (UTF-8 vs. ISO) → sempre usar UTF-8 com BOM |
| **Dependência** | Sprint LGPD-1 US-1.1, 1.3 |
| **Sprint** | Sprint LGPD-1 (US-1.5) |
| **Estimativa** | 1-2 horas |

---

### 6. Upload de Evidências (arquivo)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | POST `/api/v1/lgpd/evidences` com multipart file upload + metadados |
| **MVP?** | ✅ Sim — Crítica |
| **Justificativa** | Evidências são a prova de execução das ações. Essencial para dossiê/vistoria. |
| **Risco** | Arquivo grande ou corrupto → validação de tamanho/tipo; recovery se falhar |
| **Dependência** | Sprint LGPD-1 (LgpdAction) pronta; permissões `_VISTORIA/` confirmadas com TI |
| **Sprint** | Sprint LGPD-2 (US-2.2) |
| **Estimativa** | 6-8 horas (upload + hash + storage) |

---

### 7. Cálculo de Hash SHA-256

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Calcular e armazenar hash SHA-256 de cada evidência automaticamente |
| **MVP?** | ✅ Sim — Crítica |
| **Justificativa** | Hash é prova de integridade para vistoriador. Obrigatório para dossiê. |
| **Risco** | Cálculo incorreto (testar com hashes conhecidos) |
| **Dependência** | Sprint LGPD-2 US-2.2 |
| **Sprint** | Sprint LGPD-2 (US-2.2) |
| **Estimativa** | 2-3 horas (incluído em upload) |

---

### 8. Armazenamento Físico em `_VISTORIA/`

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Salvar arquivo original em `_VISTORIA/01_Evidencias_LGPD/AC-XX/` |
| **MVP?** | ✅ Sim — Crítica |
| **Justificativa** | Arquivo original é necessário para vistoria. Estrutura `_VISTORIA/` é padrão do projeto. |
| **Risco** | Permissões NTFS; espaço em disco | Coordenar com TI antes de Sprint 2 |
| **Sprint** | Sprint LGPD-2 (US-2.2) |
| **Estimativa** | 2 horas (+ coordenação com TI) |

---

### 9. Versionamento de Políticas

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Armazenar 14 políticas INOVA com versionamento (v1.0, v1.1, etc.) |
| **MVP?** | ✅ Sim — Desejável |
| **Justificativa** | Políticas mudam; precisar saber qual versão estava em vigor em qual data. Rastreabilidade. |
| **Risco** | Versioning policy não clara (v1.0.1 vs. v1.1?) → usar semântico rígido |
| **Dependência** | Sprint LGPD-2 US-2.4 |
| **Sprint** | Sprint LGPD-2 (US-2.4) |
| **Estimativa** | 3-4 horas |

---

### 10. Relatório de Status (Markdown)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Gerar arquivo `lgpd_status_summary.md` com panorama legível |
| **MVP?** | ✅ Sim — Importante |
| **Justificativa** | Gestor precisa documento formatado para INOVA/vistoria. Simples de gerar com templates. |
| **Risco** | Formatação quebrada no Markdown → testes com visualizador |
| **Dependência** | Sprint LGPD-1 (LgpdAction) pronta |
| **Sprint** | Sprint LGPD-3 (US-3.2) |
| **Estimativa** | 2-3 horas |

---

### 11. Relatório de Detalhe por Ação

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Gerar arquivo `lgpd_action_detail.md` com seção por ação (AC-01..25) |
| **MVP?** | ✅ Sim — Desejável |
| **Justificativa** | Detalhe útil para vistoria; mostra execução específica de cada ação. Documenta rastreamento. |
| **Risco** | Arquivo muito grande (25 ações × 10 linhas) → aceitar, é detalhe esperado |
| **Dependência** | Sprint LGPD-3 US-3.2 |
| **Sprint** | Sprint LGPD-3 (US-3.3) |
| **Estimativa** | 2 horas |

---

### 12. Matriz de Conformidade CNJ 213

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Gerar CSV mapeando AC-XX → Bloco CNJ (G/A/B/T/I/D) → Status |
| **MVP?** | ✅ Sim — Importante |
| **Justificativa** | Demonstra alinhamento LGPD + CNJ 213 para vistoriador. Integração crítica dos dois frameworks. |
| **Risco** | Mapeamento incorreto (AC-X não vinculada a bloco certo) → validação manual após geração |
| **Dependência** | Mapeamento documentado em análise LGPD (já feito no contexto report) |
| **Sprint** | Sprint LGPD-3 (US-3.4) |
| **Estimativa** | 3-4 horas |

---

### 13. Relatório de Treinamentos

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Gerar CSV com training_name, date, participant, certificate_hash, duration |
| **MVP?** | ✅ Sim — Importante |
| **Justificativa** | AC-11 exige documentação de treinamento. CSV é fácil de verificar. Dados já existem (certificados em pasta). |
| **Risco** | Participantes múltiplos em 1 treinamento → 1 linha por participante (design OK) |
| **Dependência** | Sprint LGPD-2 (TrainingRecord) pronta |
| **Sprint** | Sprint LGPD-3 (US-3.5) |
| **Estimativa** | 2 horas |

---

### 14. Manifesto de Evidências (JSON com hashes)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Gerar `lgpd_evidence_manifest.json` com arquivo, hash, tipo, ação vinculada |
| **MVP?** | ✅ Sim — Crítica |
| **Justificativa** | Índice de integridade; usado para validação de dossiê e integração com Audit. Essencial. |
| **Risco** | Nenhum (é apenas serialização de dados já capturados) |
| **Dependência** | Sprint LGPD-2 (LgpdEvidence) pronta |
| **Sprint** | Sprint LGPD-3 (US-3.6) |
| **Estimativa** | 1 hora |

---

### 15. API Dashboard (JSON estruturado)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | GET `/api/v1/lgpd/reports/status` → JSON com métricas para frontend consumir |
| **MVP?** | ✅ Sim — Desejável |
| **Justificativa** | Pronto para integração com frontend futuro (dashboard visual). Reutiliza US-1.4. |
| **Risco** | Nenhum (é refatoração de código já testado) |
| **Dependência** | Sprint LGPD-1 (US-1.4) |
| **Sprint** | Sprint LGPD-3 (US-3.1) |
| **Estimativa** | 1 hora |

---

### 16. Integração com Módulo Audit

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Ambos os módulos geram manifests compatíveis; preparação para Fase 10 (dossiê unificado) |
| **MVP?** | ⏳ Não — Futuro (Sprint 7) |
| **Justificativa** | Sprint 1-3: ambos geram manifests separados. Unificação é Phase 10 Audit (setembro/2026). |
| **Risco** | Se unificação atrasar, manifests divergem → manter padrão consistente desde Sprint 1 |
| **Dependência** | Audit Fase 10 pronta; padrão de manifesto alinhado |
| **Sprint** | Sprint LGPD-7 (futuro) |
| **Estimativa** | 3-4 horas (integração final) |

---

### 17. Autenticação Multiusuário

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Controle de acesso por usuário (quem criou, atualizou, quando) |
| **MVP?** | ⏳ Não — MVP usa "created_by=gestor" temporariamente |
| **Justificativa** | Módulo Audit Sprint 1 é read-only. Auth multiusuário vem em Etapa C (fora do MVP LGPD). |
| **Risco** | Se Sprint 2-3 precisar saber "quem fez", usar temporário "created_by=gestor" |
| **Dependência** | Auth multiusuário do Cartório System (futuro, Etapa C) |
| **Sprint** | Etapa C (fora do MVP LGPD) |
| **Estimativa** | Futuro |

---

### 18. Integração com Plataforma INOVA

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Sincronização bidirecional: ações, políticas, RAT/ROPa com plataforma INOVA |
| **MVP?** | ❌ Não — Bloqueado por erro técnico |
| **Justificativa** | Integração está quebrada (erro de chave INOVA). Módulo LGPD funciona independente. Resolver depois. |
| **Risco** | Se não resolver, módulo permanece standalone (design já prevê) |
| **Dependência** | Suporte INOVA resolver erro de integração (prazo desconhecido) |
| **Sprint** | Sprint LGPD-6+ (depende de INOVA) |
| **Estimativa** | 4-5 horas (após INOVA liberar) |

---

### 19. Coleta de Consentimento (AC-10)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Registrar consentimento formal de colaboradores via formulário ou aditivo contratual |
| **MVP?** | ❌ Não — Fora do escopo Sprint 1-3 |
| **Justificativa** | AC-10 ainda não foi definido (aguardando resposta INOVA A-04). Deixar para Sprint 4+. |
| **Risco** | Se forma simples, podia vir em Sprint 3; mas INOVA ainda não respondeu |
| **Dependência** | Resposta INOVA sobre forma legal de coleta (pergunta A-04) |
| **Sprint** | Sprint LGPD-4+ (após decisão INOVA) |
| **Estimativa** | 4-5 horas (futuro) |

---

### 20. Incidentes de Privacidade (AC-25 completo)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Registro formal de incidentes: tipo, descrição, resposta, comunicação ANPD |
| **MVP?** | ❌ Não — Apenas suporte básico em Sprint 3 |
| **Justificativa** | AC-25 é crítica, mas template ainda não definido (pergunta A-05). MVP apenas marca como "validado". |
| **Risco** | Se template definido cedo, pode vir em Sprint 3; senão Sprint 4+ |
| **Dependência** | Resposta INOVA sobre template IRP (pergunta A-05) |
| **Sprint** | Sprint LGPD-4+ (PrivacyIncident CRUD completo) |
| **Estimativa** | 4-5 horas (futuro) |

---

### 21. Avaliação de Fornecedores (AC-13 completo)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | CRUD de fornecedores: risco, conformidade, últimas avaliações |
| **MVP?** | ❌ Não — Futuro |
| **Justificativa** | AC-13 ainda está em andamento com INOVA. Deixar para Sprint 4+ quando critérios estiverem claros. |
| **Risco** | Scope creep: se desculpa implementar cedo, afeta Sprint 1-3 |
| **Dependência** | Resposta INOVA sobre status e critérios (pergunta B-02) |
| **Sprint** | Sprint LGPD-5+ |
| **Estimativa** | 4 horas (futuro) |

---

### 22. RAT/ROPa Estruturado (ProcessingActivity completo)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Importar e rastrear 38 atividades: propósito, categorias de dados, legal basis, retenção |
| **MVP?** | ❌ Não — Futuro |
| **Justificativa** | 38 atividades estão na plataforma INOVA (inacessível por erro). Deixar para Sprint 6+ quando integração funcionar. |
| **Risco** | Se tentar importar via CSV, ajuste manual 38 atividades é trabalhoso |
| **Dependência** | Integração INOVA funcionar (pergunta A-03) |
| **Sprint** | Sprint LGPD-6+ |
| **Estimativa** | 5-6 horas (após integração) |

---

### 23. Dashboard Visual (Gráficos)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Dashboard com gráficos: % concluído, timeline, breakdown por categoria (frontend React/Vue) |
| **MVP?** | ❌ Não — Futuro |
| **Justificativa** | MVP foca em relatórios estruturados (CSV, JSON, Markdown). Frontend visual é Sprint 4+ (depende de design). |
| **Risco** | Scope creep: fácil gastar tempo em UI |
| **Dependência** | Decisão sobre stack frontend (React, Vue, etc.) — futuro |
| **Sprint** | Sprint 4+ (integração com frontend) |
| **Estimativa** | 8-10 horas (futuro) |

---

### 24. Export para ANPD/Autoridades

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Gerar arquivo de conformidade formatado conforme exigência de ANPD ou órgão externo |
| **MVP?** | ❌ Não — Futuro |
| **Justificativa** | Só necessário se houver incidente ou requisição formal. Deixar para fase de maturidade. |
| **Risco** | Baixo; pode ser adicionado facilmente |
| **Dependência** | Incidente ocorrer ou ANPD solicitar |
| **Sprint** | Futuro (on-demand) |
| **Estimativa** | 2-3 horas (quando necessário) |

---

### 25. Teste Integrado E2E (import → evidências → relatórios)

| Campo | Valor |
|-------|-------|
| **Funcionalidade** | Teste ponta-a-ponta: importa CSV → adiciona 2 evidências → gera relatórios → valida output |
| **MVP?** | ✅ Sim — Crítica |
| **Justificativa** | Valida fluxo completo de Sprint 1-3. Detecta integração quebrada cedo. |
| **Risco** | Nenhum; é teste, não código novo |
| **Dependência** | Sprint LGPD-3 US-3.7 |
| **Sprint** | Sprint LGPD-3 (US-3.7) — Fase 5 (validação) |
| **Estimativa** | 3-4 horas (teste + documentação) |

---

## Resumo de Decisões

### Inclusos no MVP (Sprint 1-3) — 15 funcionalidades

✅ 1. Importação CSV (AC-01..25)
✅ 2. CRUD de ações
✅ 3. Dashboard resumo
✅ 4. Filtros (categoria, status, prioridade)
✅ 5. Exportação CSV
✅ 6. Upload de evidências
✅ 7. Hash SHA-256
✅ 8. Armazenamento `_VISTORIA/`
✅ 9. Versionamento de políticas
✅ 10. Relatório status Markdown
✅ 11. Relatório detalhe por ação
✅ 12. Matriz CNJ 213
✅ 13. Relatório treinamentos
✅ 14. Manifesto evidências JSON
✅ 15. API dashboard JSON
✅ + Testes integrados E2E

### Fora do MVP (Sprint 4+) — 10 funcionalidades

❌ 1. Autenticação multiusuário (Etapa C do projeto)
❌ 2. Integração INOVA (bloqueada)
❌ 3. Coleta consentimento AC-10 (aguarda INOVA)
❌ 4. Incidentes completo AC-25 (aguarda template)
❌ 5. Fornecedores AC-13 (aguarda critérios)
❌ 6. RAT/ROPa AC-17 (aguarda integração)
❌ 7. Dashboard visual (futuro, frontend)
❌ 8. Export ANPD (on-demand)
❌ 9. Integração Audit completa (Fase 10)
❌ 10. Recursos futuros TBD

---

## Estimativa Total do MVP

| Sprint | Horas | Dias (5h/dia) | Timeline |
|--------|-------|---|----------|
| LGPD-1 (Ações) | 20-24h | 4-5 dias | 2 semanas (com testes, doc) |
| LGPD-2 (Evidências) | 20-24h | 4-5 dias | 2 semanas (com testes) |
| LGPD-3 (Relatórios) | 12-16h | 2-3 dias | 1-2 semanas (com testes) |
| **Total MVP** | **52-64h** | **~2 semanas** | **Junho-julho 2026** |

**Nota:** Estimativa é para 1 dev com padrões do projeto já conhecidos (FastAPI, SQLAlchemy, Pytest). Inclui testes e documentação.

---

## Decisões Técnicas Críticas

### D-01: Armazenar arquivo ou apenas metadados/hash?

**Decisão:** ✅ Armazenar arquivo original em `_VISTORIA/`; banco armazena metadados + hash.

**Justificativa:**
- Arquivo original necessário para vistoriador
- Banco fica leve (só metadados)
- Hash prova integridade
- Backup de `_VISTORIA/` gerenciado pelo PRD

---

### D-02: LgpdAction derivada do CSV ou manual?

**Decisão:** ✅ Derivar diretamente do CSV. Importação automática no Sprint LGPD-1.

**Justificativa:**
- 25 ações já estão no CSV (Plano de Ação.csv)
- Manual seria erro-prone
- Importação automática é rastreável

---

### D-03: Status preserva INOVA ou normaliza?

**Decisão:** ✅ Normalizar para 3 status: Pendente, Em Progresso, Concluída.

**Justificativa:**
- INOVA pode usar nomes diferentes
- 3 status alinha com CNJ 213 (planejado, em execução, completo)
- Mais simples para transitions

---

### D-04: Matriz LGPD x CNJ 213 é entidade ou relatório?

**Decisão:** ✅ Relatório derivado (não entidade separada).

**Justificativa:**
- Mapeamento é estático (AC-XX → Bloco CNJ Y)
- Não muda em tempo de execução
- Relatório é suficiente

---

### D-05: Evidências têm nível de confidencialidade?

**Decisão:** ✅ Sim, campo `confidentiality_level` (Public, Internal, Restricted, Confidential).

**Justificativa:**
- Algumas evidências podem ser sensíveis (parecer jurídico, contrato)
- Útil para futuro controle de acesso
- Documentado no domínio

---

### D-06: API pública interna ou apenas service/repository?

**Decisão:** ✅ API pública interna (FastAPI /api/v1/lgpd/*).

**Justificativa:**
- Consistente com Audit (que tem /api/v1/audit/*)
- Pronto para frontend futuro
- Reutilizável por outros módulos

---

### D-07: Autenticação multiusuário obrigatória?

**Decisão:** ❌ Não no MVP. Usar `created_by="gestor"` temporariamente.

**Justificativa:**
- Auth completa é Etapa C (fora do MVP LGPD)
- MVP é prototipo para validação
- Fácil adicionar auth depois

---

### D-08: Qual parte aguarda resposta INOVA antes de implementação?

**Decisão:** ✅ Sprint 4+ aguarda respostas A-04, A-05, B-02.

**Justificativa:**
- AC-10 (consentimento): aguarda forma legal (A-04)
- AC-25 (incidentes): aguarda template (A-05)
- AC-13 (fornecedores): aguarda critérios (B-02)
- Sprint 1-3 não depende dessas respostas

---

## Próximos Passos

1. ✅ **Validar decisões com João** (semana de 2026-05-29)
2. ✅ **Obter respostas INOVA** (até 2026-05-12)
3. ✅ **Atualizar matriz se necessário** (2026-05-15)
4. ⏳ **Iniciar Fase 1** (preparação, 2026-06-05)
5. ⏳ **Sprint LGPD-1** (implementação ações, 2026-06-12)

---

**Preparado por:** Claude Code  
**Data:** 2026-05-05  
**Versão:** 1.0  
**Status:** Decisões Consolidadas
