import streamlit as st
import pandas as pd
import re
from pypdf import PdfReader
import io
import os

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(layout="wide", page_title="Controle FP&A - Ibratec")

# --- ESTILIZAÇÃO COMPLETA ---
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC !important; }
    .fpa-card { padding: 20px !important; border-radius: 8px !important; box-shadow: 0px 3px 10px rgba(0,0,0,0.03) !important; border: 1px solid #E2E8F0 !important; margin-bottom: 20px !important; color: #1E293B !important; }
    .bg-gradient-soft { background: linear-gradient(135deg, #F1F5F9 0%, #E2E8F0 100%) !important; }
    .bg-gradient-blue { background: linear-gradient(135deg, #E0F2FE 0%, #BAE6FD 100%) !important; }
    .bg-gradient-neutral { background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%) !important; }
    .bg-gradient-teal { background: linear-gradient(135deg, #E0F2F1 0%, #B2DFDB 100%) !important; }
    .bg-gradient-green { background: linear-gradient(135deg, #DCFCE7 0%, #BBF7D0 100%) !important; }
    .fpa-metric-title { color: #475569 !important; font-size: 13px !important; font-weight: bold !important; text-transform: uppercase !important; }
    .fpa-metric-value { color: #0F172A !important; font-size: 24px !important; font-weight: bold !important; margin-top: 5px !important; }
    .stAlert p { color: #000000 !important; font-weight: 500 !important; }
    h5, h4, h3 { color: #1E3A8A !important; }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO BANNER (TOPO) ---
banner_path = None
nomes_possiveis = ["TOPO.png", "TOPO.jpg", "TOPO.webp", "banner.png", "banner.webp", "Gemini_Generated_Image_zbojlezbojlezboj.png", "1.png"]
for nome in nomes_possiveis:
    if os.path.exists(nome):
        banner_path = nome
        break

if banner_path:
    st.image(banner_path, use_container_width=True)
else:
    st.warning("⚠️ Imagem do cabeçalho não encontrada. Salve a imagem como 'TOPO.png' na pasta do projeto.")

st.markdown("---")

arquivo_pdf = st.file_uploader("Arraste ou selecione o PDF do Metrics aqui", type=["pdf"])

def parse_brl(val_str):
    try: return float(str(val_str).replace('.', '').replace(',', '.'))
    except: return 0.0

def format_brl(val_float):
    if val_float.is_integer(): return f"{int(val_float):,}".replace(',', '.')
    return f"{val_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def extrair_texto_pdf(upload_file):
    reader = PdfReader(upload_file)
    texto_completo = ""
    for page in reader.pages: texto_completo += page.extract_text() + "\n"
    return texto_completo

if arquivo_pdf is not None:
    texto = extrair_texto_pdf(arquivo_pdf)
    linhas = texto.split("\n")
    
    orcamento, cliente, servico, vendedor = "Não encontrado", "Não encontrado", "Não encontrado", "Não encontrado"
    qtd_folhas, num_cores, formato_cartao, qtd_cartuchos, perdas = "0", "0x0", "0x0", "0", "0"
    qtd_solicitada, preco_venda_total = "0", "0,00"
    desc_cartao, peso_cartao, unit_cartao, custo_cartao = "Cartão não localizado", "0,00", "0,00", "0,00"
    
    materiais_encontrados = []
    indiretos_encontrados = []
    tem_laminadora, tem_cortadeira, tem_frete = False, False, False

    # --- VARREDURA BLINDADA ---
    for i, linha in enumerate(linhas):
        l = linha.strip()
        l_upper = l.upper()
        
        if "ORÇAMENTO N" in l_upper or "ORCAMENTO N" in l_upper:
            match_orc = re.search(r"N[°º]?\s*(\d+)", l_upper)
            if match_orc: orcamento = match_orc.group(1).strip()
            
        if "CLIENTE:" in l_upper:
            cliente_prov = l[l_upper.find("CLIENTE:")+8:].strip()
            if len(cliente_prov) > 1: cliente = cliente_prov
            elif (i+1) < len(linhas): cliente = linhas[i+1].strip()
                
        if "SERVIÇO:" in l_upper or "SERVICO:" in l_upper: servico = l[l_upper.find("SERVI")+8:].strip()
        if "VENDEDOR:" in l_upper: vendedor = l[l_upper.find("VENDEDOR:")+9:].strip()

        match_tec = re.search(r"(\d{4,8})\s+([\d.]+)\s+(\d+x\d+)\s+(\d+x\d+)\s+(\d+/\d+)\s+(\d+)\s+([\d.]+)\s+([\d,.]+)", l)
        if match_tec:
            num_cores = match_tec.group(3)
            formato_cartao = match_tec.group(4)
            qtd_cartuchos = match_tec.group(6)
            qtd_folhas = match_tec.group(7)
            perdas = match_tec.group(8)

        if l.startswith(">"):
            match_qtd = re.search(r">\s*1\s*(\d{1,3}(?:\.\d{3})*)", l)
            if match_qtd: qtd_solicitada = match_qtd.group(1)
            
            valores_monetarios = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', l.replace(" ", ""))
            if valores_monetarios: preco_venda_total = valores_monetarios[-1]
            else:
                nums = re.findall(r'[\d.,]+', l)
                if nums: preco_venda_total = nums[-1]

        if "CARTAO" in l_upper and "KG" in l_upper:
            match_mp = re.search(r"CARTAO\s+(.*?)\s+([\d.,]+)\s*KG\s+([\d.,]+)\s+([\d.,]+)", l_upper)
            if match_mp:
                desc_cartao = match_mp.group(1).strip()
                peso_cartao = match_mp.group(2).strip()
                unit_cartao = match_mp.group(3).strip()
                custo_cartao = match_mp.group(4).strip()

        if "LAMINADORA" in l_upper: tem_laminadora = True
        if "CORTADEIRA" in l_upper: tem_cortadeira = True
        if "FRETE" in l_upper: tem_frete = True

        padrao_unidades = re.search(r"([\d.,]+)\s*(KG|UN|M2|CM2|MIL|FLS|GR|MM)\s+([\d.,]+)\s+([\d.,]+)", l_upper)
        is_material = False
        if ("-ORC" in l_upper or "_ORC" in l_upper or " ORC" in l_upper): is_material = True
        elif padrao_unidades and "CARTAO" not in l_upper[:15]: is_material = True
            
        if is_material:
            valores_mat = re.findall(r"([\d,.]+)", l)
            if len(valores_mat) >= 2:
                nome_mat = l
                match_nome = re.search(r"^(.*?)(?=\s*[\d.,]+\s*(?:KG|UN|M2|CM2|MIL|FLS|GR|MM))", l_upper)
                if match_nome: nome_mat = l[:match_nome.end()].strip()
                else:
                    partes_mat = re.split(r"\s{2,}", l)
                    nome_mat = partes_mat[1] if len(partes_mat) > 1 and not any(c.isdigit() for c in partes_mat[1]) else partes_mat[0]
                
                c_total = valores_mat[-2]
                p_custo = valores_mat[-1]
                try: pct_f = float(p_custo.replace(",", ".").replace("%", ""))
                except: pct_f = 0.0
                materiais_encontrados.append({
                    "Item / Processo": nome_mat, "Custo (R$)": c_total, "% Part": f"{p_custo}%",
                    "Critico": pct_f > 10.0, "Zerado": "0,00" in c_total or c_total == "0"
                })

        proc_alvo = ["DESPESAS FIXAS", "ASSESSORIA", "IMP_", "CORTE/VINCO", "COLAGEM", "COMPLEMENTO", "REFILE", "CORTADEIRA", "LAMINADORA", "POLAR", "HOT ", "HOTSTAMPING", "RELEVO", "VERNIZ", "SERIGRAFIA", "DOBRADEIRA", "ACOPLAMENTO", "GUILHOTINA", "CTP", "REVISAO", "EMBALAGEM", "MONTAGEM", "CLICHE"]
        if any(p in l_upper for p in proc_alvo) and ("HR" in l_upper or "0,00" in l or "," in l) and not is_material:
            valores_ind = re.findall(r"([\d,.]+)", l)
            texto_linha = re.sub(r"[\d,.:+]+", "", l).replace("-", " ").replace(" HR ", " ").strip()
            nome_proc = texto_linha if len(texto_linha) > 2 else l_upper.split()[0]
            if len(valores_ind) >= 2:
                c_ind = valores_ind[-2]
                p_ind = valores_ind[-1]
                try: pct_f = float(p_ind.replace(",", ".").replace("%", ""))
                except: pct_f = 0.0
                indiretos_encontrados.append({
                    "Processo / Despesa": nome_proc, "Custo (R$)": c_ind, "% Part": f"{p_ind}%",
                    "Critico": pct_f > 10.0, "Zerado": ("0,00" in c_ind or c_ind == "0") and "COMPLEMENTO" not in l_upper
                })

    # --- CORREÇÃO DO BUG DO NOME DO CLIENTE (PEPSICO) ---
    cliente = re.sub(r'\s+\d{4,6}_.*$', '', cliente).strip()
    if servico != "Não encontrado" and len(servico) > 3:
        cliente = cliente.replace(servico, "").strip()

    lista_alertas_pdf = [] 

    # --- PROCESSAMENTO DOS TURBOS ---
    tem_processo_colagem = any("COLAGEM" in str(ind["Processo / Despesa"]).upper() for ind in indiretos_encontrados)
    tem_material_adesivo = any(any(k in str(mat["Item / Processo"]).upper() for k in ["ADESIVO", "COLA"]) for mat in materiais_encontrados)
    
    tem_processo_verniz = any(any(k in str(ind["Processo / Despesa"]).upper() for k in ["VERNIZ", "SERIGRAFIA"]) for ind in indiretos_encontrados)
    tem_material_verniz = any(any(k in str(mat["Item / Processo"]).upper() for k in ["VERNIZ", "TINTA", "VUV", "VBA"]) for mat in materiais_encontrados)

    tem_material_cliche = any(any(k in str(mat["Item / Processo"]).upper() for k in ["CLICHE", "FACA", "CLI00"]) for mat in materiais_encontrados)
    
    precisa_cliche = any(k in servico.upper() for k in ["RELEVO", "HOT", "CLICHE"])

    if materiais_encontrados:
        t_mat_custo = sum(parse_brl(m["Custo (R$)"]) for m in materiais_encontrados)
        t_mat_part = sum(parse_brl(m["% Part"].replace("%","")) for m in materiais_encontrados)
        materiais_encontrados.append({"Item / Processo": "TOTAL DA CATEGORIA", "Custo (R$)": format_brl(t_mat_custo), "% Part": f"{format_brl(t_mat_part)}%", "Critico": False, "Zerado": False})

    df_ind_final_temp = pd.DataFrame(indiretos_encontrados).drop_duplicates(subset=["Processo / Despesa"]) if indiretos_encontrados else pd.DataFrame()
    ind_lista_limpa = df_ind_final_temp.to_dict(orient='records') if not df_ind_final_temp.empty else []
    
    if ind_lista_limpa:
        t_ind_custo = sum(parse_brl(m["Custo (R$)"]) for m in ind_lista_limpa)
        t_ind_part = sum(parse_brl(m["% Part"].replace("%","")) for m in ind_lista_limpa)
        ind_lista_limpa.append({"Processo / Despesa": "TOTAL DA CATEGORIA", "Custo (R$)": format_brl(t_ind_custo), "% Part": f"{format_brl(t_ind_part)}%", "Critico": False, "Zerado": False})

    df_mat_final = pd.DataFrame(materiais_encontrados)
    df_ind_final = pd.DataFrame(ind_lista_limpa)

    # --- INTERFACE TELA ---
    st.markdown("<h4>📋 Especificações Estruturais do Item</h4>", unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(f"<div class='fpa-card bg-gradient-soft'><div class='fpa-metric-title'>Qtd. Folhas</div><div class='fpa-metric-value'>{qtd_folhas}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='fpa-card bg-gradient-soft'><div class='fpa-metric-title'>N° Cores</div><div class='fpa-metric-value'>{num_cores}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='fpa-card bg-gradient-soft'><div class='fpa-metric-title'>Formato Cartão</div><div class='fpa-metric-value'>{formato_cartao}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='fpa-card bg-gradient-soft'><div class='fpa-metric-title'>Qtd. Cartuchos</div><div class='fpa-metric-value'>{qtd_cartuchos}</div></div>", unsafe_allow_html=True)
    with c5: st.markdown(f"<div class='fpa-card bg-gradient-soft'><div class='fpa-metric-title'>Perdas</div><div class='fpa-metric-value'>{perdas}%</div></div>", unsafe_allow_html=True)

    st.markdown("<h4 style='margin-top: 10px;'>💰 Alvo Comercial & Preço</h4>", unsafe_allow_html=True)
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: st.markdown(f"<div class='fpa-card bg-gradient-blue' style='border-left: 5px solid #0284C7 !important;'><div class='fpa-metric-title'>Orçamento</div><div class='fpa-metric-value'>N° {orcamento}</div></div>", unsafe_allow_html=True)
    with cc2: st.markdown(f"<div class='fpa-card bg-gradient-neutral'><div class='fpa-metric-title'>Cliente</div><div class='fpa-metric-value' style='font-size: 16px; margin-top:12px;'>{cliente}</div></div>", unsafe_allow_html=True)
    with cc3: st.markdown(f"<div class='fpa-card bg-gradient-teal' style='border-left: 5px solid #0D9488 !important;'><div class='fpa-metric-title'>Qtd. Solicitada</div><div class='fpa-metric-value'>{qtd_solicitada}</div></div>", unsafe_allow_html=True)
    with cc4: st.markdown(f"<div class='fpa-card bg-gradient-green' style='border-left: 5px solid #16A34A !important;'><div class='fpa-metric-title'>Preço de Venda Total</div><div class='fpa-metric-value' style='color: #15803D;'>R$ {preco_venda_total}</div></div>", unsafe_allow_html=True)

    st.markdown("<br><h4>🔍 Auditoria de Regras de Negócio do FP&A</h4>", unsafe_allow_html=True)
    col_alertas, col_tabelas = st.columns([1, 1.2])

    with col_alertas:
        # --- CORREÇÃO DA DIAGRAMAÇÃO AQUI (O FIM DA CEGUEIRA!) ---
        st.markdown("<h6 style='color:#1E3A8A; font-weight:bold;'>📐 Validação de Diagramação</h6>", unsafe_allow_html=True)
        q_sol_float = parse_brl(qtd_solicitada)
        q_cart_float = parse_brl(qtd_cartuchos)
        q_fls_float = parse_brl(qtd_folhas)
        
        if q_cart_float <= 0:
            msg_diag_zero = "[CRÍTICO] A quantidade de Cartuchos/Formato está ZERADA! Verifique a diagramação estrutural."
            st.error("🚨 " + msg_diag_zero); lista_alertas_pdf.append(msg_diag_zero)
        elif q_fls_float <= 0:
            msg_fls_zero = "[CRÍTICO] A Quantidade de Folhas de produção está ZERADA!"
            st.error("🚨 " + msg_fls_zero); lista_alertas_pdf.append(msg_fls_zero)
        elif q_sol_float <= 0:
            msg_sol_zero = "[CRÍTICO] A Quantidade Solicitada do pedido está ZERADA ou não foi identificada."
            st.error("🚨 " + msg_sol_zero); lista_alertas_pdf.append(msg_sol_zero)
        else:
            fls_esperadas = q_sol_float / q_cart_float
            if abs(fls_esperadas - q_fls_float) > 100: 
                msg_diag = f"[CRÍTICO] Incoerência Estrutural! Qtd Solicitada ({qtd_solicitada}) ÷ Cartuchos/Folha ({qtd_cartuchos}) resultaria em {format_brl(fls_esperadas)} folhas de produção, mas a ficha está com {qtd_folhas} folhas."
                st.error("🚨 " + msg_diag); lista_alertas_pdf.append(msg_diag)
            else: 
                st.success("✔️ Sucesso: Diagramação aprovada e coerente.")

        st.markdown("<h6 style='color:#1E3A8A; font-weight:bold; margin-top:15px;'>🚛 Validação de Logística</h6>", unsafe_allow_html=True)
        if (tem_laminadora or tem_cortadeira):
            if tem_frete: st.success("✔️ [OK] O roteiro possui Laminadora/Cortadeira e o Frete Interno foi incluído.")
            else:
                msg_log = "[CRÍTICO] Roteiro exige Laminadora/Cortadeira, mas o FRETE COMPLEMENTAR NÃO FOI LANÇADO!"
                st.error("🚨 " + msg_log); lista_alertas_pdf.append(msg_log)

        st.markdown("<h6 style='color:#1E3A8A; font-weight:bold; margin-top:15px;'>⚡ Turbo 1: Consistência Roteiro vs. Insumos</h6>", unsafe_allow_html=True)
        t1_limpo = True
        if tem_processo_colagem and not tem_material_adesivo:
            msg_t1_cola = "[CRÍTICO] Processo de COLAGEM incluído no roteiro, mas nenhum ADESIVO/COLA foi lançado nos materiais!"
            st.error("🚨 " + msg_t1_cola); lista_alertas_pdf.append(msg_t1_cola); t1_limpo = False
        if tem_processo_verniz and not tem_material_verniz:
            msg_t1_verniz = "[CRÍTICO] Processo de VERNIZ/SERIGRAFIA ativo, mas nenhuma TINTA ou VERNIZ consta na lista de materiais!"
            st.error("🚨 " + msg_t1_verniz); lista_alertas_pdf.append(msg_t1_verniz); t1_limpo = False
        if precisa_cliche and not tem_material_cliche:
            msg_t1_corte = f"[ATENÇÃO] O serviço indica uso de acabamento especial, mas não há custo de CLICHÊ/FACA nos materiais."
            st.warning("⚠️ " + msg_t1_corte); lista_alertas_pdf.append(msg_t1_corte); t1_limpo = False
        
        if t1_limpo: st.success("✔️ Relação entre Processos e Insumos validada com sucesso!")

        st.markdown("<h6 style='color:#1E3A8A; font-weight:bold; margin-top:15px;'>📉 Turbo 4: Termômetro de Perdas (Refugo)</h6>", unsafe_allow_html=True)
        perdas_float = parse_brl(perdas)
        try:
            match_c = re.search(r"(\d+)", str(num_cores))
            cores_int = int(match_c.group(1)) if match_c else 0
        except: cores_int = 0
        
        alta_complexidade = cores_int >= 6 or (tem_processo_verniz and tem_processo_colagem) or precisa_cliche
        if perdas_float > 0.0:
            if alta_complexidade and perdas_float < 3.5:
                msg_t4 = f"[ATENÇÃO] Item de alta complexidade ({num_cores} cores / processos múltiplos), mas a taxa de perdas é de apenas {perdas}%. Risco de subestimar custos de refugo!"
                st.warning("⚠️ " + msg_t4); lista_alertas_pdf.append(msg_t4)
            elif perdas_float > 12.0:
                msg_t4 = f"[ATENÇÃO] Taxa de perda muito elevada ({perdas}%) identificada neste orçamento. Avaliar otimização de folha."
                st.warning("⚠️ " + msg_t4); lista_alertas_pdf.append(msg_t4)
            else: st.success(f"✔️ Perda de {perdas}% adequada para a complexidade do item.")
        else: st.warning("⚠️ Taxa de perdas zerada ou não identificada.")

        st.markdown("<h6 style='color:#1E3A8A; font-weight:bold; margin-top:15px;'>⚠️ Alertas Gerais de Custos</h6>", unsafe_allow_html=True)
        alertas_custo = 0
        if not df_mat_final.empty:
            for _, r in df_mat_final.iterrows():
                if "TOTAL" in r["Item / Processo"]: continue
                if r["Zerado"]: 
                    msg_mat = f"[CRÍTICO] Material '{r['Item / Processo']}' está ZERADO!"
                    st.error("🚨 " + msg_mat); alertas_custo+=1; lista_alertas_pdf.append(msg_mat)
                elif r.get("Critico"): 
                    msg_mat_crit = f"[ATENÇÃO] Material '{r['Item / Processo']}' representa uma parcela alta do custo (>10%): {r['% Part']}"
                    st.warning("⚠️ " + msg_mat_crit); alertas_custo+=1; lista_alertas_pdf.append(msg_mat_crit)

        if not df_ind_final.empty:
            for _, r in df_ind_final.iterrows():
                if "TOTAL" in r["Processo / Despesa"]: continue
                if r["Zerado"]: 
                    msg_ind = f"[CRÍTICO] Processo '{r['Processo / Despesa']}' está ZERADO!"
                    st.error("🚨 " + msg_ind); alertas_custo+=1; lista_alertas_pdf.append(msg_ind)
                elif r.get("Critico"):
                    msg_ind_crit = f"[ATENÇÃO] Processo '{r['Processo / Despesa']}' representa uma parcela alta do custo (>10%): {r['% Part']}"
                    st.warning("⚠️ " + msg_ind_crit); alertas_custo+=1; lista_alertas_pdf.append(msg_ind_crit)

        if alertas_custo == 0: st.success("✔️ Todos os insumos possuem valores lançados e participações adequadas.")

    with col_tabelas:
        st.markdown("##### 📊 Custos de Materiais para Orçamento")
        if not df_mat_final.empty: st.dataframe(df_mat_final[["Item / Processo", "Custo (R$)", "% Part"]], width="stretch", hide_index=True)
        else: st.info("Nenhum item listado.")
        st.markdown("<h5 style='margin-top:20px;'>⚙️ Custos Indiretos e Despesas Fixas</h5>", unsafe_allow_html=True)
        if not df_ind_final.empty: st.dataframe(df_ind_final[["Processo / Despesa", "Custo (R$)", "% Part"]], width="stretch", hide_index=True)
        else: st.info("Nenhum custo indireto listado.")

    st.markdown("---")
    st.markdown("<h4>📥 Exportar Documentação do FP&A</h4>", unsafe_allow_html=True)
    
    def gerar_pdf_fpa():
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor('#1E3A8A'), spaceAfter=10)
        style_subtitle = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=11, leading=14, textColor=colors.HexColor('#475569'), spaceAfter=20)
        style_h2 = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor('#0B1E36'), spaceBefore=15, spaceAfter=8)
        style_body = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=13, textColor=colors.Color(0,0,0), spaceAfter=5)
        style_table_cell = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=9, leading=11)
        style_bold_cell = ParagraphStyle('TableCellBold', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold')
        
        story.append(Paragraph("IBRATEC — Relatório de Auditoria FP&A", style_title))
        story.append(Paragraph(f"Análise estrutural e validação do Orçamento N° {orcamento}", style_subtitle))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("💰 Alvo Comercial & Resumo Estrutural", style_h2))
        dados_comerciais = [
            [Paragraph("<b>Orçamento:</b>", style_body), Paragraph(f"N° {orcamento}", style_body), Paragraph("<b>Qtd Folhas:</b>", style_body), Paragraph(qtd_folhas, style_body)],
            [Paragraph("<b>Cliente:</b>", style_body), Paragraph(cliente, style_body), Paragraph("<b>N° Cores:</b>", style_body), Paragraph(num_cores, style_body)],
            [Paragraph("<b>Qtd. Solicitada:</b>", style_body), Paragraph(qtd_solicitada, style_body), Paragraph("<b>Formato Cartão:</b>", style_body), Paragraph(formato_cartao, style_body)],
            [Paragraph("<b>Preço de Venda:</b>", style_body), Paragraph(f"R$ {preco_venda_total}", style_body), Paragraph("<b>Perdas Mapeadas:</b>", style_body), Paragraph(f"{perdas}%", style_body)]
        ]
        t1 = Table(dados_comerciais, colWidths=[100, 170, 110, 150])
        t1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 8)]))
        story.append(t1)
        
        story.append(Paragraph("⚠️ Resumo de Alertas de Auditoria (Turbos Ativos)", style_h2))
        if lista_alertas_pdf:
            for alerta in lista_alertas_pdf:
                if "[CRÍTICO]" in alerta: alerta_formatado = f"<font color='red'><b>{alerta}</b></font>"
                elif "[ATENÇÃO]" in alerta: alerta_formatado = f"<font color='orange'><b>{alerta}</b></font>"
                else: alerta_formatado = f"<font color='green'><b>{alerta}</b></font>"
                story.append(Paragraph(alerta_formatado, style_body))
        else:
            story.append(Paragraph("<font color='green'><b>✔️ Roteiro 100% aprovado sem nenhuma inconsistência de processos ou perdas.</b></font>", style_body))
        
        if materiais_encontrados:
            story.append(Paragraph("📊 Detalhamento de Custos de Materiais", style_h2))
            dados_mat = [["Item / Processo", "Custo (R$)", "% Part"]]
            for m in materiais_encontrados:
                font_st = style_bold_cell if "TOTAL" in m["Item / Processo"] else style_table_cell
                p_item = Paragraph(m["Item / Processo"], font_st)
                dados_mat.append([p_item, m["Custo (R$)"], m["% Part"]])
            t2 = Table(dados_mat, colWidths=[270, 130, 130])
            t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 6)]))
            story.append(t2)
            
        if indiretos_encontrados:
            story.append(Paragraph("⚙️ Custos Indiretos e Despesas Fixas", style_h2))
            dados_ind = [["Processo / Despesa", "Custo (R$)", "% Part"]]
            for ind in df_ind_final.to_dict(orient='records'):
                font_st = style_bold_cell if "TOTAL" in ind["Processo / Despesa"] else style_table_cell
                p_ind = Paragraph(ind["Processo / Despesa"], font_st)
                dados_ind.append([p_ind, ind["Custo (R$)"], ind["% Part"]])
            t3 = Table(dados_ind, colWidths=[270, 130, 130])
            t3.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#475569')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('PADDING', (0,0), (-1,-1), 6)]))
            story.append(t3)
            
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    pdf_data = gerar_pdf_fpa()
    
    st.download_button(
        label="📥 Baixar Ficha Técnica Oficial com Alertas (Relatório PDF)",
        data=pdf_data,
        file_name=f"Relatorio_Auditoria_FPA_{orcamento}.pdf",
        mime="application/pdf"
    )
