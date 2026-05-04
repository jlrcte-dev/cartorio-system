# Política de Separação de Dados Locais

## Regra fundamental

`docs/` contém **apenas documentação técnica do projeto** — arquitetura, decisões, roadmaps, módulos, políticas de desenvolvimento. Esses arquivos são versionados no Git.

`_local_data/` contém **documentos reais da serventia** e **nunca deve ser commitado**. A pasta está listada no `.gitignore`.

---

## Estrutura de pastas

```
repositório/
├── docs/                      ← documentação técnica (versionada)
│   ├── architecture/
│   ├── modules/
│   ├── security/
│   └── *.md (docs do projeto)
│
└── _local_data/               ← dados da serventia (NUNCA versionar)
    └── serventia_docs/
        ├── Atos Normativos e Administrativos/
        ├── Calculo de Documentos/
        ├── Estrutura tecnica/
        ├── Gerenciamento_financeiro/
        ├── LGPD/
        ├── operations/
        ├── Planos de ação e adequação/
        ├── Politicas, manuais e procedimentos/
        ├── Procedimentos Operacionais Padrão/
        └── SGCN/
```

---

## O que NÃO pode entrar no Git

| Categoria | Exemplos |
|---|---|
| Dados pessoais / LGPD | fichas, cadastros, documentos com CPF/RG |
| Dados financeiros | planilhas, balanços, recibos, comprovantes |
| Credenciais | senhas, tokens, chaves de API |
| Documentos do acervo | PDFs de escrituras, certidões, atos |
| Atos normativos baixados | portarias, provimentos em PDF |
| POPs reais | procedimentos operacionais padrão da serventia |
| Relatórios gerados | outputs de scanner, diagnósticos, inventários |
| Artefatos de auditoria | `file_inventory.json`, `scan_manifest.json` etc. |

---

## Onde armazenar relatórios de auditoria

O módulo de auditoria pode analisar dados em `_local_data/` localmente, mas os outputs **nunca devem ficar dentro da pasta raiz do repositório**.

Caminhos recomendados para outputs:

```
C:\Audit_Reports\AAAA-MM-DD\   ← relatórios de auditoria periódicos
C:\Audit_Reports\scan_AAAA-MM-DD\
_local_data\audit_outputs\     ← alternativa (coberta pelo .gitignore)
```

Nunca salvar outputs dentro de `app/`, `docs/`, `scripts/` ou na raiz do projeto.

---

## Uso pelo módulo de auditoria

Ao configurar varreduras locais para teste:

```python
# Correto — aponta para dados locais fora do repo
scan_path = r"C:\Users\<user>\_local_data\serventia_docs"
output_path = r"C:\Audit_Reports\2026-05-04"

# Errado — nunca usar o root do projeto como alvo de scan
# scan_path = r"C:\Users\<user>\Documents\cartorio_system"
```

---

## Verificação rápida antes de commitar

```bash
git status --short
```

Se aparecer qualquer item de `_local_data/` ou artefatos `.json`/`.csv` de scanner, **não commitar**. Verificar o `.gitignore` e usar `git rm --cached` se necessário.
