# ADR-012 — Exportação financeira para o Atlas com contrato próprio e fechado

- **Status:** Proposto — implementado e testado localmente com dados sintéticos; aceite
  depende de revisão humana. *Nota factual (2026-10-27):* o contrato 1.0 passou a ter
  consumidor no Atlas e uso produtivo desde 26/10/2026, por operação manual realizada fora
  desta ADR. A ativação não a aceita nem altera seu status.
- **Data:** 2026-10-22
- **Sprint:** `CARTORIO-ATLAS-FINANCE-EXPORT-1`
- **Módulo:** `app/modules/finance_snapshot/atlas_export.py`
- **Guia e contrato:** [`docs/modules/finance_snapshot.md`](../modules/finance_snapshot.md)
  § Exportação para o Atlas

---

## Contexto

O leitor offline do Financeiro publica `finance_snapshot/latest.json` no formato local
`cartorio_system.finance_snapshot.local` 0.1. Esse formato é interno, experimental e
livre para mudar. O próximo passo é deixar o Atlas consultar o demonstrativo diário e os
sinais de conferência, preservando procedência, temporalidade e limitações.

O retrato de serviços já tem um exportador (`cartorio_system.atlas.services_snapshot` 1.0)
com o padrão a seguir:

- arquivo único;
- montagem campo a campo;
- esquema fechado;
- troca atômica.

Mas o financeiro **não** tem registro de tentativas: não existe o `last_attempt.json` dos
serviços.

A configuração do projeto (§ 6.1, § 12) exige ADR quando uma integração com o Atlas ou um
contrato de export é definido.

## Decisão

1. **Contrato próprio, versionado:** `cartorio_system.atlas.finance_snapshot` 1.0, em
   `<data_dir>/finance_snapshot/atlas_snapshot.json`. O formato local e o contrato de
   serviços não mudam, e os dois contratos não compartilham arquivo nem estado.
2. **Entrada única:** um `latest.json` financeiro, lido uma vez. Ele precisa casar com a
   fonte configurada e com o run e o período **passados explicitamente** (os três
   argumentos são obrigatórios). Não lê XLSX, Markdown nem rede e não executa `analyze` ou
   coleta.
3. **Procedência declarada:** o vínculo aos bytes do XLSX foi feito pelo `analyze`. O
   exportador valida o relatório e repassa os metadados declarados. Ele não reconfere a
   captura, não assina e não cria digest semântico.
4. **Seleção explícita:** listas de campos e enumerações são declaradas no exportador,
   não importadas do formato local. Mudança interna futura recusa a exportação até uma
   decisão deliberada; um teste aponta a divergência.
5. **Recorte:** envelope, origem, período, tempos, limitações, cobertura, totais de
   checagens e `dias[]`. `dias[]` tem um item por aba, ignoradas e repetidas incluídas,
   com os campos agregados de cada bloco e as checagens diárias. Fica fora tudo o que
   identifica pessoa, lançamento, aba ou arquivo do Drive, e também versão, tamanho e
   SHA-256 do XLSX.
6. **Sem bloco de atualização:** o contrato não informa tentativas posteriores nem
   confirma atualização, porque não há registro para isso.
7. **Validação antes da publicação:**
   - esquema fechado em todos os níveis;
   - tempos e datas efetivos;
   - coerência das contagens e das relações valor/ausência com `dias[]`.

   Divergência recusa, nunca conserta.
8. **Publicação:** troca atômica privada do coletor (`atomic_write_bytes`). Se falhar, a
   CLI informa o estado real do arquivo, conferido em disco, inclusive o de falha depois
   do `os.replace`.
9. **Concorrência:** `RunLock` no diretório financeiro exclui só outra exportação. O
   `analyze` não é travado e não foi alterado. A consistência vem da leitura única de um
   arquivo promovido atomicamente.

## Consequências positivas

- O Atlas poderá consumir o financeiro sem depender do formato interno, e com as lacunas
  explícitas (`null` com motivo, estados e limitações).
- Recusas com código controlado e retornos fixos (0/2/3/4), sem conteúdo em mensagens.
- Exemplo sintético gerado pelo produtor real, que servirá de fixture ao consumidor.

## Consequências negativas

- O arquivo é **privado** (traz valores agregados por dia), e o transporte para a VPS
  ainda não está definido. Ele exigirá decisão própria, com o mesmo cuidado do canal de
  serviços.
  *Nota de 2026-10-27:* o transporte foi realizado manualmente em 26/10/2026, por canal
  próprio e fora do escopo desta ADR.
- Sem registro de tentativas, o consumidor não distingue "nada mudou" de "a atualização
  falhou": só vê os tempos da captura e da exportação.
- Trava órfã de processo interrompido exige remoção manual.
- A coerência exige que as regras publicadas pelo leitor continuem valendo. Mudar regra
  no leitor sem atualizar o contrato faz a exportação ser recusada.

## Alternativas consideradas

| Alternativa | Motivo da recusa |
|---|---|
| Expor `latest.json` (formato local) ao Atlas | Formato interno e experimental; carrega metadados técnicos que o Atlas não precisa |
| Ampliar o contrato de serviços com o financeiro | Mistura fontes, estados de tentativa e cadências distintas num arquivo só |
| Copiar subobjetos do relatório genericamente | Mudança interna atravessaria o contrato sem decisão |
| Travar `analyze` com o mesmo `RunLock` | Exigiria alterar o pipeline aprovado; a leitura única já fixa a versão exportada |

## Referências

- [`docs/modules/finance_snapshot.md`](../modules/finance_snapshot.md)
- [`docs/modules/services_snapshot.md`](../modules/services_snapshot.md) § Exportação para o Atlas
- [ADR-011](ADR-011-drive-readonly-capture.md) — captura local somente leitura (não alterada)
- [`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](../../CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md) § 6.1, § 12
