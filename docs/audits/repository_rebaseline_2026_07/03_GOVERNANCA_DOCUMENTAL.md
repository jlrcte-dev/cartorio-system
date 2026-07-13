# 03 — Governança Documental

> Sprint **CARTORIO-REPOSITORY-REBASELINE-1** — 2026-07-09.
> 74 documentos versionados em `docs/` + 3 na raiz. Nenhum documento foi alterado nesta sprint; ações são **propostas**.

---

## 1. Matriz de autoridade por tema

Legenda de aderência ao código: ✅ confere · ⚠️ parcialmente defasado · ❌ contradiz o estado real · ➖ não aplicável (documento normativo/planejamento).

| Tema | Documento atual | Concorrentes | Última evidência | Aderência | Autoridade recomendada | Ação proposta | Justificativa |
|------|----------------|--------------|------------------|-----------|------------------------|---------------|---------------|
| Visão do projeto | `README.md` (raiz) | `CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md` §1 | 2026-05-08 | ⚠️ | `README.md` | **Revisar** | Não menciona notas, RI, compliance implementados |
| Governança operacional | `CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md` | `CLAUDE.md` (resumo) | 2026-05-08 | ⚠️ | CONFIGURATION.md | **Revisar** (tabela de módulos) | CLAUDE.md §9 omite `notas` e pipeline RI |
| Arquitetura | `docs/architecture.md` | `02_DIAGNOSTICO_ARQUITETURAL.md` (esta auditoria) | pré-2026-05-04 | ❌ | `docs/architecture.md` **reescrito** | **Revisar (urgente)** | Diz que `finance` é o único módulo ativo; 8 módulos existem; referencia doc inexistente |
| Roadmap geral | `docs/roadmap.md` | `docs/audit/module_roadmap.md`, `docs/regulatory/cnj_213/roadmap.md`, `docs/knowledge_base/IMPLEMENTATION_ROADMAP.md`, `docs/infrastructure/infrastructure_roadmap.md` | 2026-05-23 (parcial) | ❌ | `docs/roadmap.md` como **índice mestre** apontando para roadmaps por eixo | **Revisar + declarar hierarquia** | Sprint 3 marcada "🟡 próxima" mas concluída (commits `2e329e0`, `441a33e`); contagens de teste antigas |
| Roadmap do módulo audit | `docs/audit/module_roadmap.md` | `docs/roadmap.md` (defasado) | 2026-05-05 | ✅ | ele mesmo | Manter (corrigir marcador "✅ Em andamento" da Sprint 3.6) | Mais atualizado que o roadmap geral |
| Roadmap regulatório CNJ 213 | `docs/regulatory/cnj_213/roadmap.md` | compliance_plan.md, alignment.md | 2026-05-07+ | ✅/➖ | ele mesmo | Manter | Checkboxes refletem sprints reais |
| Decisões arquiteturais | `docs/decisions/index.md` + ADR-001..009 + D-01..23 | — | 2026-05-21 | ⚠️ | `decisions/index.md` | **Revisar** | ADR-009 existe mas não está no índice |
| Setup local / execução | `docs/operations/how_to_run.md` | README.md | não confirmado | ⚠️ (não confirmado em detalhe) | how_to_run.md | Revisar na atualização geral | — |
| Testes | `docs/quality/testing.md` | — | Etapa 1.2 (~2026-05-01) | ❌ | testing.md **reescrito** | **Revisar** | Declara "48 testes em 3 arquivos"; reais: 904 em 41 arquivos |
| Banco e migrations | `docs/architecture.md` §princípios + D-04, D-17 | alembic/ | — | ✅ | decisions + architecture.md | Manter | Código cumpre |
| Segurança / dados locais | `docs/operations/local_data_policy.md`, `docs/audit/read_only_policy.md` | CLAUDE.md §2 | 2026-05 | ✅ | os dois citados | Manter | Política cumprida no repo (582 MB fora do git) |
| Finance | `docs/modules/finance.md` | — | v1.2 | ✅ (módulo congelado) | ele mesmo | Manter | — |
| Audit (módulo) | `docs/modules/audit.md` + 4 docs auxiliares | docs/audit/* | 2026-05-05 | ⚠️ | audit.md | Revisar (link engegraph quebrado) | — |
| LGPD | `docs/modules/lgpd.md` | docs/analysis/* (históricos) | 2026-05-05 | ✅ | lgpd.md | Manter; marcar analysis/ como histórico | — |
| Retention | `docs/modules/retention.md` | — | 2026-05-05 | ✅ | ele mesmo | Manter | — |
| Compliance | `docs/modules/compliance.md` | regulatory_integration_blueprint.md | 2026-05-07 | ✅ | compliance.md | Manter | — |
| Notas/Inventários | `docs/modules/notas_inventarios.md` + `notas_inventarios_checklist.md` | POP untracked em `docs/modules/notas_inventarios/` | 2026-05-20+ | ✅ | notas_inventarios.md | Manter + **decidir destino do POP untracked** | POP não versionado nem indexado |
| Registro de Imóveis | `docs/modules/registro_imoveis.md` | docs/ri_inventory/SANITIZED_DATA_DICTIONARY.md | 2026-05 | ⚠️ | registro_imoveis.md | **Revisar** | "Pré-implementação" subrepresenta 7,4k LOC + 334 testes em scripts |
| Geração documental (minutas) | `docs/modules/notas_inventarios.md` | golden files (contrato executável) | 2026-05-22 | ✅ | notas_inventarios.md | Manter | Golden files são a fonte de verdade do output |
| PROAD / IERI | `docs/proad/resposta_ieri_2026/00_README_CONTROLE_DOCUMENTAL.md` | 12 docs irmãos + versões em `_local_data/proad_final_package/` | working tree (não commitado) | ⚠️ | 00_README_CONTROLE_DOCUMENTAL.md | **Commitar estado final** + registrar que ODTs oficiais vivem fora do git | 6 semanas de edições sem commit; duas fontes (git × _local_data) |
| Knowledge Base / IA | `docs/knowledge_base/*` + ADR-004..008 + `docs/ai/AI_LEGal_TOOLS_INVESTIGATION.md` | — | 2026-05-25 | ✅/➖ | KNOWLEDGE_BASE_BLUEPRINT.md | Manter (aguarda DHP-01..10) | Explícito que não há código |
| Integrações / exports | `docs/architecture.md` §Atlas | exports/atlas/.gitkeep | — | ✅ | architecture.md (reescrito) | Manter princípio | Nada implementado (correto) |
| Operação / deploy | `docs/audit/deployment_and_operation.md` | how_to_run.md | 2026-05 | ✅ (escopo audit) | deployment_and_operation.md | Manter | — |
| Changelog / evolução | (inexistente — histórico só no git log) | relatórios de sprint dispersos | — | ➖ | criar `CHANGELOG.md` ou aceitar git log | Decisão humana | Hoje a evolução é rastreável só por commits + memória externa |
| Índice documental | `docs/README.md` | — | 2026-05-23 | ⚠️ | docs/README.md | **Revisar** | Faltam seções: notas, registro_imoveis, proad/, ri_inventory/, ai/; ADRs 004-009 ausentes da seção 8 |

---

## 2. Problemas transversais encontrados

1. **Documentos genéricos desatualizados convivendo com documentos específicos atualizados.** O padrão do repositório é claro: docs por módulo/eixo são mantidos nas sprints; os docs "guarda-chuva" (`architecture.md`, `roadmap.md`, `testing.md`, índices) ficaram para trás. Um leitor que entre por eles sai com uma imagem de ~2026-05-04.
2. **Relatórios de sprint tratados como documentação permanente.** `docs/analysis/` (6 docs LGPD), `docs/ai/` (investigação), `docs/reports/` (relatório à diretoria) são registros históricos valiosos, mas nada os marca como "fotografia de época" — sem banner de status, sem pasta `history/`. Contagens de testes neles (32, 48, 767…) envelhecem e contradizem o presente.
3. **Sem convenção de status de documento.** Apenas alguns docs têm linha `Status:`. Não há frontmatter padrão (status/data/dono), o que torna a distinção vigente × histórico dependente de contexto externo (memória do autor).
4. **Trabalho documental crítico fora do controle de versão.** Os 12 docs PROAD modificados + relatório 11 untracked representam o pacote de resposta à corregedoria — o material mais sensível a prazo do repositório — sem commit desde 2026-05-25. Além disso, o pacote oficial final (ODTs) vive apenas em `_local_data/proad_final_package/` (correto por conter assinaturas/dados, mas o texto-fonte em git deveria estar consolidado).
5. **Dois documentos com o mesmo papel em níveis diferentes**: `README.md` (raiz) e `docs/README.md` se sobrepõem parcialmente como índices; toleráveis se um apontar para o outro com papéis declarados (visão × índice).
6. **Títulos problemáticos ("final", "v2", "novo"):** não encontrados em arquivos versionados — ponto positivo.
7. **Referências quebradas:** `docs/operations/engegraph.md` (3 referências, arquivo inexistente). Contexto Engegraph hoje só existe resumido em `architecture.md` §Coexistência.

---

## 3. Recomendações (para sprints futuras — não executadas)

1. **REB-B1** — Reescrever `docs/architecture.md` a partir do diagnóstico desta auditoria; resolver as 3 referências quebradas (recriar `operations/engegraph.md` ou redirecionar).
2. **REB-B2** — Transformar `docs/roadmap.md` em índice mestre de roadmaps com hierarquia declarada (geral → por eixo), sincronizado com o estado real (ver `06_ROADMAP_RECONCILIADO.md`).
3. **REB-B3** — Atualizar os 4 índices/documentos defasados de baixa complexidade: `docs/README.md`, `decisions/index.md` (+ADR-009), `CLAUDE.md` §9, `docs/quality/testing.md`.
4. **REB-B4** — Adotar convenção mínima de status documental (frontmatter `status: vigente|histórico|rascunho|proposto` + data) e aplicá-la primeiro aos relatórios históricos (`analysis/`, `ai/`, `reports/`).
5. **REB-A1** — Antes de tudo: decidir e commitar o estado final dos docs PROAD (trabalho em risco).
