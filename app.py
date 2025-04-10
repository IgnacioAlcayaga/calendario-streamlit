import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
import datetime

# ----------------------------------------------------------------
# CONFIGURACIÓN DE COLUMNAS Y PESTAÑA DE GOOGLE SHEETS
# ----------------------------------------------------------------
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
WORKSHEET_NAME = "Data"

# Paleta de colores para las plataformas
PLATAFORMA_COLORES = {
    "Instagram": "#ffc0cb",  # Rosa
    "TikTok": "#ffffff",     # Blanco
    "Facebook": "#add8e6",   # Azul clarito
    "Otra": "#dddddd"        # Gris para "Otra"
}

NOMBRE_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# ----------------------------------------------------------------
# FUNCIONES PARA CONECTAR A GOOGLE SHEETS
# ----------------------------------------------------------------
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

# ----------------------------------------------------------------
# PANTALLAS
# ----------------------------------------------------------------

def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown(
        """
        **Bienvenido(a)** a tu Panel Principal.

        **Navega** a las distintas secciones:
        - **Agregar Evento**
        - **Editar/Eliminar Evento**
        - **Vista Mensual**
        - **Vista Anual**
        """
    )

    # Botones directos a cada sección
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Agregar Evento"):
            st.session_state["page"] = "Agregar"
            st.experimental_rerun()
    with col2:
        if st.button("Editar/Eliminar Evento"):
            st.session_state["page"] = "Editar"
            st.experimental_rerun()
    with col3:
        if st.button("Vista Mensual"):
            st.session_state["page"] = "Mensual"
            st.experimental_rerun()
    with col4:
        if st.button("Vista Anual"):
            st.session_state["page"] = "Anual"
            st.experimental_rerun()

    st.write("---")
    total_eventos = len(df)
    st.metric("Total de eventos registrados", total_eventos)

    if not df.empty:
        if "Estado" in df.columns:
            conteo_estado = df["Estado"].value_counts().to_dict()
            st.subheader("Conteo por Estado")
            for estado, count in conteo_estado.items():
                st.write(f"- **{estado}**: {count}")
        else:
            st.warning("No existe la columna 'Estado'.")
    else:
        st.info("No hay datos todavía.")

def vista_agregar(df, client, sheet_id):
    st.title("Agregar Nuevo Evento")

    with st.form("form_agregar", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.date.today())
        titulo = st.text_input("Título", "")
        festividad = st.text_input("Festividad/Efeméride", "")
        plataforma = st.selectbox("Plataforma", ["Instagram","TikTok","Facebook","Otra"])
        estado = st.selectbox("Estado", ["Planeación","Diseño","Programado","Publicado"])
        notas = st.text_area("Notas", "")

        enviado = st.form_submit_button("Guardar")
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

def vista_editar_eliminar(df, client, sheet_id):
    st.title("Editar o Eliminar Eventos")

    if df.empty:
        st.info("No hay eventos registrados todavía.")
        return

    st.dataframe(df)

    indices = df.index.tolist()
    if indices:
        selected_index = st.selectbox("Selecciona la fila a modificar", indices)
        if selected_index is not None:
            row_data = df.loc[selected_index]

            with st.form("form_editar"):
                fecha_edit = st.date_input("Fecha", value=row_data["Fecha"] if not pd.isnull(row_data["Fecha"]) else datetime.date.today())
                titulo_edit = st.text_input("Título", value=row_data["Titulo"])
                festividad_edit = st.text_input("Festividad/Efeméride", value=row_data["Festividad"])
                plataformas_posibles = ["Instagram","TikTok","Facebook","Otra"]
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
                    st.success("¡Evento editado y guardado!")
                    st.experimental_rerun()

                if submit_delete:
                    df.drop(index=selected_index, inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    guardar_datos(client, sheet_id, df)
                    st.warning("Evento eliminado.")
                    st.experimental_rerun()

def vista_mensual(df):
    st.title("Vista Mensual")

    if df.empty:
        st.info("No hay datos.")
        return

    # Seleccionar mes por nombre
    nombre_mes = st.selectbox("Selecciona el mes", NOMBRE_MESES)
    mes_index = NOMBRE_MESES.index(nombre_mes) + 1  # 1-12
    df["Mes"] = df["Fecha"].dt.month
    filtrado = df[df["Mes"] == mes_index].drop(columns=["Mes"], errors="ignore")

    st.write(f"### Eventos de {nombre_mes}")
    st.dataframe(filtrado)

def vista_anual(df):
    st.title("Vista Anual - Calendario Global")

    if df.empty:
        st.info("No hay datos.")
        return

    st.write("Se mostrará un calendario para cada mes, con recuadros de colores.")
    # Crear un HTML que contenga 12 calendarios (3 col x 4 fil)
    html_output = []
    html_output.append("""
    <style>
    .calendar-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr); /* 3 meses por fila */
        gap: 1rem;
    }
    .month-card {
        border: 2px solid #ccc;
        padding: 0.5rem;
    }
    .month-title {
        text-align: center;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .days-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        grid-auto-rows: 80px;
        gap: 2px;
    }
    .day-cell {
        border: 1px solid #eee;
        padding: 3px;
        position: relative;
        overflow: hidden;
        font-size: 0.8rem;
    }
    .day-number {
        font-weight: bold;
        font-size: 0.8rem;
    }
    .event-label {
        font-size: 0.7rem;
        margin-top: 2px;
        display: block;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
    </style>
    """)

    # Agrupamos df por dia
    df["year"] = df["Fecha"].dt.year
    df["month"] = df["Fecha"].dt.month
    df["day"] = df["Fecha"].dt.day

    # Tomamos el año de la mayoría de datos (o primer evento)
    anios = df["year"].unique()
    if len(anios) == 1:
        anio = anios[0]
    else:
        anio = st.number_input("Elige año:", value=int(datetime.date.today().year), step=1)

    # Filtrar por anio
    df_anio = df[df["year"] == anio]
    if df_anio.empty:
        st.warning(f"No hay datos para el año {anio}.")
        return

    # Estructura de 12 calendarios
    html_output.append('<div class="calendar-container">')

    for mes_idx in range(1, 13):
        df_mes = df_anio[df_anio["month"] == mes_idx]
        # Armar el calendario de mes
        # 1) Determinar 1er dia del mes, dia de la semana, etc.
        month_start = datetime.date(int(anio), mes_idx, 1)
        start_weekday = month_start.weekday()  # lunes=0, domingo=6
        # Calculamos cuántos días tiene el mes
        if mes_idx == 12:
            next_month = datetime.date(int(anio)+1, 1, 1)
        else:
            next_month = datetime.date(int(anio), mes_idx+1, 1)
        num_dias = (next_month - month_start).days

        # HTML mes
        mes_name = NOMBRE_MESES[mes_idx-1]
        html_output.append(f'<div class="month-card"><div class="month-title">{mes_name} {anio}</div>')
        # Grid de 7 col
        html_output.append('<div class="days-grid">')

        # Rellenar celdas vacías antes del 1 (para alinear)
        for _ in range(start_weekday):
            html_output.append('<div class="day-cell"></div>')

        # Rellenar días
        for day_num in range(1, num_dias+1):
            # Buscamos si hay evento en df_mes con day == day_num
            df_day = df_mes[df_mes["day"] == day_num]
            # Varias plataformas => varios eventos => definimos 1 color principal (o varios?)
            # Ejemplo simple: si hay 1, tomamos la 1ra.
            day_html = f'<span class="day-number">{day_num}</span><br/>'
            if not df_day.empty:
                # Recorremos df_day. Muestra Titulo y Festividad (solo un poco)
                for _, row in df_day.iterrows():
                    plat = row["Plataforma"]
                    color = PLATAFORMA_COLORES.get(plat, "#dddddd")
                    title = (row["Titulo"][:10] + '...') if len(str(row["Titulo"])) > 10 else str(row["Titulo"])
                    fest = (row["Festividad"][:10] + '...') if len(str(row["Festividad"])) > 10 else str(row["Festividad"])
                    # Muestra un span con color de fondo
                    day_html += f'<span class="event-label" style="background-color:{color};">{title}'
                    if fest.strip():
                        day_html += f' ({fest})'
                    day_html += '</span>'
            # Insertamos celda
            html_output.append(f'<div class="day-cell">{day_html}</div>')

        html_output.append('</div></div>')  # end days-grid, end month-card

    html_output.append('</div>')  # end calendar-container

    st.markdown("\n".join(html_output), unsafe_allow_html=True)


# ----------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# ----------------------------------------------------------------
def main():
    st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

    # Control interno de páginas
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    # Conectamos a Google Sheets
    client = get_gsheet_connection()
    sheet_id = st.secrets["SHEET_ID"]

    # Cargamos df
    df = cargar_datos(client, sheet_id)

    # Lógica de navegación
    page = st.session_state["page"]

    if page == "Dashboard":
        dashboard(df)
    elif page == "Agregar":
        vista_agregar(df, client, sheet_id)
    elif page == "Editar":
        vista_editar_eliminar(df, client, sheet_id)
    elif page == "Mensual":
        vista_mensual(df)
    elif page == "Anual":
        vista_anual(df)

    # Botón para volver al Dashboard
    st.sidebar.write("---")
    if st.sidebar.button("Volver al Dashboard"):
        st.session_state["page"] = "Dashboard"
        st.experimental_rerun()

if __name__ == "__main__":
    main()

