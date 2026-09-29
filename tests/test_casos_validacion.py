"""Casos de aceptación del motor de decisiones y persistencia."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import datos
from datos import cargar_configuracion, guardar_registro_csv
from logica import evaluar_estado_silo
from validaciones import validar_lecturas_silo


class CasosDeValidacionTest(unittest.TestCase):
    """Verifica la matriz funcional entregada para el proyecto."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = cargar_configuracion()

    def assert_estado(
        self, temperatura: float, humedad: float, grano: str, esperado: str
    ) -> None:
        valido, mensaje = validar_lecturas_silo(
            temperatura, humedad, self.config
        )
        self.assertTrue(valido, mensaje)
        evaluacion = evaluar_estado_silo(
            temperatura, humedad, grano, self.config
        )
        self.assertEqual(evaluacion["estado"], esperado)

    def test_limite_exacto_arroz_es_optimo(self) -> None:
        self.assert_estado(25.0, 65.0, "arroz", "OPTIMO")

    def test_exceso_temperatura_arroz_activa_rele_uno(self) -> None:
        self.assert_estado(26.5, 50.0, "arroz", "ENFRIAMIENTO")
        evaluacion = evaluar_estado_silo(26.5, 50.0, "arroz", self.config)
        self.assertEqual(evaluacion["accion"], "Activar Relé 1")

    def test_exceso_humedad_frijol_activa_rele_dos(self) -> None:
        self.assert_estado(20.0, 64.0, "frijol", "EXTRACCION_HUMEDAD")
        evaluacion = evaluar_estado_silo(20.0, 64.0, "frijol", self.config)
        self.assertEqual(evaluacion["accion"], "Activar Relé 2")

    def test_caso_critico_activa_ambos_reles(self) -> None:
        self.assert_estado(28.0, 70.0, "arroz", "RIESGO_CRITICO")
        evaluacion = evaluar_estado_silo(28.0, 70.0, "arroz", self.config)
        self.assertEqual(evaluacion["accion"], "Activar Relés 1 y 2")

    def test_entrada_invalida_no_se_guarda(self) -> None:
        with tempfile.TemporaryDirectory() as directorio:
            csv_temporal = Path(directorio) / "registros.csv"
            with patch.object(datos, "CSV_PATH", csv_temporal):
                valido, _ = validar_lecturas_silo(
                    "temperatura inválida", 50.0, self.config
                )
                self.assertFalse(valido)
                if valido:
                    guardar_registro_csv(
                        "temperatura inválida",
                        50.0,
                        "arroz",
                        {"estado": "OPTIMO", "accion": "Ninguna", "observacion": ""},
                    )
                self.assertFalse(csv_temporal.exists())

    def test_valores_no_finitos_son_invalidos(self) -> None:
        self.assertFalse(validar_lecturas_silo(float("nan"), 50.0, self.config)[0])
        self.assertFalse(validar_lecturas_silo(20.0, float("inf"), self.config)[0])


if __name__ == "__main__":
    unittest.main()
