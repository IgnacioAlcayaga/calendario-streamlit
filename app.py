import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import calendar

# -----------------------------------------------------------------
# 1) st.set_page_config => PRIMER COMANDO
# -----------------------------------------------------------------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

# -----------------------------------------------------------------
# CONSTANTES Y HOJAS
# -----------------------------------------------------------------
DATA_SHEET = "Data"
CONFIG_SHEET = "Config"
COLUMNS = ["Fecha","Titulo","Festividad","Plataforma","Estado","Notas"]

NOMBRE_MESES = [
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
]

# -----------------------------------------------------------------
# CONEXIÓN A GOOGLE SHEETS
# -----------------------------------------------------------------
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
    ws.update(data_to_upload)

# ------------------------
# CONFIG (número requerido por red)
# ------------------------
def cargar_config(client, sheet_id):
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(CONFIG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=CONFIG_SHEET, rows="10", cols="5")
        # Por defecto, valores para 4 redes:
        default_data = [["Red","Requerido"], ["Instagram","5"], ["Facebook","5"], ["TikTok","3"], ["Blog","1"]]
        ws.update("A1", default_data)
        return {"Instagram":5,"Facebook":5,"TikTok":3,"Blog":1}
    data = ws.get_all_values()
    if len(data)<2:
        return {}
    config_dict = {}
    for row in data[1:]:
        if len(row)>=2 and row[0].strip()!="" and row[1].strip()!="":
            # row[0] => Red, row[1] => Requerido
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
    data = [["Red","Requerido"]]
    for red,req in config_dict.items():
        data.append([red,str(req)])
    ws.clear()
    ws.update("A1", data)

# -----------------------------------------------------------------
# PÁGINAS
# -----------------------------------------------------------------
def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")
    st.markdown("""
    **Bienvenido(a)** a tu Calendario de Contenidos.
    - **Agregar Evento**: Crea eventos (fecha, título, plataforma, estado...).
    - **Editar/Eliminar Evento**: Ajusta o borra eventos existentes.
    - **Vista Mensual**: Muestra un mes en bloques semanales (con días y estado).
    - **Vista Anual**: Calendario estilo librería (filas=semanas, días en columnas, estado a la derecha).
    - **Configuración**: Parámetros de publicaciones semanales requeridas por red.
    """)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("Agregar Evento"):
            st.session_state["page"] = "Agregar"
    with col2:
        if st.button("Editar/Eliminar Evento"):
            st.session_state["page"] = "Editar"
    with col3:
        if st.button("Vista Mensual"):
            st.session_state["page"] = "Mensual"
    with col4:
        if st.button("Vista Anual"):
            st.session_state["page"] = "Anual"
    with col5:
        if st.button("Configuración"):
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
        fecha = st.date_input("Fecha", datetime.date.today())
        titulo = st.text_input("Título", "")
        festividad = st.text_input("Festividad/Efeméride", "")
        plataforma = st.selectbox("Plataforma", ["Instagram","Facebook","TikTok","Blog","Otra"])
        estado = st.selectbox("Estado", ["Planeación","Diseño","Programado","Publicado"])
        notas = st.text_area("Notas","")
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
    sel_idx = st.selectbox("Selecciona fila a modificar", idxs)
    row_data = df.loc[sel_idx]
    with st.form("form_editar"):
        fecha_e = st.date_input("Fecha", value=row_data["Fecha"] if not pd.isnull(row_data["Fecha"]) else datetime.date.today())
        titulo_e = st.text_input("Título", value=row_data["Titulo"])
        festividad_e = st.text_input("Festividad/Efeméride", value=row_data["Festividad"])
        plat_options = ["Instagram","Facebook","TikTok","Blog","Otra"]
        if row_data["Plataforma"] in plat_options:
            idx_plat = plat_options.index(row_data["Plataforma"])
        else:
            idx_plat = 0
        plat_e = st.selectbox("Plataforma", plat_options, index=idx_plat)
        estados = ["Planeación","Diseño","Programado","Publicado"]
        if row_data["Estado"] in estados:
            idx_est = estados.index(row_data["Estado"])
        else:
            idx_est = 0
        est_e = st.selectbox("Estado", estados, index=idx_est)
        notas_e = st.text_area("Notas", row_data["Notas"])
        c1,c2 = st.columns(2)
        with c1:
            if st.form_submit_button("Guardar cambios"):
                df.at[sel_idx, "Fecha"] = fecha_e
                df.at[sel_idx, "Titulo"] = titulo_e
                df.at[sel_idx, "Festividad"] = festividad_e
                df.at[sel_idx, "Plataforma"] = plat_e
                df.at[sel_idx, "Estado"] = est_e
                df.at[sel_idx, "Notas"] = notas_e
                guardar_datos(client, sheet_id, df)
                st.success("Cambios guardados!")
        with c2:
            if st.form_submit_button("Borrar evento"):
                df.drop(index=sel_idx, inplace=True)
                df.reset_index(drop=True, inplace=True)
                guardar_datos(client, sheet_id, df)
                st.warning("Evento eliminado.")


def vista_configuracion(client, sheet_id):
    st.title("Configuración - Redes Sociales")
    st.markdown("Define cuántas publicaciones semanales son requeridas para cada red social.")
    config_dict = cargar_config(client, sheet_id)
    if not config_dict:
        config_dict = {"Instagram":5,"Facebook":5,"TikTok":3,"Blog":1}

    nuevos = {}
    st.markdown("### Redes configuradas:")
    for red in sorted(config_dict.keys()):
        col1, col2 = st.columns([2,1])
        with col1:
            st.write(f"**{red}**")
        with col2:
            val = st.number_input(f"Requerido - {red}", min_value=0, value=config_dict[red], key=f"req_{red}")
            nuevos[red] = val

    st.markdown("### Agregar nueva red (opcional)")
    red_nueva = st.text_input("Nombre de la nueva red", "")
    if red_nueva.strip():
        val_nuevo = st.number_input(f"Requerido para {red_nueva}", min_value=0, value=1, key="req_nuevo")
        nuevos[red_nueva.strip()] = val_nuevo

    if st.button("Guardar Configuración"):
        guardar_config(client, sheet_id, nuevos)
        st.success("¡Configuración actualizada!")


def vista_mensual(df, config_dict):
    st.title("Vista Mensual - Semanas")

    # Rango ±10 años
    anio_actual = datetime.date.today().year
    años = list(range(anio_actual-10, anio_actual+11))
    anio_sel = st.selectbox("Año", años, index=años.index(anio_actual))

    df_year = df[df["Fecha"].dt.year==anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return

    meses_disp = sorted(df_year["Fecha"].dt.month.unique().astype(int))
    if not meses_disp:
        st.warning("No hay meses con datos en este año.")
        return

    mes_sel = st.selectbox("Mes", meses_disp, format_func=lambda m: NOMBRE_MESES[m-1])
    df_mes = df_year[df_year["Fecha"].dt.month==mes_sel]
    if df_mes.empty:
        st.warning("No hay datos para este mes.")
        return

    st.markdown(f"## {NOMBRE_MESES[mes_sel-1]} {anio_sel}")

    # Obtenemos cuántos días tiene:
    _, ndays = calendar.monthrange(anio_sel, mes_sel)

    semana_idx = 1
    start_day = 1
    while start_day <= ndays:
        end_day = min(start_day+6, ndays)
        dias_sem = range(start_day, end_day+1)

        st.subheader(f"Semana {semana_idx}")

        # 1) Listado de días
        for d in dias_sem:
            df_day = df_mes[df_mes["Fecha"].dt.day==d]
            if df_day.empty:
                st.write(f"Día {d} (sin eventos)")
            else:
                st.write(f"**Día {d}:**")
                for _, rowx in df_day.iterrows():
                    linea = f"- {rowx['Titulo']}"
                    # Festividad
                    if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                        linea += f" ({rowx['Festividad']})"
                    st.write(linea)

        # 2) Bloque de estado => 2 filas
        df_sem = df_mes[df_mes["Fecha"].dt.day.between(start_day, end_day)]
        if df_sem.empty:
            st.write("Sin eventos esta semana.")
        else:
            # Se muestran todas las redes de config, en orden
            redes_orden = sorted(config_dict.keys())
            # Fila 1 => nombres
            row_names = []
            # Fila 2 => contadores
            row_cnt = []
            for r in redes_orden:
                df_r = df_sem[df_sem["Plataforma"].str.strip().str.lower() == r.strip().lower()]
                # planeado = eventos con estado != 'publicado'
                planeado = len(df_r[ df_r["Estado"].str.strip().str.lower() != "publicado" ])
                requerido = config_dict[r]
                cnt_str = f"{planeado}/{requerido}"
                if planeado == 0:
                    cnt_str = f"<span style='color:red'>{cnt_str}</span>"
                row_names.append(r)
                row_cnt.append(cnt_str)
            # Mostramos en HTML
            st.markdown("<div style='text-align:center; font-weight:bold;'>"+" | ".join(row_names)+"</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;'>"+" | ".join(row_cnt)+"</div>", unsafe_allow_html=True)

        st.write("---")
        semana_idx+=1
        start_day = end_day+1


def vista_anual(df, config_dict):
    st.title("Vista Anual - Calendario Librería + Estado")

    # Rango ±10 años
    anio_actual = datetime.date.today().year
    años = list(range(anio_actual-10, anio_actual+11))
    anio_sel = st.selectbox("Año", años, index=años.index(anio_actual))

    df_year = df[df["Fecha"].dt.year==anio_sel]
    if df_year.empty:
        st.warning("No hay datos en este año.")
        return

    st.markdown(f"## {anio_sel}")

    # CSS: una sola tabla con 9 columnas: col0 => "Sx", col1..7 => días, col8 => estado
    st.markdown("""
    <style>
    table.anual-cal {
        border-collapse: collapse;
        width: 100%;
        table-layout: fixed; /* para celdas uniformes */
    }
    table.anual-cal td, table.anual-cal th {
        border: 1px solid #ccc;
        padding: 4px;
        vertical-align: top;
        text-align: left;
    }
    /* For text truncation to one line with ellipsis: */
    .truncate {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block; 
    }
    /* Alto de la celda para uniformidad (ej 60px) */
    .day-cell {
        height: 60px;
    }
    .state-cell {
        width: 120px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # Generamos HTML para cada mes
    full_html = []
    for mes in range(1,13):
        df_mes = df_year[df_year["Fecha"].dt.month==mes]
        if df_mes.empty:
            # Si no hay datos, igual podrías mostrar un mes vacío, o saltarlo
            continue

        # monthcalendar => lista de semanas, cada semana => 7 ints (0 => no day)
        mat = calendar.monthcalendar(anio_sel, mes)
        # Cabecera con mes
        month_html = [f"<h3>{NOMBRE_MESES[mes-1]} {anio_sel}</h3>"]
        month_html.append("<table class='anual-cal'>")

        # Fila de encabezados => 9
        # col0 => "", col1..7 => L..D, col8 => "Estado"
        # s_name, L, M, X, J, V, S, D, Estado
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
           <th style="width:120px;">Estado</th>
        </tr>
        """)

        # Semanas => filas
        for w_i, week in enumerate(mat):
            s_label = f"S{w_i+1}"
            # Recolectamos day_of_week en un array para luego calcular planeado
            day_nums = []
            row_html = f"<tr><td style='text-align:center;background:#eee;'>{s_label}</td>"
            for d in week:
                if d == 0:
                    # Celda vacía
                    row_html += "<td class='day-cell'></td>"
                    day_nums.append(None)
                else:
                    df_day = df_mes[df_mes["Fecha"].dt.day==d]
                    # Título => una sola línea con ellipsis
                    content = f"<div class='truncate'><strong>{d}</strong> - "
                    if not df_day.empty:
                        # Tomamos el primer evento (o todos en una sola linea?):
                        # haremos un for con una pequeña separacion
                        lines = []
                        for _, rowx in df_day.iterrows():
                            txt = rowx["Titulo"]
                            if pd.notna(rowx["Festividad"]) and rowx["Festividad"].strip():
                                txt += f"({rowx['Festividad']})"
                            lines.append(txt)
                        content += " | ".join(lines)
                    else:
                        content += "Sin eventos"
                    content += "</div>"
                    row_html += f"<td class='day-cell'>{content}</td>"
                    day_nums.append(d)

            # Col final => estado
            valid_days = [d for d in day_nums if d is not None]
            if not valid_days:
                row_html += "<td class='state-cell'>-</td>"
            else:
                df_sem = df_mes[df_mes["Fecha"].dt.day.isin(valid_days)]
                if df_sem.empty:
                    row_html += "<td class='state-cell'>Sin ev.</td>"
                else:
                    # Recolectamos redes en config
                    redes_list = sorted(config_dict.keys())
                    row_plat = []
                    row_cnt = []
                    for r in redes_list:
                        df_r = df_sem[df_sem["Plataforma"].str.strip().str.lower() == r.strip().lower()]
                        planeado = len(df_r[df_r["Estado"].str.lower()!="publicado"])
                        req = config_dict[r]
                        c_str = f"{planeado}/{req}"
                        if planeado == 0:
                            c_str = f"<span style='color:red'>{c_str}</span>"
                        row_plat.append(r)
                        row_cnt.append(c_str)
                    line1 = " | ".join(row_plat)
                    line2 = " | ".join(row_cnt)
                    state_html = f"<div style='font-size:0.8rem'><div class='truncate'>{line1}</div><div class='truncate'>{line2}</div></div>"
                    row_html += f"<td class='state-cell'>{state_html}</td>"
            row_html += "</tr>"
            month_html.append(row_html)

        month_html.append("</table>")
        full_html.append("".join(month_html))

    # Salida final
    st.markdown("<div>"+ "".join(full_html) +"</div>", unsafe_allow_html=True)


def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    client = get_gsheet_connection()
    sheet_id = st.secrets["SHEET_ID"]
    df = cargar_datos(client, sheet_id)
    config_dict = cargar_config(client, sheet_id)

    st.sidebar.title("Navegación")
    if st.sidebar.button("Dashboard"):
        st.session_state["page"] = "Dashboard"
    if st.sidebar.button("Agregar Evento"):
        st.session_state["page"] = "Agregar"
    if st.sidebar.button("Editar/Eliminar Evento"):
        st.session_state["page"] = "Editar"
    if st.sidebar.button("Vista Mensual"):
        st.session_state["page"] = "Mensual"
    if st.sidebar.button("Vista Anual"):
        st.session_state["page"] = "Anual"
    if st.sidebar.button("Configuración"):
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
