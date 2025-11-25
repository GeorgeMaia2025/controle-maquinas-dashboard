import streamlit as st
import pandas as pd
import os
from datetime import date

# ------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------
st.set_page_config(
    page_title="Dashboard – Controle de Máquinas",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("Dashboard – Desempenho e Custos das Máquinas")

# ------------------------
# ARQUIVOS DOS DADOS
# ------------------------
ARQ_HORAS = "lancamentos.csv"
ARQ_DIESEL = "diesel.csv"

# ------------------------
# CARREGAR DADOS (APENAS LEITURA)
# ------------------------
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
        df_horas[col] = pd.to_numeric(df_horas[col], errors="coerce").fillna(0)

if not df_diesel.empty:
    df_diesel["Litros"] = pd.to_numeric(df_diesel["Litros"], errors="coerce").fillna(0)

# ------------------------
# SIDEBAR – CONFIGURAÇÃO
# ------------------------
st.sidebar.title("Filtros e Configurações")

custo_litro = st.sidebar.number_input(
    "Custo do diesel (R$/L)", min_value=0.0, value=6.00, step=0.10
)
st.sidebar.caption("Usado para calcular custo total e R$/hora.")

# ------------------------
# SE NÃO TIVER DADOS
# ------------------------
if df_horas.empty and df_diesel.empty:
    st.info("Ainda não há dados de horas ou diesel para exibir no dashboard.")
    st.stop()

# ------------------------
# PREPARAR DATAS PARA FILTRO
# ------------------------
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

col_f1, col_f2 = st.columns(2)
with col_f1:
    data_ini = st.date_input("Data inicial", value=data_min)
with col_f2:
    data_fim = st.date_input("Data final", value=data_max)

# Lista de máquinas para filtro
maquinas_existentes = set()
if not dfh.empty and "Máquina" in dfh.columns:
    maquinas_existentes.update(dfh["Máquina"].dropna().unique().tolist())
if not dfd.empty and "Máquina" in dfd.columns:
    maquinas_existentes.update(dfd["Máquina"].dropna().unique().tolist())
maquinas_existentes = sorted(list(maquinas_existentes))

maquina_filtro = st.selectbox(
    "Filtrar por máquina",
    ["Todas"] + maquinas_existentes if maquinas_existentes else ["Todas"],
)

# Aplicar filtros por data
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

# ------------------------
# RESUMO POR MÁQUINA
# ------------------------
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
).fillna(0)

if not resumo_maquinas.empty:
    resumo_maquinas["Litros por Hora (L/H)"] = resumo_maquinas.apply(
        lambda r: r["Litros"] / r["Horas Trabalhadas"]
        if r["Horas Trabalhadas"] > 0
        else 0,
        axis=1,
    )
    resumo_maquinas["Custo Total (R$)"] = resumo_maquinas["Litros"] * custo_litro
    resumo_maquinas["Custo por Hora (R$/h)"] = resumo_maquinas.apply(
        lambda r: r["Custo Total (R$)"] / r["Horas Trabalhadas"]
        if r["Horas Trabalhadas"] > 0
        else 0,
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
else:
    st.info("Nenhum dado dentro do período/filtros selecionados.")

# ------------------------
# CONSUMO POR OBRA / TALHÃO
# ------------------------
st.subheader("Consumo e Custo por Obra / Talhão (filtrado)")

if not dfd.empty and "Local/Obra" in dfd.columns:
    por_obra = dfd.groupby("Local/Obra")[["Litros"]].sum().reset_index()
    por_obra["Custo Total (R$)"] = por_obra["Litros"] * custo_litro
    st.dataframe(por_obra, use_container_width=True)
else:
    st.info("Sem abastecimentos para o período/filtros selecionados.")

# ------------------------
# HORAS POR OPERADOR / LITROS POR ABASTECEDOR
# ------------------------
st.subheader("Horas por Operador e Litros por Abastecedor (filtrado)")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Horas por Operador**")
    if not dfh.empty and "Operador" in dfh.columns:
        por_operador = (
            dfh.groupby("Operador")["Horas Trabalhadas"].sum().reset_index()
        )
        st.dataframe(por_operador, use_container_width=True)
    else:
        st.info("Sem lançamentos de horas no período/filtro.")

with col2:
    st.markdown("**Litros por Abastecedor**")
    if not dfd.empty and "Abastecedor" in dfd.columns:
        por_abastecedor = (
            dfd.groupby("Abastecedor")["Litros"].sum().reset_index()
        )
        por_abastecedor["Custo Total (R$)"] = (
            por_abastecedor["Litros"] * custo_litro
        )
        st.dataframe(por_abastecedor, use_container_width=True)
    else:
        st.info("Sem abastecimentos no período/filtro.")

st.markdown("---")
st.caption(
    "Dashboard somente leitura. Os dados vêm dos arquivos 'lancamentos.csv' e "
    "'diesel.csv', atualizados pelo sistema interno."
)
