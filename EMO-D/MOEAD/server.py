import os
from flask import Flask, request, jsonify, send_from_directory, send_file, abort, url_for
import subprocess, glob
import matplotlib.pyplot as plt
import io
import re
import base64
import json
from werkzeug.utils import secure_filename

def gen_number_from_path(path: str) -> int:
    """
    Extrae el número de generación desde nombres tipo:
      ...GEN_36.dat, ...GEN36.dat, ..._GEN_36.txt, etc.
    """
    base = os.path.basename(path)
    m = re.search(r'GEN[_-]?(\d+)', base)
    return int(m.group(1)) if m else 10**9  # grande si no matchea


app = Flask(__name__, static_folder="static", static_url_path="/static")

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
    """
    points: lista [(x,y)] ya filtrada (Pareto) y sin duplicados.
    Ordena por f1 asc, luego f2 asc. Escribe con alta precisión y SIN '#'.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    ordered = sorted(points, key=lambda p: (p[0], p[1]))  # f1 asc, f2 asc
    with open(filepath, "w") as f:
        for x, y in ordered:
            f.write(f"{x:.10f} {y:.10f}\n")

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
      - 'x y P 2 3 5 | 98.00' o 'x y D 2 3 5 | 75.00' (aeds existentes)
    Retorna (x, y, ids:list[int], flag:str|None, coverage:float|None)
    """
    s = line.strip()
    if not s or s.startswith("#"):
        return None

    coverage = None
    if "|" in s:
        left, right = s.split("|", 1)
        s = left.strip()
        try:
            coverage = float(right.strip().split()[0])
        except Exception:
            coverage = None

    if "- IDs instalados:" in s:
        left, right = s.split("- IDs instalados:", 1)
        nums = left.strip().split()
        x, y = float(nums[0]), float(nums[1])
        ids = [int(tok) for tok in right.strip().split() if tok.isdigit()]
        return (x, y, ids, None, coverage)

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
    return (x, y, ids, flag, coverage)

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

# --------- helpers para instancias / cobertura ----------
RADIOS = {
    "toy_DRP": 10,
    "100-3": 800,
    "150-11": 800,
    "SJC324-3": 800,
    "DRP": 10,
    "1000-88_4": 800,
    "1450-71_4": 800,
}

def cargar_instancia_coords_y_demanda(instancia_path):
    """Devuelve (nodes, coords_por_id, demanda, preinstalados, radio)
       Lee radio R desde INSTANCES/<archivo>.dat.meta.json si existe.
    """
    base_name = os.path.splitext(os.path.basename(instancia_path))[0]
    radio = RADIOS.get(base_name, 800)

    # --- lee meta si existe ---
    meta_path = instancia_path + ".meta.json"
    if os.path.exists(meta_path):
        try:
            with open(meta_path) as mf:
                meta = json.load(mf)
                radio = float(meta.get("R", radio))
        except Exception:
            pass

    nodes, coords = [], {}
    with open(instancia_path, 'r') as f:
        for line in f:
            if re.match(r'^\d+', line):
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        idx = int(parts[0])
                        x, y = float(parts[1]), float(parts[2])
                        flag = int(parts[3])    # 0 demanda, 1 preinstalado
                        prob = float(parts[4])
                        nodes.append((idx, x, y, flag, prob))
                        coords[idx] = (x, y)
                    except ValueError:
                        continue
    demanda = [(x, y, p) for (_, x, y, f, p) in nodes if f == 0]
    preinstalados = [(x, y) for (_, x, y, f, _) in nodes if f == 1]
    return nodes, coords, demanda, preinstalados, radio


def cobertura_por_ids(ids_instalados, demanda, preinstalados, radio):
    """Calcula (n_cubiertos, prob_cubierta, porc) para una lista de ids instalados."""
    puntos_instalados = ids_instalados  # coords afuera
    puntos_totales = puntos_instalados + preinstalados
    r2 = radio * radio

    def cubierto(px, py):
        for (axc, ayc) in puntos_totales:
            if (px - axc) * (px - axc) + (py - ayc) * (py - ayc) <= r2:
                return True
        return False

    total_prob = sum(p for _, _, p in demanda)
    nodos_cubiertos = 0
    prob_cubierta = 0.0
    for (px, py, p) in demanda:
        if cubierto(px, py):
            nodos_cubiertos += 1
            prob_cubierta += p
    porc = (prob_cubierta / total_prob * 100.0) if total_prob > 0 else 0.0
    return nodos_cubiertos, prob_cubierta, porc, total_prob, len(demanda)

def save_aeds_with_flags_and_coverage(entries_all, filepath):
    """
    entries_all: [(x,y, ids:list[int], is_pareto:bool, coverage:float|None)]
    Regla de desempatado por (x,y):
      1) P > D
      2) IDs lexicográficamente menores
      3) primero que llegó
    Orden de salida final: f1 asc, luego f2 asc.
    Devuelve SOLO coordenadas Pareto (ordenadas igual) para HV.
    """
    best = {}  # key=(x,y) -> (x,y,ids,is_par,cov)
    for x, y, ids, is_par, cov in entries_all:
        key = (x, y)
        cand = (x, y, list(ids or []), bool(is_par),
                float(cov) if cov is not None else None)
        if key not in best:
            best[key] = cand
        else:
            bx, by, b_ids, b_par, b_cov = best[key]
            # 1) Pareto primero
            if (not b_par) and is_par:
                best[key] = cand
            elif (b_par == is_par):
                # 2) IDs lexicográficos menores
                if tuple(ids or []) < tuple(b_ids or []):
                    best[key] = cand
                # 3) else: se queda el existente

    # ordenar por f1 asc, f2 asc
    ordered = sorted(best.values(), key=lambda p: (p[0], p[1]))

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write("#\n")
        for x, y, ids, is_par, cov in ordered:
            flag = "P" if is_par else "D"
            tail = (" " + " ".join(map(str, ids))) if ids else ""
            cov_str = f" | {cov:.4f}" if cov is not None else ""
            f.write(f"{x:.10f} {y:.10f} {flag}{tail}{cov_str}\n")
        f.write("#\n")

    # coords Pareto en el MISMO orden para el archivo de frente
    return [(x, y) for (x, y, ids, is_par, cov) in ordered if is_par]




# ------------------- /run -------------------
@app.route("/run", methods=["POST"])
def run():
    instancia = request.json["instancia"]
    semilla = request.json["semilla"]
    num_var = request.json["num_var"]

    full_path = os.path.join("INSTANCES", instancia)
    subprocess.run(["./MOEAD", full_path, str(semilla), str(num_var)])

    base_name = parse_instance_name(instancia)
    raw_files = glob.glob(f"SAVING/MOEAD/POF/POF_{instancia}_GEN_*.dat")
    raw_files = sorted(raw_files, key=gen_number_from_path)
    hv_results = []

    fp_folder = os.path.join("FrentesDePareto", base_name)
    aeds_folder = os.path.join("aeds", base_name)
    os.makedirs(fp_folder, exist_ok=True)
    os.makedirs(aeds_folder, exist_ok=True)

    # cargar instancia para cobertura
    nodes, coords_by_id, demanda, preinst_coords, radio = cargar_instancia_coords_y_demanda(os.path.join("INSTANCES", instancia))

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
                        x, y, ids, _, _ = parsed
                        entries_raw.append((x, y, ids))

            if not entries_raw:
                hv_results.append(0.0)
                resumen_file.write(f"GEN{i} 0.0\n")
                continue

            # separar P/D
            nd_idx = get_non_dominated_idx([(x, y) for (x, y, _) in entries_raw])
            nd_set = set(nd_idx)
            nd_entries  = [(x, y, ids, True)  for k, (x, y, ids) in enumerate(entries_raw) if k in nd_set]
            dom_entries = [(x, y, ids, False) for k, (x, y, ids) in enumerate(entries_raw) if k not in nd_set]

            # calcular cobertura para cada punto
            entries_all = []
            for (x, y, ids, is_par) in (nd_entries + dom_entries):
                coords_inst = [coords_by_id[i] for i in ids if i in coords_by_id]
                _, prob_cov, porc, _, _ = cobertura_por_ids(coords_inst, demanda, preinst_coords, radio)
                entries_all.append((x, y, ids, is_par, porc))

            aeds_file = os.path.join(aeds_folder, f"{base_name}_Ubicaciones_GEN{i}.dat")
            coords_for_hv = save_aeds_with_flags_and_coverage(entries_all, aeds_file)
            aed_files.append(aeds_file)

            fp_file = os.path.join(fp_folder, f"{base_name}_GEN{i}.dat")
            save_front_to_file(coords_for_hv, fp_file)

            hv = calculate_hv(fp_file, ref_point, gen_number=i) or 0.0
            hv_results.append(hv)
            resumen_file.write(f"GEN{i} {hv:.4f}\n")
        resumen_file.write("#\n")

    print("Archivos AEDs que voy a devolver al front:")
    for f in aed_files:
        print(f, os.path.exists(f))


    return jsonify({"files": aed_files, "hv": hv_results})

# ------------------- /load -------------------
@app.route("/load", methods=["POST"])
def load():
    instancia = request.json["instancia"]
    recalcular = request.json.get("recalcular", True)
    base_name = parse_instance_name(instancia)

    raw_files = glob.glob(f"SAVING/MOEAD/POF/POF_{instancia}_GEN_*.dat")
    raw_files = sorted(raw_files, key=gen_number_from_path)
    fp_folder = os.path.join("FrentesDePareto", base_name)
    aeds_folder = os.path.join("aeds", base_name)
    os.makedirs(fp_folder, exist_ok=True)
    os.makedirs(aeds_folder, exist_ok=True)

    resumen_path = os.path.join(fp_folder, f"{base_name}_HV_summary.txt")
    hv_results = []
    aed_files = glob.glob(os.path.join(aeds_folder, f"{base_name}_Ubicaciones_GEN*.dat"))
    aed_files = sorted(aed_files, key=gen_number_from_path)

    if (not recalcular) and os.path.exists(resumen_path) and aed_files:
        with open(resumen_path) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            if len(lines) > 1:
                hv_results = [float(line.split()[1]) for line in lines[1:]]
        return jsonify({"files": aed_files, "hv": hv_results})

    # recalcular y reescribir aeds/ con cobertura
    nodes, coords_by_id, demanda, preinst_coords, radio = cargar_instancia_coords_y_demanda(os.path.join("INSTANCES", instancia))

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
                        x, y, ids, _, _ = parsed
                        entries_raw.append((x, y, ids))

            if not entries_raw:
                hv_results.append(0.0)
                resumen_file.write(f"GEN{i} 0.0\n")
                continue

            nd_idx = get_non_dominated_idx([(x, y) for (x, y, _) in entries_raw])
            nd_set = set(nd_idx)
            nd_entries  = [(x, y, ids, True)  for k, (x, y, ids) in enumerate(entries_raw) if k in nd_set]
            dom_entries = [(x, y, ids, False) for k, (x, y, ids) in enumerate(entries_raw) if k not in nd_set]

            entries_all = []
            for (x, y, ids, is_par) in (nd_entries + dom_entries):
                coords_inst = [coords_by_id[i] for i in ids if i in coords_by_id]
                _, prob_cov, porc, _, _ = cobertura_por_ids(coords_inst, demanda, preinst_coords, radio)
                entries_all.append((x, y, ids, is_par, porc))

            aeds_file = os.path.join(aeds_folder, f"{base_name}_Ubicaciones_GEN{i}.dat")
            coords_for_hv = save_aeds_with_flags_and_coverage(entries_all, aeds_file)
            aed_files.append(aeds_file)

            fp_file = os.path.join(fp_folder, f"{base_name}_GEN{i}.dat")
            save_front_to_file(coords_for_hv, fp_file)

            hv = calculate_hv(fp_file, ref_point, gen_number=i) or 0.0
            hv_results.append(hv)
            resumen_file.write(f"GEN{i} {hv:.4f}\n")
        resumen_file.write("#\n")
    
    print("Archivos AEDs que voy a devolver al front:")
    for f in aed_files:
        print(f, os.path.exists(f))


    return jsonify({"files": aed_files, "hv": hv_results})

# ------------------- /map -------------------
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

    nodes, coords_por_id, demanda, preinstalados, radio = cargar_instancia_coords_y_demanda(archivo)
    puntos_instalados = [coords_por_id[i] for i in ids_instalados if i in coords_por_id]
    puntos_totales = puntos_instalados + preinstalados

    # métricas
    nodos_cubiertos, prob_cubierta, porc, total_prob, total_nodos = cobertura_por_ids(
        puntos_instalados, demanda, preinstalados, radio
    )

    # resumen formateado con IDs en líneas de 40
    ids_str_lines = []
    for i in range(0, len(ids_instalados), 30):
        chunk = ids_instalados[i:i+40]
        ids_str_lines.append(", ".join(map(str, chunk)))
    ids_formateados = ("\n   " + "\n   ".join(ids_str_lines)) if ids_str_lines else "[]"

    resumen = (
        f"📊 {base_name}\n"
        f" - Estaciones manuales instaladas  : {str(len(ids_instalados)).ljust(4)} - Estaciones preinstaladas        : {len(preinstalados)}\n"
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

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

@app.route("/get/<path:filename>")
def get_file(filename):
    # Normaliza y evita salirte del proyecto
    safe_path = os.path.normpath(filename).lstrip(os.sep)
    full_path = os.path.join(BASE_DIR, safe_path)

    # Log para depurar
    # print("[/get] filename:", filename, flush=True)
    # print("[/get] full_path:", full_path, flush=True)
    # print("[/get] exists?:", os.path.exists(full_path), flush=True)

    if not os.path.exists(full_path):
        # Dilo fuerte para que aparezca en consola
        print(f"[/get] 404 -> NO existe: {full_path}", flush=True)
        abort(404)

    return send_file(full_path)

ALLOWED_IMG = {"png", "jpg", "jpeg", "webp"}

def allowed_img(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMG

@app.route("/upload_map", methods=["POST"])
def upload_map():
    """
    Recibe multipart/form-data con 'image' y opcional 'name'.
    Guarda en static/maps/ y devuelve la URL servible /static/maps/<archivo>.
    """
    if "image" not in request.files:
        return jsonify({"error": "No se envió archivo 'image'"}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Archivo vacío"}), 400
    if not allowed_img(file.filename):
        return jsonify({"error": "Formato no permitido"}), 400

    raw_name = request.form.get("name", os.path.splitext(file.filename)[0])
    fname = secure_filename(raw_name) or "map"
    ext = os.path.splitext(file.filename)[1].lower()

    os.makedirs(os.path.join("static", "maps"), exist_ok=True)
    out_path = os.path.join("static", "maps", fname + ext)
    file.save(out_path)

    url = url_for('static', filename=f"maps/{fname}{ext}", _external=False)
    return jsonify({"url": url}), 200

@app.route("/save_instance", methods=["POST"])
def save_instance():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON inválido"}), 400

    name = (data.get("name") or "").strip()
    points = data.get("points", [])
    if not name:
        return jsonify({"error": "Falta 'name'"}), 400
    if not isinstance(points, list) or not points:
        return jsonify({"error": "Faltan 'points'"}), 400
    if not name.endswith(".dat"):
        name += ".dat"

    # Parámetros adicionales
    P = float(data.get("presupuesto", 0))
    R = float(data.get("radio", 800))
    c1 = float(data.get("c1", 1))
    c2 = float(data.get("c2", 1))
    nombre_instancia = name

    # Ordenar por ID
    rows = []
    for p in points:
        pid = int(p["id"])
        x = float(p["x"])
        y = float(p["y"])
        flag = int(p.get("flag", 0))
        prob = float(p.get("prob", 1.0)) or 1.0
        rows.append((pid, x, y, flag, prob))
    rows.sort(key=lambda r: r[0])

    N = len(rows)

    os.makedirs("INSTANCES", exist_ok=True)
    dat_path = os.path.join("INSTANCES", name)

    with open(dat_path, "w") as f:
        # Cabecera
        f.write("/* CONJUNTOS */\n\n")
        f.write(f"set N:= {N} ;\n\n")
        f.write("/* PARAMETROS */\n\n")
        f.write(f"param P:= {P} ;\n\n")
        f.write(f"param R:= {R} ;\n\n")
        f.write(f"param c1:= {c1} ;\n\n")
        f.write(f"param c2:= {c2} ;\n\n")
        f.write(f'param nombre_instancia := "{nombre_instancia}" ;\n\n')

        # Coordenadas y parámetros
        f.write("param : coordx coordy flag prob_ohca:=\n")
        for (pid, x, y, flag, prob) in rows:
            f.write(f"{pid} {x:.6f} {y:.6f} {flag} {prob:.2f}\n")
        f.write(";\n")

    return jsonify({"ok": True, "path": dat_path, "filename": name}), 200


@app.route("/list_instances", methods=["GET"])
def list_instances():
    files = []
    os.makedirs("INSTANCES", exist_ok=True)
    for fn in sorted(os.listdir("INSTANCES")):
        if fn.lower().endswith(".dat"):
            files.append(fn)
    return jsonify({"instances": files})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
