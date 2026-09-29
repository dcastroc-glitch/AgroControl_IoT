"""Dashboard Streamlit oscuro para el monitoreo de silos."""

from __future__ import annotations

import random
from html import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from analisis import analizar_picos_por_horario, calcular_metricas_generales
from datos import cargar_configuracion, cargar_historial_csv, guardar_registro_csv
from graficos import (
    generar_grafico_barras_agrupadas,
    generar_grafico_barras_separadas,
    generar_grafico_circular,
    generar_grafico_montana,
)
from logica import evaluar_estado_silo
from validaciones import validar_lecturas_silo


def reproducir_sonido_alarma() -> None:
    """Emite tres tonos de alarma en el navegador mediante Web Audio API."""
    components.html(
        """
        <script>
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            const audioCtx = new AudioContext();
            function emitirBeep(frecuencia, duracion, retraso) {
                setTimeout(() => {
                    const osc = audioCtx.createOscillator();
                    const gain = audioCtx.createGain();
                    osc.type = "sawtooth";
                    osc.frequency.setValueAtTime(frecuencia, audioCtx.currentTime);
                    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
                    osc.connect(gain);
                    gain.connect(audioCtx.destination);
                    osc.start();
                    osc.stop(audioCtx.currentTime + duracion / 1000);
                }, retraso);
            }
            emitirBeep(880, 150, 0);
            emitirBeep(660, 150, 200);
            emitirBeep(880, 250, 400);
        }
        </script>
        """,
        height=0,
        width=0,
    )


st.set_page_config(page_title="AgroControl IoT - Monitoreo de Silos", page_icon="🌾", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background-color: #0E1117; color: #E6EDF3; }
    .main-header, .card-capture { background: #161B22; border: 1px solid #30363D;
        border-radius: 12px; padding: 20px; margin-bottom: 20px;
        box-shadow: 0 4px 18px rgba(0,0,0,.35); }
    .main-header { background: linear-gradient(90deg,#1E2640,#0F172A); }
    .status-card { padding: 15px; border-radius: 8px; }
    .status-optimo { background: rgba(16,185,129,.14); border-left: 6px solid #10B981; color: #A7F3D0; }
    .status-warning { background: rgba(245,158,11,.14); border-left: 6px solid #F59E0B; color: #FDE68A; }
    .status-danger { background: rgba(239,68,68,.15); border-left: 6px solid #EF4444; color: #FCA5A5;
        animation: pulse-alert 1.5s infinite; }
    @keyframes pulse-alert {
        0%, 100% { box-shadow: 0 0 4px rgba(239,68,68,.25); }
        50% { box-shadow: 0 0 20px rgba(239,68,68,.75); }
    }
    .history-card { background: #161B22; border: 1px solid #30363D;
        border-left: 5px solid #64748B; border-radius: 10px; padding: 14px 18px;
        margin: 0 0 12px 0; box-shadow: 0 3px 12px rgba(0,0,0,.24); }
    .history-card-success { border-left-color: #10B981; }
    .history-card-info { border-left-color: #3B82F6; }
    .history-card-warning { border-left-color: #F59E0B; }
    .history-card-danger { border-left-color: #EF4444; animation: pulse-alert 1.5s infinite; }
    .history-header { display: flex; justify-content: space-between; gap: 12px;
        align-items: center; color: #94A3B8; font-size: .85rem; margin-bottom: 9px; }
    .history-time { color: #E6EDF3; font-weight: 700; }
    .history-badge { border-radius: 999px; padding: 4px 10px; font-weight: 700;
        white-space: nowrap; }
    .badge-success { background: rgba(16,185,129,.18); color: #6EE7B7; }
    .badge-info { background: rgba(59,130,246,.18); color: #93C5FD; }
    .badge-warning { background: rgba(245,158,11,.18); color: #FCD34D; }
    .badge-danger { background: rgba(239,68,68,.18); color: #FCA5A5; }
    .history-title { color: #F8FAFC; font-size: 1.02rem; font-weight: 700; margin-bottom: 5px; }
    .history-detail { color: #CBD5E1; margin: 3px 0; }
    .history-code { color: #67E8F9; font-family: monospace; }
    @media (max-width: 700px) {
        .history-header { align-items: flex-start; flex-direction: column; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="main-header"><h1 style="color:#38BDF8;margin:0">🌾 AgroControl IoT</h1>'
    '<p style="color:#94A3B8">Monitoreo ambiental y control de ventilación en silos '
    '(Raspberry Pi + SHT31)</p></div>',
    unsafe_allow_html=True,
)

config = cargar_configuracion()
with st.sidebar:
    st.header("⚙️ Parámetros de Operación")
    grano = st.selectbox("Seleccione Tipo de Grano", ["Arroz", "Frijol"])
    umbral = config.get("granos", {}).get(grano.lower(), {"temp_max": 25, "humedad_max": 65})
    st.caption(f"Temperatura máxima: {umbral['temp_max']} °C")
    st.caption(f"Humedad máxima: {umbral['humedad_max']} %")

tab_control, tab_historial, tab_analitica, tab_info = st.tabs(
    ["🎛️ Panel de Control", "📜 Historial", "📊 Analítica", "ℹ️ Especificaciones"]
)

with tab_control:
    izquierda, derecha = st.columns([1, 1.3])
    with izquierda:
        st.markdown('<div class="card-capture">', unsafe_allow_html=True)
        st.subheader("🤖 Adquisición Automática")
        if st.button("⚡ Lectura Instantánea de Sensor", use_container_width=True):
            st.session_state["temp_input"] = round(random.uniform(18, 32), 1)
            st.session_state["humedad_input"] = round(random.uniform(45, 75), 1)
        st.session_state.setdefault("temp_input", 24.0)
        st.session_state.setdefault("humedad_input", 55.0)
        st.metric("Última Temperatura Capturada", f"{st.session_state['temp_input']} °C")
        st.metric("Última Humedad Capturada", f"{st.session_state['humedad_input']} %")
        st.markdown("</div>", unsafe_allow_html=True)
    with derecha:
        st.markdown('<div class="card-capture">', unsafe_allow_html=True)
        st.subheader("📝 Confirmación y Registro")
        temperatura = st.number_input("Temperatura medida (°C)", value=float(st.session_state["temp_input"]), step=0.1)
        humedad = st.number_input("Humedad relativa medida (%)", value=float(st.session_state["humedad_input"]), step=0.1)
        if st.button("💾 Guardar Registro en CSV", type="primary", use_container_width=True):
            valido, mensaje = validar_lecturas_silo(temperatura, humedad, config)
            if not valido:
                st.error(f"❌ Error de validación: {mensaje}")
            else:
                evaluacion = evaluar_estado_silo(temperatura, humedad, grano, config)
                guardar_registro_csv(temperatura, humedad, grano, evaluacion)
                reles_activos = "Relé" in evaluacion["accion"] or "Relés" in evaluacion["accion"]
                if reles_activos:
                    reproducir_sonido_alarma()
                    st.toast(
                        f"🚨 ¡ACTIVACIÓN DE ACTUADORES DETECTADA! -> {evaluacion['accion']}",
                        icon="🔊",
                    )
                clase = "status-optimo" if evaluacion["estado"] == "OPTIMO" else (
                    "status-danger" if evaluacion["estado"] == "RIESGO_CRITICO" else "status-warning"
                )
                st.success("✅ Registro almacenado exitosamente.")
                st.markdown(
                    f'<div class="status-card {clase}"><b>{evaluacion["estado"]}</b><br>'
                    f'{evaluacion["accion"]}<br>{evaluacion["observacion"]}</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

with tab_historial:
    st.header("📜 Historial de Mediciones")
    historial = cargar_historial_csv()
    granos = st.multiselect("Filtrar por grano", ["Arroz", "Frijol"], default=["Arroz", "Frijol"])
    estados = st.multiselect("Filtrar por estado", sorted(historial["estado"].unique()), default=sorted(historial["estado"].unique()))
    filtrado = historial[historial["grano"].isin(granos) & historial["estado"].isin(estados)]
    st.caption(f"{len(filtrado)} registro(s) coinciden con los filtros seleccionados.")

    nombres_estado = {
        "OPTIMO": ("🟢", "ÓPTIMO", "success"),
        "ENFRIAMIENTO": ("🔵", "ENFRIAMIENTO", "info"),
        "EXTRACCION_HUMEDAD": ("🔵", "EXTRACCIÓN DE HUMEDAD", "info"),
        "ALERTA_BAJA": ("🟡", "ALERTA DE LÍMITES INFERIORES", "warning"),
        "RIESGO_CRITICO": ("🔴", "RIESGO CRÍTICO", "danger"),
    }
    for indice, registro in filtrado.sort_values("fecha_hora", ascending=False).iterrows():
        fecha = pd.to_datetime(registro["fecha_hora"]).strftime("%d %b %Y · %H:%M")
        estado = str(registro["estado"])
        icono, etiqueta, severidad = nombres_estado.get(
            estado, ("🔵", estado.replace("_", " "), "info")
        )
        log_id = f"LOG-{indice + 1:04d}"
        grano_registro = escape(str(registro["grano"]))
        accion = escape(str(registro["accion"]))
        observacion = escape(str(registro["observacion"]))
        temperatura = f"{float(registro['temperatura']):.1f} °C"
        humedad = f"{float(registro['humedad']):.1f} %"
        st.markdown(
            f"""
            <article class="history-card history-card-{severidad}">
                <div class="history-header">
                    <span class="history-time">🕒 {fecha}</span>
                    <span class="history-code">#{log_id}</span>
                    <span class="history-badge badge-{severidad}">{icono} {etiqueta}</span>
                </div>
                <div class="history-title">Lectura del silo · {grano_registro}</div>
                <div class="history-detail">
                    🌡️ <span class="history-code">{temperatura}</span>
                    &nbsp; 💧 <span class="history-code">{humedad}</span>
                </div>
                <div class="history-detail"><strong>Acción:</strong> {accion}</div>
                <div class="history-detail"><strong>Detalle:</strong> {observacion}</div>
            </article>
            """,
            unsafe_allow_html=True,
        )

with tab_analitica:
    st.markdown("## 📊 Diagnóstico Operacional y Analítica de Silo")
    historial = cargar_historial_csv()
    metricas = calcular_metricas_generales(historial)
    if not metricas:
        st.warning("⚠️ Aún no existen registros para analizar.")
    else:
        st.markdown("### 🎯 Indicadores Clave de Rendimiento")
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        tarjetas = [
            ("ESTABILIDAD", f"{metricas['porcentaje_estabilidad']}%", "Tiempo en Óptimo", "#00FF66"),
            ("TEMP. PROMEDIO", f"{metricas['temp_promedio']}°C", f"Máx: {metricas['temp_maxima']}°C", "#FF2A6D"),
            ("HUMEDAD PROM.", f"{metricas['humedad_promedio']}%", f"Máx: {metricas['humedad_maxima']}%", "#00E5FF"),
            ("HORA CRÍTICA", metricas["hora_pico_calor"], "Pico Máximo Térmico", "#FFB703"),
            ("ACTIVACIONES", str(metricas["activaciones_totales"]), "Eventos de Ventilación", "#D8B4FE"),
        ]
        for columna, (titulo, valor, detalle, color) in zip((kpi1, kpi2, kpi3, kpi4, kpi5), tarjetas):
            with columna:
                st.markdown(
                    f'<div class="card-capture" style="border-left:4px solid {color};text-align:center;padding:12px">'
                    f'<p style="color:#8E9AAF;margin:0;font-size:.8rem;font-weight:bold">{titulo}</p>'
                    f'<h3 style="color:{color};margin:4px 0">{valor}</h3>'
                    f'<p style="color:#E6EDF3;margin:0;font-size:.75rem">{detalle}</p></div>',
                    unsafe_allow_html=True,
                )
        resumen = analizar_picos_por_horario(historial)
        st.markdown("---")
        st.subheader("1. Comparativa de Temperaturas (Barras Agrupadas)")
        st.pyplot(generar_grafico_barras_agrupadas(resumen), clear_figure=True)
        st.markdown("---")
        izquierda, derecha = st.columns(2)
        with izquierda:
            st.subheader("2. Frecuencia de Ventilación (Barras Separadas)")
            st.pyplot(generar_grafico_barras_separadas(resumen), clear_figure=True)
        with derecha:
            st.subheader("3. Porcentaje de Estados (Gráfico Circular)")
            st.pyplot(generar_grafico_circular(historial), clear_figure=True)
        st.markdown("---")
        st.subheader("4. Intensidad Operativa (Gráfico de Área)")
        st.pyplot(generar_grafico_montana(resumen), clear_figure=True)

with tab_info:
    st.header("ℹ️ Arquitectura del Sistema")
    st.markdown(
        "- **Hardware:** Raspberry Pi 4, SHT31 y módulo relé doble de 5 V.\n"
        "- **Visualización:** dashboard oscuro industrial con gráficos DPI 150.\n"
        "- **Persistencia:** historial CSV y configuración JSON."
    )
