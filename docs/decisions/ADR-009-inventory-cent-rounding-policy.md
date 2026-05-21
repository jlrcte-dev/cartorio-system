# ADR-009 — Política de centavos em inventários extrajudiciais

## Status

Proposto — vigora para o MVP do módulo `notas/inventarios`

Data: 2026-05-20
Autores: João + Claude Code
Sprint de origem: NOTAS-INVENTARIO-2

---

## Contexto

O módulo `app/modules/notas/inventarios/` recebe um inventário descrito
estruturalmente (patrimônio total, percentual de meação, lista de herdeiros e
distribuição por bem) e calcula meação, monte partilhável e quinhões. Toda a
aritmética é feita em `Decimal` com arredondamento `ROUND_HALF_EVEN` para 2
casas (ver [`calculator.py`](../../app/modules/notas/inventarios/application/calculator.py)).

Apesar disso, a combinação de percentuais com fracionamento exato impossível
(`33,33% × 3 = 99,99%`; `33,34% × 1 = 33,34%`) faz com que a soma do que é
efetivamente distribuído possa diferir do patrimônio total em alguns centavos.
A Sprint NOTAS-INVENTARIO-0/1 introduziu o campo
`ResumoInventario.divergencia_centavos` para registrar esse resíduo, mas deixou
explicitamente em aberto a decisão sobre como tratá-lo
(ver [docs/modules/notas_inventarios.md § 6](../modules/notas_inventarios.md#6-pol%C3%ADtica-de-centavos--decis%C3%A3o-tempor%C3%A1ria)).

A próxima sprint (NOTAS-INVENTARIO-2) começa a renderizar a minuta-base em
Markdown a partir do template
`inventario_extrajudicial_padrao.md.j2`. Antes de a minuta passar a ser usada
como base para escrituras reais, é necessário fixar a regra de como
divergências de centavos aparecem no documento e quais cenários bloqueiam a
geração.

A decisão tem impacto regulatório (CNJ 213/2026, Resolução 35 CNJ) e
financeiro (a escritura instrui ITCMD e DOI). Erros de centavos silenciosamente
absorvidos pelo sistema poderiam produzir descasamento entre o valor declarado
na escritura e o valor declarado na guia de imposto, e induziriam o tabelião
a assinar um documento cujos números não fecham.

---

## Decisão

**No MVP do módulo de inventários, o sistema NÃO corrige centavos
silenciosamente. Divergências geram alerta explícito e — fora de tolerância —
bloqueiam a validação.**

Em concreto:

1. **Tolerância única de `±0,01` por linha de validação.**
   Mantém-se a tolerância de `Decimal("0.01")` já existente em
   `DECIMAL_TOLERANCIA` para as três verificações de soma:
   - soma dos percentuais de herança dos herdeiros vs. 100,00;
   - soma dos valores dos bens vs. `patrimonio_total` declarado;
   - soma dos percentuais da distribuição de cada bem vs. 100,00.

2. **Divergência dentro da tolerância não bloqueia, mas gera alerta.**
   Quando `ResumoInventario.divergencia_centavos > 0` e cada validação acima
   ainda passa (cada uma com `±0,01`):
   - o JSON de validação inclui o objeto `alerta_centavos` no nível raiz;
   - o resumo técnico Markdown traz uma seção `⚠ Alerta de centavos`;
   - a CLI imprime aviso em `stderr` sem alterar exit code (`EXIT_OK`);
   - **a minuta-base, quando gerada com `--render-minuta`, traz um aviso
     técnico próprio sinalizando a divergência e instruindo revisão manual
     do tabelião** (essa é a única forma de o resíduo aparecer no texto
     cartorário; o sistema nunca atribui o centavo silenciosamente a um
     beneficiário).

3. **Divergência fora da tolerância bloqueia a validação.**
   Qualquer uma das três somas acima fora de `±0,01` aciona
   `ValidationResult.errors`, o CLI sai com `EXIT_VALIDATION_FAILED = 1`, e a
   minuta-base **não** é gerada — mesmo quando `--render-minuta` é passado.
   Esse comportamento já está implementado pelo `InventarioValidator` e fica
   formalizado aqui como regra desta fase.

4. **Ajuste automático de "último beneficiário" fica proibido nesta fase.**
   Nenhuma rotina pode tomar o centavo residual e atribuí-lo a um beneficiário
   pré-definido (ex.: último herdeiro listado) sem revisão humana. Essa
   alternativa (a "(b) Ajuste controlado" listada em
   [docs/modules/notas_inventarios.md § 6](../modules/notas_inventarios.md#6-pol%C3%ADtica-de-centavos--decis%C3%A3o-tempor%C3%A1ria))
   é explicitamente **proibida** enquanto este ADR estiver vigente.

5. **Distribuição por valor absoluto fica para sprint futura.**
   A alternativa "(c) Distribuição por valor" — receber `R$` por
   bem/beneficiário em vez de percentual — pode ser reavaliada em sprint
   futura. Ela exigirá novo ADR que substitua este, alterando o contrato de
   entrada do `loader` e a semântica do `validator`.

---

## Alternativas consideradas

### Alternativa A — Ajuste automático de "último beneficiário"

Atribuir o centavo residual ao último herdeiro listado (ou ao meeiro) e
registrar o ajuste no JSON de validação.

**Por que descartada (nesta fase):**

- A escritura instrui ITCMD e DOI; um centavo "doado" silenciosamente pelo
  sistema cria descasamento entre `total_por_beneficiario` calculado e o que
  foi efetivamente declarado no demonstrativo SPL.
- A regra "último herdeiro" é arbitrária e não tem amparo no texto da minuta
  nem na Resolução 35 CNJ. Qualquer escolha do sistema seria invisível ao
  tabelião sem leitura cuidadosa do JSON.
- Há risco regulatório: o sistema declararia automaticamente que um
  beneficiário recebeu valor diferente do que os percentuais da escritura
  expressam — o que, em caso de auditoria, sustentaria a interpretação de que
  o cálculo foi feito "pelo software" e não revisado pelo notário.
- Reabilitável em sprint futura com ADR próprio se ficar comprovado, em
  produção, que o volume de divergências torna o alerta operacionalmente
  custoso.

### Alternativa B — Tolerância proporcional ao patrimônio

Substituir `±0,01` por algo como `±0,01% × patrimonio_total`.

**Por que descartada:**

- Esconde erros de digitação proporcionalmente: em um inventário de
  R$ 50 milhões, uma divergência de R$ 5.000 passaria silenciosamente.
- A tolerância existe para absorver arredondamento de percentual, não
  diferença de valor. Tolerância proporcional muda a natureza da regra.
- Pode ser reconsiderada se aparecerem casos legítimos onde percentuais
  combinados produzem resíduo > R$ 0,01 — algo improvável dentro do limite
  de 2 casas decimais.

### Alternativa C — Distribuição por valor absoluto (sem percentual)

Receber `R$` por bem/beneficiário em vez de percentual.

**Por que descartada (nesta fase):**

- Quebra o contrato de entrada YAML atual (`percentual: 25` em
  `bens[].distribuicao[]`), que já foi adotado pelos exemplos versionados e
  pelos testes.
- Move o problema: o cliente passa a precisar calcular os valores fora do
  sistema, o que recria a divergência em outro lugar.
- Pode coexistir como modo alternativo em sprint futura com ADR próprio.

### Alternativa D — Bloquear sempre que `divergencia_centavos > 0`

Tratar qualquer divergência (mesmo dentro de `±0,01`) como erro de validação.

**Por que descartada:**

- Inviabiliza casos legítimos de fracionamento equânime entre 3 herdeiros
  (33,33% / 33,33% / 33,34%), que é um dos exemplos versionados do módulo.
- A tolerância `±0,01` já existe explicitamente no validator e nos testes
  como decisão técnica anterior — esta ADR a confirma, não a substitui.

---

## Consequências

### Positivas

1. **Não há decisão financeira invisível.** O sistema nunca atribui um
   centavo a um beneficiário sem que o tabelião veja o alerta em três
   superfícies (JSON, resumo, minuta).
2. **Compatível com o princípio do projeto** de "nunca declarar conformidade
   automaticamente". Centavo residual é sinalizado, não absorvido.
3. **Auditável em caso de revisão CNJ.** O JSON de validação carimba a
   divergência com sua mensagem padrão; o resumo Markdown e a minuta-base
   carregam o mesmo aviso. Há rastro consistente em três artefatos.
4. **Reversível.** Esta ADR é explicitamente uma decisão de fase MVP.
   Quando houver dados de uso real do módulo, alternativas (A) e (C) podem
   ser reavaliadas via novo ADR.

### Negativas

1. **Fricção operacional.** O tabelião precisa decidir manualmente como
   tratar o resíduo — tipicamente reescrevendo a partilha de um bem para
   absorver o centavo. Pode ser aceitável para um cartório com baixo volume,
   mas pode pesar conforme o volume cresce.
2. **Sem caminho de "auto-resolução".** Não há flag `--ajustar-centavos`
   nesta fase, mesmo para casos onde o usuário queira aceitar
   conscientemente a regra de "último beneficiário". Quem quiser esse
   comportamento precisa esperar nova sprint + novo ADR.

---

## Impacto no módulo `notas/inventarios`

### Calculator (`application/calculator.py`)

Já implementa a regra: `divergencia_centavos` é sempre calculado e
retornado em `ResumoInventario`. **Nenhuma mudança nesta sprint.**

### Validator (`application/validator.py`)

Já implementa as três checagens de tolerância. **Nenhuma mudança nesta
sprint.**

### Renderer

- `render_resumo_markdown` já emite a seção `⚠ Alerta de centavos` quando
  aplicável. **Mantido.**
- O novo `render_minuta_markdown` (Sprint NOTAS-INVENTARIO-2) deve
  igualmente trazer um aviso técnico no corpo da minuta sempre que
  `divergencia_centavos > 0`. O aviso deve ser visualmente destacado
  (blockquote em Markdown) e deve instruir o tabelião a revisar a partilha
  bem a bem antes de assinar.

### CLI (`interfaces/cli.py`)

- Comportamento de exit code mantido: `EXIT_OK` quando há apenas alerta;
  `EXIT_VALIDATION_FAILED` quando há erro de validação.
- A flag `--render-minuta`, introduzida na Sprint NOTAS-INVENTARIO-2, **não
  gera** `inventario_minuta.md` quando a validação falha (exit 1). Geração
  da minuta exige `EXIT_OK`, ainda que com alerta.

### Documentação

- `docs/modules/notas_inventarios.md` § 6 passa a referenciar esta ADR como
  a decisão vigente. A redação "decisão temporária" original é preservada
  apenas como histórico — a nova fonte de verdade é este documento.

---

## Critérios para revisão futura

Esta ADR deve ser reavaliada (substituída por nova ADR) quando **qualquer
um** dos critérios abaixo for atendido:

1. **Volume operacional indica fricção excessiva.** Se o cartório passar a
   gerar mais de 5 inventários por mês com alerta de centavos exigindo
   reescrita manual, vale reabrir a discussão sobre Alternativa A.
2. **Mudança no contrato de entrada YAML.** Se a fonte (Engegraph,
   formulário web, API) passar a fornecer distribuição por valor absoluto,
   Alternativa C precisará ser endereçada.
3. **Provimento CNJ ou normativa estadual** trouxer regra explícita sobre
   tratamento de centavo residual em escritura pública de inventário.
4. **Diagnóstico de auditoria interna** detectar que o alerta atual está
   sendo ignorado pelo tabelião na revisão da minuta — sinal de que a
   ergonomia precisa mudar.
5. Decorridos 12 meses desde a aprovação desta ADR, mesmo sem outro
   gatilho — revisão programática.

---

## Referências

- [`docs/modules/notas_inventarios.md`](../modules/notas_inventarios.md) — § 6
  (decisão temporária original)
- [`app/modules/notas/inventarios/application/calculator.py`](../../app/modules/notas/inventarios/application/calculator.py)
  — `DECIMAL_TOLERANCIA`, `ResumoInventario.divergencia_centavos`
- [`app/modules/notas/inventarios/application/validator.py`](../../app/modules/notas/inventarios/application/validator.py)
  — três checagens com `abs(soma - alvo) > DECIMAL_TOLERANCIA`
- Resolução 35 CNJ — disciplina inventários extrajudiciais
- Provimento 46/2020 CGJ-GO; Decreto 93.240/86, art. 1º, § 3º
- ADR-008 — toda saída de IA é rascunho sujeito à revisão humana (o mesmo
  princípio "sistema não decide silenciosamente" se aplica aqui ao cálculo
  determinístico)
