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
# CONFIGURACIÓN / CONSTANTES
# --------------------------------------------------------------------------------
COLUMNS = ["Fecha","Titulo","Festividad","Plataforma","Estado","Notas"]
WORKSHEET_NAME = "Data"

NOMBRE_MESES = [
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
]

# (Opcional) Colores de plataformas
PLATAFORMA_COLORES = {
    "Instagram": "#ffc0cb",
    "Facebook": "#add8e6",
    "TikTok": "#ffffff",
    "Otra": "#dddddd"
}

# --------------------------------------------------------------------------------
# FUNCIONES DE CONEXIÓN A GOOGLE SHEETS
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
# PANTALLAS
# --------------------------------------------------------------------------------

def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown("""
    **Bienvenido(a)** a tu Calendario de Contenidos.

    - **Agregar Evento**: Añadir nuevas publicaciones (con fecha, título, plataforma, etc.)
    - **Editar/Eliminar Evento**: Modificar o borrar publicaciones existentes.
    - **Vista Mensual**: Seleccionar 1 año y 1 mes; ver semanas en bloques con días y estado (2 filas).
    - **Vista Anual**: Seleccionar 1 año; se listan todos los meses como un calendario librería,
      cada fila = semana, con un bloque de estado (2 filas: plataformas / conteos) a la derecha.
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
        st.info("No hay eventos.")
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
      - Se agrupan semanas: S1 => dias 1..7, S2 => 8..14...
      - Muestra un bloque por semana:
        * Título "Semana X"
        * Lista de días con sus eventos
        * DOS filas de estado (Primera con nombres de plataforma, segunda con conteos).
    """
    st.title("Vista Mensual - Bloques semanales")

    if df.empty:
        st.info("No hay datos.")
        return

    # Seleccion de año/mes
    anios = sorted(df["Fecha"].dropna().dt.year.unique().astype(int))
    if not anios:
        st.warning("No hay años disponibles.")
        return

    anio_sel = st.selectbox("Año", anios)
    df_year = df[df["Fecha"].dt.year==anio_sel]
    if df_year.empty:
        st.warning("No hay datos en ese año.")
        return

    # Filtramos los meses disponibles
    meses_disp = sorted(df_year["Fecha"].dt.month.unique().astype(int))
    mes_sel = st.selectbox("Mes", meses_disp, format_func=lambda x: NOMBRE_MESES[x-1])
    df_mes = df_year[df_year["Fecha"].dt.month==mes_sel]
    if df_mes.empty:
        st.warning("No hay datos en ese mes.")
        return

    st.markdown(f"## {NOMBRE_MESES[mes_sel-1]} {anio_sel}")

    # Cant. de dias
    _, ndays = calendar.monthrange(anio_sel, mes_sel)
    semana_idx = 1
    start_day = 1

    while start_day <= ndays:
        end_day = min(start_day+6, ndays)
        dias_sem = range(start_day, end_day+1)

        st.subheader(f"Semana {semana_idx}")

        # 1) Lista de días y eventos
        for d in dias_sem:
            df_day = df_mes[df_mes["Fecha"].dt.day==d]
            if df_day.empty:
                st.write(f"Día {d} (sin eventos)")
            else:
                st.write(f"**Día {d}:**")
                for _, rowx in df_day.iterrows():
                    line = f"- {rowx['Titulo']}"
                    if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                        line += f" ({rowx['Festividad']})"
                    st.write(line)

        # 2) Bloque de estado => DOS filas
        df_sem = df_mes[df_mes["Fecha"].dt.day.between(start_day, end_day)]
        if df_sem.empty:
            st.write("No hay publicaciones esta semana.")
        else:
            plats = df_sem["Plataforma"].unique()
            if len(plats)==0:
                st.write("Sin plataformas en esta semana.")
            else:
                # Fila 1 => nombres
                row_plat = []
                # Fila 2 => conteos "2/5" etc
                row_cnt = []
                for p in plats:
                    subsetp = df_sem[df_sem["Plataforma"]==p]
                    total = len(subsetp)
                    publ = len(subsetp[subsetp["Estado"]=="Publicado"])
                    row_plat.append(p)
                    row_cnt.append(f"{publ}/{total}")
                # Mostramos en dos líneas
                st.write(" | ".join(row_plat))
                st.write(" | ".join(row_cnt))

        st.write("---")
        semana_idx += 1
        start_day = end_day+1


def vista_anual(df):
    """
    Vista Anual:
     - Seleccionas año
     - Para cada mes => un "calendario" con filas = semanas
       y cada fila => 7 celdas de dia + un BLOQUE de estado a la derecha
       con DOS lineas (plataformas / conteos).
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

    # CSS
    st.markdown("""
    <style>
    .month-container {
      margin-bottom: 2rem;
    }
    .week-row {
      display: flex;
      flex-direction: row;
      margin-bottom: 5px;
    }
    .week-label {
      width: 40px;
      text-align: center;
      background-color: #ddd;
      margin-right: 3px;
      border: 1px solid #ccc;
      padding: 4px;
    }
    .days-container {
      display: flex;
      flex-direction: row;
    }
    .day-cell {
      border: 1px solid #ccc;
      min-width: 70px;
      min-height: 60px;
      margin-right: 2px;
      padding: 4px;
      vertical-align: top;
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

    # Recorremos los 12 meses
    for mes in range(1,13):
        df_mes = df_year[df_year["Fecha"].dt.month==mes]
        if df_mes.empty:
            continue

        st.markdown(f"### {NOMBRE_MESES[mes-1]} {anio_sel}")
        st.markdown("<div class='month-container'>", unsafe_allow_html=True)

        mat = calendar.monthcalendar(anio_sel, mes)
        # Cada row => [lunes, martes, mier, juev, vier, sab, dom], 0 = no day

        for w_i,week in enumerate(mat):
            st.markdown("<div class='week-row'>", unsafe_allow_html=True)

            # col0 => Sx
            s_label = f"S{w_i+1}"
            st.markdown(f"<div class='week-label'>{s_label}</div>", unsafe_allow_html=True)

            # contenedor de days
            days_html = "<div class='days-container'>"
            day_nums = []
            for d in week:
                if d==0:
                    days_html += "<div class='day-cell'></div>"
                    day_nums.append(None)
                else:
                    df_day = df_mes[df_mes["Fecha"].dt.day==d]
                    cell_content = f"<strong>Día {d}</strong><br/>"
                    if len(df_day)>0:
                        for _, rowx in df_day.iterrows():
                            line = f"- {rowx['Titulo']}"
                            if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                                line += f" ({rowx['Festividad']})"
                            line += "<br/>"
                            cell_content += line
                    days_html += f"<div class='day-cell'>{cell_content}</div>"
                    day_nums.append(d)
            days_html += "</div>"  # fin days-container

            # state-block a la derecha
            valid_days = [x for x in day_nums if x is not None]
            if not valid_days:
                state_html = "<div class='state-block'>Sin días</div>"
            else:
                df_sem = df_mes[df_mes["Fecha"].dt.day.isin(valid_days)]
                if df_sem.empty:
                    state_html = "<div class='state-block'>Sin eventos</div>"
                else:
                    plats = df_sem["Plataforma"].unique()
                    if len(plats)==0:
                        state_html = "<div class='state-block'>Sin plataformas</div>"
                    else:
                        row_plat = []
                        row_cnt = []
                        for p in plats:
                            subp = df_sem[df_sem["Plataforma"]==p]
                            total = len(subp)
                            publ = len(subp[subp["Estado"]=="Publicado"])
                            row_plat.append(p)
                            row_cnt.append(f"{publ}/{total}")

                        line1 = " | ".join(row_plat)
                        line2 = " | ".join(row_cnt)
                        state_html = f"<div class='state-block'>{line1}<br/>{line2}</div>"

            row_html = days_html + state_html
            st.markdown(row_html, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True) # fin week-row

        st.markdown("</div>", unsafe_allow_html=True) # fin month-container


def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    client = get_gsheet_connection()
    sheet_id = st.secrets["SHEET_ID"]
    df = cargar_datos(client, sheet_id)

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
