# POP-RI-001 — Alimentação Mensal do IERI-e e Atualização do SIG-RI

**Status:** MINUTA OPERACIONAL — DEPENDE DE VALIDAÇÃO PRÁTICA no Portal RI Digital  
**Referência:** Anexo III da Manifestação — PROAD nº 202509000672377  
**Versão:** 1.0 | **Aprovação prevista:** Márcia Maria da Silva Costa Teixeira  
**Atualizado em:** 2026-05-16

> **Atenção:** Este POP é uma minuta operacional. Os fluxos devem ser validados na prática após o início das operações no Portal RI Digital. Campos marcados com `[___]` devem ser preenchidos antes da aprovação final.

---

## 1. Objetivo

Padronizar os procedimentos operacionais para:

a) Alimentação mensal dos atos registrais ao ONR (IERI-e);  
b) Inserção progressiva dos imóveis georreferenciados no SIG-RI (formação do mosaico);  
c) Levantamento e saneamento progressivo do acervo legado;  
d) Produção e arquivamento de evidências auditáveis de cumprimento do Provimento CNJ nº 195/2025.

---

## 2. Escopo

Aplica-se a todas as atividades do setor de Registro de Imóveis relacionadas ao cumprimento do Provimento CNJ nº 195/2025. Não se aplica a outros ofícios da serventia (Notas, Protesto, RC etc.).

---

## 3. Base normativa

- Provimento CNJ nº 195/2025 — Arts. 4º, 5º, 320-O §1º, 343-A a 343-J, 343-F, 343-G, 440-AR a 440-BG
- Decisão/Ofício Circular nº 103/2025 — Corregedoria-Geral GO
- Portaria Interna nº 01/2026-RI desta serventia (18/05/2026)
- Manual Técnico Operacional ONR v1.3 (25/02/2026)
- Manuais complementares: Manual do Mapa (v2.7), Manual da API REST (v1.0), Manual do Mapa Público (v1.0), Manual CAD/ITN 003/2025 (v1.1), Manual Gerenciador de Imóveis Rurais de Estrangeiros (v1.2)

---

## 4. Definições

| Termo | Definição |
|---|---|
| IERI-e | Inventário Estatístico Eletrônico do Registro de Imóveis — base de dados estatísticos do RI, gerida pelo ONR |
| SIG-RI | Sistema de Informações Geográficas do Registro de Imóveis — base de dados geográficos, gerida pelo ONR |
| ONR | Operador Nacional do Sistema de Registro Eletrônico de Imóveis |
| SREI | Sistema de Registro Eletrônico de Imóveis |
| SIGEF | Sistema de Gestão Fundiária do INCRA |
| Mosaico | Representação geográfica das poligonais georreferenciadas dos imóveis registrados |
| Legado | Acervo histórico anterior ao Provimento CNJ nº 195/2025 |
| Ato corrente | Ato registral praticado após 01/09/2025 |
| Engegraph | Sistema de automação atualmente utilizado pela serventia |

---

## 5. Responsáveis

| Função | Nome |
|---|---|
| Responsável geral / Autoridade aprovadora | Márcia Maria da Silva Costa Teixeira (Oficial Registradora e Tabeliã) |
| Responsável operacional principal | André (Suboficial) — Portaria nº 01/2026-RI |
| Responsável substituto | [a designar] — a ser definido pela Oficial Registradora; enquanto não designado, supervisão direta pela Oficial Registradora |
| Profissional técnico habilitado (SIG-RI) | [a confirmar] |

---

## 6. Fontes de dados

**Para o IERI-e (alimentação mensal):**
- Livro 1 (Protocolo) — registro de todos os atos praticados no mês
- Livro 4 (Indicador Real) — dados dos imóveis
- Sistema Engegraph — exportação dos atos registrais conforme layout do ONR
- Matrículas e transcrições — especialidade objetiva e subjetiva

**Para o SIG-RI (georreferenciamento):**
- Matrículas com descrição georreferenciada (coordenadas geodésicas)
- Sistema SIGEF/INCRA — imóveis rurais certificados
- Memorial descritivo dos imóveis rurais e urbanos georreferenciados
- Profissional técnico habilitado credenciado pelo ONR

**Para o levantamento do legado:**
- Todos os livros do Registro de Imóveis
- Acervo de matrículas e transcrições (físico e digital)
- Indicadores Real e Pessoal

---

## 7. Fluxo mensal — Alimentação do IERI-e

| Etapa | Ação | Prazo interno | Responsável |
|---|---|---|---|
| M.1 | Verificar se todos os atos do mês foram lançados no Engegraph | Último dia útil do mês M | Operadores RI |
| M.2 | Extrair/exportar dados do mês anterior (M-1) do Engegraph conforme layout ONR | Até o dia 5 do mês M+1 | Responsável operacional |
| M.3 | Conferir dados: quantidade de atos por tipo, campos obrigatórios, ausência de duplicidades | Até o dia 10 do mês M+1 | Responsável operacional + Oficial |
| M.4 | Corrigir inconsistências identificadas na conferência | Até o dia 15 do mês M+1 | Responsável operacional |
| M.5 | Revisão e aprovação final dos dados | Até o dia 20 do mês M+1 | Oficial Registradora |
| M.6 | Envio dos dados ao ONR conforme layout e especificações | Até o **último dia útil** do mês M+1 | Responsável operacional |
| M.7 | Arquivar comprovante/protocolo de envio e planilha de conferência | Mesmo dia do envio | Responsável operacional |
| M.8 | Elaborar Relatório Mensal Interno de Cumprimento | Até 5 dias após M.6 | Responsável operacional |
| M.9 | Revisar e arquivar o Relatório Mensal Interno | Até 5 dias após M.8 | Oficial Registradora |

> **Observação crítica:** Se o Engegraph ainda não disponibilizar exportação automática no layout do ONR, a extração deverá ser feita manualmente (etapa M.2) conforme instruções do Manual Técnico ONR, até que a integração seja viabilizada. Comunicar formalmente ao ONR e ao fornecedor, registrando no Dossiê IERI-e/SIG-RI.

---

## 8. Checklist de conferência mensal

Preencher e arquivar a cada envio:

- `[ ]` Todos os atos do mês foram lançados no sistema?
- `[ ]` A extração abrange o período correto (mês M-1)?
- `[ ]` Os campos obrigatórios do layout ONR estão preenchidos?
- `[ ]` O número de atos extraídos corresponde ao Livro de Protocolo?
- `[ ]` Não há duplicidade de atos na extração?
- `[ ]` O formato do arquivo de envio está correto?
- `[ ]` A Oficial Registradora revisou e aprovou?
- `[ ]` O envio foi realizado dentro do prazo (até o último dia útil do mês)?
- `[ ]` O comprovante de envio foi arquivado?
- `[ ]` O Relatório Mensal Interno foi elaborado e arquivado?

**Em caso de inconsistência:**
a) Registrar no Relatório Mensal Interno;  
b) Corrigir antes do envio, se possível;  
c) Se a inconsistência decorrer de limitação do Engegraph, comunicar formalmente ao fornecedor e ao ONR;  
d) Submeter apenas dados que possam ser validados conforme o canal operacional do ONR. Quando houver impedimento técnico, registrar a pendência, buscar orientação formal do ONR/fornecedor e manter evidência no Dossiê IERI-e/SIG-RI.

---

## 9. Canal de envio ao ONR

O envio observa o Manual Técnico Operacional ONR v1.3 (25/02/2026). Canais disponíveis:

| Canal | Situação |
|---|---|
| Portal RI Digital (preenchimento manual) | Disponível — referência operacional atual |
| Exportação automática pelo Engegraph | Pendente de confirmação com o fornecedor |
| API REST do ONR (envio programático) | Documentada — adoção condicionada a habilitação técnica |

---

## 10. Fluxo de inserção no SIG-RI

| Etapa | Ação | Responsável |
|---|---|---|
| S.1 | Identificar matrículas com descrição georreferenciada (rurais INCRA, urbanas) | Responsável operacional |
| S.2 | Classificar imóveis conforme grupos do art. 343-C, II (a–e) | Responsável operacional + Oficial |
| S.3 | Preparar arquivos de polígonos (.shp) com os atributos exigidos pelo ONR | Profissional técnico habilitado |
| S.4 | Inserir polígonos no SIG-RI via Portal RI Digital (individual ou em lote) | Profissional técnico habilitado |
| S.5 | Verificar sobreposições no mosaico após inserção | Responsável operacional |
| S.6 | Arquivar registros de inserção no Dossiê IERI-e/SIG-RI | Responsável operacional |
| S.7 | Reportar evolução no Relatório Semestral | Oficial Registradora |

> **Prioridade de inserção:** Imóveis rurais com georreferenciamento certificado pelo INCRA/SIGEF (Grupo A do art. 343-C).

---

## 11. Fluxo de levantamento do legado

| Etapa | Ação | Prazo |
|---|---|---|
| L.1 | Consultar livros físicos e digitais do RI | 0–30 dias após portaria |
| L.2 | Consultar Engegraph (relatórios gerenciais) | 0–30 dias após portaria |
| L.3 | Verificar matrículas com averbação de georreferenciamento | 0–30 dias após portaria |
| L.4 | Consultar SIGEF/INCRA para rurais certificados | 0–30 dias após portaria |
| L.5 | Preencher campos `[a apurar]` do Plano de Ação | 0–30 dias após portaria |
| L.6 | Identificar e priorizar irregularidades | 6–24 meses |
| L.7 | Promover saneamento progressivo | 6–48 meses (até 01/09/2029) |

---

## 12. Tratamento de divergências e impedimentos

| Situação | Ação |
|---|---|
| Engegraph não exporta no layout ONR | Fazer envio manual; comunicar formalmente ao fornecedor e ao ONR; registrar no Dossiê |
| ONR não confirma procedimento de envio retroativo | Aguardar confirmação; registrar pendência; manter envios correntes |
| Profissional técnico não disponível para SIG-RI | Registrar impossibilidade técnica; manter levantamento em andamento; comunicar à Corregedoria se necessário |
| Inconsistência identificada após o envio | Registrar; corrigir no envio do mês seguinte; comunicar ao ONR se relevante |

---

## 13. Rotina correlata — ITN 003/2025

> **Status:** Pendente de validação operacional — fluxo a ser confirmado junto ao ONR e ao fornecedor Engegraph.

A ITN 003/2025 (Instrução Técnica Normativa — módulo "Incluir Atos e Dados") é obrigação correlata e distinta do IERI-e/SIG-RI, com vigência a partir de 09/03/2026. Aplica-se a imóveis rurais e imóveis urbanos da União.

| Etapa | Ação |
|---|---|
| T.1 | Identificar os atos registrais abrangidos pela ITN 003/2025 (imóveis rurais e urbanos da União) |
| T.2 | Verificar, para cada ato, se o imóvel é rural ou urbano da União conforme os critérios da ITN |
| T.3 | Conferir os campos obrigatórios no módulo "Incluir Atos e Dados" do Portal RI Digital |
| T.4 | Registrar o envio realizado ou o impedimento técnico no Dossiê IERI-e/SIG-RI |
| T.5 | Revisar mensalmente as pendências relacionadas à ITN 003/2025 |

---

## 14. Revisão e aprovação

| Item | Dado |
|---|---|
| Versão | 1.0 |
| Data de elaboração | [mês/2026] |
| Próxima revisão | [mai/2027] ou quando o ONR publicar nova versão do Manual Técnico |
| Aprovação prevista | Márcia Maria da Silva Costa Teixeira — Oficial Registradora e Tabeliã |

---

*Status: MINUTA OPERACIONAL. Validar fluxos na prática após início das operações no Portal RI Digital.*
