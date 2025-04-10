{\rtf1\ansi\ansicpg1252\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import os\
from datetime import date\
\
CSV_FILE = "data.csv"\
\
def cargar_datos():\
    """Lee data.csv si existe, de lo contrario retorna un DataFrame vac\'edo."""\
    if os.path.exists(CSV_FILE):\
        return pd.read_csv(CSV_FILE, parse_dates=["Fecha"])\
    else:\
        return pd.DataFrame(columns=["Fecha","Titulo","Festividad","Plataforma","Status","Notas"])\
\
def guardar_datos(df):\
    """Guarda el DataFrame en data.csv."""\
    df.to_csv(CSV_FILE, index=False)\
\
st.title("Calendario de Contenidos")\
\
# Cargar los datos existentes\
df = cargar_datos()\
\
st.subheader("Agregar nuevo evento")\
with st.form("form_nuevo_evento", clear_on_submit=True):\
    fecha = st.date_input("Fecha", date.today())\
    titulo = st.text_input("T\'edtulo/Idea", "")\
    festividad = st.text_input("Festividad/Efem\'e9ride (opcional)", "")\
    plataforma = st.selectbox("Plataforma", ["IG","TikTok","Facebook","Blog","Otra"])\
    status = st.selectbox("Status", ["Planeaci\'f3n","Dise\'f1o","Programado","Publicado"])\
    notas = st.text_area("Notas adicionales")\
\
    enviado = st.form_submit_button("Guardar")\
    if enviado:\
        # Agregamos la nueva fila al DataFrame\
        nuevo = \{\
            "Fecha": fecha,\
            "Titulo": titulo,\
            "Festividad": festividad,\
            "Plataforma": plataforma,\
            "Status": status,\
            "Notas": notas\
        \}\
        df = df.append(nuevo, ignore_index=True)\
        guardar_datos(df)\
        st.success("\'a1Evento agregado y guardado!")\
\
st.write("## Eventos registrados")\
if not df.empty:\
    st.dataframe(df)\
else:\
    st.info("A\'fan no hay datos registrados.")\
}