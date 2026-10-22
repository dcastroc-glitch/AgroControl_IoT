"""Control seguro de actuadores con implementación simulada."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EstadoActuadores:
    rele_1: bool = False
    rele_2: bool = False


class ActuadoresSimulados:
    """Representa relés sin accionar GPIO en equipos de desarrollo."""

    def __init__(self) -> None:
        self.estado = EstadoActuadores()

    def aplicar(self, evaluacion: dict[str, str]) -> EstadoActuadores:
        estado = evaluacion["estado"]
        self.estado.rele_1 = estado in {"ENFRIAMIENTO", "RIESGO_CRITICO"}
        self.estado.rele_2 = estado in {"EXTRACCION_HUMEDAD", "RIESGO_CRITICO"}
        return self.estado

    def apagar(self) -> None:
        self.estado = EstadoActuadores()
