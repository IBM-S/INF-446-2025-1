import glob
import hashlib
import os
from collections import defaultdict


# Carpeta donde están los archivos
folder = "SAVING/MOEAD/POF"
pattern = os.path.join(folder, "POF_*_GEN*.dat")

# Función para calcular hash del archivo (para comparar)

def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def compactar_indices(indices):
    """Recibe una lista de índices y devuelve una lista con rangos compactados."""
    indices = sorted(indices)
    grupos = []
    inicio = indices[0]
    fin = indices[0]

    for i in indices[1:]:
        if i == fin + 1:
            fin = i
        else:
            grupos.append(f"{inicio} - {fin}" if inicio != fin else str(inicio))
            inicio = fin = i

    grupos.append(f"{inicio} - {fin}" if inicio != fin else str(inicio))
    return ", ".join(grupos)

files = sorted(glob.glob(pattern))

if not files:
    print("⚠️ No se encontraron archivos de generaciones.")
    exit()

print(f"🔍 Analizando {len(files)} generaciones...\n")

# === Primera parte: grupos consecutivos (igual que antes)
prev_hash = None
start = 1
groups = []   # Guardará tuplas: (inicio, fin, iguales?)
hash_to_files = defaultdict(list)  # Guardará archivos por hash

for i, file in enumerate(files, 1):
    current_hash = file_hash(file)
    hash_to_files[current_hash].append(i)

    if prev_hash is None:
        prev_hash = current_hash
        start = i
    else:
        if current_hash != prev_hash:
            groups.append((start, i - 1, True)) if (i - 1) > start else groups.append((start, start, False))
            start = i
            prev_hash = current_hash

    if i == len(files):
        groups.append((start, i, True)) if i > start else groups.append((start, start, False))

# === Mostrar grupos consecutivos como antes
print("📌 Grupos consecutivos:")
for inicio, fin, iguales in groups:
    if inicio == fin:
        print(f"{inicio}")
    else:
        print(f"{inicio} - {fin} (iguales)")

# === Nueva salida agrupando por hash, con compactación
print("\n📌 Archivos iguales (sin importar el orden):")
for h, indices in hash_to_files.items():
    if len(indices) > 1:
        print(f"Grupo ({len(indices)} archivos): {compactar_indices(indices)}")
