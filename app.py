import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import calendar

# --------------------------------------------------------------------------------
# 1) DEBE SER PRIMER COMANDO DE STREAMLIT
# --------------------------------------------------------------------------------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

# --------------------------------------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------------------------------------
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]
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
# PANTALLAS
# --------------------------------------------------------------------------------
def dashboard(df):
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown("""
    **Bienvenido(a)** a tu Calendario de Contenidos.

    - **Agregar Evento**: Crea nuevas publicaciones.
    - **Editar/Eliminar Evento**: Ver y modificar/borrar publicaciones existentes.
    - **Vista Mensual**: Muestra semanas en bloques (cada semana con sus días, eventos y estado).
    - **Vista Anual**: Muestra un calendario estilo “librería” con filas=semanas, columnas=días, y una columna de estado al costado.
    """)

    col1,col2,col3,col4 = st.columns(4)
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
      - Selecciono año y mes.
      - Para cada semana, muestro:
        * "Semana X"
        * Debajo, la lista de días con sus eventos
        * Debajo, DOS filas de estado: la primera fila con nombres de plataformas
          (Instagram, Tiktok...) 
          la segunda fila con "3/5, 1/2, etc."
    """
    st.title("Vista Mensual - Semanas en Bloques")

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

    meses = sorted(df_year["Fecha"].dt.month.unique().astype(int))
    mes_sel = st.selectbox("Mes", meses, format_func=lambda m: NOMBRE_MESES[m-1])
    df_mes = df_year[df_year["Fecha"].dt.month==mes_sel]
    if df_mes.empty:
        st.warning("No hay datos para ese mes.")
        return

    st.markdown(f"## {NOMBRE_MESES[mes_sel-1]} {anio_sel}")

    _, ndays = calendar.monthrange(anio_sel, mes_sel)

    # Repartimos semanas => S1 => 1..7, S2 => 8..14 ...
    semana_idx = 1
    start_day = 1
    while start_day <= ndays:
        end_day = min(start_day+6, ndays)
        dias_sem = list(range(start_day, end_day+1))

        st.subheader(f"Semana {semana_idx}")

        # 1) Lista de fechas con eventos
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

        # 2) DOS filas de estado
        df_sem = df_mes[df_mes["Fecha"].dt.day.between(start_day, end_day)]
        if df_sem.empty:
            # No hay publicaciones
            st.write("Sin publicaciones en esta semana.")
        else:
            # Recolectar plataformas
            plats_en_sem = df_sem["Plataforma"].unique()
            if len(plats_en_sem)==0:
                st.write("No hay plataformas en esta semana.")
            else:
                # Fila 1 => Nombres de plataformas
                row_plat = []
                # Fila 2 => Conteo (3/5)
                row_cnt = []
                for plat in plats_en_sem:
                    dfp = df_sem[df_sem["Plataforma"]==plat]
                    total = len(dfp)
                    publ = len(dfp[dfp["Estado"]=="Publicado"])
                    row_plat.append(plat)
                    row_cnt.append(f"{publ}/{total}")
                # Mostramos en la misma linea: IG   Face   TikTok
                # Y en la siguiente:        3/5  1/2   2/6
                st.write(" | ".join(row_plat))
                st.write(" | ".join(row_cnt))

        st.write("---")
        semana_idx += 1
        start_day = end_day+1


def vista_anual(df):
    """
    Vista Anual: Estilo calendario-librería,
    filas = semanas (S1..S5/6),
    columnas = L..D + 'Estado' al costado,
    pero con DOS filas dentro del 'Estado': una con nombres (IG, Face, TikTok) y otra con '3/5, 1/2...'
    """
    st.title("Vista Anual - Calendario Librería + Estado al costado")

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
        st.warning("No hay datos en ese año.")
        return

    st.markdown(f"## {anio_sel}")

    full_html = []
    for mes in range(1,13):
        df_mes = df_year[df_year["Fecha"].dt.month==mes]
        if df_mes.empty:
            continue
        # Obtenemos la matriz con monthcalendar => lista de semanas
        mat = calendar.monthcalendar(anio_sel, mes)
        # Cada fila => [L, M, X, J, V, S, D], 0 si no corresponde

        # Generamos una tabla con 1 + 7 + 1 = 9 columnas:
        # col0 => "S1"
        # col1..7 => L..D
        # col8 => Estado (dos filas internas: una de nombres de plataformas, otra con "3/5")
        # Recorremos las filas => S1..Sx

        table_rows = []
        # Encabezados => 9
        table_rows.append("""
        <tr>
          <th></th>
          <th>L</th><th>M</th><th>X</th><th>J</th><th>V</th><th>S</th><th>D</th>
          <th>Estado</th>
        </tr>
        """)

        for w_i,week in enumerate(mat):
            s_name = f"S{w_i+1}"
            row_cells = []
            row_cells.append(f"<td><strong>{s_name}</strong></td>")  # col0
            day_numbers = []
            # col1..7 => lunes..domingo
            for day_of_week in week:  # 0 => no day
                if day_of_week==0:
                    row_cells.append("<td></td>")
                    day_numbers.append(None)
                else:
                    # Filtramos df
                    df_day = df_mes[df_mes["Fecha"].dt.day==day_of_week]
                    day_text = f"{day_of_week}:<br/>"
                    if not df_day.empty:
                        for _, rowx in df_day.iterrows():
                            day_text += f"- {rowx['Titulo']}"
                            if pd.notna(rowx['Festividad']) and rowx['Festividad'].strip():
                                day_text += f" ({rowx['Festividad']})"
                            day_text += "<br/>"
                    row_cells.append(f"<td style='vertical-align:top;'>{day_text}</td>")
                    day_numbers.append(day_of_week)

            # col8 => estado, con DOS filas internas
            valid_days = [d for d in day_numbers if d is not None]
            if not valid_days:
                # Sin dias
                row_cells.append("<td></td>")
            else:
                df_sem = df_mes[df_mes["Fecha"].dt.day.isin(valid_days)]
                if df_sem.empty:
                    row_cells.append("<td>Sin eventos</td>")
                else:
                    # Agrupamos por plataforma
                    plats = df_sem["Plataforma"].unique()
                    if len(plats)==0:
                        row_cells.append("<td>Sin eventos</td>")
                    else:
                        # construimos 2 lineas: 
                        # 1) "IG | Face | TikTok"
                        # 2) "3/5 | 1/2 | 2/7"
                        # Recolectamos en arrays
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
                        td_content = f"{line1}<br/>{line2}"
                        row_cells.append(f"<td style='vertical-align:top;'>{td_content}</td>")

            table_rows.append("<tr>" + "".join(row_cells) + "</tr>")

        # Armamos la tabla
        table_html = []
        table_html.append(f"<h3>{NOMBRE_MESES[mes-1]} {anio_sel}</h3>")
        table_html.append("<table border='1' style='border-collapse:collapse; width:100%;'>")
        table_html.append("".join(table_rows))
        table_html.append("</table>")
        full_html.append("".join(table_html))

    st.markdown("<div style='width:100%'>" + "".join(full_html) + "</div>", unsafe_allow_html=True)


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
