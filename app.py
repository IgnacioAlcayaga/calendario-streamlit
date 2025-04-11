import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import calendar

# --------------------------------------------------------------------------------
# 1) PRIMER COMANDO: set_page_config
# --------------------------------------------------------------------------------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

# --------------------------------------------------------------------------------
# CONFIGURACIÓN Y CONSTANTES
# --------------------------------------------------------------------------------
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
WORKSHEET_NAME = "Data"

PLATAFORMA_COLORES = {
    "Instagram": "#ffc0cb",   # Rosa
    "TikTok": "#ffffff",      # Blanco
    "Facebook": "#add8e6",    # Azul clarito
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
    return gspread.authorize(credentials)

def cargar_datos(client, sheet_id):
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")
        ws.append_row(COLUMNS)
        return pd.DataFrame(columns=COLUMNS)

    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=COLUMNS)
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
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")

    ws.clear()
    ws.update(data_to_upload)

# --------------------------------------------------------------------------------
# PÁGINAS
# --------------------------------------------------------------------------------

def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown("""
    **Bienvenido(a) a tu Calendario de Contenidos.**

    - **Agregar Evento**: Para ingresar nuevas publicaciones.
    - **Editar/Eliminar Evento**: Ver y modificar/borrar eventos.
    - **Vista Mensual**: Muestra un mes con columnas S1..S5 (semanas).
    - **Vista Anual**: Muestra cada mes en columnas de semanas, con días y fila final de estado.
    """)

    # Botones
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
        st.subheader("Conteo por Estado")
        for estado, count in df["Estado"].value_counts().items():
            st.write(f"- **{estado}**: {count}")
    else:
        st.info("Aún no hay datos o falta la columna 'Estado'.")


def vista_agregar(df, client, sheet_id):
    st.title("Agregar Evento")
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
            st.success("Evento agregado.")


def vista_editar_eliminar(df, client, sheet_id):
    st.title("Editar/Eliminar Evento")

    if df.empty:
        st.info("No hay eventos registrados.")
        return

    st.dataframe(df)

    idxs = df.index.tolist()
    if not idxs:
        return

    sel_idx = st.selectbox("Selecciona fila", idxs, key="sel_index_editar")
    row_data = df.loc[sel_idx]

    with st.form("form_edit"):
        fecha_edit = st.date_input("Fecha", value=row_data["Fecha"] if not pd.isnull(row_data["Fecha"]) else datetime.date.today())
        titulo_edit = st.text_input("Título", value=row_data["Titulo"])
        festividad_edit = st.text_input("Festividad/Efeméride", value=row_data["Festividad"])

        plataformas = ["Instagram","TikTok","Facebook","Otra"]
        if row_data["Plataforma"] in plataformas:
            idx_plat = plataformas.index(row_data["Plataforma"])
        else:
            idx_plat = 0
        plataforma_edit = st.selectbox("Plataforma", plataformas, index=idx_plat)

        estados = ["Planeación","Diseño","Programado","Publicado"]
        if row_data["Estado"] in estados:
            idx_est = estados.index(row_data["Estado"])
        else:
            idx_est = 0
        estado_edit = st.selectbox("Estado", estados, index=idx_est)

        notas_edit = st.text_area("Notas", row_data["Notas"])

        c1, c2 = st.columns(2)
        with c1:
            save_btn = st.form_submit_button("Guardar cambios")
        with c2:
            del_btn = st.form_submit_button("Borrar evento")

        if save_btn:
            df.at[sel_idx, "Fecha"] = fecha_edit
            df.at[sel_idx, "Titulo"] = titulo_edit
            df.at[sel_idx, "Festividad"] = festividad_edit
            df.at[sel_idx, "Plataforma"] = plataforma_edit
            df.at[sel_idx, "Estado"] = estado_edit
            df.at[sel_idx, "Notas"] = notas_edit
            guardar_datos(client, sheet_id, df)
            st.success("¡Cambios guardados!")

        if del_btn:
            df.drop(index=sel_idx, inplace=True)
            df.reset_index(drop=True, inplace=True)
            guardar_datos(client, sheet_id, df)
            st.warning("Evento eliminado.")


def vista_mensual(df):
    st.title("Vista Mensual (Columnas Semanas)")

    if df.empty:
        st.info("No hay datos.")
        return

    # Seleccionar un año y mes
    anios = sorted(df["Fecha"].dropna().dt.year.unique().astype(int))
    if not anios:
        st.warning("No hay años disponibles.")
        return
    anio_sel = st.selectbox("Año", anios)
    df_year = df[df["Fecha"].dt.year == anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return

    # Meses del df_year
    meses_disponibles = sorted(df_year["Fecha"].dt.month.unique().astype(int))
    mes_sel = st.selectbox("Mes", meses_disponibles, format_func=lambda m: NOMBRE_MESES[m-1])

    df_mes = df_year[df_year["Fecha"].dt.month == mes_sel]
    if df_mes.empty:
        st.warning("No hay datos para ese mes.")
        return

    st.markdown(f"## {NOMBRE_MESES[mes_sel-1]} {anio_sel}")

    # 5 columnas => S1..S5
    # Filas => 7 de días + 1 final para estado
    _, ndays = calendar.monthrange(anio_sel, mes_sel)
    # Preparamos la matriz 8x5
    celdas = [["" for _ in range(5)] for _ in range(8)]
    # Encabezados
    for c in range(5):
        celdas[0][c] = f"S{c+1}"

    # Llenar filas 1..7 con días y eventos
    for day_num in range(1, ndays+1):
        col = (day_num-1)//7
        if col>4:
            break
        row = ((day_num-1)%7)+1
        df_day = df_mes[df_mes["Fecha"].dt.day==day_num]
        day_text = f"{day_num}:<br/>"
        if not df_day.empty:
            for _, rowx in df_day.iterrows():
                day_text += f"- {rowx['Titulo']}"
                if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                    day_text += f" ({rowx['Festividad']})"
                day_text += "<br/>"
        celdas[row][col] += day_text

    # Fila 8 => estado (plataformas)
    for c in range(5):
        # days in that col
        start_day = c*7+1
        end_day = min(start_day+6, ndays)
        df_sem = df_mes[df_mes["Fecha"].dt.day.between(start_day, end_day)]
        if df_sem.empty:
            celdas[7][c] = "Sin eventos."
        else:
            plat_counts = {}
            for plat in df_sem["Plataforma"].unique():
                subsetp = df_sem[df_sem["Plataforma"]==plat]
                total = len(subsetp)
                publ = len(subsetp[subsetp["Estado"]=="Publicado"])
                plat_counts[plat] = (publ, total)
            txt = "<strong>Estado:</strong><br/>"
            if not plat_counts:
                txt += "Sin eventos."
            else:
                for p,(pb,tt) in plat_counts.items():
                    txt += f"{p}: {pb}/{tt} publ.<br/>"
            celdas[7][c] = txt

    # Generar HTML
    table_html = []
    table_html.append("<table border='1' style='border-collapse:collapse; width:100%;'>")
    for row_i in range(8):
        table_html.append("<tr>")
        for col_i in range(5):
            cell = celdas[row_i][col_i]
            table_html.append(f"<td style='vertical-align:top; padding:5px;'>{cell}</td>")
        table_html.append("</tr>")
    table_html.append("</table>")

    st.markdown("<div style='width:100%'>"+ "".join(table_html) +"</div>", unsafe_allow_html=True)


def vista_anual(df):
    st.title("Vista Anual (Columnas Semanas)")

    if df.empty:
        st.info("No hay datos.")
        return

    anios = sorted(df["Fecha"].dropna().dt.year.unique().astype(int))
    if not anios:
        st.warning("No hay años disponibles.")
        return

    anio_sel = st.selectbox("Año", anios)
    df_year = df[df["Fecha"].dt.year==anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return

    st.markdown(f"## {anio_sel}")

    # Vamos a generar la misma tabla 8x5 (S1..S5) para cada mes 1..12
    full_html = []
    for mes in range(1,13):
        df_mes = df_year[df_year["Fecha"].dt.month==mes]
        if df_mes.empty:
            continue

        # Titulo
        full_html.append(f"<h3>{NOMBRE_MESES[mes-1]} {anio_sel}</h3>")

        # Llenar la tabla 8x5
        celdas = [["" for _ in range(5)] for _ in range(8)]
        for c in range(5):
            celdas[0][c] = f"S{c+1}"

        # Cuantos días tiene el mes
        _, ndays = calendar.monthrange(anio_sel, mes)
        # Rellenar filas
        for day_num in range(1, ndays+1):
            col = (day_num-1)//7
            if col>4:
                break
            row = ((day_num-1)%7)+1
            df_day = df_mes[df_mes["Fecha"].dt.day==day_num]
            day_text = f"{day_num}:<br/>"
            if not df_day.empty:
                for _, rowx in df_day.iterrows():
                    day_text += f"- {rowx['Titulo']}"
                    if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                        day_text += f" ({rowx['Festividad']})"
                    day_text += "<br/>"
            celdas[row][col] += day_text

        # Fila 8 => estado
        for c in range(5):
            start_day = c*7+1
            end_day = min(start_day+6, ndays)
            df_sem = df_mes[df_mes["Fecha"].dt.day.between(start_day, end_day)]
            if df_sem.empty:
                celdas[7][c] = "Sin eventos."
            else:
                plat_counts = {}
                for plat in df_sem["Plataforma"].unique():
                    subsetp = df_sem[df_sem["Plataforma"]==plat]
                    total = len(subsetp)
                    publ = len(subsetp[subsetp["Estado"]=="Publicado"])
                    plat_counts[plat] = (publ, total)
                txt = "<strong>Estado:</strong><br/>"
                if not plat_counts:
                    txt += "Sin eventos."
                else:
                    for p,(pb,tt) in plat_counts.items():
                        txt += f"{p}: {pb}/{tt} publ.<br/>"
                celdas[7][c] = txt

        # Convertir celdas en HTML
        table_html = ["<table border='1' style='border-collapse:collapse; width:100%;'>"]
        for r in range(8):
            table_html.append("<tr>")
            for co in range(5):
                cell = celdas[r][co]
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
