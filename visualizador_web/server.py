import os
import glob
import subprocess
import re
import json
import shutil
import random
import time
import base64
import io
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, send_file, abort, url_for
from werkzeug.utils import secure_filename
import matplotlib.pyplot as plt

# ==============================================================================
# CONFIGURACIÓN Y RUTAS
# ==============================================================================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROYECTO_ROOT = os.path.join(BASE_DIR, "..")

DIR_DATOS = os.path.join(PROYECTO_ROOT, "datos")
DIR_INSTANCES = os.path.join(DIR_DATOS, "inst")
DIR_RESULTADOS = os.path.join(DIR_DATOS, "res")

DIR_RAW_MOEAD = os.path.join(DIR_RESULTADOS, "raw_moead/cam") 
DIR_RAW_AMPL = os.path.join(DIR_RESULTADOS, "raw_ampl/cam") 

DIR_FRENTES_PARETO = os.path.join(DIR_RESULTADOS, "cache_procesada", "frentes_pareto")
DIR_AEDS_PROCESADOS = os.path.join(DIR_RESULTADOS, "cache_procesada", "aeds")
DIR_RUN_STATS = os.path.join(DIR_RESULTADOS, "cache_procesada", "run_stats")
DIR_STATIC_MAPS = os.path.join(BASE_DIR, "static", "maps")

DIR_MOEAD_CORE = os.path.join(PROYECTO_ROOT, "solver_moead")
PATH_MOEAD_EXEC = os.path.join(DIR_MOEAD_CORE, "MOEAD")
PATH_HV_EXEC = os.path.join(PROYECTO_ROOT, "material", "hv-1.3-src", "hv")
OPTIMOS_PATH = os.path.join(PROYECTO_ROOT, "Tuning/optimos.txt")

OPTIMOS_CACHE = None
ALLOWED_IMG = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__, static_folder="static", static_url_path="/static")

# ==============================================================================
# HELPERS GENÉRICOS
# ==============================================================================
def get_compare_dir(instance_name: str) -> str:
    """
    Devuelve la carpeta TT2/datos/res/raw_moead/cam/{instancia}/comparacion
    y la crea si no existe.
    instance_name puede venir con o sin .dat.
    """
    base = parse_instance_name(instance_name)
    inst_dir = os.path.join(DIR_RAW_MOEAD, base, "comparacion")
    os.makedirs(inst_dir, exist_ok=True)
    return inst_dir

def save_compare_result(instance_name: str, compare_dir: str, result: dict):
    """
    Guarda el resultado de compare_all en un JSONL dentro de comparacion/.
    Así luego se puede recuperar con /compare_load sin volver a ejecutar nada.
    """
    path = os.path.join(compare_dir, "compare_results.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def load_last_compare_result(compare_dir: str):
    """
    Lee la última línea de compare_results.jsonl y la devuelve como dict.
    Si no existe o está vacío, devuelve None.
    """
    path = os.path.join(compare_dir, "compare_results.jsonl")
    if not os.path.exists(path):
        return None
    last = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            last = line
    if last is None:
        return None
    try:
        return json.loads(last)
    except Exception:
        return None


def gen_number_from_path(path: str) -> int:
    m = re.search(r'GEN[_-]?(\d+)', os.path.basename(path))
    return int(m.group(1)) if m else 10**9

def parse_instance_name(filename):
    """
    Obtiene el nombre de la instancia eliminando la ruta y el sufijo '.dat'.
    Usa os.path.basename para quitar la ruta y str.removesuffix() para quitar la extensión.
    """
    # 1. Obtener el nombre base del archivo (ej. 'cam_24523_GUSTAVO_A._MADERO.dat')
    basename = os.path.basename(filename)
    
    # 2. Quitar el sufijo conocido '.dat'. Esto mantiene todos los puntos intermedios.
    name_without_dat = basename.removesuffix(".dat")
    
    return name_without_dat

def append_jsonl(path: str, obj: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load_optimos():
    global OPTIMOS_CACHE
    if OPTIMOS_CACHE is not None: return OPTIMOS_CACHE
    d = {}
    if os.path.exists(OPTIMOS_PATH):
        with open(OPTIMOS_PATH, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4 and not line.startswith("#"):
                    try:
                        key = parse_instance_name(parts[0])
                        d[key] = {"hv_opt": float(parts[1]), "ref": (float(parts[2]), float(parts[3]))}
                    except ValueError: pass
    OPTIMOS_CACHE = d
    return d

def get_non_dominated_idx(points_xy):
    n = len(points_xy)
    dominated = set()
    for i in range(n):
        for j in range(n):
            if i != j:
                px, py = points_xy[i]; qx, qy = points_xy[j]
                if (qx <= px and qy <= py) and (qx < px or qy < py):
                    dominated.add(i)
                    break
    return [i for i in range(n) if i not in dominated]

def save_front_to_file(points, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        for x, y in sorted(points, key=lambda p: (p[0], p[1])):
            f.write(f"{x:.10f} {y:.10f}\n")

def calcular_referencia_global(files):
    max_x, max_y = -float('inf'), -float('inf')
    found = False
    for file in files:
        with open(file) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    try:
                        x, y = map(float, line.split()[:2])
                        max_x, max_y = max(max_x, x), max(max_y, y)
                        found = True
                    except: pass
    if not found: return (1.0, 1.0)
    ref_x = max_x + abs(max_x) * 0.001
    ref_y = max_y + abs(max_y) * 0.001
    return (ref_x if ref_x != 0 else 0.1, ref_y if ref_y != 0 else 0.1)

def get_time_from_log(path, header_key, sep=",", skip_first=True):
    if not os.path.exists(path): return None
    tiempos = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines: return None
        
        idx = -1
        if header_key:
            header = lines[0].split(sep)
            if header_key in header: idx = header.index(header_key)
        else:
            idx = 1 # Default index for AMPL log

        if idx == -1: return None
        
        start = 1 if skip_first else 0
        for row in lines[start:]:
            cols = row.split(sep)
            if len(cols) > idx:
                try: tiempos.append(float(cols[idx]))
                except ValueError: pass
    except: return None
    return sum(tiempos)/len(tiempos) if tiempos else None

def get_moead_time(base_name):
    d = os.path.join(DIR_RAW_MOEAD, base_name)
    if not os.path.isdir(d): return None
    # Busca el primer execution log válido
    for p in glob.glob(os.path.join(d, "execution_*")):
        t = get_time_from_log(p, "Time_s")
        if t is not None: return t
    return None

def get_ampl_time(base_name):
    return get_time_from_log(os.path.join(DIR_RAW_AMPL, base_name, f"execution_{base_name}_summary.log"), None)

def get_first_last_front_in_dir(compare_dir: str):
    """
    Dado un directorio TT2/datos/res/raw_moead/cam/{instancia}/comparacion,
    devuelve las rutas al primer y último frente encontrados, ordenados por GEN.

    Retorna: (first_front_path, last_front_path) o (None, None) si no hay archivos válidos.
    """
    if not os.path.isdir(compare_dir):
        return None, None

    # Todos los .dat que tengan "GEN" en el nombre
    pattern = os.path.join(compare_dir, "*.dat")
    files = [p for p in glob.glob(pattern) if "GEN" in os.path.basename(p)]
    if not files:
        return None, None

    files_sorted = sorted(files, key=gen_number_from_path)
    return files_sorted[0], files_sorted[-1]

def get_ampl_stats_for_instance(base_name: str):
    """
    Devuelve información básica de AMPL para una instancia:

      base_name: nombre sin extensión (.dat), por ejemplo 'cam_1390_MILPA_ALTA'

    Retorna:
      (ampl_front_file, t_ampl_s)

      - ampl_front_file: ruta al pareto_front.txt de AMPL o None si no se encuentra.
      - t_ampl_s       : tiempo promedio de AMPL (float) leído del summary, o None.
    """
    inst_name = base_name.replace(".dat", "")

    # Candidatos típicos
    candidates = [
        os.path.join(DIR_RAW_AMPL, inst_name, "run_1", "pareto_front.txt"),
        os.path.join(DIR_RAW_AMPL, inst_name, "pareto_front.txt"),
    ]

    ampl_front = None
    for p in candidates:
        if os.path.exists(p):
            ampl_front = p
            break

    # Fallback: buscar en subcarpetas por si cambia la estructura
    if ampl_front is None:
        pattern = os.path.join(DIR_RAW_AMPL, inst_name, "**", "pareto_front.txt")
        matches = glob.glob(pattern, recursive=True)
        if matches:
            ampl_front = matches[0]

    # Tiempo AMPL (ya tienes get_ampl_time definido usando el summary)
    t_ampl = get_ampl_time(inst_name)

    return ampl_front, t_ampl


def read_all_inst_list():
    candidates = [
        os.path.join(DIR_INSTANCES, "All.inst"),
        os.path.join(PROYECTO_ROOT, "All.inst"),
        os.path.join(BASE_DIR, "All.inst"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)

    insts = []
    if path:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or s.startswith("//"):
                    continue
                tok = s.split()[0].strip().strip('"').strip("'")
                if not tok.endswith(".dat"):
                    tok += ".dat"
                insts.append(os.path.basename(tok))

    if not insts:
        insts = [f for f in os.listdir(DIR_INSTANCES) if f.endswith(".dat")]

    return [n for n in sorted(set(insts)) if os.path.exists(os.path.join(DIR_INSTANCES, n))]


def find_ampl_front_file(base_name: str):
    base_dir = os.path.join(DIR_RAW_AMPL, base_name)
    if not os.path.isdir(base_dir):
        return None

    p1 = os.path.join(base_dir, "run_1", "pareto_front.txt")
    if os.path.exists(p1):
        return p1

    runs = sorted(glob.glob(os.path.join(base_dir, "run_*", "pareto_front.txt")))
    if runs:
        return runs[0]

    p2 = os.path.join(base_dir, "pareto_front.txt")
    return p2 if os.path.exists(p2) else None


def parse_line_with_ids(line):
    s = line.strip()
    if not s or s.startswith("#"): return None
    cov = None
    if "|" in s:
        s, r = s.split("|", 1)
        try: cov = float(r.strip().split()[0])
        except: pass
    
    parts = s.split("- IDs instalados:", 1)
    if len(parts) == 2:
        nums = parts[0].split()
        ids = [int(x) for x in parts[1].split() if x.isdigit()]
        return (float(nums[0]), float(nums[1]), ids, None, cov)
    
    toks = s.split()
    if len(toks) < 2: return None
    x, y = float(toks[0]), float(toks[1])
    flag = None
    idx = 2
    if len(toks) > 2 and toks[2] in ("P", "D"):
        flag, idx = toks[2], 3
    ids = [int(x) for x in toks[idx:] if x.isdigit()]
    return (x, y, ids, flag, cov)

def build_front_file_for_hv(filepath: str) -> str | None:
    """
    Dado un frente (por ejemplo un POF_cam_...GEN_9.dat con IDs instalados),
    crea un archivo limpio con solo las 2 primeras columnas numéricas,
    que es el formato que espera el binario hv.

    Devuelve la ruta al archivo limpio (mismo directorio, sufijo _HV.dat)
    o None si no se pudo extraer ningún punto válido.
    """
    filepath = os.path.abspath(filepath)
    base, ext = os.path.splitext(os.path.basename(filepath))
    dir_ = os.path.dirname(filepath)

    clean_path = os.path.join(dir_, base + "_HV.dat")

    n_valid = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fin, \
             open(clean_path, "w", encoding="utf-8") as fout:

            for line in fin:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                try:
                    x = float(parts[0])
                    y = float(parts[1])
                except ValueError:
                    # si las primeras columnas tampoco son numéricas, saltamos la línea
                    continue

                fout.write(f"{x} {y}\n")
                n_valid += 1

    except Exception as e:
        print(f"[HV] Error construyendo archivo limpio para {filepath}: {e}")
        return None

    if n_valid == 0:
        print(f"[HV] Advertencia: no se encontraron puntos válidos en {filepath}")
        return None

    print(f"[HV] Archivo limpio generado: {clean_path} ({n_valid} puntos)")
    return clean_path


def calculate_hv(filepath, ref_point, gen_number=None):
    """
    Calcula el hipervolumen llamando al binario externo hv.
    1) Construye un archivo 'limpio' con solo las 2 primeras columnas numéricas.
    2) Llama a hv sobre ese archivo.
    Si algo sale mal, retorna None.
    """
    # 1) Crear archivo limpio compatible con hv
    clean_path = build_front_file_for_hv(filepath)
    if clean_path is None:
        print(f"[HV] No se pudo generar archivo limpio para {filepath}, HV=None")
        return None

    hv_exec_rel = os.path.relpath(PATH_HV_EXEC, BASE_DIR)
    front_rel   = os.path.relpath(clean_path, BASE_DIR)
    cmd = [hv_exec_rel, "-r", f"{ref_point[0]} {ref_point[1]}", front_rel]

    print(f"[HV] Ejecutando: {' '.join(cmd)} (cwd={BASE_DIR})")

    try:
        # Capturamos bytes y decodificamos a mano, para evitar UnicodeDecodeError
        res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True)
    except Exception as e:
        print(f"[HV] ERROR al ejecutar hv: {e}")
        return None

    stdout = (res.stdout or b"").decode("utf-8", errors="ignore").strip()
    stderr = (res.stderr or b"").decode("utf-8", errors="ignore").strip()

    if res.returncode != 0:
        print(f"[HV] ERROR: returncode={res.returncode}")
        if stderr:
            print(f"[HV] stderr: {stderr}")
        return None

    print(f"[HV] stdout crudo: '{stdout}'")

    if not stdout:
        print(f"[HV] Advertencia: stdout vacío para {clean_path}")
        return None

    try:
        resultado_hv = float(stdout)
    except ValueError:
        print(f"[HV] Advertencia: no pude parsear HV desde '{stdout}' para {clean_path}")
        if stderr:
            print(f"[HV] stderr asociado: {stderr}")
        return None

    nombre = filepath.strip().split("/")[-1]
    if gen_number is not None:
        print(f"[HV] {nombre} (GEN {gen_number}) -> HV = {resultado_hv}")
    else:
        print(f"[HV] {nombre} -> HV = {resultado_hv}")

    return resultado_hv


def cargar_instancia_coords_y_demanda(path):
    radio = 800.0
    try:
        with open(path, 'r') as f: txt = f.read()
        m = re.search(r'param\s+R\s*:=\s*([-+]?\d*\.?\d+)', txt)
        if m: radio = float(m.group(1))
    except: pass
    
    nodes, coords = [], {}
    with open(path, 'r') as f:
        for line in f:
            if line[0].isdigit():
                p = line.split()
                if len(p) >= 5:
                    idx = int(p[0])
                    nodes.append((idx, float(p[1]), float(p[2]), int(p[3]), float(p[4])))
                    coords[idx] = (float(p[1]), float(p[2]))
    demanda = [(x,y,p) for _,x,y,f,p in nodes if f==0]
    pre = [(x,y) for _,x,y,f,_ in nodes if f==1]
    return nodes, coords, demanda, pre, radio

def cobertura_por_ids(ids, demanda, pre, radio):
    if not ids and not pre: return 0, 0.0, 0.0, sum(d[2] for d in demanda), len(demanda)
    r2 = radio**2
    pts = [ids[i] for i in range(len(ids))] + pre # asume ids son coords ya procesadas afuera o pasar coords
    # Nota: la función original recibía coords en 'ids'. Ajustado en el caller.
    cubiertos, prob_cov = 0, 0.0
    for px, py, p in demanda:
        for cx, cy in pts:
            if (px-cx)**2 + (py-cy)**2 <= r2:
                cubiertos += 1; prob_cov += p; break
    tot_p = sum(d[2] for d in demanda)
    return cubiertos, prob_cov, (prob_cov/tot_p*100 if tot_p>0 else 0), tot_p, len(demanda)

def save_aeds_with_flags_and_coverage(entries, filepath):
    # Desempatar y ordenar
    best = {}
    for x, y, ids, par, cov in entries:
        k = (x, y)
        val = (x, y, ids or [], par, cov)
        if k not in best: best[k] = val
        else:
            curr = best[k]
            if (not curr[3] and par) or (curr[3] == par and tuple(ids or []) < tuple(curr[2])):
                best[k] = val
    
    ordered = sorted(best.values(), key=lambda v: (v[0], v[1]))
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write("#\n")
        for x, y, ids, par, cov in ordered:
            flag = "P" if par else "D"
            tail = (" " + " ".join(map(str, ids))) if ids else ""
            c_str = f" | {cov:.4f}" if cov is not None else ""
            f.write(f"{x:.10f} {y:.10f} {flag}{tail}{c_str}\n")
        f.write("#\n")
    return [(x,y) for x,y,_,par,_ in ordered if par]

# ==============================================================================
# LÓGICA CENTRAL DE PROCESAMIENTO (REFACTORIZADA)
# ==============================================================================
def core_process_results(instancia, raw_files, hv_every):
    base_name = parse_instance_name(instancia)
    fp_folder = os.path.join(DIR_FRENTES_PARETO, base_name)
    aeds_folder = os.path.join(DIR_AEDS_PROCESADOS, base_name)
    resumen_path = os.path.join(fp_folder, f"{base_name}_HV_summary.txt")

    # Limpieza
    if os.path.exists(fp_folder): shutil.rmtree(fp_folder)
    if os.path.exists(aeds_folder): shutil.rmtree(aeds_folder)
    os.makedirs(fp_folder, exist_ok=True)
    os.makedirs(aeds_folder, exist_ok=True)

    # Cargar datos instancia
    nodes, coords_map, demanda, pre_coords, radio = cargar_instancia_coords_y_demanda(os.path.join(DIR_INSTANCES, instancia))
    
    # Referencia HV
    opt = load_optimos().get(base_name)
    ref_point = opt["ref"] if opt else calcular_referencia_global(raw_files)
    hv_opt = opt["hv_opt"] if opt else None

    hv_results = []
    aed_files_out = []
    gen_numbers = []
    last_hv = 0.0
    n_gens = len(raw_files)

    with open(resumen_path, "w") as f_res:
        header = f"{ref_point[0]} {ref_point[1]}"
        if hv_opt: header += f" {hv_opt}"
        f_res.write(header + "\n")

        for i, f_path in enumerate(raw_files):
            gen = gen_number_from_path(f_path)
            gen_numbers.append(gen)
            
            # Filtro de generaciones
            is_edge = (i == 0 or i == n_gens - 1)
            should_calc = is_edge or (hv_every > 0 and gen % hv_every == 0)

            if not should_calc:
                hv_results.append(last_hv)
                continue

            # Parsear
            raw_pts = []
            with open(f_path) as f:
                for ln in f:
                    p = parse_line_with_ids(ln)
                    if p: raw_pts.append(p)
            
            if not raw_pts:
                hv_results.append(last_hv)
                if should_calc: f_res.write(f"GEN{gen} {last_hv:.4f}\n")
                continue

            # Pareto
            pts_xy = [(r[0], r[1]) for r in raw_pts]
            t0 = time.perf_counter()
            nd_idx = set(get_non_dominated_idx(pts_xy))
            t1 = time.perf_counter()
            
            entries = []
            for k, (x, y, ids, _, _) in enumerate(raw_pts):
                is_par = k in nd_idx
                # Cobertura
                c_coords = [coords_map[mid] for mid in ids if mid in coords_map]
                _, _, porc, _, _ = cobertura_por_ids(c_coords, demanda, pre_coords, radio)
                entries.append((x, y, ids, is_par, porc))

            t2 = time.perf_counter()

            # Guardar AEDs
            aed_path = os.path.join(aeds_folder, f"{base_name}_Ubicaciones_GEN{gen}.dat")
            hv_pts = save_aeds_with_flags_and_coverage(entries, aed_path)
            aed_files_out.append(aed_path)

            # Calcular HV
            fp_path = os.path.join(fp_folder, f"{base_name}_GEN{gen}.dat")
            save_front_to_file(hv_pts, fp_path)
            t3 = time.perf_counter()
            hv = calculate_hv(fp_path, ref_point, gen)
            t4 = time.perf_counter()
            print(f"[GEN {gen}] ND={t1-t0:.4f}s  "
                f"cobertura={t2-t1:.4f}s  "
                f"write_fp={t3-t2:.4f}s  "
                f"hv={t4-t3:.4f}s")
            last_hv = hv
            hv_results.append(hv)
            f_res.write(f"GEN{gen} {hv:.4f}\n")
        
        f_res.write("#\n")

    return aed_files_out, hv_results, gen_numbers, hv_opt, ref_point


# ==============================================================================
# ENDPOINTS PRINCIPALES
# ==============================================================================
@app.route("/")
def main(): return send_from_directory(".", "main.html")

@app.route("/run", methods=["POST"])
def run():
    d = request.json or {}
    inst = d["instancia"]
    seed = int(d.get("semilla") or random.randint(1, 100))
    hv_every = int(d.get("save_interval") or d.get("hv_every") or 0)
    
    # Mapeo de parámetros CLI
    params = {
        "-inst": os.path.join(DIR_INSTANCES, inst),
        "-type": d.get("tipo", "cam"), "-variant": d.get("variante", "location"),
        "-alg": d.get("algoritmo", "MOEAD"), "-seed": str(seed),
        "-neval": str(d.get("neval", 1000)), "-pop": str(d.get("pop", 100)),
        "-neighbor": str(d.get("neighbor", 10)), "-decomp": str(d.get("decompType", 1)),
        "-save": str(hv_every if hv_every > 0 else 0)
    }
    for k in ["mut", "cross", "op1", "outDir"]:
        if d.get(k): params[f"-{k}"] = str(d[k])

    cmd = [PATH_MOEAD_EXEC] + [item for pair in params.items() for item in pair]
    print(f"[/run] Ejecutando MOEAD: {inst} seed={seed}")


    
    t0 = time.perf_counter()
    res = subprocess.run(cmd, cwd=DIR_MOEAD_CORE, capture_output=True, text=True)
    elapsed = time.perf_counter() - t0

    if res.returncode != 0:
        return jsonify({"error": "Error MOEAD", "stderr": res.stderr}), 500

    if res.stdout:
        print("[/run] MOEAD stdout:\n", res.stdout, flush=True)

    # Buscar archivos generados
    base = parse_instance_name(inst)
    raw_files = sorted(glob.glob(os.path.join(DIR_RAW_MOEAD, base, f"POF_{base}_SEED_*_GEN_*.dat")), key=gen_number_from_path)
    
    # Procesar usando la función centralizada
    files, hvs, gens, hv_opt, ref = core_process_results(inst, raw_files, hv_every)
    
    # Stats y retorno
    t_ampl = get_ampl_time(base)
    gap = ((elapsed - t_ampl)/t_ampl*100) if t_ampl else None
    
    # Guardar log run
    rec = {
        "run_id": f"{base}_{seed}_{int(time.time())}", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "instance": base, "seed": seed, "hv_final": hvs[-1] if hvs else 0,
        "time_moead_s": elapsed, "params": d
    }
    append_jsonl(os.path.join(DIR_RUN_STATS, "runs_all.jsonl"), rec)
    append_jsonl(os.path.join(DIR_RUN_STATS, f"{base}.jsonl"), rec)

    return jsonify({
        "files": [os.path.relpath(f, PROYECTO_ROOT) for f in files],
        "hv": hvs, "gen_numbers": gens, "hv_opt": hv_opt,
        "ref_point": {"x": ref[0], "y": ref[1]},
        "timeAmpl": t_ampl, "timeMoead": elapsed, "timeGap": gap
    })

@app.route("/load", methods=["POST"])
def load():
    d = request.json
    inst = d["instancia"]
    recalc = d.get("recalcular", False)
    strict = d.get("strict", False)
    hv_every = int(d.get("save_interval") or d.get("hv_every") or 0)
    if hv_every > 0: recalc = True

    base = parse_instance_name(inst)
    aeds_dir = os.path.join(DIR_AEDS_PROCESADOS, base)
    sum_path = os.path.join(DIR_FRENTES_PARETO, base, f"{base}_HV_summary.txt")
    
    # 1. Intentar cargar Caché
    cached_files = sorted(glob.glob(os.path.join(aeds_dir, f"{base}_Ubicaciones_GEN*.dat")), key=gen_number_from_path)
    
    if not recalc and os.path.exists(sum_path) and cached_files:
        print(f"[/load] Cache hit: {inst}")
        gens = [gen_number_from_path(f) for f in cached_files]
        hv_map, ref, hv_opt = {}, None, None
        
        with open(sum_path) as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        if lines:
            h = lines[0].split()
            ref = (float(h[0]), float(h[1]))
            if len(h) > 2: hv_opt = float(h[2])
            for l in lines[1:]:
                p = l.split()
                if len(p) >= 2:
                    try: hv_map[int(p[0].replace("GEN",""))] = float(p[1])
                    except: pass
        
        hvs = []
        last = 0.0
        for g in gens:
            if g in hv_map: last = hv_map[g]
            hvs.append(last)
            
        t_moead = get_moead_time(base)
        t_ampl = get_ampl_time(base)
        gap = ((t_ampl - t_moead)/t_ampl*100) if (t_ampl and t_moead) else None
        
        return jsonify({
            "files": [os.path.relpath(f, PROYECTO_ROOT) for f in cached_files],
            "hv": hvs, "gen_numbers": gens, "hvAmpl": hv_opt,
            "refPointGlobal": {"x": ref[0], "y": ref[1]} if ref else None,
            "timeAmpl": t_ampl, "timeMoead": t_moead, "timeGap": gap
        })

    if strict and not cached_files: return jsonify({"files": [], "hv": []})

    # 2. Procesar Raw (Fallback)
    raw_files = sorted(glob.glob(os.path.join(DIR_RAW_MOEAD, base, f"POF_{base}_GEN_*.dat")), key=gen_number_from_path)
    if not raw_files:
        print(f"[/load] No data found: {inst}")
        return jsonify({"files": [], "hv": []})

    print(f"[/load] Processing raw: {inst}")
    files, hvs, gens, hv_opt, ref = core_process_results(inst, raw_files, hv_every)
    
    t_moead = get_moead_time(base)
    t_ampl = get_ampl_time(base)
    gap = ((t_ampl - t_moead)/t_ampl*100) if (t_ampl and t_moead) else None

    return jsonify({
        "files": [os.path.relpath(f, PROYECTO_ROOT) for f in files],
        "hv": hvs, "gen_numbers": gens, "hv_opt": hv_opt,
        "ref_point": {"x": ref[0], "y": ref[1]},
        "timeAmpl": t_ampl, "timeMoead": t_moead, "timeGap": gap
    })

# ==============================================================================
# OTROS ENDPOINTS (Visualización, Maps, Utils)
# ==============================================================================
@app.route("/map", methods=["POST"])
def generar_mapa():
    d = request.json
    try:
        inst, ids = d["instancia"], set(map(int, d["ids"]))
        show_probs = d.get("show_probs", True)
        nodes, coords, demanda, pre, radio = cargar_instancia_coords_y_demanda(os.path.join(DIR_INSTANCES, inst))
    except: return "Error datos", 400

    flag_map = {idx: f for idx,_,_,f,_ in nodes}
    aeds_pre = [coords[i] for i in ids if i in coords and flag_map.get(i)==1]
    aeds_new = [coords[i] for i in ids if i in coords and flag_map.get(i)==0]
    all_aeds = [coords[i] for i in ids if i in coords]
    
    r2 = radio**2
    def is_cov(px, py, sources):
        for cx, cy in sources:
            if (px-cx)**2 + (py-cy)**2 <= r2: return True
        return False

    cov_pre_x, cov_pre_y, cov_pre_s = [], [], []
    cov_new_x, cov_new_y, cov_new_s = [], [], []
    uncov_x, uncov_y, uncov_s = [], [], []
    mov_x, mov_y, mov_s = [], [], []
    
    for idx, x, y, f, p in nodes:
        sz = (p*200) if show_probs else 20
        if idx not in ids:
            if f == 0:
                if aeds_pre and is_cov(x, y, aeds_pre): 
                    cov_pre_x.append(x); cov_pre_y.append(y); cov_pre_s.append(sz)
                elif aeds_new and is_cov(x, y, aeds_new):
                    cov_new_x.append(x); cov_new_y.append(y); cov_new_s.append(sz)
                else:
                    uncov_x.append(x); uncov_y.append(y); uncov_s.append(sz)
            elif f == 1:
                mov_x.append(x); mov_y.append(y); mov_s.append(sz)

    n_cov, p_cov, pct, tot_p, _ = cobertura_por_ids(all_aeds, demanda, [], radio)
    
    fig, ax = plt.subplots(figsize=(15, 8), dpi=100)
    if uncov_x: ax.scatter(uncov_x, uncov_y, s=uncov_s, c='blue', alpha=0.9, label='No Cubierta', edgecolors='k')
    if cov_pre_x: ax.scatter(cov_pre_x, cov_pre_y, s=cov_pre_s, c='orange', alpha=0.4, label='Cubierta (Pre)', edgecolors='k')
    if cov_new_x: ax.scatter(cov_new_x, cov_new_y, s=cov_new_s, c='green', alpha=0.4, label='Cubierta (New)', edgecolors='k')
    if mov_x: ax.scatter(mov_x, mov_y, s=mov_s, facecolors='none', edgecolors='red', linewidth=1.5, label='Movido')
    
    ax.scatter([x for x,y in aeds_pre], [y for x,y in aeds_pre], c='orange', s=120, marker='*', label='Preinstalado', edgecolors='k', zorder=4)
    ax.scatter([x for x,y in aeds_new], [y for x,y in aeds_new], c='green', s=120, marker='*', label='Nuevo', edgecolors='k', zorder=5)
    
    for x, y in all_aeds: ax.add_patch(plt.Circle((x,y), radio, color='gray', alpha=0.15, zorder=1))
    
    ax.set_aspect('equal'); ax.grid(True); ax.legend(loc='upper right')
    ax.set_title(f"{inst} - Cob: {pct:.2f}%")
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    return jsonify({"img": base64.b64encode(buf.getvalue()).decode('utf-8'), "stats": f"Cubiertos: {n_cov}\nProb: {p_cov:.4f}"})

@app.route("/map_json", methods=["POST"])
def map_json():
    d = request.json
    try:
        inst, ids = d["instancia"], set(map(int, d["ids"]))
        nodes, coords, demanda, pre_orig, radio = cargar_instancia_coords_y_demanda(os.path.join(DIR_INSTANCES, inst))
    except: return "Error", 400

    res = {"demanda": {"x":[],"y":[],"s":[]}, "pre_mov": {"x":[],"y":[],"s":[]}, "sel_new": {"x":[],"y":[]}, "sel_old": {"x":[],"y":[]}}
    show_p = d.get("show_probs", True)
    
    for idx, x, y, f, p in nodes:
        sz = (p*200) if show_p else 20
        if idx in ids:
            if f==0: res["sel_new"]["x"].append(x); res["sel_new"]["y"].append(y)
            elif f==1: res["sel_old"]["x"].append(x); res["sel_old"]["y"].append(y)
        else:
            if f==0: res["demanda"]["x"].append(x); res["demanda"]["y"].append(y); res["demanda"]["s"].append(sz)
            elif f==1: res["pre_mov"]["x"].append(x); res["pre_mov"]["y"].append(y); res["pre_mov"]["s"].append(sz)

    final_coords = [coords[i] for i in ids if i in coords]
    n_cov, p_cov, pct, tot_p, tot_n = cobertura_por_ids(final_coords, demanda, [], radio)
    
    txt = (f"📊 {inst}\nEstaciones: {len(ids)}\nPreinstaladas orig: {len(pre_orig)}\n"
           f"Cobertura: {n_cov}/{tot_n} ({pct:.2f}%)\nProbabilidad: {p_cov:.4f}/{tot_p:.4f}")

    coords_finales = list(zip(res["sel_new"]["x"]+res["sel_old"]["x"], res["sel_new"]["y"]+res["sel_old"]["y"]))
    return jsonify({"meta": {"instancia": inst, "radio": radio}, "demanda": res["demanda"], 
                    "preinstalados_movidos_origen": res["pre_mov"], "seleccionados_nuevos": res["sel_new"],
                    "seleccionados_existentes": res["sel_old"], "coords_finales_aeds": coords_finales, "stats": txt})

@app.route("/get/<path:filename>")
def get_file(filename):
    f = os.path.join(PROYECTO_ROOT, os.path.normpath(filename).lstrip(os.sep))
    return send_file(f) if os.path.exists(f) else abort(404)

@app.route("/list_instances", methods=["GET"])
def list_instances():
    os.makedirs(DIR_INSTANCES, exist_ok=True)
    return jsonify({"instances": sorted([f for f in os.listdir(DIR_INSTANCES) if f.endswith(".dat")])})

@app.route('/list_ampl_instances', methods=['GET'])
def list_ampl_instances():
    b = os.path.join(DIR_RAW_AMPL)
    if not os.path.isdir(b):
        return jsonify([])

    out = []
    for inst in os.listdir(b):
        base_dir = os.path.join(b, inst)
        if not os.path.isdir(base_dir):
            continue
        if find_ampl_front_file(inst):
            out.append(inst)

    return jsonify(sorted(out))


@app.route('/load_ampl_front', methods=['POST'])
def load_ampl_front():
    inst = request.get_json().get('instancia', '').replace('.dat', '')
    path = find_ampl_front_file(inst)
    if not path or not os.path.exists(path):
        return "No found", 404

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [l for l in f if l.strip() and not l.lstrip().startswith('#')]

    return "".join(lines), 200, {'Content-Type': 'text/plain'}


@app.route("/upload_map", methods=["POST"])
def upload_map():
    f = request.files.get("image")
    if not f or not f.filename: return jsonify({"error": "Falta archivo"}), 400
    name = secure_filename(request.form.get("name") or os.path.splitext(f.filename)[0])
    ext = os.path.splitext(f.filename)[1].lower()
    if ext[1:] not in {"png", "jpg", "jpeg", "webp"}: return jsonify({"error": "Formato"}), 400
    os.makedirs(DIR_STATIC_MAPS, exist_ok=True)
    f.save(os.path.join(DIR_STATIC_MAPS, name + ext))
    return jsonify({"url": url_for('static', filename=f"maps/{name}{ext}")})

@app.route("/save_instance", methods=["POST"])
def save_instance():
    d = request.get_json()
    name = secure_filename(d.get("name", "")).replace(".dat", "") + ".dat"
    pts = d.get("points", [])
    if not name or not pts: return jsonify({"error": "Datos incompletos"}), 400
    
    path = os.path.join(DIR_INSTANCES, name)
    os.makedirs(DIR_INSTANCES, exist_ok=True)
    with open(path, "w") as f:
        f.write(f"/* Gen Web */\nparam N_total:= {len(pts)} ;\n")
        for k in ["presupuesto", "radio", "c1", "c2"]:
            v = d.get(k, 0) if k=="presupuesto" else d.get(k, 1)
            f.write(f"param {k if k!='presupuesto' else 'P'}:= {v} ;\n")
        f.write(f'param nombre_instancia := "{name}" ;\n\nparam : coordx coordy flag prob_ohca:=\n')
        for p in sorted(pts, key=lambda x: int(x["id"])):
            f.write(f"{p['id']} {float(p['x']):.6f} {float(p['y']):.6f} {int(p.get('flag',0))} {float(p.get('prob',1)):.2f}\n")
        f.write(";\n")
    return jsonify({"ok": True})

@app.route("/list_run_stats", methods=["GET"])
def list_run_stats():
    i = request.args.get("inst", "").replace(".dat", "")
    p = os.path.join(DIR_RUN_STATS, f"{i}.jsonl" if i else "runs_all.jsonl")
    
    if not os.path.exists(p): return jsonify([])
    
    rows = []
    try:
        with open(p, "r", encoding="utf-8") as f:
            rows = [json.loads(l) for l in f if l.strip()]
    except: return jsonify([])

    result = []
    # Invertimos para ver los más recientes primero
    for r in rows[::-1]:
        # Las ejecuciones nuevas guardan los inputs dentro de "params"
        p = r.get("params", {}) 
        
        result.append({
            "run_id": r.get("run_id"),
            "ts": r.get("timestamp") or r.get("ts"),
            "hv_final": r.get("hv_final"),
            # Buscamos en la raíz (formato antiguo) O en params (formato nuevo)
            "neval": r.get("neval") or p.get("neval"),
            "pop": r.get("pop") or p.get("pop"),
            "neighbor": r.get("neighbor") or p.get("neighbor"),
            "mut": r.get("mut") or p.get("mut"),
            "cross": r.get("cross") or p.get("cross"),
            "op1": r.get("op1") or p.get("op1"),
            "time_s": r.get("time_moead_s")
        })
        
    return jsonify(result)

@app.route("/run_stats_detail", methods=["GET"])
def run_stats_detail():
    rid = request.args.get("run_id")
    p = os.path.join(DIR_RUN_STATS, "runs_all.jsonl")
    if not rid or not os.path.exists(p): return jsonify({"error": "No found"}), 404
    with open(p) as f:
        for l in f:
            if l.strip():
                j = json.loads(l)
                if j.get("run_id") == rid: return jsonify(j)
    return jsonify({"error": "ID not found"}), 404



@app.route("/compare_all", methods=["POST"])
def compare_all():
    """
    Ejecuta MOEAD DESDE CERO para TODAS las instancias en All.inst,
    guardando los frentes en:
        TT2/datos/res/raw_moead/cam/{instancia}/comparacion/
    y luego calcula HV / tiempos comparando contra AMPL.

    Devuelve para cada instancia:
      - HV AMPL, HV MOEAD, gap HV (%)
      - tiempo AMPL, tiempo MOEAD, gap tiempo (%)
      - archivos: frente AMPL, frente GEN0 MOEAD, frente GEN final MOEAD
    """

    data = request.get_json(force=True) or {}

    # Parámetros globales para la corrida de MOEAD
    algoritmo = data.get("algoritmo", "MOEAD")
    variante  = data.get("variante", "location")
    neval     = int(data.get("neval") or 1000)
    pop       = int(data.get("pop") or 100)
    neighbor  = int(data.get("neighbor") or 10)
    decomp    = int(data.get("decompType") or 1)

    def to_float_or_none(x):
        try:
            return float(x) if x not in (None, "",) else None
        except:
            return None

    mut   = to_float_or_none(data.get("mut"))
    cross = to_float_or_none(data.get("cross"))
    op1   = to_float_or_none(data.get("op1"))

    base_seed_raw = data.get("seed")
    base_seed = int(base_seed_raw) if base_seed_raw not in (None, "",) else None

    inst_list = read_all_inst_list()
    results = []
    errors  = []

    def rel_to_root(p):
        if not p:
            return None
        return os.path.relpath(p, PROYECTO_ROOT)

    for idx, inst in enumerate(inst_list):
        base_name = parse_instance_name(inst)
        print(f"[compare_all] Instancia: {inst}")

        # Carpeta comparacion: TT2/datos/res/raw_moead/cam/{instancia}/comparacion
        compare_dir = get_compare_dir(base_name)

        # Limpiar .dat viejos en comparacion/ (dejamos el JSONL de historial)
        for old in glob.glob(os.path.join(compare_dir, "*.dat")):
            try:
                os.remove(old)
            except OSError:
                pass

        # Seed: si el usuario dio una, la variamos un poco por instancia; si no, random
        if base_seed is not None:
            seed = base_seed + idx
        else:
            seed = random.randint(1, 10**6)

        compare_dir_abs = os.path.join(DIR_RAW_MOEAD, base_name, "comparacion")
        print("AAAAA", DIR_RAW_MOEAD, base_name, "comparacion")
        os.makedirs(compare_dir_abs, exist_ok=True)

        # 2) Directorio RELATIVO que MOEAD necesita (solo carpeta, sin ruta completa)
        #    MOEAD ya sabe que cuelga de datos/res/raw_moead/cam
        out_dir_rel = "comparacion"

        # Construir parámetros de línea de comando para MOEAD
        params = {
            "-inst": os.path.join(DIR_INSTANCES, inst),
            "-type": "cam",
            "-variant": variante,
            "-alg": algoritmo,
            "-seed": str(seed),
            "-neval": str(neval),
            "-pop": str(pop),
            "-neighbor": str(neighbor),
            "-decomp": str(decomp),
            # Queremos solo primer y último frente en comparacion/ (el ejecutable
            # suele controlar cuántos POF genera; aquí dejamos -save=0 para no
            # forzar nada adicional).
            "-save": "0",
            "-outDir": out_dir_rel,  # ← AQUÍ el cambio importante
        }
        if mut is not None:
            params["-mut"] = str(mut)
        if cross is not None:
            params["-cross"] = str(cross)
        if op1 is not None:
            params["-op1"] = str(op1)

        cmd = [PATH_MOEAD_EXEC] + [item for pair in params.items() for item in pair]
        print(f"[compare_all] Ejecutando MOEAD: {' '.join(cmd)} (cwd={DIR_MOEAD_CORE})")

        # Ejecutar MOEAD y medir tiempo
        t0 = time.perf_counter()
        res = subprocess.run(cmd, cwd=DIR_MOEAD_CORE, capture_output=True, text=True)
        t_moead_s = time.perf_counter() - t0

        if res.stdout:
            print(f"[compare_all] stdout MOEAD ({base_name}):\n{res.stdout}")

        if res.returncode != 0:
            err_msg = (res.stderr or "").strip() or f"returncode={res.returncode}"
            print(f"[compare_all] ERROR ejecutando MOEAD para {base_name}: {err_msg}")
            errors.append({"instance": base_name, "error": err_msg})

            # Igual intentamos leer datos de AMPL para que aparezca algo en la tabla
            ampl_front_file, t_ampl_s = get_ampl_stats_for_instance(base_name)
            result = {
                "instance": base_name,
                "hv_ampl": None,
                "hv_moead": None,
                "hv_gap_pct": None,
                "time_ampl_s": t_ampl_s,
                "time_moead_s": t_moead_s,
                "time_gap_pct": None,
                "ampl_front": rel_to_root(ampl_front_file),
                "moead_front_first": None,
                "moead_front_last": None,
            }
            save_compare_result(base_name, compare_dir, result)
            results.append(result)
            continue

        # -----------------------------
        # Frentes generados en comparacion/
        # -----------------------------
        first_front_file, last_front_file = get_first_last_front_in_dir(compare_dir)

        # Stats de AMPL
        ampl_front_file, t_ampl_s = get_ampl_stats_for_instance(base_name)

        # Si no hay nada de ninguno, igual guardamos algo mínimo
        if not ampl_front_file and not last_front_file:
            result = {
                "instance": base_name,
                "hv_ampl": None,
                "hv_moead": None,
                "hv_gap_pct": None,
                "time_ampl_s": t_ampl_s,
                "time_moead_s": t_moead_s,
                "time_gap_pct": None,
                "ampl_front": None,
                "moead_front_first": None,
                "moead_front_last": None,
            }
            save_compare_result(base_name, compare_dir, result)
            results.append(result)
            continue

        # -----------------------------
        #  HV con referencia automática
        # -----------------------------
        hv_ampl = None
        hv_moead = None
        hv_gap_pct = None

        files_for_ref = [f for f in [ampl_front_file, last_front_file] if f]
        if files_for_ref:
            ref_point = calcular_referencia_global(files_for_ref)

            if last_front_file:
                hv_moead = calculate_hv(last_front_file, ref_point)
            if ampl_front_file:
                hv_ampl = calculate_hv(ampl_front_file, ref_point)

            if hv_ampl not in (None, 0.0) and hv_moead is not None:
                hv_gap_pct = 100.0 * (hv_ampl - hv_moead) / hv_ampl

        # -----------------------------
        #  Gap de tiempos
        # -----------------------------
        time_gap_pct = None
        if t_ampl_s not in (None, 0.0) and t_moead_s is not None:
            time_gap_pct = 100.0 * (t_ampl_s - t_moead_s) / t_ampl_s

        # -----------------------------
        #  Resultado final por instancia
        # -----------------------------
        result = {
            "instance": base_name,
            "hv_ampl": hv_ampl,
            "hv_moead": hv_moead,
            "hv_gap_pct": hv_gap_pct,
            "time_ampl_s": t_ampl_s,
            "time_moead_s": t_moead_s,
            "time_gap_pct": time_gap_pct,
            # OJO: guardamos rutas RELATIVAS para que /get funcione bien
            "ampl_front": rel_to_root(ampl_front_file),
            "moead_front_first": rel_to_root(first_front_file),
            "moead_front_last": rel_to_root(last_front_file),
        }

        save_compare_result(base_name, compare_dir, result)
        results.append(result)

    return jsonify({
        "count": len(results),
        "results": results,
        "errors": errors
    })



@app.route("/compare_load", methods=["GET"])
def compare_load():
    """
    Carga la última comparación guardada en
    TT2/datos/res/raw_moead/cam/{instancia}/comparacion/compare_results.jsonl
    para cada instancia que tenga esa carpeta.
    """
    results = []

    # Recorre todas las instancias que tengan carpeta cam/*/comparacion
    pattern = os.path.join(DIR_RAW_MOEAD, "*", "comparacion")
    for compare_dir in glob.glob(pattern):
        inst_dir = os.path.dirname(compare_dir)
        base_name = os.path.basename(inst_dir)

        last = load_last_compare_result(compare_dir)
        if not last:
            continue

        # Por si quieres ajustar caminos relativos/absolutos aquí
        results.append(last)

    return jsonify({"count": len(results), "results": results})


if __name__ == "__main__":
    app.run(port=5000, debug=True)