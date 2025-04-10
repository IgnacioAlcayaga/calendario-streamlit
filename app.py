import streamlit as st
import pandas as pd
import os
import datetime
from io import BytesIO

# -----------------------------------------------------------------------------------
# CONFIGURACIÓN DE LA APP
# -----------------------------------------------------------------------------------
st.set_page_config(
    page_title="Calendario de Contenidos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Nombre del archivo CSV local donde se almacenarán los datos:
CSV_FILE = "data.csv"

# Columnas principales
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Estado", "Notas"]

# -----------------------------------------------------------------------------------
# FUNCIONES DE LECTURA/ESCRITURA
# -----------------------------------------------------------------------------------
def cargar_datos() -> pd.DataFrame:
    """
    Carga los datos desde un archivo CSV (si existe).
    De lo contrario, devuelve un DataFrame vacío con las columnas definidas.
    """
    if os.path.exists(CSV_FILE):
        # parse_dates para que 'Fecha' se trate como datetime
        return pd.read_csv(CSV_FILE, parse_dates=["Fecha"], dayfirst=False)
    else:
        return pd.DataFrame(columns=COLUMNS)

def guardar_datos(df: pd.DataFrame):
    """
    Guarda el DataFrame en un CSV, sobrescribiendo el archivo anterior.
    """
    df.to_csv(CSV_FILE, index=False)

# -----------------------------------------------------------------------------------
# VISTAS / SECCIONES DE LA APP
# -----------------------------------------------------------------------------------

def vista_dashboard(df: pd.DataFrame):
    """Pantalla de inicio con información general y métricas."""
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown(
        """
        <style>
        .instructions {
            font-size: 1rem;
            line-height: 1.6;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="instructions">
        <p>¡Bienvenido(a) al <strong>Calendario de Contenidos</strong>! Aquí podrás organizar y gestionar 
        todas tus publicaciones de manera sencilla y profesional.</p>

        <ul>
          <li><strong>Data:</strong> Ingresar y editar eventos (fecha, título, plataforma, estado, etc.).</li>
          <li><strong>Vista Mensual:</strong> Filtra los contenidos por mes.</li>
          <li><strong>Vista Anual:</strong> Muestra todos los contenidos de un año específico, con opción de descarga en Excel.</li>
        </ul>

        <p>La información se almacena en un archivo CSV interno. 
        Ten en cuenta que, en la versión gratuita de Streamlit Cloud, los datos podrían perderse en un redeploy.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("---")

    total_eventos = len(df)
    st.metric(label="Total de eventos registrados", value=total_eventos)

    # Estadísticas por "Estado"
    if not df.empty:
        conteo_estado = df["Estado"].value_counts().to_dict()
        st.subheader("Conteo por Estado")
        for estado, count in conteo_estado.items():
            st.write(f"- **{estado}**: {count}")
    else:
        st.info("No hay datos aún. Ve a la sección 'Data' para agregar tus primeros eventos.")


def vista_data(df: pd.DataFrame):
    """Sección para ver, agregar y editar datos."""
    st.title("Gestión de Data - Agregar / Editar Eventos")

    st.markdown(
        """
        <p>En esta sección podrás agregar nuevos eventos o editar/borrar los existentes.
        Cada evento representa una futura publicación o contenido que planeas generar.</p>
        <hr>
        """,
        unsafe_allow_html=True
    )

    # FORMULARIO PARA AGREGAR NUEVO EVENTO
    st.subheader("Agregar nuevo evento")
    with st.form("form_nuevo", clear_on_submit=True):
        fecha = st.date_input(
            label="Fecha",
            value=datetime.date.today(),
            help="Selecciona la fecha planeada para la publicación o suceso."
        )
        titulo = st.text_input(
            label="Título o Descripción Breve",
            help="Ejemplo: 'Rutina de ejercicios matutina' o 'Promoción especial'."
        )
        festividad = st.text_input(
            label="Festividad / Efeméride (opcional)",
            help="Si corresponde a un día especial (Ej: Día de la Madre, Fiestas Patrias, etc.)."
        )
        plataforma = st.selectbox(
            label="Canal de Difusión",
            options=["Instagram", "TikTok", "Facebook", "Blog", "Otra"],
            help="Selecciona la principal plataforma para el contenido."
        )
        estado = st.selectbox(
            label="Estado del Contenido",
            options=["Planeación","Diseño","Programado","Publicado"],
            help="Indica la etapa actual del contenido."
        )
        notas = st.text_area(
            label="Notas Adicionales",
            help="Información extra, ideas de copy, hashtags, etc."
        )

        enviado = st.form_submit_button("Guardar evento", help="Haz clic para agregar este evento al calendario.")
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
            guardar_datos(df)
            st.success("¡Evento agregado exitosamente!")

    st.write("---")
    st.subheader("Eventos existentes")

    if df.empty:
        st.info("No hay eventos registrados todavía.")
        return

    st.dataframe(df)

    st.markdown("### Editar o Eliminar eventos")
    indices = df.index.tolist()
    if indices:
        selected_index = st.selectbox(
            "Selecciona la fila que deseas modificar",
            indices,
            help="Elige el índice de la tabla para editar o eliminar un evento."
        )
        if selected_index is not None:
            row_data = df.loc[selected_index]

            with st.form("form_editar"):
                fecha_edit = st.date_input(
                    "Fecha",
                    value=(row_data["Fecha"] if not pd.isnull(row_data["Fecha"]) else datetime.date.today()),
                    help="Ajusta la fecha si lo requieres."
                )
                titulo_edit = st.text_input(
                    "Título o Descripción",
                    value=row_data["Titulo"],
                    help="Breve texto descriptivo."
                )
                festividad_edit = st.text_input(
                    "Festividad / Efeméride",
                    value=row_data["Festividad"]
                )
                plataformas_posibles = ["Instagram", "TikTok", "Facebook", "Blog", "Otra"]
                if row_data["Plataforma"] in plataformas_posibles:
                    idx_plat = plataformas_posibles.index(row_data["Plataforma"])
                else:
                    idx_plat = 0

                plataforma_edit = st.selectbox(
                    "Canal de Difusión",
                    plataformas_posibles,
                    index=idx_plat
                )
                estados_posibles = ["Planeación","Diseño","Programado","Publicado"]
                if row_data["Estado"] in estados_posibles:
                    idx_est = estados_posibles.index(row_data["Estado"])
                else:
                    idx_est = 0

                estado_edit = st.selectbox(
                    "Estado del Contenido",
                    estados_posibles,
                    index=idx_est
                )
                notas_edit = st.text_area("Notas", value=(row_data["Notas"] if not pd.isnull(row_data["Notas"]) else ""))

                col1, col2 = st.columns(2)
                with col1:
                    submit_edit = st.form_submit_button("Guardar cambios", help="Aplica las modificaciones a este evento.")
                with col2:
                    submit_delete = st.form_submit_button("Borrar este evento", help="Elimina permanentemente el evento.")

                # PROCESAR ACCIONES
                if submit_edit:
                    df.at[selected_index, "Fecha"] = fecha_edit
                    df.at[selected_index, "Titulo"] = titulo_edit
                    df.at[selected_index, "Festividad"] = festividad_edit
                    df.at[selected_index, "Plataforma"] = plataforma_edit
                    df.at[selected_index, "Estado"] = estado_edit
                    df.at[selected_index, "Notas"] = notas_edit
                    guardar_datos(df)
                    st.success("¡Evento editado exitosamente!")

                if submit_delete:
                    df.drop(index=selected_index, inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    guardar_datos(df)
                    st.warning("Evento eliminado.")
                    st.experimental_rerun()


def vista_mensual(df: pd.DataFrame):
    """Sección para filtrar y mostrar eventos por mes."""
    st.title("Vista Mensual de Eventos")

    if df.empty:
        st.info("No hay eventos registrados. Ve a la sección 'Data' para agregar.")
        return

    mes_seleccionado = st.selectbox(
        "Selecciona el mes",
        list(range(1,13)),
        format_func=lambda x: f"Mes {x:02d}",
        help="Elige el número de mes para filtrar los eventos."
    )
    df["Mes"] = df["Fecha"].dt.month
    filtrado = df[df["Mes"] == mes_seleccionado]

    st.write(f"### Eventos para el mes {mes_seleccionado:02d}")
    st.dataframe(filtrado.drop(columns=["Mes"], errors="ignore"))

def vista_anual(df: pd.DataFrame):
    """Sección para filtrar eventos por año y permitir descarga."""
    st.title("Vista Anual de Eventos")

    if df.empty:
        st.info("No hay eventos registrados. Ve a la sección 'Data' para agregar.")
        return

    anio = st.number_input(
        "Selecciona el año",
        value=2025,
        min_value=2000,
        max_value=2100,
        step=1,
        help="Ingresa el año para filtrar los eventos."
    )
    df["Anio"] = df["Fecha"].dt.year
    filtrado = df[df["Anio"] == anio]

    st.write(f"### Mostrando eventos del año {anio}")
    if filtrado.empty:
        st.warning(f"No se encontraron eventos para {anio}.")
    else:
        st.dataframe(filtrado.drop(columns=["Anio","Mes"], errors="ignore"))

        # Botón para descargar Excel
        if st.button("Descargar en Excel", help="Exporta los datos de este año a un archivo Excel."):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                filtrado.drop(columns=["Anio","Mes"], errors="ignore")\
                    .to_excel(writer, sheet_name=str(anio), index=False)
            excel_data = output.getvalue()
            st.download_button(
                label="Descargar Excel",
                data=excel_data,
                file_name=f"Eventos_{anio}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# -----------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# -----------------------------------------------------------------------------------
def main():
    # Cargamos el DataFrame
    df = cargar_datos()

    # Barra lateral (menú)
    st.sidebar.title("Navegación")
    menu = ["Dashboard","Data","Vista Mensual","Vista Anual"]
    choice = st.sidebar.radio("Ir a:", menu)

    if choice == "Dashboard":
        vista_dashboard(df)
    elif choice == "Data":
        vista_data(df)
    elif choice == "Vista Mensual":
        vista_mensual(df)
    elif choice == "Vista Anual":
        vista_anual(df)

if __name__ == "__main__":
    main()
