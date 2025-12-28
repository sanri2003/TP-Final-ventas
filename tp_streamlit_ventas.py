import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

# =========================
# CONFIGURACIÓN GENERAL
# =========================
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


# =========================
# CARGA DE DATOS (OPTIMIZADA)
# =========================
@st.cache_data(show_spinner="Cargando datos...")
def load_data():
    """
    Carga datos desde parte_1 y parte_2.
    - Prioriza .csv.gz (deploy).
    - Si no existe, prueba .csv (local).
    - Lee solo columnas necesarias para bajar RAM.
    - Fuerza tipos de dato y crea columnas temporales.
    """
    # Columnas realmente usadas por el dashboard
    usecols = [
        "date", "store_nbr", "family", "sales", "onpromotion",
        "state", "transactions"
    ]

    # Tipos para ahorrar memoria (según tu screenshot + buenas prácticas)
    dtype_map = {
        "store_nbr": "int32",
        "family": "category",
        "sales": "float32",
        "onpromotion": "int32",
        "state": "category",
        "transactions": "float32",
    }

    def read_part(base_name: str) -> pd.DataFrame:
        gz_path = Path(f"{base_name}.csv.gz")
        csv_path = Path(f"{base_name}.csv")

        if gz_path.exists():
            df_part = pd.read_csv(
                gz_path,
                compression="gzip",
                usecols=lambda c: c in usecols or c == "Unnamed: 0",
                low_memory=False,
            )
        elif csv_path.exists():
            df_part = pd.read_csv(
                csv_path,
                usecols=lambda c: c in usecols or c == "Unnamed: 0",
                low_memory=False,
            )
        else:
            raise FileNotFoundError(f"No encontré {base_name}.csv.gz ni {base_name}.csv")

        # Limpieza típica
        if "Unnamed: 0" in df_part.columns:
            df_part = df_part.drop(columns=["Unnamed: 0"])

        return df_part

    df1 = read_part("parte_1")
    df2 = read_part("parte_2")
    df = pd.concat([df1, df2], ignore_index=True)

    # Asegurar columnas clave presentes
    missing = [c for c in ["date", "store_nbr", "family", "sales"] if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en el dataset: {missing}")

    # Parse date y crear columnas temporales (una vez)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Tipos
    for col, dt in dtype_map.items():
        if col in df.columns:
            try:
                df[col] = df[col].astype(dt)
            except Exception:
                # si por algún motivo no se puede castear, lo deja como viene
                pass

    # Si no existe transactions, la creo en 0 (por seguridad)
    if "transactions" not in df.columns:
        df["transactions"] = 0.0
    df["transactions"] = df["transactions"].fillna(0).astype("float32")

    df["year"] = df["date"].dt.year.astype("int16")
    df["month"] = df["date"].dt.month.astype("int8")
    df["week"] = df["date"].dt.isocalendar().week.astype("int16")

    # Día de semana (en inglés para ordenar, después lo mostramos en ES)
    df["day_of_week"] = df["date"].dt.day_name()

    return df


df = load_data()


# =========================
# PRE-CÁLCULOS (CLAVE para NO CRASHEAR)
# =========================
@st.cache_data(show_spinner="Precalculando agregaciones...")
def build_aggregates(df: pd.DataFrame):
    # 1) Top productos
    ventas_por_producto_top10 = (
        df.groupby("family", observed=True)["sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    ventas_por_producto_top10.columns = ["Producto", "Ventas"]

    # 2) Ventas por tienda (para distribución)
    ventas_por_tienda = (
        df.groupby("store_nbr", observed=True)["sales"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    ventas_por_tienda.columns = ["Tienda", "Ventas"]

    # 3) Top tiendas promo
    df_promo = df[df["onpromotion"] > 0]
    top_tiendas_promo = (
        df_promo.groupby("store_nbr", observed=True)["sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_tiendas_promo.columns = ["Tienda", "Ventas_en_promoción"]

    # 4) Estacionalidad (promedios)
    orden_dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dias_es = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }

    ventas_dia = (
        df.groupby("day_of_week", observed=True)["sales"]
        .mean()
        .reindex(orden_dias)
        .reset_index()
    )
    ventas_dia["Día"] = ventas_dia["day_of_week"].map(dias_es)
    ventas_dia.columns = ["day_of_week", "Ventas_medias", "Día"]

    ventas_semana = (
        df.groupby("week", observed=True)["sales"]
        .mean()
        .sort_index()
        .reset_index()
    )
    ventas_semana.columns = ["Semana", "Ventas_medias"]

    ventas_mes = (
        df.groupby("month", observed=True)["sales"]
        .mean()
        .sort_index()
        .reset_index()
    )
    ventas_mes.columns = ["Mes", "Ventas_medias"]

    # 5) Por tienda: ventas por año (para tab 2)
    tienda_anio = (
        df.groupby(["store_nbr", "year"], observed=True)["sales"]
        .sum()
        .reset_index()
        .sort_values(["store_nbr", "year"])
    )

    # 6) Por estado: transacciones por año + top tiendas por estado + ventas por familia (para tab 3)
    estado_anio_trans = (
        df.groupby(["state", "year"], observed=True)["transactions"]
        .sum()
        .reset_index()
        .sort_values(["state", "year"])
    )
    estado_top_tiendas = (
        df.groupby(["state", "store_nbr"], observed=True)["sales"]
        .sum()
        .reset_index()
    )
    estado_familia = (
        df.groupby(["state", "family"], observed=True)["sales"]
        .sum()
        .reset_index()
    )

    # 7) Ventas diarias por tienda (para tab 4)
    ventas_diarias = (
        df.groupby(["date", "store_nbr"], observed=True)["sales"]
        .sum()
        .reset_index()
        .sort_values(["date", "store_nbr"])
    )

    return {
        "ventas_por_producto_top10": ventas_por_producto_top10,
        "ventas_por_tienda": ventas_por_tienda,
        "top_tiendas_promo": top_tiendas_promo,
        "ventas_dia": ventas_dia,
        "ventas_semana": ventas_semana,
        "ventas_mes": ventas_mes,
        "tienda_anio": tienda_anio,
        "estado_anio_trans": estado_anio_trans,
        "estado_top_tiendas": estado_top_tiendas,
        "estado_familia": estado_familia,
        "ventas_diarias": ventas_diarias,
    }


agg = build_aggregates(df)


# =========================
# NAVEGACIÓN
# =========================
seccion = st.sidebar.radio(
    "Navegación",
    ["Visión global", "Por tienda", "Por estado", "Gráfico extra"]
)


# =========================
# SECCIÓN 1 - VISIÓN GLOBAL
# =========================
if seccion == "Visión global":
    st.header("Visión global de las ventas")

    st.write(
        "En esta sección se presenta un resumen general del desempeño comercial: "
        "número de tiendas, familias de producto, estados y meses analizados, "
        "junto con rankings de ventas y patrones de estacionalidad."
    )

    # a) Conteo general
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Número total de tiendas", int(df["store_nbr"].nunique()))
    col2.metric("Número total de productos que se venden", int(df["family"].nunique()))
    col3.metric("Estados en los que está la empresa", int(df["state"].nunique()) if "state" in df.columns else 0)
    col4.metric("Meses con datos", int(df["month"].nunique()))

    st.divider()

    # b) Análisis en términos medios
    st.subheader("Análisis en términos medios")

    c1, c2 = st.columns(2)

    with c1:
        st.write("Ranking (Top 10) de los productos más vendidos")
        chart_prod = (
            alt.Chart(agg["ventas_por_producto_top10"])
            .mark_bar(color=COLOR_PRINCIPAL)
            .encode(
                x=alt.X("Producto:N", sort="-y", title="Producto / familia"),
                y=alt.Y("Ventas:Q", title="Ventas totales")
            )
        )
        st.altair_chart(chart_prod, use_container_width=True)

    with c2:
        st.write("Distribución de las ventas por tiendas")
        chart_tienda = (
            alt.Chart(agg["ventas_por_tienda"])
            .mark_bar(color=COLOR_SECUNDARIO)
            .encode(
                x=alt.X("Tienda:N", sort="-y", title="Tienda"),
                y=alt.Y("Ventas:Q", title="Ventas totales")
            )
        )
        st.altair_chart(chart_tienda, use_container_width=True)

    st.divider()

    # b iii) Top tiendas promo
    st.subheader("Ranking (Top 10) de tiendas con ventas en productos en promoción")

    chart_promo = (
        alt.Chart(agg["top_tiendas_promo"])
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

    est1, est2, est3 = st.columns(3)

    with est1:
        st.write("Ventas medias por día de la semana")
        chart_dia = (
            alt.Chart(agg["ventas_dia"])
            .mark_bar(color=COLOR_PRINCIPAL)
            .encode(
                x=alt.X("Día:N", title="Día de la semana"),
                y=alt.Y("Ventas_medias:Q", title="Ventas medias")
            )
        )
        st.altair_chart(chart_dia, use_container_width=True)

    with est2:
        st.write("Volumen de ventas medio por semana del año")
        chart_semana = (
            alt.Chart(agg["ventas_semana"])
            .mark_line(color=COLOR_SECUNDARIO)
            .encode(
                x=alt.X("Semana:Q", title="Semana del año"),
                y=alt.Y("Ventas_medias:Q", title="Ventas medias")
            )
        )
        st.altair_chart(chart_semana, use_container_width=True)

    with est3:
        st.write("Volumen de ventas medio por mes")
        chart_mes = (
            alt.Chart(agg["ventas_mes"])
            .mark_line(color=COLOR_TERCERO)
            .encode(
                x=alt.X("Mes:Q", title="Mes"),
                y=alt.Y("Ventas_medias:Q", title="Ventas medias")
            )
        )
        st.altair_chart(chart_mes, use_container_width=True)


# =========================
# SECCIÓN 2 - POR TIENDA
# =========================
elif seccion == "Por tienda":
    st.header("Rendimiento por tienda")

    tiendas = sorted(df["store_nbr"].unique().tolist())
    # Guardar selección estable (evita bugs raros al rerun)
    if "tienda_sel" not in st.session_state:
        st.session_state.tienda_sel = int(tiendas[0])

    tienda = st.selectbox(
        "Selecciona una tienda",
        tiendas,
        index=tiendas.index(st.session_state.tienda_sel)
    )
    st.session_state.tienda_sel = int(tienda)

    # KPIs por tienda (sin filtrar todo el DF gigante)
    # Filtrar solo lo necesario para KPIs (es rápido), y el gráfico sale del agregado cacheado
    df_tienda = df[df["store_nbr"] == tienda]

    total_productos_vendidos = float(df_tienda["sales"].sum())
    total_vendidos_promo = float(df_tienda.loc[df_tienda["onpromotion"] > 0, "sales"].sum())
    porcentaje_promo = (total_vendidos_promo / total_productos_vendidos * 100) if total_productos_vendidos > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total productos vendidos", f"{int(total_productos_vendidos):,}")
    col2.metric("Productos vendidos en promoción", f"{int(total_vendidos_promo):,}")
    col3.metric("% vendidos en promoción", f"{porcentaje_promo:.2f}%")

    st.divider()

    st.subheader("Número total de ventas por año (de más antiguo a más reciente)")

    ventas_anio = agg["tienda_anio"][agg["tienda_anio"]["store_nbr"] == tienda][["year", "sales"]]
    ventas_anio = ventas_anio.rename(columns={"year": "Año", "sales": "Ventas"})

    chart_ventas_anio = (
        alt.Chart(ventas_anio)
        .mark_bar(color=COLOR_PRINCIPAL)
        .encode(
            x=alt.X("Año:O", title="Año", sort="ascending"),
            y=alt.Y("Ventas:Q", title="Ventas totales (unidades)")
        )
    )
    st.altair_chart(chart_ventas_anio, use_container_width=True)


# =========================
# SECCIÓN 3 - POR ESTADO
# =========================
elif seccion == "Por estado":
    st.header("Análisis por estado")

    if "state" not in df.columns or df["state"].isna().all():
        st.info("No hay información de estado en el dataset.")
    else:
        estados = sorted(df["state"].dropna().unique().tolist())
        if "estado_sel" not in st.session_state:
            st.session_state.estado_sel = str(estados[0])

        estado = st.selectbox(
            "Selecciona un estado",
            estados,
            index=estados.index(st.session_state.estado_sel)
        )
        st.session_state.estado_sel = str(estado)

        c1, c2 = st.columns(2)

        # Transacciones por año (agregado)
        trans = agg["estado_anio_trans"][agg["estado_anio_trans"]["state"] == estado][["year", "transactions"]]
        trans = trans.rename(columns={"year": "Año", "transactions": "Transacciones"})

        with c1:
            st.write("Transacciones por año")
            chart_trans = (
                alt.Chart(trans)
                .mark_bar(color=COLOR_PRINCIPAL)
                .encode(
                    x=alt.X("Año:O", title="Año"),
                    y=alt.Y("Transacciones:Q", title="Número de transacciones")
                )
            )
            st.altair_chart(chart_trans, use_container_width=True)

        # Top tiendas por ventas en el estado (agregado)
        top_tiendas = agg["estado_top_tiendas"][agg["estado_top_tiendas"]["state"] == estado]
        top_tiendas = (
            top_tiendas.sort_values("sales", ascending=False)
            .head(10)
            .rename(columns={"store_nbr": "Tienda", "sales": "Ventas"})
        )

        with c2:
            st.write("Top tiendas por ventas en el estado")
            chart_top_tiendas = (
                alt.Chart(top_tiendas)
                .mark_bar(color=COLOR_SECUNDARIO)
                .encode(
                    x=alt.X("Tienda:N", sort="-y", title="Tienda"),
                    y=alt.Y("Ventas:Q", title="Ventas totales")
                )
            )
            st.altair_chart(chart_top_tiendas, use_container_width=True)

        st.subheader("Producto más vendido en el estado")

        fam = agg["estado_familia"][agg["estado_familia"]["state"] == estado]
        fam = fam.sort_values("sales", ascending=False)

        if fam.empty:
            st.info("No hay datos disponibles para ese estado.")
        else:
            fam_top = str(fam.iloc[0]["family"])
            ventas_top = float(fam.iloc[0]["sales"])
            st.write(
                f"El producto/familia más vendido en **{estado}** es **{fam_top}** "
                f"con ventas totales de {int(ventas_top):,}."
            )


# =========================
# SECCIÓN 4 - GRÁFICO EXTRA
# =========================
elif seccion == "Gráfico extra":
    st.header("Comparación de la evolución de ventas entre tiendas")

    st.write(
        "En esta sección se comparan las ventas diarias de distintas tiendas "
        "para observar diferencias de comportamiento, picos de ventas y tendencias."
    )

    tiendas = sorted(df["store_nbr"].unique().tolist())
    default_sel = tiendas[:3] if len(tiendas) >= 3 else tiendas

    tiendas_sel = st.multiselect(
        "Selecciona tiendas",
        tiendas,
        default=default_sel
    )

    if not tiendas_sel:
        st.info("Selecciona al menos una tienda para ver la comparación.")
    else:
        # Usamos el agregado cacheado (MUCHO más estable que agrupar cada vez)
        ventas_diarias = agg["ventas_diarias"][agg["ventas_diarias"]["store_nbr"].isin(tiendas_sel)]

        chart_lineas = (
            alt.Chart(ventas_diarias)
            .mark_line()
            .encode(
                x=alt.X("date:T", title="Fecha"),
                y=alt.Y("sales:Q", title="Ventas diarias"),
                color=alt.Color("store_nbr:N", title="Tienda", scale=alt.Scale(scheme="greens"))
            )
        )
        st.altair_chart(chart_lineas, use_container_width=True)

# Ejecución local:
# streamlit run tp_streamlit_ventas.py
