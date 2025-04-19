# ======================================================
# CALENDARIO DE CONTENIDOS – v3.1  (17‑Abr‑2025)
# ------------------------------------------------------
# * Botón Cerrar integrado en el modal (visible y útil)
# * El modal sólo muestra Título, Plataforma y Estado
# ======================================================

import streamlit as st
import pandas as pd
import json, gspread, datetime, calendar, unicodedata
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# ---------- CONFIG BÁSICA ----------
st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

DATA_SHEET   = "Data"
CONFIG_SHEET = "Config"
COLUMNS      = ["Fecha","Titulo","Festividad","Plataforma","Estado","Notas"]
MESES        = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio",
                "Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
REDES_PREDEFINIDAS = ["Instagram","Facebook","TikTok","Blog","Twitter"]

# ---------- CSS ----------
st.markdown("""
<style>
.modal{position:fixed;top:0;left:0;width:100%;height:100%;
       background:rgba(0,0,0,.55);display:flex;justify-content:center;
       align-items:center;z-index:1000}
.modal-content{background:#fff;padding:24px 32px;border-radius:8px;
               max-width:700px;width:90%;max-height:85vh;overflow-y:auto;
               box-shadow:0 4px 10px rgba(0,0,0,.25)}
.stButton>button{margin-top:18px}
</style>
""", unsafe_allow_html=True)

# ---------- UTILIDADES ----------
def norm(t:str)->str:
    if not isinstance(t,str): return ""
    return "".join(c for c in unicodedata.normalize("NFD",t.replace("\u00a0"," "))
                   if unicodedata.category(c)!="Mn").lower().strip()

def status_html(p:int,r:int)->str:
    txt=f"{p}/{r}"
    if p==0:        return f"<span style='color:red'>{txt}</span>"
    if p>=r:        return f"<span style='color:green;font-weight:700'>{txt}</span>"
    if p>r/2:       return f"<span style='color:blue'>{txt}</span>"
    return txt

def get_gsheet_connection():
    creds=json.loads(st.secrets["gcp_service_account"])
    scope=["https://www.googleapis.com/auth/spreadsheets",
           "https://www.googleapis.com/auth/drive"]
    return gspread.authorize(
        ServiceAccountCredentials.from_json_keyfile_dict(creds,scope))

@st.cache_data(ttl=60,hash_funcs={gspread.client.Client:lambda _:None})
def load_df(cli,shid):
    sh=cli.open_by_key(shid)
    try: ws=sh.worksheet(DATA_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws=sh.add_worksheet(title=DATA_SHEET,rows="1000",cols="20")
        ws.append_row(COLUMNS); return pd.DataFrame(columns=COLUMNS)
    df=pd.DataFrame(ws.get_all_records())
    df["Fecha"]=pd.to_datetime(df["Fecha"],errors="coerce")
    for c in ["Plataforma","Estado"]:
        df[c]=df[c].astype(str).str.replace("\u00a0"," ").str.strip()
    df["Plataforma_norm"]=df["Plataforma"].apply(norm)
    df["Estado_norm"]     =df["Estado"].apply(norm)
    return df

@st.cache_data(ttl=60,hash_funcs={gspread.client.Client:lambda _:None})
def load_cfg(cli,shid):
    sh=cli.open_by_key(shid)
    try: ws=sh.worksheet(CONFIG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws=sh.add_worksheet(title=CONFIG_SHEET,rows="10",cols="5")
        ws.update("A1",[["Red","Requerido"],
                        ["Instagram","5"],["Facebook","5"],
                        ["TikTok","3"],["Blog","1"]])
    return {r[0]:int(r[1]) if len(r)>1 and r[1].isdigit() else 0
            for r in ws.get_all_values()[1:]}

def guardar_datos(cli,shid,df):
    sh=cli.open_by_key(shid)
    out=df[COLUMNS].copy(); out["Fecha"]=out["Fecha"].astype(str)
    data=[out.columns.tolist()]+out.values.tolist()
    try: ws=sh.worksheet(DATA_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws=sh.add_worksheet(title=DATA_SHEET,rows="1000",cols="20")
    ws.clear(); ws.update("A1",data); st.cache_data.clear()

def guardar_config(cli,shid,cfg):
    sh=cli.open_by_key(shid)
    try: ws=sh.worksheet(CONFIG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws=sh.add_worksheet(title=CONFIG_SHEET,rows="10",cols="5")
    ws.clear()
    ws.update("A1",[["Red","Requerido"]]+[[k,str(v)] for k,v in cfg.items()])
    st.cache_data.clear()

# ---------- DASHBOARD ----------
def weeks_in_year(yr: int) -> int:
    """Número ISO‑semanas reales de un año (52 o 53)."""
    yr = int(yr)                          # evita floats tipo 2025.0
    return datetime.date(yr, 12, 28).isocalendar().week  # 28‑dic siempre cae en la última semana ISO


def dashboard(df: pd.DataFrame, cfg: dict):
    st.title("Dashboard – Calendario de Contenidos")

    # -------- Navegación rápida
    cols = st.columns(5)
    for i, (lbl, pg) in enumerate(
        [("Agregar Evento", "Agregar"),
         ("Editar/Eliminar", "Editar"),
         ("Vista Mensual", "Mensual"),
         ("Vista Anual", "Anual"),
         ("Configuración", "Config")]
    ):
        if cols[i].button(lbl, key=f"dash_{pg}"):
            st.session_state["page"] = pg

    st.write("---")

    # -------- Año a analizar
    years = sorted({int(y) for y in df["Fecha"].dt.year.dropna()})
    if not years:
        st.warning("No hay años disponibles para visualizar.")
        return

    hoy = datetime.date.today().year
    default_idx = years.index(hoy) if hoy in years else 0
    yr = int(st.selectbox("Año a visualizar", years, index=default_idx))

    df_yr = df[df["Fecha"].dt.year == yr]
    wks   = weeks_in_year(yr)

    # -------- KPI global
    objetivo_total = sum(v * wks for v in cfg.values())
    planeado_total = len(df_yr)

    st.metric("⏱️ Eventos planificados / objetivo anual",
              f"{planeado_total}/{objetivo_total}",
              delta=f"{planeado_total - objetivo_total}")

    # -------- Conteo por ESTADO (planificado vs objetivo anual)
    vc_estado = df_yr["Estado"].value_counts().reindex(
        ["Planeación", "Diseño", "Programado", "Publicado"], fill_value=0
    )
    st.subheader("Conteo por estado (año seleccionado)")
    st.dataframe(vc_estado.rename("Planificados").to_frame())

    # -------- Conteo POR RED (planificado vs objetivo anual)
    st.subheader("Planificado vs objetivo por red social")
    cols = st.columns(len(cfg))
    for i, red in enumerate(sorted(cfg)):
        objetivo = cfg[red] * wks
        planeado = len(
            df_yr[df_yr["Plataforma_norm"].str.contains(norm(red), na=False)]
        )
        cols[i].metric(red, f"{planeado}/{objetivo}")

    # -------- Pie de estados
    fig = px.pie(
        values=vc_estado.values,
        names=vc_estado.index,
        title=f"Distribución de estados – {yr}",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------- AGREGAR / EDITAR / MENÚ / CONFIG (igual que 3.0) ----------
def vista_agregar(df,cli,sheet_id):
    st.title("Agregar Evento")
    default_date=datetime.date.today()
    sel=st.session_state.get("selected_date")
    if isinstance(sel,datetime.date): default_date=sel
    with st.form("f_add",clear_on_submit=True):
        fecha=st.date_input("Fecha",default_date)
        titulo=st.text_input("Título","")
        festividad=st.text_input("Festividad/Efeméride","")
        plataforma=st.selectbox("Plataforma",REDES_PREDEFINIDAS+["Otra"])
        estado=st.selectbox("Estado",["Planeación","Diseño","Programado","Publicado"])
        notas=st.text_area("Notas","")
        if st.form_submit_button("Guardar Evento"):
            nuevo={"Fecha":pd.Timestamp(fecha),"Titulo":titulo.strip(),
                   "Festividad":festividad.strip(),"Plataforma":plataforma.strip(),
                   "Estado":estado.strip(),"Notas":notas.strip()}
            df=pd.concat([df,pd.DataFrame([nuevo])],ignore_index=True)
            guardar_datos(cli,sheet_id,df); st.success("¡Evento agregado!")

def vista_editar_eliminar(df,cli,sheet_id):
    st.title("Editar / Eliminar Evento")
    if df.empty: st.info("No hay eventos registrados."); return
    st.dataframe(df,use_container_width=True)
    idx=st.selectbox("Fila",df.index.tolist())
    row=df.loc[idx]
    with st.form("f_edit",clear_on_submit=True):
        fecha=st.date_input("Fecha",row["Fecha"].date())
        titulo=st.text_input("Título",row["Titulo"])
        festividad=st.text_input("Festividad/Efeméride",row["Festividad"])
        plat_opts=REDES_PREDEFINIDAS+["Otra"]
        plataforma=st.selectbox("Plataforma",plat_opts,
                     index=plat_opts.index(row["Plataforma"]
                           if row["Plataforma"] in plat_opts else "Otra"))
        estados=["Planeación","Diseño","Programado","Publicado"]
        estado=st.selectbox("Estado",estados,
                index=estados.index(row["Estado"]) if row["Estado"] in estados else 0)
        notas=st.text_area("Notas",row["Notas"])
        c1,c2=st.columns(2)
        with c1:
            if st.form_submit_button("Guardar Cambios"):
                df.loc[idx]=[pd.Timestamp(fecha),titulo,festividad,plataforma,estado,notas,
                             norm(plataforma),norm(estado)]
                guardar_datos(cli,sheet_id,df); st.success("¡Guardado!")
        with c2:
            if st.form_submit_button("Borrar Evento"):
                df.drop(index=idx,inplace=True); df.reset_index(drop=True,inplace=True)
                guardar_datos(cli,sheet_id,df); st.warning("Eliminado"); st.rerun()

def vista_configuracion(cli,sheet_id):
    st.title("Configuración – Redes Sociales")
    cfg=load_cfg(cli,sheet_id)
    nuevos={}
    for red in sorted(cfg):
        c1,c2=st.columns([2,1]); c1.write(f"**{red}**")
        nuevos[red]=c2.number_input("",value=cfg[red],min_value=0,key=f"cfg_{red}")
    st.markdown("### Nueva red social")
    nueva=st.text_input("Nombre nueva red").strip()
    if nueva:
        req=st.number_input("Requerido",min_value=0,value=1)
        nuevos[nueva]=req
    if st.button("Guardar"):
        guardar_config(cli,sheet_id,nuevos); st.success("¡Configuración guardada!")

def vista_mensual(df: pd.DataFrame, cfg: dict):
    st.title("Vista Mensual – Semanas")

    # --- Selector de fecha
    anio = st.selectbox("Año",
        list(range(datetime.date.today().year - 10,
                   datetime.date.today().year + 11)),
        index=10)
    df_y = df[df["Fecha"].dt.year == anio]
    if df_y.empty:
        st.warning("Sin datos para ese año.")
        return

    meses = sorted(df_y["Fecha"].dt.month.unique())
    mes = st.selectbox("Mes", meses, format_func=lambda m: MESES[m-1])
    df_m = df_y[df_y["Fecha"].dt.month == mes]
    if df_m.empty:
        st.warning("Sin datos para ese mes.")
        return

    st.markdown(f"## {MESES[mes-1]} {anio}")

    ndays = calendar.monthrange(anio, mes)[1]
    weekday = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

    semana, d = 1, 1
    while d <= ndays:
        fin = min(d + 6, ndays)
        dias = list(range(d, fin + 1))
        st.subheader(f"Semana {semana}")

        # --- Días
        for day in dias:
            fecha = datetime.date(anio, mes, day)
            st.markdown(f"**{weekday[fecha.weekday()]} {day}:**")

            df_d = df_m[df_m["Fecha"].dt.day == day]
            if df_d.empty:
                st.markdown("- (vacío)")
            else:


                ### ---------- TABLA COMPACTA AJUSTADA ----------
                mini = (
                    df_d[["Titulo", "Plataforma", "Estado"]]
                    .rename(columns={"Titulo": "Título"})
                )

                st.markdown(
                    """
                    <style>
                    /* Contenedor del DataFrame → ancho al mínimo y pegado a la derecha */
                    div[data-testid="stDataFrame"]{
                        width:fit-content !important;
                        margin-left:auto;        /* empuja a la derecha */
                    }
                    /* columnas Plataforma y Estado: texto alineado a la derecha + nowrap */
                    div[data-testid="stDataFrame"] tbody tr td:nth-last-child(-n+2){
                        text-align:right !important;
                        white-space:nowrap !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                st.dataframe(
                    mini,
                    hide_index=True,
                    use_container_width=False,   # ← dejamos que el CSS decida
                    column_config={
                        "Título":     st.column_config.TextColumn(width="large"),
                        "Plataforma": st.column_config.TextColumn(width="small"),
                        "Estado":     st.column_config.TextColumn(width="small"),
                    },
                )
                ### ----------------------------------------------


        # --- Estado semanal por red
        st.markdown("**Estado de la semana:**")
        cols = st.columns(len(cfg))
        for i, red in enumerate(sorted(cfg)):
            rn = norm(red)
            pend = len(df_m[
                (df_m["Fecha"].dt.day.isin(dias)) &
                (df_m["Plataforma_norm"].str.contains(rn, na=False)) &
                (df_m["Estado_norm"] != "publicado")
            ])
            cols[i].markdown(
                f"<div style='text-align:center'><strong>{red}</strong><br/>{status_html(pend, cfg[red])}</div>",
                unsafe_allow_html=True
            )
        st.write("---")
        semana += 1
        d = fin + 1


# ---------- VISTA ANUAL (botón dentro del modal) ----------
def vista_anual(df: pd.DataFrame, cfg: dict):
    st.title("Vista Anual – Calendario")
    yr = st.selectbox("Año",
        list(range(datetime.date.today().year - 10,
                   datetime.date.today().year + 11)), index=10)

    year_df = df[df["Fecha"].dt.year == yr]
    if year_df.empty:
        st.info("Sin datos para este año.")
        return

    # Obtener la fecha seleccionada
    sel = st.session_state.get("selected_date")
    if isinstance(sel, str):
        try:
            sel = datetime.date.fromisoformat(sel)
        except ValueError:
            sel = None
        st.session_state["selected_date"] = sel

    # ---------- MODAL ----------
    if isinstance(sel, datetime.date):
        dfe = year_df[year_df["Fecha"].dt.date == sel]

        # Mostrar ventana emergente con eventos del día
        with st.container():
            st.markdown(f"### Eventos del {sel.strftime('%d/%m/%Y')}")
            if dfe.empty:
                st.info("No hay eventos para este día.")
            else:
                for _, ev in dfe.iterrows():
                    st.markdown(f"""
                    - **Título:** {ev['Titulo']}  
                    - **Plataforma:** {ev['Plataforma']}  
                    - **Estado:** {ev['Estado']}  
                    """)

            # Botón "Cerrar" para volver a la vista anual
            if st.button("Cerrar", key="close_modal"):
                st.session_state["selected_date"] = None
                st.rerun()  # Recargar la página para volver a la vista anual

        return  # Detener la ejecución para no mostrar el calendario

    # ---------- CALENDARIO ----------
    for mes in range(1, 13):
        mdf = year_df[year_df["Fecha"].dt.month == mes]
        st.markdown(f"### {MESES[mes-1]} {yr}")

        # Encabezado del calendario
        head = st.columns(9)
        head[0].markdown("**Semana**")
        for i, d in enumerate(["L", "M", "X", "J", "V", "S", "D"]):
            head[i + 1].markdown(f"**{d}**")
        head[8].markdown("**Estado**")

        # Filas del calendario
        for wnum, week in enumerate(calendar.monthcalendar(yr, mes), start=1):
            row = st.columns(9)
            row[0].markdown(f"**S{wnum}**")
            valid = []
            for i, d in enumerate(week):
                if d == 0:
                    row[i + 1].markdown("")
                    continue
                valid.append(d)
                if row[i + 1].button(str(d), key=f"{yr}-{mes}-{d}"):
                    st.session_state["selected_date"] = datetime.date(yr, mes, d)
                    st.rerun()

            # Barra de estado semanal
            if valid:
                wdf = mdf[mdf["Fecha"].dt.day.isin(valid)]
                partes = []
                for red in sorted(cfg):
                    pend = len(wdf[
                        (wdf["Plataforma_norm"].str.contains(norm(red), na=False)) &
                        (wdf["Estado_norm"] != "publicado")
                    ])
                    partes.append(f"{red}: {status_html(pend, cfg[red])}")
                estado = "<br>".join(partes)
            else:
                estado = "-"
            row[8].markdown(estado, unsafe_allow_html=True)


# ---------- MAIN ----------
def main():
    params = st.query_params
    if "page" in params:  st.session_state["page"] = params["page"][0]
    if "fecha" in params: st.session_state["selected_date"] = params["fecha"][0]
    st.session_state.setdefault("page", "Dashboard")

    cli = get_gsheet_connection()
    SHEET_ID = st.secrets["SHEET_ID"]
    df  = load_df(cli, SHEET_ID)
    cfg = load_cfg(cli, SHEET_ID)

    st.sidebar.title("Navegación")
    for lbl, pg in [("Dashboard","Dashboard"),("Agregar Evento","Agregar"),
                    ("Editar/Eliminar","Editar"),("Vista Mensual","Mensual"),
                    ("Vista Anual","Anual"),("Configuración","Config")]:
        if st.sidebar.button(lbl, key=f"side_{pg}"):
            st.session_state["page"] = pg

    pg = st.session_state["page"]
    if pg == "Dashboard": dashboard(df, cfg)
    elif pg == "Agregar": vista_agregar(df, cli, SHEET_ID)
    elif pg == "Editar":  vista_editar_eliminar(df, cli, SHEET_ID)
    elif pg == "Mensual": vista_mensual(df, cfg)
    elif pg == "Anual":   vista_anual(df, cfg)
    elif pg == "Config":  vista_configuracion(cli, SHEET_ID)

if __name__ == "__main__":
    main()
