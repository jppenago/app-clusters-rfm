"""
Módulo de visualizaciones Plotly para el análisis RFM.

Todas las funciones reciben un DataFrame con columnas
    recencia | frecuencia | valor_total | cluster
y devuelven un go.Figure listo para ser renderizado con st.plotly_chart.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Paleta de colores consistente para todos los gráficos — tonos indigo/blue modernos
_PALETTE = [
    "#6366F1",
    "#3B82F6",
    "#06B6D4",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#EC4899",
    "#14B8A6",
    "#F97316",
    "#84CC16",
]

# Tema de layout compartido para todos los gráficos
_LAYOUT_BASE = dict(
    font=dict(family="Inter, sans-serif", color="#334155"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)


def _cluster_color_map(clusters: list[int]) -> dict[str, str]:
    """Devuelve un dict {str(cluster_id): color} en orden ascendente."""
    return {str(c): _PALETTE[i % len(_PALETTE)] for i, c in enumerate(sorted(clusters))}


# ── Interruptor de DEBUG: escaladas vs. originales ────────────────────────────
# Pon en True para graficar los valores ESCALADOS (los que usa el K-Means);
# pon en False para graficar las variables ORIGINALES (días / tx / COP).
# Afecta tanto al scatter 3D como a los boxplots.
USE_SCALED_FEATURES = True

_ORIG_FEATURES = ["recencia", "frecuencia", "valor_total"]
_SCALED_FEATURES = ["recencia_scaled", "frecuencia_scaled", "valor_total_scaled"]
_ORIG_LABELS = ["Recencia (días)", "Frecuencia (# transacciones)", "Valor Total (COP)"]
_SCALED_LABELS = [
    "Recencia (escalada)",
    "Frecuencia (escalada)",
    "Valor Total (escalado)",
]


def _resolve_features(
    df: pd.DataFrame,
) -> tuple[list[str], list[str], list[bool], bool]:
    """
    Decide qué columnas graficar según ``USE_SCALED_FEATURES``.

    Retorna ``(columnas, etiquetas, usar_log_por_variable, son_escaladas)``.
    Si se piden escaladas pero no están presentes, cae a las originales.
    Con valores escalados nunca se usa escala log (pueden ser negativos o 0-100).
    """
    scaled_available = all(col in df.columns for col in _SCALED_FEATURES)
    if USE_SCALED_FEATURES and scaled_available:
        return _SCALED_FEATURES, _SCALED_LABELS, [False, False, False], True
    # Originales: log en frecuencia y monto por su alta asimetría
    return _ORIG_FEATURES, _ORIG_LABELS, [False, True, True], False


# ── 1. Scatter 3D ─────────────────────────────────────────────────────────────
def plot_3d_scatter(df: pd.DataFrame, max_points: int = 5000) -> go.Figure:
    """
    Scatter 3D coloreado por cluster. Siempre usa los valores **escalados**
    (el mismo espacio en el que opera el K-Means). Si no están disponibles,
    cae a las variables originales.
    """
    plot_df = df if len(df) <= max_points else df.sample(max_points, random_state=42)
    plot_df = plot_df.copy()
    plot_df["cluster_str"] = plot_df["cluster"].astype(str)

    color_map = _cluster_color_map(df["cluster"].unique().tolist())

    scaled_available = all(col in plot_df.columns for col in _SCALED_FEATURES)
    if scaled_available:
        cols, labels, use_scaled = _SCALED_FEATURES, _SCALED_LABELS, True
    else:
        cols, labels, use_scaled = _ORIG_FEATURES, _ORIG_LABELS, False
    x_col, y_col, z_col = cols
    axis_labels = dict(zip(cols, labels))
    title = (
        "Distribución RFM por Cluster (valores escalados)"
        if use_scaled
        else "Distribución RFM por Cluster"
    )

    # En el hover mantenemos los valores originales para interpretabilidad
    hover_data: dict[str, bool] = {}
    if "llave_sistema" in plot_df.columns:
        hover_data["llave_sistema"] = True
    for orig_col in _ORIG_FEATURES:
        if use_scaled and orig_col in plot_df.columns:
            hover_data[orig_col] = True

    fig = px.scatter_3d(
        plot_df,
        x=x_col,
        y=y_col,
        z=z_col,
        color="cluster_str",
        color_discrete_map=color_map,
        opacity=0.70,
        title=title,
        labels={**axis_labels, "cluster_str": "Cluster"},
        hover_data=hover_data,
    )
    fig.update_traces(marker_size=4)
    fig.update_layout(
        **_LAYOUT_BASE,
        height=550,
        legend_title_text="Cluster",
        margin=dict(l=0, r=0, t=55, b=0),
        title=dict(font=dict(size=14, color="#1E293B"), x=0),
    )
    return fig


# ── 2. Distribución de tamaños ────────────────────────────────────────────────
def plot_cluster_sizes(df: pd.DataFrame) -> go.Figure:
    """Gráfico de dona con la proporción de clientes por cluster."""
    counts = df["cluster"].value_counts().sort_index()
    color_map = _cluster_color_map(df["cluster"].unique().tolist())
    colors = [color_map[str(c)] for c in counts.index]

    fig = go.Figure(
        go.Pie(
            labels=[f"Cluster {c}" for c in counts.index],
            values=counts.values,
            hole=0.45,
            marker_colors=colors,
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Clientes: %{value}<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(
            text="Clientes por Cluster", font=dict(size=14, color="#1E293B"), x=0
        ),
        height=400,
        showlegend=False,
    )
    return fig


# ── 3. Box plots por variable ─────────────────────────────────────────────────
def plot_feature_boxplots(df: pd.DataFrame) -> go.Figure:
    """
    Box plots de recencia, frecuencia y valor_total agrupados por cluster.
    Siempre usa las variables originales (días / transacciones / COP).
    """
    features, labels, log_axes, use_scaled = (
        _ORIG_FEATURES,
        _ORIG_LABELS,
        [False, True, True],
        False,
    )

    clusters = sorted(df["cluster"].unique())
    color_map = _cluster_color_map(clusters)

    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=labels,
        vertical_spacing=0.10,
    )

    for row_i, (feature, use_log) in enumerate(zip(features, log_axes), start=1):
        for cl_i, cluster in enumerate(clusters):
            data = df.loc[df["cluster"] == cluster, feature]
            # Para log scale desplazamos valores ≤ 0
            y_vals = data.clip(lower=1) if use_log else data
            fig.add_trace(
                go.Box(
                    y=y_vals,
                    name=f"Cluster {cluster}",
                    marker=dict(
                        color=color_map[str(cluster)],
                        opacity=0.7,
                        outliercolor=color_map[str(cluster)],
                        size=4,
                        line=dict(outlierwidth=1, outliercolor=color_map[str(cluster)]),
                    ),
                    line=dict(width=2),
                    boxmean=True,
                    whiskerwidth=0.6,
                    width=0.5,
                    showlegend=(row_i == 1),
                    legendgroup=f"cl_{cluster}",
                ),
                row=row_i,
                col=1,
            )
        if use_log:
            fig.update_yaxes(type="log", row=row_i, col=1)
        fig.update_xaxes(
            tickvals=[f"Cluster {c}" for c in clusters],
            row=row_i,
            col=1,
        )

    _box_title = "Distribución de variables RFM"
    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(
            text="",
            font=dict(size=14, color="#1E293B"),
            x=0,
        ),
        height=850,
        boxmode="group",
        boxgap=0.25,
        boxgroupgap=0.15,
        legend_title_text="Cluster",
        margin=dict(t=65, l=60, r=20, b=20),
    )
    return fig


# ── 4. Radar chart de perfiles ────────────────────────────────────────────────
def plot_radar_chart(summary: pd.DataFrame) -> go.Figure:
    """
    Radar chart con los perfiles normalizados por cluster.

    La recencia se invierte (1 − valor_norm) para que en todos los ejes
    "más hacia afuera = mejor perfil de cliente".
    """
    mean_cols = ["recencia_mean", "frecuencia_mean", "valor_total_mean"]
    norm = summary[mean_cols + ["cluster"]].copy()

    # Normalización min-max
    for col in mean_cols:
        mn, mx = norm[col].min(), norm[col].max()
        norm[col] = (norm[col] - mn) / (mx - mn) if mx > mn else 0.5

    # Invertir recencia: menor recencia (más reciente) → mejor puntaje
    norm["recencia_mean"] = 1.0 - norm["recencia_mean"]

    categories = ["Recencia\n(invertida)", "Frecuencia", "Valor Total"]
    clusters = sorted(summary["cluster"].unique())
    color_map = _cluster_color_map(clusters)

    fig = go.Figure()
    for _, row in norm.iterrows():
        cid = int(row["cluster"])
        vals = [row[c] for c in mean_cols]
        closed = vals + [vals[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=closed,
                theta=categories + [categories[0]],
                fill="toself",
                name=f"Cluster {cid}",
                line_color=color_map[str(cid)],
                opacity=0.75,
            )
        )

    fig.update_layout(
        **_LAYOUT_BASE,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], gridcolor="#E2E8F0"),
            bgcolor="rgba(0,0,0,0)",
        ),
        title=dict(
            text=(
                "Perfil Normalizado de Clusters<br>"
                "<sup style='color:#64748B;'>Recencia invertida: mayor radio = clientes más recientes</sup>"
            ),
            font=dict(size=14, color="#1E293B"),
            x=0,
        ),
        height=450,
        legend_title_text="Cluster",
    )
    return fig


# ── 6. Scatter 2D Clara e Interpretable ───────────────────────────────────────
def plot_2d_scatter(df: pd.DataFrame, max_points: int = 5_000) -> go.Figure:
    """
    Scatter 2D: Frecuencia (eje X) vs Valor Total (eje Y) con Recencia en el tamaño.
    Gráfico intuitivo de dos dimensiones, extremadamente fácil de leer para negocio.
    """
    plot_df = df if len(df) <= max_points else df.sample(max_points, random_state=42)
    plot_df = plot_df.copy()
    plot_df["cluster_str"] = "Cluster " + plot_df["cluster"].astype(str)

    # Invertimos recencia para que los puntos más grandes representen compras más recientes
    max_rec = plot_df["recencia"].max()
    plot_df["recencia_size"] = max_rec - plot_df["recencia"] + 5

    clusters = sorted(df["cluster"].unique())
    color_map = {
        f"Cluster {c}": _PALETTE[i % len(_PALETTE)] for i, c in enumerate(clusters)
    }

    fig = px.scatter(
        plot_df,
        x="frecuencia",
        y="valor_total",
        color="cluster_str",
        size="recencia_size",
        color_discrete_map=color_map,
        opacity=0.75,
        title=(
            "Análisis RFM 2D: Frecuencia vs. Valor Total<br>"
            "<sup style='color:#64748B;'>El tamaño del círculo representa la recencia (círculo más grande = compra más reciente)</sup>"
        ),
        labels={
            "frecuencia": "Número de Transacciones (Frecuencia)",
            "valor_total": "Monto Total en COP (Valor)",
            "cluster_str": "Segmento",
            "recencia_size": "Recencia de Compra",
        },
        hover_data={
            "frecuencia": True,
            "valor_total": ":,.2f",
            "recencia": True,
            "recencia_size": False,
        },
    )

    # Aplicamos escala logarítmica opcional en el eje Y para manejar la alta disparidad monetaria
    fig.update_yaxes(type="log", title="Monto Total en COP (Escala Log)")
    fig.update_xaxes(type="log", title="Frecuencia de Compra (Escala Log)")

    fig.update_layout(
        **_LAYOUT_BASE,
        height=500,
        legend_title_text="Segmentos",
        margin=dict(l=10, r=10, t=70, b=10),
    )
    return fig


# ── 7. Comparación directa de medianas (Barras) ───────────────────────────────
def plot_cluster_comparison_bars(summary: pd.DataFrame) -> go.Figure:
    """
    Gráfico de barras múltiples que muestra la mediana de Recencia, Frecuencia
    y Valor de forma independiente por clúster con escala e indicadores claros.
    """
    clusters = sorted(summary["cluster"].unique())

    # Creamos subplots de 1 fila x 3 columnas
    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=[
            "<b>Recencia</b><br><sub>(Días desde última compra - menor es mejor)</sub>",
            "<b>Frecuencia</b><br><sub>(Número de transacciones - mayor es mejor)</sub>",
            "<b>Valor Total</b><br><sub>(Inversión en COP - mayor es mejor)</sub>",
        ],
        horizontal_spacing=0.1,
    )

    color_map = _cluster_color_map(clusters)
    for _, row in summary.sort_values("cluster").iterrows():
        c_id = int(row["cluster"])
        c_color = color_map[str(c_id)]
        label = f"Cluster {c_id}"

        # Barra Recencia (Col 1)
        fig.add_trace(
            go.Bar(
                x=[label],
                y=[row["recencia_median"]],
                marker_color=c_color,
                hovertemplate="<b>%{x}</b><br>Recencia Mediana: %{y:.1f} días<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=1,
        )

        # Barra Frecuencia (Col 2)
        fig.add_trace(
            go.Bar(
                x=[label],
                y=[row["frecuencia_median"]],
                marker_color=c_color,
                hovertemplate="<b>%{x}</b><br>Frecuencia Mediana: %{y:.1f} transacciones<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=2,
        )

        # Barra Valor Total (Col 3)
        fig.add_trace(
            go.Bar(
                x=[label],
                y=[row["valor_total_median"]],
                marker_color=c_color,
                hovertemplate="<b>%{x}</b><br>Valor Mediano: COP %{y:,.2f}<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=3,
        )

    fig.update_layout(
        **_LAYOUT_BASE,
        height=450,
        margin=dict(l=10, r=10, t=75, b=60),
    )

    # Formatear el eje de Valor Total (Col 3) para moneda
    fig.update_yaxes(tickprefix="$", row=1, col=3)

    return fig
