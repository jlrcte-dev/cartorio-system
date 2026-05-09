# Estrutura do Dossiê Técnico — Vistoria CNJ 213/2026

> O dossiê técnico é o conjunto de evidências que comprova, para o vistoriador,
> que a serventia adotou as medidas exigidas pelo Provimento CNJ nº 213/2026
> para Classe 3. Cada documento deve ter data, versão, hash e responsável.

Última atualização: 2026-05-04

---

## Onde guardar o dossiê

```
Pasta na rede local (acesso restrito ao gestor e responsável TI):
_VISTORIA/
│
├── 01_Governanca/
├── 02_Inventario/
├── 03_Rede/
├── 04_Acesso/
├── 05_Backup/
├── 06_Continuidade/
├── 07_Seguranca/
├── 08_Auditoria/
├── 09_Incidentes/
├── 10_Fluxos_Operacionais/
├── 11_Sistema_Proprio/
├── 12_Contratos_Licencas/
└── 00_Indice_Hashes.xlsx   ← Índice mestre com hashes SHA-256 de todos os docs
```

Cópia off-site: exportar o dossiê (sem credenciais) para armazenamento seguro
externo. Proteger com senha e registrar hash do arquivo comprimido.

---

## Seção 01 — Governança

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| PSI — Política de Segurança da Informação v1.0 | PDF assinado | Sim | Assinaturas: gestor + colaboradores |
| Lista de ciência dos colaboradores | PDF assinado | Sim | Nome + data + assinatura |
| Designação do responsável técnico de TI | PDF ou e-mail formal | Sim | |
| Documento de classificação dos dados | PDF assinado | Sim | |
| Termo de responsabilidade por acesso a sistemas críticos | PDF assinado | Sim | Um por colaborador |
| Registros de capacitação em segurança | Atas ou certificados | Sim | Com data e lista de presença |

---

## Seção 02 — Inventário de ativos

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Planilha de inventário de ativos | XLSX ou PDF | Sim | Servidor, estações, switches, APs, nobreaks, impressoras |
| Campos mínimos | — | — | Nome do ativo, tipo, fabricante, modelo, serial, localização, função, SO/firmware, responsável |
| Contratos e licenças (ver Seção 12) | — | — | |

**Modelo de planilha de inventário:**

| Campo | Exemplo |
|-------|---------|
| ID | SERV-001 |
| Tipo | Servidor físico |
| Fabricante/Modelo | [não publicar] |
| Número de série | [não publicar] |
| Localização | Sala técnica |
| Função | Host de virtualização / Engegraph |
| SO | Windows Server 20XX |
| Data de compra | AAAA-MM-DD |
| Garantia até | AAAA-MM-DD |
| Responsável | [nome] |
| Observações | |

---

## Seção 03 — Rede

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Diagrama de rede atual | PNG/PDF | Sim | Com todos os dispositivos e conexões |
| Diagrama de rede alvo (com VLANs) | PNG/PDF | Sim | |
| Configuração de VLANs | Screenshot + export | Sim | |
| Configuração do firewall (regras, sem credenciais) | PDF/Screenshot | Sim | |
| Configuração VPN (sem credenciais) | Screenshot | Sim | |
| Evidência de isolamento do Wi-Fi de clientes | Screenshot | Sim | |

---

## Seção 04 — Controle de acesso

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Matriz de acesso por usuário/grupo e sistema | PDF ou planilha | Sim | Função vs. sistema vs. nível de acesso |
| Auditoria de contas (lista de contas ativas, sem senhas) | PDF | Sim | Confirmar inexistência de contas genéricas |
| Evidência de MFA ativo (screenshot configuração) | PNG | Sim | Sem credenciais |
| Configuração de permissões NTFS (pastas críticas) | Screenshot | Sim | |
| Procedimento de autorização de suporte remoto | PDF | Sim | Quem autoriza; como registrar |
| Log de chamados de suporte (últimos 6 meses) | PDF ou planilha | Sim | Data, motivo, responsável, duração |

---

## Seção 05 — Backup

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Plano de backup aprovado (política, retenção, responsáveis) | PDF assinado | Sim | |
| Configuração do software de backup (screenshots) | PNG | Sim | |
| Log de execução de backup (últimos 30 dias) | PDF ou arquivo de log | Sim | Incluir falhas |
| Evidência de backup off-site em operação | Screenshot | Sim | |
| Ata de teste de restauração nº 1 | PDF assinado | Sim | Data, hora, sistema restaurado, RTO medido |
| Ata de teste de restauração nº 2 | PDF assinado | Recomendado | |
| Hash dos arquivos restaurados no teste | Arquivo .sha256 | Recomendado | |

**Modelo de ata de teste de restauração:**

```
ATA DE TESTE DE RESTAURAÇÃO

Data: AAAA-MM-DD
Hora de início: HH:MM
Responsável técnico: [nome]
Sistema restaurado: [ex.: Banco Engegraph, FileServer]
Versão de backup utilizada: [data do backup]
Ambiente de teste: VM-TestRestore (isolado de produção)

Procedimento executado:
1. [passo 1]
2. [passo 2]
...

Resultado: [ ] Sucesso total  [ ] Sucesso parcial  [ ] Falha
Tempo total de restauração: HH:MM (RTO medido)
Observações: [se parcial/falha — descrever o que não restaurou e motivo]

Hash SHA-256 do backup restaurado: [hash]
Hash SHA-256 dos arquivos validados: [hash]

Assinaturas:
Responsável técnico: __________________ Data: ___________
Gestor: ________________________________ Data: ___________
```

---

## Seção 06 — Continuidade

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| PCN — Plano de Continuidade de Negócios v1.0 | PDF assinado | Sim | |
| PRD — Plano de Recuperação de Desastres v1.0 | PDF assinado | Sim | Com RTO ≤8h e RPO ≤4h explícitos |
| Documentação dos nobreaks (autonomia, baterias) | PDF | Sim | |
| Plano de contingência energética | PDF | Sim | |
| Contrato de suporte Engegraph (SLA de recuperação) | PDF | Sim | Ocultar valores comerciais se necessário |

---

## Seção 07 — Segurança

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Evidência de antivírus/EDR ativo no servidor | Screenshot | Sim | |
| Evidência de antivírus/EDR ativo nas estações | Screenshot ou relatório | Sim | |
| Relatório de atualização de patches (SO + aplicações) | Screenshot ou relatório | Sim | |
| Política de gestão de vulnerabilidades | PDF | Sim | |

---

## Seção 08 — Trilhas de auditoria

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Configuração de auditoria Windows (eventos habilitados) | Screenshot | Sim | |
| Configuração de auditoria de objetos nas pastas críticas | Screenshot | Sim | |
| Política de retenção de logs (≥5 anos) | PDF | Sim | |
| Amostra de log de auditoria (sem dados pessoais) | PDF | Sim | |
| Evidência de proteção de logs contra alteração | Screenshot/config | Sim | |

---

## Seção 09 — Gestão de incidentes

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Plano de resposta a incidentes v1.0 | PDF assinado | Sim | |
| Tabela de classificação de incidentes | PDF | Sim | |
| Registro de incidentes (se houver) | PDF/planilha | Sim | Vazio é aceitável se sistema é novo |

---

## Seção 10 — Fluxos operacionais

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Mapeamento dos fluxos internos críticos | PDF | Sim | |
| POPs aprovados por fluxo | PDF assinado | Sim | |
| Fluxo de digitalização documentado | PDF | Sim | |
| Fluxo de documentos sigilosos/suspeitos | PDF | Sim | |

---

## Seção 11 — Sistema próprio (Cartório System)

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Documentação técnica do sistema | PDF/Markdown | Recomendado | |
| Evidência de backup do banco do sistema (PostgreSQL) | Screenshot/log | Sim | Quando em produção |
| Evidência de trilha de auditoria do sistema | Screenshot | Sim | Quando em produção |
| Política de retenção de logs do sistema | PDF | Sim | |

---

## Seção 12 — Contratos e licenças

| Documento | Formato | Obrigatório | Notas |
|-----------|---------|-------------|-------|
| Contrato Engegraph (sem valores se necessário) | PDF | Sim | Verificar SLA |
| Licença Windows Server | PDF | Sim | |
| Licença SQL Server (se aplicável) | PDF | Sim | |
| Contrato de internet | PDF | Sim | |
| Contrato de backup off-site / nuvem | PDF | Sim | Quando escolhido |
| Contratos de antivírus/EDR | PDF | Sim | |

---

## Índice mestre de hashes

O arquivo `00_Indice_Hashes.xlsx` deve conter, para cada documento do dossiê:

| Coluna | Conteúdo |
|--------|----------|
| Seção | Número e nome da seção |
| Arquivo | Nome do arquivo |
| Versão | Versão do documento |
| Data | Data de geração |
| Hash SHA-256 | Hash do arquivo |
| Tamanho (bytes) | Tamanho do arquivo |
| Responsável | Quem gerou |
| Observações | |

**Como gerar o hash SHA-256 no Windows:**
```powershell
Get-FileHash -Algorithm SHA256 -Path ".\documento.pdf"
```

---

## Notas importantes

1. Nenhum documento do dossiê deve conter credenciais, senhas ou chaves de acesso.
2. Dados pessoais de clientes não devem aparecer em nenhum documento do dossiê.
3. Valores comerciais de contratos podem ser omitidos; o que importa é a existência e vigência.
4. Prints de configuração devem ser datados (incluir data/hora na captura).
5. Atas devem ser assinadas pelo gestor e pelo responsável técnico.
6. O dossiê físico (pasta na rede) deve ter acesso restrito e log de acesso habilitado.
