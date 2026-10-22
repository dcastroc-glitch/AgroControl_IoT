"""Reglas de decisión para ventilación y extracción del silo."""

from __future__ import annotations

from typing import Any, Mapping


def evaluar_estado_silo(
    temp: Any, humedad: Any, grano: str, config: Mapping[str, Any]
) -> dict[str, str]:
    """Evalúa umbrales del grano y devuelve estado, acción y observación."""
    try:
        temperatura = float(temp)
        porcentaje = float(humedad)
    except (TypeError, ValueError) as exc:
        raise ValueError("Temperatura y humedad deben ser numéricas.") from exc

    clave_grano = str(grano).strip().lower()
    granos = config.get("granos", {})
    if clave_grano not in granos:
        raise ValueError("El grano debe ser 'arroz' o 'frijol'.")

    umbrales = granos[clave_grano]
    temp_min = float(umbrales.get("temp_min", config.get("temp_min_fisica", 15)))
    temp_max = float(umbrales["temp_max"])
    humedad_min = float(umbrales.get("humedad_min", config.get("humedad_min_fisica", 40)))
    humedad_max = float(umbrales["humedad_max"])
    supera_temperatura = temperatura > temp_max
    supera_humedad = porcentaje > humedad_max
    baja_temperatura = temperatura < temp_min
    baja_humedad = porcentaje < humedad_min

    if supera_temperatura and supera_humedad:
        estado = "RIESGO_CRITICO"
        accion = "Activar Relés 1 y 2"
        observacion = "Temperatura y humedad superan los umbrales del grano."
    elif supera_temperatura:
        estado = "ENFRIAMIENTO"
        accion = "Activar Relé 1"
        observacion = "La temperatura supera el umbral del grano."
    elif supera_humedad:
        estado = "EXTRACCION_HUMEDAD"
        accion = "Activar Relé 2"
        observacion = "La humedad supera el umbral del grano."
    elif baja_temperatura or baja_humedad:
        estado = "ALERTA_BAJA"
        accion = "Monitoreo de límites inferiores"
        observacion = "Una lectura está por debajo del rango óptimo."
    else:
        estado = "OPTIMO"
        accion = "Ninguna"
        observacion = "Las condiciones se encuentran dentro de los umbrales."

    return {"estado": estado, "accion": accion, "observacion": observacion}
