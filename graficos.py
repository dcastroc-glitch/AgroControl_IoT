"""Gráficos ejecutivos para el análisis operativo del silo."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BG_COLOR = "#173F2A"
PANEL_COLOR = "#214D34"
GRID_COLOR = "#4D7657"
TEXT_COLOR = "#F0F8EE"
MUTED_TEXT = "#C4D9C3"

COLOR_PROM = "#8FD694"
COLOR_MAX = "#F28F8F"
COLOR_ACT = "#D8B365"
COLOR_PEAK = "#F2C14E"
COLOR_M1 = "#B7E4C7"
COLOR_M2 = "#74C69D"
COLOR_M3 = "#52B788"

COLUMNAS_RESUMEN = {
    "hora",
    "temp_promedio",
    "temp_maxima",
    "humedad_promedio",
    "activaciones",
}


def resumen_grafico_seguro(df_resumen: pd.DataFrame) -> pd.DataFrame:
    """Valida el esquema agregado antes de que un gráfico acceda a columnas."""
    if df_resumen.empty:
        return pd.DataFrame(columns=sorted(COLUMNAS_RESUMEN))
    faltantes = COLUMNAS_RESUMEN.difference(df_resumen.columns)
    if faltantes:
        raise ValueError(
            "El resumen horario no tiene las columnas requeridas: "
            + ", ".join(sorted(faltantes))
        )
    return df_resumen


def aplicar_estilo_base(fig: plt.Figure, ax: plt.Axes) -> None:
    """Aplica formato oscuro corporativo al gráfico."""
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(PANEL_COLOR)
    ax.tick_params(colors=MUTED_TEXT, labelsize=8.5)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TEXT_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.3, color="#374151")


def generar_grafico_tendencia(df: pd.DataFrame) -> plt.Figure:
    """Muestra temperatura, humedad y umbrales a través del tiempo."""
    figura, eje = plt.subplots(figsize=(10, 3.8), dpi=150)
    aplicar_estilo_base(figura, eje)
    if df.empty:
        eje.text(0.5, 0.5, "Sin datos para analizar", ha="center", va="center", color=TEXT_COLOR)
    else:
        trabajo = df.sort_values("fecha_hora")
        eje.plot(trabajo["fecha_hora"], trabajo["temperatura"], color=COLOR_M2, label="Temperatura °C")
        eje.plot(trabajo["fecha_hora"], trabajo["humedad"], color=COLOR_PEAK, label="Humedad %")
        eje.set_title("Tendencia ambiental")
        eje.legend(facecolor=PANEL_COLOR, labelcolor=TEXT_COLOR)
        figura.autofmt_xdate()
    figura.tight_layout()
    return figura


def generar_grafico_barras_separadas(df_resumen: pd.DataFrame) -> plt.Figure:
    """Genera barras separadas de activaciones por hora."""
    figura, eje = plt.subplots(figsize=(7, 3.6), dpi=200)
    aplicar_estilo_base(figura, eje)
    df_resumen = resumen_grafico_seguro(df_resumen)
    if df_resumen.empty:
        eje.text(0.5, 0.5, "Sin datos para analizar", ha="center", va="center", color=TEXT_COLOR)
    else:
        activaciones = df_resumen["activaciones"]
        maximo = activaciones.max()
        colores = [COLOR_MAX if valor == maximo and valor > 0 else COLOR_ACT for valor in activaciones]
        barras = eje.bar(df_resumen["hora"], activaciones, color=colores, width=0.45, edgecolor="none", alpha=0.9, zorder=3)
        for barra in barras:
            altura = barra.get_height()
            if altura > 0:
                eje.annotate(
                    f"{int(altura)}", xy=(barra.get_x() + barra.get_width() / 2, altura),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    color=TEXT_COLOR, fontsize=7.5, fontweight="bold",
                )
    eje.set_xticks(range(0, 24, 2))
    eje.set_xlabel("Horario del Día (00:00 - 23:00 h)", fontsize=9, fontweight="bold", labelpad=8)
    eje.set_ylabel("N° de Activaciones (Relés)", fontsize=9, fontweight="bold")
    eje.set_title("Barras Separadas: Activaciones de Ventilación", fontsize=11, fontweight="bold", pad=12, loc="left")
    figura.tight_layout()
    return figura


def generar_grafico_barras_agrupadas(df_resumen: pd.DataFrame) -> plt.Figure:
    """Compara temperatura promedio y máxima en franjas pares."""
    figura, eje = plt.subplots(figsize=(7, 3.6), dpi=200)
    aplicar_estilo_base(figura, eje)
    df_resumen = resumen_grafico_seguro(df_resumen)
    filtrado = df_resumen[df_resumen["hora"] % 2 == 0].copy() if not df_resumen.empty else df_resumen
    if filtrado.empty:
        eje.text(0.5, 0.5, "Sin datos para analizar", ha="center", va="center", color=TEXT_COLOR)
    else:
        posiciones = np.arange(len(filtrado))
        ancho = 0.35
        eje.bar(posiciones - ancho / 2, filtrado["temp_promedio"], ancho, label="Temp. Promedio", color=COLOR_PROM, alpha=0.9, zorder=3)
        eje.bar(posiciones + ancho / 2, filtrado["temp_maxima"], ancho, label="Temp. Máxima", color=COLOR_MAX, alpha=0.9, zorder=3)
        eje.set_xticks(posiciones)
        eje.set_xticklabels([f"{hora:02d}:00" for hora in filtrado["hora"]], fontsize=8)
        eje.legend(loc="upper left", frameon=True, facecolor=PANEL_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, fontsize=8)
    eje.set_xlabel("Franja Horaria Muestreada", fontsize=9, fontweight="bold", labelpad=8)
    eje.set_ylabel("Temperatura (°C)", fontsize=9, fontweight="bold")
    eje.set_title("Barras Agrupadas: Temp. Promedio vs. Temp. Máxima", fontsize=11, fontweight="bold", pad=12, loc="left")
    figura.tight_layout()
    return figura


def generar_grafico_circular(df: pd.DataFrame) -> plt.Figure:
    """Genera un gráfico circular tradicional de distribución de estados."""
    figura, eje = plt.subplots(figsize=(5.8, 3.4), dpi=200)
    conteo = df["estado"].value_counts() if not df.empty else pd.Series(dtype=int)
    colores = {
        "OPTIMO": "#10B981", "ENFRIAMIENTO": "#F59E0B",
        "EXTRACCION_HUMEDAD": "#06B6D4", "RIESGO_CRITICO": "#EF4444",
        "ALERTA_BAJA": "#3B82F6", "ALERTA_TEMP_BAJA": "#3B82F6",
        "ALERTA_HUMEDAD_BAJA": "#6366F1",
    }
    if conteo.empty:
        eje.text(0.5, 0.5, "Sin datos para analizar", ha="center", va="center", color=TEXT_COLOR)
    else:
        _, _, textos = eje.pie(
            conteo.values,
            labels=conteo.index,
            autopct="%1.1f%%",
            colors=[colores.get(estado, "#6B7280") for estado in conteo.index],
            startangle=140,
            wedgeprops={"edgecolor": BG_COLOR, "linewidth": 1.5},
            textprops={"color": TEXT_COLOR, "fontsize": 8, "fontweight": "bold"},
        )
        for texto in textos:
            texto.set_color("#FFFFFF")
            texto.set_weight("bold")
    eje.set_title("Gráfico Circular: Distribución General de Estados", color=TEXT_COLOR, fontsize=11, fontweight="bold", pad=12)
    figura.patch.set_facecolor(BG_COLOR)
    eje.set_facecolor(BG_COLOR)
    figura.tight_layout()
    return figura


def generar_grafico_montana(df_resumen: pd.DataFrame) -> plt.Figure:
    """Genera un gráfico de área multicapa con métricas horarias reales."""
    figura, eje = plt.subplots(figsize=(10, 5), dpi=200)
    figura.patch.set_facecolor(BG_COLOR)
    eje.set_facecolor(PANEL_COLOR)

    df_resumen = resumen_grafico_seguro(df_resumen)
    if df_resumen.empty:
        eje.text(0.5, 0.5, "Sin datos para analizar", ha="center", va="center", color=TEXT_COLOR)
    else:
        horas = df_resumen["hora"].to_numpy()
        temperatura = df_resumen["temp_promedio"].to_numpy()
        humedad = df_resumen["humedad_promedio"].to_numpy()
        activaciones = df_resumen["activaciones"].to_numpy()
        # Se normalizan las series para comparar magnitudes distintas en una sola área.
        series = (
            ("Pico Térmico", temperatura, COLOR_M1, 0.35, 2.0),
            ("Cresta de Humedad", humedad, COLOR_M2, 0.45, 2.0),
            ("Flujo de Ventilación", activaciones, COLOR_M3, 0.60, 2.2),
        )
        maximos = [float(serie[1].max()) for serie in series]
        escala = max(maximos) or 1.0
        for nombre, valores, color, transparencia, ancho in series:
            valores_escalados = valores / escala * 10
            eje.fill_between(
                horas, valores_escalados, color=color, alpha=transparencia, label=nombre
            )
            eje.plot(horas, valores_escalados, color=color, linewidth=ancho)
        eje.set_xticks(range(0, 24, 2))
        eje.set_ylabel("Magnitud normalizada", fontsize=9.5, fontweight="bold", labelpad=10)

    eje.tick_params(colors=MUTED_TEXT, labelsize=9)
    eje.xaxis.label.set_color(TEXT_COLOR)
    eje.yaxis.label.set_color(TEXT_COLOR)
    eje.spines["top"].set_visible(False)
    eje.spines["right"].set_visible(False)
    eje.spines["left"].set_color(GRID_COLOR)
    eje.spines["bottom"].set_color(GRID_COLOR)
    eje.grid(True, linestyle="--", linewidth=0.5, alpha=0.3, color="#374151")
    eje.set_xlabel("Tiempo / Muestreo (Horas)", fontsize=9.5, fontweight="bold", labelpad=10)
    eje.set_title(
        "Gráfico Estilo Montaña: Intensidad Operativa",
        fontsize=12, fontweight="bold", pad=15, loc="left", color=TEXT_COLOR,
    )
    if not df_resumen.empty:
        eje.legend(
            loc="upper right", frameon=True, facecolor=PANEL_COLOR,
            edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, fontsize=8.5,
        )
    figura.tight_layout()
    return figura


# Compatibilidad con versiones previas del dashboard.
generar_grafico_activaciones = generar_grafico_barras_separadas
generar_grafico_distribucion_estados = generar_grafico_circular
grafico_tendencia_temporal = generar_grafico_tendencia
grafico_activaciones_horario = generar_grafico_barras_separadas
grafico_distribucion_estados = generar_grafico_circular
