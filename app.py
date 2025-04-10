import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
import datetime
import os

# Nombres de las columnas (asegúrate de que tu Google Sheet use exactamente estos encabezados)
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]

# Nombre de la hoja (tab) que usaremos dentro del Google Sheet
WORKSHEET_NAME = "Data"

def get_gsheet_connection():
    """
    Retorna un objeto gspread.Client autenticado con las credenciales en st.secrets.
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = st.secrets["gcp_service_account"]  # El JSON con credenciales
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    return client

def cargar_datos(client, sheet_key):
    """
    Lee los datos desde la pestaña 'WORKSHEET_NAME' de tu Google Sheet y los retorna como DataFrame.
    """
    sh = client.open_by_key(sheet_key)  # O open_by_url si prefieres
    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        # Si no existe la hoja, la creamos vacía
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")
        # Añadimos cabeceras
        worksheet.append_row(COLUMNS)
        return pd.DataFrame(columns=COLUMNS)

    # Leemos todas las filas como "records" (diccionarios)
    data = worksheet.get_all_records()

    if not data:
        # Hoja vacía (solo encabezados, quizás)
        return pd.DataFrame(columns=COLUMNS)
    else:
        df = pd.DataFrame(data)
        # Convertir la columna "Fecha" a datetime
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        return df

def guardar_datos(client, sheet_key, df):
    """
    Sube TODO el DataFrame a la hoja 'WORKSHEET_NAME' (sobrescribiendo su contenido).
    """
    sh = client.open_by_key(sheet_key)

    # Asegurarnos de que están todas las columnas en orden
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]

    # Convertir Fecha a string para subir a Sheets
    df["Fecha"] = df["Fecha"].astype(str)

    # Convertir DF a lista de listas
    data_to_upload = [df.columns.tolist()] + df.values.tolist()

    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")

    # Limpiar y subir
    worksheet.clear()
    worksheet.update(data_to_upload)

def main():
    st.set_page_config(page_title="Calendario - Google Sheets", layout="wide")
    st.title("Calendario de Contenidos (con Google Sheets)")

    st.markdown("""
    **Este calendario** guarda los datos directamente en una hoja de Google Sheets.
    Apaga tu PC con tranquilidad: al volver, los datos siguen en la nube.
    """)

    # Obtenemos la Sheet Key o ID desde st.secrets
    # Asegúrate de agregar "SHEET_ID" en tus secrets
    SHEET_ID = st.secrets["SHEET_ID"]  # Por ejemplo: 1abcdEfjk-LargoID-XYZ

    # 1) Conectamos con Google
    client = get_gsheet_connection()

    # 2) Cargar/Leer DF
    df = cargar_datos(client, SHEET_ID)

    # 3) Formulario para añadir un evento
    with st.form("form_nuevo", clear_on_submit=True):
        st.subheader("Agregar nuevo evento")

        fecha = st.date_input("Fecha", datetime.date.today())
        titulo = st.text_input("Título", "")
        festividad = st.text_input("Festividad/Efeméride", "")
        plataforma = st.selectbox("Plataforma", ["Instagram","TikTok","Facebook","Blog","Otra"])
        estado = st.selectbox("Estado", ["Planeación","Diseño","Programado","Publicado"])
        notas = st.text_area("Notas", "")

        if st.form_submit_button("Guardar evento"):
            nuevo = {
                "Fecha": fecha,
                "Titulo": titulo,
                "Festividad": festividad,
                "Plataforma": plataforma,
                "Estado": estado,
                "Notas": notas
            }
            # Agregar fila al DF usando concat en vez de append
            df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
            guardar_datos(client, SHEET_ID, df)
            st.success("¡Evento guardado en Google Sheets!")

    st.write("### Lista de Eventos Registrados")

    if df.empty:
        st.info("Aún no hay datos en la hoja.")
    else:
        st.dataframe(df)

        # Eliminar un evento (opcional)
        indices = df.index.tolist()
        if indices:
            fila_eliminar = st.selectbox("Selecciona la fila a eliminar", indices)
            if st.button("Eliminar seleccionado"):
                df.drop(index=fila_eliminar, inplace=True)
                df.reset_index(drop=True, inplace=True)
                guardar_datos(client, SHEET_ID, df)
                st.warning("¡Evento eliminado de Google Sheets!")

if __name__ == "__main__":
    main()
