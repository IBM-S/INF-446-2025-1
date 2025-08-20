import glob
import hashlib
import os
import re
from collections import defaultdict

# --- CONFIGURACIÓN ---
# Carpeta donde están los archivos
folder = "SAVING/MOEAD/POF"
# Patrón para encontrar todos los archivos de interés
pattern = os.path.join(folder, "POF_*_GEN*.dat")

# --- FUNCIONES AUXILIARES ---

def file_hash(path):
    """Calcula el hash MD5 del contenido de un archivo."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def compactar_indices(indices):
    """Recibe una lista de índices y devuelve una cadena con rangos compactados.
    Ejemplo: [1, 2, 3, 5, 6, 8] -> "1 - 3, 5 - 6, 8"
    """
    if not indices:
        return ""
    indices = sorted(indices)
    grupos = []
    inicio = fin = indices[0]

    for i in indices[1:]:
        if i == fin + 1:
            fin = i
        else:
            grupos.append(f"{inicio} - {fin}" if inicio != fin else str(inicio))
            inicio = fin = i

    grupos.append(f"{inicio} - {fin}" if inicio != fin else str(inicio))
    return ", ".join(grupos)

def get_gen_number(filepath):
    """Extrae el número de generación del nombre del archivo para poder ordenar."""
    # Usamos una expresión regular para buscar '_GEN_' seguido de números
    match = re.search(r'_GEN_(\d+)\.dat$', filepath)
    if match:
        return int(match.group(1))
    return 0 # Devuelve 0 si no encuentra el patrón, para ordenar al principio

# --- SCRIPT PRINCIPAL ---

# 1. Encontrar todos los archivos que coinciden con el patrón
all_files = glob.glob(pattern)

if not all_files:
    print("⚠️ No se encontraron archivos con el patrón especificado.")
    exit()

print(f"✅ Se encontraron {len(all_files)} archivos en total. Agrupando por instancia...")

# 2. Agrupar archivos por su nombre de instancia
instance_files = defaultdict(list)
for filepath in all_files:
    # Extraemos el nombre de la instancia (ej: "POF_100-3.dat")
    # del nombre completo del archivo (ej: "POF_100-3.dat_GEN_1.dat")
    filename = os.path.basename(filepath)
    instance_name = filename.split('_GEN_')[0]
    instance_files[instance_name].append(filepath)

if not instance_files:
    print("🤷 No se pudo agrupar ningún archivo por instancia. Revisa los nombres de archivo.")
    exit()

# 3. Analizar cada grupo de instancia por separado
for instance_name, files in instance_files.items():
    print("\n" + "="*50)
    print(f"📊 Analizando Instancia: {instance_name}")
    print("="*50)

    # Ordenar los archivos de la instancia actual por su número de generación
    files = sorted(files, key=get_gen_number)
    
    # Extraer los números de generación para un etiquetado correcto
    gen_numbers = [get_gen_number(f) for f in files]

    print(f"🔍 Se encontraron {len(files)} generaciones para esta instancia.\n")

    # --- Análisis 1: Grupos de generaciones consecutivas con el mismo contenido ---
    prev_hash = None
    start_gen = None
    groups = []

    for i, file in enumerate(files):
        current_hash = file_hash(file)
        current_gen = gen_numbers[i]

        if prev_hash is None: # Primera iteración
            prev_hash = current_hash
            start_gen = current_gen
        elif current_hash != prev_hash:
            # Fin del grupo anterior. Lo guardamos.
            end_gen = gen_numbers[i-1]
            groups.append((start_gen, end_gen))
            # Empezamos un nuevo grupo
            start_gen = current_gen
            prev_hash = current_hash

    # Guardar el último grupo
    if start_gen is not None:
        groups.append((start_gen, gen_numbers[-1]))

    print("📌 Grupos de generaciones consecutivas iguales:")
    for inicio, fin in groups:
        if inicio == fin:
            print(f"Generación: {inicio}")
        else:
            print(f"Generaciones: {inicio} - {fin} (son idénticas)")

    # --- Análisis 2: Todos los archivos iguales, sin importar el orden ---
    hash_to_gens = defaultdict(list)
    for i, file in enumerate(files):
        h = file_hash(file)
        gen_num = gen_numbers[i]
        hash_to_gens[h].append(gen_num)

    print("\n📌 Grupos de generaciones idénticas (sin importar el orden):")
    found_duplicates = False
    for h, indices in hash_to_gens.items():
        if len(indices) > 1:
            found_duplicates = True
            print(f"  - Grupo de {len(indices)} generaciones idénticas: {compactar_indices(indices)}")
    
    if not found_duplicates:
        print("  - No se encontraron generaciones duplicadas en esta instancia.")

print("\n\n✨ Análisis completado.")