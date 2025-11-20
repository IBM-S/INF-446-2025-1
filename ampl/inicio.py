import matplotlib.pyplot as plt
import matplotlib.patches as patches
import re
import os

def leer_dat(ruta_dat):
    with open(ruta_dat, 'r') as f:
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

        if linea.startswith("param : coordx coordy flag :="):
            modo_coords = True
            continue

        if modo_coords:
            if linea == ";":
                break
            partes = linea.split()
            if len(partes) == 4:
                id_, x, y, flag = partes
                coordenadas[int(id_)] = (int(x), int(y), int(flag))

    return R, coordenadas

def graficar_desde_dat(ruta_dat, ruta_salida_img):
    R, coords = leer_dat(ruta_dat)

    fig, ax = plt.subplots(figsize=(8, 8))

    for id_, (x, y, flag) in coords.items():
        if flag == 1:
            ax.plot(x, y, 'ro', label='AED' if 'AED' not in ax.get_legend_handles_labels()[1] else "")
            circle = patches.Circle((x, y), R, color='r', alpha=0.2)
            ax.add_patch(circle)
            #ax.text(x + 1, y + 1, str(id_), fontsize=8, color='red')
        else:
            ax.plot(x, y, 'bo', label='OHCA' if 'OHCA' not in ax.get_legend_handles_labels()[1] else "")
            #ax.text(x + 1, y + 1, str(id_), fontsize=8, color='blue')

    ax.set_xlabel('Coordenada X')
    ax.set_ylabel('Coordenada Y')
    ax.set_title(f"Instancia: {os.path.basename(ruta_dat)}")
    ax.legend()
    ax.grid(True)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()
    plt.savefig(ruta_salida_img, dpi=300)
    plt.close()
    print(f"✅ Gráfico guardado: {ruta_salida_img}")

def procesar_carpeta(carpeta_entrada, carpeta_salida):
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)

    archivos = [f for f in os.listdir(carpeta_entrada) if f.endswith(".dat")]

    for archivo in archivos:
        ruta_dat = os.path.join(carpeta_entrada, archivo)
        nombre_salida = os.path.splitext(archivo)[0] + ".png"
        ruta_salida = os.path.join(carpeta_salida, nombre_salida)
        graficar_desde_dat(ruta_dat, ruta_salida)

# Ejecutar
if __name__ == "__main__":
    procesar_carpeta("casos_dats_prob", "graficos_iniciales_sin_numeros")
