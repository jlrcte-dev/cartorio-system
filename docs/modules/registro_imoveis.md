# Módulo Registro de Imóveis — Documentação Inicial

**Status:** Pré-implementação — análise e base sanitizada apenas
**Fase atual:** Inventário técnico completo (urbanos + rurais via Indicador Real JSON)
**Módulo de produção:** Não implementado — sem rotas, migrations ou banco

---

## 1. Objetivo do módulo

O módulo `registro_imoveis` (RI) será o componente do Cartório System responsável por:

- Apoiar o cumprimento do Provimento CNJ nº 195/2025 (IERI-e e SIG-RI);
- Fornecer base técnica sanitizada para o levantamento diagnóstico do legado;
- Futuramente, integrar-se ao fluxo de envio ao ONR e ao SIG-RI;
- Gerar evidências auditáveis de conformidade regulatória para o setor de Registro de Imóveis.

O módulo **não substitui o Engegraph** e **não se integra diretamente a ele** nesta fase.  
A ingestão de dados ocorre por extração sanitizada de relatórios locais.

---

## 2. Relação com o Provimento CNJ nº 195/2025

O Provimento CNJ nº 195/2025 (vigente desde 01/09/2025) impõe às serventias de Registro de Imóveis:

| Obrigação | Referência normativa | Prazo |
|---|---|---|
| Alimentação mensal do IERI-e ao ONR | Art. 5º e §único | Até o último dia útil do mês subsequente |
| Inserção de imóveis georreferenciados no SIG-RI | Arts. 343-D a 343-J | 48 meses (até 01/09/2029) |
| Levantamento diagnóstico do legado | Arts. 343-A a 343-C | 0–30 dias (fase inicial) |
| Saneamento progressivo de irregularidades | Arts. 440-AR a 440-BG | 48 meses |
| Relatórios semestrais de cumprimento | Plano de Ação | A cada 6 meses |

A serventia (Terezópolis de Goiás) responde ao PROAD nº 202509000672377  
(Ofício nº 045/2026/GNP, prazo até 10/06/2026).

---

## 3. Relação com IERI-e, SIG-RI e ITN 003/2025

### IERI-e — Inventário Estatístico Eletrônico do Registro de Imóveis
- Base de dados estatísticos dos atos registrais, gerida pelo ONR.
- Alimentação mensal obrigatória via Portal RI Digital ou exportação do sistema interno.
- O Engegraph ainda não disponibiliza exportação automática no layout do ONR (pendência — Alerta T.2 do PROAD).

### SIG-RI — Sistema de Informações Geográficas do Registro de Imóveis
- Base geográfica das poligonais dos imóveis registrados.
- Prioridade: Grupo A (rurais certificados pelo INCRA/SIGEF).
- Exige profissional técnico habilitado credenciado no ONR (art. 343-G).

### ITN 003/2025 — Módulo "Incluir Atos e Dados"
- Obrigação correlata e distinta do IERI-e.
- Escopo: imóveis rurais e imóveis urbanos da União.
- Início obrigatório: 09/03/2026.
- Canal: módulo "Incluir Atos e Dados" no Portal RI Digital.
- Envio manual (formulário) ou por arquivo `.json` (schemas separados rural/urbano).

---

## 4. Regra de proteção de dados

O módulo RI lida com dados de proprietários de imóveis — CPF, CNPJ, nomes e documentos.

**Regras permanentes:**

1. Dados pessoais brutos não são incorporados ao repositório em nenhuma hipótese.
2. Relatórios brutos do Engegraph ficam exclusivamente em `_local_data/ri_inventory/raw/` (ignorado pelo Git).
3. A base sanitizada (`_local_data/ri_inventory/sanitized/`) não contém PII.
4. O script extrator valida a ausência de PII antes de salvar qualquer saída.
5. Fixtures, testes e exemplos usam exclusivamente dados fictícios.
6. Nenhuma rota ou endpoint do módulo de produção expõe dados pessoais sem controle LGPD.
7. Toda ingestão de dados reais exige autorização da Diretoria da serventia.

---

## 5. Fluxo de ingestão sanitizada (fase atual)

```
Relatório Engegraph (PDF pesquisável)
       │
       ▼
_local_data/ri_inventory/raw/              ← Arquivos brutos — NÃO versionados
       │
       ▼
scripts/local_tools/extract_ri_rural_inventory.py
  ├── Extração de campos técnicos (matrícula, tipo, município, área, indicadores)
  ├── Remoção de PII (nomes, CPF, CNPJ descartados — nunca salvos)
  ├── Validação anti-PII (abort se detectar CPF/CNPJ/RG na saída)
  └── Salvamento apenas de campos permitidos
       │
       ▼
_local_data/ri_inventory/sanitized/        ← Base sanitizada — NÃO versionada
  ├── ri_rural_inventory_sanitized.csv
  └── ri_rural_inventory_sanitized.json
       │
       ▼
_local_data/ri_inventory/reports/          ← Relatório agregado — NÃO versionado
  └── ri_rural_inventory_summary.md
```

---

## 6. Dicionário da base sanitizada

Ver: [`docs/ri_inventory/SANITIZED_DATA_DICTIONARY.md`](../ri_inventory/SANITIZED_DATA_DICTIONARY.md)

---

## 7. Próximos passos

### Fase atual (inventário — sem módulo de produção)
- [ ] Colocar os PDFs do Engegraph em `_local_data/ri_inventory/raw/`
- [ ] Executar `extract_ri_rural_inventory.py` para cada relatório
- [ ] Validar os totais extraídos com a equipe do RI
- [ ] Consultar SIGEF/INCRA para imóveis rurais certificados na circunscrição
- [ ] Concluir Relatório Diagnóstico v2.0 (PROAD nº 202509000672377)

### Fase futura (módulo de produção — somente após decisão da Diretoria)
- [ ] ADR: definir ownership do módulo `registro_imoveis`
- [ ] Modelo de dados: matrículas, transcrições, indicadores
- [ ] Migration Alembic (jamais `create_all` em runtime)
- [ ] API interna para consulta de matrículas (sem exposição de PII)
- [ ] Integração com fluxo de evidências do módulo `compliance`
- [ ] Conexão futura com ONR (IERI-e, SIG-RI, ITN 003/2025) — via adapter isolado

---

## 8. Decisão arquitetural desta fase

**Esta fase não cria:**
- Rotas ou endpoints
- Migrations ou tabelas de banco de produção
- Integração com Engegraph, ONR ou INCRA
- Qualquer funcionalidade operacional

**Esta fase cria apenas:**
- Pipeline local de extração e sanitização
- Base técnica sanitizada para suporte ao Plano de Ação IERI-e/SIG-RI
- Documentação inicial do futuro módulo

Razão: o módulo RI exige decisão arquitetural sobre ownership, schema e integração  
antes de qualquer implementação. A extração local sanitizada é o único insumo necessário  
neste momento para cumprir o prazo regulatório (PROAD — 10/06/2026).

---

## 9. Arquivos relevantes

| Caminho | Descrição |
|---|---|
| `scripts/local_tools/extract_ri_rural_inventory.py` | Script extrator sanitizado |
| `docs/ri_inventory/SANITIZED_DATA_DICTIONARY.md` | Dicionário de dados da base sanitizada |
| `_local_data/ri_inventory/raw/` | PDFs brutos — não versionados |
| `_local_data/ri_inventory/sanitized/` | Base sanitizada — não versionada |
| `_local_data/ri_inventory/reports/` | Relatório agregado — não versionado |
| `_local_data/serventia_docs/Proad Corregedoria/Resposta_IERI-e_2026/` | Documentos do PROAD |

---

*Documento criado em 2026-05-13. Revisar após conclusão do inventário e antes da implementação do módulo de produção.*
