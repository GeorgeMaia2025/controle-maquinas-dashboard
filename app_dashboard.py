import streamlit as st
import pandas as pd
import os
from datetime import date
import altair as alt

# ---------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------
st.set_page_config(
    page_title="Serracal - Gestão de Operações",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------
# LOGO E CABEÇALHO SERRACAL
# ---------------------------------
LOGO_URL = "https://raw.githubusercontent.com/GeorgeMaia2025/controle-maquinas-dashboard/main/LOGOTIPO_SERRACAL_SEM_SLOGAN-removebg-preview.png"

col_logo, col_title = st.columns([1, 3])
with col_logo:
    st.image(LOGO_URL, width=160)
with col_title:
    st.markdown(
        "<h2 style='margin-bottom:0;'>SERRACAL CORRETIVOS AGRÍCOLAS</h2>"
        "<h4 style='margin-top:4px; color:#5a5a5a;'>Dashboard de Desempenho e Custos de Máquinas</h4>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ---------------------------------
# ARQUIVOS DOS DADOS
# ---------------------------------
ARQ_HORAS = "lancamentos.csv"
ARQ_DIESEL = "diesel.csv"

# ---------------------------------
# CARREGAR DADOS (APENAS LEITURA)
# ---------------------------------
if os.path.exists(ARQ_HORAS):
    df_horas = pd.read_csv(ARQ_HORAS)
else:
    df_horas = pd.DataFrame(
        columns=[
            "Máquina",
            "Data",
            "Operador",
            "Horímetro Inicial",
            "Horímetro Final",
            "Horas Trabalhadas",
        ]
    )

if os.path.exists(ARQ_DIESEL):
    df_diesel = pd.read_csv(ARQ_DIESEL)
else:
    df_diesel = pd.DataFrame(
        columns=[
            "Máquina",
            "Data",
            "Litros",
            "Abastecedor",
            "Local/Obra",
            "Observações",
        ]
    )

# Garantir tipos numéricos
if not df_horas.empty:
    for col in ["Horímetro Inicial", "Horímetro Final", "Horas Trabalhadas"]:
        df_horas[col] = pd.to_numeric(df_horas[col], errors="coerce").fillna(0.0)

if not df_diesel.empty:
    df_diesel["Litros"] = pd.to_numeric(df_diesel["Litros"], errors="coerce").fillna(0.0)

# Se não houver dado nenhum, encerra
if df_horas.empty and df_diesel.empty:
    st.info("Ainda não há dados de horas ou diesel para exibir no dashboard.")
    st.stop()

# ---------------------------------
# SIDEBAR – CONFIGURAÇÕES
# ---------------------------------
st.sidebar.markdown("### Parâmetros de Análise")

custo_litro = st.sidebar.number_input(
    "Custo do diesel (R$/L)", min_value=0.0, value=6.00, step=0.10
)
st.sidebar.caption("Usado para calcular custo total e R$/hora.")

# ---------------------------------
# PREPARAR DATAS PARA FILTRO
# ---------------------------------
dfh = df_horas.copy()
dfd = df_diesel.copy()

if not dfh.empty and "Data" in dfh.columns:
    dfh["Data_dt"] = pd.to_datetime(dfh["Data"], dayfirst=True, errors="coerce")
if not dfd.empty and "Data" in dfd.columns:
    dfd["Data_dt"] = pd.to_datetime(dfd["Data"], dayfirst=True, errors="coerce")

datas = []
if not dfh.empty and "Data_dt" in dfh.columns:
    datas.extend(dfh["Data_dt"].dropna().tolist())
if not dfd.empty and "Data_dt" in dfd.columns:
    datas.extend(dfd["Data_dt"].dropna().tolist())

if datas:
    data_min = min(datas).date()
    data_max = max(datas).date()
else:
    data_min = data_max = date.today()

st.subheader("Filtros")

col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
with col_f1:
    data_ini = st.date_input("Data inicial", value=data_min)
with col_f2:
    data_fim = st.date_input("Data final", value=data_max)

# Lista de máquinas
maquinas_existentes = set()
if not dfh.empty and "Máquina" in dfh.columns:
    maquinas_existentes.update(dfh["Máquina"].dropna().unique().tolist())
if not dfd.empty and "Máquina" in dfd.columns:
    maquinas_existentes.update(dfd["Máquina"].dropna().unique().tolist())
maquinas_existentes = sorted(list(maquinas_existentes))

with col_f3:
    maquina_filtro = st.selectbox(
        "Filtrar por máquina",
        ["Todas"] + maquinas_existentes if maquinas_existentes else ["Todas"],
    )

# Aplicar filtro de datas
if not dfh.empty and "Data_dt" in dfh.columns:
    dfh = dfh[
        (dfh["Data_dt"] >= pd.to_datetime(data_ini))
        & (dfh["Data_dt"] <= pd.to_datetime(data_fim))
    ]
if not dfd.empty and "Data_dt" in dfd.columns:
    dfd = dfd[
        (dfd["Data_dt"] >= pd.to_datetime(data_ini))
        & (dfd["Data_dt"] <= pd.to_datetime(data_fim))
    ]

# Filtro por máquina
if maquina_filtro != "Todas":
    if not dfh.empty and "Máquina" in dfh.columns:
        dfh = dfh[dfh["Máquina"] == maquina_filtro]
    if not dfd.empty and "Máquina" in dfd.columns:
        dfd = dfd[dfd["Máquina"] == maquina_filtro]

st.markdown("---")

# ---------------------------------
# KPIs GERAIS
# ---------------------------------
total_horas = dfh["Horas Trabalhadas"].sum() if not dfh.empty else 0.0
total_litros = dfd["Litros"].sum() if not dfd.empty else 0.0
lh_medio = total_litros / total_horas if total_horas > 0 else 0.0
custo_total = total_litros * custo_litro

k1, k2, k3, k4 = st.columns(4)
k1.metric("Horas trabalhadas", f"{total_horas:.1f}")
k2.metric("Litros consumidos", f"{total_litros:.0f}")
k3.metric("L/H médio", f"{lh_medio:.2f}")
k4.metric("Custo total (R$)", f"{custo_total:,.2f}")

st.markdown("---")

# ---------------------------------
# RESUMO POR MÁQUINA + GRÁFICOS
# ---------------------------------
st.subheader("Resumo por Máquina (filtrado)")

if not dfh.empty:
    horas_por_maquina = (
        dfh.groupby("Máquina")["Horas Trabalhadas"].sum().reset_index()
    )
else:
    horas_por_maquina = pd.DataFrame(columns=["Máquina", "Horas Trabalhadas"])

if not dfd.empty:
    litros_por_maquina = dfd.groupby("Máquina")["Litros"].sum().reset_index()
else:
    litros_por_maquina = pd.DataFrame(columns=["Máquina", "Litros"])

resumo_maquinas = pd.merge(
    horas_por_maquina, litros_por_maquina, on="Máquina", how="outer"
).fillna(0.0)

if not resumo_maquinas.empty:
    resumo_maquinas["Litros por Hora (L/H)"] = resumo_maquinas.apply(
        lambda r: r["Litros"] / r["Horas Trabalhadas"]
        if r["Horas Trabalhadas"] > 0
        else 0.0,
        axis=1,
    )
    resumo_maquinas["Custo Total (R$)"] = resumo_maquinas["Litros"] * custo_litro
    resumo_maquinas["Custo por Hora (R$/h)"] = resumo_maquinas.apply(
        lambda r: r["Custo Total (R$)"] / r["Horas Trabalhadas"]
        if r["Horas Trabalhadas"] > 0
        else 0.0,
        axis=1,
    )

    def classificar_consumo(lh):
        if lh == 0:
            return "Sem dados"
        elif lh <= 6:
            return "Bom"
        elif lh <= 8:
            return "Atento"
        else:
            return "Alto"

    resumo_maquinas["Classificação L/H"] = resumo_maquinas[
        "Litros por Hora (L/H)"
    ].apply(classificar_consumo)

    st.dataframe(resumo_maquinas, use_container_width=True)

    st.markdown("### Gráficos por Máquina")

    colg1, colg2 = st.columns(2)

    with colg1:
        chart_litros = (
            alt.Chart(resumo_maquinas)
            .mark_bar()
            .encode(
                x=alt.X("Máquina:N", sort="-y", title="Máquina"),
                y=alt.Y("Litros:Q", title="Litros"),
            )
            .properties(height=300, title="Litros por Máquina")
        )
        st.altair_chart(chart_litros, use_container_width=True)

    with colg2:
        chart_custo_h = (
            alt.Chart(resumo_maquinas)
            .mark_bar()
            .encode(
                x=alt.X("Máquina:N", sort="-y", title="Máquina"),
                y=alt.Y("Custo por Hora (R$/h):Q", title="R$/h"),
            )
            .properties(height=300, title="Custo por Hora por Máquina")
        )
        st.altair_chart(chart_custo_h, use_container_width=True)

else:
    st.info("Nenhum dado no período/filtro selecionado.")

# ---------------------------------
# CONSUMO POR OBRA / TALHÃO
# ---------------------------------
st.subheader("Consumo e Custo por Obra / Talhão (filtrado)")

if not dfd.empty and "Local/Obra" in dfd.columns:
    por_obra = dfd.groupby("Local/Obra")[["Litros"]].sum().reset_index()
    por_obra["Custo Total (R$)"] = por_obra["Litros"] * custo_litro
    st.dataframe(por_obra, use_container_width=True)

    chart_obra = (
        alt.Chart(por_obra)
        .mark_bar()
        .encode(
            x=alt.X("Local/Obra:N", sort="-y", title="Local / Talhão"),
            y=alt.Y("Litros:Q", title="Litros"),
        )
        .properties(height=300, title="Litros por Obra / Talhão")
    )

    st.altair_chart(chart_obra, use_container_width=True)

else:
    st.info("Sem abastecimentos para o período/filtro selecionados.")





