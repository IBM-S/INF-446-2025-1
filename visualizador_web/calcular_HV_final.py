
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
BOLD_WINNERS = True   # <- prende/apaga negritas en el compacto

def bold_latex(s: str) -> str:
    # s debe ser el string ya formateado (ej: "60.06")
    return rf"$\mathbf{{{s}}}$"

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
    return sorted(unique_points, key=lambda x: x[0])

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

def get_max_from_points(points_list):
    """Auxiliar para sacar maximos de una lista de puntos en memoria [[x,y], ...]"""
    if not points_list:
        return None, None
    mx = -1e30
    my = -1e30
    for p in points_list:
        if p[0] > mx: mx = p[0]
        if p[1] > my: my = p[1]
    return mx, my

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

def fmt_gap_only(v):
    return f"{v:+.4f}%" if pd.notna(v) else "-"

def fmt_float(v, w=12, d=4):
    return f"{v:>{w}.{d}f}" if pd.notna(v) else f"{'-':>{w}}"

def fmt_int(v, w=12):
    try:
        return f"{int(v):>{w}d}"
    except:
        return f"{'-':>{w}}"

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

def fmt_seconds_only(sec, dec_s=4):
    """Devuelve: "12.3456 s". Si sec es NaN -> "-" """
    if sec is None or (isinstance(sec, float) and np.isnan(sec)):
        return "-"
    try:
        s = float(sec)
    except:
        return "-"
    return f"{s:,.{dec_s}f}"

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

# eliminar
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

    if a_miss and m_miss: return "-"          # ninguno
    if a_miss and not m_miss: return "MOEAD"      # solo MOEAD tiene
    if m_miss and not a_miss: return "AMPL"       # solo AMPL tiene

    if abs(ampl - moead) <= tol:
        return "EMPATE"
    return "AMPL" if ampl < moead else "MOEAD"

def winner_max(ampl, moead, tol=1e-12):
    """Gana el mayor (HV, ND). Si uno no tiene dato, gana el que sí tiene."""
    a_miss = _is_missing(ampl)
    m_miss = _is_missing(moead)

    if a_miss and m_miss: return "-"
    if a_miss and not m_miss: return "MOEAD"
    if m_miss and not a_miss: return "AMPL"

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
    moead_folder = args.moead_subdir if args.moead_subdir else problem_type
    path_moead_base = os.path.join(DIR_MOEAD, moead_folder)

    suffix = f"{args.moead_subdir}" if args.moead_subdir else ""
    
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
    report_path = os.path.join(BASE_DIR, f"final_reporte_{problem_type}_resumen_{suffix}.txt")
    # Si estás analizando todas las instancias, lo reiniciamos
    if target_instance is None:
        with open(report_path, "w", encoding="utf-8") as rf:
            rf.write(f"REPORTE RESUMEN - TIPO {problem_type.upper()}\n\n")

    processed = 0
    summary_rows = []  # una fila por instancia (HV best + T.Ejec promedio)

    Width_ND = 18

    if problem_type.lower() == "cam":
        W_INST = 24
        W_REF_X = 14
        W_REF_Y = 14       
        W_HV   = 24    
        W_GAP  = 12          
        W_TE   = 32        
        W_WIN  = 12
    else:  # drp
        W_INST = 16
        W_REF_X = 14
        W_REF_Y = 14       
        W_HV   = 20    
        W_GAP  = 12          
        W_TE   = 32        
        W_WIN  = 12

    FACTOR_F1 = 0.99
    FACTOR_F2 = 1.001


    for inst in todas_instancias:
        if target_instance and inst != target_instance: continue
        
        print(f"\n>>> Procesando: {inst}")
        out_dir = os.path.join(DIR_ANALISIS, moead_folder, inst)
        os.makedirs(out_dir, exist_ok=True)

        # ---------------------------------------------------------
        # 1. LECTURA DE DATOS RAW Y PUNTOS EXTREMOS
        # ---------------------------------------------------------
        print("  [1] Análisis de Puntos Extremos (Nadir)")
        
        # A. AMPL (Solo tiene un resultado final, se usa para ambos referencias)
        max_x_ampl, max_y_ampl, all_ampl_points = None, None, []
        path_inst_ampl = os.path.join(path_ampl_base, inst)

        t_scan_ampl = 0.0
        if os.path.exists(path_inst_ampl):
            t0 = time.time()
            ampl_files = glob.glob(os.path.join(path_inst_ampl, "run_*", "pareto_front.txt"))
            max_x_ampl, max_y_ampl, all_ampl_points = get_max_values_and_points(ampl_files)
            t_scan_ampl = time.time() - t0
            
            if max_x_ampl is not None:
                print(f"      -> AMPL  : F1={fmt_f1(problem_type, max_x_ampl)}, F2={fmt_f2(problem_type, max_y_ampl)} (Scan: {t_scan_ampl:.4f}s)")
            else:
                print(f"      -> AMPL  : Carpeta existe pero sin puntos válidos.")
        else:
            print(f"      -> AMPL  : No existe carpeta de resultados.")

        # B. MOEAD (Historial para Ref Global, Best Fronts para Ref Final)
        max_x_moead_runs, max_y_moead_runs = None, None
        all_moead_final_points = []
        path_inst_moead = os.path.join(path_moead_base, inst)
        
        # Para el máximo global buscamos en TODO el historial (POF_*.dat)
        # Para el Best Front solo usaremos pareto_front.txt

        t_scan_moead_hist = 0.0
        t_scan_moead_final = 0.0
        
        if os.path.exists(path_inst_moead):
            t0 = time.time()
            # 1. Busqueda de maximos en historial
            moead_last_gens = glob.glob(os.path.join(path_inst_moead, "run_*", f"last_gen_{inst}.dat"))
            max_x_moead_runs, max_y_moead_runs, _ = get_max_values_and_points(moead_last_gens)
            t_scan_moead_hist = time.time() - t0
            
            # 2. Puntos Finales (Para Best Front y Ref Final)
            t1 = time.time()
            moead_final_files = glob.glob(os.path.join(path_inst_moead, "run_*", "pareto_front.txt"))
            _, _, all_moead_final_points = get_max_values_and_points(moead_final_files)
            t_scan_moead_final = time.time() - t1

            if max_x_moead_runs is not None:
                print(f"      -> MOEAD : F1={fmt_f1(problem_type, max_x_moead_runs)}, F2={fmt_f2(problem_type, max_y_moead_runs)} (Scan: {t_scan_moead_hist:.4f}s)")
            else:
                print(f"      -> MOEAD : Carpeta existe pero sin puntos válidos.")
        else:
            print(f"      -> MOEAD : No existe carpeta de resultados.")

        # ---------------------------------------------------------
        # 2. CALCULO DE DOS PUNTOS DE REFERENCIA
        # ---------------------------------------------------------
        # A) REF GLOBAL (Basado en el peor de todas las runs individuales)
        valid_x_glob = [v for v in [max_x_ampl, max_x_moead_runs] if v is not None]
        valid_y_glob = [v for v in [max_y_ampl, max_y_moead_runs] if v is not None]

        if not valid_x_glob or not valid_y_glob:
            print("      [!] Sin datos en ningún método. Saltando instancia.")
            continue

        g_worst_x = max(valid_x_glob)
        g_worst_y = max(valid_y_glob)

        src_x = "AMPL/MOEAD" if (max_x_ampl is not None and max_x_moead_runs is not None and abs(max_x_ampl - max_x_moead_runs) < 1e-12) \
        else ("AMPL" if (max_x_ampl is not None and abs(g_worst_x - max_x_ampl) < 1e-12) else "MOEAD")
        src_y = "AMPL/MOEAD" if (max_y_ampl is not None and max_y_moead_runs is not None and abs(max_y_ampl - max_y_moead_runs) < 1e-12) \
                else ("AMPL" if (max_y_ampl is not None and abs(g_worst_y - max_y_ampl) < 1e-12) else "MOEAD")

        ref_x_global = g_worst_x * FACTOR_F1
        ref_y_global = g_worst_y * FACTOR_F2
        if (ref_x_global == 0.0):
            ref_x_global = 0.1

        print(f"      -> peor F1 = {fmt_f1(problem_type, g_worst_x)}  (desde {src_x})")
        print(f"      -> peor F2 = {fmt_f2(problem_type, g_worst_y)}  (desde {src_y})")
        print(f"      -> PUNTO REF_GLOBAL: F1_ref = {FACTOR_F1} * peorF1 = {FACTOR_F1} * {fmt_f1(problem_type, g_worst_x)} = {fmt_f1(problem_type, ref_x_global)}; "
            f"F2_ref = {FACTOR_F2} * peorF2 = {FACTOR_F2} * {fmt_f2(problem_type, g_worst_y)} = {fmt_f2(problem_type, ref_y_global)}")
        print(f"      -> REF GLOBAL (para Runs/Promedio): {fmt_ref(problem_type, ref_x_global, ref_y_global)}")


        # B) REF FINAL
        t2 = time.time()
        ampl_best = filter_nondominated(all_ampl_points)
        moead_best = filter_nondominated(all_moead_final_points)
        t_scan_best = time.time() - t2

        mx_a_best, my_a_best = get_max_from_points(ampl_best)
        mx_m_best, my_m_best = get_max_from_points(moead_best)

        print("\n")
        print(f"      -> AMPL BestFront : peorF1={fmt_f1(problem_type, mx_a_best) if mx_a_best is not None else '-'} "
            f"peorF2={fmt_f2(problem_type, my_a_best) if my_a_best is not None else '-'} (Scan: {t_scan_best:.4f}s)")
        print(f"      -> MOEAD BestFront: peorF1={fmt_f1(problem_type, mx_m_best) if mx_m_best is not None else '-'} "
            f"peorF2={fmt_f2(problem_type, my_m_best) if my_m_best is not None else '-'} (Scan: {t_scan_moead_final:.4f}s)")

        valid_x_final = [v for v in [mx_a_best, mx_m_best] if v is not None]
        valid_y_final = [v for v in [my_a_best, my_m_best] if v is not None]

        if valid_x_final and valid_y_final:
            f_worst_x = max(valid_x_final)
            f_worst_y = max(valid_y_final)

            src_x2 = "AMPL/MOEAD" if (mx_a_best is not None and mx_m_best is not None and abs(mx_a_best - mx_m_best) < 1e-12) \
                    else ("AMPL" if (mx_a_best is not None and abs(f_worst_x - mx_a_best) < 1e-12) else "MOEAD")
            src_y2 = "AMPL/MOEAD" if (my_a_best is not None and my_m_best is not None and abs(my_a_best - my_m_best) < 1e-12) \
                    else ("AMPL" if (my_a_best is not None and abs(f_worst_y - my_a_best) < 1e-12) else "MOEAD")

            ref_x_final = f_worst_x * FACTOR_F1
            ref_y_final = f_worst_y * FACTOR_F2

            if ref_x_final == 0.0:
                ref_x_final = 0.1

            print(f"      -> peor F1 = {fmt_f1(problem_type, f_worst_x)}  (desde {src_x2})")
            print(f"      -> peor F2 = {fmt_f2(problem_type, f_worst_y)}  (desde {src_y2})")
            print(f"      -> PUNTO REF_FINAL: F1_ref = {FACTOR_F1} * peorF1 = {FACTOR_F1} * {fmt_f1(problem_type, f_worst_x)} = {fmt_f1(problem_type, ref_x_final)}; "
                f"F2_ref = {FACTOR_F2} * peorF2 = {FACTOR_F2} * {fmt_f2(problem_type, f_worst_y)} = {fmt_f2(problem_type, ref_y_final)}")
            print(f"      -> REF FINAL (para Best Fronts): {fmt_ref(problem_type, ref_x_final, ref_y_final)}")
        else:
            ref_x_final, ref_y_final = ref_x_global, ref_y_global
            print(f"      -> REF FINAL: Usando Global (sin best fronts validos)")

        dec_x_config = f1_dec(problem_type)
        dec_y_best_config = 1 if is_drp(problem_type) else 0

        with open(os.path.join(out_dir, "reference_point_global.txt"), "w") as f:
            f.write(f"{ref_x_global:.{dec_x_config}f} {ref_y_global:.3f}\n")

        with open(os.path.join(out_dir, "reference_point_final.txt"), "w") as f:
            f.write(f"{ref_x_final:.{dec_x_config}f} {ref_y_final:.3f}\n")


        # GUARDAR BEST FRONTS (Si existen puntos)
        if ampl_best: save_points_to_file(ampl_best, os.path.join(out_dir, "best_front_ampl.txt"), dec_x=dec_x_config, dec_y=dec_y_best_config)
        if moead_best: save_points_to_file(moead_best, os.path.join(out_dir, "best_front_moead.txt"), dec_x=dec_x_config, dec_y=dec_y_best_config)

        print(f"      -> Best Fronts: AMPL ({len(ampl_best)} pts), MOEAD ({len(moead_best)} pts)")

        # ---------------------------------------------------------
        # 3. CÁLCULO DE MÉTRICAS INDIVIDUALES (USANDO REF GLOBAL) es decir los peores objetivos de las runs
        # ---------------------------------------------------------
        # 3.1 Promedios de MOEA/D con Ref Global
        print("\n  [2] Calculando Métricas MOEA/D por Run (REF GLOBAL)")
        final_data = []  
        moead_hv_runs_global = []
        moead_times = []

        if os.path.exists(path_inst_moead):
            times_dict = get_execution_times(path_inst_moead)
            run_folders = sorted(glob.glob(os.path.join(path_inst_moead, "run_*")), key=lambda x: int(os.path.basename(x).split('_')[1] if '_' in os.path.basename(x) else 99999))

            for rf in run_folders:
                try : run_id = int(os.path.basename(rf).split('_')[1])
                except: continue

                pareto_file = os.path.join(rf, "pareto_front.txt")
                points = read_points(pareto_file)
                clean_points = filter_nondominated(points)

                # HV Run individual con ref global
                temp = os.path.join(out_dir, f"temp_moead_glob_{run_id}.dat")
                hv_val = calculate_hv_transparent(clean_points, (ref_x_global, ref_y_global), temp)

                t = times_dict.get(run_id, np.nan)
                if pd.notna(t): moead_times.append(t)

                moead_hv_runs_global.append(hv_val)
                final_data.append({"metodo": "MOEAD", "run_id": run_id, "time_ejec": t, "nd_points": len(clean_points), "hv": hv_val})
                print(f"      -> MOEAD Run {run_id:<2} OK. HV={hv_val:.6f}")
        
        hv_moead_avg_global = np.mean(moead_hv_runs_global) if moead_hv_runs_global else np.nan
        te_moead_avg = np.mean(moead_times) if moead_times else np.nan
        te_moead_total = np.sum(moead_times) if moead_times else np.nan

        # 3.2 Tiempos AMPL
        ampl_times = []
        if os.path.exists(path_inst_ampl):
            times_dict_a = get_execution_times(path_inst_ampl)
            ampl_times = [v for v in times_dict_a.values() if pd.notna(v)]

        te_ampl_avg = np.mean(ampl_times) if ampl_times else np.nan


        # 3.3 Best Fronts con Ref Global
        temp_bf_a_g = os.path.join(out_dir, "temp_best_ampl_glob.dat")
        hv_ampl_best_global = calculate_hv_transparent(ampl_best, (ref_x_global, ref_y_global), temp_bf_a_g)

        temp_bf_m_g = os.path.join(out_dir, "temp_best_moead_glob.dat")
        hv_moead_best_global = calculate_hv_transparent(moead_best, (ref_x_global, ref_y_global), temp_bf_m_g)


        print(f"      -> HV(AMPL) Glob:      {hv_ampl_best_global:.6f}")
        print(f"      -> HV(MOEA Best) Glob: {hv_moead_best_global:.6f}")
        #print(f"      -> HV(MOEA Avg) Glob:  {hv_moead_avg_global:.6f}")

         # ---------------------------------------------------------
        # 4. CÁLCULO DE MÉTRICAS - TABLA 2 (REF FINAL)
        # ---------------------------------------------------------
        # Aquí solo recalculamos Best Fronts con Ref Final

        temp_bf_a_f = os.path.join(out_dir, "temp_best_ampl_final.dat")
        hv_ampl_best_final = calculate_hv_transparent(ampl_best, (ref_x_final, ref_y_final), temp_bf_a_f)

        temp_bf_m_f = os.path.join(out_dir, "temp_best_moead_final.dat")
        hv_moead_best_final = calculate_hv_transparent(moead_best, (ref_x_final, ref_y_final), temp_bf_m_f)

        #print(f"      -> HV(AMPL) Fin:        {hv_ampl_best_final:.6f}")
        #print(f"      -> HV(MOEA Best) Fin:   {hv_moead_best_final:.6f}")

                
        # Guardar CSV detallado (incluso si solo hay datos de uno)
        if final_data:
            df = pd.DataFrame(final_data)
            csv_out = os.path.join(out_dir, "final_summary_global_ref.csv")
            df.to_csv(csv_out, index=False)

            
            # --- PROMEDIOS (Usando Ref Global) ---
            resumen = df.groupby("metodo")[["time_ejec", "hv"]].mean()

            def safe_get(method, col):
                return float(resumen.loc[method, col]) if method in resumen.index and pd.notna(resumen.loc[method, col]) else np.nan

            ampl_te  = te_ampl_avg
            moead_te = te_moead_avg
            #hv promedio (ref global) 
            ampl_hv_avg  = hv_ampl_best_global
            moead_hv_avg = hv_moead_avg_global

            print(f"\n  [3] RESUMEN PROMEDIO (Ref global {fmt_ref(problem_type, ref_x_global, ref_y_global)}):")
            print("-" * 75)
            print(f"{'metodo':<10} {'T. Ejec prom':<15} {'HV Promedio':<15}")
            print("-" * 75)
            print(f"{'AMPL':<10} {fmt_float(ampl_te,4):<15} {fmt_float(ampl_hv_avg,4):<15}")
            print(f"{'MOEAD':<10} {fmt_float(moead_te,4):<15} {fmt_float(moead_hv_avg,4):<15}")
            print("-" * 75)

            # fila GAP (con tu fórmula AMPL-MOEAD sobre AMPL)
            g_te  = gap_pct(ampl_te, moead_te)
            g_hv_avg  = gap_pct(ampl_hv_avg, moead_hv_avg)

            print(f"{'GAP%':<10} {fmt_gap_only(g_te):<15} {fmt_gap_only(g_hv_avg):<15}")
            print("-" * 75)

            win_te = winner_min(ampl_te, moead_te)
            win_hv_avg = winner_max(ampl_hv_avg, moead_hv_avg)

            print(f"{'WINNER':<10} {win_te:<15} {win_hv_avg:<15}")
            print("-" * 75)

            # --- TABLA 2: BEST FRONTS (usnado ref final) ---
            print(f"\n  [4] COMPARACIÓN DE BEST FRONTS (Ref Final {fmt_ref(problem_type, ref_x_final, ref_y_final)}):")
            print("-" * 75)
            print(f"{'metodo':<10} {'nd_points':<15} {'HV Best (Fin)':<15}")
            print("-" * 75)

            n_a, h_a_best = print_best_row("AMPL", ampl_best, (ref_x_final, ref_y_final), out_dir)
            n_m, h_m_best = print_best_row("MOEAD", moead_best, (ref_x_final, ref_y_final), out_dir)

            # ======= Fila para resumen final =======
            win_hv_best = winner_max(h_a_best, h_m_best)          # HV best front: mayor es mejor

            # Conteos de victorias
            win_hv_glob_best = winner_max(hv_ampl_best_global, hv_moead_best_global)
            win_te = winner_min(te_ampl_avg, te_moead_avg)

            summary_rows.append({
                "inst": inst,
                "inst_disp": display_inst_name(inst),

                # refs
                "ref_global": (ref_x_global, ref_y_global),
                "ref_final":  (ref_x_final,  ref_y_final),

                # HV con ref_global (para RESUMEN FINAL)
                "hv_ampl_global": ampl_hv_avg,                 # tu "HV(AMPL) Glob"
                "hv_moead_best_global": hv_moead_best_global,     # tu "HV(MOEA Best) Glob"
                "hv_moead_avg_global": hv_moead_avg_global,       # tu "HV(MOEA Avg) Glob"

                # HV con ref_final (para RESUMEN FINAL FINAL)
                "hv_ampl_best_final": hv_ampl_best_final,                   # tu "HV(AMPL) Fin"
                "hv_moead_best_final": hv_moead_best_final,       # tu "HV(MOEA Best) Fin"

                # ND best fronts finales
                "nd_ampl_best_final": n_a,
                "nd_moead_best_final": n_m,

                # tiempos (promedios)
                "te_ampl": te_ampl_avg,
                "te_moead": te_moead_avg,
                "te_moead_total": te_moead_total
            })



            processed += 1

            g_nd = gap_pct(float(n_a), float(n_m))
            g_hv_best = gap_pct(h_a_best, h_m_best)

            print("-" * 75)
            print(f"{'GAP%':<10} {fmt_gap_only(g_nd):<15} {fmt_gap_only(g_hv_best):<15}")
            print("-" * 75)
            w_nd  = winner_max(float(n_a), float(n_m))
            w_hvt = winner_max(h_a_best, h_m_best)

            print(f"{'WINNER':<10} {w_nd:<15} {w_hvt:<15}")
            print("-" * 75)


            # Guardar metrics de Best Fronts
            best_csv = os.path.join(out_dir, "best_fronts_metrics.csv")
            with open(best_csv, 'w') as f:
                f.write("metodo,nd_points,hv_total\n")
                if ampl_best: f.write(f"AMPL,{n_a},{h_a_best}\n")
                if moead_best: f.write(f"MOEAD,{n_m},{h_m_best}\n")
            

            with open(report_path, "a", encoding="utf-8") as rf:
                rf.write(f"INSTANCIA: {inst}\n")

                rf.write("[1] ANALISIS PUNTOS (Nadir)\n")
                rf.write(f"Ref Global (Runs): {fmt_ref(problem_type, ref_x_global, ref_y_global)}\n")
                rf.write(f"Ref Final (Best Fronts): {fmt_ref(problem_type, ref_x_final, ref_y_final)}\n\n")

                rf.write("[3] RESUMEN PROMEDIO (Ref Global)\n")
                rf.write(f"{'metodo':<8}{'T.Ejec(s)':>12}{'HV Avg':>18}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'AMPL':<8}{fmt_float(ampl_te,12,4)}{fmt_float(ampl_hv_avg,18,6)}\n")
                rf.write(f"{'MOEAD':<8}{fmt_float(moead_te,12,4)}{fmt_float(moead_hv_avg,18,6)}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'GAP%':<8}{fmt_gap_only(g_te):>12}{fmt_gap_only(g_hv_avg):>18}\n")
                rf.write(f"{'WINNER':<8}{win_te:>12}{win_hv_avg:>18}\n")


                rf.write("\n")

                rf.write("[4] COMPARACIÓN BEST FRONTS (Ref Final)\n")
                rf.write(f"{'metodo':<8}{'ND':>12}{'HV Best':>18}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'AMPL':<8}{fmt_int(n_a,12)}{fmt_float(h_a_best,18,6)}\n")
                rf.write(f"{'MOEAD':<8}{fmt_int(n_m,12)}{fmt_float(h_m_best,18,6)}\n")
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
    summary2_lines = []

    if not summary_rows:
        print("No hay filas para resumir (no se procesó ninguna instancia con datos).")
    else:
        # Formato fijo
        header = (
            f"{'Instance':<{W_INST}}{'Nd(AMPL)':>{Width_ND}}{'NdAg(MOEA/D)':>{Width_ND}}"
            f"{'ref_glob_1':>{W_REF_X}}{'ref_global_2':>{W_REF_Y}}"
            f"{'HvBest(AMPL)':>{W_HV}}{'AgHvBest(MOEA/D)':>{W_HV}}{'AvHv(MOEA/D)':>{W_HV}}{'GAP_HvBest':>{W_GAP}}{'WIN_HvBest':>{W_WIN}}"
            f"{'TE_PROM_AMPL':>{W_TE}}{'TE_PROM_MOEAD':>{W_TE}}{'GAP_TE':>{W_GAP}}{'WIN_TE':>{W_WIN}}"
        )

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
            inst_disp = r["inst_disp"]

            # puntos ND best fronts finales
            n_a_final = r["nd_ampl_best_final"]
            n_m_final = r["nd_moead_best_final"]

            nd_a_cell = cell(str(n_a_final), Width_ND)
            nd_m_cell = cell(str(n_m_final), Width_ND)

            # referencia global para mostrar
            rgx, rgy = r["ref_global"]

            # hvs usando punto global
            hv_a     = r["hv_ampl_global"]
            hv_best  = r["hv_moead_best_global"]
            hv_avg   = r["hv_moead_avg_global"]

            g_hv = gap_pct(hv_a, hv_best)
            win_hv = winner_max(hv_a, hv_best)

            # contar wins HV
            if win_hv == "AMPL": hv_w_ampl += 1
            elif win_hv == "MOEAD": hv_w_moead += 1

            te_a = r["te_ampl"]
            te_m = r["te_moead"]
            g_te = gap_pct(te_a, te_m)
            win_te = winner_min(te_a, te_m) 

            if win_te == "AMPL": te_w_ampl += 1
            elif win_te == "MOEAD": te_w_moead += 1
            
            ## Ref X/Y
            ref_x_txt = "-" if _is_missing(rgx) else fmt_f1(problem_type, float(rgx))
            ref_y_txt = "-" if _is_missing(rgy) else fmt_f2(problem_type, float(rgy))
            ref_x_cell = cell(ref_x_txt, W_REF_X)
            ref_y_cell = cell(ref_y_txt, W_REF_Y)

            # --- HV base (sin paréntesis todavía)
            hv_a_txt = "-" if pd.isna(hv_a) else f"{hv_a:.6f}"
            hv_m_txt = "-" if pd.isna(hv_best) else f"{hv_best:.6f}"
            hv_prom_m_txt = "-" if pd.isna(hv_avg) else f"{hv_avg:.6f}"

            hv_a_cell = cell(hv_a_txt, W_HV)
            hv_m_cell = cell(hv_m_txt, W_HV)
            hv_prom_m_cell = cell(hv_prom_m_txt, W_HV)

            # marcar ganador HV con ( ... ) usando ancho fijo
            if win_hv == "AMPL" and hv_a_txt != "-":
                hv_a_cell = mark_winner_cell(hv_a_txt, W_HV)
            elif win_hv == "MOEAD" and hv_m_txt != "-":
                hv_m_cell = mark_winner_cell(hv_m_txt, W_HV)

            gap_hv_cell = cell(fmt_gap_only(g_hv), W_GAP)

            # --- Tiempo con minutos
            te_a_txt = fmt_seconds_with_minutes(te_a, dec_s=4, dec_m=2)
            te_m_txt = fmt_seconds_with_minutes(te_m, dec_s=4, dec_m=2)

            te_a_cell = cell(te_a_txt, W_TE)
            te_m_cell = cell(te_m_txt, W_TE)

            # marcar ganador de tiempo (también con paréntesis)
            # OJO: aquí el paréntesis encapsula el texto completo "xx s (yy min)"
            if win_te == "AMPL" and te_a_txt != "-":
                te_a_cell = maybe_bold(cell(f"({te_a_txt})", W_TE))
            elif win_te == "MOEAD" and te_m_txt != "-":
                te_m_cell = maybe_bold(cell(f"({te_m_txt})", W_TE))

            gap_te_cell = cell(fmt_gap_only(g_te), W_GAP)

            line = (
                f"{inst_disp:<{W_INST}}{nd_a_cell}{nd_m_cell}"
                f"{ref_x_cell}{ref_y_cell}"
                f"{hv_a_cell}{hv_m_cell}{hv_prom_m_cell}{gap_hv_cell}{win_hv:>{W_WIN}}"
                f"{te_a_cell}{te_m_cell}{gap_te_cell}{win_te:>{W_WIN}}"
            )

            print(line)
            summary_lines.append(strip_ansi(line))


        wins_line = (
            f"{'WINS':<{W_INST}}"
            f"{'':>{Width_ND}}{'':>{Width_ND}}"
            f"{'':>{W_REF_X}}{'':>{W_REF_Y}}"
            f"{str(hv_w_ampl):>{W_HV}}"      # HV wins AMPL bajo HvBest(AMPL)
            f"{str(hv_w_moead):>{W_HV}}"     # HV wins MOEAD bajo AgHvBest(MOEA/D)
            f"{'':>{W_HV}}"                  # AvHv(MOEA/D) vacío
            f"{'':>{W_GAP}}"
            f"{'':>{W_WIN}}"
            f"{str(te_w_ampl):>{W_TE}}"      # TE wins AMPL bajo TE_AMPL
            f"{str(te_w_moead):>{W_TE}}"     # TE wins MOEAD bajo TE_MOEAD
            f"{'':>{W_GAP}}"
            f"{'':>{W_WIN}}"
        )

        print("-" * len(header))
        print(wins_line)

        summary_lines.append("-" * len(header))
        summary_lines.append(strip_ansi(wins_line))

        W_TE2 = 20
        print("\n")
        print(" RESUMEN FINAL FINAL (compacto)")
        print("=" * (W_INST + W_REF_X + W_REF_Y + W_HV*2 + W_GAP + W_WIN + W_TE2*2 + W_GAP + Width_ND*2))

        header2 = (
            f"{'Instance':<{W_INST}}{'Nd(AMPL)':>{Width_ND}}{'AgNd(MOEA/D)':>{Width_ND}}"
            f"{'$y_{ref1}$':>{W_REF_X}}{'$y_{ref2}$':>{W_REF_Y}}"
            f"{'Hv(AMPL)':>{W_HV}}{'AgHv(MOEA/D)':>{W_HV}}{'GapHv':>{W_GAP}}"
            f"{'Time[s](AMPL)':>{W_TE2}}{'AgTime[s](MOEA/D)':>{W_TE2}}{'GapTime':>{W_GAP}}"
        )

        # f"{'T [s] (AMPL)':>{W_TE2}}{'AgT [s] (MOEA/D)':>{W_TE2}}{'GapT':>{W_GAP}}"


        print(header2)
        print("-" * len(header2))

        summary2_lines.append(header2)
        summary2_lines.append("-" * len(header2))

        def fmt_gap_only_2(v):
            return f"{v:+.2f}%" if pd.notna(v) else "-"


        for r in summary_rows:
            inst_disp = r["inst_disp"]
            
            # puntos ND best fronts finales
            n_a_final_tabla2 = r["nd_ampl_best_final"]
            n_m_final_tabla2 = r["nd_moead_best_final"]

            nd_a_txt_tabla2 = "-" if pd.isna(n_a_final_tabla2) else f"{n_a_final_tabla2}"
            nd_m_txt_tabla2 = "-" if pd.isna(n_m_final_tabla2) else f"{n_m_final_tabla2}"

            rfx, rfy = r["ref_final"]

            hv_a_final     = r["hv_ampl_best_final"]
            hv_best_final  = r["hv_moead_best_final"]
            gap_hv_final   = gap_pct(hv_a_final, hv_best_final)
            te_a_2 = r["te_ampl"]
            te_m_sum = r["te_moead_total"]
            gap_te_final = gap_pct(te_a_2, te_m_sum)

            # Ref X/Y
            ref_x_txt = "-" if _is_missing(rfx) else f"{float(rfx):,.2f}"
            ref_y_txt = "-" if _is_missing(rfy) else f"{float(rfy):,.2f}"

            hv_a_txt = "-" if pd.isna(hv_a_final) else f"{float(hv_a_final):,.2f}"
            hv_m_txt = "-" if pd.isna(hv_best_final) else f"{float(hv_best_final):,.2f}"

            te_a_txt = fmt_seconds_only(te_a_2, dec_s=2)
            te_m_txt = fmt_seconds_only(te_m_sum, dec_s=2)

            def to_float_or_nan(x):
                try:
                    if x is None: 
                        return np.nan
                    if isinstance(x, str) and x.strip() == "-":
                        return np.nan
                    return float(x)
                except:
                    return np.nan

            if args.bold_winners:

                # ---------------- ND (mayor es mejor) ----------------
                nd_a_num = to_float_or_nan(n_a_final_tabla2)
                nd_m_num = to_float_or_nan(n_m_final_tabla2)

                if np.isfinite(nd_a_num) and np.isfinite(nd_m_num):
                    if nd_a_num > nd_m_num:
                        nd_a_txt_tabla2 = bold_latex(nd_a_txt_tabla2)
                    elif nd_m_num > nd_a_num:
                        nd_m_txt_tabla2 = bold_latex(nd_m_txt_tabla2)
                    else:
                        nd_a_txt_tabla2 = bold_latex(nd_a_txt_tabla2)
                        nd_m_txt_tabla2 = bold_latex(nd_m_txt_tabla2)

                # ---------------- HV (mayor es mejor) ----------------
                hv_a_num = to_float_or_nan(hv_a_final)
                hv_m_num = to_float_or_nan(hv_best_final)

                if np.isfinite(hv_a_num) and np.isfinite(hv_m_num):
                    if hv_a_num > hv_m_num:
                        hv_a_txt = bold_latex(hv_a_txt)
                    elif hv_m_num > hv_a_num:
                        hv_m_txt = bold_latex(hv_m_txt)
                    else:
                        hv_a_txt = bold_latex(hv_a_txt)
                        hv_m_txt = bold_latex(hv_m_txt)

                # ---------------- TIME (menor es mejor) ----------------
                te_a_num = to_float_or_nan(te_a_2)
                te_m_num = to_float_or_nan(te_m_sum)

                if np.isfinite(te_a_num) and np.isfinite(te_m_num):
                    if te_a_num < te_m_num:
                        te_a_txt = bold_latex(te_a_txt)
                    elif te_m_num < te_a_num:
                        te_m_txt = bold_latex(te_m_txt)
                    else:
                        te_a_txt = bold_latex(te_a_txt)
                        te_m_txt = bold_latex(te_m_txt)


            line2 = (
                f"{inst_disp:<{W_INST}}{cell(nd_a_txt_tabla2, Width_ND)}{cell(nd_m_txt_tabla2, Width_ND)}"
                f"{cell(ref_x_txt, W_REF_X)}{cell(ref_y_txt, W_REF_Y)}"
                f"{cell(hv_a_txt, W_HV)}{cell(hv_m_txt, W_HV)}{cell(fmt_gap_only_2(gap_hv_final), W_GAP)}"
                f"{cell(te_a_txt, W_TE2)}{cell(te_m_txt, W_TE2)}{cell(fmt_gap_only_2(gap_te_final), W_GAP)}"
            )

            print(line2)
            summary2_lines.append(strip_ansi(line2))

    print("========================================================================================================================================================\n")

    
    with open(report_path, "a", encoding="utf-8") as rf:
        rf.write("\n")
        rf.write("====================================\n")
        rf.write("RESUMEN FINAL (por instancia)\n")
        rf.write("====================================\n")
        if summary_lines:
            rf.write("\n".join(summary_lines))
            rf.write("\n")
        else:
            rf.write("(sin datos)\n")

        rf.write("\n")
        rf.write("====================================\n")
        rf.write("RESUMEN FINAL FINAL (compacto)\n")
        rf.write("====================================\n")
        if summary2_lines:
            rf.write("\n".join(summary2_lines))
            rf.write("\n")
        else:
            rf.write("(sin datos)\n")





if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--instancia', type=str, default=None)
    parser.add_argument('--tipo', type=str, default="cam")
    parser.add_argument("--moead_subdir", type=str, default=None, help="Subcarpeta dentro de raw_moead. Ej: cam_final. Si no se pasa, se usa --tipo (cam/drp).")
    parser.add_argument( "--bold_winners", action="store_true", help="Si se activa, pone en negrita (LaTeX \\mathbf{...}) a los ganadores en el RESUMEN FINAL FINAL."
)


    args = parser.parse_args()
    
    procesar_instancias(args.tipo, args.instancia, args)