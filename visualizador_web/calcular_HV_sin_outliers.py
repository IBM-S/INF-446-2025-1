
# ejecutar hipervolumen:  ../material/hv-1.3-src/hv -r "-3742.3881 12420.98" ../datos/res/analisis/cam/cam_14468_VENUSTIANO_CARRANZA/best_front_moead.txt

import os
import glob
import subprocess
import pandas as pd
import numpy as np
import argparse
import sys
import time
import re
from decimal import Decimal, ROUND_HALF_UP

# ================= CONFIGURACIÓN DE RUTAS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.join(BASE_DIR, "..") 

DIR_RES = os.path.join(PROYECTO_ROOT, "datos", "res")
DIR_AMPL = os.path.join(DIR_RES, "raw_ampl")
DIR_MOEAD = os.path.join(DIR_RES, "raw_moead")
DIR_ANALISIS = os.path.join(DIR_RES, "analisis")

HV_EXEC = os.path.join(PROYECTO_ROOT, "material", "hv-1.3-src", "hv")

REPORT_FILE = None

# ================= FUNCIONES =================
def filter_outliers_f2(points, mode="iqr", k=1.5, q=0.99, cap=None):
    if not points or mode == "none":
        return points, [], None

    ys = np.array([p[1] for p in points], dtype=float)

    if mode == "iqr":
        q1 = np.quantile(ys, 0.25)
        q3 = np.quantile(ys, 0.75)
        iqr = q3 - q1
        thr = q3 + k * iqr
    elif mode == "pctl":
        thr = np.quantile(ys, q)
    elif mode == "cap":
        if cap is None:
            return points, [], None
        thr = float(cap)
    else:
        return points, [], None

    kept = [p for p in points if p[1] <= thr]
    removed = [p for p in points if p[1] > thr]
    return kept, removed, thr


INST_PREFIX_RE = re.compile(r"^(cam|drp)_\d+_", re.IGNORECASE)

def display_inst_name(inst: str) -> str:
    # cam_1390_MILPA_ALTA -> MILPA_ALTA
    # drp_657_STATEN_ISLAND -> STATEN_ISLAND
    return INST_PREFIX_RE.sub("", inst)


def is_drp(problem_type: str) -> bool:
    return str(problem_type).lower().startswith("drp")

def f1_dec(problem_type: str) -> int:
    return 7 if is_drp(problem_type) else 4

def f2_dec(problem_type: str) -> int:
    return 3  # siempre 3 para costo / F2

def fmt_f1(problem_type: str, v: float) -> str:
    return f"{v:.{f1_dec(problem_type)}f}"

def fmt_f2(problem_type: str, v: float) -> str:
    return f"{v:.{f2_dec(problem_type)}f}"

def fmt_ref(problem_type: str, rx: float, ry: float) -> str:
    # (F1 con 4/7; F2 con 3)
    return f"({fmt_f1(problem_type, rx)}, {fmt_f2(problem_type, ry)})"


def read_points(filepath):
    points = []
    if not os.path.exists(filepath): return points
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and not line[0].isalpha():
                try:
                    parts = line.split()
                    x, y = float(parts[0]), float(parts[1])
                    points.append([x, y])
                except ValueError: pass
    return points

def filter_nondominated(points):
    if not points: return []
    points = np.array(points)
    clean_points = []
    for i, p1 in enumerate(points):
        dominated = False
        for j, p2 in enumerate(points):
            if i != j:
                if (p2[0] <= p1[0] and p2[1] <= p1[1]) and (p2[0] < p1[0] or p2[1] < p1[1]):
                    dominated = True
                    break
        if not dominated:
            clean_points.append(p1)
    
    unique_points = []
    seen = set()
    for p in clean_points:
        t = tuple(p)
        if t not in seen:
            unique_points.append(p)
            seen.add(t)
    return unique_points

def get_max_values_and_points(file_list):
    max_x, max_y = -1e30, -1e30
    all_points = []
    found = False
    
    for fpath in file_list:
        pts = read_points(fpath)
        if pts:
            found = True
            all_points.extend(pts)
            for p in pts:
                if p[0] > max_x: max_x = p[0]
                if p[1] > max_y: max_y = p[1]
                
    return (max_x, max_y, all_points) if found else (None, None, [])

def _qexp(decimals: int) -> Decimal:
    return Decimal("1") if decimals <= 0 else Decimal("1." + ("0" * decimals))

def quantize_float(v: float, decimals: int) -> float:
    # evita artefactos binarios tipo -0.018153432000...
    return float(Decimal(str(v)).quantize(_qexp(decimals), rounding=ROUND_HALF_UP))

def save_points_to_file(points, filepath, dec_x: int = 10, dec_y: int = 10, do_quantize: bool = False):
    with open(filepath, 'w') as f:
        for p in points:
            x, y = float(p[0]), float(p[1])
            if do_quantize:
                x = quantize_float(x, dec_x)
                y = quantize_float(y, dec_y)
            f.write(f"{x:.{dec_x}f} {y:.{dec_y}f}\n")

def calculate_hv_transparent(points, ref_point, temp_file_path):
    if not points: return 0.0
    
    save_points_to_file(points, temp_file_path)
    ref_string = f"{ref_point[0]} {ref_point[1]}"
    cmd = [HV_EXEC, "-r", ref_string, temp_file_path]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0: return 0.0
        return float(result.stdout.strip())
    except: return 0.0
    finally:
        if os.path.exists(temp_file_path): os.remove(temp_file_path)

def calculate_hv_from_file(ref_point, points_file_path):
    ref_string = f"{ref_point[0]} {ref_point[1]}"
    cmd = [HV_EXEC, "-r", ref_string, points_file_path]
    cmd_pretty = f'{HV_EXEC} -r "{ref_string}" {points_file_path}'
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return 0.0, cmd_pretty
        return float(result.stdout.strip()), cmd_pretty
    except:
        return 0.0, cmd_pretty

def get_execution_times(folder_path):
    # Busca summary log
    summary_file = os.path.join(folder_path, "execution_summary.csv")
    if not os.path.exists(summary_file):
        candidates = glob.glob(os.path.join(folder_path, "execution*summary.*"))
        if candidates: summary_file = candidates[0]
    
    times = {}
    if os.path.exists(summary_file):
        try:
            df = pd.read_csv(summary_file)
            df.columns = [c.strip().lower() for c in df.columns]
            col_run, col_time = None, None
            for c in df.columns:
                if c == 'run': col_run = c
                if c in ['time_s', 'time', 'duration']: col_time = c
            if col_run and col_time:
                for _, row in df.iterrows():
                    try: times[int(row[col_run])] = float(row[col_time])
                    except: continue
        except: pass
    return times

def gap_pct(ampl_val, moead_val):
    """
    GAP% = ((AMPL - MOEAD) / AMPL) * 100
    4 decimales. Si AMPL es NaN o 0 -> NaN
    """
    try:
        if ampl_val is None or np.isnan(ampl_val) or ampl_val == 0:
            return np.nan
        if moead_val is None or np.isnan(moead_val):
            return np.nan
        return ((ampl_val - moead_val) / ampl_val) * 100.0
    except:
        return np.nan

def winner_min(ampl, moead, tol=1e-12):
    """Gana el menor (tiempo)."""
    if ampl is None or moead is None or np.isnan(ampl) or np.isnan(moead):
        return "-"
    if abs(ampl - moead) <= tol:
        return "EMPATE"
    return "AMPL" if ampl < moead else "MOEAD"

def winner_max(ampl, moead, tol=1e-12):
    """Gana el mayor (HV, ND)."""
    if ampl is None or moead is None or np.isnan(ampl) or np.isnan(moead):
        return "-"
    if abs(ampl - moead) <= tol:
        return "EMPATE"
    return "AMPL" if ampl > moead else "MOEAD"

def fmt_gap_only(v):
    return f"{v:+.4f}%" if pd.notna(v) else "-"

def fmt_float(v, w=12, d=4):
    return f"{v:>{w}.{d}f}" if pd.notna(v) else f"{'-':>{w}}"

def fmt_int(v, w=12):
    try:
        return f"{int(v):>{w}d}"
    except:
        return f"{'-':>{w}}"

def safe_round_int(v):
    """Devuelve int redondeado o None si v es NaN/None."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and np.isnan(v):
            return None
        if pd.isna(v):
            return None
        return int(round(float(v)))
    except:
        return None

def fmt_int_or_dash(v, w):
    """Alinea a la derecha: entero o '-'."""
    return f"{v:>{w}d}" if isinstance(v, int) else f"{'-':>{w}}"


def get_max_values_moead_clean(file_list, outlier_mode, k, q, cap):
    # junta todos los puntos
    _, _, all_pts = get_max_values_and_points(file_list)
    if not all_pts:
        return None, None, 0, None

    nd = filter_nondominated(all_pts)

    nd_clean, removed, thr = filter_outliers_f2(
        nd, mode=outlier_mode, k=k, q=q, cap=cap
    )

    if not nd_clean:
        return None, None, len(removed), thr

    mx = max(p[0] for p in nd_clean)
    my = max(p[1] for p in nd_clean)
    return mx, my, len(removed), thr


def load_instance_order_from_all_inst(all_inst_path: str):
    """
    Lee All.inst y devuelve una lista de nombres de instancia SIN extensión .dat.
    Ignora líneas vacías y comentarios (#).
    """
    order = []
    if not os.path.exists(all_inst_path):
        return order

    with open(all_inst_path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            # puede venir con ruta o solo filename
            base = os.path.basename(s)
            name, _ext = os.path.splitext(base)
            order.append(name)
    return order

def fmt_seconds_with_minutes(sec, dec_s=4, dec_m=2):
    """
    Devuelve: "90.0000 s (1.50 min)"
    Si sec es NaN -> "-"
    """
    if sec is None or (isinstance(sec, float) and np.isnan(sec)):
        return "-"
    try:
        s = float(sec)
    except:
        return "-"
    m = s / 60.0
    return f"{s:.{dec_s}f} s ({m:.{dec_m}f} min)"

def cell(text: str, width: int) -> str:
    """Ajusta a ancho fijo (derecha)."""
    return f"{text:>{width}}"

ANSI_BOLD  = "\033[1m"
ANSI_RESET = "\033[0m"
USE_ANSI_BOLD = True

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def strip_ansi(s: str) -> str:
    """Quita códigos ANSI (negrita/colores) para dejar texto limpio en .txt."""
    return ANSI_RE.sub("", s)


def maybe_bold(text):
    if USE_ANSI_BOLD:
        return f"{ANSI_BOLD}{text}{ANSI_RESET}"
    return text

def mark_winner_cell(value_text: str, width: int) -> str:
    """
    Pone paréntesis pegados al valor: (51128.6653)
    y luego alinea TODA la cadena al ancho de la celda (padding queda afuera).
    """
    marked = f"({value_text})"
    return maybe_bold(cell(marked, width))


def print_best_row(name, points, ref, out_dir):
    if points:
        temp_f = os.path.join(out_dir, f"temp_best_{name.lower()}.dat")
        hv = calculate_hv_transparent(points, ref, temp_f)
        print(f"{name:<10} {len(points):<15} {hv:<15.6f}")
        return len(points), hv
    else:
        print(f"{name:<10} {'-':<15} {'-':<15}")
        return 0, 0.0

def _is_missing(v):
    return v is None or (isinstance(v, float) and np.isnan(v))

def winner_min(ampl, moead, tol=1e-12):
    """Gana el menor (tiempo). Si uno no tiene dato, gana el que sí tiene."""
    a_miss = _is_missing(ampl)
    m_miss = _is_missing(moead)

    if a_miss and m_miss:
        return "-"          # ninguno
    if a_miss and not m_miss:
        return "MOEAD"      # solo MOEAD tiene
    if m_miss and not a_miss:
        return "AMPL"       # solo AMPL tiene

    if abs(ampl - moead) <= tol:
        return "EMPATE"
    return "AMPL" if ampl < moead else "MOEAD"

def winner_max(ampl, moead, tol=1e-12):
    """Gana el mayor (HV, ND). Si uno no tiene dato, gana el que sí tiene."""
    a_miss = _is_missing(ampl)
    m_miss = _is_missing(moead)

    if a_miss and m_miss:
        return "-"
    if a_miss and not m_miss:
        return "MOEAD"
    if m_miss and not a_miss:
        return "AMPL"

    if abs(ampl - moead) <= tol:
        return "EMPATE"
    return "AMPL" if ampl > moead else "MOEAD"

# ================= MAIN =================

def procesar_instancias(problem_type="cam", target_instance=None, args=None):
    print(f"\n==================================================")
    print(f" ANALIZANDO TIPO: {problem_type.upper()}")
    if target_instance: print(f" FILTRO INSTANCIA: {target_instance}")
    print(f"==================================================")
    
    # 1. LISTAR TODAS LAS INSTANCIAS (Uniendo AMPL y MOEAD)
    path_ampl_base = os.path.join(DIR_AMPL, problem_type)
    path_moead_base = os.path.join(DIR_MOEAD, problem_type)
    
    insts_ampl = []
    if os.path.exists(path_ampl_base):
        insts_ampl = [d for d in os.listdir(path_ampl_base) if os.path.isdir(os.path.join(path_ampl_base, d))]
        
    insts_moead = []
    if os.path.exists(path_moead_base):
        insts_moead = [d for d in os.listdir(path_moead_base) if os.path.isdir(os.path.join(path_moead_base, d))]
        
    # Set de instancias únicas ordenadas
    todas_set = set(insts_ampl + insts_moead)

    # Orden desde All.inst (misma carpeta del script)
    all_inst_path = os.path.join(BASE_DIR, "All.inst")
    order_from_file = load_instance_order_from_all_inst(all_inst_path)

    # Primero las que aparecen en All.inst, en ese orden
    todas_instancias = [x for x in order_from_file if x in todas_set]

    # Luego cualquier instancia que exista pero no esté en All.inst (por si acaso)
    restantes = sorted(list(todas_set - set(todas_instancias)))
    todas_instancias.extend(restantes)


    if not todas_instancias:
        print("No se encontraron instancias en raw_ampl ni raw_moead.")
        return

    # Reporte global (en el mismo directorio donde está este script)
    report_path = os.path.join(BASE_DIR, f"reporte_{problem_type}_resumen_sin_outliers.txt")
    # Si estás analizando todas las instancias, lo reiniciamos
    if target_instance is None:
        with open(report_path, "w", encoding="utf-8") as rf:
            rf.write(f"REPORTE RESUMEN - TIPO {problem_type.upper()}\n\n")

    wins_hv_best = {"AMPL": 0, "MOEAD": 0, "EMPATE": 0, "SIN_DATOS": 0}
    processed = 0

    wins_instances = {"AMPL": [], "MOEAD": [], "EMPATE": [], "SIN_DATOS": []}

    # ================= RESUMEN FINAL TABLA =================
    summary_rows = []  # una fila por instancia (HV best + T.Ejec promedio)
    wins_hv_total = {"AMPL": 0, "MOEAD": 0, "EMPATE": 0, "-": 0}
    wins_te_prom  = {"AMPL": 0, "MOEAD": 0, "EMPATE": 0, "-": 0}

    W_INST = 22       
    W_HV   = 18    
    W_GAP  = 12          
    W_TE   = 28        
    W_WIN  = 12

    W_METH = 10
    W_TE   = 18
    W_ND   = 10
    W_HV1  = 18
    W_HV2  = 22
    W_HV3  = 22




    for inst in todas_instancias:
        if target_instance and inst != target_instance: continue
        
        print(f"\n>>> Procesando: {inst}")
        out_dir = os.path.join(DIR_ANALISIS, problem_type, inst)
        os.makedirs(out_dir, exist_ok=True)

        # ---------------------------------------------------------
        # 1. ANÁLISIS DE MÁXIMOS (Punto de Referencia)
        # ---------------------------------------------------------
        print("  [1] Análisis de Puntos Extremos (Nadir)")
        
        # A. AMPL
        max_x_ampl, max_y_ampl, all_ampl_points = None, None, []
        path_inst_ampl = os.path.join(path_ampl_base, inst)
        
        if os.path.exists(path_inst_ampl):
            t_start = time.time()
            ampl_files = glob.glob(os.path.join(path_inst_ampl, "run_*", "pareto_front.txt"))
            max_x_ampl, max_y_ampl, all_ampl_points = get_max_values_and_points(ampl_files)
            t_scan = time.time() - t_start
            
            if max_x_ampl is not None:
                print(f"      -> AMPL  : F1={fmt_f1(problem_type, max_x_ampl)}, F2={fmt_f2(problem_type, max_y_ampl)} (Scan: {t_scan:.4f}s)")
            else:
                print(f"      -> AMPL  : Carpeta existe pero sin puntos válidos.")
        else:
            print(f"      -> AMPL  : No existe carpeta de resultados.")

        # B. MOEAD
        max_x_moead, max_y_moead, all_moead_final_points = None, None, []
        path_inst_moead = os.path.join(path_moead_base, inst)
        
        # Para el máximo global buscamos en TODO el historial (POF_*.dat)
        # Para el Best Front solo usaremos pareto_front.txt
        
        if os.path.exists(path_inst_moead):
            t_start = time.time()
            # 1. Busqueda de maximos en historial
            moead_last_gens = glob.glob(os.path.join(path_inst_moead, "run_*", f"last_gen_{inst}.dat"))
            max_x_moead, max_y_moead, _ = get_max_values_and_points(moead_last_gens)
            t_scan = time.time() - t_start
            
            # 2. Recolección de puntos finales para Best Front
            moead_final_files = glob.glob(os.path.join(path_inst_moead, "run_*", "pareto_front.txt"))
            _, _, all_moead_final_points = get_max_values_and_points(moead_final_files)

            if max_x_moead is not None:
                print(f"      -> MOEAD : F1={fmt_f1(problem_type, max_x_moead)}, F2={fmt_f2(problem_type, max_y_moead)} (Scan: {t_scan:.4f}s)")
            else:
                print(f"      -> MOEAD : Carpeta existe pero sin puntos válidos.")
            max_x_moead_clean, max_y_moead_clean, rem_ref, thr_ref = get_max_values_moead_clean(
                moead_last_gens,
                args.outliers, args.outlier_k, args.outlier_q, args.outlier_cap
            )

            print(f"      -> MOEAD(clean for REF): F1={fmt_f1(problem_type, max_x_moead_clean) if max_x_moead_clean is not None else '-'}, "
                f"F2={fmt_f2(problem_type, max_y_moead_clean) if max_y_moead_clean is not None else '-'} "
                f"(removed={rem_ref}, thr={thr_ref})")

        else:
            print(f"      -> MOEAD : No existe carpeta de resultados.")

        # C. CALCULO PUNTO REFERENCIA
        valid_x = [v for v in [max_x_ampl, max_x_moead] if v is not None]
        valid_y = [v for v in [max_y_ampl, max_y_moead] if v is not None]

        if not valid_x or not valid_y:
            print("      [!] Sin datos en ningún método. Saltando instancia.")
            continue

        global_max_x = max(valid_x)
        global_max_y = max(valid_y)

        FACTOR_F1 = 0.99
        FACTOR_F2 = 1.001

        ref1_x = global_max_x * FACTOR_F1
        ref1_y = global_max_y * FACTOR_F2


        if (ref1_x == 0.0):
            ref1_x = 0.1

        src_x = []
        src_y = []
        if max_x_ampl is not None and abs(max_x_ampl - global_max_x) <= 1e-12: src_x.append("AMPL")
        if max_x_moead is not None and abs(max_x_moead - global_max_x) <= 1e-12: src_x.append("MOEAD")
        if max_y_ampl is not None and abs(max_y_ampl - global_max_y) <= 1e-12: src_y.append("AMPL")
        if max_y_moead is not None and abs(max_y_moead - global_max_y) <= 1e-12: src_y.append("MOEAD")

        src_x_txt = "/".join(src_x) if src_x else "-"
        src_y_txt = "/".join(src_y) if src_y else "-"

        # prints con decimales correctos
        print(f"      -> peor F1 = {fmt_f1(problem_type, global_max_x)}  (desde {src_x_txt})")
        print(f"      -> peor F2 = {fmt_f2(problem_type, global_max_y)}  (desde {src_y_txt})")
        print(
            f"      -> PUNTO REF: F1_ref = {FACTOR_F1} * peorF1 = {FACTOR_F1} * {fmt_f1(problem_type, global_max_x)}"
            f" = {fmt_f1(problem_type, ref1_x)}; "
            f"F2_ref = {FACTOR_F2} * peorF2 = {FACTOR_F2} * {fmt_f2(problem_type, global_max_y)}"
            f" = {fmt_f2(problem_type, ref1_y)}"
        )
        print(f"      -> PUNTO REF: {fmt_ref(problem_type, ref1_x, ref1_y)}")


        valid_x2 = [v for v in [max_x_ampl, max_x_moead_clean] if v is not None]
        valid_y2 = [v for v in [max_y_ampl, max_y_moead_clean] if v is not None]

        # AMPL siempre puede aportar (si existe)
        if max_x_ampl is not None: valid_x2.append(max_x_ampl)
        if max_y_ampl is not None: valid_y2.append(max_y_ampl)

        # MOEAD limpio solo si existe y tuvo puntos
        if max_x_moead_clean is not None: valid_x2.append(max_x_moead_clean)
        if max_y_moead_clean is not None: valid_y2.append(max_y_moead_clean)

        if not valid_x2 or not valid_y2:
            # si REF1 existe, puedes reutilizar REF1 como REF2 (o saltar HV3)
            print("      [!] No hay datos suficientes para REF2. Se reutiliza REF1 para HV3.")
            ref2_x, ref2_y = ref_x, ref_y
        else:
            global_max_x2 = max(valid_x2)
            global_max_y2 = max(valid_y2)
            ref2_x = global_max_x2 * FACTOR_F1
            ref2_y = global_max_y2 * FACTOR_F2


        global_max_x2 = max(valid_x2)
        global_max_y2 = max(valid_y2)

        ref2_x = global_max_x2 * FACTOR_F1
        ref2_y = global_max_y2 * FACTOR_F2

        print(f"      -> PUNTO REF2 (MOEAD limpio): {fmt_ref(problem_type, ref2_x, ref2_y)}")


        dec_x_config = f1_dec(problem_type)
        dec_y_best_config = 1 if is_drp(problem_type) else 0

        # guardar ref (puedes guardar con full precisión o con formato)
        with open(os.path.join(out_dir, "reference_point.txt"), "w") as f:
            f.write(f"{ref1_x:.{dec_x_config}f} {ref1_y:.3f}\n")


        # D. GUARDAR BEST FRONTS (Si existen puntos)
        ampl_best = filter_nondominated(all_ampl_points)
        if ampl_best:
            save_points_to_file(ampl_best, os.path.join(out_dir, "best_front_ampl.txt"), dec_x=dec_x_config, dec_y=dec_y_best_config)
        
        moead_best = filter_nondominated(all_moead_final_points)
        if moead_best:
            save_points_to_file(moead_best, os.path.join(out_dir, "best_front_moead.txt"), dec_x=dec_x_config, dec_y=dec_y_best_config)

        print(f"      -> Best Fronts: AMPL ({len(ampl_best)} pts), MOEAD ({len(moead_best)} pts)")


        ampl_best_no, ampl_removed, thrA = ampl_best, [], None
        moead_best_no, moead_removed, thrM = filter_outliers_f2(moead_best, mode=args.outliers,
                                                            k=args.outlier_k, q=args.outlier_q,
                                                            cap=args.outlier_cap)

        # HV con ref fijo (escenario A)
        h_a_no = calculate_hv_transparent(ampl_best_no, (ref1_x, ref1_y), os.path.join(out_dir,"temp_best_ampl_no.dat"))
        h_m_no = calculate_hv_transparent(moead_best_no, (ref1_x, ref1_y), os.path.join(out_dir,"temp_best_moead_no.dat"))

        # HV3: AMPL normal con ref2
        h_a_3 = calculate_hv_transparent(ampl_best, (ref2_x, ref2_y), os.path.join(out_dir,"temp_best_ampl_ref2.dat"))

        # HV3: MOEAD limpio con ref2
        h_m_3 = calculate_hv_transparent(moead_best_no, (ref2_x, ref2_y), os.path.join(out_dir,"temp_best_moead_clean_ref2.dat"))

        # ---------------------------------------------------------
        # 2. CÁLCULO DE MÉTRICAS INDIVIDUALES
        # ---------------------------------------------------------
        print("\n  [2] Calculando Métricas por Run")
        final_data = []
        methods = [
            {'name': 'AMPL',  'path': path_inst_ampl},
            {'name': 'MOEAD', 'path': path_inst_moead}
        ]

        for m in methods:
            m_name = m['name']
            m_path = m['path']
            
            if not os.path.exists(m_path):
                # Si no existe la carpeta, simplemente no agregamos datos (el resumen pondrá guiones)
                continue

            times_dict = get_execution_times(m_path)
            run_folders = sorted(glob.glob(os.path.join(m_path, "run_*")))

            def get_run_number(folder_path):
                try:
                    return int(os.path.basename(folder_path).split('_')[1])
                except:
                    return 99999

            run_folders.sort(key=get_run_number)
            
            if not run_folders:
                print(f"      -> {m_name}: Carpeta vacía (sin runs).")

            for rf in run_folders:
                try: run_id = int(os.path.basename(rf).split('_')[1])
                except: continue
                
                print(f"      -> {m_name} Run {run_id:<2} ... ", end='', flush=True)
                
                pareto_file = os.path.join(rf, "pareto_front.txt")
                points = read_points(pareto_file)
                
                # Si no hay puntos, igual registramos la run pero con HV 0
                if not points:
                    print(f"VACÍO/ERROR")
                    final_data.append({
                        "metodo": m_name, "run": run_id, "time_ejec": np.nan,
                        "nd_points": 0, "hv": 0.0
                    })
                    continue

                clean_points = filter_nondominated(points)

                # --- temp file (se reutiliza para las 3 llamadas) ---
                temp_file = os.path.join(out_dir, f"temp_{m_name}_{run_id}.dat")

                # =========================
                # ESCENARIO 1: Normal (ref1) sin filtrar
                # =========================
                hv_s1 = calculate_hv_transparent(clean_points, (ref1_x, ref1_y), temp_file)
                # =========================
                # ESCENARIO 2: Quitar outliers a AMBOS, ref1 fijo
                # =========================
                if m_name == "MOEAD":
                    clean_f, removed_f, thr_f = filter_outliers_f2(
                        clean_points, mode=args.outliers,
                        k=args.outlier_k, q=args.outlier_q, cap=args.outlier_cap
                    )
                else:
                    clean_f, removed_f, thr_f = clean_points, [], None


                hv_s2 = calculate_hv_transparent(clean_f, (ref1_x, ref1_y), temp_file)

                # =========================
                # ESCENARIO 3: Quitar outliers SOLO a MOEAD + ref2 nuevo
                #   - AMPL: puntos normales
                #   - MOEAD: puntos filtrados
                # =========================
                hv_s3 = calculate_hv_transparent(clean_f, (ref2_x, ref2_y), temp_file)

                time_exec = times_dict.get(run_id, np.nan)

                print(
                    f"OK. HV1={hv_s1:.6f} | HV2={hv_s2:.6f} | HV3={hv_s3:.6f} | "
                    f"removed={len(removed_f)}" + (f" thr={thr_f:.3f}" if thr_f is not None else "")
                )


                final_data.append({
                    "metodo": m_name,
                    "run": run_id,
                    "time_ejec": time_exec,

                    # ND sin filtro (base)
                    "nd_raw": len(clean_points),

                    # HVs
                    "hv_s1": hv_s1,   # normal con ref1
                    "hv_s2": hv_s2,   # MOEAD filtrado (si aplica) con ref1
                    "hv_s3": hv_s3,   # MOEAD filtrado (si aplica) con ref2

                    # info del filtro (solo MOEAD, en AMPL queda 0/None)
                    "nd_filt": len(clean_f),          # puntos después de filtro (o igual a raw si AMPL)
                    "out_removed": len(removed_f),
                    "out_thr": thr_f,
                })




        # ---------------------------------------------------------
        # 3. RESUMEN FINAL Y TABLAS
        # ---------------------------------------------------------

                
        # Guardar CSV detallado (incluso si solo hay datos de uno)
        if final_data:
            df = pd.DataFrame(final_data)
            csv_out = os.path.join(out_dir, "final_summary.csv")
            df.to_csv(csv_out, index=False)

            
            # --- TABLA 1: PROMEDIOS POR ALGORITMO + GAP ---
            print(f"\n  [3] RESUMEN PROMEDIO (Por Run):")
            print("-" * 95)
            print(f"{'metodo':<10} {'T. Ejec prom':<20} {'ND prom':<15} {'HV1(ref1)':<20} {'HV2(no_out+ref1)':<20} {'HV3(moeadClean+ref2)':<25}")
            print("-" * 95)

            resumen = df.groupby("metodo")[["time_ejec", "nd_raw", "hv_s1", "hv_s2", "hv_s3"]].mean()

            def safe_get(method, col):
                return float(resumen.loc[method, col]) if method in resumen.index and pd.notna(resumen.loc[method, col]) else np.nan

            ampl_nd  = safe_round_int(safe_get("AMPL", "nd_raw"))
            moead_nd = safe_round_int(safe_get("MOEAD", "nd_raw"))
            g_nd = gap_pct(ampl_nd, moead_nd)
            w_nd = winner_max(ampl_nd, moead_nd)   # si “más ND” lo consideras mejor


            ampl_te  = safe_get("AMPL",  "time_ejec")
            moead_te = safe_get("MOEAD", "time_ejec")

            ampl_hv1  = safe_get("AMPL",  "hv_s1")
            moead_hv1 = safe_get("MOEAD", "hv_s1")

            ampl_hv2  = safe_get("AMPL",  "hv_s2")
            moead_hv2 = safe_get("MOEAD", "hv_s2")

            ampl_hv3  = safe_get("AMPL",  "hv_s3")
            moead_hv3 = safe_get("MOEAD", "hv_s3")


            def fmt_time(v, d=4): return f"{v:.{d}f} s" if pd.notna(v) else "-"
            def fmt_num(v, d=6):  return f"{v:.{d}f}" if pd.notna(v) else "-"
            def fmt_gap(v):       return f"{v:.4f} %" if pd.notna(v) else "-"

            # filas AMPL/MOEAD
            print(f"{'AMPL':<10} {fmt_time(ampl_te,4):>12} {fmt_int_or_dash(ampl_nd, W_ND):>15} {fmt_num(ampl_hv1,4):>20} {fmt_num(ampl_hv2,4):>20} {fmt_num(ampl_hv3,4):>25}")
            print(f"{'MOEAD':<10} {fmt_time(moead_te,4):>12} {fmt_int_or_dash(moead_nd, W_ND):>15} {fmt_num(moead_hv1,4):>20} {fmt_num(moead_hv2,4):>20} {fmt_num(moead_hv3,4):>25}")


            # fila GAP (con tu fórmula AMPL-MOEAD sobre AMPL)
            g_te  = gap_pct(ampl_te, moead_te)

            g_hv1 = gap_pct(ampl_hv1, moead_hv1)
            g_hv2 = gap_pct(ampl_hv2, moead_hv2)
            g_hv3 = gap_pct(ampl_hv3, moead_hv3)

            print("-" * 95)
            print(f"{'GAP%':<10} {fmt_gap(g_te):>12} {fmt_gap(g_nd):>15} {fmt_gap(g_hv1):>20} {fmt_gap(g_hv2):>20} {fmt_gap(g_hv3):>25}")
            print("-" * 95)

            w_time = winner_min(ampl_te, moead_te)
            w_hv1 = winner_max(ampl_hv1, moead_hv1)
            w_hv2 = winner_max(ampl_hv2, moead_hv2)
            w_hv3 = winner_max(ampl_hv3, moead_hv3)


            print(f"{'WINNER':<10} {w_time:>12} {w_nd:>15} {w_hv1:>20} {w_hv2:>20} {w_hv3:>25}")
            print("-" * 95)


            # --- TABLA 2: BEST FRONTS UNIFICADOS ---
            print(f"\n  [4] COMPARACIÓN DE BEST FRONTS (Frentes Unificados):")
            print("-" * 95)
            print(f"{'metodo':<10} {'ND':<6} {'HV1(ref1)':<15} {'HV2(no_out+ref1)':<18} {'HV3(moeadClean+ref2)':<22}")
            print("-" * 95)

            # ND
            n_a = len(ampl_best) if ampl_best else 0
            n_m = len(moead_best) if moead_best else 0

            # HV1 (ref1, sin filtro)
            h_a = calculate_hv_transparent(ampl_best, (ref1_x, ref1_y), os.path.join(out_dir, "temp_best_ampl_ref1.dat"))
            h_m = calculate_hv_transparent(moead_best, (ref1_x, ref1_y), os.path.join(out_dir, "temp_best_moead_ref1.dat"))

            # HV2 (MOEAD filtrado con ref1) -> ya lo tienes como h_a_no, h_m_no
            # (pero ojo: tú estás filtrando AMPL también en ampl_best_no; si quieres “solo MOEAD”, deja AMPL sin filtrar)
            # Forzamos HV2 de AMPL = HV1
            h_a_no = h_a

            # HV3 (MOEAD filtrado con ref2) -> ya tienes h_a_3, h_m_3
            # Para consistencia, calculamos h_a_3 aquí también (AMPL sin filtrar con ref2):
            h_a_3 = calculate_hv_transparent(ampl_best, (ref2_x, ref2_y), os.path.join(out_dir, "temp_best_ampl_ref2.dat"))
            # y MOEAD limpio con ref2:
            h_m_3 = calculate_hv_transparent(moead_best_no, (ref2_x, ref2_y), os.path.join(out_dir, "temp_best_moead_clean_ref2.dat"))

            # Imprimir filas completas (3 HV)
            print(f"{'AMPL':<10} {n_a:<6} {h_a:<15.6f} {h_a_no:<18.6f} {h_a_3:<22.6f}")
            print(f"{'MOEAD':<10} {n_m:<6} {h_m:<15.6f} {h_m_no:<18.6f} {h_m_3:<22.6f}  removed={len(moead_removed)}" +
                (f" thr={thrM:.3f}" if thrM is not None else ""))


            # ======= Fila para resumen final =======
            win_hv = winner_max(h_a, h_m)          # HV best front: mayor es mejor
            win_te = winner_min(ampl_te, moead_te) # T.Ejec promedio: menor es mejor

            # Conteos de victorias
            wins_hv_total[win_hv] = wins_hv_total.get(win_hv, 0) + 1
            wins_te_prom[win_te]  = wins_te_prom.get(win_te, 0) + 1

            summary_rows.append({
                "inst": inst,
                "inst_disp": display_inst_name(inst),

                # ND best fronts (por si quieres GAP_ND en resumen final)
                "nd_a": n_a,
                "nd_m": n_m,

                # HVs best fronts (los que YA calculaste arriba)
                "hv1_a": h_a,     "hv1_m": h_m,
                "hv2_a": h_a_no,  "hv2_m": h_m_no,
                "hv3_a": h_a_3,   "hv3_m": h_m_3,

                # tiempos promedio (tabla [3])
                "te_a": ampl_te,
                "te_m": moead_te,
                "gap_te": gap_pct(ampl_te, moead_te),
                "win_te": winner_min(ampl_te, moead_te),
            })


            processed += 1

            # Victoria por HV Total de Best Fronts (mayor HV gana)
            if (ampl_best and moead_best):
                if abs(h_a - h_m) <= 1e-12:
                    wins_hv_best["EMPATE"] += 1
                    wins_instances["EMPATE"].append(inst)
                elif h_a > h_m:
                    wins_hv_best["AMPL"] += 1
                    wins_instances["AMPL"].append(inst)
                else:
                    wins_hv_best["MOEAD"] += 1
                    wins_instances["MOEAD"].append(inst)
            elif ampl_best and (not moead_best):
                wins_hv_best["AMPL"] += 1
                wins_instances["AMPL"].append(inst)
            elif moead_best and (not ampl_best):
                wins_hv_best["MOEAD"] += 1
                wins_instances["MOEAD"].append(inst)
            else:
                wins_hv_best["SIN_DATOS"] += 1
                wins_instances["SIN_DATOS"].append(inst)

            g_nd = gap_pct(float(n_a), float(n_m))
            g_hv_best = gap_pct(h_a, h_m)

            print("-" * 95)
            print(f"{'GAP%':<10} {'':<6} {fmt_gap(gap_pct(h_a,h_m)):<15} {fmt_gap(gap_pct(h_a_no,h_m_no)):<18} {fmt_gap(gap_pct(h_a_3,h_m_3)):<22}")

            w_nd = winner_max(float(n_a), float(n_m))

            w_bf1 = winner_max(h_a,   h_m)
            w_bf2 = winner_max(h_a_no, h_m_no)
            w_bf3 = winner_max(h_a_3, h_m_3)

            print("-" * 95)
            print(f"{'WINNER':<10} {'':<6} {w_bf1:<15} {w_bf2:<18} {w_bf3:<22}")
            print("-" * 95)



            # Guardar metrics de Best Fronts
            best_csv = os.path.join(out_dir, "best_fronts_metrics.csv")
            with open(best_csv, 'w') as f:
                f.write("metodo,nd_points,hv_total\n")
                if ampl_best: f.write(f"AMPL,{n_a},{h_a}\n")
                if moead_best: f.write(f"MOEAD,{n_m},{h_m}\n")

            # ---------------------------------------------------------
            # REPORTE GLOBAL (append por instancia) - TABLAS ALINEADAS
            # ---------------------------------------------------------
            w_time = winner_min(ampl_te, moead_te)
            w_hv   = winner_max(ampl_hv1, moead_hv1)

            w_nd   = winner_max(float(n_a), float(n_m))
            w_hvt  = winner_max(h_a, h_m)

            with open(report_path, "a", encoding="utf-8") as rf:
                rf.write(f"INSTANCIA: {inst}\n")

                rf.write("[1] ANALISIS PUNTOS EXTREMOS (Nadir)\n")
                rf.write(f"AMPL : F1={fmt_f1(problem_type, max_x_ampl) if max_x_ampl is not None else '-'} "
                        f"F2={fmt_f2(problem_type, max_y_ampl) if max_y_ampl is not None else '-'}\n")
                rf.write(f"MOEAD: F1={fmt_f1(problem_type, max_x_moead) if max_x_moead is not None else '-'} "
                        f"F2={fmt_f2(problem_type, max_y_moead) if max_y_moead is not None else '-'}\n")
                rf.write(f"peorF1={fmt_f1(problem_type, global_max_x)} (src {src_x_txt}), "
                        f"peorF2={fmt_f2(problem_type, global_max_y)} (src {src_y_txt})\n")
                rf.write(f"REF: F1_ref=0.99*peorF1={fmt_f1(problem_type, ref1_x)} | "
                        f"F2_ref=1.001*peorF2={fmt_f2(problem_type, ref1_y)}\n")
                rf.write(f"PUNTO REF: {fmt_ref(problem_type, ref1_x, ref1_y)}\n\n")


                # [3]
                rf.write("[3] RESUMEN PROMEDIO (Por Run)\n")
                rf.write(f"{'metodo':<8}{'T.Ejec(s)':>12}{'HV1':>18}{'HV2':>18}{'HV3':>18}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'AMPL':<8}{fmt_float(ampl_te,12,4)}{fmt_float(ampl_hv1,18,6)}{fmt_float(ampl_hv2,18,6)}{fmt_float(ampl_hv3,18,6)}\n")
                rf.write(f"{'MOEAD':<8}{fmt_float(moead_te,12,4)}{fmt_float(moead_hv1,18,6)}{fmt_float(moead_hv2,18,6)}{fmt_float(moead_hv3,18,6)}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'GAP%':<8}{fmt_gap_only(g_te):>12}{fmt_gap_only(g_hv1):>18}{fmt_gap_only(g_hv2):>18}{fmt_gap_only(g_hv3):>18}\n")
                rf.write(f"{'WINNER':<8}{w_time:>12}{w_hv:>18}\n")

                rf.write("\n")

                # [4]
                rf.write("[4] COMPARACIÓN BEST FRONTS (Unificados)\n")
                rf.write(f"{'metodo':<8}{'ND':>12}{'HV':>18}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'AMPL':<8}{fmt_int(n_a,12)}{fmt_float(h_a,18,6)}\n")
                rf.write(f"{'MOEAD':<8}{fmt_int(n_m,12)}{fmt_float(h_m,18,6)}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'GAP%':<8}{fmt_gap_only(g_nd):>12}{fmt_gap_only(g_hv_best):>18}\n")
                rf.write(f"{'WINNER':<8}{w_nd:>12}{w_hvt:>18}\n")

                rf.write("\n" + ("-" * 60) + "\n\n")
   
        else:
            print("      [!] No se generaron datos para ninguna run.")

    # ==========================================================
    # RESUMEN FINAL EN TABLA
    # ==========================================================
    print("\n========================================================================================================================================================\n")
    print(" RESUMEN FINAL (por instancia)")
    print("========================================================================================================================================================\n")

    summary_lines = []

    if not summary_rows:
        msg = "No hay filas para resumir (no se procesó ninguna instancia con datos)."
        print(msg)
        summary_lines.append(msg)
    else:
        # Formato fijo
        header = (
            f"{'INSTANCIA':<{W_INST}}"
            f"{'ESC':<6}"
            f"{'HV_AMPL':>{W_HV}}{'HV_MOEAD':>{W_HV}}{'GAP_HV':>{W_GAP}}{'WIN_HV':>{W_WIN}}"
            f"{'TE_AMPL':>{W_TE}}{'TE_MOEAD':>{W_TE}}{'GAP_TE':>{W_GAP}}{'WIN_TE':>{W_WIN}}"
        )


        summary_lines = []

        print(header)
        print("-" * len(header))

        summary_lines.append(header)
        summary_lines.append("-" * len(header))


        # Conteos “victorias” (solo AMPL/MOEAD; empates y '-' aparte si quieres)
        hv_w_ampl = 0
        hv_w_moead = 0
        te_w_ampl = 0
        te_w_moead = 0

        for r in summary_rows:
            def row_hv(inst_disp, esc_label, hv_a, hv_m, te_a_txt="", te_m_txt="", gap_te_txt="", win_te_txt=""):
                gap_hv = gap_pct(hv_a, hv_m)
                win_hv = winner_max(hv_a, hv_m)

                # texto HV
                hv_a_txt = "-" if pd.isna(hv_a) else f"{hv_a:.6f}"
                hv_m_txt = "-" if pd.isna(hv_m) else f"{hv_m:.6f}"

                # celdas HV base
                hv_a_cell = cell(hv_a_txt, W_HV)
                hv_m_cell = cell(hv_m_txt, W_HV)

                # marcar ganador HV con ( ... )
                if win_hv == "AMPL" and hv_a_txt != "-":
                    hv_a_cell = mark_winner_cell(hv_a_txt, W_HV)
                elif win_hv == "MOEAD" and hv_m_txt != "-":
                    hv_m_cell = mark_winner_cell(hv_m_txt, W_HV)

                # tiempo (solo si viene)
                te_a_cell = cell(te_a_txt, W_TE)
                te_m_cell = cell(te_m_txt, W_TE)

                # marcar ganador tiempo con ( ... )  (solo si hay texto)
                if te_a_txt != "-" and te_a_txt != "" and te_m_txt != "-" and te_m_txt != "" and win_te_txt:
                    if win_te_txt == "AMPL":
                        te_a_cell = maybe_bold(cell(f"({te_a_txt})", W_TE))
                    elif win_te_txt == "MOEAD":
                        te_m_cell = maybe_bold(cell(f"({te_m_txt})", W_TE))

                line = (
                    f"{inst_disp:<{W_INST}}"
                    f"{esc_label:<6}"
                    f"{hv_a_cell}{hv_m_cell}"
                    f"{cell(fmt_gap_only(gap_hv), W_GAP)}{win_hv:>{W_WIN}}"
                    f"{te_a_cell}{te_m_cell}"
                    f"{cell(gap_te_txt, W_GAP)}{win_te_txt:>{W_WIN}}"
                )
                return line


            inst_disp = r["inst_disp"]

            te_a_txt = fmt_seconds_with_minutes(r["te_a"], 4, 2)
            te_m_txt = fmt_seconds_with_minutes(r["te_m"], 4, 2)
            gap_te_txt = fmt_gap_only(r["gap_te"])
            win_te_txt = r["win_te"]

            print(row_hv(inst_disp, "HV1", r["hv1_a"], r["hv1_m"], te_a_txt, te_m_txt, gap_te_txt, win_te_txt))
            print(row_hv(inst_disp, "HV2", r["hv2_a"], r["hv2_m"]))  # sin tiempo
            print(row_hv(inst_disp, "HV3", r["hv3_a"], r["hv3_m"]))  # sin tiempo

            print("-" * len(header))



        wins_line = (
            f"{'WINS':<{W_INST}}"
            f"{hv_w_ampl:>{W_HV}}{hv_w_moead:>{W_HV}}{'':>{W_WIN}}"
            f"{te_w_ampl:>{W_TE}}{te_w_moead:>{W_TE}}{'':>{W_WIN}}"
        )
        print("-" * len(header))
        print(wins_line)

        summary_lines.append("-" * len(header))
        summary_lines.append(strip_ansi(wins_line))
    print("========================================================================================================================================================\n")

    with open(report_path, "a", encoding="utf-8") as rf:
        rf.write("\n")
        rf.write("====================================\n")
        rf.write("RESUMEN FINAL (por instancia)\n")
        rf.write("====================================\n")
        rf.write("\n".join(summary_lines))
        rf.write("\n")




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--instancia', type=str, default=None)
    parser.add_argument('--tipo', type=str, default="cam")

    parser.add_argument('--outliers', type=str, default="none", choices=["none","iqr","pctl","cap"])
    parser.add_argument('--outlier_k', type=float, default=1.5)       # para iqr
    parser.add_argument('--outlier_q', type=float, default=0.99)      # para pctl
    parser.add_argument('--outlier_cap', type=float, default=None)    # para cap (F2 > cap)
    parser.add_argument('--ref_ignore_outliers', action='store_true') # si quieres escenario B


    args = parser.parse_args()
    
    procesar_instancias(args.tipo, args.instancia, args)