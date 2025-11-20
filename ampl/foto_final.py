import matplotlib.pyplot as plt
import matplotlib.patches as patches
import re

def parsear_resultados(ruta_resultado):
    with open(ruta_resultado, 'r') as f:
        contenido = f.read()

    # Extraer nombre del archivo .dat
    match_dat = re.search(r"Ejecutando el caso de prueba: (.+\.dat)", contenido)
    nombre_dat = match_dat.group(1) if match_dat else None

    # Extraer valor de R
    match_r = re.search(r"R:\s*(\d+)", contenido)
    radio = int(match_r.group(1)) if match_r else 10  # Por defecto 10 si no se encuentra

    # Buscar todos los sitios con AED
    sitios_aeds = set()
    mantenidos = re.findall(r"Se Mantiene un desfibrilador en el sitio (\d+)", contenido)
    sitios_aeds.update(map(int, mantenidos))

    movidos = re.findall(r"Se desplazo un desfibrilador del sitio \d+ al (\d+)", contenido)
    sitios_aeds.update(map(int, movidos))

    instalados = re.findall(r"Se instala un desfibrilador en el sitio (\d+)", contenido)
    sitios_aeds.update(map(int, instalados))

    # Extraer coordenadas
    coord_lines = contenido.split("----------- COORDENADAS X,Y ------------")[-1].strip().splitlines()
    coordenadas = {}
    for linea in coord_lines:
        partes = linea.strip().split()
        if len(partes) == 3:
            sitio, x, y = map(int, partes)
            coordenadas[sitio] = (x, y)

    return nombre_dat, sitios_aeds, coordenadas, radio

def graficar(nombre_dat, sitios_aeds, coordenadas, radio, nombre_salida="toy_toy.png"):
    fig, ax = plt.subplots(figsize=(8, 8))

    for sitio, (x, y) in coordenadas.items():
        if sitio in sitios_aeds:
            ax.plot(x, y, 'ro', label='AED' if 'AED' not in ax.get_legend_handles_labels()[1] else "")
            circle = patches.Circle((x, y), radio, color='r', alpha=0.2)
            ax.add_patch(circle)
            ax.text(x + 1, y + 1, f'{sitio}', fontsize=8, color='red')
        else:
            ax.plot(x, y, 'bo', label='OHCA' if 'OHCA' not in ax.get_legend_handles_labels()[1] else "")
            ax.text(x + 1, y + 1, f'{sitio}', fontsize=8, color='blue')

    ax.set_xlabel('Coordenada X')
    ax.set_ylabel('Coordenada Y')
    ax.set_title(f'Distribución de AEDs según {nombre_dat} (R={radio})')
    ax.legend()
    ax.grid(True)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()
    plt.savefig(nombre_salida, dpi=300)
    plt.close()
    print(f"✅ Imagen guardada como {nombre_salida}")

# Ejecutar
if __name__ == "__main__":
    archivo_resultado = "resultados_gurobi/res_toy_drp_b.txt"  # ← Actualiza con tu ruta real
    nombre_dat, sitios_aeds, coordenadas, radio = parsear_resultados(archivo_resultado)
    graficar(nombre_dat, sitios_aeds, coordenadas, radio, "toy_drp_punto_b.png")
