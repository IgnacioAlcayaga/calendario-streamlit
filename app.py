import streamlit as st
import pandas as pd
import os
from datetime import date

CSV_FILE = "data.csv"

def cargar_datos():
    """Lee data.csv si existe, de lo contrario retorna un DataFrame vacío."""
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE, parse_dates=["Fecha"])
    else:
        return pd.DataFrame(columns=["Fecha","Titulo","Festividad","Plataforma","Status","Notas"])

def guardar_datos(df):
    """Guarda el DataFrame en data.csv."""
    df.to_csv(CSV_FILE, index=False)

st.title("Calendario de Contenidos")

# Cargar los datos existentes
df = cargar_datos()

st.subheader("Agregar nuevo evento")
with st.form("form_nuevo_evento", clear_on_submit=True):
    fecha = st.date_input("Fecha", date.today())
    titulo = st.text_input("Título/Idea", "")
    festividad = st.text_input("Festividad/Efeméride (opcional)", "")
    plataforma = st.selectbox("Plataforma", ["IG","TikTok","Facebook","Blog","Otra"])
    status = st.selectbox("Status", ["Planeación","Diseño","Programado","Publicado"])
    notas = st.text_area("Notas adicionales")

    enviado = st.form_submit_button("Guardar")
    if enviado:
        # Agregamos la nueva fila al DataFrame
        nuevo = {
            "Fecha": fecha,
            "Titulo": titulo,
            "Festividad": festividad,
            "Plataforma": plataforma,
            "Status": status,
            "Notas": notas
        }
        df = df.append(nuevo, ignore_index=True)
        guardar_datos(df)
        st.success("¡Evento agregado y guardado!")

st.write("## Eventos registrados")
if not df.empty:
    st.dataframe(df)
else:
    st.info("Aún no hay datos registrados.")
