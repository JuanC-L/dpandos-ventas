import streamlit as st
import pandas as pd
from datetime import date, datetime
import requests
import json

st.set_page_config(page_title="Registro de Ventas - Panadería", layout="wide")

# Configuración de Supabase
SUPABASE_URL = "https://tbzqbojmnbxhliblgoss.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRienFib2ptbmJ4aGxpYmxnb3NzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk4NDYwNzIsImV4cCI6MjA2NTQyMjA3Mn0.Q_wK9y4aM2ARIeKQ2DoXu5JyFOqh5dbdlYqtYx52Kbc"

class SupabaseDB:
    def __init__(self, url, key):
        self.url = url
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def _make_request(self, method, endpoint, data=None):
        """Método centralizado para hacer requests"""
        try:
            url = f"{self.url}/rest/v1/{endpoint}"
            response = requests.request(method, url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201, 204]:
                return True, response.json() if response.content else None
            else:
                st.error(f"Error {response.status_code}: {response.text}")
                return False, None
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            return False, None
    
    def get_data(self, table, filters=None, select="*", order=None):
        """Obtiene datos de una tabla"""
        endpoint = f"{table}?select={select}"
        if filters:
            endpoint += f"&{filters}"
        if order:
            endpoint += f"&order={order}"
        
        success, data = self._make_request("GET", endpoint)
        return data if success and data else []
    
    def call_rpc(self, function_name, params=None):
        """Llama a función RPC"""
        success, data = self._make_request("POST", f"rpc/{function_name}", params or {})
        return data if success else None
    
    def insert_data(self, table, data):
        """Inserta datos"""
        success, result = self._make_request("POST", table, data)
        return success, result
    
    # Métodos específicos del negocio
    def get_productos(self):
        return self.get_data("productos", order="categoria,producto")
    
    def get_stock_local(self, local):
        return self.get_data("stock", 
                           filters=f"local=eq.{local}",
                           select="producto,stock_actual",
                           order="producto")
    
    def get_stock_producto(self, local, producto):
        result = self.get_data("stock", 
                             filters=f"local=eq.{local}&producto=eq.{producto}",
                             select="stock_actual")
        return result[0]['stock_actual'] if result else 0
    
    def registrar_venta(self, venta_data):
        return self.call_rpc("registrar_venta_con_stock", {
            "p_fecha": venta_data["fecha"],
            "p_local": venta_data["local"],
            "p_categoria": venta_data["categoria"],
            "p_producto": venta_data["producto"],
            "p_cantidad": venta_data["cantidad"],
            "p_precio": venta_data["precio"],
            "p_venta": venta_data["venta"],
            "p_tipo_pago": venta_data["tipo_pago"]
        })
    
    def actualizar_stock(self, local, producto, nuevo_stock):
        return self.call_rpc("upsert_stock", {
            "p_local": local,
            "p_producto": producto,
            "p_stock_actual": nuevo_stock
        })
    
    def registrar_gasto(self, gasto_data):
        success, result = self.insert_data("gastos", gasto_data)
        return result if success else None
    
    def registrar_salida(self, salida_data):
        return self.call_rpc("registrar_salida_con_stock", {
            "p_fecha": salida_data["fecha"],
            "p_local": salida_data["local"],
            "p_producto": salida_data["producto"],
            "p_cantidad": salida_data["cantidad"],
            "p_motivo": salida_data["motivo"],
            "p_observaciones": salida_data.get("observaciones", "")
        })
    
    def get_ventas_local(self, local, fecha_inicio=None, fecha_fin=None):
        filters = f"local=eq.{local}"
        if fecha_inicio and fecha_fin:
            filters += f"&fecha=gte.{fecha_inicio}&fecha=lte.{fecha_fin}"
        return self.get_data("ventas", filters=filters, order="fecha.desc,id.desc")
    
    def get_gastos_local(self, local, fecha_inicio=None, fecha_fin=None):
        filters = f"local=eq.{local}"
        if fecha_inicio and fecha_fin:
            filters += f"&fecha=gte.{fecha_inicio}&fecha=lte.{fecha_fin}"
        return self.get_data("gastos", filters=filters, order="fecha.desc,id.desc")
    
    def get_salidas_local(self, local):
        return self.get_data("salidas", 
                           filters=f"local=eq.{local}",
                           order="fecha.desc,id.desc")
    
    def get_dashboard_data(self, local, fecha_inicio, fecha_fin):
        return self.call_rpc("get_dashboard_resumen", {
            "p_local": local,
            "p_fecha_inicio": fecha_inicio,
            "p_fecha_fin": fecha_fin
        })

# Inicializar DB
@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return SupabaseDB(SUPABASE_URL, SUPABASE_KEY)

db = init_supabase()

if not db:
    st.stop()

# Configuraciones básicas
LOCALES = ["El Agustino", "Carapongo", "SJL", "Santa Anita"]
TIPOS_PAGO = ["Yape", "Tarjeta", "Efectivo", "Varios"]
TIPOS_GASTO = ["Insumos", "Servicios", "Personal", "Alquiler", "Transporte", "Otros"]
MOTIVOS_SALIDA = ["Vencido", "Dañado", "Degustación", "Merma", "Donación", "Otros"]

# SIDEBAR
with st.sidebar:
    st.title("🥖 Panaderías")
    local = st.selectbox("Selecciona el local", LOCALES)
    if st.button("🔄 Refrescar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# TABS PRINCIPALES
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🛒 Ventas", "📦 Stock", "💰 Gastos", "📉 Salidas", "📊 Dashboard"
])

# TAB 1: VENTAS
with tab1:
    st.header("🛒 Registro de Ventas")
    
    productos = db.get_productos()
    if not productos:
        st.error("No se pudieron cargar los productos")
        st.stop()
    
    productos_df = pd.DataFrame(productos)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_venta = st.date_input("📅 Fecha", date.today(), key="fecha_venta")
        categoria = st.selectbox("📋 Categoría", productos_df['categoria'].unique(), key="categoria_venta")
    
    with col2:
        productos_cat = productos_df[productos_df['categoria'] == categoria]
        producto = st.selectbox("🥖 Producto", productos_cat['producto'], key="producto_venta")
        precio = float(productos_cat[productos_cat['producto'] == producto]['precio'].iloc[0])
        st.info(f"💰 Precio: S/ {precio:.2f}")
    
    with col3:
        stock_actual = db.get_stock_producto(local, producto)
        st.success(f"📦 Stock: {int(stock_actual)}")
        cantidad = st.number_input("🔢 Cantidad", min_value=0, max_value=int(stock_actual) if stock_actual > 0 else 100, key="cantidad_venta")
        tipo_pago = st.selectbox("💳 Pago", TIPOS_PAGO, key="tipo_pago_venta")
    
    total = cantidad * precio
    st.metric("💵 Total Venta", f"S/ {total:.2f}")
    
    if st.button("💾 Registrar Venta", type="primary", use_container_width=True):
        if cantidad <= 0:
            st.warning("⚠️ Cantidad debe ser mayor a cero")
        elif cantidad > stock_actual:
            st.error("❌ Stock insuficiente")
        else:
            venta = {
                "fecha": fecha_venta.strftime("%Y-%m-%d"),
                "local": local,
                "categoria": categoria,
                "producto": producto,
                "cantidad": cantidad,
                "precio": precio,
                "venta": total,
                "tipo_pago": tipo_pago
            }
            
            result = db.registrar_venta(venta)
            if result and result.get('success'):
                st.success(f"✅ {result['message']} - Stock: {result['nuevo_stock']}")
                st.rerun()
            else:
                st.error(f"❌ {result.get('message', 'Error') if result else 'Error de conexión'}")

# TAB 2: STOCK
with tab2:
    st.header("📦 Gestión de Stock")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔄 Actualizar Stock")
        productos = db.get_productos()
        if productos:
            productos_df = pd.DataFrame(productos)
            prod_stock = st.selectbox("🥖 Producto", productos_df['producto'].unique(), key="producto_stock")
            nuevo_stock = st.number_input("📊 Nuevo Stock", min_value=0, key="nuevo_stock")
            
            if st.button("✅ Actualizar", type="primary"):
                result = db.actualizar_stock(local, prod_stock, nuevo_stock)
                if result and result.get('success'):
                    st.success(f"✅ Stock actualizado: {result['stock_actual']}")
                    st.rerun()
                else:
                    st.error("❌ Error actualizando stock")
    
    with col2:
        st.subheader("📋 Stock Actual")
        stock_data = db.get_stock_local(local)
        if stock_data:
            stock_df = pd.DataFrame(stock_data)
            st.dataframe(stock_df, use_container_width=True)
        else:
            st.info("📭 No hay stock registrado")

# TAB 3: GASTOS
with tab3:
    st.header("💰 Gastos Diarios")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("➕ Nuevo Gasto")
        fecha_gasto = st.date_input("📅 Fecha", date.today(), key="fecha_gasto")
        tipo_gasto = st.selectbox("📋 Tipo", TIPOS_GASTO, key="tipo_gasto")
        descripcion = st.text_input("📝 Descripción", key="descripcion_gasto")
        monto = st.number_input("💰 Monto (S/)", min_value=0.01, format="%.2f", key="monto_gasto")
        
        if st.button("💸 Registrar Gasto", type="primary"):
            if descripcion.strip():
                gasto = {
                    "fecha": fecha_gasto.strftime("%Y-%m-%d"),
                    "local": local,
                    "tipo": tipo_gasto,
                    "descripcion": descripcion,
                    "monto": monto
                }
                result = db.registrar_gasto(gasto)
                if result:
                    st.success("✅ Gasto registrado")
                    st.rerun()
                else:
                    st.error("❌ Error registrando gasto")
            else:
                st.warning("⚠️ Ingrese descripción")
    
    with col2:
        st.subheader("📋 Gastos Registrados")
        gastos = db.get_gastos_local(local)
        if gastos:
            gastos_df = pd.DataFrame(gastos)
            st.dataframe(gastos_df, use_container_width=True)
            st.metric("💸 Total Gastos", f"S/ {gastos_df['monto'].sum():.2f}")
        else:
            st.info("📭 No hay gastos registrados")

# TAB 4: SALIDAS
with tab4:
    st.header("📉 Salidas y Mermas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("➖ Nueva Salida")
        productos = db.get_productos()
        if productos:
            productos_df = pd.DataFrame(productos)
            fecha_salida = st.date_input("📅 Fecha", date.today(), key="fecha_salida")
            producto_salida = st.selectbox("🥖 Producto", productos_df['producto'].unique(), key="producto_salida")
            
            stock_disponible = db.get_stock_producto(local, producto_salida)
            st.info(f"📦 Stock disponible: {int(stock_disponible)}")
            
            cantidad_salida = st.number_input("🔢 Cantidad", min_value=1, max_value=int(stock_disponible) if stock_disponible > 0 else 1, key="cantidad_salida")
            motivo = st.selectbox("📋 Motivo", MOTIVOS_SALIDA, key="motivo_salida")
            observaciones = st.text_area("📝 Observaciones", key="observaciones_salida")
            
            if st.button("📤 Registrar Salida", type="primary"):
                if cantidad_salida > stock_disponible:
                    st.error("❌ Stock insuficiente")
                else:
                    salida = {
                        "fecha": fecha_salida.strftime("%Y-%m-%d"),
                        "local": local,
                        "producto": producto_salida,
                        "cantidad": cantidad_salida,
                        "motivo": motivo,
                        "observaciones": observaciones
                    }
                    
                    result = db.registrar_salida(salida)
                    if result and result.get('success'):
                        st.success(f"✅ {result['message']} - Stock: {result['nuevo_stock']}")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('message', 'Error') if result else 'Error de conexión'}")
    
    with col2:
        st.subheader("📋 Historial Salidas")
        salidas = db.get_salidas_local(local)
        if salidas:
            salidas_df = pd.DataFrame(salidas)
            st.dataframe(salidas_df, use_container_width=True)
        else:
            st.info("📭 No hay salidas registradas")

# TAB 5: DASHBOARD
with tab5:
    st.header("📊 Dashboard")
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("📅 Desde", date.today().replace(day=1))
    with col2:
        fecha_fin = st.date_input("📅 Hasta", date.today())
    
    # Obtener datos del dashboard
    dashboard_data = db.get_dashboard_data(local, fecha_inicio.strftime("%Y-%m-%d"), fecha_fin.strftime("%Y-%m-%d"))
    
    if dashboard_data and len(dashboard_data) > 0:
        data = dashboard_data[0] if isinstance(dashboard_data, list) else dashboard_data
        total_ventas = float(data.get('total_ventas', 0) or 0)
        total_gastos = float(data.get('total_gastos', 0) or 0)
        total_unidades = int(data.get('total_unidades', 0) or 0)
        ganancia_neta = float(data.get('ganancia_neta', 0) or 0)
    else:
        total_ventas = total_gastos = ganancia_neta = 0
        total_unidades = 0
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Ventas", f"S/ {total_ventas:.2f}")
    with col2:
        st.metric("💸 Gastos", f"S/ {total_gastos:.2f}")
    with col3:
        st.metric("📈 Ganancia", f"S/ {ganancia_neta:.2f}")
    with col4:
        st.metric("📦 Unidades", f"{total_unidades}")
    
    # Gráficos
    ventas_data = db.get_ventas_local(local, fecha_inicio.strftime("%Y-%m-%d"), fecha_fin.strftime("%Y-%m-%d"))
    
    if ventas_data:
        ventas_df = pd.DataFrame(ventas_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🥖 Ventas por Producto")
            ventas_producto = ventas_df.groupby('producto')['venta'].sum().sort_values(ascending=False)
            st.bar_chart(ventas_producto)
        
        with col2:
            st.subheader("💳 Ventas por Tipo de Pago")
            ventas_pago = ventas_df.groupby('tipo_pago')['venta'].sum()
            st.bar_chart(ventas_pago)
        
        st.subheader("📋 Detalle de Ventas")
        st.dataframe(ventas_df, use_container_width=True)
    else:
        st.info("📭 No hay ventas en el período seleccionado")

