# Política de Operação Read-Only — Módulo de Auditoria

> Este documento define o contrato operacional do Módulo de Auditoria do
> Cartório System. Toda funcionalidade de coleta de dados deve aderir a esta
> política antes de ser implementada ou executada.

Última atualização: 2026-05-04
Versão: 1.0

---

## 1. Declaração de princípio

O Módulo de Auditoria opera em modo **somente leitura** em sua fase inicial.

O sistema **lê**, **analisa** e **reporta**.
O sistema **nunca** escreve, modifica, move ou exclui nada no ambiente analisado.

Essa restrição não é apenas técnica — é uma decisão de governança. Qualquer
intervenção no servidor ou nos arquivos da serventia deve ser:

1. Aprovada explicitamente pelo gestor
2. Executada manualmente por um responsável identificado
3. Documentada com data, hora, motivo e resultado

O módulo de auditoria apoia essa decisão humana com informação — não a substitui.

---

## 2. O que o sistema PODE fazer

### Leitura de sistema de arquivos

- ✅ Listar arquivos e pastas a partir de um caminho raiz configurável
- ✅ Coletar metadados: nome, tamanho, extensão, datas de criação e modificação
- ✅ Calcular profundidade de diretório
- ✅ Agregar estatísticas: total de arquivos, total de pastas, tamanho total
- ✅ Verificar se um caminho existe e é acessível
- ✅ Registrar erros de permissão (sem tentar contorná-los)

### Coleta de informações do sistema operacional (fases posteriores)

- ✅ Listar usuários locais e seus metadados (exceto senhas)
- ✅ Listar grupos locais e membros
- ✅ Verificar status do Windows Defender (somente leitura)
- ✅ Verificar portas abertas (`netstat -an`)
- ✅ Verificar regras de firewall (somente leitura)
- ✅ Verificar interfaces de rede e endereços IP
- ✅ Verificar espaço em disco (`shutil.disk_usage`)

### Leitura de logs (somente metadados)

- ✅ Ler arquivos de log de texto do Cobian Gravity (somente metadados de execução)
- ✅ Verificar existência e data de arquivos de backup esperados
- ✅ Registrar presença/ausência de dumps esperados

### Geração de artefatos

- ✅ Escrever arquivos JSON, CSV e Markdown no diretório de saída designado
  (`exports/audit/`)
- ✅ Calcular hashes SHA-256 dos artefatos gerados
- ✅ Registrar logs de execução internos (sem dados sensíveis)

---

## 3. O que o sistema NÃO PODE fazer

### Proibições absolutas — nunca implementar

| Operação proibida | Motivo |
|-------------------|--------|
| ❌ Abrir, ler ou parsear o **conteúdo** de arquivos de documentos | Protege sigilo profissional e dados pessoais |
| ❌ Modificar, renomear, mover ou excluir qualquer arquivo | Preserva integridade do ambiente |
| ❌ Gravar qualquer dado no servidor analisado | Previne alteração não autorizada |
| ❌ Alterar permissões de arquivos ou pastas | Operação administrativa, não de auditoria |
| ❌ Criar, modificar ou excluir usuários ou grupos | Operação administrativa |
| ❌ Alterar regras de firewall | Operação administrativa |
| ❌ Iniciar ou encerrar serviços | Operação administrativa |
| ❌ Modificar configurações do Windows | Operação administrativa |
| ❌ Acessar conteúdo de e-mails ou mensagens | Privacidade e sigilo |
| ❌ Coletar ou registrar senhas, hashes de senhas ou tokens | Segurança de credenciais |
| ❌ Realizar port scan ativo de outros hosts na rede | Requer autorização explícita |
| ❌ Capturar tráfego de rede (packet sniffing) | Requer autorização explícita |
| ❌ Executar queries diretas no banco do Engegraph | Dependência e risco de corrupção |
| ❌ Acessar dados de clientes (nome, CPF, documentos) | LGPD e sigilo notarial/registral |

### Proibições de execução automática

| Operação | Condição para execução |
|----------|----------------------|
| Qualquer varredura do servidor | Autorização explícita do gestor por escrito |
| Execução em ambiente de produção | Janela de execução definida (fora do expediente) |
| Execução agendada automática | Apenas após autenticação multiusuário implementada |
| Exportação de resultados para terceiros | Nunca sem autorização e remoção de dados sensíveis |

---

## 4. Como evitar risco aos dados

### Ao desenvolver

1. **Nunca usar `open(file)` para ler conteúdo** — apenas `os.stat()` e `os.path.*`
2. **Tratar erros de permissão com `try/except PermissionError`** — registrar e continuar
3. **Nunca usar `os.remove()`, `shutil.move()`, `os.rename()` ou equivalentes**
4. **Sempre usar modo somente leitura** ao abrir qualquer arquivo de log (`open(f, "r")`)
5. **Limitar recursão** com `max_depth` para evitar loops em symlinks
6. **Detectar symlinks** e não seguir links que saem do caminho raiz
7. **Sanitizar caminhos de saída** — nunca escrever fora de `exports/audit/`
8. **Validar o caminho raiz** antes de iniciar — o caminho deve existir e ser um diretório

### Ao executar

1. Executar sempre em janela sem expediente ativo (pós-17h, pré-8h)
2. Notificar o gestor antes de iniciar a varredura
3. Manter log de todas as execuções com responsável identificado
4. Não executar varredura em produção sem ter testado com diretório de teste menor

### Ao reportar

1. **Nunca incluir caminhos absolutos do servidor** nos relatórios exportáveis
   — usar sempre caminhos relativos à raiz de varredura
2. **Nunca incluir nomes de clientes** em qualquer relatório
3. **Mascarar nomes de arquivos sensíveis** em relatórios compartilhados
   (ex.: mostrar apenas `[ARQUIVO_SIGILOSO.pdf]` se o nome indicar sigilo)
4. Incluir aviso de confidencialidade em todos os artefatos exportados

---

## 5. Como registrar logs sem dados sensíveis

### O que registrar nos logs internos da aplicação

```python
# CORRETO
logger.info("Scan iniciado: run_id=%s, root=[REDACTED], total_files=%d", run_id, count)
logger.warning("Acesso negado: path=[REDACTED_PATH], error=%s", str(e))
logger.error("Erro inesperado: run_id=%s, phase=%s", run_id, phase)

# INCORRETO — nunca fazer
logger.info("Scanning: %s", full_absolute_path)
logger.debug("File content preview: %s", file_content[:100])
logger.info("User: %s, CPF: %s", name, cpf)
```

### O que registrar nos artefatos de saída (inventory.json, report.md)

| Campo | Incluir | Não incluir |
|-------|---------|-------------|
| Caminho relativo ao raiz | ✅ | ❌ Caminho absoluto do servidor |
| Nome do arquivo | ✅ | ❌ Conteúdo do arquivo |
| Tamanho em bytes | ✅ | ❌ Hash do conteúdo do arquivo |
| Data de modificação | ✅ | ❌ Metadados de autoria do documento |
| Extensão | ✅ | ❌ Conteúdo mesmo que parcial |
| Erro de acesso (genérico) | ✅ | ❌ Stack trace com caminhos absolutos |

### manifest.json — campos de rastreabilidade

O manifest registra a execução sem dados sensíveis:

```json
{
  "run_id": "uuid",
  "executed_at": "ISO 8601",
  "executed_by": "gestor",
  "root_path_hash": "sha256 do caminho absoluto",
  "parameters_summary": "depth=8, excludes=2",
  "totals": { "files": 12543, "dirs": 876, "bytes": 45678901234 }
}
```

O `root_path_hash` permite confirmar que foi varrido o mesmo caminho em execuções
diferentes sem expor o caminho absoluto nos artefatos.

---

## 6. Como validar execução em ambiente seguro

### Checklist pré-execução (rodar antes de qualquer varredura)

```
[ ] O caminho raiz configurado é o caminho correto para esta execução?
[ ] O diretório de saída (exports/audit/) está no sistema do Cartório System,
    não no servidor analisado?
[ ] A execução foi aprovada pelo gestor?
[ ] A janela de execução é fora do expediente ou o servidor está em baixo uso?
[ ] Os testes unitários passam (pytest tests/)?
[ ] Nenhum arquivo de produção foi usado nos testes?
```

### Testes unitários obrigatórios (Sprint 1)

O scanner deve ter testes que verificam:

1. **Nenhuma escrita acontece:** usar `unittest.mock.patch("builtins.open", ...)`
   para confirmar que `open()` não é chamado com modo de escrita
2. **Diretório temporário:** `tempfile.mkdtemp()` — nunca apontar para caminho real
3. **Erros de permissão:** criar arquivo com permissão negada no tmp e verificar
   que o scanner registra o erro e continua (não lança exceção fatal)
4. **Exclusão de caminhos:** verificar que caminhos excluídos não aparecem no inventário
5. **Profundidade máxima:** criar estrutura de 10 níveis e confirmar que `max_depth=3`
   para no nível 3
6. **Symlinks fora do raiz:** criar symlink apontando para fora do diretório e
   confirmar que não é seguido

### Validação pós-execução

```
[ ] O diretório de saída esperado foi criado em exports/audit/<run-name>/?
[ ] O manifest.json contém hash SHA-256 do inventory.json?
[ ] O hash do inventory.json confere com o registrado no manifest?
[ ] Nenhum arquivo no servidor analisado teve sua data de modificação alterada?
[ ] O log da aplicação não contém caminhos absolutos do servidor?
[ ] O relatório report.md não contém dados pessoais de clientes?
```

---

## 7. Versionamento desta política

Esta política deve ser revisada:

- Antes de implementar qualquer nova funcionalidade de coleta de dados
- Antes de qualquer sprint que acesse o servidor de produção
- Anualmente como parte da revisão da PSI

Mudanças que ampliam o escopo de coleta (ex.: ler conteúdo de arquivos) exigem:

1. Aprovação do gestor por escrito
2. Atualização desta política com nova versão
3. Novo ciclo de testes antes de execução em produção
