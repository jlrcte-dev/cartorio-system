# LGPD Module — Executive Brief & Action Items

> Síntese para tomada de decisão — Maio 2026

---

## 1. Resumo Executivo (10 linhas)

1. **Situação atual:** Plano LGPD da INOVA tem 44% concluído (11/25 ações); 14 pendentes; 15 sem data confirmada.
2. **Lacuna:** Políticas existem, mas não há sistema integrado para rastrear execução, evidências e conformidade.
3. **Solução proposta:** Módulo LGPD no Cartório System para centralizar, rastrear e evidenciar o Plano de Ação.
4. **Escopo:** Importação de ações | Gestão de evidências | Relatórios de conformidade (MVP em 3 sprints).
5. **Integração:** Módulo trabalha em paralelo com Sprint 2 do Audit; ambos alimentam dossiê técnico para vistoria.
6. **Risco crítico:** 2 atividades de tratamento têm "ausência de base legal" — requer ação jurídica urgente.
7. **Timing:** Implementação junho-julho/2026; pronto para vistoria CNJ em agosto/2026.
8. **Capacidade:** Requer 1 dev em paralelo (2-3 sprints); não bloqueia outras prioridades.
9. **Dependências:** Respostas de INOVA a 12 perguntas críticas para refinar roadmap.
10. **Recomendação:** Proceder com implementação, sujeito a aprovação de escopo e timing.

---

## 2. Decisões que João Precisa Tomar (agora)

| # | Decisão | Opção A | Opção B | Opção C | Recomendação |
|---|---------|---------|---------|---------|--------------|
| **D-01** | Criar módulo LGPD? | Sim, agora | Adiar para depois | Não criar | ✅ Sim, agora |
| **D-02** | Quando iniciar? | Junho/2026 (imediato) | Após Audit Sprint 2 | Após vistoria | ✅ Junho (paralelo OK) |
| **D-03** | Alocação: 1 dev tem capacidade? | Sim | Não | Terceirizar | ✅ Precisa decidir |
| **D-04** | Nomear DPO formalmente? | Sim | Não | Consultar INOVA | ✅ Consultar INOVA |
| **D-05** | Base Legal: risco das 2 atividades? | Risco alto | Médio | Baixo | ✅ Avaliar INOVA urgente |

---

## 3. Perguntas para Enviar à INOVA LGPD (próximas 48h)

### Grupo A — Crítico (respostas necessárias para D-01/D-02)

1. **DPO:** Serventia precisa nomear formal? Há critério legal?
   - **Impacto:** AC-15 está meses atrasada; trava AC-16

2. **Base Legal:** Qual é a situação exata das 2 atividades com "ausência de base legal"?
   - **Impacto:** Risco crítico de não-conformidade; requer ação jurídica

3. **Integração Plataforma:** Qual é o status do erro de chave? ETA para resolver?
   - **Impacto:** Bloqueia AC-20; afeta roadmap de consentimento

### Grupo B — Alto (respostas para refinar roadmap)

4. **Consentimento (AC-10):** Qual é a forma legal preferida? Aditivo? Formulário? Platform?
   - **Impacto:** Design do módulo LGPD

5. **Avaliação de Fornecedores (AC-13):** Quem executa? INOVA ou Cliente?
   - **Impacto:** Ownership das ações; timing

6. **Plano de Resposta (AC-25):** Há template? Pode ser genérico?
   - **Impacto:** Crítica para CNJ 213 (48h para comunicar incidente)

### Grupo C — Planejamento (para refinar fases 4+)

7. **Responsáveis:** Das 25 ações, quantas INOVA fará vs. quantas Cliente?
8. **Retenção (AC-24):** É baseada na tabela de ciclo de vida existente?
9. **Treinamento (AC-11):** Qual é o plano atual para 2026? Reciclagem anual?
10. **Análises (LI + RIPD):** Há templates prontos? Devem ser parte do módulo LGPD?
11. **Conformidade CNJ 213:** INOVA mapeou requisitos técnicos no Plano LGPD?
12. **Vistoria:** Como estruturar evidências para o vistoriador?

**Enviar em:** Email ou reunião na próxima semana

---

## 4. Proposta de Primeira Sprint (LGPD-1 — junho/2026)

### Objetivo
Trazer Plano de Ação LGPD para banco estruturado e criar interface de acompanhamento.

### O que implementar
- **Entidades:** `LgpdAction`, `LgpdActionOwner`
- **Endpoints:** CRUD de ações + filtros + resumo de execução
- **Armazenamento:** CSV → Banco (Alembic migration)
- **Relatórios:** Dashboard JSON + CSV exportável

### Saídas esperadas
- 100% dos 25 itens do Plano importados ✅
- Dashboard mostrando 44% de conclusão (11/25) ✅
- Relatório exportável (CSV) ✅
- 20+ testes passando ✅
- Ruff clean ✅

### Estimativa
**2 semanas** com 1 dev (paralelo com Audit Sprint 2 OK)

### Testes a incluir
- [ ] Import de CSV (validação, duplicatas)
- [ ] CRUD de ações
- [ ] Transições de status (pending → in_progress → completed)
- [ ] Filtros por categoria, prioridade, status
- [ ] Exportação CSV com metadados
- [ ] Dashboard API

### Critério de Pronto
- [ ] Todos os 25 itens no banco
- [ ] Dashboard mostra números corretos (11 concluídas, 14 pendentes)
- [ ] Relatório CSV gerado corretamente
- [ ] Testes passando (100%)
- [ ] Ruff clean
- [ ] Documentação atualizada

---

## 5. Roadmap Resumido (3 Sprints = MVP pronto)

```
Junho 2026          Julho 2026            Agosto 2026
├─ LGPD-1          ├─ LGPD-2            ├─ LGPD-3 
│  (Ações)         │  (Evidências)       │  (Relatórios)
│  2 semanas       │  2 semanas          │  1-2 semanas
│                  │                     │
├─ Audit Sprint 2   ├─ Audit Fase 3+     ├─ Ambos prontos
│  (Findings)      │                     │  para dossiê
│  paralelo OK     │  paralelo OK        │  (Fase 10)
│                  │                     │
└─────────────────────────────────────────┘
     MVP em paralelo
```

**Total:** 5-6 semanas de dev; 1 dev; módulo operacional em produção

---

## 6. O Que Fica FORA do MVP (Sprint 4+)

Essas funcionalidades são **importantes, mas não críticas** para v1:

- ❌ Integração com plataforma INOVA (bloqueada por erro técnico — resolver depois)
- ❌ Coleta de consentimento de colaboradores (AC-10) — requer ferramenta especializada
- ❌ Monitoramento de titulares (AC-20) — integração externa
- ❌ Dashboard visual gráfico — focar em relatórios estruturados (CSV/JSON)
- ❌ Avaliação de fornecedores (AC-13) — ainda em andamento com INOVA
- ❌ Incidentes de privacidade (AC-25) — CRUD completo; apenas suporte básico em v1
- ❌ RAT/ROPa estruturado — deixar para Fase 9

---

## 7. Riscos & Mitigações

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| Gestor acha que INOVA é suficiente | **Alta** | Demo: relatórios de conformidade que INOVA não fornece |
| Vistoria CNJ acontece antes do MVP | **Alta** | Usar Audit primeiro (em produção); LGPD como suporte |
| Chave INOVA continua quebrada | **Média** | Módulo LGPD funciona sem integração; resolver depois |
| Escopo cresce durante dev | **Alta** | Rigor: tudo fora do MVP vai para "Sprint 4+" |
| Base Legal (2 atividades) é crítica | **Crítica** | **Enviar para INOVA AGORA** — não bloqueie MVP |
| Dev sai do time | **Média** | Documentação clara; usar padrões do Audit (familiar) |

---

## 8. Próximas Ações (Checklist)

### Hoje (2026-05-05)

- [ ] Enviar este documento para João
- [ ] Marcar reunião 1:1 com João para D-01 a D-05
- [ ] Preparar email com 12 perguntas para INOVA

### Semana 1 (até 2026-05-10)

- [ ] Feedback de João sobre decisões
- [ ] Resposta de INOVA com respostas às perguntas
- [ ] Agendar reunião com INOVA + João + Engenharia

### Semana 2 (até 2026-05-17)

- [ ] Decisão final: "vai/não vai"
- [ ] Se aprovado: iniciar Fase 1 (preparação)
- [ ] Criar épicas no backlog
- [ ] Estimar Fases 2-4 com dev selecionado

### Semana 3+ (a partir de 2026-05-20)

- [ ] Fase 1 concluída
- [ ] Sprint LGPD-1 iniciada
- [ ] Stand-ups paralelos com Audit Sprint 2

---

## 9. Entrega Esperada ao Final do MVP

Ao final de julho/2026, o módulo LGPD terá:

✅ **Banco estruturado** com 25 ações do Plano LGPD  
✅ **14 políticas versionadas** importadas e acessíveis  
✅ **Mínimo 2 evidências por ação** (22+ documentos rastreáveis com hashes)  
✅ **Dashboard** mostrando 44% de conclusão + próximos prazos  
✅ **4 relatórios principais:**
  - Status summary (Markdown)
  - Action detail (Markdown)
  - Conformity matrix (CSV vs. CNJ 213)
  - Training summary (CSV)

✅ **Pasta `_VISTORIA/`** com evidências organizadas por ação (pronta para dossiê)  
✅ **Manifesto** com hashes de todos os arquivos (para integridade)  
✅ **100% ruff clean** + 60+ testes passando  
✅ **Documentação operacional** (como usar, como integrar com Audit)

---

## 10. Recomendação Final

### **Proceder com criação do módulo LGPD**

**Por quê:**
1. Ganho rápido: 3 sprints entregam MVP funcional
2. Suporte operacional: Gestor ganha ferramenta para rastrear Plano de Ação
3. Preparação para vistoria: Evidências centralizadas + dossiê estruturado
4. Independência INOVA: Não bloqueia por integração quebrada
5. Sem conflito Audit: Paralelo OK; ambos ortogonais

**Condições:**
- ✅ Aprovação de D-01 a D-05 (João)
- ✅ Respostas de INOVA (12 perguntas)
- ✅ Alocação de 1 dev (paralelo Audit Sprint 2)
- ✅ Validação de não-duplicação estruturas jurídicas

**Timing:**
- Decisão esperada: semana de 29/05
- Fase 1: 05/06 — 12/06
- Sprint LGPD-1: 12/06 — 26/06
- Sprint LGPD-2: 26/06 — 10/07
- Sprint LGPD-3: 10/07 — 24/07
- MVP em produção: 01/08/2026

---

## 11. Contato para Dúvidas

**Relatório completo:** `docs/analysis/lgpd_module_context_report.md` (9.400+ linhas, todas as 14 perguntas respondidas)

**Perguntas sobre:**
- Arquitetura → seção 11-13
- Riscos → seção 19
- Roadmap → seção 18
- Integração Audit → seção 16
- Entidades → seção 12
- Use cases → seção 13
- Relatórios → seção 14

---

**Preparado por:** Claude Code  
**Data:** 2026-05-05  
**Versão:** 1.0 — Pronto para Decisão  

**Próxima ação:** Aguardar feedback de João (semana de 29/05)

---
