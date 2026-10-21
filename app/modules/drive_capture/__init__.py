"""Coletor local, somente leitura, de fontes autorizadas do Google Drive do cartório.

Captura bytes (exportação XLSX/DOCX ou download de arquivo armazenado) com procedência
e publicação atômica, sem interpretar conteúdo. Contrato em docs/modules/drive_capture.md
e decisão de acesso na ADR-011.

Importar este pacote não autentica, não abre rede e não inicia coleta: a dependência
do Google (extra ``[drive]``) só é carregada quando a CLI monta o transporte real.
"""
