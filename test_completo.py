"""
Script de pruebas completo para el servicio BI
Prueba todos los endpoints y funcionalidades
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"

def print_separator(title):
    """Imprime un separador visual"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_health():
    """Prueba 1: Health Check"""
    print_separator("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Status Code: {response.status_code}")
        print(f"📄 Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_sync_status():
    """Prueba 2: Estado de Sincronización"""
    print_separator("TEST 2: Estado de Sincronización")
    
    try:
        response = requests.get(f"{BASE_URL}/sync/status")
        print(f"✅ Status Code: {response.status_code}")
        data = response.json()
        print(f"📄 Response:")
        print(f"   - Sync Enabled: {data.get('sync_enabled')}")
        print(f"   - Sync Running: {data.get('sync_running')}")
        print(f"   - Message: {data.get('message')}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_dashboard_resumen():
    """Prueba 3: Dashboard Resumen (sin filtros)"""
    print_separator("TEST 3: Dashboard Resumen (sin filtros)")
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard/resumen")
        print(f"✅ Status Code: {response.status_code}")
        data = response.json()
        
        print(f"\n📊 KPIs:")
        kpis = data.get('kpis', {})
        print(f"   - Total Clientes: {kpis.get('total_clientes')}")
        print(f"   - Total Ventas Confirmadas: {kpis.get('total_ventas_confirmadas')}")
        print(f"   - Total Monto Vendido: ${kpis.get('total_monto_vendido', 0):.2f}")
        print(f"   - Tasa de Cancelación: {kpis.get('tasa_cancelacion', 0):.2f}%")
        
        print(f"\n🏆 Top 5 Destinos:")
        for i, destino in enumerate(data.get('top_destinos', [])[:5], 1):
            print(f"   {i}. {destino.get('destino')}: ${destino.get('ingresos', 0):.2f}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_dashboard_con_filtros():
    """Prueba 4: Dashboard Resumen (con filtros de fecha)"""
    print_separator("TEST 4: Dashboard Resumen (con filtros de fecha)")
    
    # Últimos 30 días
    fecha_fin = datetime.now().date()
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    try:
        response = requests.get(
            f"{BASE_URL}/dashboard/resumen",
            params={
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat()
            }
        )
        print(f"✅ Status Code: {response.status_code}")
        print(f"📅 Período: {fecha_inicio} al {fecha_fin}")
        
        data = response.json()
        kpis = data.get('kpis', {})
        print(f"\n📊 KPIs del período:")
        print(f"   - Ventas Confirmadas: {kpis.get('total_ventas_confirmadas')}")
        print(f"   - Monto Vendido: ${kpis.get('total_monto_vendido', 0):.2f}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_margen_bruto():
    """Prueba 5: KPI Margen Bruto"""
    print_separator("TEST 5: KPI - Margen Bruto")
    
    try:
        response = requests.get(f"{BASE_URL}/kpi/margen-bruto")
        print(f"✅ Status Code: {response.status_code}")
        data = response.json()
        
        print(f"\n💰 Margen Bruto:")
        print(f"   - Margen: {data.get('margen_bruto_pct', 0):.2f}%")
        print(f"   - Ingresos: ${data.get('ingresos', 0):.2f}")
        print(f"   - Costo: ${data.get('costo', 0):.2f}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_tasa_conversion():
    """Prueba 6: KPI Tasa de Conversión"""
    print_separator("TEST 6: KPI - Tasa de Conversión")
    
    try:
        response = requests.get(f"{BASE_URL}/kpi/tasa-conversion")
        print(f"✅ Status Code: {response.status_code}")
        data = response.json()
        
        print(f"\n📈 Tasa de Conversión:")
        print(f"   - Tasa: {data.get('tasa_conversion_pct', 0):.2f}%")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_tasa_cancelacion():
    """Prueba 7: KPI Tasa de Cancelación"""
    print_separator("TEST 7: KPI - Tasa de Cancelación")
    
    try:
        response = requests.get(f"{BASE_URL}/kpi/tasa-cancelacion")
        print(f"✅ Status Code: {response.status_code}")
        data = response.json()
        
        print(f"\n🚫 Tasa de Cancelación:")
        print(f"   - Tasa: {data.get('tasa_cancelacion_pct', 0):.2f}%")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_csat():
    """Prueba 8: KPI CSAT (Satisfacción del Cliente)"""
    print_separator("TEST 8: KPI - CSAT Promedio")
    
    try:
        response = requests.get(f"{BASE_URL}/kpi/csat-promedio")
        print(f"✅ Status Code: {response.status_code}")
        data = response.json()
        
        print(f"\n⭐ CSAT Promedio:")
        print(f"   - Puntuación: {data.get('csat_promedio', 0):.2f}/5.0")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_top_destinos():
    """Prueba 9: Top Destinos"""
    print_separator("TEST 9: Analytics - Top Destinos")
    
    try:
        response = requests.get(f"{BASE_URL}/analytics/top-destinos?limit=10")
        print(f"✅ Status Code: {response.status_code}")
        data = response.json()
        
        print(f"\n🌍 Top 10 Destinos por Ingresos:")
        for i, destino in enumerate(data.get('destinos', []), 1):
            print(f"   {i}. {destino.get('destino')}: ${destino.get('ingresos', 0):.2f}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_export_csv():
    """Prueba 10: Exportar CSV"""
    print_separator("TEST 10: Exportar Ventas CSV")
    
    try:
        response = requests.get(f"{BASE_URL}/export/ventas.csv")
        print(f"✅ Status Code: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('content-type')}")
        
        # Contar líneas del CSV
        lines = response.text.split('\n')
        print(f"📊 Total de líneas en CSV: {len(lines)}")
        print(f"📋 Primeras 3 líneas:")
        for line in lines[:3]:
            print(f"   {line}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_sync_restart():
    """Prueba 11: Reiniciar Sincronización"""
    print_separator("TEST 11: Reiniciar Sincronización")
    
    try:
        response = requests.post(f"{BASE_URL}/sync/restart")
        print(f"✅ Status Code: {response.status_code}")
        data = response.json()
        print(f"📄 Response:")
        print(f"   - Status: {data.get('status')}")
        print(f"   - Message: {data.get('message')}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "PRUEBAS SERVICIO BI" + " " * 39 + "║")
    print("╚" + "═" * 78 + "╝")
    
    tests = [
        ("Health Check", test_health),
        ("Estado Sincronización", test_sync_status),
        ("Dashboard Resumen", test_dashboard_resumen),
        ("Dashboard con Filtros", test_dashboard_con_filtros),
        ("KPI Margen Bruto", test_margen_bruto),
        ("KPI Tasa Conversión", test_tasa_conversion),
        ("KPI Tasa Cancelación", test_tasa_cancelacion),
        ("KPI CSAT", test_csat),
        ("Top Destinos", test_top_destinos),
        ("Export CSV", test_export_csv),
        ("Reiniciar Sync", test_sync_restart),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error ejecutando {name}: {e}")
            results.append((name, False))
    
    # Resumen
    print_separator("RESUMEN DE PRUEBAS")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📊 Resultados:")
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {name}")
    
    print(f"\n🎯 Total: {passed}/{total} pruebas exitosas ({(passed/total*100):.1f}%)")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("✅ El servicio está listo para desplegar")
    else:
        print(f"\n⚠️ {total - passed} prueba(s) fallaron")
        print("❌ Revisa los errores antes de desplegar")
    
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    run_all_tests()
