"""
Dashboard de Ventas - Práctica Final Streamlit
Autor: Santiago Rivas
Descripción: Dashboard para analizar las ventas de una empresa de alimentación.
"""

import streamlit as st
import pandas as pd
import altair as alt

alt.data_transformers.disable_max_rows()



# ===============================
# CONFIGURACIÓN GENERAL
# ===============================

st.set_page_config(
    page_title="Dashboard de Ventas",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Dashboard de Ventas - Empresa de Alimentación")
st.caption("Autor: Santiago Rivas – Práctica final Streamlit")

# Paleta de colores (verdes)
COLOR_PRINCIPAL = "#145A32"
COLOR_SECUNDARIO = "#1E8449"
COLOR_TERCERO = "#27AE60"


# ===============================
# CARGA DE DATOS
# ===============================

@st.cache_data
def load_data():
    # Cargar CSV comprimidos
    df1 = pd.read_csv("parte_1.csv.gz", compression="gzip")
    df2 = pd.read_csv("parte_2.csv.gz", compression="gzip")
    df = pd.concat([df1, df2], ignore_index=True)

    # Quitar índice sobrante si viene en los CSV
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # Asegurar columnas temporales
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["week"] = df["date"].dt.isocalendar().week.astype(int)
        df["day_of_week"] = df["date"].dt.day_name()

    return df


df = load_data()


# ===============================
# NAVEGACIÓN POR SIDEBAR
# ===============================

seccion = st.sidebar.radio(
    "Navegación",
    ["Visión global", "Por tienda", "Por estado", "Gráfico extra"]
)


# ===============================
# SECCIÓN 1 - VISIÓN GLOBAL
# ===============================

if seccion == "Visión global":
    st.header("Visión global de las ventas")

    st.write(
        "En esta sección se presenta un resumen general del desempeño comercial: "
        "número de tiendas, familias de producto, estados y meses analizados, "
        "junto con rankings de ventas y patrones de estacionalidad."
    )

    # a) Conteo general (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Número total de tiendas", df["store_nbr"].nunique())
    col2.metric("Número total de productos que se venden", df["family"].nunique())
    col3.metric("Estados en los que está la empresa", df["state"].nunique())
    col4.metric("Meses con datos", df["month"].nunique())

    st.divider()

    # b) Análisis en términos medios
    st.subheader("Análisis en términos medios")

    c1, c2 = st.columns(2)

    # b.i Ranking (top 10) de productos más vendidos
    ventas_por_producto = (
        df.groupby("family")["sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    ventas_por_producto.columns = ["Producto", "Ventas"]

    with c1:
        st.write("Ranking (Top 10) de los productos más vendidos")
        chart_prod = (
            alt.Chart(ventas_por_producto)
            .mark_bar(color=COLOR_PRINCIPAL)
            .encode(
                x=alt.X("Producto:N", sort="-y", title="Producto / familia"),
                y=alt.Y("Ventas:Q", title="Ventas totales")
            )
        )
        st.altair_chart(chart_prod, use_container_width=True)

    # b.ii Distribución de ventas por tiendas
    ventas_por_tienda = (
        df.groupby("store_nbr")["sales"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    ventas_por_tienda.columns = ["Tienda", "Ventas"]

    with c2:
        st.write("Distribución de las ventas por tiendas")
        chart_tienda = (
            alt.Chart(ventas_por_tienda)
            .mark_bar(color=COLOR_SECUNDARIO)
            .encode(
                x=alt.X("Tienda:N", sort="-y", title="Tienda"),
                y=alt.Y("Ventas:Q", title="Ventas totales")
            )
        )
        st.altair_chart(chart_tienda, use_container_width=True)

    st.divider()

    # b.iii Ranking (Top 10) de tiendas con ventas en productos en promoción
    st.subheader("Ranking (Top 10) de tiendas con ventas en productos en promoción")

    df_promo = df[df["onpromotion"] > 0].copy()
    top_tiendas_promo = (
        df_promo.groupby("store_nbr")["sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_tiendas_promo.columns = ["Tienda", "Ventas_en_promoción"]

    chart_promo = (
        alt.Chart(top_tiendas_promo)
        .mark_bar(color=COLOR_TERCERO)
        .encode(
            x=alt.X("Tienda:N", sort="-y", title="Tienda"),
            y=alt.Y("Ventas_en_promoción:Q", title="Ventas en productos en promoción")
        )
    )
    st.altair_chart(chart_promo, use_container_width=True)

    st.divider()

    # c) Estacionalidad
    st.subheader("Análisis de la estacionalidad de las ventas")

    # Orden correcto de días (inglés) para que queden en orden y no alfabético
    orden_dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df["day_of_week"] = pd.Categorical(df["day_of_week"], categories=orden_dias, ordered=True)

    # Map a español (para mostrar)
    dias_es = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }

    est1, est2, est3 = st.columns(3)

    # c.i Día con más ventas (por término medio)
    ventas_dia = df.groupby("day_of_week")["sales"].mean().sort_index().reset_index()
    ventas_dia["Día"] = ventas_dia["day_of_week"].map(dias_es)
    ventas_dia.columns = ["day_of_week", "Ventas_medias", "Día"]

    with est1:
        st.write("Ventas medias por día de la semana")
        chart_dia = (
            alt.Chart(ventas_dia)
            .mark_bar(color=COLOR_PRINCIPAL)
            .encode(
                x=alt.X("Día:N", sort=list(dias_es.values()), title="Día de la semana"),
                y=alt.Y("Ventas_medias:Q", title="Ventas medias")
            )
        )
        st.altair_chart(chart_dia, use_container_width=True)

    # c.ii Volumen medio por semana del año
    ventas_semana = df.groupby("week")["sales"].mean().sort_index().reset_index()
    ventas_semana.columns = ["Semana", "Ventas_medias"]

    with est2:
        st.write("Volumen de ventas medio por semana del año")
        chart_semana = (
            alt.Chart(ventas_semana)
            .mark_line(color=COLOR_SECUNDARIO)
            .encode(
                x=alt.X("Semana:Q", title="Semana del año"),
                y=alt.Y("Ventas_medias:Q", title="Ventas medias")
            )
        )
        st.altair_chart(chart_semana, use_container_width=True)

    # c.iii Volumen medio por mes
    ventas_mes = df.groupby("month")["sales"].mean().sort_index().reset_index()
    ventas_mes.columns = ["Mes", "Ventas_medias"]

    with est3:
        st.write("Volumen de ventas medio por mes")
        chart_mes = (
            alt.Chart(ventas_mes)
            .mark_line(color=COLOR_TERCERO)
            .encode(
                x=alt.X("Mes:Q", title="Mes"),
                y=alt.Y("Ventas_medias:Q", title="Ventas medias")
            )
        )
        st.altair_chart(chart_mes, use_container_width=True)


# ===============================
# SECCIÓN 2 - POR TIENDA
# ===============================

elif seccion == "Por tienda":
    st.header("Rendimiento de la tienda seleccionada")

    tienda = st.selectbox(
        "Selecciona una tienda",
        sorted(df["store_nbr"].unique())
    )

    df_tienda = df[df["store_nbr"] == tienda].copy()

    # b) Total productos vendidos (sales)
    total_productos_vendidos = df_tienda["sales"].sum()

    # c) Total productos vendidos en promoción
    total_vendidos_promo = df_tienda.loc[df_tienda["onpromotion"] > 0, "sales"].sum()

    porcentaje_promo = (total_vendidos_promo / total_productos_vendidos * 100) if total_productos_vendidos > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total productos vendidos", f"{int(total_productos_vendidos):,}")
    col2.metric("Productos vendidos en promoción", f"{int(total_vendidos_promo):,}")
    col3.metric("% vendidos en promoción", f"{porcentaje_promo:.2f}%")

    st.divider()

    # a) Ventas por año (ordenadas)
    st.subheader("Ventas totales por año")

    ventas_anio = (
        df_tienda.groupby("year", as_index=False)["sales"]
        .sum()
        .sort_values("year")
    )

    chart_ventas_anio = (
        alt.Chart(ventas_anio)
        .mark_bar(color=COLOR_PRINCIPAL)
        .encode(
            x=alt.X("year:O", title="Año", sort="ascending"),
            y=alt.Y("sales:Q", title="Ventas totales (unidades)")
        )
    )

    st.altair_chart(chart_ventas_anio, use_container_width=True)


# ===============================
# SECCIÓN 3 - POR ESTADO
# ===============================

elif seccion == "Por estado":
    st.header("Análisis por estado")

    estado = st.selectbox(
        "Selecciona un estado",
        sorted(df["state"].dropna().unique())
    )

    df_estado = df[df["state"] == estado].copy()

    c1, c2 = st.columns(2)

    # Transacciones por año
    trans_anio = (
        df_estado.groupby("year")["transactions"]
        .sum()
        .sort_index()
        .reset_index()
    )
    trans_anio.columns = ["Año", "Transacciones"]

    with c1:
        st.write("Transacciones por año")
        chart_trans = (
            alt.Chart(trans_anio)
            .mark_bar(color=COLOR_PRINCIPAL)
            .encode(
                x=alt.X("Año:O", title="Año"),
                y=alt.Y("Transacciones:Q", title="Número de transacciones")
            )
        )
        st.altair_chart(chart_trans, use_container_width=True)

    # Top tiendas por ventas en ese estado
    top_tiendas_estado = (
        df_estado.groupby("store_nbr")["sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_tiendas_estado.columns = ["Tienda", "Ventas"]

    with c2:
        st.write("Ranking de tiendas con mas ventas en el estado")
        chart_top_tiendas = (
            alt.Chart(top_tiendas_estado)
            .mark_bar(color=COLOR_SECUNDARIO)
            .encode(
                x=alt.X("Tienda:N", sort="-y", title="Tienda"),
                y=alt.Y("Ventas:Q", title="Ventas totales")
            )
        )
        st.altair_chart(chart_top_tiendas, use_container_width=True)

    # Producto más vendido en el estado
    st.subheader("Producto más vendido en el estado")

    ventas_familia_estado = (
        df_estado.groupby("family")["sales"]
        .sum()
        .sort_values(ascending=False)
    )

    if not ventas_familia_estado.empty:
        fam_top = ventas_familia_estado.index[0]
        ventas_top = ventas_familia_estado.iloc[0]

        st.write(
            f"El producto/familia más vendido en **{estado}** es **{fam_top}** "
            f"con ventas totales de {int(ventas_top):,}."
        )

        df_familias_estado = ventas_familia_estado.reset_index()
        df_familias_estado.columns = ["Producto", "Ventas"]

        chart_familias = (
            alt.Chart(df_familias_estado)
            .mark_bar(color=COLOR_TERCERO)
            .encode(
                x=alt.X("Producto:N", sort="-y", title="Producto / familia"),
                y=alt.Y("Ventas:Q", title="Ventas totales")
            )
        )
        st.altair_chart(chart_familias, use_container_width=True)
    else:
        st.info("No hay datos disponibles para ese estado.")


# ===============================
# SECCIÓN 4 - GRÁFICO EXTRA
# ===============================

elif seccion == "Gráfico extra":
    st.header("Comparación de la evolución de ventas entre tiendas")

    st.write(
        "En esta sección se comparan las ventas diarias de distintas tiendas "
        "para observar diferencias de comportamiento, picos de ventas y tendencias."
    )

    tiendas_sel = st.multiselect(
        "Selecciona tiendas",
        sorted(df["store_nbr"].unique()),
        default=sorted(df["store_nbr"].unique())[:3]
    )

    df_sel = df[df["store_nbr"].isin(tiendas_sel)].copy()

    if not df_sel.empty:
        ventas_diarias = (
            df_sel.groupby(["date", "store_nbr"])["sales"]
            .sum()
            .reset_index()
        )

        chart_lineas = (
            alt.Chart(ventas_diarias)
            .mark_line()
            .encode(
                x=alt.X("date:T", title="Fecha"),
                y=alt.Y("sales:Q", title="Ventas diarias"),
                color=alt.Color(
                    "store_nbr:N",
                    title="Tienda",
                    scale=alt.Scale(scheme="greens")
                )
            )
        )
        st.altair_chart(chart_lineas, use_container_width=True)
    else:
        st.info("Selecciona al menos una tienda para ver la comparación.")

# Ejecución: streamlit run tp_streamlit_ventas.py

