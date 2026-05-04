"""
Gera o Relatório Técnico de Situação — Serventia Cartório Costa Teixeira
como arquivo PDF em docs/Relatorio_Tecnico_Situacao.pdf
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import date

OUTPUT_PATH = "docs/Relatorio_Tecnico_Situacao.pdf"

# ─── paleta ──────────────────────────────────────────────────────────────────
COR_TITULO = (15, 55, 90)  # azul escuro
COR_SECAO = (25, 80, 130)  # azul médio
COR_SUBSECAO = (50, 110, 160)  # azul claro
COR_CRITICO_BG = (255, 235, 235)  # vermelho claro (fundo)
COR_CRITICO_FG = (180, 30, 30)  # vermelho escuro (texto)
COR_ALTO_BG = (255, 245, 220)  # laranja claro
COR_ALTO_FG = (160, 90, 0)  # laranja escuro
COR_MEDIO_BG = (255, 253, 210)  # amarelo claro
COR_MEDIO_FG = (130, 110, 0)  # amarelo escuro
COR_OK_BG = (220, 240, 220)  # verde claro
COR_OK_FG = (30, 100, 30)  # verde escuro
COR_TABELA_HDR = (40, 80, 130)  # azul cabeçalho tabela
COR_TABELA_ALT = (240, 245, 252)  # azul muito claro (linha alternada)
COR_LINHA = (200, 210, 220)  # divisória
COR_RODAPE = (130, 140, 155)
COR_TEXTO = (30, 30, 30)


FONTE = "ArialUni"


class RelatorioTecnico(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=22)
        # Fontes Unicode (Arial do Windows)
        self.add_font(FONTE, "", r"C:\Windows\Fonts\arial.ttf")
        self.add_font(FONTE, "B", r"C:\Windows\Fonts\arialbd.ttf")
        self.add_font(FONTE, "I", r"C:\Windows\Fonts\ariali.ttf")
        self.add_font(FONTE, "BI", r"C:\Windows\Fonts\arialbi.ttf")
        self._num_paginas = 0

    # ── cabeçalho de página ──────────────────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font(FONTE, "B", 8)
        self.set_text_color(*COR_SECAO)
        self.cell(
            0,
            8,
            "Relatório Técnico de Situação — Cartório Costa Teixeira",
            align="L",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_draw_color(*COR_LINHA)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    # ── rodapé de página ─────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*COR_LINHA)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1)
        self.set_font(FONTE, "", 7)
        self.set_text_color(*COR_RODAPE)
        self.cell(0, 5, f"Página {self.page_no()}", align="C")

    # ── helpers ──────────────────────────────────────────────────────────────
    def titulo_documento(self, linha1: str, linha2: str, meta: list[str]):
        self.set_fill_color(*COR_TITULO)
        self.rect(0, 0, self.w, 52, "F")
        self.set_y(12)
        self.set_font(FONTE, "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, linha1, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(FONTE, "", 13)
        self.cell(0, 8, linha2, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.set_font(FONTE, "", 8)
        self.set_text_color(200, 220, 240)
        for item in meta:
            self.cell(0, 5, item, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*COR_TEXTO)
        self.ln(16)

    def secao(self, numero: str, titulo: str):
        self.ln(4)
        self.set_fill_color(*COR_SECAO)
        self.set_text_color(255, 255, 255)
        self.set_font(FONTE, "B", 11)
        self.cell(0, 9, f"  {numero}. {titulo}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*COR_TEXTO)
        self.ln(3)

    def subsecao(self, numero: str, titulo: str):
        self.ln(2)
        self.set_text_color(*COR_SUBSECAO)
        self.set_font(FONTE, "B", 10)
        self.cell(0, 7, f"{numero}  {titulo}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*COR_SUBSECAO)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), self.l_margin + 80, self.get_y())
        self.set_text_color(*COR_TEXTO)
        self.ln(2)

    def paragrafo(self, texto: str, tamanho: int = 9):
        self.set_font(FONTE, "", tamanho)
        self.set_text_color(*COR_TEXTO)
        self.multi_cell(0, 5, texto, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def badge_vulnerabilidade(self, codigo: str, titulo: str, nivel: str):
        """Cabeçalho colorido de cada vulnerabilidade."""
        cores = {
            "CRITICO": (COR_CRITICO_BG, COR_CRITICO_FG, "● CRITICO"),
            "ALTO": (COR_ALTO_BG, COR_ALTO_FG, "▲ ALTO"),
            "MEDIO": (COR_MEDIO_BG, COR_MEDIO_FG, "* MEDIO"),
        }
        bg, fg, label = cores.get(nivel, (COR_TABELA_ALT, COR_SECAO, nivel))
        self.ln(3)
        self.set_fill_color(*bg)
        self.set_text_color(*fg)
        self.set_font(FONTE, "B", 9)
        self.cell(
            0,
            8,
            f"  {codigo} — {titulo}   [{label}]",
            fill=True,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_text_color(*COR_TEXTO)
        self.ln(1)

    def item_lista(self, texto: str, nivel: int = 0, negrito: bool = False):
        marcador = "•" if nivel == 0 else "-"
        indent = 5 + nivel * 8
        x0 = self.l_margin + indent
        estilo = "B" if negrito else ""
        self.set_font(FONTE, estilo, 9)
        self.set_text_color(*COR_TEXTO)
        self.set_x(x0)
        self.cell(5, 5, marcador)
        self.multi_cell(0, 5, texto, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def caixa_destaque(
        self, titulo: str, linhas: list[str], bg: tuple = COR_TABELA_ALT, fg: tuple = COR_SECAO
    ):
        self.ln(2)
        self.set_fill_color(*bg)
        self.set_draw_color(*COR_LINHA)
        self.set_line_width(0.3)
        x = self.l_margin
        w = self.w - self.l_margin - self.r_margin
        y_ini = self.get_y()
        # titulo
        self.set_font(FONTE, "B", 9)
        self.set_text_color(*fg)
        self.cell(w, 7, f"  {titulo}", fill=True, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # linhas
        self.set_font(FONTE, "", 8.5)
        self.set_text_color(*COR_TEXTO)
        for linha in linhas:
            self.set_x(x)
            self.cell(
                w, 5.5, f"    {linha}", fill=True, border="LR", new_x=XPos.LMARGIN, new_y=YPos.NEXT
            )
        self.set_x(x)
        self.cell(w, 1, "", border="LRB", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def tabela(
        self,
        cabecalhos: list[str],
        larguras: list[float],
        linhas: list[list[str]],
        cor_status: dict | None = None,
    ):
        """
        cor_status: { valor_celula: (bg, fg) } — aplica cor à célula que contiver esse valor.
        """
        # cabeçalho
        self.set_fill_color(*COR_TABELA_HDR)
        self.set_text_color(255, 255, 255)
        self.set_font(FONTE, "B", 8)
        self.set_draw_color(*COR_LINHA)
        self.set_line_width(0.2)
        for cab, larg in zip(cabecalhos, larguras):
            self.cell(larg, 7, f" {cab}", border=1, fill=True)
        self.ln()

        # linhas
        self.set_font(FONTE, "", 8)
        for i, linha in enumerate(linhas):
            fill_bg = COR_TABELA_ALT if i % 2 == 0 else (255, 255, 255)
            for j, (cel, larg) in enumerate(zip(linha, larguras)):
                # verifica cor de status
                bg, fg = fill_bg, COR_TEXTO
                if cor_status:
                    for chave, (cbg, cfg) in cor_status.items():
                        if chave in cel:
                            bg, fg = cbg, cfg
                            break
                self.set_fill_color(*bg)
                self.set_text_color(*fg)
                self.cell(larg, 6, f" {cel}", border=1, fill=True)
            self.ln()

        self.set_text_color(*COR_TEXTO)
        self.ln(2)

    def linha_divisoria(self):
        self.ln(2)
        self.set_draw_color(*COR_LINHA)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)


# ═══════════════════════════════════════════════════════════════════════════════
def construir_relatorio(pdf: RelatorioTecnico):

    # ── CAPA ──────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.titulo_documento(
        "RELATÓRIO TÉCNICO DE SITUAÇÃO",
        "Serventia Cartório Costa Teixeira",
        [
            "Versão: 1.0  |  Data: 03/05/2026  |  Elaborado por: João Lucas",
            "Classificação: Uso Interno  |  Confidencial",
        ],
    )

    # ── 1. SUMÁRIO EXECUTIVO ──────────────────────────────────────────────────
    pdf.secao("1", "Sumário Executivo")
    pdf.paragrafo(
        "A serventia opera com infraestrutura física funcional, mas apresenta fragilidades "
        "sistêmicas significativas em quatro dimensões: segurança de dados, continuidade "
        "operacional, organização documental e governança de acesso. Os riscos mais críticos — "
        "espaço em disco crítico, ausência de controle de acesso a arquivos e acesso remoto "
        "sem VPN — representam ameaças imediatas à integridade dos dados cartorários e à "
        "conformidade legal."
    )
    pdf.paragrafo(
        "O sistema em desenvolvimento (Cartório System) endereça a dimensão financeira/"
        "gerencial, mas os problemas de infraestrutura subjacente precisam de atenção paralela, "
        "pois o novo sistema herdará parte desses riscos ao ser implantado sobre a mesma "
        "infraestrutura."
    )

    # ── 2. INVENTÁRIO DE INFRAESTRUTURA ───────────────────────────────────────
    pdf.secao("2", "Inventário de Infraestrutura — Estado Atual")

    pdf.subsecao("2.1", "Servidor")
    pdf.tabela(
        ["Atributo", "Valor"],
        [70, 100],
        [
            ["Tipo", "Físico Windows"],
            ["Localização", "Sala técnica isolada"],
            ["Função", "Arquivos, sistema Engegraph, backup"],
        ],
    )

    pdf.subsecao("2.2", "Estrutura de Discos")
    cor_disco = {
        "CRITICO": (COR_CRITICO_BG, COR_CRITICO_FG),
        "Atenção": (COR_ALTO_BG, COR_ALTO_FG),
        "OK": (COR_OK_BG, COR_OK_FG),
    }
    pdf.tabela(
        ["Drive", "Label", "Total (GB)", "Usado (GB)", "Livre (GB)", "% Livre", "Status"],
        [18, 38, 26, 26, 26, 20, 16],
        [
            ["C:", "WIN SSD", "476", "149", "327", "69%", "OK"],
            ["D:", "Dados", "296", "236", "60", "20%", "CRITICO"],
            ["E:", "Engegraph GED", "635", "362", "274", "43%", "Atenção"],
            ["F:", "Engegraph", "224", "102", "121", "54%", "OK"],
            ["H:", "(sem label)", "932", "388", "544", "58%", "OK"],
            ["I:", "Backup Cartório", "3726", "3305", "421", "11%", "CRITICO"],
        ],
        cor_status=cor_disco,
    )

    pdf.subsecao("2.3", "Rede")
    pdf.tabela(
        ["Atributo", "Valor"],
        [70, 100],
        [
            ["Topologia", "Cabeada (estações/impressoras) + Wi-Fi colaboradores + Wi-Fi clientes"],
            ["Equipamentos", "1 roteador + 1 switch central"],
            ["Controle de acesso à rede", "Senha (básico)"],
            ["Acesso remoto", "Sim (gestor + suporte Engegraph)"],
            ["VPN", "NÃO EXISTE"],
        ],
    )

    pdf.subsecao("2.4", "Energia")
    pdf.tabela(
        ["Atributo", "Valor"],
        [70, 100],
        [
            ["Gerador", "NÃO POSSUI"],
            ["Proteção", "Nobreaks com baixa autonomia"],
            ["Histórico", "Quedas de energia e internet ocorrem com frequência"],
        ],
    )

    # ── 3. VULNERABILIDADES CRÍTICAS ──────────────────────────────────────────
    pdf.secao("3", "Vulnerabilidades Criticas")

    # V-01
    pdf.badge_vulnerabilidade("V-01", "Disco de Backup (I:) em colapso iminente", "CRITICO")
    pdf.paragrafo(
        "O disco de backup possui apenas 421 GB livres de 3,7 TB (11% livre). O backup "
        "completo semanal via Cobian Gravity, considerando o volume dos drives D: e E: "
        "juntos (~598 GB usados), pode já estar falhando silenciosamente por falta de espaço."
    )
    pdf.item_lista(
        "Risco: perda de dados irreparável em caso de falha de hardware sem backup válido.",
        negrito=True,
    )
    pdf.item_lista(
        "Evidência: o mapeamento técnico confirma — 'já foram perdidos arquivos por falta de backup'."
    )
    pdf.caixa_destaque(
        "Recomendações Imediatas",
        [
            "Verificar log do Cobian Gravity: confirmar se os últimos backups completaram com sucesso.",
            "Adicionar disco ou expandir armazenamento antes da próxima execução semanal.",
            "Configurar alertas de espaço em disco (notificação por e-mail quando < 20% livre).",
        ],
        COR_CRITICO_BG,
        COR_CRITICO_FG,
    )

    # V-02
    pdf.badge_vulnerabilidade("V-02", "Disco de Dados (D:) com 20% de espaço livre", "CRITICO")
    pdf.paragrafo(
        "Com apenas 60 GB livres em 296 GB totais, o disco de dados principal está abaixo "
        "do limiar seguro para operação estável do Windows Server e do Engegraph. Abaixo de "
        "15% (~44 GB), o sistema operacional começa a se comportar de forma imprevisível. "
        "Com crescimento diário de documentos digitalizados, esse limiar pode ser atingido "
        "em semanas."
    )
    pdf.caixa_destaque(
        "Recomendações Imediatas",
        [
            "Auditar disco D: para identificar duplicatas e arquivos temporários.",
            "Mover arquivos históricos para o disco H: (543 GB livres — drive subutilizado).",
        ],
        COR_CRITICO_BG,
        COR_CRITICO_FG,
    )

    # V-03
    pdf.badge_vulnerabilidade("V-03", "Acesso Remoto sem VPN", "CRITICO")
    pdf.paragrafo(
        "O gestor e o suporte do Engegraph acessam o servidor remotamente sem tunelamento "
        "VPN. O protocolo usado (presumivelmente RDP ou SMB) expõe a porta de acesso remoto "
        "diretamente à internet. Ataques de força bruta contra RDP são automatizados e "
        "contínuos. Uma credencial fraca ou vulnerabilidade do protocolo resulta em acesso "
        "completo ao servidor — incluindo todos os documentos cartorários e banco do Engegraph."
    )
    pdf.caixa_destaque(
        "Recomendações",
        [
            "Implementar VPN (WireGuard — gratuito, leve, instalável no roteador ou servidor).",
            "Bloquear RDP/SMB direto na borda do roteador.",
            "Habilitar autenticação de dois fatores para o acesso remoto.",
        ],
        COR_CRITICO_BG,
        COR_CRITICO_FG,
    )

    # V-04
    pdf.badge_vulnerabilidade("V-04", "Ausência Total de Controle de Acesso a Arquivos", "CRITICO")
    pdf.paragrafo(
        "Qualquer colaborador pode criar, renomear, mover e deletar arquivos e pastas de "
        "outros em \\\\SERVIDOR\\Documentos Compartilhados. Não há permissões por usuário "
        "nem por grupo. A pasta 'Esta pasta da Milena apareceu dentro da Moni' (19/01/2026) "
        "confirma que a movimentação indevida já ocorreu em produção."
    )
    pdf.item_lista("Risco: perda acidental ou intencional de documentos com efeito jurídico.")
    pdf.item_lista("Risco: impossibilidade de rastrear quem deletou ou moveu um arquivo.")
    pdf.item_lista(
        "Risco: não conformidade direta com CNJ e LGPD (ausência de trilha de auditoria)."
    )
    pdf.caixa_destaque(
        "Recomendações",
        [
            "Implementar permissões NTFS: escrita restrita à pasta própria, leitura controlada.",
            "Ativar auditoria de arquivo do Windows Server (log de acesso, modificações, deleções).",
        ],
        COR_CRITICO_BG,
        COR_CRITICO_FG,
    )

    # ── 4. VULNERABILIDADES ALTAS ─────────────────────────────────────────────
    pdf.secao("4", "Vulnerabilidades Altas")

    # V-05
    pdf.badge_vulnerabilidade("V-05", "Documentos Sigilosos sem Restrição de Acesso", "ALTO")
    pdf.paragrafo(
        "A pasta 'DOCUMENTOS FALSOS' (criada em 19/01/2026) armazena documentos fraudulentos "
        "— incluindo um RG falso e documentos relacionados a fraudes investigadas — acessíveis "
        "a todos os colaboradores, incluindo estagiários. Não existe protocolo documentado "
        "para tratamento de documentos suspeitos/falsos apresentados à serventia."
    )
    pdf.item_lista("Risco: violação de sigilo profissional.")
    pdf.item_lista(
        "Risco legal: estagiário com acesso a documento de fraude investigada pelo MP configura violação de sigilo."
    )
    pdf.caixa_destaque(
        "Recomendações",
        [
            "Criar pasta restrita com acesso apenas ao titular e responsável legal.",
            "Documentar procedimento formal para recebimento, registro e guarda de documentos suspeitos.",
        ],
        COR_ALTO_BG,
        COR_ALTO_FG,
    )

    # V-06
    pdf.badge_vulnerabilidade("V-06", "Duplicação Massiva e Descontrolada de Arquivos", "ALTO")
    pdf.paragrafo(
        "O diretório compartilhado apresenta multiplicação sistemática de pastas e arquivos "
        "sem controle de versão, com exemplos identificados:"
    )
    pdf.item_lista("'INTIMAÇÕES ONR TEREZOPOLIS' + 4 cópias (- Copia, - Copia (2), (3), (4))")
    pdf.item_lista("'DOCUMENTOS ESCRITURAS' + 'DOCUMENTOS ESCRITURAS - Copia'")
    pdf.item_lista(
        "'INVENTARIO CLEVERSON' vs 'INVENTARIO CLEWERSON' (mesmo processo, nomes diferentes)"
    )
    pdf.item_lista("'Nova pasta', 'Nova pasta (2)', 'Nova pasta (3)' — sem identificação")
    pdf.item_lista(
        "traslado.pdf / traslado-.pdf / traslado--.pdf / traslado--1.pdf na raiz compartilhada"
    )
    pdf.paragrafo(
        "Risco: trabalho executado na versão errada do documento, retrabalho, impossibilidade "
        "de auditoria e consumo acelerado de espaço em disco."
    )

    # V-07
    pdf.badge_vulnerabilidade("V-07", "Arquivos de Clientes na Raiz da Pasta Compartilhada", "ALTO")
    pdf.paragrafo(
        "Dezenas de PDFs de clientes estão soltos na raiz de \\\\SERVIDOR\\Documentos "
        "Compartilhados — escrituras, matrículas, contratos assinados, traslados, certidões. "
        "Exemplos: 'cliente.pdf' (21 MB), dois arquivos 'escritura.pdf' com datas diferentes, "
        "contrato assinado com CPF no nome do arquivo. Documentos de clientes identificáveis "
        "acessíveis sem restrição violam diretamente a LGPD (Art. 6 — finalidade e adequação). "
        "Risco de sanção da ANPD."
    )

    # V-08
    pdf.badge_vulnerabilidade("V-08", "Dependência Critica do Engegraph sem Contingência", "ALTO")
    pdf.paragrafo(
        "O Engegraph ocupa dois discos dedicados (F: 223 GB, E: 635 GB), é o único sistema de "
        "automação de documentos e admite acesso remoto do suporte terceirizado sem VPN. "
        "Não há contingência documentada para indisponibilidade do sistema. Uma falha no "
        "servidor resulta em parada total da produção de documentos."
    )

    # ── 5. VULNERABILIDADES MÉDIAS ────────────────────────────────────────────
    pdf.secao("5", "Vulnerabilidades Medias")

    pdf.badge_vulnerabilidade(
        "V-09", "Ausência de Gerador com Dependência de Infraestrutura Digital", "MEDIO"
    )
    pdf.paragrafo(
        "A serventia não possui gerador. Nobreaks têm baixa autonomia. Queda de energia "
        "resulta em desligamento abrupto do servidor Windows, com risco de corrupção do banco "
        "de dados do Engegraph e perda de documentos abertos."
    )

    pdf.badge_vulnerabilidade(
        "V-10", "Digitalização Descentralizada com Perda de Documentos", "MEDIO"
    )
    pdf.paragrafo(
        "Documentos são digitalizados localmente em cada estação e salvos no disco local. "
        "O mapeamento confirma: 'às vezes documentos são escaneados e perdidos sendo necessário "
        "refazer a cópia'. Se a estação falhar, documentos escaneados localmente são perdidos "
        "definitivamente."
    )

    pdf.badge_vulnerabilidade("V-11", "Wi-Fi de Clientes na Mesma Infraestrutura", "MEDIO")
    pdf.paragrafo(
        "Existe Wi-Fi para clientes sem indicação de segmentação de rede (VLAN ou rede separada). "
        "Se o Wi-Fi de clientes estiver na mesma rede que as estações de trabalho e o servidor, "
        "qualquer cliente conectado pode tentar acessar os compartilhamentos."
    )

    pdf.badge_vulnerabilidade("V-12", "Política de Segurança Adaptada de Outra Serventia", "MEDIO")
    pdf.paragrafo(
        "O documento de PSI identificado ('PoliticadeSegurança-PSI Cartorio de Alta Floresta.pdf') "
        "é referente ao Cartório de Alta Floresta, não ao Cartório Costa Teixeira. A política de "
        "PLD está em 'protótipo'. Em caso de incidente de segurança ou auditoria do CNJ, a ausência "
        "de PSI própria e atualizada é uma não-conformidade grave."
    )

    # ── 6. ANÁLISE DOS PROCESSOS INTERNOS ─────────────────────────────────────
    pdf.secao("6", "Análise dos Processos Internos — Pontos de Fragilidade")

    pdf.subsecao("6.1", "Fluxo Operacional")
    pdf.tabela(
        ["Etapa", "Fragilidade", "Risco"],
        [35, 80, 55],
        [
            [
                "Entrada",
                "Documentação escaneada e salva localmente sem padrão",
                "Perda antes do protocolo",
            ],
            [
                "Qualificação",
                "Sem rastreamento de status por protocolo",
                "Perda de prazo, trabalho duplicado",
            ],
            ["Geração de doc.", "100% dependente do Engegraph", "Parada total se indisponível"],
            [
                "Assinatura",
                "Processo híbrido sem registro centralizado",
                "Impossível auditar quem assinou",
            ],
            [
                "Arquivamento",
                "Sem padrão de nomenclatura ou estrutura",
                "Documentos 'perdidos' no servidor",
            ],
        ],
    )

    pdf.subsecao("6.2", "Gerenciamento Financeiro")
    pdf.paragrafo(
        "O histórico financeiro de 10+ anos está distribuído em planilhas isoladas (.ods, .xlsx) "
        "sem integração. Os documentos identificados mostram:"
    )
    pdf.item_lista(
        "Planilhas de emolumentos, taxas e fundos por ano (2016–2022), cada uma em arquivo separado."
    )
    pdf.item_lista("Solicitações de ISS como 12 documentos individuais por ano (um por mês).")
    pdf.item_lista("DREs em PDFs gerados manualmente, sem trilha de auditoria.")
    pdf.item_lista("CNJ alimentado separadamente em planilhas específicas por período.")
    pdf.item_lista(
        "Risco de erro humano no cálculo de repasses — cada obrigação calculada manualmente."
    )
    pdf.item_lista(
        "Ausência de trilha de auditoria nas planilhas — quem alterou o quê e quando é desconhecido."
    )

    # ── 7. ANÁLISE DE CONTINUIDADE ────────────────────────────────────────────
    pdf.secao("7", "Análise de Continuidade de Negócio")

    cor_contingencia = {
        "NÃO": (COR_CRITICO_BG, COR_CRITICO_FG),
        "Parcial": (COR_ALTO_BG, COR_ALTO_FG),
    }
    pdf.tabela(
        ["Cenário", "Prob.", "Impacto", "Contingência"],
        [80, 18, 22, 50],
        [
            [
                "Queda de energia + desligamento abrupto do servidor",
                "Alta",
                "Alto",
                "NÃO — só nobreaks",
            ],
            ["Disco D: (Dados) esgota", "Média-alta", "Alto", "NÃO — sem monitoramento"],
            [
                "Backup falha silenciosamente (disco I: cheio)",
                "Alta",
                "Critico",
                "NÃO — sem alertas",
            ],
            [
                "Colaborador deleta pasta de processo acidentalmente",
                "Alta",
                "Alto",
                "NÃO — sem permissões NTFS",
            ],
            ["Ataque via RDP sem VPN", "Média", "Critico", "NÃO — sem VPN"],
            [
                "Engegraph indisponível por falha no servidor",
                "Média",
                "Alto",
                "NÃO — sem contingência",
            ],
            ["Internet indisponível", "Alta", "Médio", "Parcial — operação local continua"],
        ],
        cor_status=cor_contingencia,
    )

    # ── 8. ALINHAMENTO COM O SISTEMA EM DESENVOLVIMENTO ───────────────────────
    pdf.secao("8", "Alinhamento com o Sistema em Desenvolvimento")
    pdf.paragrafo(
        "O Cartório System (Finance Core + Monthly Closing + Obligations) está sendo construído "
        "sobre fundação técnica sólida (FastAPI, SQLAlchemy, Alembic, Pydantic v2, 48 testes "
        "passando). No entanto, os riscos de infraestrutura criam impactos diretos para o novo "
        "sistema:"
    )
    pdf.tabela(
        ["Risco de Infraestrutura", "Impacto no Cartório System"],
        [90, 80],
        [
            ["Disco D: esgotado", "SQLite (dev) e futuro PostgreSQL falham em escrever"],
            ["Backup sem espaço", "Banco de dados do novo sistema fora do backup"],
            ["Sem controle de acesso", "Colaborador pode deletar o arquivo cartorio.db"],
            ["Sem VPN", "API exposta sem camada de segurança adequada"],
            [
                "Auth. multiusuário como 'muito depois'",
                "created_by='gestor' fixo — trilha de auditoria fraca",
            ],
        ],
    )

    # ── 9. RECOMENDAÇÕES PRIORIZADAS ──────────────────────────────────────────
    pdf.secao("9", "Recomendações Priorizadas")

    pdf.subsecao("9.1", "Imediatas — Esta Semana")
    pdf.item_lista(
        "Verificar log do Cobian Gravity — confirmar se os últimos backups completaram.",
        negrito=True,
    )
    pdf.item_lista("Se backups falharam: os dados do servidor estão sem backup válido AGORA.")
    pdf.item_lista(
        "Auditar disco I: (Backup) — identificar backups antigos para liberar espaço urgentemente.",
        negrito=True,
    )
    pdf.item_lista(
        "Auditar disco D: (Dados) — mover arquivos históricos para H: (543 GB livres).",
        negrito=True,
    )

    pdf.subsecao("9.2", "Curto Prazo — 30 Dias")
    pdf.item_lista(
        "Implementar VPN (WireGuard) como pré-requisito para qualquer acesso remoto.", negrito=True
    )
    pdf.item_lista("Bloquear RDP/SMB direto na borda do roteador.")
    pdf.item_lista(
        "Implementar permissões NTFS no servidor — estrutura por colaborador e por processo.",
        negrito=True,
    )
    pdf.item_lista(
        "Criar PSI própria da serventia, documentando acesso remoto, dispositivos e colaboradores.",
        negrito=True,
    )
    pdf.item_lista("Mover documentos falsos/suspeitos para pasta com acesso restrito ao titular.")

    pdf.subsecao("9.3", "Médio Prazo — 90 Dias")
    pdf.item_lista(
        "Padronizar nomenclatura de arquivos — convenção: TIPO_CLIENTE_DATA_VERSAO.ext.",
        negrito=True,
    )
    pdf.item_lista(
        "Centralizar digitalização — scanner salva direto em pasta do servidor, não local."
    )
    pdf.item_lista(
        "Adquirir gerador de baixa potência para o servidor (30–60 min — shutdown controlado)."
    )
    pdf.item_lista("Configurar alertas de espaço em disco no servidor (e-mail quando < 20% livre).")

    pdf.subsecao("9.4", "Associado ao Cartório System")
    pdf.item_lista(
        "Garantir que o banco de dados do Cartório System fique em disco monitorado e no backup.",
        negrito=True,
    )
    pdf.item_lista(
        "Antecipar autenticação multiusuário antes de liberar o sistema para colaboradores."
    )
    pdf.item_lista(
        "Planejar importação histórica (Etapa 6) com mapeamento manual das planilhas existentes."
    )

    # ── 10. MAPA DE RISCOS ────────────────────────────────────────────────────
    pdf.secao("10", "Mapa de Riscos Consolidado")

    pdf.tabela(
        ["Cod.", "Titulo", "Nivel", "Probabilidade", "Impacto"],
        [14, 90, 22, 28, 20],
        [
            ["V-01", "Disco de Backup (I:) em colapso iminente", "CRITICO", "Alta", "Critico"],
            [
                "V-02",
                "Disco de Dados (D:) com 20% de espaço livre",
                "CRITICO",
                "Média-alta",
                "Alto",
            ],
            ["V-03", "Acesso Remoto sem VPN", "CRITICO", "Média", "Critico"],
            ["V-04", "Ausência de controle de acesso a arquivos", "CRITICO", "Alta", "Alto"],
            ["V-05", "Documentos sigilosos sem restrição de acesso", "ALTO", "Média", "Alto"],
            ["V-06", "Duplicação massiva e descontrolada de arquivos", "ALTO", "Alta", "Médio"],
            ["V-07", "Arquivos de clientes na raiz da pasta compartilhada", "ALTO", "Alta", "Alto"],
            ["V-08", "Dependência critica do Engegraph sem contingência", "ALTO", "Média", "Alto"],
            ["V-09", "Ausência de gerador", "MEDIO", "Alta", "Médio"],
            ["V-10", "Digitalização descentralizada", "MEDIO", "Alta", "Médio"],
            ["V-11", "Wi-Fi de clientes na mesma infraestrutura", "MEDIO", "Média", "Médio"],
            ["V-12", "PSI adaptada de outra serventia", "MEDIO", "Baixa", "Alto"],
        ],
        cor_status={
            "CRITICO": (COR_CRITICO_BG, COR_CRITICO_FG),
            "ALTO": (COR_ALTO_BG, COR_ALTO_FG),
            "MEDIO": (COR_MEDIO_BG, COR_MEDIO_FG),
        },
    )

    # ── 11. CONCLUSÃO ─────────────────────────────────────────────────────────
    pdf.secao("11", "Conclusão")
    pdf.paragrafo(
        "A serventia está operacional, mas opera com tolerância ao risco implicitamente alta — "
        "os problemas identificados não causaram falha total ainda, mas a probabilidade de um "
        "evento crítico (perda de documentos, falha de backup, acesso indevido) é significativa. "
        "As vulnerabilidades V-01 a V-04 são independentes entre si: qualquer uma delas pode "
        "materializar um incidente grave isoladamente."
    )
    pdf.paragrafo(
        "O projeto Cartório System representa a abordagem correta: construir sobre fundação "
        "técnica sólida com regras de domínio centralizadas, migrações reversíveis e cobertura "
        "de testes. Mas o maior risco do sistema não está no código — está na infraestrutura "
        "que vai sustentá-lo. As recomendações imediatas (seção 9.1) têm custo baixo e impacto "
        "alto, e devem ser executadas antes da expansão do sistema para além do uso do gestor."
    )
    pdf.caixa_destaque(
        "Nota sobre conformidade",
        [
            "Este relatório foi gerado como ferramenta de apoio à gestão da serventia.",
            "As recomendações de segurança são orientativas e devem ser avaliadas pelo titular.",
            "A implementação de PSI e adequação LGPD podem requerer assessoria jurídica especializada.",
        ],
        COR_TABELA_ALT,
        COR_SECAO,
    )

    # ── RODAPÉ DE DOCUMENTO ───────────────────────────────────────────────────
    pdf.linha_divisoria()
    pdf.set_font(FONTE, "I", 7.5)
    pdf.set_text_color(*COR_RODAPE)
    pdf.multi_cell(
        0,
        4,
        "Relatório gerado com base em: Mapeamento Técnico Inicial (01/05/2026), "
        "Estrutura de Discos do Servidor, Diretório Documentos Compartilhados e "
        "contexto do projeto de desenvolvimento. Data de geração: 03/05/2026.",
        align="C",
    )


# ─── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pdf = RelatorioTecnico()
    construir_relatorio(pdf)
    pdf.output(OUTPUT_PATH)
    print(f"PDF gerado: {OUTPUT_PATH}")
