# Resposta Técnica Inicial ao PROAD — Adequação ao Provimento CNJ nº 195/2025

**Status:** PRELIMINAR — Em consolidação  
**PROAD:** Nº 202509000672377  
**Serventia:** Cartório Costa Teixeira — Terezópolis de Goiás / Comarca de Goianápolis — GO  
**Atualizado em:** 2026-05-16

> Este documento é uma visão consolidada das providências da serventia para adequação ao Provimento CNJ nº 195/2025. Complementa (mas não substitui) os documentos específicos em `resposta_ieri_2026/`. Não deve ser protocolado diretamente.

---

## 1. Contexto

Em 03 de junho de 2025, o Conselho Nacional de Justiça publicou o **Provimento CNJ nº 195/2025**, que alterou o Código Nacional de Normas para criar o **IERI-e** (Inventário Estatístico Eletrônico do Registro de Imóveis) e o **SIG-RI** (Sistema de Informações Geográficas do Registro de Imóveis), disciplinando procedimentos de saneamento e retificação no Registro de Imóveis.

O provimento entrou em vigor em **01/09/2025**, estabelecendo obrigações imediatas e progressivas para as serventias de Registro de Imóveis em todo o Brasil.

A serventia Cartório Costa Teixeira (Terezópolis de Goiás) responde ao **PROAD nº 202509000672377**, aberto na Corregedoria do Foro Extrajudicial do Tribunal de Justiça do Estado de Goiás, com **prazo vigente de ~10/06/2026** (30 dias a contar do Ofício nº 045/2026/GNP, de 11/05/2026).

---

## 2. Marco normativo

| Norma | Data | Conteúdo |
|---|---|---|
| Provimento CNJ nº 195/2025 | 03/06/2025 | Cria IERI-e e SIG-RI; disciplina saneamento do RI |
| Vigência do Provimento | 01/09/2025 | Início das obrigações de alimentação mensal |
| Decisão/Ofício Circular nº 103/2025 — CGJ-GO | Out/2025 | Determina informação eletrônica ao ONR; 48 meses para adequação do acervo |
| Despacho/Ofício nº 703/2026 — 4º Juiz Auxiliar CGJ | 29/04/2026 | Registra descumprimento; determina nova notificação |
| Ofício nº 045/2026/GNP — Diretoria do Foro | 11/05/2026 | 2ª notificação; prazo de 30 dias para juntada do Plano de Ação |
| ITN 003/2025 (ONR) | 09/03/2026 | Obrigação correlata — módulo "Incluir Atos e Dados" |

---

## 3. Marco administrativo

| Item | Situação |
|---|---|
| Colaborador responsável definido | Sim — a ser formalizado na portaria |
| Portaria Interna nº 01/2026-RI | Prevista para **18/05/2026** |
| Nome do responsável (antes da portaria) | `[NOME_DO_COLABORADOR_DESIGNADO]` |
| Prazo final PROAD | ~10/06/2026 |
| 1º Relatório Semestral | Novembro/2026 |

---

## 4. Providências já iniciadas

| Providência | Status |
|---|---|
| Análise do Provimento CNJ nº 195/2025 e normas correlatas | Concluída |
| Análise dos manuais ONR (Técnico v1.3, Mapa v2.7, API v1.0, CAD v1.1, rurais estrangeiros v1.2) | Concluída |
| Extração sanitizada de dados parciais de matrículas/Indicadores Reais | Concluída (dados em `_local_data/`) |
| Estruturação do pacote documental para juntada no PROAD | Em andamento |
| Designação do colaborador responsável | Definida — formalização em 18/05/2026 |
| Elaboração da Portaria Interna nº 01/2026-RI | Minuta concluída |
| Elaboração do Plano de Ação | Minuta concluída — campos `[a apurar]` pendentes de levantamento |
| Elaboração do POP-RI-001 | Minuta concluída — validação prática pendente |
| Elaboração do Relatório de Diagnóstico Inicial | Estrutura concluída — dados a apurar nos 30 dias pós-portaria |
| Elaboração da Matriz de Evidências e Controles | Em validação |

---

## 5. Relação com IERI-e, SIG-RI e módulo RI

### IERI-e — Inventário Estatístico Eletrônico
- Alimentação mensal obrigatória ao ONR a partir de 01/09/2025
- Envios de set/2025 a abr/2026 em regularização retroativa (condicionada ao procedimento ONR)
- Início da alimentação corrente: jun/2026 (atos de mai/2026)
- Dependência técnica: exportação do Engegraph no layout do ONR ainda não confirmada

### SIG-RI — Sistema de Informações Geográficas
- Inserção gradual dos imóveis georreferenciados — prazo 48 meses (até 01/09/2029)
- Prioridade: imóveis rurais com georreferenciamento certificado INCRA/SIGEF
- Dependência: credenciamento de profissional técnico habilitado junto ao ONR (art. 343-G)

### Módulo RI no Cartório System
- O **Cartório System** está na fase de inventário técnico sanitizado: extração local de dados sem PII, dicionário de dados e scripts de análise
- Dados brutos de matrículas ficam em `_local_data/ri_inventory/` — nunca versionados
- Não há módulo de produção com banco, rotas ou migrations nesta fase
- A fase de produção do módulo RI aguarda decisão arquitetural formal (ADR)

---

## 6. Levantamento parcial de matrículas / Indicadores Reais

Os dados abaixo são **parciais e preliminares**, extraídos de forma sanitizada de relatórios locais. Não contêm PII. Devem ser validados contra o sistema Engegraph e os livros do RI.

| Campo | Situação |
|---|---|
| Total de matrículas | A apurar — levantamento diagnóstico em andamento |
| Matrículas urbanas | Dados parciais disponíveis em `_local_data/` |
| Matrículas rurais | Dados parciais disponíveis em `_local_data/` |
| Imóveis georreferenciados INCRA/SIGEF | Parcialmente identificados |
| Pendências de saneamento | A apurar após diagnóstico completo |

> **Limitação declarada:** Esses dados não podem ser usados como números oficiais sem validação no sistema. O levantamento diagnóstico completo será concluído nos 30 dias seguintes à expedição da Portaria nº 01/2026-RI.

---

## 7. Limitações e cautelas

1. **Dados de matrículas são parciais** — nenhum total deve ser declarado como definitivo sem validação no sistema.
2. **Bases anteriores podem conter imprecisões** — extrações realizadas a partir de fontes preliminares; confrontar com dados atualizados.
3. **Dependências externas registradas** — exportação do Engegraph, confirmação do ONR sobre retroativos, credenciamento de profissional técnico.
4. **Conformidade progressiva** — o Provimento prevê 48 meses para adequação do legado; conformidade plena imediata não é exigida nem possível.
5. **Dados brutos não versionados** — CSVs, JSONs e relatórios operacionais de matrículas ficam exclusivamente em `_local_data/` (ignorados pelo Git).

---

## 8. Documentos de suporte

| Documento | Localização | Status |
|---|---|---|
| README de controle documental | `docs/proad/resposta_ieri_2026/00_README_CONTROLE_DOCUMENTAL.md` | Vigente |
| Relatório analítico preliminar | `docs/proad/resposta_ieri_2026/01_relatorio_analitico_preliminar.md` | PRELIMINAR |
| Minuta de manifestação | `docs/proad/resposta_ieri_2026/02_minuta_manifestacao_proad.md` | MINUTA |
| Plano de Ação | `docs/proad/resposta_ieri_2026/03_plano_acao_ieri_sig_ri.md` | MINUTA |
| Portaria nº 01/2026-RI | `docs/proad/resposta_ieri_2026/04_minuta_portaria_designacao_ri.md` | MINUTA |
| POP-RI-001 | `docs/proad/resposta_ieri_2026/05_pop_ri_001_alimentacao_ieri_sig_ri.md` | MINUTA OPERACIONAL |
| Diagnóstico inicial (histórico) | `docs/proad/resposta_ieri_2026/06_diagnostico_inicial_historico.md` | HISTÓRICO |
| Matriz de evidências | `docs/proad/resposta_ieri_2026/07_matriz_evidencias_controles.md` | EM VALIDAÇÃO |
| Checklist de juntada | `docs/proad/resposta_ieri_2026/08_checklist_juntada.md` | EM VALIDAÇÃO |
| Pendências e alertas | `docs/proad/resposta_ieri_2026/09_pendencias_alertas.md` | EM VALIDAÇÃO |
| Análise dos manuais ONR | `docs/proad/resposta_ieri_2026/10_analise_manuais_ri_digital.md` | PRELIMINAR |
| Documentação do módulo RI | `docs/modules/registro_imoveis.md` | Vigente |
| Dicionário de dados sanitizados | `docs/ri_inventory/SANITIZED_DATA_DICTIONARY.md` | Vigente |

---

## 9. Próximas etapas

| Prazo | Ação |
|---|---|
| **18/05/2026** | Expedir a Portaria Interna nº 01/2026-RI com nome real do colaborador |
| **Até 22/05/2026** | Iniciar levantamento diagnóstico completo do acervo |
| **Até 17/06/2026** | Preencher campos `[a apurar]` e finalizar o Relatório Diagnóstico |
| **Até 05/06/2026** | Revisão final e assinatura de todos os documentos do pacote |
| **Até 10/06/2026** | Protocolo/juntada do pacote completo nos autos do PROAD |
| **Jun/2026** | Início da alimentação mensal corrente do IERI-e (atos de mai/2026) |
| **Até set/2026** | Regularização retroativa dos envios (condicionada ao ONR) |
| **Nov/2026** | Entrega do 1º Relatório Semestral de cumprimento |
| **Mai/2027** | Revisão do Plano de Ação (versão 2.0) |

---

## 10. Evidências previstas

| Evidência | Prazo | Status |
|---|---|---|
| Portaria Interna nº 01/2026-RI assinada | 18/05/2026 | Pendente |
| Pacote completo juntado nos autos do PROAD | ~10/06/2026 | Pendente |
| Relatório Diagnóstico Inicial (campos preenchidos) | 30 dias pós-portaria | Pendente |
| Comprovantes mensais de envio ao ONR (IERI-e) | A partir de jun/2026 | Pendente |
| Registros de inserção no SIG-RI | A partir de nov/2026 | Pendente |
| 1º Relatório Semestral de cumprimento | Nov/2026 | Pendente |

---

## 11. Nota de responsabilidade

Este documento é de uso interno da serventia. As informações aqui contidas são baseadas em dados parciais e estão em validação. A serventia está em processo de adequação progressiva ao Provimento CNJ nº 195/2025, conforme os prazos estabelecidos pela Corregedoria-Geral de Justiça do Estado de Goiás (48 meses para o legado).

**Não declarar conformidade plena.** O sistema Cartório System gera evidências e registros de suporte à adequação — não substitui o cumprimento direto das obrigações no Portal RI Digital/ONR.

---

*Atualizado em: 2026-05-16. Revisar após a expedição da portaria e antes da juntada do pacote.*
