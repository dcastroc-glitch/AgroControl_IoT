"""Dashboard Streamlit de monitoreo de silos con identidad verde/tierra."""

from __future__ import annotations

import os
import sqlite3
from datetime import date
from html import escape

import pandas as pd
import streamlit as st

from actuadores import ActuadoresSimulados
from alertas import enviar_alerta_email
from auth import usuarios_por_defecto, verify_password
from datos import (
    cargar_configuracion,
    cargar_historial_csv,
    exportar_historial_csv,
    guardar_configuracion,
    guardar_registro_csv,
    registrar_evento,
    validar_configuracion,
)
from graficos import generar_grafico_barras_agrupadas, generar_grafico_circular, generar_grafico_tendencia
from logica import evaluar_estado_silo
from sensor import leer_sensor
from validaciones import validar_lecturas_silo
from analisis import analizar_picos_por_horario, calcular_metricas_generales
from agrodatos import (
    CULTIVOS,
    crear_cultivo,
    crear_parcela,
    listar_cultivos,
    listar_parcelas,
    registrar_cosecha,
    registrar_gasto,
    registrar_humedad_suelo,
    registrar_venta,
    resumen_financiero,
    resumen_suelo,
)


st.set_page_config(page_title="AgroControl IoT", page_icon="🌱", layout="wide")
st.markdown(
    """<style>
    .stApp { background:#edf5ec !important; color:#19352a !important; }
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div { color:#19352a; }
    [data-testid="stAppViewContainer"], [data-testid="stMainBlockContainer"] {
      background:#edf5ec !important; }
    [data-testid="stHeader"] { background:rgba(237,245,236,.9) !important; }
    .login-page { min-height:78vh; display:flex; align-items:center; justify-content:center;
      padding:24px 16px; background:
      linear-gradient(135deg,rgba(235,247,232,.96),rgba(250,252,247,.98)),
      radial-gradient(circle at 14% 20%,#b9dfbb,transparent 34%); }
    .login-layout { width:min(430px,100%); position:relative; padding:1px;
      border-radius:24px; background:linear-gradient(145deg,#d7ead6,#fff,#b9d9bc);
      box-shadow:0 24px 55px rgba(27,78,43,.18); }
    .login-form-panel { position:relative; overflow:hidden; border-radius:23px; padding:34px 38px 28px;
      background:rgba(255,255,255,.97); }
    .login-form-panel:before { content:""; position:absolute; width:220px; height:220px;
      top:-135px; right:-85px; border-radius:50%; background:#e7f5e4; }
    .login-form-panel:after { content:""; position:absolute; width:150px; height:150px;
      bottom:-105px; left:-75px; border-radius:50%; background:#f0f8ed; }
    .st-key-login-shell { width:100%; max-width:430px; margin:0 auto; }
    .st-key-login-shell [data-testid="stForm"] { width:100%; max-width:360px;
      margin:0 auto; border:0 !important; padding:0 !important; }
    .login-card { position:relative; z-index:1; }
    .brand-content { text-align:center; }
    .brand-mark { width:58px; height:58px; margin:0 auto 15px; display:grid; place-items:center;
      border-radius:18px; background:linear-gradient(145deg,#e4f4e1,#c4e4c6);
      border:1px solid #b5d8b7; font-size:1.8rem; box-shadow:0 8px 18px rgba(42,105,57,.14); }
    .brand-kicker { margin:0 0 8px; color:#3d8b52; font-size:.66rem;
      font-weight:800; letter-spacing:.16em; text-transform:uppercase; }
    .brand-title { color:#173f2a; font-size:1.72rem; line-height:1.1;
      letter-spacing:-.045em; margin:0; font-weight:800; }
    .brand-copy { max-width:310px; margin:12px auto 0; color:#708775;
      font-size:.82rem; line-height:1.5; }
    .brand-pills { display:flex; justify-content:center; flex-wrap:wrap; gap:6px; margin-top:18px; }
    .brand-pill { padding:5px 8px; border-radius:999px; color:#3c7450;
      background:#eef7eb; border:1px solid #d7e9d5; font-size:.63rem; }
    .brand-footer { margin-top:24px; color:#8aa18c; font-size:.66rem; text-align:center; }
    [data-testid="stSidebar"] { background:linear-gradient(180deg,#123c28,#1d5c3a) !important;
      border-right:1px solid #2f7650; }
    [data-testid="stSidebar"] * { color:#f0f8ee !important; }
    [data-testid="stSidebar"] [data-testid="stAlert"] { background:#286844; border:1px solid #4b9966; }
    [data-testid="stSidebar"] [data-testid="stSlider"] div { color:#f0f8ee !important; }
    h1,h2,h3 { color:#174f31 !important; letter-spacing:-.025em; }
    .dashboard-hero { position:relative; overflow:hidden; display:flex; justify-content:space-between;
      align-items:flex-end; gap:18px; padding:26px 30px; margin:0 0 20px; border-radius:18px;
      color:#f5fff2; background:linear-gradient(115deg,#123c28,#246b43 58%,#438c5b);
      box-shadow:0 10px 24px rgba(24,79,44,.16); }
    .dashboard-hero:after { content:""; position:absolute; width:260px; height:260px; right:-80px;
      top:-145px; border:1px solid rgba(255,255,255,.16); border-radius:50%;
      box-shadow:0 0 0 25px rgba(255,255,255,.04),0 0 0 50px rgba(255,255,255,.03); }
    .dashboard-hero > * { position:relative; z-index:1; }
    .stApp .dashboard-kicker { color:#bfe9c3 !important; font-size:.7rem; font-weight:800; letter-spacing:.16em;
      text-transform:uppercase; margin-bottom:5px; }
    .stApp .dashboard-title { color:#fff !important; font-size:2rem !important; font-weight:800; margin:0; }
    .stApp .dashboard-subtitle { color:#d2efd3 !important; margin:5px 0 0; font-size:.88rem; }
    .stApp .live-badge { color:#eaffdf !important; border:1px solid rgba(216,255,213,.35); background:#ffffff18;
      border-radius:999px; padding:8px 12px; font-size:.75rem; font-weight:700; white-space:nowrap; }
    .section-label { color:#4c7658; font-size:.68rem; font-weight:800; letter-spacing:.13em;
      text-transform:uppercase; margin:5px 0 10px; }
    .kpi-card { background:#fff; border:1px solid #d5e6d3; border-radius:14px; padding:16px;
      min-height:104px; box-shadow:0 5px 14px rgba(35,91,49,.08); }
    .stApp .kpi-label { color:#78917b !important; font-size:.62rem !important; font-weight:800; letter-spacing:.06em; text-transform:uppercase; white-space:nowrap; }
    .stApp .kpi-value { color:#174f31 !important; font-size:1.05rem !important; font-weight:800; margin-top:8px; white-space:nowrap; }
    .stApp .kpi-detail { color:#78917b !important; font-size:.68rem !important; margin-top:3px; }
    .stTabs [data-baseweb="tab-list"] { gap:4px; border-bottom:1px solid #cbdcca; }
    .stTabs [data-baseweb="tab"] { color:#52745a !important; border-radius:8px 8px 0 0;
      padding:10px 14px; font-weight:700; }
    .stTabs [aria-selected="true"] { color:#1d6a3d !important; background:#e0f0dd;
      border-bottom:3px solid #3d9a5e; }
    .stMultiSelect [data-baseweb="select"], .stSelectbox [data-baseweb="select"],
    .stMultiSelect [data-baseweb="select"] > div, .stDateInput input,
    .stSelectbox [data-baseweb="select"] > div { background:#fff !important; color:#19352a !important;
      border:1px solid #bdd5be !important; border-radius:9px !important; }
    .stMultiSelect [data-baseweb="select"] *, .stSelectbox [data-baseweb="select"] *,
    .stMultiSelect input, .stSelectbox input, .stDateInput input { color:#19352a !important; }
    .stMultiSelect [data-baseweb="tag"] { background:#3d8b52 !important; color:#fff !important; }
    .stButton button, .stDownloadButton button { border:1px solid #71a678 !important;
      background:#fff !important; color:#205b36 !important; border-radius:9px !important;
      font-weight:700 !important; }
    .stButton button:hover, .stDownloadButton button:hover { background:#e1f1df !important;
      border-color:#3d8b52 !important; color:#174f31 !important; }
    [data-testid="stSidebar"] .stButton button { background:#286844 !important;
      color:#f0f8ee !important; border-color:#73ad7d !important; }
    [data-testid="stSidebar"] .stButton button:hover { background:#3d8b52 !important; color:#fff !important; }
    .stAlert { border-radius:10px !important; }
    .login-eyebrow { color:#3d8b52; font-size:.66rem; font-weight:800; letter-spacing:.14em;
      text-transform:uppercase; margin:26px 0 5px; text-align:center; }
    .login-card h1 { color:#173f2a; font-size:1.5rem; letter-spacing:-.04em; margin:0 0 5px; text-align:center; }
    .login-card > p { color:#6a8270; margin:0 0 20px; line-height:1.45; font-size:.82rem; text-align:center; }
    .st-key-login-shell label,
    .st-key-login-shell label p,
    .st-key-login-shell [data-testid="stTextInput"] label span,
    .st-key-login-shell [data-testid="stTextInput"] label p {
      color:#173f2a !important; font-weight:800 !important; font-size:.9rem !important;
      letter-spacing:.01em; text-shadow:none !important; opacity:1 !important;
    }
    .st-key-login-shell [data-testid="stTextInput"] { margin-bottom:14px; }
    .st-key-login-shell [data-testid="stTextInput"] label { margin-bottom:6px; }
    .st-key-login-shell [data-testid="stTextInputRootElement"] { height:48px; gap:0;
      background:linear-gradient(145deg,#ffffff,#f3f9f2) !important;
      border:1px solid #c8ddc9 !important; border-radius:12px !important;
      box-shadow:inset 0 1px 2px rgba(22,72,40,.05),0 3px 8px rgba(37,91,52,.07);
      transition:border-color .2s,box-shadow .2s,transform .2s; }
    .st-key-login-shell [data-testid="stTextInputRootElement"]:hover {
      border-color:#79ae80 !important; box-shadow:0 5px 14px rgba(37,91,52,.12); }
    .st-key-login-shell [data-testid="stTextInputRootElement"]:focus-within {
      border-color:#3d9a5e !important; outline:3px solid rgba(61,154,94,.14);
      box-shadow:0 6px 16px rgba(40,122,73,.16); transform:translateY(-1px); }
    .st-key-login-shell input { height:46px !important; background:transparent !important;
      color:#19352a !important; border:0 !important; font-size:.9rem !important;
      padding:0 14px !important; }
    .st-key-login-shell input::placeholder { color:#91a494 !important; opacity:1; }
    .st-key-login-shell input:-webkit-autofill { -webkit-text-fill-color:#19352a !important;
      -webkit-box-shadow:0 0 0 1000px #f7fbf6 inset !important; }
    .st-key-login-shell [data-testid="stTextInputRootElement"] button {
      color:#4f8060 !important; margin-right:7px; border-radius:8px; }
    .st-key-login-shell [data-testid="stTextInputRootElement"] button:hover {
      background:#e4f1e3 !important; color:#1d5c3a !important; }
    .st-key-login-shell [data-testid="stFormSubmitButton"] { margin-top:8px; }
    .st-key-login-shell [data-testid="stFormSubmitButton"] button { background:linear-gradient(100deg,#287a49,#3d9a5e);
      color:white; border:1px solid #267344; border-radius:12px; font-weight:750; min-height:48px;
      letter-spacing:.01em; box-shadow:0 7px 0 #1d5c3a,0 12px 22px rgba(40,122,73,.2);
      transition:transform .16s,box-shadow .16s,filter .16s; }
    .st-key-login-shell [data-testid="stFormSubmitButton"] button:hover { background:#1d5c3a;
      filter:brightness(1.05); transform:translateY(-2px); box-shadow:0 9px 0 #174c2e,0 15px 25px rgba(40,122,73,.28); }
    .st-key-login-shell [data-testid="stFormSubmitButton"] button:active {
      transform:translateY(3px); box-shadow:0 3px 0 #174c2e,0 7px 12px rgba(40,122,73,.18); }
    .st-key-login-shell [data-testid="stForm"] { border:0 !important; padding:0 !important; }
    .login-note { color:#8aa18c; font-size:.7rem; text-align:center; margin-top:14px; }
    @media (max-width:520px) {
      .login-page { min-height:82vh; padding:14px 10px; }
      .login-form-panel { padding:28px 22px 22px; }
    }
    .hero { background:linear-gradient(135deg,#155d3a,#3d8b52); padding:25px;
      border-radius:16px; color:white; margin-bottom:18px; }
    .hero h1 { color:#f4ffe9; margin:0; }
    .card { background:white; border-left:6px solid #4f9d69; border-radius:12px;
      padding:16px; box-shadow:0 2px 12px #265d351c; margin-bottom:12px; }
    .ok { border-left-color:#2e8b57; } .warn { border-left-color:#d99b25; }
    .danger { border-left-color:#c64747; }
    @media (max-width:760px) {
      .dashboard-hero { align-items:flex-start; flex-direction:column; padding:20px; }
      .dashboard-title { font-size:1.55rem; }
    }
    </style>""",
    unsafe_allow_html=True,
)


def iniciar_sesion() -> bool:
    if st.session_state.get("usuario"):
        return True
    with st.container(key="login-shell"):
        st.markdown(
            '<div class="login-page"><div class="login-layout">'
            '<section class="login-form-panel"><div class="login-card"><div class="brand-content">'
            '<div class="brand-mark">🌱</div>'
            '<div class="brand-kicker">Control agrícola inteligente</div>'
            '<h1 class="brand-title">Cuida el grano.<br>Protege la cosecha.</h1>'
            '<p class="brand-copy">Visualiza el ambiente de tus silos y toma decisiones a tiempo con datos claros, alertas y control operativo.</p>'
            '<div class="brand-pills"><span class="brand-pill">● Monitoreo ambiental</span><span class="brand-pill">⌁ Alertas inteligentes</span><span class="brand-pill">⌂ Control de silo</span></div>'
            '</div><div class="brand-footer">AgroControl IoT · Tecnología para una cosecha segura</div>'
            '<div class="login-eyebrow">Bienvenido de nuevo</div>'
            '<h1>Inicia sesión</h1>'
            '<p>Accede a tu centro de monitoreo y revisa el estado de tus silos.</p>',
            unsafe_allow_html=True,
        )
        with st.form("login", border=False):
            usuario = st.text_input("Usuario", placeholder="Escribe tu usuario")
            password = st.text_input("Contraseña", type="password", placeholder="Escribe tu contraseña")
            acceder = st.form_submit_button("Entrar al sistema", use_container_width=True)
        st.markdown(
            '<div class="login-note">🔒 Panel protegido · Acceso local seguro</div></div></div></section></div></div>',
            unsafe_allow_html=True,
        )
    if acceder:
        usuarios = st.session_state.setdefault("usuarios", usuarios_por_defecto())
        registro = usuarios.get(usuario)
        if registro and verify_password(password, registro["password"]):
            st.session_state["usuario"] = usuario
            st.session_state["rol"] = registro["rol"]
            st.rerun()
        st.error("Usuario o contraseña incorrectos.")
    st.caption("Perfil local inicial: operador / agrocontrol. Cámbialo antes de desplegar.")
    return False


if not iniciar_sesion():
    st.stop()

config = cargar_configuracion()
actuadores = st.session_state.setdefault("actuadores", ActuadoresSimulados())
with st.sidebar:
    st.header("🌿 Control")
    st.success(f"Sesión: {st.session_state['usuario']} ({st.session_state['rol']})")
    grano = st.selectbox("Tipo de grano", ["Arroz", "Frijol"])
    intervalo = st.slider("Actualización (s)", 0, 30, int(config.get("intervalo_actualizacion", 2)))
    if st.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

st.markdown(
    '<div class="dashboard-hero"><div><div class="dashboard-kicker" style="color:#bfe9c3 !important">Centro de operaciones · Silo principal</div>'
    '<div class="dashboard-title" style="color:#ffffff !important">🌱 AgroControl IoT</div>'
    '<div class="dashboard-subtitle" style="color:#d2efd3 !important">Monitoreo ambiental y protección inteligente de tu cosecha</div></div>'
    '<div class="live-badge" style="color:#eaffdf !important">● SISTEMA EN LÍNEA</div></div>',
    unsafe_allow_html=True,
)

@st.fragment(run_every=f"{intervalo}s" if intervalo else None)
def panel_en_vivo() -> None:
    st.markdown('<div class="section-label">Monitoreo en tiempo real</div>', unsafe_allow_html=True)
    lectura = leer_sensor(simulado=True)
    evaluacion = evaluar_estado_silo(lectura.temperatura, lectura.humedad, grano, config)
    estado_reles = actuadores.aplicar(evaluacion)
    clase = "ok" if evaluacion["estado"] == "OPTIMO" else "danger" if evaluacion["estado"] == "RIESGO_CRITICO" else "warn"
    tarjetas = [
        ("TEMPERATURA", f"{lectura.temperatura:.1f} °C", "Lectura SHT31 simulada"),
        ("HUMEDAD RELATIVA", f"{lectura.humedad:.1f} %", "Ambiente del silo"),
        ("ESTADO DEL SILO", evaluacion["estado"], "Evaluación automática"),
        ("VENTILACIÓN", "ACTIVA" if estado_reles.rele_1 else "EN ESPERA", "Relé 1 · Enfriamiento"),
        ("EXTRACCIÓN", "ACTIVA" if estado_reles.rele_2 else "EN ESPERA", "Relé 2 · Humedad"),
    ]
    for columnas, fila in ((st.columns(3), tarjetas[:3]), (st.columns(2), tarjetas[3:])):
        for columna, (titulo, valor, detalle) in zip(columnas, fila):
            columna.markdown(
                f'<div class="kpi-card"><div class="kpi-label" style="color:#78917b !important">{titulo}</div>'
                f'<div class="kpi-value" style="color:#174f31 !important">{valor}</div>'
                f'<div class="kpi-detail" style="color:#78917b !important">{detalle}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown(f'<div class="card {clase}"><b>{evaluacion["accion"]}</b><br>{evaluacion["observacion"]}<br><small>Fuente: {lectura.fuente} · {lectura.fecha_hora:%d/%m/%Y %H:%M:%S}</small></div>', unsafe_allow_html=True)
    if st.button("Guardar lectura actual", key="guardar_vivo"):
        valido, mensaje = validar_lecturas_silo(lectura.temperatura, lectura.humedad, config)
        if valido:
            guardar_registro_csv(lectura.temperatura, lectura.humedad, grano, evaluacion)
            registrar_evento("medicion", f"{grano}: {evaluacion['estado']}")
            if evaluacion["estado"] == "RIESGO_CRITICO":
                clave_alerta = f"{grano}:{evaluacion['estado']}"
                if st.session_state.get("ultima_alerta") != clave_alerta:
                    enviado, detalle = enviar_alerta_email("AgroControl: riesgo crítico", evaluacion["observacion"])
                    registrar_evento("alerta_email", detalle)
                    st.session_state["ultima_alerta"] = clave_alerta
            st.success("Lectura guardada.")
        else:
            st.error(mensaje)


panel_en_vivo()
tab_resumen, tab_suelo, tab_finanzas, tab_historial, tab_analitica, tab_admin = st.tabs(
    ["🏡 Finca", "💧 Suelo y riego", "💰 Finanzas", "📜 Historial", "📊 Analítica", "⚙️ Administración"]
)

with tab_resumen:
    st.markdown('<div class="section-label">Control general de la finca</div>', unsafe_allow_html=True)
    finanzas = resumen_financiero()
    k1, k2, k3, k4 = st.columns(4)
    for col, titulo, valor in (
        (k1, "Gastos acumulados", f"₡{finanzas['gastos']:,.0f}"),
        (k2, "Ingresos registrados", f"₡{finanzas['ingresos']:,.0f}"),
        (k3, "Margen estimado", f"₡{finanzas['margen']:,.0f}"),
        (k4, "Inventario", f"{finanzas['inventario_kg']:,.1f} kg"),
    ):
        col.metric(titulo, valor)
    suelo = resumen_suelo()
    st.subheader("Estado de parcelas")
    if suelo.empty:
        st.info("Registra una parcela y un cultivo desde Administración para comenzar.")
    else:
        suelo["estado"] = suelo.apply(
            lambda fila: "SECO" if pd.isna(fila["humedad_actual"]) or fila["humedad_actual"] < fila["humedad_min"]
            else "HÚMEDO" if fila["humedad_actual"] > fila["humedad_max"] else "ÓPTIMO", axis=1
        )
        st.dataframe(suelo[["parcela", "cultivo", "humedad_actual", "humedad_min", "humedad_max", "estado"]],
                     use_container_width=True, hide_index=True)

with tab_suelo:
    st.markdown('<div class="section-label">Humedad del suelo y riego</div>', unsafe_allow_html=True)
    parcelas = listar_parcelas()
    if parcelas.empty:
        st.warning("Primero crea una parcela desde Administración.")
    else:
        parcela_nombre = st.selectbox("Parcela", parcelas["nombre"].tolist(), key="suelo_parcela")
        parcela_id = int(parcelas.loc[parcelas["nombre"] == parcela_nombre, "id"].iloc[0])
        humedad = st.slider("Lectura simulada de humedad del suelo (%)", 0, 100, 45, 1)
        estado = "SECO · recomendar riego" if humedad < 35 else "HÚMEDO · revisar drenaje" if humedad > 70 else "ÓPTIMO"
        st.info(f"Estado actual: **{estado}**")
        if st.button("Registrar lectura de suelo", type="primary"):
            registrar_humedad_suelo(parcela_id, humedad)
            st.success("Lectura de suelo registrada.")
        st.caption("Modo simulado: el adaptador está preparado para reemplazarse por un sensor físico.")

with tab_finanzas:
    st.markdown('<div class="section-label">Gastos, cosechas e ingresos</div>', unsafe_allow_html=True)
    finanzas = resumen_financiero()
    st.metric("Margen estimado", f"₡{finanzas['margen']:,.0f}")
    opcion = st.radio("Registrar", ["Gasto", "Cosecha", "Venta"], horizontal=True)
    if opcion == "Gasto":
        with st.form("form_gasto"):
            categoria = st.selectbox("Categoría", ["Semillas", "Fertilizante", "Riego", "Mano de obra", "Transporte", "Otro"])
            concepto = st.text_input("Concepto")
            monto = st.number_input("Monto (CRC)", min_value=0.0, step=1000.0)
            cultivo_gasto = st.selectbox("Cultivo", ["General", *CULTIVOS])
            guardar_gasto = st.form_submit_button("Guardar gasto")
        if guardar_gasto:
            registrar_gasto(str(date.today()), categoria, concepto, monto, None, cultivo_gasto, "", "")
            st.success("Gasto registrado en colones.")
    elif opcion == "Cosecha":
        with st.form("form_cosecha"):
            cultivo_cosecha = st.selectbox("Cultivo", list(CULTIVOS))
            cantidad = st.number_input("Cantidad (kg)", min_value=0.1, step=1.0)
            costo = st.number_input("Costo de cosecha (CRC)", min_value=0.0, step=1000.0)
            calidad = st.text_input("Calidad", "Primera")
            guardar_cosecha = st.form_submit_button("Registrar cosecha")
        if guardar_cosecha:
            registrar_cosecha(str(date.today()), cultivo_cosecha, None, cantidad, calidad, "Almacén", costo)
            st.success(f"Cosecha registrada: {cantidad / 46:.2f} quintales.")
    else:
        with st.form("form_venta"):
            cultivo_venta = st.selectbox("Cultivo", list(CULTIVOS))
            cliente = st.text_input("Cliente")
            cantidad_venta = st.number_input("Cantidad (kg)", min_value=0.1, step=1.0)
            precio = st.number_input("Precio por kg (CRC)", min_value=0.0, step=10.0)
            estado_pago = st.selectbox("Estado de pago", ["Pendiente", "Pagado", "Parcial"])
            guardar_venta = st.form_submit_button("Registrar venta")
        if guardar_venta:
            try:
                registrar_venta(str(date.today()), cultivo_venta, cliente, cantidad_venta, precio, estado_pago)
                st.success("Venta registrada y descontada del inventario.")
            except ValueError as exc:
                st.error(str(exc))

with tab_historial:
    historial = cargar_historial_csv()
    st.markdown('<div class="section-label">Trazabilidad y registros</div>', unsafe_allow_html=True)
    st.subheader("Historial de mediciones")
    granos = st.multiselect("Granos", ["Arroz", "Frijol"], default=["Arroz", "Frijol"])
    estados_disponibles = sorted(historial["estado"].dropna().unique())
    estados = st.multiselect("Estados", estados_disponibles, default=estados_disponibles)
    desde = st.date_input("Desde", value=historial["fecha_hora"].min().date())
    hasta = st.date_input("Hasta", value=historial["fecha_hora"].max().date())
    filtrado = historial[
        historial["grano"].isin(granos)
        & historial["estado"].isin(estados)
        & (historial["fecha_hora"].dt.date >= desde)
        & (historial["fecha_hora"].dt.date <= hasta)
    ]
    st.caption(f"{len(filtrado)} registro(s)")
    st.download_button("⬇️ Exportar CSV", exportar_historial_csv(filtrado), "agrocontrol_historial.csv", "text/csv")
    if filtrado.empty:
        st.info("No hay registros que coincidan con los filtros.")
    else:
        for _, fila in filtrado.sort_values("fecha_hora", ascending=False).head(100).iterrows():
            st.markdown(f'<div class="card"><b>{fila["fecha_hora"]:%d/%m/%Y %H:%M} · {escape(str(fila["grano"]))}</b><br>🌡️ {fila["temperatura"]:.1f} °C · 💧 {fila["humedad"]:.1f} % · <b>{escape(str(fila["estado"]))}</b><br>{escape(str(fila["observacion"]))}</div>', unsafe_allow_html=True)

with tab_analitica:
    historial = cargar_historial_csv()
    metricas = calcular_metricas_generales(historial)
    if not metricas:
        st.info("Aún no existen registros para analizar.")
    else:
        st.markdown('<div class="section-label">Indicadores de rendimiento</div>', unsafe_allow_html=True)
        cols = st.columns(5)
        for col, (titulo, valor) in zip(cols, [("Estabilidad", f"{metricas['porcentaje_estabilidad']}%"), ("Temp. promedio", f"{metricas['temp_promedio']} °C"), ("Humedad promedio", f"{metricas['humedad_promedio']}%"), ("Hora crítica", metricas["hora_pico_calor"]), ("Activaciones", metricas["activaciones_totales"])]):
            col.metric(titulo, valor)
        resumen = analizar_picos_por_horario(historial)
        st.pyplot(generar_grafico_tendencia(historial), clear_figure=True)
        st.pyplot(generar_grafico_barras_agrupadas(resumen), clear_figure=True)
        st.pyplot(generar_grafico_circular(historial), clear_figure=True)

with tab_admin:
    if st.session_state["rol"] != "admin":
        st.warning("Modo consulta: inicia sesión como administrador para modificar la configuración.")
        st.info("El operador puede consultar el estado del sistema, pero los umbrales y el correo están protegidos.")
    else:
        st.markdown('<div class="section-label">Configuración protegida</div>', unsafe_allow_html=True)
        st.subheader("Finca y parcelas")
        with st.form("form_parcela"):
            nombre_parcela = st.text_input("Nombre de parcela")
            hectareas = st.number_input("Hectáreas", min_value=0.01, step=0.1)
            ubicacion = st.text_input("Ubicación o referencia")
            crear = st.form_submit_button("Crear parcela")
        if crear:
            try:
                crear_parcela(nombre_parcela, hectareas, ubicacion)
                st.success("Parcela creada.")
            except sqlite3.IntegrityError:
                st.error("Ya existe una parcela con ese nombre.")
        parcelas_admin = listar_parcelas()
        if not parcelas_admin.empty:
            with st.form("form_cultivo"):
                parcela_admin = st.selectbox("Parcela del cultivo", parcelas_admin["nombre"].tolist())
                cultivo_admin = st.selectbox("Cultivo", list(CULTIVOS))
                temporada_admin = st.text_input("Temporada", str(date.today().year))
                humedad_min_admin = st.number_input("Humedad mínima del suelo (%)", 0.0, 100.0, 35.0)
                humedad_max_admin = st.number_input("Humedad máxima del suelo (%)", 0.0, 100.0, 70.0)
                crear_cultivo_btn = st.form_submit_button("Vincular cultivo a parcela")
            if crear_cultivo_btn:
                try:
                    parcela_id_admin = int(parcelas_admin.loc[parcelas_admin["nombre"] == parcela_admin, "id"].iloc[0])
                    crear_cultivo(cultivo_admin, parcela_id_admin, temporada_admin, humedad_min_admin, humedad_max_admin)
                    st.success("Cultivo vinculado a la parcela.")
                except (ValueError, sqlite3.IntegrityError) as exc:
                    st.error(f"No se pudo vincular el cultivo: {exc}")
        cultivos_admin = listar_cultivos()
        if not cultivos_admin.empty:
            st.dataframe(cultivos_admin[["parcela", "nombre", "temporada", "humedad_min", "humedad_max"]],
                         use_container_width=True, hide_index=True)
        st.subheader("Parámetros de operación")
        with st.form("admin_configuracion"):
            nuevo_intervalo = st.number_input("Intervalo de actualización (segundos)", 0, 60, int(config.get("intervalo_actualizacion", 2)))
            valores: dict[str, float] = {}
            for clave, nombre in [("arroz", "Arroz"), ("frijol", "Frijol")]:
                st.markdown(f"**Umbrales de {nombre}**")
                actual = config["granos"][clave]
                valores[f"{clave}_temp_min"] = st.number_input(f"Temperatura mínima {nombre}", value=float(actual["temp_min"]))
                valores[f"{clave}_temp_max"] = st.number_input(f"Temperatura máxima {nombre}", value=float(actual["temp_max"]))
                valores[f"{clave}_humedad_min"] = st.number_input(f"Humedad mínima {nombre}", value=float(actual["humedad_min"]))
                valores[f"{clave}_humedad_max"] = st.number_input(f"Humedad máxima {nombre}", value=float(actual["humedad_max"]))
            guardar = st.form_submit_button("Guardar configuración", type="primary")
        if guardar:
            nueva_config = {**config, "intervalo_actualizacion": nuevo_intervalo, "granos": {}}
            for clave in ("arroz", "frijol"):
                nueva_config["granos"][clave] = {
                    "temp_min": valores[f"{clave}_temp_min"],
                    "temp_max": valores[f"{clave}_temp_max"],
                    "humedad_min": valores[f"{clave}_humedad_min"],
                    "humedad_max": valores[f"{clave}_humedad_max"],
                }
            valido, mensaje = validar_configuracion(nueva_config)
            if not valido:
                st.error(mensaje)
            else:
                guardar_configuracion(nueva_config)
                registrar_evento("configuracion", f"Parámetros actualizados por {st.session_state['usuario']}")
                st.success("Configuración guardada correctamente.")
                st.rerun()
