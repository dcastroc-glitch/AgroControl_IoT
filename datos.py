import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import pandas as pd

# Rutas absolutas del proyecto
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "configuracion.json"
CSV_PATH = BASE_DIR / "data" / "registros.csv"
DB_PATH = BASE_DIR / "data" / "agrocontrol.db"

CONFIG_POR_DEFECTO: Dict[str, Any] = {
    "temp_min_fisica": 15.0,
    "temp_max_fisica": 40.0,
    "humedad_min_fisica": 40.0,
    "humedad_max_fisica": 90.0,
    "granos": {
        "arroz": {"temp_min": 18.0, "temp_max": 25.0, "humedad_min": 50.0, "humedad_max": 65.0},
        "frijol": {"temp_min": 18.0, "temp_max": 22.0, "humedad_min": 50.0, "humedad_max": 60.0},
    },
}

COLUMNAS = [
    "fecha_hora",
    "temperatura",
    "humedad",
    "grano",
    "estado",
    "accion",
    "observacion",
]


def guardar_configuracion(configuracion: Dict[str, Any]) -> None:
    """Guarda la configuración en el archivo JSON."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as archivo:
        json.dump(configuracion, archivo, indent=4, ensure_ascii=False)


def validar_configuracion(configuracion: Dict[str, Any]) -> tuple[bool, str]:
    """Comprueba límites físicos, umbrales y parámetros antes de persistirlos."""
    try:
        fisica = (
            float(configuracion["temp_min_fisica"]),
            float(configuracion["temp_max_fisica"]),
            float(configuracion["humedad_min_fisica"]),
            float(configuracion["humedad_max_fisica"]),
        )
        if fisica[0] >= fisica[1] or fisica[2] >= fisica[3]:
            return False, "Los límites físicos mínimos deben ser menores que los máximos."
        for nombre, valores in configuracion["granos"].items():
            minimo_temp = float(valores["temp_min"])
            maximo_temp = float(valores["temp_max"])
            minimo_humedad = float(valores["humedad_min"])
            maximo_humedad = float(valores["humedad_max"])
            if not minimo_temp < maximo_temp or not minimo_humedad < maximo_humedad:
                return False, f"Los umbrales de {nombre} tienen un orden inválido."
            if not fisica[0] <= minimo_temp <= maximo_temp <= fisica[1]:
                return False, f"La temperatura de {nombre} queda fuera del rango físico."
            if not fisica[2] <= minimo_humedad <= maximo_humedad <= fisica[3]:
                return False, f"La humedad de {nombre} queda fuera del rango físico."
        intervalo = int(configuracion.get("intervalo_actualizacion", 2))
        if not 0 <= intervalo <= 60:
            return False, "El intervalo debe estar entre 0 y 60 segundos."
    except (KeyError, TypeError, ValueError):
        return False, "La configuración contiene valores incompletos o no numéricos."
    return True, "Configuración válida."


def inicializar_base_datos() -> None:
    """Crea el almacenamiento SQLite sin alterar el CSV histórico."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """CREATE TABLE IF NOT EXISTS mediciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT NOT NULL,
                temperatura REAL NOT NULL, humedad REAL NOT NULL, grano TEXT NOT NULL,
                estado TEXT NOT NULL, accion TEXT NOT NULL, observacion TEXT NOT NULL
            )"""
        )
        conexion.execute(
            """CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT NOT NULL,
                tipo TEXT NOT NULL, detalle TEXT NOT NULL
            )"""
        )


def registrar_evento(tipo: str, detalle: str) -> None:
    """Registra eventos operativos para diagnóstico y auditoría."""
    inicializar_base_datos()
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            "INSERT INTO eventos(fecha_hora,tipo,detalle) VALUES(datetime('now','localtime'), ?, ?)",
            (tipo, detalle),
        )


def _migrar_csv_si_vacio() -> None:
    inicializar_base_datos()
    with sqlite3.connect(DB_PATH) as conexion:
        cantidad = conexion.execute("SELECT COUNT(*) FROM mediciones").fetchone()[0]
        if cantidad or not CSV_PATH.exists():
            return
        historico = pd.read_csv(CSV_PATH)
        for fila in historico.to_dict("records"):
            conexion.execute(
                """INSERT INTO mediciones(fecha_hora,temperatura,humedad,grano,estado,accion,observacion)
                VALUES(?,?,?,?,?,?,?)""",
                tuple(fila[columna] for columna in COLUMNAS),
            )


def cargar_configuracion() -> Dict[str, Any]:
    """Carga el JSON de configuración y crea uno válido si no existe."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        guardar_configuracion(CONFIG_POR_DEFECTO)

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as archivo:
            configuracion = json.load(archivo)
        if not isinstance(configuracion, dict):
            raise ValueError("La configuración debe ser un objeto JSON.")
        return configuracion
    except (OSError, json.JSONDecodeError, ValueError):
        guardar_configuracion(CONFIG_POR_DEFECTO)
        return CONFIG_POR_DEFECTO


def generar_datos_semilla() -> None:
    """Genera 120 registros sintéticos separados por intervalos de 10 minutos."""
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = cargar_configuracion()

    registros = []
    fecha_base = datetime.now() - timedelta(minutes=120 * 10)
    granos = ["Arroz", "Frijol"]

    for i in range(120):
        fecha_hora = fecha_base + timedelta(minutes=i * 10)
        grano = random.choice(granos)

        hora = fecha_hora.hour
        if 11 <= hora <= 16:
            temp = round(random.uniform(24.0, 32.0), 1)
            humedad = round(random.uniform(58.0, 75.0), 1)
        else:
            temp = round(random.uniform(18.0, 24.5), 1)
            humedad = round(random.uniform(45.0, 62.0), 1)

        grano_key = grano.lower()
        umbrales = config.get("granos", {}).get(
            grano_key, {"temp_max": 25.0, "humedad_max": 65.0}
        )
        temp_min = float(umbrales.get("temp_min", 18.0))
        temp_max = float(umbrales.get("temp_max", 25.0))
        humedad_min = float(umbrales.get("humedad_min", 50.0))
        humedad_max = float(umbrales.get("humedad_max", 65.0))

        temp_alta = temp > temp_max
        temp_baja = temp < temp_min
        humedad_alta = humedad > humedad_max
        humedad_baja = humedad < humedad_min

        if temp_alta and humedad_alta:
            estado = "RIESGO_CRITICO"
            accion = "Activar Relés 1 y 2 (Emergencia)"
            obs = f"Exceso de temperatura (> {temp_max}°C) y humedad (> {humedad_max}%)."
        elif temp_alta:
            estado = "ENFRIAMIENTO"
            accion = "Activar Relé 1 (Ventilador)"
            obs = f"Temperatura excede {temp_max}°C."
        elif humedad_alta:
            estado = "EXTRACCION_HUMEDAD"
            accion = "Activar Relé 2 (Extractor)"
            obs = f"Humedad excede {humedad_max}%."
        elif temp_baja or humedad_baja:
            estado = "ALERTA_BAJA"
            accion = "Monitoreo de Límites Inferiores"
            obs = "Lecturas por debajo del rango óptimo."
        else:
            estado = "OPTIMO"
            accion = "Ninguna"
            obs = "Condiciones seguras."

        registros.append(
            {
                "fecha_hora": fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
                "temperatura": temp,
                "humedad": humedad,
                "grano": grano,
                "estado": estado,
                "accion": accion,
                "observacion": obs,
            }
        )

    df = pd.DataFrame(registros, columns=COLUMNAS)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")


def guardar_registro_csv(
    temp: float, humedad: float, grano: str, evaluacion: Dict[str, Any]
) -> None:
    """Guarda un nuevo registro de medición en el archivo CSV."""
    inicializar_base_datos()
    _migrar_csv_si_vacio()

    nuevo_registro = {
        "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "temperatura": float(temp),
        "humedad": float(humedad),
        "grano": grano,
        "estado": evaluacion["estado"],
        "accion": evaluacion["accion"],
        "observacion": evaluacion["observacion"],
    }

    df_nuevo = pd.DataFrame([nuevo_registro], columns=COLUMNAS)
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """INSERT INTO mediciones(fecha_hora,temperatura,humedad,grano,estado,accion,observacion)
            VALUES(?,?,?,?,?,?,?)""",
            tuple(nuevo_registro[columna] for columna in COLUMNAS),
        )
    df_nuevo.to_csv(CSV_PATH, mode="a", header=not CSV_PATH.exists(), index=False, encoding="utf-8")


def cargar_historial_csv() -> pd.DataFrame:
    """Carga el historial persistente desde el CSV como DataFrame de Pandas."""
    try:
        _migrar_csv_si_vacio()
        with sqlite3.connect(DB_PATH) as conexion:
            df = pd.read_sql_query(
                "SELECT fecha_hora,temperatura,humedad,grano,estado,accion,observacion "
                "FROM mediciones ORDER BY fecha_hora",
                conexion,
            )
        if df.empty:
            generar_datos_semilla()
            _migrar_csv_si_vacio()
            with sqlite3.connect(DB_PATH) as conexion:
                df = pd.read_sql_query("SELECT * FROM mediciones ORDER BY fecha_hora", conexion)
        df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
        return df
    except (OSError, sqlite3.Error, pd.errors.ParserError, KeyError, ValueError):
        generar_datos_semilla()
        _migrar_csv_si_vacio()
        with sqlite3.connect(DB_PATH) as conexion:
            df = pd.read_sql_query("SELECT * FROM mediciones ORDER BY fecha_hora", conexion)
        df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
        return df


def exportar_historial_csv(df: pd.DataFrame) -> bytes:
    """Devuelve el historial filtrado listo para descarga."""
    return df.to_csv(index=False).encode("utf-8")
