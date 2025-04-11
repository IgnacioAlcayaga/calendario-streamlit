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
# CONFIGURACIÓN DE COLUMNAS Y PESTAÑA DE GOOGLE SHEETS
# --------------------------------------------------------------------------------
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
WORKSHEET_NAME = "Data"

# Paleta de colores (opcional) para cada plataforma
PLATAFORMA_COLORES = {
    "Instagram": "#ffc0cb",  # Rosa
    "TikTok": "#ffffff",     # Blanco
    "Facebook": "#add8e6",   # Azul clarito
    "Otra": "#dddddd"        # Gris
}

# Nombres de meses en español
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
# OTRAS FUNCIONES
# --------------------------------------------------------------------------------
def semanas_del_mes(anio: int, mes: int):
    """
    Devuelve una lista de tuplas [(semanaN, dias)] para un mes dado.
    Cada tupla: (sX, [listado de días]).
    Ejemplo: (S1, [1,2,3,4]), (S2,[5,6,7,8,9]) ...
    """
    import calendar
    c = calendar.monthrange(anio, mes)  # (weekday_of_first_day, number_of_days_in_month)
    num_dias = c[1]
    # Repartir días en S1, S2, S3...
    semanas = []
    # Ej: S1 => días 1..7, S2 => 8..14, etc.  (Tú ajusta la lógica si prefieres lunes=0, etc.)
    # Simple approach: 7 días por “semana”
    start = 1
    semana_index = 1
    while start <= num_dias:
        end = min(start + 6, num_dias)
        dias_semana = list(range(start, end+1))
        semanas.append((f"S{semana_index}", dias_semana))
        semana_index += 1
        start = end + 1
    return semanas

def contar_publicaciones_por_semana(df_mes, dias_semana):
    """
    Dado un DF (filtrado al mes) y una lista de días (ej. [1,2,3,4]),
    retorna un dict con {plataforma: (numPublicadas, totalEventos)} para esa 'semana'.
    'publicado' se interpretará como 'Estado' == 'Publicado'.
    """
    # Filtramos las filas donde day in dias_semana
    df_sem = df_mes[df_mes["Fecha"].dt.day.isin(dias_semana)]
    # Agrupamos por plataforma
    res = {}
    for plat in df_sem["Plataforma"].unique():
        df_plat = df_sem[df_sem["Plataforma"] == plat]
        total = len(df_plat)
        publicadas = len(df_plat[df_plat["Estado"] == "Publicado"])
        res[plat] = (publicadas, total)
    return res

# --------------------------------------------------------------------------------
# PANTALLAS
# --------------------------------------------------------------------------------

def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown("""
    Bienvenido(a) a tu **Calendario de Contenidos**. 

    - **Agregar Evento**: ingresa nuevas publicaciones (fecha, título, plataforma...).  
    - **Editar/Eliminar Evento**: lista completa para modificar o borrar.  
    - **Vista Mensual**: ver un mes con columnas de semanas.  
    - **Vista Anual**: ver cada mes como una tabla de semanas, con estado (por plataforma) al pie.
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
            st.warning("No existe la columna 'Estado'.")
    else:
        st.info("No hay datos aún. Agrega algún evento para comenzar.")


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
    st.title("Vista Mensual (columnas = Semanas)")

    if df.empty:
        st.info("No hay datos.")
        return

    # Elegir mes y año
    anios = sorted(df["Fecha"].dt.year.dropna().unique().astype(int))
    if len(anios)==0:
        st.warning("No hay fechas válidas.")
        return

    anio_sel = st.selectbox("Selecciona el Año", anios, index=0)
    meses_disponibles = sorted(df[df["Fecha"].dt.year==anio_sel]["Fecha"].dt.month.unique().astype(int))
    mes_sel = st.selectbox("Selecciona el Mes", meses_disponibles, format_func=lambda x: NOMBRE_MESES[x-1])

    df_mes = df[(df["Fecha"].dt.year==anio_sel)&(df["Fecha"].dt.month==mes_sel)].copy()
    if df_mes.empty:
        st.warning("No hay datos para ese mes.")
        return

    # Calcular semanas del mes
    sem_list = semanas_del_mes(anio_sel, mes_sel)  # [(S1,[1..x]), (S2,[x+1..y])...]

    # Haremos una tabla: fila 1 => "S1", "S2",..., fila 2 => días / eventos, fila 3 => status
    # Generamos HTML
    mes_html = []
    mes_html.append(f"<h3>{NOMBRE_MESES[mes_sel-1]} {anio_sel}</h3>")
    mes_html.append("<table border='1' style='border-collapse:collapse; width:100%;'>")

    # Encabezado (semana)
    mes_html.append("<tr>")
    for (sem_name, dias_sem) in sem_list:
        mes_html.append(f"<th>{sem_name}</th>")
    mes_html.append("</tr>")

    # Fila de días/eventos
    mes_html.append("<tr>")
    for (sem_name, dias_sem) in sem_list:
        # Filtrar eventos de esos días
        df_sem = df_mes[df_mes["Fecha"].dt.day.isin(dias_sem)]
        # Construir texto
        cell_text = ""
        for day_num in dias_sem:
            # Filtrar day
            day_events = df_sem[df_sem["Fecha"].dt.day == day_num]
            if len(day_events)>0:
                # Podemos poner un “Day X: Título”
                cell_text += f"<strong>{day_num}</strong>:<br/>"
                for _, row in day_events.iterrows():
                    # Título + Festividad
                    cell_text += f"- {row['Titulo']}"
                    if pd.notna(row["Festividad"]) and row["Festividad"].strip():
                        cell_text += f" ({row['Festividad']})"
                    cell_text += "<br/>"
            else:
                # Sin eventos
                cell_text += f"{day_num}<br/>"
            cell_text += "<hr style='margin:2px;'/>"
        mes_html.append(f"<td style='vertical-align:top; padding:5px;'>{cell_text}</td>")
    mes_html.append("</tr>")

    # Fila de “estado” por plataforma
    mes_html.append("<tr>")
    for (sem_name, dias_sem) in sem_list:
        # Contar publicadas vs total en cada plataforma
        df_sem = df_mes[df_mes["Fecha"].dt.day.isin(dias_sem)]
        plat_counts = {}
        for plat in df_sem["Plataforma"].unique():
            dfp = df_sem[df_sem["Plataforma"]==plat]
            total = len(dfp)
            publ = len(dfp[dfp["Estado"]=="Publicado"])
            plat_counts[plat] = (publ, total)

        # Armar texto: "IG 2/5, FB 1/4..."
        cell_text = "<strong>Estado:</strong><br/>"
        if len(plat_counts)==0:
            cell_text += "Sin eventos."
        else:
            for plat, (p, t) in plat_counts.items():
                cell_text += f"{plat}: {p}/{t} publicadas<br/>"

        mes_html.append(f"<td style='vertical-align:top; padding:5px;'>{cell_text}</td>")
    mes_html.append("</tr>")

    mes_html.append("</table>")

    # Lo mostramos
    st.markdown("".join(mes_html), unsafe_allow_html=True)


def vista_anual(df):
    st.title("Vista Anual (mes con columnas = semanas)")

    if df.empty:
        st.info("No hay datos.")
        return

    anios = sorted(df["Fecha"].dt.year.dropna().unique().astype(int))
    if len(anios)==0:
        st.warning("No hay fechas válidas.")
        return

    anio_sel = st.selectbox("Selecciona el Año", anios, index=0)
    df_anio = df[df["Fecha"].dt.year==anio_sel].copy()
    if df_anio.empty:
        st.warning("No hay datos para ese año.")
        return

    st.markdown(f"## {anio_sel}")

    # Para cada mes 1..12, construimos tabla igual que en vista_mensual
    full_html = []
    for mes in range(1,13):
        df_mes = df_anio[df_anio["Fecha"].dt.month==mes]
        if len(df_mes)==0:
            # Mes sin eventos, igual podemos mostrarlo o no
            continue

        sem_list = semanas_del_mes(anio_sel, mes)
        # Encabezado
        table_html = []
        table_html.append(f"<h3>{NOMBRE_MESES[mes-1]} {anio_sel}</h3>")
        table_html.append("<table border='1' style='border-collapse:collapse; width:100%;'>")

        # Fila 1 => sem_name
        table_html.append("<tr>")
        for (sem_name, dias_sem) in sem_list:
            table_html.append(f"<th>{sem_name}</th>")
        table_html.append("</tr>")

        # Fila 2 => días + eventos
        table_html.append("<tr>")
        for (sem_name, dias_sem) in sem_list:
            # Filtrar filas
            df_sem = df_mes[df_mes["Fecha"].dt.day.isin(dias_sem)]
            cell_text = ""
            for d in dias_sem:
                day_events = df_sem[df_sem["Fecha"].dt.day==d]
                if len(day_events)>0:
                    cell_text += f"<strong>{d}</strong>:<br/>"
                    for _, row in day_events.iterrows():
                        cell_text += f"- {row['Titulo']}"
                        if pd.notna(row['Festividad']) and row['Festividad'].strip():
                            cell_text += f" ({row['Festividad']})"
                        cell_text += "<br/>"
                else:
                    # Sin evento
                    cell_text += f"{d}<br/>"
                cell_text += "<hr style='margin:2px;'/>"
            table_html.append(f"<td style='vertical-align:top; padding:5px;'>{cell_text}</td>")
        table_html.append("</tr>")

        # Fila 3 => estado por plataforma
        table_html.append("<tr>")
        for (sem_name, dias_sem) in sem_list:
            df_sem = df_mes[df_mes["Fecha"].dt.day.isin(dias_sem)]
            plat_counts = {}
            for plat in df_sem["Plataforma"].unique():
                dfp = df_sem[df_sem["Plataforma"]==plat]
                total = len(dfp)
                publ = len(dfp[dfp["Estado"]=="Publicado"])
                plat_counts[plat] = (publ, total)

            cell_text = "<strong>Estado:</strong><br/>"
            if len(plat_counts)==0:
                cell_text += "Sin eventos."
            else:
                for plat,(p,t) in plat_counts.items():
                    cell_text += f"{plat}: {p}/{t} publ.<br/>"

            table_html.append(f"<td style='vertical-align:top; padding:5px;'>{cell_text}</td>")
        table_html.append("</tr>")

        table_html.append("</table>")
        # Agregamos al full_html
        full_html.append("".join(table_html))

    # Mostrar todo
    st.markdown("<div style='width:100%'>"+ "".join(full_html) +"</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# --------------------------------------------------------------------------------
def main():
    # Nota: st.set_page_config() ya se llamó arriba
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    # Conexión
    client = get_gsheet_connection()
    sheet_id = st.secrets["SHEET_ID"]
    df = cargar_datos(client, sheet_id)

    # Barra lateral
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

    # Navegación
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


