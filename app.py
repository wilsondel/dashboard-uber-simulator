import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RideSim Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── connection ────────────────────────────────────────────────────────────────
PG_HOST = os.getenv("POSTGRES_HOST", "54.209.228.100")
PG_DB   = os.getenv("POSTGRES_DB",   "ridesim")
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")

@st.cache_resource
def get_engine():
    url = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:5432/{PG_DB}"
    return create_engine(url)

@st.cache_data(ttl=60)
def query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)

# ── helpers ───────────────────────────────────────────────────────────────────
def fmt_money(v):  return f"${v:,.2f}"
def fmt_int(v):    return f"{int(v):,}"
def fmt_float(v):  return f"{v:.2f}"

CARD_CSS = """
<style>
.metric-card {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
}
.metric-label { color: #a6adc8; font-size: 0.82rem; margin-bottom: 4px; }
.metric-value { color: #cdd6f4; font-size: 1.7rem; font-weight: 700; }
.metric-sub   { color: #6c7086; font-size: 0.75rem; margin-top: 4px; }
h1, h2, h3 { color: #cdd6f4 !important; }
section[data-testid="stSidebar"] { background: #1e1e2e; }
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

def card(label, value, sub=""):
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>"""

COLORS = px.colors.qualitative.Pastel

# ── load data ─────────────────────────────────────────────────────────────────
pay_sum   = query("SELECT * FROM payment_summary LIMIT 1")
pay_meth  = query("SELECT * FROM payment_by_method ORDER BY total_revenue DESC")
pay_drv   = query("SELECT * FROM payment_by_driver ORDER BY total_earned DESC LIMIT 20")
pay_usr   = query("SELECT * FROM payment_by_user   ORDER BY total_spent  DESC LIMIT 20")
rat_sum   = query("SELECT * FROM rating_summary LIMIT 1")
rat_stars = query("SELECT * FROM rating_star_dist ORDER BY stars")
rat_drv   = query("SELECT * FROM rating_driver_ranking ORDER BY avg_stars DESC, total_ratings DESC LIMIT 20")
rat_usr   = query("SELECT * FROM rating_user_ranking   ORDER BY avg_stars DESC, total_ratings DESC LIMIT 20")
lifecycle = query("""
    SELECT event_type, origin_city, count(*) AS total
    FROM lifecycle_events
    GROUP BY event_type, origin_city
    ORDER BY origin_city, event_type
""")
geo       = query("""
    SELECT trip_id, user_id, driver_id, lat, lon, status, timestamp_utc
    FROM geo_events
    ORDER BY timestamp_utc
""")

# ── header ────────────────────────────────────────────────────────────────────
st.markdown("# 🚗 RideSim Dashboard")
st.caption(f"Base de datos: `{PG_DB}` · `{PG_HOST}:5432`")
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — KPIs globales
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## Resumen Global")
c1, c2, c3, c4, c5, c6 = st.columns(6)

p = pay_sum.iloc[0]
r = rat_sum.iloc[0]

c1.markdown(card("Transacciones", fmt_int(p.total_transactions)), unsafe_allow_html=True)
c2.markdown(card("Revenue Total", fmt_money(p.total_revenue), f"Promedio: {fmt_money(p.avg_ride_price)}"), unsafe_allow_html=True)
c3.markdown(card("Usuarios Únicos", fmt_int(p.unique_users)), unsafe_allow_html=True)
c4.markdown(card("Conductores Únicos", fmt_int(p.unique_drivers)), unsafe_allow_html=True)
c5.markdown(card("Total Ratings", fmt_int(r.total_ratings)), unsafe_allow_html=True)
c6.markdown(card("Estrellas Promedio", fmt_float(r.global_avg_stars), "⭐ global"), unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Pagos
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 💳 Análisis de Pagos")

col_a, col_b = st.columns([1, 2])

with col_a:
    fig_pie = px.pie(
        pay_meth,
        names="method",
        values="total_revenue",
        title="Revenue por Método de Pago",
        hole=0.45,
        color_discrete_sequence=COLORS,
    )
    fig_pie.update_traces(textposition="outside", textinfo="percent+label")
    fig_pie.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_pie, use_container_width=True)

with col_b:
    fig_meth = go.Figure()
    for col, color, label in [
        ("total_revenue", "#89b4fa", "Revenue Total ($)"),
        ("avg_amount",    "#a6e3a1", "Precio Promedio ($)"),
    ]:
        fig_meth.add_trace(go.Bar(
            name=label,
            x=pay_meth["method"],
            y=pay_meth[col],
            marker_color=color,
            text=pay_meth[col].apply(lambda v: f"${v:,.2f}"),
            textposition="outside",
        ))
    fig_meth.update_layout(
        title="Métricas por Método",
        barmode="group",
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="#cdd6f4",
        legend=dict(orientation="h", y=1.12),
        margin=dict(t=60, b=20),
    )
    st.plotly_chart(fig_meth, use_container_width=True)

col_c, col_d = st.columns(2)

with col_c:
    fig_drv = px.bar(
        pay_drv,
        x="total_earned",
        y="driver_id",
        orientation="h",
        title="Top 20 Conductores por Ganancias",
        labels={"total_earned": "Total Ganado ($)", "driver_id": "Conductor"},
        color="total_earned",
        color_continuous_scale="Blues",
        text="total_earned",
    )
    fig_drv.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
    fig_drv.update_layout(
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="#cdd6f4",
        coloraxis_showscale=False,
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig_drv, use_container_width=True)

with col_d:
    fig_usr = px.bar(
        pay_usr,
        x="total_spent",
        y="user_id",
        orientation="h",
        title="Top 20 Usuarios por Gasto",
        labels={"total_spent": "Total Gastado ($)", "user_id": "Usuario"},
        color="total_spent",
        color_continuous_scale="Purples",
        text="total_spent",
    )
    fig_usr.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
    fig_usr.update_layout(
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="#cdd6f4",
        coloraxis_showscale=False,
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig_usr, use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Ratings
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## ⭐ Análisis de Ratings")

col_e, col_f = st.columns([1, 2])

with col_e:
    rat_stars["label"] = rat_stars["stars"].astype(str) + " ⭐"
    fig_stars = px.bar(
        rat_stars,
        x="label",
        y="count",
        title="Distribución de Estrellas",
        labels={"label": "Estrellas", "count": "Cantidad"},
        color="stars",
        color_continuous_scale=["#f38ba8", "#fab387", "#f9e2af", "#a6e3a1", "#89b4fa"],
        text="count",
    )
    fig_stars.update_traces(textposition="outside")
    fig_stars.update_layout(
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="#cdd6f4",
        coloraxis_showscale=False,
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig_stars, use_container_width=True)

with col_f:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=float(r.global_avg_stars),
        delta={"reference": 3.0, "suffix": " vs media"},
        title={"text": "Rating Global Promedio", "font": {"color": "#cdd6f4"}},
        gauge={
            "axis": {"range": [1, 5], "tickcolor": "#cdd6f4"},
            "bar":  {"color": "#89b4fa"},
            "steps": [
                {"range": [1, 2], "color": "#313244"},
                {"range": [2, 3], "color": "#45475a"},
                {"range": [3, 4], "color": "#585b70"},
                {"range": [4, 5], "color": "#6c7086"},
            ],
            "threshold": {
                "line": {"color": "#a6e3a1", "width": 3},
                "thickness": 0.75,
                "value": float(r.global_avg_stars),
            },
        },
        number={"font": {"color": "#cdd6f4", "size": 60}},
    ))
    fig_gauge.update_layout(
        paper_bgcolor="#1e1e2e",
        font_color="#cdd6f4",
        height=300,
        margin=dict(t=60, b=20),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

col_g, col_h = st.columns(2)

with col_g:
    fig_rdrv = px.scatter(
        rat_drv,
        x="total_ratings",
        y="avg_stars",
        hover_name="driver_id",
        size="total_ratings",
        color="avg_stars",
        color_continuous_scale="Greens",
        title="Top 20 Conductores — Estrellas vs N° de Ratings",
        labels={"avg_stars": "Promedio ⭐", "total_ratings": "N° Ratings"},
    )
    fig_rdrv.update_layout(
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="#cdd6f4",
        coloraxis_showscale=False,
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig_rdrv, use_container_width=True)

with col_h:
    fig_rusr = px.scatter(
        rat_usr,
        x="total_ratings",
        y="avg_stars",
        hover_name="user_id",
        size="total_ratings",
        color="avg_stars",
        color_continuous_scale="Oranges",
        title="Top 20 Usuarios — Estrellas vs N° de Ratings",
        labels={"avg_stars": "Promedio ⭐", "total_ratings": "N° Ratings"},
    )
    fig_rusr.update_layout(
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="#cdd6f4",
        coloraxis_showscale=False,
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig_rusr, use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Eventos en tiempo real
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🌍 Eventos de Viajes (Streaming)")

col_i, col_j = st.columns([2, 1])

with col_i:
    if not lifecycle.empty:
        fig_life = px.bar(
            lifecycle,
            x="origin_city",
            y="total",
            color="event_type",
            barmode="group",
            title="Eventos por Ciudad y Tipo",
            labels={"total": "Eventos", "origin_city": "Ciudad", "event_type": "Tipo"},
            color_discrete_sequence=COLORS,
            text="total",
        )
        fig_life.update_traces(textposition="outside")
        fig_life.update_layout(
            plot_bgcolor="#1e1e2e",
            paper_bgcolor="#1e1e2e",
            font_color="#cdd6f4",
            legend=dict(orientation="h", y=1.12),
            margin=dict(t=60, b=20),
        )
        st.plotly_chart(fig_life, use_container_width=True)

with col_j:
    if not lifecycle.empty:
        by_city = lifecycle.groupby("origin_city")["total"].sum().reset_index()
        fig_city = px.pie(
            by_city,
            names="origin_city",
            values="total",
            title="Viajes por Ciudad",
            hole=0.4,
            color_discrete_sequence=COLORS,
        )
        fig_city.update_layout(
            paper_bgcolor="#1e1e2e",
            font_color="#cdd6f4",
            margin=dict(t=40, b=0),
        )
        st.plotly_chart(fig_city, use_container_width=True)

if not geo.empty:
    st.markdown("### Posiciones GPS en Tiempo Real")
    st.map(geo[["lat", "lon"]].dropna(), zoom=2)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Tablas detalle (expandibles)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📋 Datos Detallados")

with st.expander("Top 20 Conductores por Ganancias"):
    st.dataframe(
        pay_drv.style.format({
            "total_earned": "${:.2f}",
            "avg_per_ride": "${:.2f}",
        }),
        use_container_width=True,
    )

with st.expander("Top 20 Usuarios por Gasto"):
    st.dataframe(
        pay_usr.style.format({
            "total_spent":  "${:.2f}",
            "avg_per_ride": "${:.2f}",
        }),
        use_container_width=True,
    )

with st.expander("Top 20 Conductores por Rating"):
    st.dataframe(
        rat_drv.style.format({"avg_stars": "{:.2f}"}),
        use_container_width=True,
    )

with st.expander("Eventos de Ciclo de Vida (lifecycle_events)"):
    lc_full = query("SELECT * FROM lifecycle_events ORDER BY timestamp_utc DESC LIMIT 100")
    st.dataframe(lc_full, use_container_width=True)

with st.expander("Eventos GPS (geo_events)"):
    st.dataframe(geo, use_container_width=True)

# ── footer ────────────────────────────────────────────────────────────────────
st.caption("RideSim · PFSD Maestría · Datos en vivo desde PostgreSQL")
