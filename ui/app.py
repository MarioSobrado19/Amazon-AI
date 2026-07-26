"""Punto de entrada de la interfaz web local."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from ui.navigation import (
    BIENVENIDA,
    CARGA,
    CONFIGURACION,
    PRODUCTOS_LISTOS,
    RESULTADOS,
    VISTA_PREVIA,
    ir_a,
)
from ui.screens import configuration, preview, ready, results, upload, welcome
from ui.session import inicializar_sesion


st.set_page_config(
    page_title="Amazon Scout AI",
    page_icon="🚀",
    layout="centered",
)

inicializar_sesion(st.session_state)

PANTALLAS = {
    BIENVENIDA: welcome.renderizar,
    CARGA: upload.renderizar,
    VISTA_PREVIA: preview.renderizar,
    PRODUCTOS_LISTOS: ready.renderizar,
    CONFIGURACION: configuration.renderizar,
    RESULTADOS: results.renderizar,
}

pantalla = st.session_state["pantalla_actual"]
if pantalla not in PANTALLAS:
    ir_a(st.session_state, BIENVENIDA)
    pantalla = BIENVENIDA

PANTALLAS[pantalla](st, st.session_state)
