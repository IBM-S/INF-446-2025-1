import json
import pandas as pd
import os
import time
import numpy as np

PATH_ARCHIVO_DELITOS_JSON = "INSTANCES Camera/DatosProcesadosGeoJSON/GeoJSON/reportes_incidenciaU.geojson"

def analizar_delitos(archivo_geojson):
    """
    Función principal para leer, procesar y analizar los datos de delitos.
    """
    print(f"Cargando el archivo: {archivo_geojson}...")
    start_lectura = time.time()

    try:
        with open(archivo_geojson, 'r', encoding='utf-8') as f:
            data_geojson = json.load(f)
        end_lectura = time.time() 
        tiempo_lectura = end_lectura - start_lectura
    except FileNotFoundError:
        print(f"Error: No se encontro el archivo '{archivo_geojson}")
        return
    except json.JSONDecodeError:
        print(f"Error: El archivo '{archivo_geojson}' no es un JSON valido")
        return

    lista_de_delitos = [feature['properties'] for feature in data_geojson['features']]

    df = pd.DataFrame(lista_de_delitos)
    print(f"Tiempo de carga y lectura del archivo: {tiempo_lectura:.2f} segundos.")
    print(F"Se cargaron {len(df)} registros en total")

    df_alto_impacto = df[df['impacto_delito'] == 'DELITO DE ALTO IMPACTO'].copy()
    print(f"Se encontraron {len(df_alto_impacto)} delitos de alto impacto")

    if df_alto_impacto.empty:
        print("No se encontraron delitos de alto impacto paara analizar")
        return
    # Analisis estadistico

    # Frecuencia y probablidad por categoria de delito de alto impacto
    print("\n--- Analisis 1: Frecuencia de Delitos de Alto Impacto ---")
    conteo_por_categoria = df_alto_impacto['categoria_delito'].value_counts()
    probabilidad_por_categoria = df_alto_impacto['categoria_delito'].value_counts(normalize=True)*100

    stats_categoria = pd.DataFrame({
        'Cantidad': conteo_por_categoria,
        'Probabilidad (%)': probabilidad_por_categoria.round(2)
    })
    print(stats_categoria)

    # Cantidad de delitos de alto impacto por año
    print("\n --- Analisis 2:Total de Delitos de Alto Impacto por año ---")

    # Usamos .astype(str) para que todos los valores de la columna sean texto y se puedan agrupar correctamente.
    df_alto_impacto['anio_agrupado'] = np.where(
        df_alto_impacto['anio_hecho'] <= 2010,
        '2010 y Anteriores',
        df_alto_impacto['anio_hecho'].astype(str)
    )

    conteo_por_año = df_alto_impacto['anio_hecho'].value_counts().sort_index()
    #print(conteo_por_año)
    conteo_por_año_agrupado  = df_alto_impacto['anio_hecho'].value_counts().sort_index()
    print(conteo_por_año_agrupado)

    # Matriz de delitos por alcaldia (¿Que delito es mas comun en cada alcaldia?)
    print("\n--- Analisis 3: Matriz de Delitos vs Alcaldias ---")
    matriz_delitos_alcaldias = pd.crosstab(df_alto_impacto['alcaldia'], df_alto_impacto['categoria_delito'])
    print(matriz_delitos_alcaldias)

    print("\n--- Guardando resultados en archivos CSV ---")
    
    # Crear una carpeta para guardar los resultados si no existe
    if not os.path.exists('analisis_delitos'):
        os.makedirs('analisis_delitos')

    stats_categoria.to_csv('analisis_delitos/estadisticas_por_categoria_delito.csv')
    conteo_por_año.to_csv('analisis_delitos/estadisticas_por_anio.csv')
    matriz_delitos_alcaldias.to_csv('analisis_delitos/matriz_alcaldia_vs_delito.csv')
    
    print("¡Análisis completo! Los archivos CSV se han guardado en la carpeta 'analisis_delitos'.")



if __name__ == "__main__":
    start_total = time.time()

    analizar_delitos(PATH_ARCHIVO_DELITOS_JSON)

    end_total = time.time() 
    tiempo_total = end_total - start_total 

    print(f"\n--- TIEMPO TOTAL DE EJECUCIÓN: {tiempo_total:.2f} segundos ---") 
