"""Pruebas del flujo agrícola de parcelas, inventario y finanzas."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import agrodatos


class DatosAgricolasTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directorio = TemporaryDirectory()
        agrodatos.DB_PATH = Path(self.directorio.name) / "test.db"
        agrodatos.inicializar_datos_agricolas()
        agrodatos.crear_parcela("Lote Norte", 1.5, "Arriba")
        self.parcela_id = int(agrodatos.listar_parcelas().iloc[0]["id"])

    def tearDown(self) -> None:
        self.directorio.cleanup()

    def test_humedad_suelo_y_cosecha_actualizan_inventario(self) -> None:
        agrodatos.crear_cultivo("Maíz", self.parcela_id, "2026", 35, 70)
        agrodatos.registrar_humedad_suelo(self.parcela_id, 25)
        agrodatos.registrar_cosecha("2026-01-01", "Maíz", self.parcela_id, 92, "Primera", "Almacén", 500)
        self.assertEqual(agrodatos.resumen_financiero()["inventario_kg"], 92)

    def test_venta_no_supera_inventario(self) -> None:
        agrodatos.registrar_cosecha("2026-01-01", "Café", self.parcela_id, 10, "Primera", "Almacén", 0)
        with self.assertRaises(ValueError):
            agrodatos.registrar_venta("2026-01-02", "Café", "Cliente", 11, 20, "Pendiente")

    def test_gasto_y_venta_calculan_margen(self) -> None:
        agrodatos.registrar_gasto("2026-01-01", "Semillas", "Compra", 1000, self.parcela_id, "Frijol", "", "")
        agrodatos.registrar_cosecha("2026-01-02", "Frijol", self.parcela_id, 20, "Primera", "Almacén", 0)
        agrodatos.registrar_venta("2026-01-03", "Frijol", "Cliente", 10, 200, "Pagado")
        self.assertEqual(agrodatos.resumen_financiero()["margen"], 1000)


if __name__ == "__main__":
    unittest.main()
