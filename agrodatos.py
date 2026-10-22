"""Persistencia y cálculos del módulo de gestión agrícola."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from datos import DB_PATH, inicializar_base_datos

KG_POR_QUINTAL = 46.0
CULTIVOS = ("Café", "Frijol", "Maíz", "Arroz")


def inicializar_datos_agricolas() -> None:
    """Crea tablas agrícolas y datos de catálogo mínimos, sin datos financieros."""
    inicializar_base_datos()
    with sqlite3.connect(DB_PATH) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS parcelas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                hectareas REAL NOT NULL CHECK(hectareas > 0),
                ubicacion TEXT NOT NULL DEFAULT '',
                activa INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS cultivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                parcela_id INTEGER NOT NULL REFERENCES parcelas(id),
                temporada TEXT NOT NULL,
                humedad_min REAL NOT NULL DEFAULT 35,
                humedad_max REAL NOT NULL DEFAULT 70,
                UNIQUE(nombre, parcela_id, temporada)
            );
            CREATE TABLE IF NOT EXISTS suelo_lecturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora TEXT NOT NULL,
                parcela_id INTEGER NOT NULL REFERENCES parcelas(id),
                humedad REAL NOT NULL CHECK(humedad >= 0 AND humedad <= 100),
                fuente TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL, categoria TEXT NOT NULL, concepto TEXT NOT NULL,
                monto_crc REAL NOT NULL CHECK(monto_crc >= 0), parcela_id INTEGER,
                cultivo TEXT NOT NULL DEFAULT '', proveedor TEXT NOT NULL DEFAULT '',
                notas TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS cosechas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL, cultivo TEXT NOT NULL, parcela_id INTEGER,
                cantidad_kg REAL NOT NULL CHECK(cantidad_kg > 0),
                calidad TEXT NOT NULL DEFAULT '', destino TEXT NOT NULL DEFAULT '',
                costo_crc REAL NOT NULL DEFAULT 0 CHECK(costo_crc >= 0)
            );
            CREATE TABLE IF NOT EXISTS inventario_movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL, cultivo TEXT NOT NULL, tipo TEXT NOT NULL,
                cantidad_kg REAL NOT NULL CHECK(cantidad_kg > 0),
                referencia TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL, cultivo TEXT NOT NULL, cliente TEXT NOT NULL,
                cantidad_kg REAL NOT NULL CHECK(cantidad_kg > 0),
                precio_kg_crc REAL NOT NULL CHECK(precio_kg_crc >= 0),
                estado_pago TEXT NOT NULL DEFAULT 'Pendiente'
            );
            """
        )


def listar_parcelas() -> pd.DataFrame:
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        return pd.read_sql_query("SELECT * FROM parcelas WHERE activa=1 ORDER BY nombre", db)


def crear_parcela(nombre: str, hectareas: float, ubicacion: str) -> None:
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO parcelas(nombre, hectareas, ubicacion) VALUES(?,?,?)",
                   (nombre.strip(), hectareas, ubicacion.strip()))


def listar_cultivos() -> pd.DataFrame:
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        return pd.read_sql_query(
            """SELECT c.*, p.nombre parcela FROM cultivos c
               JOIN parcelas p ON p.id=c.parcela_id ORDER BY p.nombre,c.nombre""", db
        )


def crear_cultivo(nombre: str, parcela_id: int, temporada: str, humedad_min: float, humedad_max: float) -> None:
    if nombre not in CULTIVOS:
        raise ValueError("Cultivo no permitido.")
    if not 0 <= humedad_min < humedad_max <= 100:
        raise ValueError("El rango de humedad debe estar entre 0 y 100.")
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """INSERT INTO cultivos(nombre,parcela_id,temporada,humedad_min,humedad_max)
               VALUES(?,?,?,?,?)""",
            (nombre, parcela_id, temporada.strip(), humedad_min, humedad_max),
        )


def registrar_humedad_suelo(parcela_id: int, humedad: float, fuente: str = "simulado") -> None:
    if not 0 <= humedad <= 100:
        raise ValueError("La humedad del suelo debe estar entre 0 y 100 %.")
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO suelo_lecturas(fecha_hora,parcela_id,humedad,fuente) VALUES(?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), parcela_id, humedad, fuente),
        )


def resumen_suelo() -> pd.DataFrame:
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        return pd.read_sql_query(
            """SELECT p.nombre parcela, c.nombre cultivo, c.humedad_min, c.humedad_max,
                      (SELECT s.humedad FROM suelo_lecturas s WHERE s.parcela_id=p.id
                       ORDER BY s.id DESC LIMIT 1) humedad_actual
               FROM parcelas p JOIN cultivos c ON c.parcela_id=p.id WHERE p.activa=1""", db
        )


def registrar_gasto(fecha: str, categoria: str, concepto: str, monto_crc: float,
                    parcela_id: int | None, cultivo: str, proveedor: str, notas: str) -> None:
    if monto_crc < 0:
        raise ValueError("El gasto no puede ser negativo.")
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """INSERT INTO gastos(fecha,categoria,concepto,monto_crc,parcela_id,cultivo,proveedor,notas)
               VALUES(?,?,?,?,?,?,?,?)""",
            (fecha, categoria, concepto.strip(), monto_crc, parcela_id, cultivo, proveedor.strip(), notas.strip()),
        )


def registrar_cosecha(fecha: str, cultivo: str, parcela_id: int | None, cantidad_kg: float,
                      calidad: str, destino: str, costo_crc: float) -> None:
    if cantidad_kg <= 0 or costo_crc < 0:
        raise ValueError("Cantidad y costo de cosecha no son válidos.")
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO cosechas(fecha,cultivo,parcela_id,cantidad_kg,calidad,destino,costo_crc) VALUES(?,?,?,?,?,?,?)",
            (fecha, cultivo, parcela_id, cantidad_kg, calidad, destino, costo_crc),
        )
        db.execute(
            "INSERT INTO inventario_movimientos(fecha,cultivo,tipo,cantidad_kg,referencia) VALUES(?,?,?,?,?)",
            (fecha, cultivo, "Entrada", cantidad_kg, "Cosecha"),
        )


def registrar_venta(fecha: str, cultivo: str, cliente: str, cantidad_kg: float,
                    precio_kg_crc: float, estado_pago: str) -> None:
    if cantidad_kg <= 0 or precio_kg_crc < 0:
        raise ValueError("Cantidad o precio de venta no válido.")
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        disponible = db.execute(
            """SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad_kg ELSE -cantidad_kg END),0)
               FROM inventario_movimientos WHERE cultivo=?""", (cultivo,)
        ).fetchone()[0]
        if cantidad_kg > disponible:
            raise ValueError(f"Inventario insuficiente: quedan {disponible:.1f} kg.")
        db.execute(
            "INSERT INTO ventas(fecha,cultivo,cliente,cantidad_kg,precio_kg_crc,estado_pago) VALUES(?,?,?,?,?,?)",
            (fecha, cultivo, cliente.strip(), cantidad_kg, precio_kg_crc, estado_pago),
        )
        db.execute(
            "INSERT INTO inventario_movimientos(fecha,cultivo,tipo,cantidad_kg,referencia) VALUES(?,?,?,?,?)",
            (fecha, cultivo, "Salida", cantidad_kg, "Venta"),
        )


def resumen_financiero() -> dict[str, float]:
    inicializar_datos_agricolas()
    with sqlite3.connect(DB_PATH) as db:
        gastos = db.execute("SELECT COALESCE(SUM(monto_crc),0) FROM gastos").fetchone()[0]
        ingresos = db.execute("SELECT COALESCE(SUM(cantidad_kg*precio_kg_crc),0) FROM ventas").fetchone()[0]
        inventario = db.execute(
            """SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad_kg ELSE -cantidad_kg END),0)
               FROM inventario_movimientos"""
        ).fetchone()[0]
    return {"gastos": float(gastos), "ingresos": float(ingresos),
            "margen": float(ingresos - gastos), "inventario_kg": float(inventario),
            "inventario_quintales": float(inventario / KG_POR_QUINTAL)}
