# 06 — Roadmap Reconciliado

> Sprint **CARTORIO-REPOSITORY-REBASELINE-1** — 2026-07-09.
> **Proposta de reconciliação para aprovação — não substitui o roadmap oficial.**
> Fontes cruzadas: `docs/roadmap.md`, `docs/audit/module_roadmap.md`, `docs/regulatory/cnj_213/roadmap.md`, `docs/knowledge_base/IMPLEMENTATION_ROADMAP.md`, `docs/infrastructure/infrastructure_roadmap.md`, git log, código e testes.

---

## 1. Matriz única de itens (estado comprovado)

Legenda: 🟢 implementado · 🟡 parcial · 🔵 implementado sem doc adequada · 📄 documentado, não implementado · ⚪ não iniciado · 🔴 obsoleto/defasado · ❓ status desconhecido.

| Item | Fonte original | Estado | Evidência código | Evidência testes | Evidência doc | Recomendação |
|------|---------------|--------|------------------|------------------|----------------|--------------|
| Etapa 0 — Fundação FastAPI | roadmap.md | 🟢 | `app/core`, `app/main.py` | `test_health` | architecture.md | — |
| Finance Core v1.2 | roadmap.md | 🟢 (congelado) | `app/modules/finance` | `test_finance_entries` (44) | `modules/finance.md` | Manter em backlog conforme decisão |
| Monthly Closing (Etapa 2 finance) | roadmap.md backlog | ⚪ | — | — | roadmap.md | Backlog (inalterado) |
| Obligations/Reports (Etapa 3 finance) | roadmap.md backlog | ⚪ | — | — | roadmap.md | Backlog |
| Exports estruturados (Etapa 4 finance/Atlas) | roadmap.md backlog | ⚪ | `exports/atlas/.gitkeep` apenas | — | architecture.md | Primeiro candidato pós-estabilização se integração Atlas voltar à pauta |
| Audit Sprint 1 — Scanner read-only | roadmap.md + module_roadmap | 🟢 | `audit/scanner` | `test_file_scanner` | ambos | — |
| Audit Sprint 2 — Findings CRUD | idem | 🟢 | `audit/findings` | `test_audit_findings` (43) | ambos | — |
| Audit Sprint 2.5 — Procedimento operacional | module_roadmap | 🟢 | — (doc) | — | `audit/operational_procedure.md` | — |
| Audit Sprint 3 — DocumentDiagnosis | roadmap.md ("🟡 próxima") | 🟢 **contradição** | `audit/diagnosis` (commits `2e329e0`, `6e3a39f`, `441a33e`) | `test_document_diagnosis` (39) + integração | module_roadmap ✅; **roadmap.md defasado** | Corrigir roadmap.md (REB-B2) |
| Audit Sprint 3.6 — Calibração pós-real | module_roadmap | 🟢 | commit `441a33e` | testes de regras | marcador confuso "✅ (Em andamento)" | Corrigir marcador |
| Audit Fases 3–12 (evidências, dossiê, etc.) | module_roadmap | ⚪ | — | — | module_roadmap | Retomada em REB-E conforme prioridade CNJ |
| LGPD-1 — Ações (AC-01..25) | analysis/ + roadmap | 🟢 | `lgpd/` (commit `ebade5d`) | `test_lgpd_actions` (37) | `modules/lgpd.md` | — |
| Retention-1A/1B | cnj/blueprint | 🟢 | `retention/` (commit `646b59b`) | `test_retention_*` | `modules/retention.md` | — |
| Compliance-1 (matriz INOVA read-only) | blueprint regulatório | 🟢 | `compliance/` (commit `fc5ef6e`) | 14 arquivos de teste | `modules/compliance.md` | — |
| Compliance-2 (evidências) | idem | 🟢 | commit `4ccf50c` | test_compliance_evidence_* | idem | — |
| Compliance-3 (vínculos req↔achado) | idem | 🟢 | commit `c588bc2` | test_compliance_finding_link_* | idem | — |
| Compliance-4 (status indicativo) | idem | 🟢 | commit `d782013` | test_compliance_requirement_status_* | idem + cnj_213/roadmap checkbox | — |
| Notas/Inventários (minuta-base + ODT + schema) | sprints NOTAS-0..5B | 🔵 | `notas/inventarios` (commits `e4a2dea`..`ff09613`) | 7 arquivos + golden | `modules/notas_inventarios.md` ok; **ausente de CLAUDE.md §9, docs/README.md e roadmap.md** | Indexar (REB-B3) |
| NOTAS — frações/percentuais exatos (FRACOES-1) | proposta de sprint (não versionada — memória de sessão) | 📄/❓ | renderer trunca 3,125%→3,12% (rota manual §15) | golden atual | **nenhuma doc versionada** | Registrar proposta em doc versionado; quick win |
| Pipeline RI sanitizado (extração/análise/consolidação) | sprints RI-* | 🔵 | `scripts/local_tools/` 7 ferramentas | 6 arquivos (~334 testes) | `registro_imoveis.md` diz "pré-implementação" | Reclassificar doc + DH-1 (REB-C1) |
| PROAD/IERI — dossiê de resposta | sprints PROAD-* | 🟡 | 12 docs modificados **não commitados** + pacote ODT em `_local_data/` | — | working tree | **REB-A1 urgente** |
| Auth multiusuário (antecipada CNJ) | roadmap.md eixo regulatório | ⚪ | — | — | roadmap.md, cnj_213 | **Próxima etapa funcional estrutural (REB-E1)** |
| Trilha de auditoria de sistema | cnj_213/roadmap (req. estrutural) | ⚪ (parcial por módulo: históricos append-only) | históricos lgpd/compliance | testes de history | cnj_213/roadmap | REB-E2 após auth |
| Knowledge Base KB-1+ | knowledge_base/IMPLEMENTATION_ROADMAP | 📄 (bloqueado por DHP-01..10) | — (explícito: sem código) | — | blueprint completo | Aguarda decisões humanas (correto) |
| Document Registry (módulo) | ADR-003 + document_registry/ | 📄 | — | — | blueprint + matriz CNPFE-GO | Sem urgência evidenciada |
| AI Gateway / integração IA | docs/ai + ADR-004..008 | 📄 (Proposto) | — | — | investigação completa | Aguarda DHP; depende de KB |
| Infraestrutura-alvo (VMs, VLANs, backup) | infrastructure_roadmap | ❓ (externo ao repo) | n/a | n/a | docs de plano | Validar na serventia; fora do escopo do repo (TD-22) |
| Protocolos / GED / clients / tasks | fundação original (placeholders) | ⚪ | 6 `__init__.py` vazios | — | architecture.md ("etapas futuras") | Decidir manter/remover (DH-2) |

## 2. Comparação com as fases conceituais

| Fase conceitual | Progresso real |
|-----------------|----------------|
| Fundação | 🟢 completa e sólida |
| Domínio operacional (protocolos/tarefas/clientes) | ⚪ não iniciado (adiado conscientemente — MVP redirecionado 05/2026) |
| Financeiro e gestão | 🟡 core completo e congelado; fechamento/obrigações/exports em backlog |
| Auditoria interna e evidências | 🟢 fases 0–2.5+3.6 completas; fases 3–12 à frente |
| Autenticação e permissões | ⚪ **maior gap estrutural** (antecipado no papel, não iniciado) |
| Protocolos e tarefas | ⚪ backlog |
| Documentos (geração) | 🟢 notas/inventários maduro (1 falecido, rota manual p/ frações) |
| Relatórios | 🟡 pontuais (executivo, PROAD) — sem módulo |
| Exports estruturados | ⚪ pasta reservada apenas |
| Integração futura (Atlas) | ⚪ correto — princípio de independência respeitado |
| Automações avançadas / IA | 📄 blueprints prontos, bloqueados por decisões humanas (correto) |

## 3. O roadmap original ainda é adequado?

**A ordenação estratégica sim; o documento não.** A decisão de maio/2026 (audit-first por causa do CNJ 213) continua válida e foi executada com sucesso — o eixo regulatório (audit+lgpd+retention+compliance) é hoje o núcleo maduro do sistema. Porém:

1. `docs/roadmap.md` congelou em 2026-05-23 e não registra: notas/inventários (6 commits), pipeline RI, PROAD, Compliance-2..4 (registrados apenas no cnj_213/roadmap).
2. Surgiram **dois eixos novos não previstos** no roadmap geral: geração documental (notas) e dossiê PROAD/RI — ambos consumiram a maior parte do esforço de maio/junho e não têm lugar no documento.
3. O item "próxima etapa" real não está escrito em nenhum roadmap versionado.

## 4. Proposta de reordenação (para aprovação)

1. **Estabilização do repositório** (Grupos A/B do plano — commit PROAD, docs guarda-chuva, CI mínimo).
2. **Encerramento formal do ciclo PROAD** no repositório (dossiê commitado, status registrado, pendências → `09_pendencias`).
3. **Retomada funcional em duas vias paralelas de tamanho assimétrico:**
   - **Via estrutural (principal): autenticação multiusuário mínima** — pré-requisito declarado do CNJ 213 para colaboradores usarem o sistema, e dependência da trilha de auditoria transversal (que precisa de identidade). É o item com maior razão risco-regulatório/esforço.
   - **Via de valor rápido (secundária): NOTAS-FRACOES-1** — elimina a rota manual de frações da minuta (escopo pequeno, contratos golden protegem regressão).
4. **Depois:** trilha de auditoria transversal → audit Fases 3+ (evidence pack para vistoria) → exports estruturados.
5. **Sem mudança:** KB/IA e Document Registry permanecem bloqueados por decisões humanas (DHP-01..10) — não retomar sem aprovação formal.
