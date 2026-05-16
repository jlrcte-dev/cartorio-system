# Relatório Analítico Preliminar — Provimento CNJ nº 195/2025

**Status:** PRELIMINAR  
**Uso:** Documento interno de trabalho — NÃO destinado a juntada direta no PROAD  
**PROAD:** Nº 202509000672377  
**Serventia:** Cartório Costa Teixeira — Terezópolis de Goiás / Comarca de Goianápolis — GO  
**Elaborado em:** Maio de 2026  
**Atualizado em:** 2026-05-16

> **Atenção:** Este documento é preliminar. Dados de matrículas são parciais e estão em validação. Não afirma conformidade plena. Percentuais e totais precisam ser confirmados diretamente no sistema Engegraph e nos livros do Registro de Imóveis.

---

## 1. Contexto e objetivo

Este relatório reúne a análise interna da situação da serventia em relação às exigências do **Provimento CNJ nº 195/2025**, que instituiu o IERI-e e o SIG-RI.

Objetivo: subsidiar a resposta ao PROAD nº 202509000672377, orientar a elaboração do Plano de Ação e organizar as providências internas para adequação progressiva.

---

## 2. Linha do tempo dos atos

| Data | Ato |
|---|---|
| 03/06/2025 | Publicação do Provimento CNJ nº 195/2025 (DJe/CNJ nº 121/2025) |
| 01/09/2025 | Entrada em vigor do Provimento |
| 20/10/2025 | Despacho/Assessoria Correicional nº 4838/2025 — notificação com prazo de 60 dias |
| 26/11/2025 | Ofício nº 049/2025_DF — 1ª notificação pelo Diretor do Foro (Dr. Gabriel Consigliero Lessa) — prazo 60 dias (~25/01/2026) |
| 26/11/2025–29/04/2026 | Ausência de manifestação da serventia nos autos |
| 29/04/2026 | Despacho/Ofício nº 703/2026 — 4º Juiz Auxiliar da CGJ determina nova notificação |
| 11/05/2026 | Ofício nº 045/2026/GNP — 2ª notificação (Dr. Leonardo de Camargos Martins) — **prazo 30 dias (~10/06/2026)** |

**Prazo vigente:** ~10/06/2026 (30 dias a contar de 11/05/2026).

---

## 3. Obrigações exigidas da serventia

| Obrigação | Base normativa | Prazo | Situação |
|---|---|---|---|
| Rotina interna de levantamento do acervo | Art. 4º, Prov. 195/2025 | A partir de 01/09/2025 | Em estruturação |
| Alimentação mensal do IERI-e ao ONR | Art. 5º e §único, Prov. 195/2025 | Até último dia útil do mês subsequente | Envios set/2025–abr/2026 em aberto |
| Inserção de imóveis georreferenciados no SIG-RI | Art. 4º e 343-F, Prov. 195/2025 | 48 meses (até 01/09/2029, conforme Goiás) | Pendente levantamento |
| Juntada do Plano de Ação preenchido | Art. 4º e Ofício 045/2026/GNP | **~10/06/2026** | Em elaboração |
| Relatórios semestrais de cumprimento | Despacho 4838/2025 | A cada 6 meses | 1º previsto: nov/2026 |
| Saneamento progressivo do legado | Arts. 343-C e 440-AR a 440-BG | 48 meses (até 01/09/2029) | Pendente diagnóstico |

---

## 4. Fontes utilizadas

- Provimento CNJ nº 195/2025 (texto completo)
- Ofício Circular nº 103/2025 — Corregedoria-Geral GO
- Despacho/Ofício nº 703/2026 — 4º Juiz Auxiliar CGJ
- Ofício nº 045/2026/GNP — Diretoria do Foro da Comarca de Goianápolis
- Manual Técnico Operacional ONR v1.3 (25/02/2026)
- Manuais complementares do Portal RI Digital (Mapa, API REST, Mapa Público, Gerenciador de Imóveis Rurais, ITN 003/2025)
- Dados parciais de Indicadores Reais extraídos localmente via scripts sanitizados

> **Limitação de fonte:** Os dados quantitativos de matrículas foram obtidos a partir de extração parcial do Engegraph. Não refletem necessariamente o acervo completo. O levantamento diagnóstico formal será concluído nos 30 dias seguintes à portaria de designação.

---

## 5. Situação atual do levantamento de matrículas / Indicadores Reais

O levantamento diagnóstico encontra-se **em andamento**. Os dados abaixo são **parciais e preliminares**, extraídos de relatórios locais sanitizados, sem PII.

| Campo | Situação |
|---|---|
| Total de matrículas no acervo | A apurar — estimativas disponíveis, não validadas |
| Matrículas urbanas | Dados parciais disponíveis em `_local_data/` |
| Matrículas rurais | Dados parciais disponíveis em `_local_data/` |
| Imóveis georreferenciados (INCRA/SIGEF) | Parcialmente identificados |
| Pendências de saneamento | A apurar após diagnóstico completo |

> **Nota:** Todos os dados brutos e relatórios operacionais de matrículas ficam em `_local_data/ri_inventory/` (não versionados). O repositório contém apenas documentação agregada e scripts sanitizados.

---

## 6. Achados preliminares

1. **Dependência técnica do Engegraph:** A exportação automática compatível com o layout do IERI-e ainda não está confirmada junto ao fornecedor. É uma dependência externa à serventia.

2. **Dependência do Manual ONR:** Parte das obrigações depende das especificações técnicas do ONR. O Manual Técnico Operacional v1.3 (25/02/2026) está disponível e adotado como referência.

3. **Regularização retroativa condicionada:** O envio retroativo dos atos de set/2025 a abr/2026 está condicionado à confirmação do procedimento aplicável no Portal RI Digital junto ao ONR.

4. **Credenciamento de profissional técnico:** A inserção de polígonos no SIG-RI exige profissional habilitado e credenciado junto ao ONR (art. 343-G). Processo em avaliação.

5. **ITN 003/2025:** Obrigação correlata e distinta do IERI-e — módulo "Incluir Atos e Dados" para imóveis rurais e urbanos da União. Início obrigatório: 09/03/2026. Será tratada em rotina interna específica.

---

## 7. Riscos administrativos identificados

| Risco | Gravidade | Mitigation |
|---|---|---|
| Não resposta dentro do prazo (~10/06/2026) | CRÍTICA | Protocolar pacote antes do prazo; prioridade máxima |
| Plano de Ação incompleto devolvido pela CGJ | ALTA | Completar campos `[a apurar]` antes de protocolar |
| Promessa de prazos inviáveis | ALTA | Usar linguagem de adequação progressiva; registrar dependências externas |
| Escalada correicional por nova omissão | ALTA | Juntada do pacote completo com antecedência |

---

## 8. Estratégia de resposta adotada

1. **Juntada dentro do prazo:** Protocolar antes de ~10/06/2026, com antecedência de 3–5 dias úteis.
2. **Pacote documental completo:** Manifestação + Plano de Ação + Portaria + POP + Diagnóstico + Matriz de Evidências.
3. **Posicionamento correto:** Reconhecer a obrigação sem questionar o normativo; registrar dependências externas de forma técnica; não prometer conformidade integral imediata.
4. **Governança interna demonstrada:** Portaria, POP e Matriz de Evidências demonstram seriedade institucional.

---

## 9. Próximos passos

1. Expedir a Portaria Interna nº 01/2026-RI em **18/05/2026** com nome real do colaborador designado.
2. Completar o levantamento diagnóstico (campos `[a apurar]`) nos 30 dias seguintes à portaria.
3. Revisar a minuta de manifestação e o Plano de Ação com os dados apurados.
4. Finalizar e protocolar o pacote completo até **~10/06/2026**.

---

*Documento preliminar. Revisar antes de qualquer uso externo.*
