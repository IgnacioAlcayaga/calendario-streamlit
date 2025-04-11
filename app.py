import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import calendar

# --------------------------------------------------------------------------------
# 1) PRIMER COMANDO ST
# --------------------------------------------------------------------------------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

# --------------------------------------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------------------------------------
COLUMNS = ["Fecha","Titulo","Festividad","Plataforma","Estado","Notas"]
WORKSHEET_NAME = "Data"

PLATAFORMA_COLORES = {
    "Instagram": "#ffc0cb",
    "Facebook": "#add8e6",
    "TikTok": "#ffffff",
    "Otra": "#dddddd"
}

NOMBRE_MESES = [
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
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
    **Bienvenido(a)** a tu Calendario de Contenidos.

    - **Agregar Evento**: Crea nuevas publicaciones.
    - **Editar/Eliminar Evento**: Ver y modificar/borrar publicaciones existentes.
    - **Vista Mensual**: Muestra semanas en bloques (cada semana con sus días, eventos y al final un bloque de estado).
    - **Vista Anual**: Calendario tipo librería, con las semanas en filas y un bloque de estado a la derecha.
    """)

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        if st.button("Agregar Evento", key="dash_agregar"):
            st.session_state["page"] = "Agregar"
    with c2:
        if st.button("Editar/Eliminar Evento", key="dash_editar"):
            st.session_state["page"] = "Editar"
    with c3:
        if st.button("Vista Mensual", key="dash_mensual"):
            st.session_state["page"] = "Mensual"
    with c4:
        if st.button("Vista Anual", key="dash_anual"):
            st.session_state["page"] = "Anual"

    st.write("---")
    total_eventos = len(df)
    st.metric("Total de eventos registrados", total_eventos)
    if not df.empty and "Estado" in df.columns:
        st.subheader("Conteo por Estado")
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
        plataforma = st.selectbox("Plataforma", ["Instagram","Facebook","TikTok","Otra"])
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
            st.success("Evento agregado con éxito.")

def vista_editar_eliminar(df, client, sheet_id):
    st.title("Editar / Eliminar Evento")
    if df.empty:
        st.info("No hay eventos registrados.")
        return
    st.dataframe(df)

    idxs = df.index.tolist()
    if not idxs:
        return

    sel_idx = st.selectbox("Selecciona fila", idxs, key="sel_index_editar")
    row = df.loc[sel_idx]
    with st.form("form_editar"):
        fecha_e = st.date_input("Fecha", value=row["Fecha"] if not pd.isnull(row["Fecha"]) else datetime.date.today())
        titulo_e = st.text_input("Título", value=row["Titulo"])
        festividad_e = st.text_input("Festividad/Efeméride", value=row["Festividad"])

        plataformas = ["Instagram","Facebook","TikTok","Otra"]
        try:
            idx_plat = plataformas.index(row["Plataforma"]) if row["Plataforma"] in plataformas else 0
        except:
            idx_plat = 0
        plat_e = st.selectbox("Plataforma", plataformas, index=idx_plat)

        estados = ["Planeación","Diseño","Programado","Publicado"]
        try:
            idx_est = estados.index(row["Estado"]) if row["Estado"] in estados else 0
        except:
            idx_est = 0
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

def vista_mensual(df):
    """
    Vista Mensual:
      - Seleccionar año y mes.
      - Para cada semana: Título "Semana X"
        * Listar cada día con sus eventos
        * Luego DOS bloques de estado:
          - Fila 1 => nombres de plataforma
          - Fila 2 => "3/5, 1/2..." 
    """
    st.title("Vista Mensual (Bloques por semana)")

    if df.empty:
        st.info("No hay datos.")
        return

    # Seleccionar año y mes
    anios = sorted(df["Fecha"].dropna().dt.year.unique().astype(int))
    if not anios:
        st.warning("No hay años.")
        return
    anio_sel = st.selectbox("Año", anios)

    df_year = df[df["Fecha"].dt.year==anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return

    meses = sorted(df_year["Fecha"].dt.month.unique().astype(int))
    mes_sel = st.selectbox("Mes", meses, format_func=lambda m: NOMBRE_MESES[m-1])
    df_mes = df_year[df_year["Fecha"].dt.month==mes_sel]
    if df_mes.empty:
        st.warning("No hay datos para ese mes.")
        return

    st.markdown(f"## {NOMBRE_MESES[mes_sel-1]} {anio_sel}")

    # Calculamos cuántos días
    _, ndays = calendar.monthrange(anio_sel, mes_sel)
    # Repartir semanas => 1..7 => S1, 8..14 => S2
    semana_idx = 1
    start_day = 1
    while start_day <= ndays:
        end_day = min(start_day+6, ndays)
        dias_sem = list(range(start_day, end_day+1))

        st.subheader(f"Semana {semana_idx}")
        # Listar días
        for d in dias_sem:
            df_day = df_mes[df_mes["Fecha"].dt.day==d]
            if len(df_day)>0:
                st.write(f"**Día {d}:**")
                for _, rowx in df_day.iterrows():
                    line = f"- {rowx['Titulo']}"
                    if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                        line += f" ({rowx['Festividad']})"
                    st.write(line)
            else:
                st.write(f"Día {d} (sin eventos)")

        # Bloque de estado
        df_sem = df_mes[df_mes["Fecha"].dt.day.between(start_day, end_day)]
        if df_sem.empty:
            st.write("No hay publicaciones esta semana.")
        else:
            # Extraemos las plataformas
            plats = df_sem["Plataforma"].unique()
            if len(plats)==0:
                st.write("Sin plataformas esta semana.")
            else:
                # Fila 1 => nombres
                row_plat = []
                # Fila 2 => conteos
                row_cnt = []
                for p in plats:
                    subsetp = df_sem[df_sem["Plataforma"]==p]
                    total = len(subsetp)
                    publ = len(subsetp[subsetp["Estado"]=="Publicado"])
                    row_plat.append(p)
                    row_cnt.append(f"{publ}/{total}")
                # Mostramos
                st.write(" | ".join(row_plat))
                st.write(" | ".join(row_cnt))

        st.write("---")
        semana_idx+=1
        start_day = end_day+1

def vista_anual(df):
    """
    Vista Anual estilo librería:
     - Filas => Semanas (S1..S5)
     - Columnas => L..D (7 col)
     - A la derecha, un bloque de estado, con 2 filas: 
       1) nombres de plataforma
       2) "3/5, 1/2..."
     Se hace con contenedores "flex" para que queden alineados horizontalmente.
    """
    st.title("Vista Anual (Calendario librería + Estado al costado)")

    if df.empty:
        st.info("No hay datos.")
        return

    anios = sorted(df["Fecha"].dropna().dt.year.unique().astype(int))
    if not anios:
        st.warning("No hay años.")
        return
    anio_sel = st.selectbox("Año", anios)
    df_year = df[df["Fecha"].dt.year==anio_sel]
    if df_year.empty:
        st.warning("No hay datos para ese año.")
        return

    st.markdown(f"## {anio_sel}")

    # CSS para "flex" containers
    st.markdown("""
    <style>
    .month-container {
        margin-bottom: 2rem;
    }
    .week-row {
        display: flex;
        flex-direction: row;
        margin-bottom: 0.5rem;
    }
    .calendar-cell {
        border: 1px solid #ccc;
        min-width: 70px;
        min-height: 70px;
        padding: 4px;
        margin-right: 2px;
        text-align: left;
        vertical-align: top;
    }
    .calendar-cell-day {
        font-size: 0.8rem;
        font-weight: bold;
    }
    .week-label {
        width: 40px;
        border: 1px solid #ccc;
        margin-right: 2px;
        padding: 4px;
        text-align: center;
        background-color: #eee;
    }
    .state-block {
        border: 1px solid #ccc;
        min-width: 100px;
        padding: 4px;
        margin-left: 4px;
        text-align: left;
    }
    </style>
    """, unsafe_allow_html=True)

    for mes in range(1,13):
        df_mes = df_year[df_year["Fecha"].dt.month==mes]
        if df_mes.empty:
            continue

        st.markdown(f"### {NOMBRE_MESES[mes-1]} {anio_sel}")
        st.markdown("<div class='month-container'>", unsafe_allow_html=True)

        # Obtenemos las semanas con monthcalendar
        mat = calendar.monthcalendar(anio_sel, mes)
        # Cada row = [L, M, X, J, V, S, D]
        # 0 => no day del mes

        for w_i, week in enumerate(mat):
            # week-block en flex
            st.markdown("<div class='week-row'>", unsafe_allow_html=True)

            # 1) Semanal label
            sem_label = f"S{w_i+1}"
            st.markdown(f"<div class='week-label'>{sem_label}</div>", unsafe_allow_html=True)

            # 2) 7 celdas de días
            day_nums = []
            day_html = []
            for d in week:  # monday..sunday
                if d==0:
                    # Celda vacía
                    cell_html = "<div class='calendar-cell'></div>"
                    day_html.append(cell_html)
                    day_nums.append(None)
                else:
                    # Filtrar df
                    df_day = df_mes[df_mes["Fecha"].dt.day==d]
                    content = f"<div class='calendar-cell-day'>Día {d}</div>"
                    if not df_day.empty:
                        for _, rowx in df_day.iterrows():
                            content += f"- {rowx['Titulo']}"
                            if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                                content += f" ({rowx['Festividad']})"
                            content += "<br/>"
                    cell_html = f"<div class='calendar-cell'>{content}</div>"
                    day_html.append(cell_html)
                    day_nums.append(d)

            # 3) Al final "state-block" a la derecha
            # Calculamos
            valid_days = [x for x in day_nums if x is not None]
            if len(valid_days)==0:
                # Sin días
                state_str = "<div class='state-block'>No hay días en esta semana.</div>"
            else:
                df_sem = df_mes[df_mes["Fecha"].dt.day.isin(valid_days)]
                if df_sem.empty:
                    state_str = "<div class='state-block'>Sin eventos.</div>"
                else:
                    plats = df_sem["Plataforma"].unique()
                    if len(plats)==0:
                        state_str = "<div class='state-block'>Sin plataformas.</div>"
                    else:
                        # Fila1 => nombres, Fila2 => "x/y"
                        row_plat = []
                        row_cnt = []
                        for p in plats:
                            subsetp = df_sem[df_sem["Plataforma"]==p]
                            total = len(subsetp)
                            publ = len(subsetp[subsetp["Estado"]=="Publicado"])
                            row_plat.append(p)
                            row_cnt.append(f"{publ}/{total}")
                        line1 = " | ".join(row_plat)
                        line2 = " | ".join(row_cnt)
                        state_str = f"<div class='state-block'>{line1}<br/>{line2}</div>"

            # Unimos
            row_html = "".join(day_html) + state_str
            st.markdown(row_html, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)  # fin .week-row

        st.markdown("</div>", unsafe_allow_html=True)  # fin .month-container


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

    # Ruta
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

