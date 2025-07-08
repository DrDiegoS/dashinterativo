
import streamlit as st
import pandas as pd
import plotly.express as px

CAMINHO_ARQUIVO = "dashacompanhamento_formatado.xlsx"

@st.cache_data
def carregar_dados():
    return pd.read_excel(CAMINHO_ARQUIVO)

def salvar_dados(df):
    df.to_excel(CAMINHO_ARQUIVO, index=False)

st.set_page_config(layout="wide")
st.title("📊 Dashboard de Linhas de Cuidado")

df = carregar_dados()

if "linha_edit" not in st.session_state:
    st.session_state.linha_edit = None
    st.session_state.fase_edit = None
    st.session_state.tarefa_edit = None

# --- Seção 1: Edição rápida no topo ---
st.markdown("## ✏️ Atualizar Status e Observações")

with st.form("form_edicao_topo"):
    col1, col2, col3 = st.columns(3)
    with col1:
        linha_sel = st.selectbox("Linha de Cuidado", df["Linha de Cuidado"].unique(), index=0 if not st.session_state.linha_edit else list(df["Linha de Cuidado"].unique()).index(st.session_state.linha_edit))
    with col2:
        fases_disp = df[df["Linha de Cuidado"] == linha_sel]["Fase"].unique()
        fase_sel = st.selectbox("Fase", fases_disp, index=0 if not st.session_state.fase_edit else list(fases_disp).index(st.session_state.fase_edit))
    with col3:
        tarefas_disp = df[(df["Linha de Cuidado"] == linha_sel) & (df["Fase"] == fase_sel)]["Tarefa"].unique()
        tarefa_sel = st.selectbox("Tarefa", tarefas_disp, index=0 if not st.session_state.tarefa_edit else list(tarefas_disp).index(st.session_state.tarefa_edit))

    status_opcoes = ["Pendente", "Em andamento", "Concluído", "Ação Contínua"]
    novo_status = st.selectbox("Novo Status", status_opcoes)
    nova_obs = st.text_area("Observações (opcional)", height=80)

    submitted = st.form_submit_button("💾 Salvar Alterações")
    if submitted:
        idx = df[
            (df["Linha de Cuidado"] == linha_sel) &
            (df["Fase"] == fase_sel) &
            (df["Tarefa"] == tarefa_sel)
        ].index
        if not idx.empty:
            df.loc[idx, "Status"] = novo_status
            df.loc[idx, "Observações"] = nova_obs if novo_status != "Concluído" else ""
            salvar_dados(df)
            st.success("Atualização salva com sucesso!")

# --- Seção 2: Adicionar nova linha ---
st.markdown("## ➕ Adicionar Nova Linha de Cuidado")

with st.form("form_adicionar"):
    nova_linha = st.text_input("Nome da nova Linha de Cuidado")
    submitted_add = st.form_submit_button("➕ Criar nova linha")
    if submitted_add and nova_linha.strip() != "":
        tarefas_modelo = df.drop_duplicates(subset=["Fase", "Tarefa"])[["Fase", "Tarefa"]]
        nova_entrada = []
        for _, row in tarefas_modelo.iterrows():
            nova_entrada.append({
                "Linha de Cuidado": nova_linha.strip(),
                "Fase": row["Fase"],
                "Tarefa": row["Tarefa"],
                "Status": "Pendente",
                "Observações": ""
            })
        df = pd.concat([df, pd.DataFrame(nova_entrada)], ignore_index=True)
        salvar_dados(df)
        st.success(f"Linha de cuidado '{nova_linha}' adicionada com sucesso!")

# --- Seção 3: Filtros e visualização ---
st.markdown("## 🔍 Filtros de Visualização")
col1, col2, col3 = st.columns(3)
with col1:
    linhas_filtro = st.multiselect("Filtrar por Linha de Cuidado", df["Linha de Cuidado"].unique(), default=df["Linha de Cuidado"].unique())
with col2:
    fases_filtro = st.multiselect("Filtrar por Fase", df["Fase"].unique(), default=df["Fase"].unique())
with col3:
    status_filtro = st.multiselect("Filtrar por Status", df["Status"].unique(), default=df["Status"].unique())

df_filtrado = df[
    (df["Linha de Cuidado"].isin(linhas_filtro)) &
    (df["Fase"].isin(fases_filtro)) &
    (df["Status"].isin(status_filtro))
]

# --- Seção 4: Tabela com clique para editar ---
st.markdown("## 📋 Tarefas Filtradas")

def on_click_editar(linha, fase, tarefa):
    st.session_state.linha_edit = linha
    st.session_state.fase_edit = fase
    st.session_state.tarefa_edit = tarefa
    st.experimental_rerun()

for i, row in df_filtrado.iterrows():
    with st.expander(f"🔹 {row['Linha de Cuidado']} → {row['Tarefa']}"):
        st.markdown(f"**Fase:** {row['Fase']}")
        st.markdown(f"**Status:** {row['Status']}")
        st.markdown(f"**Observações:** {row['Observações']}")
        if st.button("Editar esta tarefa", key=f"edit_{i}"):
            on_click_editar(row['Linha de Cuidado'], row['Fase'], row['Tarefa'])

# --- Seção 5: Gráficos ---
st.markdown("## 📈 Indicadores de Progresso")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📊 Progresso Geral (inclui 'Ação Contínua')")
    df_total = df.copy()
    df_total["Concluído"] = df_total["Status"].apply(lambda x: 1 if x.lower() in ["concluído", "ação contínua"] else 0)
    progresso_total = df_total.groupby("Linha de Cuidado")["Concluído"].mean().reset_index()
    progresso_total["% Concluído"] = (progresso_total["Concluído"] * 100).round(1)
    fig_total = px.bar(progresso_total, x="Linha de Cuidado", y="% Concluído", text="% Concluído", color="% Concluído", color_continuous_scale="Blues")
    st.plotly_chart(fig_total, use_container_width=True)

with col2:
    if linhas_filtro:
        st.markdown("### 📊 Progresso da Linha Selecionada")
        linha_selecionada = linhas_filtro[0]
        df_sel = df[df["Linha de Cuidado"] == linha_selecionada]
        total = len(df_sel)
        concluidos = df_sel[df_sel["Status"].str.lower().isin(["concluído", "ação contínua"])].shape[0]
        porcentagem = round((concluidos / total) * 100, 1) if total > 0 else 0
        st.metric(f"Progresso de {linha_selecionada}", f"{porcentagem}%")

with col3:
    st.markdown("### 🧩 Proporção dos Status (exclui 'Ação Contínua')")
    df_status_pizza = df[~df["Status"].str.lower().str.contains("ação contínua")]
    fig_pizza = px.pie(df_status_pizza, names="Status", title="Distribuição dos Status", hole=0.4)
    st.plotly_chart(fig_pizza, use_container_width=True)

# --- Seção 6: Exportação ---
st.markdown("## 📤 Exportar Dados")
csv = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button("📥 Baixar CSV filtrado", data=csv, file_name="tarefas_filtradas.csv", mime="text/csv")
