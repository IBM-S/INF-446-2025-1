import json
import os
import time
import pandas as pd
import unicodedata
import numpy as np
from pathlib import Path

# ================= CONFIGURACIÓN DE RUTAS =================
# Basado en tu estructura: TT2/visualizador_web/este_script.py
BASE_DIR = Path(__file__).resolve().parent

# Subimos niveles para llegar a la carpeta de datos de EMO-D
PATH_INPUT_DIR = BASE_DIR.parent / "EMO-D" / "MOEAD" / "INSTANCES Camera" / "DatosProcesadosGeoJSON" / "GeoJSON"
FILE_DELITOS = PATH_INPUT_DIR / "reportes_incidenciaU.geojson"
FILE_CAMARAS = PATH_INPUT_DIR / "camaraPosU.geojson"

# Ruta de salida para guardar las instancias
PATH_OUTPUT_DIR = BASE_DIR.parent / "datos" / "inst"

# Parámetros fijos del algoritmo
PARAM_P = 100000.0
PARAM_R = 200.0
PARAM_C1 = 1.0
PARAM_C2 = 0.2

def normalizar_texto(texto):
    """
    Limpia los nombres de las alcaldías para asegurar que coincidan.
    Ej: "Álvaro Obregón" -> "ALVARO OBREGON"
    """
    if not isinstance(texto, str):
        return "DESCONOCIDO"
    
    # Normalizar caracteres unicode (quitar acentos)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = texto.upper().strip()
    
    # Correcciones específicas comunes en CDMX
    if "MIGUEL HIDALGO" in texto: return "MIGUEL HIDALGO"
    if "CUAJIMALPA" in texto: return "CUAJIMALPA DE MORELOS"
    return texto

def cargar_geojson_utm(ruta_archivo):
    """
    Carga un GeoJSON asumiendo que sus coordenadas YA están en UTM (Metros).
    Lee directamente geometry['coordinates'].
    """
    if not ruta_archivo.exists():
        print(f"[ERROR] No se encontró el archivo: {ruta_archivo}")
        return pd.DataFrame()
    
    print(f"Cargando: {ruta_archivo.name} ...")
    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rows = []
    for feature in data['features']:
        props = feature['properties']
        geom = feature['geometry']
        
        # Solo nos interesan los Puntos
        if geom is not None and geom['type'] == 'Point':
            coords = geom['coordinates']
            # En tus archivos: coords[0] es X (Este), coords[1] es Y (Norte)
            props['coord_x'] = coords[0]
            props['coord_y'] = coords[1]
            rows.append(props)
            
    return pd.DataFrame(rows)

def calcular_probabilidades(df_delitos):
    """
    Calcula la probabilidad de cada tipo de delito basado en su frecuencia
    dentro del conjunto de ALTO IMPACTO.
    """
    total = len(df_delitos)
    if total == 0:
        return {}
    
    conteo = df_delitos['categoria_delito'].value_counts()
    # Probabilidad = Frecuencia / Total
    probs = (conteo / total).to_dict()
    
    print(f"   -> Probabilidades calculadas sobre {total} delitos.")
    return probs

def generar_instancias():
    # 1. Preparar directorio de salida
    PATH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Cargar los datos (Ya vienen en UTM, no transformamos nada)
    df_delitos_raw = cargar_geojson_utm(FILE_DELITOS)
    df_camaras_raw = cargar_geojson_utm(FILE_CAMARAS)

    if df_delitos_raw.empty or df_camaras_raw.empty:
        print("Datos insuficientes para continuar.")
        return

    # 3. Filtrar SOLO Delitos de Alto Impacto
    # Convertimos a mayúsculas para asegurar match
    df_delitos_raw['impacto_upper'] = df_delitos_raw['impacto_delito'].astype(str).str.upper()
    df_alto_impacto = df_delitos_raw[df_delitos_raw['impacto_upper'] == 'DELITO DE ALTO IMPACTO'].copy()
    
    print(f"   -> Delitos totales: {len(df_delitos_raw)}")
    print(f"   -> Delitos Alto Impacto: {len(df_alto_impacto)}")

    # 4. Calcular mapa de probabilidades
    mapa_probs = calcular_probabilidades(df_alto_impacto)

    # 5. Normalizar nombres de Alcaldía para poder agrupar
    df_alto_impacto['alcaldia_norm'] = df_alto_impacto['alcaldia'].apply(normalizar_texto)
    df_camaras_raw['alcaldia_norm'] = df_camaras_raw['alcaldia'].apply(normalizar_texto)

    # Obtener lista de alcaldías válidas (ignorando DESCONOCIDO)
    alcaldias = [alc for alc in df_alto_impacto['alcaldia_norm'].unique() if alc != "DESCONOCIDO"]
    alcaldias.sort()

    # Contadores globales para reporte final
    total_instancias = 0
    huerfanos_c = len(df_camaras_raw[df_camaras_raw['alcaldia_norm'] == "DESCONOCIDO"])
    huerfanos_d = len(df_alto_impacto[df_alto_impacto['alcaldia_norm'] == "DESCONOCIDO"])

    # 6. Iterar por cada alcaldía y crear su archivo
    print("\n--- Generando Archivos .dat ---")
    for alcaldia in alcaldias:
        # Filtrar datos locales
        datos_delitos = df_alto_impacto[df_alto_impacto['alcaldia_norm'] == alcaldia]
        datos_camaras = df_camaras_raw[df_camaras_raw['alcaldia_norm'] == alcaldia]

        if datos_delitos.empty and datos_camaras.empty:
            continue

        # Lista final de puntos para el archivo
        lista_puntos = []

        # A. Agregar Cámaras (Flag=1, Prob=1.00)
        for _, row in datos_camaras.iterrows():
            lista_puntos.append({
                'x': row['coord_x'],
                'y': row['coord_y'],
                'flag': 1,
                'prob': 1.00
            })

        # B. Agregar Delitos (Flag=0, Prob=Calculada)
        for _, row in datos_delitos.iterrows():
            cat = row['categoria_delito']
            # Obtener prob, si no existe (raro) usar 0.01 por defecto
            prob = mapa_probs.get(cat, 0.01)
            
            lista_puntos.append({
                'x': row['coord_x'],
                'y': row['coord_y'],
                'flag': 0,
                'prob': prob
            })

        N = len(lista_puntos)
        
        # C. Escribir el archivo .dat
        nombre_archivo = f"cam_{N}_{alcaldia.replace(' ', '_')}.dat"
        nombre_parametro = f"{alcaldia.lower()}_alto_impacto.dat"
        ruta_completa = PATH_OUTPUT_DIR / nombre_archivo

        # Construcción del contenido del archivo
        lines = []
        lines.append("/* CONJUNTOS */")
        lines.append(f"param N_total:= {N} ;")
        lines.append("")
        lines.append("/* PARAMETROS */")
        lines.append(f"param P:= {PARAM_P} ;")
        lines.append(f"param R:= {PARAM_R} ;")
        lines.append(f"param c1:= {PARAM_C1} ;")
        lines.append(f"param c2:= {PARAM_C2} ;")
        lines.append(f'param nombre_instancia := "{nombre_parametro}" ;')
        lines.append("")
        lines.append("param : coordx coordy flag prob_ohca:=")

        # Escribir puntos (ID coordX coordY flag prob)
        for i, p in enumerate(lista_puntos, 1):
            lines.append(f"{i} {p['x']:.6f} {p['y']:.6f} {p['flag']} {p['prob']:.4f}")
        
        lines.append(";") # Cierre del param

        # Guardar en disco
        try:
            with open(ruta_completa, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"[OK] {alcaldia}: {len(datos_camaras)} cams + {len(datos_delitos)} delitos -> {nombre_archivo}")
            total_instancias += 1
        except Exception as e:
            print(f"[ERROR] Al escribir {alcaldia}: {e}")

    print("\n================ RESUMEN ================")
    print(f"Instancias creadas: {total_instancias}")
    print(f"Ubicación: {PATH_OUTPUT_DIR}")
    if huerfanos_c > 0 or huerfanos_d > 0:
        print(f"NOTA: Se encontraron {huerfanos_c} cámaras y {huerfanos_d} delitos sin alcaldía válida.")
        print("      Estos puntos no se agregaron a ninguna instancia.")
    print("=========================================")

if __name__ == "__main__":
    print("--- INICIANDO PROCESO ---")
    start_time = time.time()

    total = generar_instancias()

    end_time = time.time()
    duracion = end_time - start_time

    print("\n================ RESUMEN ================")
    print(f"Tiempo total de ejecución: {duracion:.2f} segundos")
    print("=========================================")