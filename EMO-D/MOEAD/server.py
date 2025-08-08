import os
from flask import Flask, request, jsonify, send_from_directory, send_file
import subprocess, glob
import matplotlib.pyplot as plt
import io
import re
import base64

app = Flask(__name__, static_url_path='')

@app.route("/")
def main():
    return send_from_directory(".", "main.html")

def parse_instance_name(filename):
    return os.path.splitext(os.path.basename(filename))[0]

def get_non_dominated_idx(points_xy):
    """Devuelve índices de no-dominados para lista [(x,y), ...]."""
    dominated = set()
    n = len(points_xy)
    for i in range(n):
        for j in range(n):
            if i != j:
                if (points_xy[j][0] <= points_xy[i][0] and points_xy[j][1] <= points_xy[i][1] and
                    (points_xy[j][0] < points_xy[i][0] or points_xy[j][1] < points_xy[i][1])):
                    dominated.add(i)
                    break
    return [i for i in range(n) if i not in dominated]

def save_front_to_file(points, filepath):
    """Guarda solo coords x y con comentarios # al inicio/fin (para HV)."""
    rounded = [tuple(round(v, 4) for v in p) for p in points]
    unique_points = list(dict.fromkeys(sorted(rounded, key=lambda p: (-p[1], p[0]))))
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write("#\n")
        for x, y in unique_points:
            f.write(f"{x:.4f} {y:.4f}\n")
        f.write("#\n")

def save_front_with_ids(entries, filepath):
    """
    entries: lista de tuplas (x, y, ids:list[int], is_pareto:bool)
    Guarda líneas con formato:  x y P ids...   o   x y D ids...
    Devuelve coords [(x,y)] SOLO de los pareto (para HV).
    """
    seen = {}
    for x, y, ids, is_par in entries:
        key = (round(x, 4), round(y, 4))
        if key not in seen:
            seen[key] = (x, y, list(ids or []), bool(is_par))

    ordered = sorted(seen.values(), key=lambda p: (-p[1], p[0]))
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write("#\n")
        for x, y, ids, is_par in ordered:
            flag = "P" if is_par else "D"
            tail = (" " + " ".join(map(str, ids))) if ids else ""
            f.write(f"{x:.4f} {y:.4f} {flag}{tail}\n")
        f.write("#\n")

    return [(x, y) for x, y, _, is_par in ordered if is_par]

def calculate_hv(filepath, ref_point, gen_number=None):
    cmd = ["../../material/hv-1.3-src/hv", "-r", f"{ref_point[0]} {ref_point[1]}", filepath]
    print("Ejecutando:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        hv = float(result.stdout.strip())
        if gen_number:
            print(f"Hipervolumen calculado para generación {gen_number}: {hv}")
        else:
            print("Hipervolumen calculado:", hv)
        return hv
    except ValueError:
        print("Error al interpretar la salida:", result.stdout)
        return 0.0

def calcular_referencia_global(files):
    all_points = []
    for file in files:
        with open(file) as f:
            lines = [line for line in f if line.strip() and not line.startswith("#")]
            pts = [list(map(float, line.split()[:2])) for line in lines]
            all_points.extend(pts)
    max_x = max(p[0] for p in all_points)
    max_y = max(p[1] for p in all_points)
    ref_x = max_x + abs(max_x) * 0.001
    ref_y = max_y + abs(max_y) * 0.001
    if ref_x == 0:
        ref_x = 0.1
    print(f"Punto de referencia global: ({ref_x}, {ref_y})")
    return (ref_x, ref_y)

def parse_line_with_ids(line):
    """
    Soporta:
      - 'x y - IDs instalados: 2 3 5'
      - 'x y 2 3 5'
      - 'x y P 2 3 5' o 'x y D 2 3 5' (al cargar aeds existentes)
    Retorna (x, y, ids:list[int], flag:str|None)
    """
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if "- IDs instalados:" in s:
        left, right = s.split("- IDs instalados:", 1)
        nums = left.strip().split()
        x, y = float(nums[0]), float(nums[1])
        ids = [int(tok) for tok in right.strip().split() if tok.isdigit()]
        return (x, y, ids, None)
    toks = s.split()
    x, y = float(toks[0]), float(toks[1])
    flag = None
    start = 2
    if len(toks) >= 3 and not toks[2].replace('.', '', 1).isdigit():
        if toks[2] in ("P", "D"):
            flag = toks[2]
            start = 3
    ids = []
    for tok in toks[start:]:
        try:
            ids.append(int(tok))
        except ValueError:
            pass
    return (x, y, ids, flag)

@app.route("/run", methods=["POST"])
def run():
    instancia = request.json["instancia"]
    semilla = request.json["semilla"]
    num_var = request.json["num_var"]

    full_path = os.path.join("INSTANCES", instancia)
    subprocess.run(["./MOEAD", full_path, str(semilla), str(num_var)])

    base_name = parse_instance_name(instancia)
    raw_files = sorted(glob.glob(f"SAVING/MOEAD/POF/POF_{instancia}_GEN_*.dat"))
    hv_results = []

    fp_folder = os.path.join("FrentesDePareto", base_name)
    aeds_folder = os.path.join("aeds", base_name)
    os.makedirs(fp_folder, exist_ok=True)
    os.makedirs(aeds_folder, exist_ok=True)

    ref_point = calcular_referencia_global(raw_files)
    resumen_path = os.path.join(fp_folder, f"{base_name}_HV_summary.txt")

    aed_files = []
    with open(resumen_path, "w") as resumen_file:
        resumen_file.write(f"{ref_point[0]} {ref_point[1]}\n")
        for i, file in enumerate(raw_files, start=1):
            entries_raw = []
            with open(file) as f:
                for ln in f:
                    parsed = parse_line_with_ids(ln)
                    if parsed is not None:
                        x, y, ids, _ = parsed
                        entries_raw.append((x, y, ids))  # sin flag

            if not entries_raw:
                hv_results.append(0.0)
                resumen_file.write(f"GEN{i} 0.0\n")
                continue

            nd_idx = get_non_dominated_idx([(x, y) for (x, y, _) in entries_raw])
            nd_set = set(nd_idx)

            nd_entries    = [(x, y, ids, True)  for k, (x, y, ids) in enumerate(entries_raw) if k in nd_set]
            dom_entries   = [(x, y, ids, False) for k, (x, y, ids) in enumerate(entries_raw) if k not in nd_set]

            aeds_file = os.path.join(aeds_folder, f"{base_name}_Ubicaciones_GEN{i}.dat")
            coords_for_hv = save_front_with_ids(nd_entries + dom_entries, aeds_file)
            aed_files.append(aeds_file)

            fp_file = os.path.join(fp_folder, f"{base_name}_GEN{i}.dat")
            save_front_to_file(coords_for_hv, fp_file)

            hv = calculate_hv(fp_file, ref_point, gen_number=i) or 0.0
            hv_results.append(hv)
            resumen_file.write(f"GEN{i} {hv:.4f}\n")
        resumen_file.write("#\n")

    return jsonify({"files": aed_files, "hv": hv_results})

@app.route("/load", methods=["POST"])
def load():
    instancia = request.json["instancia"]
    recalcular = request.json.get("recalcular", True)
    base_name = parse_instance_name(instancia)

    raw_files = sorted(glob.glob(f"SAVING/MOEAD/POF/POF_{instancia}_GEN_*.dat"))
    fp_folder = os.path.join("FrentesDePareto", base_name)
    aeds_folder = os.path.join("aeds", base_name)
    os.makedirs(fp_folder, exist_ok=True)
    os.makedirs(aeds_folder, exist_ok=True)

    resumen_path = os.path.join(fp_folder, f"{base_name}_HV_summary.txt")
    hv_results = []
    aed_files = sorted(glob.glob(os.path.join(aeds_folder, f"{base_name}_Ubicaciones_GEN*.dat")))

    if (not recalcular) and os.path.exists(resumen_path) and aed_files:
        with open(resumen_path) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            if len(lines) > 1:
                hv_results = [float(line.split()[1]) for line in lines[1:]]
        return jsonify({"files": aed_files, "hv": hv_results})

    ref_point = calcular_referencia_global(raw_files)
    hv_results = []
    aed_files = []

    with open(resumen_path, "w") as resumen_file:
        resumen_file.write(f"{ref_point[0]} {ref_point[1]}\n")
        for i, file in enumerate(raw_files, start=1):
            entries_raw = []
            with open(file) as f:
                for ln in f:
                    parsed = parse_line_with_ids(ln)
                    if parsed is not None:
                        x, y, ids, _ = parsed
                        entries_raw.append((x, y, ids))

            if not entries_raw:
                hv_results.append(0.0)
                resumen_file.write(f"GEN{i} 0.0\n")
                continue

            nd_idx = get_non_dominated_idx([(x, y) for (x, y, _) in entries_raw])
            nd_set = set(nd_idx)

            nd_entries  = [(x, y, ids, True)  for k, (x, y, ids) in enumerate(entries_raw) if k in nd_set]
            dom_entries = [(x, y, ids, False) for k, (x, y, ids) in enumerate(entries_raw) if k not in nd_set]

            aeds_file = os.path.join(aeds_folder, f"{base_name}_Ubicaciones_GEN{i}.dat")
            coords_for_hv = save_front_with_ids(nd_entries + dom_entries, aeds_file)
            aed_files.append(aeds_file)

            fp_file = os.path.join(fp_folder, f"{base_name}_GEN{i}.dat")
            save_front_to_file(coords_for_hv, fp_file)

            hv = calculate_hv(fp_file, ref_point, gen_number=i) or 0.0
            hv_results.append(hv)
            resumen_file.write(f"GEN{i} {hv:.4f}\n")
        resumen_file.write("#\n")

    return jsonify({"files": aed_files, "hv": hv_results})

@app.route("/get/<path:filename>")
def get_file(filename):
    return send_from_directory(".", filename)

@app.route("/map", methods=["POST"])
def generar_mapa():
    data = request.json
    try:
        instancia = data["instancia"]
        ids_instalados = [int(i) for i in data["ids"]]
    except (KeyError, ValueError, TypeError):
        return "Datos inválidos", 400

    base_name = os.path.splitext(os.path.basename(instancia))[0]
    archivo = f"INSTANCES/{instancia}"
    if not os.path.exists(archivo):
        return "Instancia no encontrada", 404

    radio_por_instancia = {
        "toy_DRP": 10, "100-3": 800, "150-11": 800,
        "SJC324-3": 800, "DRP": 10
    }
    radio = radio_por_instancia.get(base_name, 800)

    def parse_ampl_instance(filepath):
        nodes, coords = [], {}
        with open(filepath, 'r') as f:
            for line in f:
                if re.match(r'^\d+', line):
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            idx = int(parts[0])
                            x, y = float(parts[1]), float(parts[2])
                            flag = int(parts[3])
                            prob = float(parts[4])
                            nodes.append((idx, x, y, flag, prob))
                            coords[idx] = (x, y)
                        except ValueError:
                            continue
        return nodes, coords

    nodes, coords_por_id = parse_ampl_instance(archivo)
    puntos_instalados = [coords_por_id[i] for i in ids_instalados if i in coords_por_id]
    puntos_preinstalados = [(x, y) for _, x, y, f, _ in nodes if f == 1]
    puntos_totales = puntos_instalados + puntos_preinstalados

    # === Calcular métricas de cobertura ===
    demanda = [(x, y, p) for (_, x, y, f, p) in nodes if f == 0]
    total_nodos = len(demanda)
    total_prob = sum(p for _, _, p in demanda)

    r2 = radio * radio
    def cubierto(px, py):
        for (axc, ayc) in puntos_totales:
            if (px - axc)**2 + (py - ayc)**2 <= r2:
                return True
        return False

    nodos_cubiertos = sum(1 for (px, py, _) in demanda if cubierto(px, py))
    prob_cubierta = sum(p for (px, py, p) in demanda if cubierto(px, py))
    porc = (prob_cubierta / total_prob * 100.0) if total_prob > 0 else 0.0

    # Formatear IDs de estaciones manuales con salto cada 40
    ids_str_lines = []
    for i in range(0, len(ids_instalados), 40):
        chunk = ids_instalados[i:i+40]
        ids_str_lines.append(", ".join(map(str, chunk)))
    ids_formateados = "\n   ".join(ids_str_lines)  # con sangría para que se vea alineado

    resumen = (
        f"📊 {base_name}\n"
        f" - Estaciones manuales instaladas  : {str(len(ids_instalados)).ljust(4)}"
        f" - Estaciones preinstaladas        : {len(puntos_preinstalados)}\n"
        f" - IDs de estaciones manuales      : {ids_formateados}\n"
        f" - Total de nodos y probabilidad   : {str(total_nodos).ljust(4)} - {total_prob:.4f}\n"
        f" - Nodos y probabilidad cubiertos  : {str(nodos_cubiertos).ljust(4)} - {prob_cubierta:.4f} ({porc:.2f}%)"
    )

    # === Graficar ===
    fig, ax = plt.subplots(figsize=(8, 6))
    x0, y0, s0 = [], [], []
    x1, y1, s1 = [], [], []
    for _, x, y, f, p in nodes:
        if f == 0:
            x0.append(x); y0.append(y); s0.append(p * 300)
        else:
            x1.append(x); y1.append(y); s1.append(p * 300)

    xi = [x for x, y in puntos_instalados]
    yi = [y for x, y in puntos_instalados]

    ax.scatter(x0, y0, s=s0, c='blue', label='Normales', alpha=0.6, edgecolors='k')
    ax.scatter(x1, y1, s=s1, c='red',  label='Preinstalados', alpha=0.8, edgecolors='k')
    ax.scatter(xi, yi, c='green', s=200, marker='*', label='Seleccionados', edgecolors='k', zorder=5)

    for x, y in puntos_totales:
        ax.add_patch(plt.Circle((x, y), radio, color='gray', alpha=0.15, zorder=1))

    xs = [x for _, x, y, _, _ in nodes]
    ys = [y for _, x, y, _, _ in nodes]
    if xs and ys:
        pad = radio
        minx, maxx = min(xs) - pad, max(xs) + pad
        miny, maxy = min(ys) - pad, max(ys) + pad
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)

    ax.set_aspect('equal', adjustable='box')
    ax.autoscale(enable=False)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title(f"Mapa: {base_name}")
    ax.grid(True)
    ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.85), framealpha=0.95)
    plt.tight_layout(rect=[0, 0, 0.85, 1])

    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    plt.close()
    img_bytes.seek(0)

    img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')
    return jsonify({"img": img_base64, "stats": resumen})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
