# Análise dos Manuais do Portal RI Digital / ONR

**Status:** PRELIMINAR — Uso interno; não destinado a juntada nesta etapa  
**PROAD:** Nº 202509000672377  
**Versão:** 1.0 (2026-05-16)  
**Fonte:** Manuais oficiais do ONR/Portal RI Digital

> Este documento consolida orientações extraídas dos manuais ONR disponíveis localmente. Serve como subsídio operacional interno para o POP-RI-001 e para o Plano de Ação. Não substitui a leitura direta dos manuais originais.

---

## 1. Manuais analisados

| Manual | Versão | Tema | Relevância |
|---|---|---|---|
| Manual Técnico Operacional | v1.3 (25/02/2026) | Marco normativo do Mapa / IERI-e / SIG-RI | FUNDAMENTAL — define obrigações, layout, categorias e indicadores do IERI-e |
| Manual da API para Envio dos Polígonos | v1.0 | API REST ONR para envio de polígonos | DIRETO — alternativa à inserção manual; integração futura |
| Manual do Mapa | v2.7 | Operação prática da intranet logada | DIRETO — fluxo prático do SIG-RI |
| Manual do Mapa Público | v1.0 | Área pública (mapa.onr.org.br) | INDIRETO — consulta pública e transparência |
| Manual CAD / ITN 003/2025 | v1.1 | Comunicação de Atos e Dados | ADJACENTE — obrigação correlata distinta do IERI-e |
| Manual Gerenciador de Imóveis Rurais de Estrangeiros | v1.2 | Registro específico de imóveis de estrangeiros | RELACIONADO — integra ao Mapa (camada 8) |

---

## 2. Fluxos operacionais relevantes

### 2.1. Acesso inicial ao Portal RI Digital (área logada)

**Pré-requisitos:**
- Conexão com a internet
- Navegador atualizado
- Certificado digital ICP-Brasil A1 ou A3

**Passo a passo resumido:**
1. Acessar `mapa.onr.org.br`
2. Clicar em "Entrar" → "Entrar com certificado digital"
3. Selecionar o certificado e inserir a senha
4. No 1º acesso: aceitar Termo de Uso do ONR
5. Em "Competência registral" → "Gerenciar usuário" → incluir substituto e prepostos

**Evidência:** Print/screenshot do cadastro de usuários — arquivar no Dossiê IERI-e/SIG-RI.

**Pendência:** Confirmar com ONR se certificado A1 é aceito especificamente para geração de chave da API REST (Manual da API menciona e-CPF A3).

---

### 2.2. Alimentação do IERI-e (envio estatístico mensal)

Conforme Manual Técnico Operacional v1.3:

- Envio mensal de dados estatísticos dos atos registrais praticados no mês anterior
- Canal: Portal RI Digital (preenchimento ou upload)
- Layout: definido pelo ONR nas especificações técnicas
- Prazo: até o último dia útil do mês subsequente (art. 5º, §único, Prov. 195/2025)

**Nota:** O Manual Técnico v1.3 é a referência normativa vigente. Revisar este POP quando o ONR publicar nova versão.

---

### 2.3. Inserção de polígonos no SIG-RI (Manual do Mapa v2.7)

**Modalidades de inserção:**
- **Individual:** upload de arquivo shapefile (.shp) para um imóvel específico
- **Em lote:** upload de múltiplos polígonos simultaneamente

**Fluxo de aprovação após inserção:**
1. Upload do shapefile com atributos exigidos pelo ONR
2. Verificação automática de sobreposição com o mosaico
3. Análise e aprovação pelo oficial
4. Polígono fica visível no Mapa público (art. 343-H)

**Atributos obrigatórios do shapefile:** conforme especificações do Manual Técnico v1.3 e Manual do Mapa v2.7 — validar com profissional técnico habilitado antes da inserção.

---

### 2.4. API REST do ONR (Manual da API v1.0)

- 3 endpoints REST documentados para envio programático de polígonos
- Autenticação: token Bearer com validade de 15 dias
- Geração de chave: requer certificado digital (confirmar tipo com ONR)
- Script QGIS disponível como exemplo

**Situação atual:** Adoção pela serventia condicionada a:
- Habilitação técnica junto ao ONR
- Capacidade do sistema Engegraph de integração
- Validação operacional

**Não há compromisso de uso imediato da API REST.**

---

### 2.5. ITN 003/2025 — Módulo "Incluir Atos e Dados" (Manual CAD v1.1)

Obrigação **correlata e distinta** do IERI-e:

| Item | Dado |
|---|---|
| Escopo | Imóveis rurais e imóveis urbanos da União |
| Início obrigatório | 09/03/2026 |
| Canal | Módulo "Incluir Atos e Dados" no Portal RI Digital |
| Modalidade | Preenchimento manual de formulário ou upload de arquivo `.json` (schemas rural/urbano) |

**Abas do formulário:** Registro / Imóvel / Transações / Partes / Georref.

A serventia deve identificar os atos aplicáveis ao escopo da ITN 003/2025 e criar rotina interna específica (separada do IERI-e mensal).

---

### 2.6. Gerenciador de Imóveis Rurais de Estrangeiros (Manual v1.2)

- Registro específico exigido por legislação aplicável
- Integra ao Mapa como camada separada (camada 8)
- Fluxo: configuração da serventia → cadastro do imóvel (5 abas) → gerenciamento e rascunhos
- Verificar se há imóveis rurais de estrangeiros no acervo da circunscrição

---

## 3. Pendências e pontos de atenção identificados

| Código | Pendência | Gravidade |
|---|---|---|
| M.01 | Confirmar com ONR o tipo de certificado exigido para geração de chave da API REST (A1 vs. A3) | MÉDIA |
| M.02 | Divergência nos manuais sobre periodicidade de atualização do SIGEF no Mapa (30 x 60 dias) — confirmar com ONR | MÉDIA |
| M.03 | Validar acesso da serventia no Portal RI Digital (perfil, cadastro de usuários, aceite do Termo de Uso) | ALTA |
| M.04 | Confirmar procedimento de envio retroativo do IERI-e (set/2025–abr/2026) junto ao ONR | ALTA |
| M.05 | Identificar imóveis rurais de estrangeiros no acervo para cumprimento da obrigação específica | BAIXA |
| M.06 | Verificar schemas JSON da ITN 003/2025 quando formalmente publicados pelo ONR | MÉDIA |

---

## 4. Impactos nos documentos do pacote PROAD

| Documento | Impacto identificado |
|---|---|
| Plano de Ação (Anexo I) | Pendências M.03 e M.04 devem ser registradas na seção de dependências externas |
| POP-RI-001 (Anexo III) | Fluxos dos manuais subsidiam as etapas M.1–M.9 (IERI-e) e S.1–S.7 (SIG-RI) |
| Portaria 01/2026-RI (Anexo II) | Certificado digital da Oficial Registradora deve ser verificado (A1 ou A3) |
| Matriz de Evidências (Anexo V) | Pendências M.01–M.06 devem ser registradas como condicionais |

---

## 5. Manuais que ainda precisam ser analisados / validados

- `[ ]` Confirmar versão mais recente do Manual Técnico Operacional (verificar se há atualização pós-v1.3)
- `[ ]` Verificar se ONR publicou guia específico para envios retroativos do IERI-e
- `[ ]` Consultar ONR sobre schemas JSON definitivos da ITN 003/2025 (rural e urbano)
- `[ ]` Analisar com profissional técnico habilitado os atributos obrigatórios do shapefile para SIG-RI

---

*Documento de referência interna. Revisar quando o ONR publicar novas versões dos manuais.*
