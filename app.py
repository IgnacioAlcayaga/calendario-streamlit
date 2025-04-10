import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
import datetime

# --------------------------------------------------
# CONFIGURACIÓN DE COLUMNAS Y PESTAÑA DE GOOGLE SHEETS
# --------------------------------------------------
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
WORKSHEET_NAME = "Data"  # Nombre de la pestaña dentro de tu Google Sheet

# --------------------------------------------------
# FUNCIONES PARA CONECTAR Y LEER/ESCRIBIR A GOOGLE SHEETS
# --------------------------------------------------
def get_gsheet_connection():
    """
    Conecta con Google Sheets usando credenciales de service account
    guardadas en st.secrets["gcp_service_account"], en formato JSON (cadena TOML).
    """
    # 1) Cargamos la cadena JSON de secrets
    cred_json_str = st.secrets["gcp_service_account"]
    # 2) Convertimos en dict Python
    creds_dict = json.loads(cred_json_str)
    # 3) Definimos los alcances que queremos
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # 4) Creamos credenciales y autorizamos gspread
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    return client

def cargar_datos(client, sheet_id):
    """
    Lee todos los datos de la pestaña WORKSHEET_NAME en la hoja con 'sheet_id'.
    Devuelve un DataFrame con las columnas definidas en COLUMNS.
    Si no existe la pestaña, la crea vacía.
    """
    sh = client.open_by_key(sheet_id)
    
    # Intentamos abrir la hoja "Data"
    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        # Si no existe, la creamos
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")
        # Insertamos la fila de encabezados
        worksheet.append_row(COLUMNS)
        return pd.DataFrame(columns=COLUMNS)

    # Leemos todas las filas en forma de lista de diccionarios
    data = worksheet.get_all_records()
    if not data:
        # Está vacía o solo tiene encabezados
        return pd.DataFrame(columns=COLUMNS)
    else:
        df = pd.DataFrame(data)
        # Convertir Fecha a datetime
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        return df

def guardar_datos(client, sheet_id, df):
    """
    Sobrescribe todo el contenido de la pestaña WORKSHEET_NAME con los datos del DataFrame 'df'.
    """
    sh = client.open_by_key(sheet_id)

    # Aseguramos que existan las columnas y en orden
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]

    # Convertimos Fecha a str
    df["Fecha"] = df["Fecha"].astype(str)

    # Convertimos el DataFrame a lista de listas, con la fila de encabezados al inicio
    data_to_upload = [df.columns.tolist()] + df.values.tolist()

    # Ubicamos o creamos la hoja
    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")

    # Limpiamos y subimos todo
    worksheet.clear()
    worksheet.update(data_to_upload)

# --------------------------------------------------
# VISTAS DE LA APP
# --------------------------------------------------
def vista_dashboard(df):
    """Sección de 'Dashboard' con info general."""
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown("""
    Aquí puedes ver un resumen de tus publicaciones y su estado.
    Ve a **Data** para agregar o editar, 
    **Vista Mensual** para filtrar por mes, 
    o **Vista Anual** para filtrar por año.
    """)

    st.write("---")

    total_eventos = len(df)
    st.metric("Total de eventos registrados", total_eventos)

    if not df.empty:
        # Conteo por "Estado"
        if "Estado" in df.columns:
            conteo_estado = df["Estado"].value_counts().to_dict()
            st.subheader("Conteo por Estado")
            for estado, count in conteo_estado.items():
                st.write(f"- **{estado}**: {count}")
        else:
            st.warning("No existe la columna 'Estado' en el DataFrame.")
    else:
        st.info("No hay datos aún. Ve a la sección 'Data' para agregar tus primeros eventos.")

def vista_data(df, client, sheet_id):
    """Pantalla para ver, agregar, editar y borrar eventos."""
    st.title("Gestión de Data - Agregar / Editar Eventos")

    st.markdown("""
    - **Agrega** nuevos eventos en el formulario.
    - **Edita** o **Elimina** seleccionando la fila correspondiente.
    """)

    st.write("---")

    # Form para agregar nuevo evento
    with st.form("form_nuevo", clear_on_submit=True):
        st.subheader("Agregar nuevo evento")

        fecha = st.date_input("Fecha", datetime.date.today())
        titulo = st.text_input("Título", "")
        festividad = st.text_input("Festividad/Efeméride", "")
        plataforma = st.selectbox("Plataforma", ["Instagram","TikTok","Facebook","Blog","Otra"])
        estado = st.selectbox("Estado", ["Planeación","Diseño","Programado","Publicado"])
        notas = st.text_area("Notas", "")

        enviado = st.form_submit_button("Guardar evento")
        if enviado:
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
            st.success("¡Evento agregado y guardado en Google Sheets!")

    st.write("### Eventos existentes")
    if df.empty:
        st.info("No hay eventos registrados todavía.")
        return

    st.dataframe(df)

    st.markdown("#### Editar o Eliminar eventos")
    indices = df.index.tolist()
    if indices:
        selected_index = st.selectbox("Selecciona la fila a modificar", indices)
        if selected_index is not None:
            row_data = df.loc[selected_index]

            with st.form("form_editar"):
                fecha_edit = st.date_input("Fecha", value=row_data["Fecha"] if not pd.isnull(row_data["Fecha"]) else datetime.date.today())
                titulo_edit = st.text_input("Título", value=row_data["Titulo"])
                festividad_edit = st.text_input("Festividad/Efeméride", value=row_data["Festividad"])
                plataformas_posibles = ["Instagram","TikTok","Facebook","Blog","Otra"]
                if row_data["Plataforma"] in plataformas_posibles:
                    idx_plat = plataformas_posibles.index(row_data["Plataforma"])
                else:
                    idx_plat = 0
                plataforma_edit = st.selectbox("Plataforma", plataformas_posibles, index=idx_plat)

                estados_posibles = ["Planeación","Diseño","Programado","Publicado"]
                if row_data["Estado"] in estados_posibles:
                    idx_est = estados_posibles.index(row_data["Estado"])
                else:
                    idx_est = 0
                estado_edit = st.selectbox("Estado", estados_posibles, index=idx_est)

                notas_edit = st.text_area("Notas", value=row_data["Notas"] if not pd.isnull(row_data["Notas"]) else "")

                col1, col2 = st.columns(2)
                with col1:
                    submit_edit = st.form_submit_button("Guardar cambios")
                with col2:
                    submit_delete = st.form_submit_button("Borrar este evento")

                if submit_edit:
                    df.at[selected_index, "Fecha"] = fecha_edit
                    df.at[selected_index, "Titulo"] = titulo_edit
                    df.at[selected_index, "Festividad"] = festividad_edit
                    df.at[selected_index, "Plataforma"] = plataforma_edit
                    df.at[selected_index, "Estado"] = estado_edit
                    df.at[selected_index, "Notas"] = notas_edit
                    guardar_datos(client, sheet_id, df)
                    st.success("¡Evento editado y guardado en Google Sheets!")

                if submit_delete:
                    df.drop(index=selected_index, inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    guardar_datos(client, sheet_id, df)
                    st.warning("Evento eliminado de Google Sheets.")
                    st.experimental_rerun()

def vista_mensual(df):
    """Muestra los eventos filtrados por mes."""
    st.title("Vista Mensual de Eventos")

    if df.empty:
        st.info("No hay datos. Agrega eventos en la sección 'Data'.")
        return

    mes_seleccionado = st.selectbox("Selecciona el mes (1-12)", list(range(1,13)), format_func=lambda x: f"Mes {x}")
    df["Mes"] = df["Fecha"].dt.month
    filtrado = df[df["Mes"] == mes_seleccionado].drop(columns=["Mes"], errors="ignore")

    st.write(f"### Eventos para el mes {mes_seleccionado}")
    if filtrado.empty:
        st.warning("No hay eventos para este mes.")
    else:
        st.dataframe(filtrado)

def vista_anual(df):
    """Muestra los eventos filtrados por año, con opción de descarga en Excel."""
    st.title("Vista Anual de Eventos")

    if df.empty:
        st.info("No hay datos. Agrega eventos en la sección 'Data'.")
        return

    anio = st.number_input("Año", value=2025, step=1)
    df["Anio"] = df["Fecha"].dt.year
    filtrado = df[df["Anio"] == anio].drop(columns=["Anio"], errors="ignore")

    st.write(f"### Mostrando eventos del año {anio}")
    if filtrado.empty:
        st.warning(f"No se encontraron eventos para {anio}.")
    else:
        st.dataframe(filtrado)

        # Botón para descargar Excel
        if st.button("Descargar en Excel"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                filtrado.to_excel(writer, sheet_name=str(anio), index=False)
            excel_data = output.getvalue()
            st.download_button(
                label="Descargar Excel",
                data=excel_data,
                file_name=f"Eventos_{anio}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --------------------------------------------------
# FUNCIÓN PRINCIPAL
# --------------------------------------------------
def main():
    st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

    # Conectamos a Google Sheets
    client = get_gsheet_connection()
    # Leemos el SHEET_ID de secrets
    sheet_id = st.secrets["SHEET_ID"]

    # Cargamos datos en DataFrame
    df = cargar_datos(client, sheet_id)

    # Sidebar para navegar
    st.sidebar.title("Navegación")
    menu = ["Dashboard", "Data", "Vista Mensual", "Vista Anual"]
    choice = st.sidebar.radio("Ir a", menu)

    if choice == "Dashboard":
        vista_dashboard(df)
    elif choice == "Data":
        vista_data(df, client, sheet_id)
    elif choice == "Vista Mensual":
        vista_mensual(df)
    elif choice == "Vista Anual":
        vista_anual(df)

if __name__ == "__main__":
    main()
