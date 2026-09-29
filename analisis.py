"""Métricas operativas y agregaciones horarias del historial del silo."""

from __future__ import annotations

from typing import Any

import pandas as pd


def calcular_metricas_generales(df: pd.DataFrame) -> dict[str, Any]:
    """Calcula KPIs de estabilidad, riesgo, activaciones y temperatura pico."""
    if df.empty:
        return {}

    trabajo = df.copy()
    trabajo["fecha_hora"] = pd.to_datetime(trabajo["fecha_hora"], errors="coerce")
    trabajo = trabajo.dropna(subset=["fecha_hora"])
    total = len(trabajo)
    estados = trabajo["estado"].fillna("").astype(str)
    optimos = int((estados == "OPTIMO").sum())
    activaciones = int(
        estados.isin(
            ["ENFRIAMIENTO", "EXTRACCION_HUMEDAD", "RIESGO_CRITICO"]
        ).sum()
    )
    criticos = int((estados == "RIESGO_CRITICO").sum())
    resumen_horas = trabajo.assign(hora=trabajo["fecha_hora"].dt.hour)
    promedios = resumen_horas.groupby("hora")["temperatura"].mean()
    hora_pico = int(promedios.idxmax()) if not promedios.empty else 0

    temp_promedio = round(float(trabajo["temperatura"].mean()), 1)
    temp_maxima = round(float(trabajo["temperatura"].max()), 1)
    humedad_promedio = round(float(trabajo["humedad"].mean()), 1)
    humedad_maxima = round(float(trabajo["humedad"].max()), 1)
    estabilidad = round((optimos / total) * 100, 1) if total else 0.0

    return {
        "total_registros": total,
        "temp_promedio": temp_promedio,
        "temp_maxima": temp_maxima,
        "humedad_promedio": humedad_promedio,
        "humedad_maxima": humedad_maxima,
        "porcentaje_estabilidad": estabilidad,
        "activaciones_totales": activaciones,
        "eventos_criticos": criticos,
        "hora_pico_calor": f"{hora_pico:02d}:00 h",
        # Alias del dashboard anterior.
        "temperatura_promedio": temp_promedio,
        "temperatura_maxima": temp_maxima,
        "humedad_promedio": humedad_promedio,
        "humedad_maxima": humedad_maxima,
        "activaciones_reles": activaciones,
    }


def analizar_picos_por_horario(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa las mediciones por hora para evaluar tendencias y activaciones."""
    columnas = [
        "hora",
        "temp_promedio",
        "humedad_promedio",
        "activaciones",
        "temperatura_promedio",
        "activaciones_reles",
    ]
    if df.empty:
        return pd.DataFrame(columns=columnas)

    trabajo = df.copy()
    trabajo["fecha_hora"] = pd.to_datetime(trabajo["fecha_hora"], errors="coerce")
    trabajo = trabajo.dropna(subset=["fecha_hora"])
    trabajo["hora"] = trabajo["fecha_hora"].dt.hour
    trabajo["es_activacion"] = trabajo["estado"].isin(
        ["ENFRIAMIENTO", "EXTRACCION_HUMEDAD", "RIESGO_CRITICO"]
    ).astype(int)
    resumen = (
        trabajo.groupby("hora")
        .agg(
            temp_promedio=("temperatura", "mean"),
            temp_maxima=("temperatura", "max"),
            humedad_promedio=("humedad", "mean"),
            activaciones=("es_activacion", "sum"),
        )
        .reset_index()
        .sort_values("hora")
    )
    resumen["temperatura_promedio"] = resumen["temp_promedio"]
    resumen["activaciones_reles"] = resumen["activaciones"]
    return resumen
