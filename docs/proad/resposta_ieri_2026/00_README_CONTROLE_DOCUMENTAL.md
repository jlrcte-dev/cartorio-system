# Controle Documental — Resposta IERI/SIG-RI 2026

**PROAD:** Nº 202509000672377  
**Ofício de referência:** Nº 045/2026/GNP (11/05/2026)  
**Prazo vigente:** ~10/06/2026  
**Atualizado em:** 2026-05-16

---

## 1. Finalidade da pasta

Esta pasta contém a base documental de trabalho para resposta ao PROAD da Corregedoria do Foro Extrajudicial relacionado ao cumprimento do Provimento CNJ nº 195/2025, que instituiu o **IERI-e** (Inventário Estatístico Eletrônico do Registro de Imóveis) e o **SIG-RI** (Sistema de Informações Geográficas do Registro de Imóveis).

Os documentos aqui presentes servem como **base de trabalho interna** para preparação do pacote documental a ser juntado nos autos do PROAD. Nenhum documento desta pasta deve ser protocolado diretamente sem revisão formal e validação administrativa.

---

## 2. Status geral

> **Atenção:** Todos os documentos nesta pasta são **MINUTAS** ou **PRELIMINARES**, em consolidação após o marco administrativo da portaria de designação.

A documentação será consolidada em definitivo a partir de **18/05/2026**, data prevista para expedição da **Portaria Interna de Designação nº 01/2026-RI**, que formalizará o colaborador responsável pelas atividades do IERI-e e do SIG-RI.

Dados de matrículas e Indicadores Reais são **parciais** — o levantamento diagnóstico completo está em andamento e será concluído nos 30 dias seguintes à expedição da portaria.

---

## 3. Marco administrativo

| Item | Situação |
|---|---|
| Colaborador responsável definido | Sim — aguardando formalização na portaria |
| Nome do responsável (antes da portaria) | `[NOME_DO_COLABORADOR_DESIGNADO]` |
| Portaria de designação prevista | **18/05/2026** |
| Prazo PROAD vigente | ~10/06/2026 |

---

## 4. Classificação dos documentos

| Documento | Status | Uso recomendado | Observações |
|---|---|---|---|
| `00_README_CONTROLE_DOCUMENTAL.md` | CONTROLE INTERNO | Orientação da equipe | Este documento |
| `01_relatorio_analitico_preliminar.md` | PRELIMINAR | Suporte à decisão interna | Não juntar diretamente — base para revisar o diagnóstico |
| `02_minuta_manifestacao_proad.md` | MINUTA | Revisar e assinar antes de protocolar | Inserir data, nomes e conferir todos os campos |
| `03_plano_acao_ieri_sig_ri.md` | MINUTA | Completar campos `[a apurar]` e assinar | Anexo I da manifestação |
| `04_minuta_portaria_designacao_ri.md` | MINUTA | Expedir em 18/05/2026 com nome real | Substituir `[NOME_DO_COLABORADOR_DESIGNADO]` |
| `05_pop_ri_001_alimentacao_ieri_sig_ri.md` | MINUTA OPERACIONAL | Revisar após validação prática | Depende de validação no Portal RI Digital |
| `06_diagnostico_inicial_historico.md` | HISTÓRICO | Referência — não usar como versão final | Gerado com base em fonte inicial; confrontar com dados atualizados |
| `07_matriz_evidencias_controles.md` | EM VALIDAÇÃO | Suporte ao monitoramento | Atualizar status conforme evolução |
| `08_checklist_juntada.md` | EM VALIDAÇÃO | Usar antes de protocolar o pacote | Marcar itens conforme conclusão |
| `09_pendencias_alertas.md` | EM VALIDAÇÃO | Controle de riscos | Atualizar à medida que pendências forem resolvidas |
| `10_analise_manuais_ri_digital.md` | PRELIMINAR | Referência operacional interna | Consolidar orientações dos manuais ONR |

**Status possíveis:**
- `MINUTA` — rascunho a ser validado e assinado
- `PRELIMINAR` — análise inicial, pode conter imprecisões
- `HISTÓRICO` — preservado por valor documental; não usar sem confronto com dados atuais
- `EM VALIDAÇÃO` — em uso ativo, sendo atualizado conforme evolução
- `PRONTO PARA REVISÃO INTERNA` — aguarda revisão antes de protocolo
- `NÃO USAR COMO VERSÃO FINAL` — conteúdo superado ou incompleto

---

## 5. Limitações conhecidas

1. **Dados de matrículas são parciais.** O levantamento diagnóstico completo depende do acesso ao Engegraph e dos livros físicos — trabalho a ser realizado nos 30 dias seguintes à portaria.
2. **Relatórios analíticos anteriores podem conter imprecisões.** Foram gerados a partir de fontes iniciais com limitações — o Relatório Analítico (doc. 01) foi atualizado, mas percentuais e totais precisam ser validados diretamente no sistema.
3. **Conclusões definitivas dependem de validação no sistema.** Nenhum número declarado como final deve ser usado sem confronto com o Engegraph e com os livros do RI.
4. **Dados brutos não devem ser versionados.** CSVs, JSONs e relatórios operacionais ficam em `_local_data/` (ignorados pelo Git).
5. **O Plano de Ação contém campos `[a apurar]`.** Serão preenchidos após o levantamento diagnóstico (30 dias pós-portaria).

---

## 6. Regras de uso

- **Não protocolar** documento marcado como `HISTÓRICO` ou `MINUTA` sem revisão e validação formal.
- **Não anexar** dados brutos de matrículas (CPF, nomes de proprietários, valores) em nenhum documento.
- **Não usar** percentuais ou conclusões finais sem validação direta no sistema.
- **Manter separação** entre evidências confirmadas e hipóteses ou estimativas.
- **Manter rastreabilidade** — registrar data de atualização e responsável ao modificar qualquer documento.
- **Não declarar conformidade plena** — o sistema está em adequação progressiva conforme os prazos do Provimento.

---

## 7. Próximos passos

| Prazo | Ação |
|---|---|
| **18/05/2026** | Expedir a Portaria Interna nº 01/2026-RI com nome real do colaborador designado |
| **Até ~22/05/2026** | Validação interna dos dados de RI e dos campos `[a apurar]` |
| **Até ~05/06/2026** | Revisão final da minuta de manifestação e do Plano de Ação |
| **Até ~10/06/2026** | Protocolo/juntada do pacote completo nos autos do PROAD |
| **Novembro/2026** | Entrega do 1º Relatório Semestral de cumprimento |

---

*Pasta criada em: 2026-05-16. Manter atualizado conforme evolução da documentação.*
