"""Adquisición de lecturas; el perfil local usa un sensor simulado seguro."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Lectura:
    temperatura: float
    humedad: float
    fecha_hora: datetime
    fuente: str


def leer_sensor(simulado: bool = True) -> Lectura:
    """Obtiene una lectura simulada; deja un punto único para integrar SHT31."""
    if not simulado:
        raise RuntimeError("El sensor SHT31 no está habilitado en el perfil local.")
    return Lectura(
        round(random.uniform(18.0, 32.0), 1),
        round(random.uniform(45.0, 78.0), 1),
        datetime.now(),
        "simulado",
    )
