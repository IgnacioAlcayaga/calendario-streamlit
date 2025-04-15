import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import calendar

# -----------------------------------------------------------------
# st.set_page_config DEBE SER EL PRIMER COMANDO de Streamlit
# -----------------------------------------------------------------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

# -----------------------------------------------------------------
# CONSTANTES Y HOJAS
# -----------------------------------------------------------------
DATA_SHEET = "Data"
CONFIG_SHEET = "Config"
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]

NOMBRE_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# Redes fijas por defecto (se pueden agregar nuevas en Configuración)
REDES_PREDEFINIDAS = ["Instagram", "Facebook", "TikTok", "Blog"]

# -----------------------------------------------------------------
# CONEXIÓN CON GOOGLE SHEETS
# -----------------------------------------------------------------
def get_gsheet_connection():
    cred_json_str = st.secrets["gcp_service_account"]
    creds_dict = json.loads(cred_json_str)
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(credentials)

# -----------------------------------------------------------------
# CACHÉ para reducir llamadas a Sheets (TTL=60 segundos)
# -----------------------------------------------------------------
@st.cache_data(ttl=60)
def cargar_datos_cached(client, sheet_id):
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(DATA_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=DATA_SHEET, rows="1000", cols="20")
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
        ws = sh.worksheet(DATA_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=DATA_SHEET, rows="1000", cols="20")
    ws.clear()
    ws.update("A1", data_to_upload)
    st.cache_data.clear()  # Limpiar caché para recargar datos

@st.cache_data(ttl=60)
def cargar_config_cached(client, sheet_id):
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(CONFIG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=CONFIG_SHEET, rows="10", cols="5")
        default_data = [["Red", "Requerido"], ["Instagram", "5"], ["Facebook", "5"], ["TikTok", "3"], ["Blog", "1"]]
        ws.update("A1", default_data)
        return {"Instagram": 5, "Facebook": 5, "TikTok": 3, "Blog": 1}
    data = ws.get_all_values()
    if len(data) < 2:
        return {}
    config_dict = {}
    for row in data[1:]:
        if len(row) >= 2 and row[0].strip() != "" and row[1].strip() != "":
            try:
                config_dict[row[0].strip()] = int(row[1])
            except:
                config_dict[row[0].strip()] = 0
    return config_dict

def guardar_config(client, sheet_id, config_dict):
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(CONFIG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=CONFIG_SHEET, rows="10", cols="5")
    data = [["Red", "Requerido"]]
    for red, req in config_dict.items():
        data.append([red, str(req)])
    ws.clear()
    ws.update("A1", data)
    st.cache_data.clear()

# -----------------------------------------------------------------
# PÁGINAS DE LA APP
# -----------------------------------------------------------------
def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")
    st.markdown("""
    **Bienvenido(a)** a tu Calendario de Contenidos.
    
    - **Agregar Evento**: Crea nuevos eventos.
    - **Editar/Eliminar Evento**: Modifica o elimina eventos.
    - **Vista Mensual**: Visualiza un mes agrupado por semanas.
    - **Vista Anual**: Visualiza el calendario anual estilo librería con estados.
    - **Configuración**: Establece la cantidad requerida de publicaciones por red.
    """)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("Agregar Evento", key="btn_dash_agregar"):
            st.session_state["page"] = "Agregar"
    with col2:
        if st.button("Editar/Eliminar Evento", key="btn_dash_editar"):
            st.session_state["page"] = "Editar"
    with col3:
        if st.button("Vista Mensual", key="btn_dash_mensual"):
            st.session_state["page"] = "Mensual"
    with col4:
        if st.button("Vista Anual", key="btn_dash_anual"):
            st.session_state["page"] = "Anual"
    with col5:
        if st.button("Configuración", key="btn_dash_config"):
            st.session_state["page"] = "Config"

    st.write("---")
    st.metric("Total de eventos", len(df))
    if not df.empty and "Estado" in df.columns:
        st.subheader("Conteo de Estados")
        for est, cnt in df["Estado"].value_counts().items():
            st.write(f"- **{est}**: {cnt}")
    else:
        st.info("No hay datos o falta la columna 'Estado'.")

def vista_agregar(df, client, sheet_id):
    st.title("Agregar Evento")
    with st.form("form_agregar", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.date.today(), key="agregar_fecha")
        titulo = st.text_input("Título", "", key="agregar_titulo")
        festividad = st.text_input("Festividad/Efeméride", "", key="agregar_festividad")
        plataforma = st.selectbox("Plataforma", ["Instagram", "Facebook", "TikTok", "Blog", "Otra"], key="agregar_plataforma")
        estado = st.selectbox("Estado", ["Planeación", "Diseño", "Programado", "Publicado"], key="agregar_estado")
        notas = st.text_area("Notas", "", key="agregar_notas")
        if st.form_submit_button("Guardar Evento", key="btn_guardar_agregar"):
            nuevo = {"Fecha": fecha, "Titulo": titulo, "Festividad": festividad,
                     "Plataforma": plataforma, "Estado": estado, "Notas": notas}
            df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
            guardar_datos(client, sheet_id, df)
            st.success("Evento agregado con éxito.")

def vista_editar_eliminar(df, client, sheet_id):
    st.title("Editar/Eliminar Evento")
    if df.empty:
        st.info("No hay eventos registrados.")
        return
    st.dataframe(df)
    idxs = df.index.tolist()
    if not idxs:
        return
    sel_idx = st.selectbox("Selecciona la fila a modificar", idxs, key="sel_idx_editar")
    row = df.loc[sel_idx]
    with st.form("form_editar", clear_on_submit=True):
        fecha_e = st.date_input("Fecha", value=row["Fecha"] if not pd.isnull(row["Fecha"]) else datetime.date.today(), key="editar_fecha")
        titulo_e = st.text_input("Título", value=row["Titulo"], key="editar_titulo")
        festividad_e = st.text_input("Festividad/Efeméride", value=row["Festividad"], key="editar_festividad")
        plat_options = ["Instagram", "Facebook", "TikTok", "Blog", "Otra"]
        idx_plat = plat_options.index(row["Plataforma"]) if row["Plataforma"] in plat_options else 0
        plat_e = st.selectbox("Plataforma", plat_options, index=idx_plat, key="editar_plataforma")
        estados = ["Planeación", "Diseño", "Programado", "Publicado"]
        idx_est = estados.index(row["Estado"]) if row["Estado"] in estados else 0
        est_e = st.selectbox("Estado", estados, index=idx_est, key="editar_estado")
        notas_e = st.text_area("Notas", value=row["Notas"], key="editar_notas")
        c1, c2 = st.columns(2)
        with c1:
            if st.form_submit_button("Guardar Cambios", key="btn_guardar_editar"):
                df.at[sel_idx, "Fecha"] = fecha_e
                df.at[sel_idx, "Titulo"] = titulo_e
                df.at[sel_idx, "Festividad"] = festividad_e
                df.at[sel_idx, "Plataforma"] = plat_e
                df.at[sel_idx, "Estado"] = est_e
                df.at[sel_idx, "Notas"] = notas_e
                guardar_datos(client, sheet_id, df)
                st.success("Cambios guardados!")
        with c2:
            if st.form_submit_button("Borrar Evento", key="btn_borrar_editar"):
                df.drop(index=sel_idx, inplace=True)
                df.reset_index(drop=True, inplace=True)
                guardar_datos(client, sheet_id, df)
                st.warning("Evento eliminado.")

def vista_configuracion(client, sheet_id):
    st.title("Configuración - Redes Sociales")
    st.markdown("Define la cantidad requerida de publicaciones semanales para cada red social.")
    config = cargar_config_cached(client, sheet_id)
    if not config:
        config = {"Instagram": 5, "Facebook": 5, "TikTok": 3, "Blog": 1}
    nuevos_config = {}
    st.markdown("### Redes Configuradas")
    for red in sorted(config.keys()):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{red}**:")
        with col2:
            valor = st.number_input(f"Requerido para {red}", min_value=0, value=int(config[red]), key=f"config_{red}")
            nuevos_config[red] = valor
    st.markdown("### Agregar Nueva Red")
    red_nueva = st.text_input("Nueva Red (deja vacío si no)", key="nueva_red")
    if red_nueva.strip() != "":
        nuevo_valor = st.number_input(f"Requerido para {red_nueva}", min_value=0, value=1, key="config_nueva_red")
        nuevos_config[red_nueva.strip()] = nuevo_valor
    if st.button("Guardar Configuración", key="btn_guardar_config"):
        guardar_config(client, sheet_id, nuevos_config)
        st.success("Configuración actualizada.")

def vista_mensual(df, config):
    st.title("Vista Mensual - Semanas")
    anio_actual = datetime.date.today().year
    años = list(range(anio_actual - 10, anio_actual + 11))
    anio_sel = st.selectbox("Año", años, index=años.index(anio_actual), key="mensual_anio")
    df_year = df[df["Fecha"].dt.year == anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return
    meses_disp = sorted(df_year["Fecha"].dt.month.unique().astype(int))
    mes_sel = st.selectbox("Mes", meses_disp, format_func=lambda m: NOMBRE_MESES[m - 1], key="mensual_mes")
    df_mes = df_year[df_year["Fecha"].dt.month == mes_sel]
    if df_mes.empty:
        st.warning("No hay datos para este mes.")
        return

    st.markdown(f"## {NOMBRE_MESES[mes_sel - 1]} {anio_sel}")

    # Dividir el mes en semanas (1-7, 8-14, etc.)
    _, ndays = calendar.monthrange(anio_sel, mes_sel)
    semana_idx = 1
    start_day = 1
    while start_day <= ndays:
        end_day = min(start_day + 6, ndays)
        dias_sem = range(start_day, end_day + 1)
        st.subheader(f"Semana {semana_idx}")
        # Listado de días y eventos
        for d in dias_sem:
            df_day = df_mes[df_mes["Fecha"].dt.day == d]
            if df_day.empty:
                st.write(f"Día {d}: (sin eventos)")
            else:
                events = []
                for _, row in df_day.iterrows():
                    ev = f"{row['Titulo']}"
                    if pd.notna(row['Festividad']) and row['Festividad'].strip():
                        ev += f" ({row['Festividad']})"
                    events.append(ev)
                st.write(f"Día {d}: " + " | ".join(events))
        # Mostrar estado en una fila horizontal con cada red en una columna
        df_semana = df_mes[df_mes["Fecha"].dt.day.between(start_day, end_day)]
        cols_state = st.columns(len(config))
        redes_orden = sorted(config.keys())
        for i, r in enumerate(redes_orden):
            df_r = df_semana[df_semana["Plataforma"].str.strip().str.lower() == r.strip().lower()]
            planeado = len(df_r[df_r["Estado"].str.strip().str.lower() != "publicado"])
            requerido = config[r]
            cnt_str = f"{planeado}/{requerido}"
            if planeado == 0:
                cnt_str = f"<span style='color:red'>{cnt_str}</span>"
            with cols_state[i]:
                st.markdown(f"**{r}**", unsafe_allow_html=True)
                st.markdown(cnt_str, unsafe_allow_html=True)
        st.write("---")
        semana_idx += 1
        start_day = end_day + 1

def vista_anual(df, config):
    st.title("Vista Anual - Calendario Librería + Estado")
    anio_actual = datetime.date.today().year
    años = list(range(anio_actual - 10, anio_actual + 11))
    anio_sel = st.selectbox("Año", años, index=años.index(anio_actual), key="anual_anio")
    df_year = df[df["Fecha"].dt.year == anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return
    st.markdown(f"## {anio_sel}")
    # CSS para la tabla
    st.markdown("""
    <style>
    table.anual-cal {
        border-collapse: collapse;
        width: 100%;
        table-layout: fixed;
    }
    table.anual-cal td, table.anual-cal th {
        border: 1px solid #ccc;
        padding: 4px;
        vertical-align: middle;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
    .state-cell {
        width: 120px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    full_html = []
    for mes in range(1, 13):
        df_mes = df_year[df_year["Fecha"].dt.month == mes]
        if df_mes.empty:
            continue
        month_html = [f"<h3>{NOMBRE_MESES[mes-1]} {anio_sel}</h3>"]
        month_html.append("<table class='anual-cal'>")
        month_html.append("""
        <tr>
           <th style="width:40px;"> </th>
           <th>L</th>
           <th>M</th>
           <th>X</th>
           <th>J</th>
           <th>V</th>
           <th>S</th>
           <th>D</th>
           <th class="state-cell">Estado</th>
        </tr>
        """)
        mat = calendar.monthcalendar(anio_sel, mes)
        for w_i, week in enumerate(mat):
            s_label = f"S{w_i+1}"
            row_html = f"<tr><td style='text-align:center;background:#eee;'>{s_label}</td>"
            day_nums = []
            for d in week:
                if d == 0:
                    row_html += "<td></td>"
                    day_nums.append(None)
                else:
                    df_day = df_mes[df_mes["Fecha"].dt.day == d]
                    content = f"<strong>{d}</strong> - "
                    if not df_day.empty:
                        events = []
                        for _, rowx in df_day.iterrows():
                            evt = f"{rowx['Titulo']}"
                            if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                                evt += f"({rowx['Festividad']})"
                            events.append(evt)
                        content += " | ".join(events)
                    else:
                        content += "Sin eventos"
                    row_html += f"<td>{content}</td>"
                    day_nums.append(d)
            valid_days = [d for d in day_nums if d is not None]
            if not valid_days:
                state_html = "-"
            else:
                df_sem = df_mes[df_mes["Fecha"].dt.day.isin(valid_days)]
                redes = sorted(config.keys())
                state_parts = []
                for r in redes:
                    df_r = df_sem[df_sem["Plataforma"].str.strip().str.lower() == r.strip().lower()]
                    planeado = len(df_r[df_r["Estado"].str.strip().str.lower() != "publicado"])
                    requerido = config[r]
                    cnt_str = f"{planeado}/{requerido}"
                    if planeado == 0:
                        cnt_str = f"<span style='color:red'>{cnt_str}</span>"
                    state_parts.append(f"{r}: {cnt_str}")
                state_html = " <br/> ".join(state_parts)
            row_html += f"<td class='state-cell'>{state_html}</td>"
            row_html += "</tr>"
            month_html.append(row_html)
        month_html.append("</table>")
        full_html.append("".join(month_html))
    st.markdown("".join(full_html), unsafe_allow_html=True)

def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    client = get_gsheet_connection()
    sheet_id = st.secrets["SHEET_ID"]
    df = cargar_datos_cached(client, sheet_id)
    config_dict = cargar_config_cached(client, sheet_id)

    st.sidebar.title("Navegación")
    if st.sidebar.button("Dashboard", key="side_dashboard"):
        st.session_state["page"] = "Dashboard"
    if st.sidebar.button("Agregar Evento", key="side_agregar"):
        st.session_state["page"] = "Agregar"
    if st.sidebar.button("Editar/Eliminar Evento", key="side_editar"):
        st.session_state["page"] = "Editar"
    if st.sidebar.button("Vista Mensual", key="side_mensual"):
        st.session_state["page"] = "Mensual"
    if st.sidebar.button("Vista Anual", key="side_anual"):
        st.session_state["page"] = "Anual"
    if st.sidebar.button("Configuración", key="side_config"):
        st.session_state["page"] = "Config"

    page = st.session_state["page"]
    if page == "Dashboard":
        dashboard(df)
    elif page == "Agregar":
        vista_agregar(df, client, sheet_id)
    elif page == "Editar":
        vista_editar_eliminar(df, client, sheet_id)
    elif page == "Mensual":
        vista_mensual(df, config_dict)
    elif page == "Anual":
        vista_anual(df, config_dict)
    elif page == "Config":
        vista_configuracion(client, sheet_id)

if __name__ == "__main__":
    main()
