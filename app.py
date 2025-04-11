import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# -----------------------------------------------------------------
# 1) set_page_config => PRIMER COMANDO
# -----------------------------------------------------------------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
WORKSHEET_NAME = "Data"

PLATAFORMA_COLORES = {
    "Instagram": "#ffc0cb",
    "TikTok": "#ffffff",
    "Facebook": "#add8e6",
    "Otra": "#dddddd"
}

NOMBRE_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

def get_gsheet_connection():
    cred_json_str = st.secrets["gcp_service_account"]
    creds_dict = json.loads(cred_json_str)
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    return client

def cargar_datos(client, sheet_id):
    sh = client.open_by_key(sheet_id)
    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")
        worksheet.append_row(COLUMNS)
        return pd.DataFrame(columns=COLUMNS)

    data = worksheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=COLUMNS)
    else:
        df = pd.DataFrame(data)
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        return df

def guardar_datos(client, sheet_id, df):
    sh = client.open_by_key(sheet_id)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]
    df["Fecha"] = df["Fecha"].astype(str)
    data_to_upload = [df.columns.tolist()] + df.values.tolist()

    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")

    worksheet.clear()
    worksheet.update(data_to_upload)

def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")
    st.write("Descripción y botones...")

    if st.button("Agregar Evento", key="dash_btn_agregar"):
        st.session_state["page"] = "Agregar"
    if st.button("Editar/Eliminar Evento", key="dash_btn_editar"):
        st.session_state["page"] = "Editar"
    if st.button("Vista Mensual", key="dash_btn_mensual"):
        st.session_state["page"] = "Mensual"
    if st.button("Vista Anual", key="dash_btn_anual"):
        st.session_state["page"] = "Anual"

    st.write("---")
    total_eventos = len(df)
    st.metric("Total de eventos registrados", total_eventos)

def vista_agregar(df, client, sheet_id):
    st.title("Agregar Nuevo Evento")
    with st.form("form_agregar", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.date.today())
        titulo = st.text_input("Título", "")
        festividad = st.text_input("Festividad/Efeméride", "")
        plataforma = st.selectbox("Plataforma", ["Instagram","TikTok","Facebook","Otra"])
        estado = st.selectbox("Estado", ["Planeación","Diseño","Programado","Publicado"])
        notas = st.text_area("Notas", "")

        if st.form_submit_button("Guardar"):
            nuevo = {
                "Fecha": fecha,
                "Titulo": titulo,
                "Festividad": festividad,
                "Plataforma": plataforma,
                "Estado": estado,
                "Notas": notas
            }
            df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
            guardar_datos(client, sheet_id, df)
            st.success("¡Evento agregado y guardado!")

def vista_editar_eliminar(df, client, sheet_id):
    st.title("Editar o Eliminar Eventos")
    if df.empty:
        st.info("No hay eventos.")
        return
    st.dataframe(df)

    indices = df.index.tolist()
    if not indices:
        return

    selected_index = st.selectbox("Fila a modificar", indices, key="sel_index_editar")
    row_data = df.loc[selected_index]
    with st.form("form_editar"):
        fecha_edit = st.date_input("Fecha", value=row_data["Fecha"] if not pd.isnull(row_data["Fecha"]) else datetime.date.today())
        titulo_edit = st.text_input("Título", value=row_data["Titulo"])
        festividad_edit = st.text_input("Festividad/Efeméride", value=row_data["Festividad"])
        plataforma_edit = st.selectbox("Plataforma", ["Instagram","TikTok","Facebook","Otra"], 
                                       index=["Instagram","TikTok","Facebook","Otra"].index(row_data["Plataforma"]) if row_data["Plataforma"] in ["Instagram","TikTok","Facebook","Otra"] else 0)
        estado_edit = st.selectbox("Estado", ["Planeación","Diseño","Programado","Publicado"], 
                                   index=["Planeación","Diseño","Programado","Publicado"].index(row_data["Estado"]) if row_data["Estado"] in ["Planeación","Diseño","Programado","Publicado"] else 0)
        notas_edit = st.text_area("Notas", value=row_data["Notas"])

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Guardar cambios"):
                df.at[selected_index, "Fecha"] = fecha_edit
                df.at[selected_index, "Titulo"] = titulo_edit
                df.at[selected_index, "Festividad"] = festividad_edit
                df.at[selected_index, "Plataforma"] = plataforma_edit
                df.at[selected_index, "Estado"] = estado_edit
                df.at[selected_index, "Notas"] = notas_edit
                guardar_datos(client, sheet_id, df)
                st.success("¡Evento editado y guardado!")

        with col2:
            if st.form_submit_button("Borrar este evento"):
                df.drop(index=selected_index, inplace=True)
                df.reset_index(drop=True, inplace=True)
                guardar_datos(client, sheet_id, df)
                st.warning("Evento eliminado.")

def vista_mensual(df):
    st.title("Vista Mensual")
    # ...
    st.info("Pendiente o ajusta la lógica aquí...")

def vista_anual(df):
    st.title("Vista Anual")
    if df.empty:
        st.info("No hay datos.")
        return

    anios = sorted(df["Fecha"].dt.year.dropna().unique().astype(int))
    if not anios:
        st.warning("No hay años disponibles.")
        return
    anio_sel = st.selectbox("Año", anios)
    df_anio = df[df["Fecha"].dt.year==anio_sel]
    if df_anio.empty:
        st.warning("No hay datos para ese año.")
        return

    st.write(f"Mostrando calendario {anio_sel}")

    # Ejemplo simplificado
    for mes in range(1,13):
        df_mes = df_anio[df_anio["Fecha"].dt.month==mes]
        if df_mes.empty:
            continue

        st.write(f"### {NOMBRE_MESES[mes-1]} {anio_sel}")

        # Possibly your new logic for columns S1..S5

        # EJEMPLO: fix the bracket mismatch -> 
        # If there's some code with day.isin(...) => be sure it is correct

        # ...
        # EJ: if some code had df_sem = df_mes[df_mes["Fecha"].dt.day.isin(days_col]]  # WRONG
        # must be df_sem = df_mes[df_mes["Fecha"].dt.day.isin(days_col)]  # FIXED

        st.dataframe(df_mes)  # Placeholder

def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    client = get_gsheet_connection()
    sheet_id = st.secrets["SHEET_ID"]
    df = cargar_datos(client, sheet_id)

    st.sidebar.title("Navegación")
    if st.sidebar.button("Dashboard", key="side_dash"):
        st.session_state["page"] = "Dashboard"
    if st.sidebar.button("Agregar Evento", key="side_agregar"):
        st.session_state["page"] = "Agregar"
    if st.sidebar.button("Editar/Eliminar Evento", key="side_editar"):
        st.session_state["page"] = "Editar"
    if st.sidebar.button("Vista Mensual", key="side_mensual"):
        st.session_state["page"] = "Mensual"
    if st.sidebar.button("Vista Anual", key="side_anual"):
        st.session_state["page"] = "Anual"

    page = st.session_state["page"]
    if page=="Dashboard":
        dashboard(df)
    elif page=="Agregar":
        vista_agregar(df, client, sheet_id)
    elif page=="Editar":
        vista_editar_eliminar(df, client, sheet_id)
    elif page=="Mensual":
        vista_mensual(df)
    elif page=="Anual":
        vista_anual(df)

if __name__ == "__main__":
    main()
