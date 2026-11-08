# Rotina local de backup do PostgreSQL — homologação

Contrato da cópia diária do banco de homologação, criada em 07/11/2026 junto da troca para
PostgreSQL ([ADR-013](../decisions/ADR-013-troca-banco-ativo-sqlite-postgresql.md)). Os
valores abaixo são **parâmetros de laboratório**. Caminhos, usuários e destinos reais ficam
no dossiê privado do operador; aqui aparecem como placeholders entre `< >`.

> **Estado do versionamento.** O script e as duas unidades systemd **rodam na VM, mas não
> estão neste repositório.** Este documento fixa o contrato que eles cumprem, para que a
> versão versionada seja conferida contra ele. Trazer os arquivos exige lê-los no host,
> e essa é uma operação da janela de homologação.

## Parâmetros

| Parâmetro | Valor de laboratório | Origem |
| --- | --- | --- |
| Frequência | diária, `OnCalendar=*-*-* <horario> UTC` (o horário real fica no dossiê privado) | decisão de 07/11/2026, ajustável |
| Atraso aleatório | `RandomizedDelaySec=300` | idem |
| Disparo perdido | `Persistent=true`: roda no próximo boot se o horário passou com a VM parada | idem |
| Retenção | as **14** cópias mais recentes | idem |
| Unidades | `<servico-backup>.service` (`Type=oneshot`) + `<servico-backup>.timer`, com `Wants=`/`After=` do serviço do PostgreSQL | — |
| Papel do banco | `<papel-backup>`: `SELECT` nas tabelas **e** `USAGE, SELECT` nas sequences, sem escrita | achado da ADR-013 |
| Destino | `<dir-backups>/recorrentes/`, com área temporária `<dir-backups>/recorrentes/.tmp/` | — |
| Formato | `pg_dump --format=custom` | — |

## Garantias

1. **Nada é publicado pela metade.** O dump é gravado na área temporária e só vira cópia
   publicada (rename atômico) depois que o `pg_dump` **e** o `pg_restore --list` passam.
2. **Cada cópia publicada leva um manifesto.** É um `.json` ao lado do dump, com o
   SHA-256 do arquivo.
3. **A retenção só atua em `recorrentes/`.** Cópias de corte e pós-corte vivem no
   diretório pai e nunca são tocadas pela rotina.
4. **A falha é visível e não destrói nada.** Erro de credencial ou de conexão termina o
   serviço com código diferente de zero ("Failed with result 'exit-code'" no journal),
   e a última cópia válida fica intacta.

## O que foi observado (homologação, 07–08/11/2026)

| Evento | Resultado |
| --- | --- |
| Disparo manual de validação | publicado e **restaurado** num banco temporário: revisão Alembic, registros de referência e nova escrita sem colisão |
| Falha induzida (credencial trocada e depois restaurada) | serviço falhou visivelmente; cópia anterior intacta |
| 1º disparo automático (07/11, no horário agendado) | sucesso no journal |
| 2º disparo automático (08/11, no horário agendado) | sucesso no journal (`Result=success`, `ExecMainStatus=0`) |

Os dois disparos automáticos consecutivos foram **lidos no journal**. O diretório de backups
não é legível pelo usuário de observação, então nenhum digest foi recalculado sobre os
arquivos. A conferência de conteúdo continua sendo o item 1 do
[checklist da janela](ops_window_checklist.md).

## Fora desta rotina

- **Cópia fora do host.** Todas as cópias ficam no disco da própria VM. O destino externo é
  pendência da ADR-013 e tema da OPS-2.
- **Alerta.** Uma falha só aparece no journal; ninguém é avisado.
- **Teste periódico de restauração.** A restauração foi provada uma vez, no disparo
  manual. A verificação recorrente é escopo do verificador da OPS-1
  ([ADR-014](../decisions/ADR-014-verificacao-operacional-e-prova-de-recuperacao.md)).
