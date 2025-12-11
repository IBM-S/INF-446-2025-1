#!/usr/bin/env python3
import os
import re
import glob
import math

# ==============================
# Rutas
# ==============================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DIR_INSTANCES = os.path.join(BASE_DIR, "..", "datos", "inst")

RE_FLOAT = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'
PAT_R = re.compile(r'param\s+R\s*:=\s*(' + RE_FLOAT + r')')
PAT_LINEA_NODO = re.compile(r'^\s*\d+\s')


def leer_nodos_y_R(path_dat):
    """
    Lee un archivo .dat del DRP y devuelve:
      - nodos: lista de (id, x, y, flag, prob)
      - R: radio de cobertura (float)
    """
    nodos = []
    R = None

    with open(path_dat, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Buscar param R := ...
            mR = PAT_R.search(line)
            if mR:
                try:
                    R = float(mR.group(1))
                except ValueError:
                    pass

            # Líneas de nodos: empiezan con un entero (id)
            if PAT_LINEA_NODO.match(line):
                partes = line.split()
                if len(partes) < 5:
                    continue
                try:
                    idx = int(partes[0])
                    x = float(partes[1])
                    y = float(partes[2])
                    flag = int(partes[3])
                    prob = float(partes[4])
                    nodos.append((idx, x, y, flag, prob))
                except ValueError:
                    continue

    if R is None:
        raise ValueError(f"No se encontró 'param R:=' en {path_dat}")

    return nodos, R


def calcular_cobertura_geometrica(nodos, R):
    """
    nodos: lista de (id, x, y, flag, prob)
    R: radio de cobertura

    AEDs = nodos con flag = 1
    Demanda = nodos con flag = 0

    Devuelve diccionario con:
      - n_cubiertos       : cuántos nodos de demanda están cubiertos
      - prob_cubierta     : suma de prob de nodos de demanda cubiertos
      - n_demanda_total   : cuántos nodos de demanda hay en total
      - prob_demanda_total: suma de prob de todos los nodos de demanda
    """
    # Separar AEDs y demanda
    aeds = []
    demanda = []
    for (idx, x, y, flag, prob) in nodos:
        if flag == 1:
            aeds.append((x, y))
        elif flag == 0:
            demanda.append((x, y, prob))

    R2 = R * R

    n_cubiertos = 0
    prob_cubierta = 0.0
    n_demanda_total = len(demanda)
    prob_demanda_total = sum(p for (_, _, p) in demanda)

    # Para cada nodo de demanda, revisar si está dentro de R de algún AED
    for (px, py, prob) in demanda:
        cubierto = False
        for (ax, ay) in aeds:
            dx = px - ax
            dy = py - ay
            if dx * dx + dy * dy <= R2:
                cubierto = True
                break

        if cubierto:
            n_cubiertos += 1
            prob_cubierta += prob

    return {
        "n_cubiertos": n_cubiertos,
        "prob_cubierta": prob_cubierta,
        "n_demanda_total": n_demanda_total,
        "prob_demanda_total": prob_demanda_total,
    }


def procesar_instancia(path_dat, mode="normal"):
    nodos, R = leer_nodos_y_R(path_dat)
    stats = calcular_cobertura_geometrica(nodos, R)
    base = os.path.basename(path_dat)
    nombre_instancia = os.path.splitext(base)[0]

    prob_cubierta = stats["prob_cubierta"]
    n_demanda_total = stats["n_demanda_total"]

    if mode == "ref":
        # MODO REFERENCIA:
        # {instancia} {(prob demanda cubierta * -1) + (prob demanda cubierta*0.1)} {Nodos demanda total*1.1}
        ref_x = (-0.99 * prob_cubierta)   # = -0.9 * prob_cubierta
        ref_y = n_demanda_total * 1.005

        print(f"{nombre_instancia} {ref_x:.6f} {ref_y:.6f}")
        return

    # --------- MODO NORMAL (RESUMEN COMPLETO) ----------
    print(f"Instancia: {base}")
    print(f"  R = {R}")
    print(f"  AEDs (flag = 1)            : {sum(1 for (_,_,_,f,_) in nodos if f == 1)}")
    print(f"  Nodos demanda totales      : {stats['n_demanda_total']}")
    print(f"  Prob demanda total         : {stats['prob_demanda_total']:.4f}")
    print(f"  Nodos demanda cubiertos    : {stats['n_cubiertos']}")
    print(f"  Prob demanda cubierta      : {stats['prob_cubierta']:.4f}")
    
    nodos_no_cubiertos = stats['n_demanda_total'] - stats['n_cubiertos']
    prob_no_cubierta = stats['prob_demanda_total'] - stats['prob_cubierta']

    print(f"  Nodos demanda NO cubiertos : {nodos_no_cubiertos}")
    print(f"  Prob demanda NO cubierta   : {prob_no_cubierta:.4f}")

    if stats['n_demanda_total'] > 0:
        porc_nodos = 100.0 * stats['n_cubiertos'] / stats['n_demanda_total']
        porc_prob = 100.0 * stats['prob_cubierta'] / stats['prob_demanda_total']
        print(f"  % de nodos cubiertos       : {porc_nodos:.2f}%")
        print(f"  % de probabilidad cubierta : {porc_prob:.2f}%")
    print()

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Calcula la cobertura geométrica actual en instancias DRP (.dat)."
    )
    parser.add_argument(
        "instancia",
        nargs="?",
        help="Nombre de archivo .dat dentro de datos/inst. "
             "Si se omite, se procesan todas las instancias.",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["normal", "ref"],
        default="normal",
        help="Formato de salida: 'normal' (resumen) o 'ref' (instancia ref_x ref_y)."
    )
    args = parser.parse_args()

    if args.instancia:
        path = os.path.join(DIR_INSTANCES, args.instancia)
        if not os.path.exists(path):
            print(f"No existe el archivo: {path}")
            return
        procesar_instancia(path, mode=args.mode)
    else:
        # procesar todas las .dat
        patrones = glob.glob(os.path.join(DIR_INSTANCES, "*.dat"))
        if not patrones:
            print(f"No se encontraron .dat en {DIR_INSTANCES}")
            return
        for path in sorted(patrones):
            procesar_instancia(path, mode=args.mode)


if __name__ == "__main__":
    main()
