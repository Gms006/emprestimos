import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import locale
from io import BytesIO

# Configurando o locale para formatação monetária brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except:
        pass

# Função para calcular o valor da parcela (Sistema Francês de Amortização - Price)
def calcular_parcela(principal, taxa_juros_anual, prazo_meses):
    taxa_mensal = taxa_juros_anual / 12 / 100
    if taxa_mensal == 0:
        return principal / prazo_meses
    parcela = principal * (taxa_mensal * (1 + taxa_mensal) ** prazo_meses) / ((1 + taxa_mensal) ** prazo_meses - 1)
    return parcela

# Função para gerar a tabela de amortização
def gerar_tabela_amortizacao(principal, taxa_juros_anual, prazo_meses, data_inicio):
    taxa_mensal = taxa_juros_anual / 12 / 100
    parcela = calcular_parcela(principal, taxa_juros_anual, prazo_meses)
    
    saldo_devedor = principal
    tabela = []
    
    for i in range(1, prazo_meses + 1):
        data_parcela = data_inicio + pd.DateOffset(months=i)
        juros = saldo_devedor * taxa_mensal
        amortizacao = parcela - juros
        saldo_devedor -= amortizacao
        
        # Corrigir possíveis erros de arredondamento na última parcela
        if i == prazo_meses:
            amortizacao += saldo_devedor
            saldo_devedor = 0
        
        tabela.append({
            'Parcela': i,
            'Data': data_parcela.strftime('%d/%m/%Y'),
            'Prestação': parcela,
            'Juros': juros,
            'Amortização': amortizacao,
            'Saldo Devedor': saldo_devedor
        })
    
    return pd.DataFrame(tabela)

# Função para analisar curto e longo prazo (conforme princípios contábeis)
def analisar_prazo_contabil(df, data_base):
    # Considera como curto prazo as parcelas que vencem até 12 meses da data base
    data_limite = data_base + pd.DateOffset(months=12)
    
    df_com_data = df.copy()
    df_com_data['Data_dt'] = pd.to_datetime(df_com_data['Data'], format='%d/%m/%Y')
    
    curto_prazo = df_com_data[df_com_data['Data_dt'] <= data_limite].copy()
    longo_prazo = df_com_data[df_com_data['Data_dt'] > data_limite].copy()
    
    return curto_prazo, longo_prazo

# Função para exportar para Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Amortização', index=False)
    return output.getvalue()

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Calculadora de Empréstimos Bancários - Fins Contábeis",
    page_icon="💰",
    layout="wide"
)

# Título e introdução
st.title("Calculadora de Empréstimos Bancários para Fins Contábeis")
st.markdown("""
Esta aplicação permite calcular empréstimos bancários com foco na contabilização correta,
incluindo a classificação de curto e longo prazo de acordo com os princípios contábeis.
""")

# Criando abas para organizar a interface
tab1, tab2 = st.tabs(["Cálculo de Empréstimo", "Sobre Princípios Contábeis"])

with tab1:
    # Formulário para entrada de dados
    st.header("Dados do Empréstimo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        nome_emprestimo = st.text_input("Nome/Descrição do Empréstimo", "Empréstimo Bancário")
        valor_principal = st.number_input("Valor Principal (R$)", min_value=1000.0, value=100000.0, step=1000.0)
        taxa_juros_anual = st.number_input("Taxa de Juros Anual (%)", min_value=0.0, max_value=100.0, value=12.0, step=0.1)
        
    with col2:
        prazo_meses = st.number_input("Prazo (meses)", min_value=1, max_value=360, value=36, step=1)
        data_inicio = st.date_input("Data de Início", datetime.date.today())
        data_base_contabil = st.date_input("Data Base para Análise Contábil", datetime.date.today())
    
    # Cálculo dos valores do empréstimo
    if st.button("Calcular Empréstimo"):
        parcela_mensal = calcular_parcela(valor_principal, taxa_juros_anual, prazo_meses)
        
        # Exibe resumo do empréstimo
        st.header("Resumo do Empréstimo")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Valor do Empréstimo", f"R$ {valor_principal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.metric("Parcela Mensal", f"R$ {parcela_mensal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        with col2:
            st.metric("Taxa de Juros", f"{taxa_juros_anual:.2f}% a.a.")
            st.metric("Prazo", f"{prazo_meses} meses")
        
        with col3:
            total_pago = parcela_mensal * prazo_meses
            total_juros = total_pago - valor_principal
            st.metric("Total Pago", f"R$ {total_pago:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.metric("Total de Juros", f"R$ {total_juros:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        # Gera tabela de amortização
        tabela_amortizacao = gerar_tabela_amortizacao(valor_principal, taxa_juros_anual, prazo_meses, pd.to_datetime(data_inicio))
        
        # Análise de curto e longo prazo
        curto_prazo, longo_prazo = analisar_prazo_contabil(tabela_amortizacao, pd.to_datetime(data_base_contabil))
        
        # Métricas de curto e longo prazo
        st.header("Classificação Contábil")
        col1, col2 = st.columns(2)
        
        with col1:
            valor_curto_prazo = curto_prazo['Amortização'].sum()
            juros_curto_prazo = curto_prazo['Juros'].sum()
            st.metric("Amortização - Curto Prazo (Passivo Circulante)", 
                     f"R$ {valor_curto_prazo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.metric("Juros - Curto Prazo", 
                     f"R$ {juros_curto_prazo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        with col2:
            valor_longo_prazo = longo_prazo['Amortização'].sum()
            juros_longo_prazo = longo_prazo['Juros'].sum()
            st.metric("Amortização - Longo Prazo (Passivo Não Circulante)", 
                     f"R$ {valor_longo_prazo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.metric("Juros - Longo Prazo", 
                     f"R$ {juros_longo_prazo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        # Visualização da distribuição de pagamentos
        st.header("Visualização da Amortização")
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Gráfico de composição da parcela ao longo do tempo
        ax.stackplot(range(1, prazo_meses + 1), 
                    tabela_amortizacao['Juros'], 
                    tabela_amortizacao['Amortização'],
                    labels=['Juros', 'Amortização'],
                    alpha=0.7)
        
        ax.set_xlabel('Mês')
        ax.set_ylabel('Valor (R$)')
        ax.set_title('Composição da Parcela: Juros vs Amortização')
        ax.legend()
        
        st.pyplot(fig)
        
        # Exibe tabela de amortização formatada
        st.header("Tabela de Amortização")
        
        # Formatando valores monetários para exibição
        tabela_formatada = tabela_amortizacao.copy()
        for coluna in ['Prestação', 'Juros', 'Amortização', 'Saldo Devedor']:
            tabela_formatada[coluna] = tabela_formatada[coluna].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        # Opção de filtrar por curto e longo prazo
        filtro = st.radio("Filtrar tabela por:", ['Todas as parcelas', 'Curto Prazo', 'Longo Prazo'])
        
        if filtro == 'Todas as parcelas':
            tabela_exibir = tabela_formatada
        elif filtro == 'Curto Prazo':
            tabela_exibir = tabela_formatada.iloc[curto_prazo.index]
        else:
            tabela_exibir = tabela_formatada.iloc[longo_prazo.index]
        
        st.dataframe(tabela_exibir, use_container_width=True)
        
        # Botão para exportar para Excel
        excel_data = to_excel(tabela_amortizacao)
        st.download_button(
            label="📥 Baixar tabela completa em Excel",
            data=excel_data,
            file_name=f"{nome_emprestimo.replace(' ', '_')}_tabela_amortizacao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Lançamentos contábeis sugeridos
        st.header("Lançamentos Contábeis Sugeridos")
        
        st.markdown(f"""
        ### Contabilização Inicial do Empréstimo
        
        **Débito:** Caixa ou Bancos - R$ {valor_principal:,.2f}  
        **Crédito:** Empréstimos a Pagar (Curto Prazo) - R$ {valor_curto_prazo:,.2f}  
        **Crédito:** Empréstimos a Pagar (Longo Prazo) - R$ {valor_longo_prazo:,.2f}
        
        ### Pagamento Mensal de Parcela
        
        **Débito:** Empréstimos a Pagar (Curto Prazo) - Valor da Amortização  
        **Débito:** Despesas Financeiras - Valor dos Juros  
        **Crédito:** Caixa ou Bancos - Valor da Parcela
        
        ### No Encerramento de Exercício
        
        **Débito:** Empréstimos a Pagar (Longo Prazo) - Valor das amortizações que passarão para curto prazo  
        **Crédito:** Empréstimos a Pagar (Curto Prazo) - Valor das amortizações que passarão para curto prazo
        """.replace(',.2f', ',.2f'.replace(',', 'X').replace('.', ',').replace('X', '.')))

with tab2:
    st.header("Princípios Contábeis Aplicados a Empréstimos Bancários")
    
    st.markdown("""
    ### Classificação em Curto e Longo Prazo
    
    De acordo com os princípios contábeis e as normas brasileiras de contabilidade:
    
    - **Curto Prazo (Passivo Circulante)**: Obrigações com vencimento em até 12 meses após a data do balanço.
    - **Longo Prazo (Passivo Não Circulante)**: Obrigações com vencimento superior a 12 meses após a data do balanço.
    
    ### Regime de Competência
    
    As despesas com juros devem ser reconhecidas no período em que são incorridas, independentemente do pagamento.
    
    ### Apresentação nas Demonstrações Financeiras
    
    Os empréstimos devem ser apresentados no Balanço Patrimonial separando:
    
    1. **Passivo Circulante**: Valor das amortizações a vencer nos próximos 12 meses
    2. **Passivo Não Circulante**: Valor das amortizações a vencer após os próximos 12 meses
    
    ### Notas Explicativas
    
    As demonstrações financeiras devem conter notas explicativas sobre os empréstimos, incluindo:
    
    - Taxas de juros
    - Prazos de vencimento
    - Garantias oferecidas
    - Cláusulas contratuais relevantes
    
    ### Custo Efetivo
    
    É recomendável calcular o custo efetivo dos empréstimos, considerando todos os custos de transação.
    
    ### Normas Contábeis Aplicáveis
    
    - **CPC 08**: Custos de Transação e Prêmios na Emissão de Títulos e Valores Mobiliários
    - **CPC 38/46/48**: Instrumentos Financeiros
    - **CPC 26**: Apresentação das Demonstrações Contábeis
    """)

st.sidebar.header("Sobre")
st.sidebar.info("""
Este aplicativo foi desenvolvido para auxiliar na contabilização correta de empréstimos bancários,
seguindo os princípios contábeis e as normas brasileiras de contabilidade.

**Recursos:**
- Cálculo detalhado de amortização (Sistema Price)
- Classificação automática em curto e longo prazo
- Sugestões de lançamentos contábeis
- Exportação para Excel
""")
