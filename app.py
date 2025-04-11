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

# --------------------------------------------------------------------------------
# CONFIGURACIÓN DE COLUMNAS / HOJA
# --------------------------------------------------------------------------------
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
WORKSHEET_NAME = "Data"

# Colores opcionales por plataforma
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

# --------------------------------------------------------------------------------
# FUNCIÓN DE CONEXIÓN A GOOGLE SHEETS
# --------------------------------------------------------------------------------
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

# --------------------------------------------------------------------------------
# PANTALLAS
# --------------------------------------------------------------------------------

def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown("""
    Bienvenido(a) a tu **Calendario de Contenidos**. 

    - **Agregar Evento**: Ingresar nuevas publicaciones.  
    - **Editar/Eliminar Evento**: Lista y modificación de contenidos.  
    - **Vista Mensual**: Ver un mes con columnas de semanas.  
    - **Vista Anual**: Ver cada mes en columnas de semanas, con estado (plataformas) al pie.
    """)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Agregar Evento", key="dash_btn_agregar"):
            st.session_state["page"] = "Agregar"
    with col2:
        if st.button("Editar/Eliminar Evento", key="dash_btn_editar"):
            st.session_state["page"] = "Editar"
    with col3:
        if st.button("Vista Mensual", key="dash_btn_mensual"):
            st.session_state["page"] = "Mensual"
    with col4:
        if st.button("Vista Anual", key="dash_btn_anual"):
            st.session_state["page"] = "Anual"

    st.write("---")
    total_eventos = len(df)
    st.metric("Total de eventos registrados", total_eventos)
    if not df.empty and "Estado" in df.columns:
        conteo_estado = df["Estado"].value_counts().to_dict()
        st.subheader("Conteo por Estado")
        for estado, count in conteo_estado.items():
            st.write(f"- **{estado}**: {count}")
    else:
        st.info("No hay datos o falta columna 'Estado'.")


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
            st.success("¡Evento agregado y guardado!")


def vista_editar_eliminar(df, client, sheet_id):
    st.title("Editar o Eliminar Eventos")
    if df.empty:
        st.info("No hay eventos.")
        return

    st.dataframe(df)
    indices = df.index.tolist()
    if not indices:
        st.info("No hay filas.")
        return

    selected_index = st.selectbox("Selecciona la fila a modificar", indices, key="sel_index_editar")
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
                submit_edit = st.form_submit_button("Guardar cambios", key="btn_guardar_edit")
            with col2:
                submit_delete = st.form_submit_button("Borrar este evento", key="btn_borrar_evento")

            if submit_edit:
                df.at[selected_index, "Fecha"] = fecha_edit
                df.at[selected_index, "Titulo"] = titulo_edit
                df.at[selected_index, "Festividad"] = festividad_edit
                df.at[selected_index, "Plataforma"] = plataforma_edit
                df.at[selected_index, "Estado"] = estado_edit
                df.at[selected_index, "Notas"] = notas_edit
                guardar_datos(client, sheet_id, df)
                st.success("¡Evento editado y guardado!")

            if submit_delete:
                df.drop(index=selected_index, inplace=True)
                df.reset_index(drop=True, inplace=True)
                guardar_datos(client, sheet_id, df)
                st.warning("Evento eliminado.")


def vista_mensual(df):
    st.title("Vista Mensual (pendiente)")

    # (Podrías adaptarlo similar a la Vista Anual de abajo,
    #  mostrando un único mes en la misma estructura de tabla.)


def vista_anual(df):
    st.title("Vista Anual (tipo segunda imagen)")

    if df.empty:
        st.info("No hay datos.")
        return

    # Elegir año
    anios = sorted(df["Fecha"].dt.year.dropna().unique().astype(int))
    if not anios:
        st.warning("No hay años disponibles.")
        return
    anio_sel = st.selectbox("Selecciona el Año", anios, index=0)

    df_anio = df[df["Fecha"].dt.year == anio_sel]
    if df_anio.empty:
        st.warning("No hay datos para ese año.")
        return

    st.markdown(f"## {anio_sel}")

    # Estructura: 5 columnas => S1..S5
    # 8 filas: fila0=encabezados, fila1..7= días, fila8= estatus
    # Para c/ mes => generamos tabla.

    full_html = []
    for mes in range(1,13):
        df_mes = df_anio[df_anio["Fecha"].dt.month == mes]
        if df_mes.empty:
            continue

        # Num dias
        import calendar
        _, ndays = calendar.monthrange(anio_sel, mes)  # (weekday_of_first_day, numDays)
        # Creamos la "rejilla" 7 filas x 5 columnas = 35 celdas (día 1..35)
        # day-> col = (day-1)//7, row = (day-1)%7 + 1
        # col max = 4 => 5 sem
        # al final fila8 => estatus

        # Recolectamos data en celdas
        # celdas[row][col] => text
        celdas = [["" for _ in range(5)] for _ in range(8)]  # 8 filas x 5 col
        # Fila 0 => "S1"..."S5"
        for c in range(5):
            celdas[0][c] = f"S{c+1}"

        # Llenar filas 1..7 con días / eventos
        for day_num in range(1, ndays+1):
            col = (day_num-1)//7
            if col>4:  # se excede las 5 sem
                break
            row = ((day_num-1)%7)+1
            # Filtrar events
            df_day = df_mes[df_mes["Fecha"].dt.day==day_num]
            # Armar texto
            day_text = f"{day_num}:<br/>"
            if not df_day.empty:
                for _, rowx in df_day.iterrows():
                    # Ej: "- Título (Festividad)"
                    item = f"- {rowx['Titulo']}"
                    if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                        item += f" ({rowx['Festividad']})"
                    item += "<br/>"
                    day_text += item
            celdas[row][col] += day_text

        # Llenar fila 8 con “estado”
        # Para cada col => col’s days => day range
        for c in range(5):
            # days in that col
            days_col = []
            # col => range is day = c*7+1.. c*7+7
            start_day = c*7+1
            end_day = min(start_day+6, ndays)
            days_col = list(range(start_day, end_day+1))

            df_sem = df_mes[df_mes["Fecha"].dt.day.isin(days_col]]
            # Agrupamos por plataforma
            if df_sem.empty:
                celdas[7][c] = "Sin eventos."
            else:
                plat_counts = {}
                for plat in df_sem["Plataforma"].unique():
                    subset = df_sem[df_sem["Plataforma"]==plat]
                    total = len(subset)
                    publ = len(subset[subset["Estado"]=="Publicado"])
                    plat_counts[plat] = (publ, total)

                txt = "<strong>Estado:</strong><br/>"
                if not plat_counts:
                    txt += "Sin eventos."
                else:
                    for p,(pb,tt) in plat_counts.items():
                        txt += f"{p}: {pb}/{tt} publ.<br/>"
                celdas[7][c] = txt

        # Generamos HTML
        table_html = []
        table_html.append(f"<h3>{NOMBRE_MESES[mes-1]} {anio_sel}</h3>")
        table_html.append("<table border='1' style='border-collapse:collapse; width:100%;'>")

        for row_i in range(8):
            table_html.append("<tr>")
            for col_i in range(5):
                cell = celdas[row_i][col_i]
                # Estilo minimal
                table_html.append(f"<td style='vertical-align:top; padding:5px;'>{cell}</td>")
            table_html.append("</tr>")

        table_html.append("</table>")
        full_html.append("".join(table_html))

    st.markdown("<div style='width:100%'>"+ "".join(full_html) +"</div>", unsafe_allow_html=True)


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


if __name__ == "__main__":
    main()
