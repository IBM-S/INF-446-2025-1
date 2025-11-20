import matplotlib.pyplot as plt
import matplotlib.patches as patches
import re
import os

def leer_datos_desde_dat(ruta_archivo):
    with open(ruta_archivo, 'r') as f:
        lineas = f.readlines()

    R = None
    coordenadas = {}

    modo_coords = False
    for linea in lineas:
        linea = linea.strip()

        if not linea or linea.startswith("/*"):
            continue

        if linea.startswith("param R"):
            match = re.search(r"param R\s*:=\s*([\d\.]+)", linea)
            if match:
                R = float(match.group(1))

        if linea.startswith("param : coordx coordy flag prob_ohca :="):
            modo_coords = True
            continue

        if modo_coords:
            if linea == ";":
                break
            partes = linea.split()
            if len(partes) == 5:
                id_, x, y, flag, _ = partes  # prob_ohca no lo usas por ahora
                coordenadas[int(id_)] = (int(x), int(y), int(flag))

    return coordenadas, R


def generar_imagen(coordenadas, radio, nombre_salida):
    fig, ax = plt.subplots(figsize=(8, 8))

    for id_, (x, y, flag) in coordenadas.items():
        if flag == 1:
            ax.plot(x, y, 'ro', label='AED' if 'AED' not in ax.get_legend_handles_labels()[1] else "")
            circle = patches.Circle((x, y), radio, color='r', alpha=0.2)
            ax.add_patch(circle)
        else:
            ax.plot(x, y, 'bo', label='OHCA' if 'OHCA' not in ax.get_legend_handles_labels()[1] else "")

    ax.set_xlabel('Coordenada X')
    ax.set_ylabel('Coordenada Y')
    ax.set_title('Distribución de OHCAs y AEDs')
    ax.legend()
    ax.grid(True)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()

    plt.savefig(nombre_salida, dpi=300)
    plt.close()
    print(f"✅ Imagen guardada: {nombre_salida}")


def procesar_todos_los_dats(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        if filename.endswith(".dat"):
            ruta_dat = os.path.join(input_folder, filename)
            nombre_salida = os.path.splitext(filename)[0] + ".jpg"
            ruta_imagen = os.path.join(output_folder, nombre_salida)

            coordenadas, radio = leer_datos_desde_dat(ruta_dat)
            generar_imagen(coordenadas, radio, ruta_imagen)

if __name__ == "__main__":
    input_folder = "casos_dats_prob"
    output_folder = "aaa"
    procesar_todos_los_dats(input_folder, output_folder)
