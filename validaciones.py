"""Validaciones de lecturas obtenidas del sensor SHT31."""

from __future__ import annotations

import math
from typing import Any, Mapping


def validar_lecturas_silo(
    temp: Any, humedad: Any, config: Mapping[str, Any]
) -> tuple[bool, str]:
    """Valida tipos y rangos físicos de una lectura del silo."""
    try:
        temperatura = float(temp)
        porcentaje = float(humedad)
    except (TypeError, ValueError):
        return False, "Temperatura y humedad deben ser valores numéricos."
    if not math.isfinite(temperatura) or not math.isfinite(porcentaje):
        return False, "Temperatura y humedad deben ser valores finitos."

    limites = (
        ("temperatura", temperatura, "temp_min_fisica", "temp_max_fisica", "°C"),
        (
            "humedad",
            porcentaje,
            "humedad_min_fisica",
            "humedad_max_fisica",
            "%",
        ),
    )
    for nombre, valor, minimo_key, maximo_key, unidad in limites:
        try:
            minimo = float(config[minimo_key])
            maximo = float(config[maximo_key])
        except (KeyError, TypeError, ValueError):
            return False, f"Configuración incompleta para {nombre}."
        if not minimo <= valor <= maximo:
            return (
                False,
                f"La {nombre} debe estar entre {minimo:g} y {maximo:g} {unidad}.",
            )
    return True, "Lectura válida."
