import streamlit as st
import pandas as pd
import os
import datetime
from io import BytesIO

# -----------------------------------------------------------------------------------
# CONFIGURACIÓN BÁSICA
# -----------------------------------------------------------------------------------
# Nombre del archivo CSV local donde guardaremos los datos dentro del contenedor
CSV_FILE = "data.csv"

# Columnas que manejaremos
COLUMNS = ["Fecha", "Titulo", "Festividad", "Plataforma", "Status", "Notas"]

# -----------------------------------------------------------------------------------
# FUNCIONES PARA CARGAR/GUARDAR DATOS
# -----------------------------------------------------------------------------------
def cargar_datos():
    """
    Lee el archivo CSV si existe, de lo contrario retorna un DataFrame vacío.
    """
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE, parse_dates=["Fecha"], dayfirst=False)
    else:
        # Creamos un DF vacío con las columnas esperadas
        return pd.DataFrame(columns=COLUMNS)

def guardar_datos(df: pd.DataFrame):
    """
    Guarda el DataFrame en CSV.
    """
    df.to_csv(CSV_FILE, index=False)

# -----------------------------------------------------------------------------------
# FUNCIONES DE VISTAS
# -----------------------------------------------------------------------------------
def vista_dashboard(df: pd.DataFrame):
    """
    Muestra la pantalla principal (instrucciones o métricas).
    """
    st.title("Dashboard - Calendario de Contenidos")

    st.markdown(
        """
        ### Bienvenido(a)
        Esta aplicación te permite gestionar tu calendario de contenidos de manera fácil:
        1. **Data**: Agrega o edita tus eventos (fecha, título, etc.).
        2. **Vista Mensual**: Filtra los contenidos por mes.
        3. **Vista Anual**: Muestra todos los contenidos de un año.
        
        > *La información se almacena en un archivo CSV interno en Streamlit Cloud.*  
        > *Si la app se “reinicia” por inactividad, los datos pueden mantenerse, pero no es un hosting definitivo.*
        """
    )

    st.write("---")

    # Opcional: alguna métrica de ejemplo
    total_eventos = len(df)
    st.metric(label="Total de Eventos Registrados", value=total_eventos)

    # Podrías añadir más estadísticas: cuántos “Programados”, “Publicados”, etc.
    if not df.empty:
        conteo_status = df["Status"].value_counts().to_dict()
        st.write("#### Conteo por Status:")
        for status, count in conteo_status.items():
            st.write(f"- **{status}**: {count}")


def vista_data(df: pd.DataFrame):
    """
    Pantalla para agregar y editar eventos.
    """
    st.title("Gestión de Data - Agregar/Editar Eventos")
    
    # Formulario para agregar nuevo evento
    st.subheader("Agregar nuevo evento")
    with st.form("form_nuevo", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.date.today())
        titulo = st.text_input("Título/Idea", "")
        festividad = st.text_input("Festividad/Efeméride", "")
        plataforma = st.selectbox("Plataforma", ["IG","TikTok","Facebook","Blog","Otra"])
        status = st.selectbox("Status", ["Planeación","Diseño","Programado","Publicado"])
        notas = st.text_area("Notas")

        enviado = st.form_submit_button("Guardar evento")
        if enviado:
            nuevo = {
                "Fecha": fecha,
                "Titulo": titulo,
                "Festividad": festividad,
                "Plataforma": plataforma,
                "Status": status,
                "Notas": notas
            }
            df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
            guardar_datos(df)
            st.success("¡Evento agregado exitosamente!")

    # Sección para editar/borrar eventos
    st.write("---")
    st.subheader("Editar / Eliminar eventos existentes")

    if df.empty:
        st.info("No hay eventos registrados aún.")
        return

    # Mostramos la tabla con los datos
    # Podríamos permitir edición en la tabla, pero Streamlit no soporta edición en st.dataframe nativo.
    # Haremos un approach sencillo: Seleccionar un evento y modificarlo con un formulario.
    st.dataframe(df)

    # Seleccionar un evento por índice
    indices = df.index.tolist()
    if indices:
        selected_index = st.selectbox("Selecciona la fila a editar/borrar", indices)
        if selected_index is not None:
            row_data = df.loc[selected_index]

            with st.form("form_editar"):
                # Convertimos la fecha a objeto date
                fecha_edit = st.date_input("Fecha", row_data["Fecha"] if not pd.isnull(row_data["Fecha"]) else datetime.date.today())
                titulo_edit = st.text_input("Título/Idea", row_data["Titulo"])
                festividad_edit = st.text_input("Festividad/Efeméride", row_data["Festividad"])
                plataforma_edit = st.selectbox("Plataforma", ["IG","TikTok","Facebook","Blog","Otra"], index=["IG","TikTok","Facebook","Blog","Otra"].index(row_data["Plataforma"]) if row_data["Plataforma"] in ["IG","TikTok","Facebook","Blog","Otra"] else 0)
                status_edit = st.selectbox("Status", ["Planeación","Diseño","Programado","Publicado"], index=["Planeación","Diseño","Programado","Publicado"].index(row_data["Status"]) if row_data["Status"] in ["Planeación","Diseño","Programado","Publicado"] else 0)
                notas_edit = st.text_area("Notas", row_data["Notas"] if not pd.isnull(row_data["Notas"]) else "")

                submit_edit = st.form_submit_button("Guardar cambios")
                if submit_edit:
                    df.at[selected_index, "Fecha"] = fecha_edit
                    df.at[selected_index, "Titulo"] = titulo_edit
                    df.at[selected_index, "Festividad"] = festividad_edit
                    df.at[selected_index, "Plataforma"] = plataforma_edit
                    df.at[selected_index, "Status"] = status_edit
                    df.at[selected_index, "Notas"] = notas_edit

                    guardar_datos(df)
                    st.success("¡Evento editado exitosamente!")

                # Botón para borrar
                submit_delete = st.form_submit_button("Borrar este evento", help="Eliminar la fila seleccionada")
                if submit_delete:
                    df.drop(index=selected_index, inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    guardar_datos(df)
                    st.warning("Evento eliminado.")
                    st.experimental_rerun()


def vista_mensual(df: pd.DataFrame):
    """
    Pantalla para filtrar eventos por mes.
    """
    st.title("Vista Mensual de Eventos")

    if df.empty:
        st.info("No hay eventos registrados.")
        return

    # Seleccionar un mes
    mes_seleccionado = st.selectbox("Selecciona el mes", list(range(1,13)), format_func=lambda x: f"{x:02d}")
    # Filtrar
    df["Mes"] = df["Fecha"].dt.month
    filtrado = df[df["Mes"] == mes_seleccionado]

    st.write(f"Mostrando eventos del mes: {mes_seleccionado:02d}")
    st.dataframe(filtrado.drop(columns=["Mes"], errors="ignore"))

def vista_anual(df: pd.DataFrame):
    """
    Muestra todos los eventos de un año seleccionado.
    """
    st.title("Vista Anual de Eventos")

    if df.empty:
        st.info("No hay eventos registrados.")
        return

    anio = st.number_input("Año", value=2025, format="%d")
    df["Anio"] = df["Fecha"].dt.year
    filtrado = df[df["Anio"] == anio]
    st.write(f"Mostrando eventos de {anio}")
    st.dataframe(filtrado.drop(columns=["Anio","Mes"], errors="ignore"))

    # Botón extra: Exportar a Excel
    if not filtrado.empty:
        if st.button("Descargar en Excel"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                filtrado.drop(columns=["Anio","Mes"], errors="ignore").to_excel(writer, index=False, sheet_name=f"{anio}")
            excel_data = output.getvalue()
            st.download_button(
                label="Descargar Excel filtrado",
                data=excel_data,
                file_name=f"Eventos_{anio}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# -----------------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Calendario de Contenidos", layout="wide")

    # Cargamos/actualizamos el DF en cada render para reflejar cambios
    df = cargar_datos()

    # Barra lateral de navegación
    menu = ["Dashboard","Data","Vista Mensual","Vista Anual"]
    choice = st.sidebar.selectbox("Menú", menu)

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
