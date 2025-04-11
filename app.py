import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
import datetime
import math

# -----------------------------------------------------------------
# 1) set_page_config => PRIMER COMANDO
# -----------------------------------------------------------------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

# --------------------------------------------------------------------------------
# CONFIGURACIÓN DE COLUMNAS Y PESTAÑA DE GOOGLE SHEETS
# --------------------------------------------------------------------------------
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
WORKSHEET_NAME = "Data"

# Paleta de colores para las plataformas
PLATAFORMA_COLORES = {
    "Instagram": "#ffc0cb",  # Rosa
    "TikTok": "#ffffff",     # Blanco
    "Facebook": "#add8e6",   # Azul clarito
    "Otra": "#dddddd"        # Gris
}

NOMBRE_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# --------------------------------------------------------------------------------
# FUNCIONES PARA CONECTAR A GOOGLE SHEETS
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
# FUNCIONES DE SEMANA
# --------------------------------------------------------------------------------
def semana_del_mes(fecha: datetime.date) -> int:
    """
    Retorna un número de semana del mes basado en día // 7 + 1.
    Ej: días 1-7 => Semana 1, días 8-14 => Semana 2, etc.
    """
    dia = fecha.day
    return (dia - 1) // 7 + 1  # 1..5

# --------------------------------------------------------------------------------
# PANTALLAS
# --------------------------------------------------------------------------------
def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown("""
    Bienvenido(a) a tu **Calendario de Contenidos**. 

    **¿Cómo funciona este panel?**  
    - **Agregar Evento**: Agregar nuevas publicaciones (fecha, título, plataforma...).  
    - **Editar/Eliminar Evento**: Ver toda la lista y modificar o borrar.  
    - **Vista Mensual**: Filtra datos por un mes específico, agrupando semanas.  
    - **Vista Anual**: Ve un calendario grande (un mes debajo del otro) y una barra de estado lateral con conteo de publicaciones planeadas/pendientes por plataforma y semana.
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

    if not df.empty:
        if "Estado" in df.columns:
            conteo_estado = df["Estado"].value_counts().to_dict()
            st.subheader("Conteo por Estado")
            for estado, count in conteo_estado.items():
                st.write(f"- **{estado}**: {count}")
        else:
            st.warning("No existe la columna 'Estado' en el DataFrame.")
    else:
        st.info("No hay datos. Empieza creando tu primer Evento.")

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
    st.title("Vista Mensual (con Semanas)")

    if df.empty:
        st.info("No hay datos.")
        return

    nombre_mes = st.selectbox("Selecciona el mes", NOMBRE_MESES, key="selbox_mes")
    mes_index = NOMBRE_MESES.index(nombre_mes) + 1
    df_fil = df[df["Fecha"].dt.month == mes_index]

    if df_fil.empty:
        st.warning(f"No hay datos para {nombre_mes}.")
        return

    # Creamos la columna "SemanaMes"
    df_fil["SemanaMes"] = df_fil["Fecha"].apply(semana_del_mes)
    # Ordenamos
    df_fil = df_fil.sort_values(by=["SemanaMes", "Fecha"])

    st.write(f"### Eventos de {nombre_mes} agrupados por semana")

    # Mostramos un “acordeón” por semana
    semanas = sorted(df_fil["SemanaMes"].unique())
    for sem in semanas:
        subset = df_fil[df_fil["SemanaMes"] == sem]
        st.subheader(f"Semana {sem}")
        # Para cada día en la semana, podemos mostrar una mini-tabla:
        #  (o un st.dataframe con subset)
        st.dataframe(subset.drop(columns=["SemanaMes"], errors="ignore"))

def vista_anual(df):
    st.title("Vista Anual - Calendario + Barra Estado (Plataformas)")

    if df.empty:
        st.info("No hay datos.")
        return

    # Creamos contenedor principal: 2 columnas (calendario a la izq, barra de estado a la derecha)
    col_cal, col_bar = st.columns([3,1])  # 3:1 de ancho

    # --- Lado izquierdo: CALENDARIO ---
    with col_cal:
        st.write("#### Calendario Mensual (1 columna por mes, con días)")

        # CSS con 1 mes por bloque vertical
        html_output = []
        html_output.append("""
        <style>
        .calendar-container {
            display: flex;
            flex-direction: column;
            gap: 2rem;
            width: 100%;
        }
        .month-card {
            border: 2px solid #ccc;
            padding: 0.5rem;
            width: 100%;
        }
        .month-title {
            text-align: center;
            font-weight: bold;
            margin-bottom: 0.5rem;
            font-size: 1.2rem;
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
            font-size: 0.75rem;
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

        df["year"] = df["Fecha"].dt.year
        df["month"] = df["Fecha"].dt.month
        df["day"] = df["Fecha"].dt.day

        anios = df["year"].unique()
        if len(anios) == 1:
            anio = anios[0]
        else:
            anio = st.number_input("Elige año:", value=int(datetime.date.today().year), step=1)

        df_anio = df[df["year"] == anio]
        if df_anio.empty:
            st.warning(f"No hay datos para el año {anio}.")
        else:
            html_output.append('<div class="calendar-container">')

            for mes_idx in range(1, 13):
                df_mes = df_anio[df_anio["month"] == mes_idx]
                try:
                    month_start = datetime.date(int(anio), mes_idx, 1)
                    if mes_idx == 12:
                        next_month = datetime.date(int(anio)+1, 1, 1)
                    else:
                        next_month = datetime.date(int(anio), mes_idx+1, 1)
                    num_dias = (next_month - month_start).days
                    start_weekday = month_start.weekday()
                except:
                    continue

                mes_name = NOMBRE_MESES[mes_idx-1]
                html_output.append(f'<div class="month-card"><div class="month-title">{mes_name} {anio}</div>')
                html_output.append('<div class="days-grid">')

                # Celdas vacías antes del día 1
                for _ in range(start_weekday):
                    html_output.append('<div class="day-cell"></div>')

                for day_num in range(1, num_dias+1):
                    df_day = df_mes[df_mes["day"] == day_num]
                    day_html = f'<span class="day-number">{day_num}</span><br/>'
                    if not df_day.empty:
                        for _, row in df_day.iterrows():
                            plat = row["Plataforma"]
                            color = PLATAFORMA_COLORES.get(plat, "#dddddd")
                            title = (row["Titulo"][:10] + '...') if len(str(row["Titulo"])) > 10 else str(row["Titulo"])
                            fest = (row["Festividad"][:10] + '...') if len(str(row["Festividad"])) > 10 else str(row["Festividad"])
                            day_html += f'<span class="event-label" style="background-color:{color};">{title}'
                            if fest.strip():
                                day_html += f' ({fest})'
                            day_html += '</span>'
                    html_output.append(f'<div class="day-cell">{day_html}</div>')

                html_output.append('</div></div>')  # end days-grid & month-card

            html_output.append('</div>')  # end calendar-container

            st.markdown("\n".join(html_output), unsafe_allow_html=True)

    # --- Lado derecho: BARRA DE ESTADO POR SEMANA/PLATAFORMA ---
    with col_bar:
        st.write("#### Estado Semanal por Plataforma")

        if df_anio.empty:
            st.info("No hay datos para el año seleccionado.")
            return
        # Definir "semana del mes"
        df_anio["SemanaMes"] = df_anio["Fecha"].apply(semana_del_mes)
        # Podríamos agrupar por (month, SemanaMes, Plataforma) y contar
        # Ej: cuántos “Planeación” vs total
        for mes_idx in range(1, 13):
            df_mes = df_anio[df_anio["month"] == mes_idx]
            if df_mes.empty:
                continue

            st.write(f"**{NOMBRE_MESES[mes_idx-1]}**")
            # Semanas del mes
            semanas_mes = sorted(df_mes["SemanaMes"].unique())
            for semana in semanas_mes:
                df_sem = df_mes[df_mes["SemanaMes"] == semana]
                # Agrupamos por plataforma
                if df_sem.empty:
                    continue
                st.write(f"- **Semana {semana}**")
                plataformas_en_sem = df_sem["Plataforma"].unique()
                for plat in plataformas_en_sem:
                    subset_plat = df_sem[df_sem["Plataforma"] == plat]
                    total_eventos = len(subset_plat)
                    planeados = len(subset_plat[subset_plat["Estado"] != "Publicado"])  # o “Planeación” + “Diseño” + “Programado”
                    # O define tu propia forma de contar “planeadas vs. publicadas”
                    # Ej: x planeadas / y tot
                    st.write(f"   - {plat}: {total_eventos - planeados}/{total_eventos} publicadas")

# --------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# --------------------------------------------------------------------------------
def main():
    # No llamamos st.set_page_config aquí: ya lo hicimos al tope
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    client = get_gsheet_connection()
    sheet_id = st.secrets["SHEET_ID"]
    df = cargar_datos(client, sheet_id)

    # Barra lateral
    st.sidebar.title("Navegación Global")
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


