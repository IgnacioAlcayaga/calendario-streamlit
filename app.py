import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import calendar

# --------------------------------------------------------------------------------
# 1) st.set_page_config() debe ser EL PRIMER COMANDO de Streamlit
# --------------------------------------------------------------------------------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

# --------------------------------------------------------------------------------
# CONFIGURACIÓN – HOJAS Y CONSTANTES
# --------------------------------------------------------------------------------
# Hoja de eventos
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
DATA_SHEET = "Data"
# Hoja de configuración
CONFIG_SHEET = "Config"  # En Config se almacenará: columnas ["Red","Requerido"]

# Orden predefinido de redes (se mostrarán en este orden en ambas vistas)
REDES_PREDEFINIDAS = ["Instagram", "Facebook", "TikTok", "Blog"]

# Nombres de meses
NOMBRE_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# --------------------------------------------------------------------------------
# CONEXIÓN CON GOOGLE SHEETS (misma para DATA y CONFIG)
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

# Funciones para la hoja de Data
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

# Funciones para la hoja de Configuración
def cargar_config(client, sheet_id):
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(CONFIG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        # Si no existe, crear con los valores por defecto
        ws = sh.add_worksheet(title=CONFIG_SHEET, rows="10", cols="5")
        default_data = [["Red", "Requerido"]]
        for red in REDES_PREDEFINIDAS:
            # Valores por defecto: Instagram:5, Facebook:5, TikTok:3, Blog:1
            default_val = {"Instagram":5, "Facebook":5, "TikTok":3, "Blog":1}.get(red, 1)
            default_data.append([red, default_val])
        ws.update("A1", default_data)
        return {row[0]: int(row[1]) for row in default_data[1:]}
    data = ws.get_all_values()
    if len(data) < 2:
        return {}
    # Asumimos que la primera fila son headers: ["Red", "Requerido"]
    config_dict = {}
    for row in data[1:]:
        if len(row) >= 2 and row[0].strip() != "" and row[1].strip() != "":
            config_dict[row[0].strip()] = int(row[1])
    return config_dict

def guardar_config(client, sheet_id, config_dict):
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(CONFIG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=CONFIG_SHEET, rows="10", cols="5")
    # Crear data en formato de lista: encabezados y luego filas.
    data = [["Red", "Requerido"]]
    for red, req in config_dict.items():
        data.append([red, str(req)])
    ws.clear()
    ws.update("A1", data)

# --------------------------------------------------------------------------------
# PÁGINAS DE LA APP
# --------------------------------------------------------------------------------

def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")
    st.markdown("""
    **Bienvenido(a)** a tu Calendario de Contenidos.
    
    - **Agregar Evento**: Crea nuevas publicaciones.
    - **Editar/Eliminar Evento**: Modifica o elimina eventos.
    - **Vista Mensual**: Visualiza un mes en bloques semanales con listado de días y estado.
    - **Vista Anual**: Visualiza un calendario anual estilo librería, con estado al costado.
    - **Configuración**: Establece la cantidad requerida de publicaciones para cada red.
    """)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("Agregar Evento", key="dash_agregar"):
            st.session_state["page"] = "Agregar"
    with col2:
        if st.button("Editar/Eliminar Evento", key="dash_editar"):
            st.session_state["page"] = "Editar"
    with col3:
        if st.button("Vista Mensual", key="dash_mensual"):
            st.session_state["page"] = "Mensual"
    with col4:
        if st.button("Vista Anual", key="dash_anual"):
            st.session_state["page"] = "Anual"
    with col5:
        if st.button("Configuración", key="dash_config"):
            st.session_state["page"] = "Configuracion"

    st.write("---")
    st.metric("Total de eventos", len(df))
    if not df.empty and "Estado" in df.columns:
        st.subheader("Conteo de Estados")
        for estado, count in df["Estado"].value_counts().items():
            st.write(f"- **{estado}**: {count}")
    else:
        st.info("No hay datos o falta la columna 'Estado'.")

def vista_agregar(df, client, sheet_id):
    st.title("Agregar Evento")
    with st.form("form_agregar", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.date.today())
        titulo = st.text_input("Título", "")
        festividad = st.text_input("Festividad/Efeméride", "")
        plataforma = st.selectbox("Plataforma", REDES_PREDEFINIDAS + ["Otra"])
        estado = st.selectbox("Estado", ["Planeación", "Diseño", "Programado", "Publicado"])
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
    sel_idx = st.selectbox("Selecciona la fila a modificar", idxs, key="sel_index_editar")
    row = df.loc[sel_idx]
    with st.form("form_editar"):
        fecha_e = st.date_input("Fecha", value=row["Fecha"] if not pd.isnull(row["Fecha"]) else datetime.date.today())
        titulo_e = st.text_input("Título", value=row["Titulo"])
        festividad_e = st.text_input("Festividad/Efeméride", value=row["Festividad"])
        plat_options = REDES_PREDEFINIDAS + ["Otra"]
        idx_plat = plat_options.index(row["Plataforma"]) if row["Plataforma"] in plat_options else 0
        plat_e = st.selectbox("Plataforma", plat_options, index=idx_plat)
        estados = ["Planeación", "Diseño", "Programado", "Publicado"]
        idx_est = estados.index(row["Estado"]) if row["Estado"] in estados else 0
        est_e = st.selectbox("Estado", estados, index=idx_est)
        notas_e = st.text_area("Notas", row["Notas"])
        c1, c2 = st.columns(2)
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
    st.title("Configuración de Redes Sociales")
    st.markdown("Define la cantidad requerida de publicaciones semanales para cada red social.")
    config = cargar_config(client, sheet_id)
    # Si no hay configuración, usamos valores por defecto
    if not config:
        config = {"Instagram":5, "Facebook":5, "TikTok":3, "Blog":1}
    nuevos_config = {}
    # Permitir editar cada red configurada
    for red in sorted(config.keys()):
        col1, col2 = st.columns([2,1])
        with col1:
            st.write(f"**{red}**")
        with col2:
            valor = st.number_input(f"Requerido para {red}", min_value=0, value=int(config[red]), key=f"config_{red}")
            nuevos_config[red] = valor
    # Opción para agregar nueva red
    red_nueva = st.text_input("Agregar nueva red (deja vacío si no)", key="red_nueva")
    if red_nueva.strip() != "":
        nuevo_valor = st.number_input(f"Requerido para {red_nueva}", min_value=0, value=1, key="config_nueva")
        nuevos_config[red_nueva.strip()] = nuevo_valor

    if st.button("Guardar Configuración", key="btn_config_guardar"):
        guardar_config(client, sheet_id, nuevos_config)
        st.success("Configuración actualizada.")

def vista_mensual(df, config):
    """
    Vista Mensual:
    - Seleccionar Año y Mes (rango de ±10 años).
    - Para cada semana (dividido en días 1-7, 8-14, etc.):
         * Mostrar título "Semana X"
         * Listado de cada día con los eventos (como en la edición de evento).
         * Debajo, mostrar un bloque de estado con dos líneas:
             - Línea 1: Nombres de redes (según la configuración, fijas).
             - Línea 2: Para cada red, mostrar "planeado/requerido" (planeado = eventos con estado != "Publicado").
             - Si planeado == 0, se muestra en rojo.
    """
    st.title("Vista Mensual - Bloques por Semana")

    # Rango de años: ±10 años respecto al actual
    anio_actual = datetime.date.today().year
    años = list(range(anio_actual-10, anio_actual+11))
    anio_sel = st.selectbox("Año", años, index=años.index(anio_actual))
    df_year = df[df["Fecha"].dt.year==anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return
    meses_disp = sorted(df_year["Fecha"].dt.month.unique().astype(int))
    mes_sel = st.selectbox("Mes", meses_disp, format_func=lambda m: NOMBRE_MESES[m-1])
    df_mes = df_year[df_year["Fecha"].dt.month==mes_sel]
    if df_mes.empty:
        st.warning("No hay datos para ese mes.")
        return

    st.markdown(f"## {NOMBRE_MESES[mes_sel-1]} {anio_sel}")
    _, ndays = calendar.monthrange(anio_sel, mes_sel)
    semana_idx = 1
    start_day = 1
    while start_day <= ndays:
        end_day = min(start_day+6, ndays)
        dias_sem = list(range(start_day, end_day+1))
        st.subheader(f"Semana {semana_idx}")
        # Listado de días con eventos:
        for d in dias_sem:
            df_day = df_mes[df_mes["Fecha"].dt.day==d]
            if df_day.empty:
                st.write(f"Día {d} (sin eventos)")
            else:
                st.write(f"**Día {d}:**")
                for _, row in df_day.iterrows():
                    linea = f"- {row['Titulo']}"
                    if pd.notna(row['Festividad']) and row['Festividad'].strip():
                        linea += f" ({row['Festividad']})"
                    st.write(linea)
        # Bloque de estado: dos filas
        df_sem = df_mes[df_mes["Fecha"].dt.day.between(start_day, end_day)]
        if df_sem.empty:
            st.write("Sin publicaciones esta semana.")
        else:
            # Usar el orden de redes basado en la configuración (mostrar siempre todas)
            redes = list(config.keys())
            row_nombres = []
            row_cuentas = []
            for red in redes:
                # Eventos de la red en la semana
                df_red = df_sem[df_sem["Plataforma"]==red]
                total = len(df_red)
                # Planeado: aquellos que no tienen estado "Publicado"
                planeado = len(df_red[df_red["Estado"]!="Publicado"])
                # Si planeado es 0, pintar ese número en rojo usando HTML simple
                cuenta_str = f"{planeado}/{config[red]}"
                if planeado == 0:
                    cuenta_str = f"<span style='color:red'>{cuenta_str}</span>"
                row_nombres.append(red)
                row_cuentas.append(cuenta_str)
            st.markdown(" | ".join(row_nombres), unsafe_allow_html=True)
            st.markdown(" | ".join(row_cuentas), unsafe_allow_html=True)
        st.write("---")
        semana_idx += 1
        start_day = end_day+1

def vista_anual(df, config):
    """
    Vista Anual:
    - Seleccionar el Año (rango ±10 años).
    - Para cada mes (de 1 a 12) se muestra un calendario tipo "librería" con:
         * Encabezado: Nombre del mes y año.
         * Por cada semana (obtenida con calendar.monthcalendar):
             - Se muestra en una fila un contenedor "week-row" que contiene:
                  • Una celda fija a la izquierda con la etiqueta "Sx" (número de semana).
                  • Una grilla de 7 celdas (de lunes a domingo) que muestran el día y, si existen, los eventos (Título y Festividad).
             - A la derecha de esa fila (en el mismo contenedor) se coloca un bloque "state-block" de la misma altura que la fila,
               que muestra en dos líneas:  
                 – La primera línea: Nombres de todas las redes (según la configuración, en el orden dado).  
                 – La segunda línea: Para cada red, se muestra "planeado/requerido" para los eventos en esa semana.  
                     Si el valor planeado es 0, se pinta en rojo.
    """
    st.title("Vista Anual - Calendario Librería con Estado")
    
    anio_actual = datetime.date.today().year
    años = list(range(anio_actual-10, anio_actual+11))
    anio_sel = st.selectbox("Año", años, index=años.index(anio_actual))
    df_year = df[df["Fecha"].dt.year==anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return
    
    st.markdown(f"## {anio_sel}")
    # CSS para formatear el contenedor flex en la vista anual
    st.markdown("""
    <style>
    .week-row {
        display: flex;
        flex-direction: row;
        align-items: stretch;
        margin-bottom: 5px;
    }
    .week-label {
        width: 40px;
        background-color: #ddd;
        border: 1px solid #ccc;
        padding: 4px;
        text-align: center;
        margin-right: 3px;
    }
    .days-container {
        display: flex;
        flex-direction: row;
        flex-wrap: nowrap;
    }
    .day-cell {
        border: 1px solid #ccc;
        min-width: 70px;
        min-height: 70px;
        padding: 4px;
        margin-right: 2px;
        vertical-align: top;
    }
    .state-block {
        border: 1px solid #ccc;
        min-width: 120px;
        padding: 4px;
        margin-left: 5px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Para cada mes (1 a 12)
    for mes in range(1,13):
        df_mes = df_year[df_year["Fecha"].dt.month==mes]
        if df_mes.empty:
            continue
        st.markdown(f"### {NOMBRE_MESES[mes-1]} {anio_sel}")
        # Utilizamos calendar.monthcalendar para obtener las semanas como listas de 7 enteros (0 si no pertenece al mes)
        mat = calendar.monthcalendar(anio_sel, mes)
        
        # Por cada semana (fila)
        for w_i, week in enumerate(mat):
            # Contenedor para la fila de la semana y el bloque de estado a la derecha
            st.markdown("<div class='week-row'>", unsafe_allow_html=True)
            # Celda con el número de semana (S1, S2, …)
            s_label = f"S{w_i+1}"
            st.markdown(f"<div class='week-label'>{s_label}</div>", unsafe_allow_html=True)
            # Contenedor de días: 7 celdas
            days_html = "<div class='days-container'>"
            day_numbers = []
            for d in week:
                if d == 0:
                    days_html += "<div class='day-cell'></div>"
                    day_numbers.append(None)
                else:
                    df_day = df_mes[df_mes["Fecha"].dt.day==d]
                    content = f"<strong>{d}</strong><br/>"
                    if not df_day.empty:
                        for _, rowx in df_day.iterrows():
                            content += f"- {rowx['Titulo']}"
                            if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                                content += f" ({rowx['Festividad']})"
                            content += "<br/>"
                    days_html += f"<div class='day-cell'>{content}</div>"
                    day_numbers.append(d)
            days_html += "</div>"  # Cierra contenedor días

            # Bloque de estado para la semana, al costado (no integrado en la grilla)
            valid_days = [d for d in day_numbers if d is not None]
            if not valid_days:
                state_html = "<div class='state-block'>Sin días</div>"
            else:
                df_sem = df_mes[df_mes["Fecha"].dt.day.isin(valid_days)]
                if df_sem.empty:
                    state_html = "<div class='state-block'>Sin eventos</div>"
                else:
                    # Se muestran todas las redes según la configuración (mantener el orden de config)
                    redes = list(config.keys())
                    row_nombres = []
                    row_contadores = []
                    for red in redes:
                        # Filtrar eventos de la semana para esa red
                        df_red = df_sem[df_sem["Plataforma"]==red]
                        total = len(df_red)
                        planeado = len(df_red[df_red["Estado"]!="Publicado"])
                        contador = f"{planeado}/{config[red]}"
                        # Si planeado es 0, se pinta en rojo (usando HTML)
                        if planeado == 0:
                            contador = f"<span style='color:red'>{contador}</span>"
                        row_nombres.append(red)
                        row_contadores.append(contador)
                    # Construir dos líneas separadas
                    line1 = " | ".join(row_nombres)
                    line2 = " | ".join(row_contadores)
                    state_html = f"<div class='state-block'>{line1}<br/>{line2}</div>"
            # Unir el contenedor de días y el bloque de estado
            row_html = days_html + state_html
            st.markdown(row_html, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)  # Cierra week-row
        st.markdown("<hr>", unsafe_allow_html=True)
        
def vista_configuracion(client, sheet_id):
    st.title("Configuración de Redes Sociales")
    st.markdown("Establece la cantidad requerida de publicaciones semanales para cada red social (este valor se usará para calcular los estados en Vista Mensual y Anual).")
    config = cargar_config(client, sheet_id)
    if not config:
        config = {"Instagram":5, "Facebook":5, "TikTok":3, "Blog":1}
    nuevos_config = {}
    st.markdown("### Redes Configuradas")
    for red in sorted(config.keys()):
        col1, col2 = st.columns([2,1])
        with col1:
            st.write(f"**{red}**:")
        with col2:
            valor = st.number_input(f"Requerido para {red}", min_value=0, value=int(config[red]), key=f"config_{red}")
            nuevos_config[red] = valor
    st.markdown("### Agregar Nueva Red")
    red_nueva = st.text_input("Nombre de la nueva red (deja vacío si no)", key="red_nueva")
    if red_nueva.strip() != "":
        nuevo_valor = st.number_input(f"Requerido para {red_nueva}", min_value=0, value=1, key="config_nueva")
        nuevos_config[red_nueva.strip()] = nuevo_valor
    if st.button("Guardar Configuración", key="btn_config_guardar"):
        guardar_config(client, sheet_id, nuevos_config)
        st.success("Configuración actualizada.")

# --------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# --------------------------------------------------------------------------------
def main():
    # Inicializar la variable de navegación
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    client = get_gsheet_connection()
    sheet_id = st.secrets["SHEET_ID"]
    df = cargar_datos(client, sheet_id)
    config = cargar_config(client, sheet_id)

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
    if st.sidebar.button("Configuración", key="side_config"):
        st.session_state["page"] = "Configuracion"

    page = st.session_state["page"]
    if page == "Dashboard":
        dashboard(df)
    elif page == "Agregar":
        vista_agregar(df, client, sheet_id)
    elif page == "Editar":
        vista_editar_eliminar(df, client, sheet_id)
    elif page == "Mensual":
        vista_mensual(df, config)
    elif page == "Anual":
        vista_anual(df, config)
    elif page == "Configuracion":
        vista_configuracion(client, sheet_id)

if __name__ == "__main__":
    main()

