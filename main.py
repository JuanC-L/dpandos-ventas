import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Registro de Ventas - Panadería", layout="wide")

# ---- DATOS BÁSICOS ----
locales = ["El Agustino", "Carapongo", "SJL", "Santa Anita"]
tipos_pago = ["Yape", "Tarjeta", "Efectivo", "Varios"]

# Cargar datos
productos_df = pd.read_excel("productos.xlsx")
try:
    stock_df = pd.read_excel("stock.xlsx")
except FileNotFoundError:
    stock_df = pd.DataFrame(columns=["Local", "Producto", "Stock Actual"])

# ---- SIDEBAR ----
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/135/135620.png", width=64)
    st.title("Panaderías")
    local = st.selectbox("Selecciona el local", locales)
    st.markdown("---")
    st.info("Todos los registros quedarán vinculados al local elegido.")

# ---- PESTAÑAS ----
tabs = st.tabs(
    [
        "🛒 Registro de Ventas",
        "📦 Gestión de Stock"
    ]
)

# ---- TAB: REGISTRO DE VENTAS ----
with tabs[0]:
    st.markdown("## 🛒 Registro de Ventas")
    with st.container():
        st.write("Completa el formulario para registrar una venta.")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            fecha = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
            categoria = st.selectbox("Categoría", productos_df['Categoria'].unique())
        with col2:
            productos_cat = productos_df[productos_df['Categoria'] == categoria]
            producto = st.selectbox("Producto", productos_cat['Producto'])
            precio = float(productos_cat[productos_cat['Producto'] == producto]['Precio'].values[0])
            st.markdown(f"<span style='font-size: 16px;'>Precio: <b>S/ {precio:.2f}</b></span>", unsafe_allow_html=True)
        with col3:
            stock_actual = stock_df.query("Local == @local and Producto == @producto")["Stock Actual"].sum()
            st.markdown(f"<span style='color: #388e3c; font-size: 16px;'>Stock actual: <b>{int(stock_actual)}</b></span>", unsafe_allow_html=True)
            salida = st.number_input("Cantidad a vender", min_value=0, max_value=int(stock_actual), step=1)
            tipo_pago = st.selectbox("Tipo de pago", tipos_pago)

        venta = salida * precio
        st.markdown(f"### Total venta: <span style='color:#1976d2'>S/ {venta:.2f}</span>", unsafe_allow_html=True)
        st.markdown("---")

        boton = st.button("💾 Registrar venta", use_container_width=True)

        if boton:
            if salida == 0:
                st.warning("Debe registrar una cantidad mayor a cero.")
            elif salida > stock_actual:
                st.error("No hay suficiente stock para esta venta.")
            else:
                nueva_venta = {
                    "Fecha": fecha,
                    "Local": local,
                    "Categoría": categoria,
                    "Producto": producto,
                    "Cantidad": salida,
                    "Precio": precio,
                    "Venta": venta,
                    "Tipo de pago": tipo_pago
                }
                ventas_file = "ventas_registradas.csv"
                try:
                    ventas_df = pd.read_csv(ventas_file)
                except FileNotFoundError:
                    ventas_df = pd.DataFrame()
                ventas_df = pd.concat([ventas_df, pd.DataFrame([nueva_venta])], ignore_index=True)
                ventas_df.to_csv(ventas_file, index=False)

                # Actualizar stock
                idx = stock_df[(stock_df["Local"] == local) & (stock_df["Producto"] == producto)].index
                if not idx.empty:
                    stock_df.loc[idx, "Stock Actual"] -= salida
                else:
                    stock_df = pd.concat([stock_df, pd.DataFrame([{"Local": local, "Producto": producto, "Stock Actual": -salida}])], ignore_index=True)
                stock_df.to_excel("stock.xlsx", index=False)
                st.success("✅ Venta registrada y stock actualizado.")

    # Dashboard: resumen por tipo de pago
    st.markdown("## 📊 Resumen de Ventas")
    try:
        ventas_hist = pd.read_csv("ventas_registradas.csv")
        ventas_hist = ventas_hist[ventas_hist['Local'] == local]
        if ventas_hist.empty:
            st.info("Aún no hay ventas registradas para este local.")
        else:
            st.dataframe(ventas_hist.style.format({"Precio": "S/ {:.2f}", "Venta": "S/ {:.2f}"}), use_container_width=True)
            st.markdown("### Ventas por producto")
            st.bar_chart(ventas_hist.groupby('Producto')['Venta'].sum())

            st.markdown("### Totales por tipo de pago")
            resumen_pago = ventas_hist.groupby("Tipo de pago")["Venta"].sum().reset_index()
            resumen_pago.columns = ["Tipo de pago", "Total S/"]
            st.table(resumen_pago.style.format({"Total S/": "S/ {:.2f}"}))

            st.markdown(f"### <span style='color:#43a047;'>Total general: <b>S/ {ventas_hist['Venta'].sum():.2f}</b></span>", unsafe_allow_html=True)
    except Exception:
        st.info("Aún no hay ventas registradas para este local.")

# ---- TAB: GESTIÓN DE STOCK ----
with tabs[1]:
    st.markdown("## 📦 Gestión de Stock")
    st.write("Actualiza manualmente el stock de los productos según inventario físico o ingreso de mercadería.")
    prod_stock = st.selectbox("Producto", productos_df['Producto'].unique(), key="stock_prod")
    nuevo_stock = st.number_input("Ajustar stock (nuevo valor)", min_value=0, step=1, key="stock_nuevo")
    if st.button("Actualizar stock", use_container_width=True):
        idx = stock_df[(stock_df["Local"] == local) & (stock_df["Producto"] == prod_stock)].index
        if not idx.empty:
            stock_df.loc[idx, "Stock Actual"] = nuevo_stock
        else:
            stock_df = pd.concat([stock_df, pd.DataFrame([{"Local": local, "Producto": prod_stock, "Stock Actual": nuevo_stock}])], ignore_index=True)
        stock_df.to_excel("stock.xlsx", index=False)
        st.success("Stock actualizado correctamente.")

    st.markdown("### 📝 Stock actual del local")
    st.dataframe(stock_df[stock_df["Local"] == local].sort_values("Producto").reset_index(drop=True), use_container_width=True)

st.markdown("---")
st.caption("Hecho con ❤️ para la gestión de tus panaderías")
