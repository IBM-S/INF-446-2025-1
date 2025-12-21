
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

def save_points_to_file(points, filepath):
    with open(filepath, 'w') as f:
        for p in points:
            f.write(f"{p[0]:.10f} {p[1]:.10f}\n")

def calculate_hv_transparent(points, ref_point, temp_file_path):
    if not points: return 0.0, 0.0
    
    save_points_to_file(points, temp_file_path)
    ref_string = f"{ref_point[0]} {ref_point[1]}"
    cmd = [HV_EXEC, "-r", ref_string, temp_file_path]
    
    hv_start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        hv_duration = time.time() - hv_start
        if result.returncode != 0: return 0.0, hv_duration
        return float(result.stdout.strip()), hv_duration
    except: return 0.0, 0.0
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
        hv, t = calculate_hv_transparent(points, ref, temp_f)
        print(f"{name:<10} {len(points):<15} {hv:<15.4f} {t:<15.6f}")
        return len(points), hv, t
    else:
        print(f"{name:<10} {'-':<15} {'-':<15} {'-':<15}")
        return 0, 0.0, 0.0


# ================= MAIN =================

def procesar_instancias(problem_type="cam", target_instance=None):
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
    report_path = os.path.join(BASE_DIR, f"reporte_{problem_type}_resumen.txt")
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

    W_INST = 32
    W_HV   = 18   # sube a 18 si quieres
    W_TE   = 28   # para que quepa "123.4567 s (2.06 min)"
    W_WIN  = 12


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
                print(f"      -> AMPL  : F1={max_x_ampl:.4f}, F2={max_y_ampl:.4f} (Scan: {t_scan:.4f}s)")
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
                print(f"      -> MOEAD : F1={max_x_moead:.4f}, F2={max_y_moead:.4f} (Scan: {t_scan:.4f}s)")
            else:
                print(f"      -> MOEAD : Carpeta existe pero sin puntos válidos.")
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

        ref_x = global_max_x + (abs(global_max_x) * 0.01 if global_max_x != 0 else 0.1)
        ref_y = global_max_y + (abs(global_max_y) * 0.01 if global_max_y != 0 else 0.1)

        print(f"      -> PUNTO REF: ({ref_x:.4f}, {ref_y:.4f})")
        with open(os.path.join(out_dir, "reference_point.txt"), "w") as f:
            f.write(f"{ref_x} {ref_y}")

        # D. GUARDAR BEST FRONTS (Si existen puntos)
        ampl_best = filter_nondominated(all_ampl_points)
        if ampl_best:
            save_points_to_file(ampl_best, os.path.join(out_dir, "best_front_ampl.txt"))
        
        moead_best = filter_nondominated(all_moead_final_points)
        if moead_best:
            save_points_to_file(moead_best, os.path.join(out_dir, "best_front_moead.txt"))

        print(f"      -> Best Fronts: AMPL ({len(ampl_best)} pts), MOEAD ({len(moead_best)} pts)")

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
                        "nd_points": 0, "hv": 0.0, "time_hv": 0.0
                    })
                    continue

                clean_points = filter_nondominated(points)
                temp_file = os.path.join(out_dir, f"temp_{m_name}_{run_id}.dat")
                hv_val, hv_time = calculate_hv_transparent(clean_points, (ref_x, ref_y), temp_file)
                time_exec = times_dict.get(run_id, np.nan)
                
                print(f"OK. HV={hv_val:.4f}, Time HV={hv_time:.4f}")

                final_data.append({
                    "metodo": m_name,
                    "run": run_id,
                    "time_ejec": time_exec,
                    "nd_points": len(clean_points),
                    "hv": hv_val,
                    "time_hv": hv_time
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
            print("-" * 75)
            print(f"{'Metodo':<10} {'T. Ejec prom':<15} {'HV Promedio':<15} {'T. HV prom':<15}")
            print("-" * 75)

            resumen = df.groupby("metodo")[["time_ejec", "hv", "time_hv"]].mean()

            def safe_get(method, col):
                return float(resumen.loc[method, col]) if method in resumen.index and pd.notna(resumen.loc[method, col]) else np.nan

            ampl_te  = safe_get("AMPL", "time_ejec")
            moead_te = safe_get("MOEAD", "time_ejec")
            ampl_hv  = safe_get("AMPL", "hv")
            moead_hv = safe_get("MOEAD", "hv")
            ampl_thv = safe_get("AMPL", "time_hv")
            moead_thv= safe_get("MOEAD", "time_hv")

            def fmt_time(v, d=4): return f"{v:.{d}f} s" if pd.notna(v) else "-"
            def fmt_num(v, d=4):  return f"{v:.{d}f}" if pd.notna(v) else "-"
            def fmt_gap(v):       return f"{v:.4f} %" if pd.notna(v) else "-"

            # filas AMPL/MOEAD
            print(f"{'AMPL':<10} {fmt_time(ampl_te,4):<15} {fmt_num(ampl_hv,4):<15} {fmt_time(ampl_thv,6):<15}")
            print(f"{'MOEAD':<10} {fmt_time(moead_te,4):<15} {fmt_num(moead_hv,4):<15} {fmt_time(moead_thv,6):<15}")

            # fila GAP (con tu fórmula AMPL-MOEAD sobre AMPL)
            g_te  = gap_pct(ampl_te, moead_te)
            g_hv_avg  = gap_pct(ampl_hv, moead_hv)
            g_thv = gap_pct(ampl_thv, moead_thv)

            print("-" * 75)
            print(f"{'GAP%':<10} {fmt_gap(g_te):<15} {fmt_gap(g_hv_avg):<15} {fmt_gap(g_thv):<15}")
            print("-" * 75)

            w_time = winner_min(ampl_te, moead_te)
            w_hv   = winner_max(ampl_hv, moead_hv)
            w_thv  = winner_min(ampl_thv, moead_thv)

            print(f"{'WINNER':<10} {w_time:<15} {w_hv:<15} {w_thv:<15}")
            print("-" * 75)


            # --- TABLA 2: BEST FRONTS UNIFICADOS ---
            print(f"\n  [4] COMPARACIÓN DE BEST FRONTS (Frentes Unificados):")
            print("-" * 75)
            print(f"{'Metodo':<10} {'Puntos ND':<15} {'HV Total':<15} {'Tiempo HV':<15}")
            print("-" * 75)

            n_a, h_a, t_a = print_best_row("AMPL", ampl_best, (ref_x, ref_y), out_dir)
            n_m, h_m, t_m = print_best_row("MOEAD", moead_best, (ref_x, ref_y), out_dir)

            # ======= Fila para resumen final =======
            win_hv = winner_max(h_a, h_m)          # HV best front: mayor es mejor
            win_te = winner_min(ampl_te, moead_te) # T.Ejec promedio: menor es mejor

            # Conteos de victorias
            wins_hv_total[win_hv] = wins_hv_total.get(win_hv, 0) + 1
            wins_te_prom[win_te]  = wins_te_prom.get(win_te, 0) + 1

            summary_rows.append({
                "inst": inst,
                "hv_ampl": h_a,
                "hv_moead": h_m,
                "win_hv": win_hv,
                "te_ampl": ampl_te,
                "te_moead": moead_te,
                "win_te": win_te
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

            print("-" * 75)
            print(f"{'GAP%':<10} {fmt_gap(g_nd):<15} {fmt_gap(g_hv_best):<15} {'-':<15}")
            print("-" * 75)
            w_nd  = winner_max(float(n_a), float(n_m))
            w_hvt = winner_max(h_a, h_m)

            print(f"{'WINNER':<10} {w_nd:<15} {w_hvt:<15} {'-':<15}")
            print("-" * 75)


            # Guardar metrics de Best Fronts
            best_csv = os.path.join(out_dir, "best_fronts_metrics.csv")
            with open(best_csv, 'w') as f:
                f.write("Metodo,Puntos_ND,HV_Total,Tiempo_HV\n")
                if ampl_best: f.write(f"AMPL,{n_a},{h_a},{t_a}\n")
                if moead_best: f.write(f"MOEAD,{n_m},{h_m},{t_m}\n")

            # ---------------------------------------------------------
            # REPORTE GLOBAL (append por instancia) - TABLAS ALINEADAS
            # ---------------------------------------------------------
            w_time = winner_min(ampl_te, moead_te)
            w_hv   = winner_max(ampl_hv, moead_hv)
            w_thv  = winner_min(ampl_thv, moead_thv)

            w_nd   = winner_max(float(n_a), float(n_m))
            w_hvt  = winner_max(h_a, h_m)

            with open(report_path, "a", encoding="utf-8") as rf:
                rf.write(f"INSTANCIA: {inst}\n")

                # [3]
                rf.write("[3] RESUMEN PROMEDIO (Por Run)\n")
                rf.write(f"{'Metodo':<8}{'T.Ejec(s)':>12}{'HV':>16}{'T.HV(s)':>12}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'AMPL':<8}{fmt_float(ampl_te,12,4)}{fmt_float(ampl_hv,16,4)}{fmt_float(ampl_thv,12,6)}\n")
                rf.write(f"{'MOEAD':<8}{fmt_float(moead_te,12,4)}{fmt_float(moead_hv,16,4)}{fmt_float(moead_thv,12,6)}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'GAP%':<8}{fmt_gap_only(g_te):>12}{fmt_gap_only(g_hv_avg):>16}{fmt_gap_only(g_thv):>12}\n")
                rf.write(f"{'WINNER':<8}{w_time:>12}{w_hv:>16}{w_thv:>12}\n")

                rf.write("\n")

                # [4]
                rf.write("[4] COMPARACIÓN BEST FRONTS (Unificados)\n")
                rf.write(f"{'Metodo':<8}{'ND':>12}{'HV':>16}{'T.HV(s)':>12}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'AMPL':<8}{fmt_int(n_a,12)}{fmt_float(h_a,16,4)}{fmt_float(t_a,12,6)}\n")
                rf.write(f"{'MOEAD':<8}{fmt_int(n_m,12)}{fmt_float(h_m,16,4)}{fmt_float(t_m,12,6)}\n")
                rf.write("-" * 48 + "\n")
                rf.write(f"{'GAP%':<8}{fmt_gap_only(g_nd):>12}{fmt_gap_only(g_hv_best):>16}{'-':>12}\n")
                rf.write(f"{'WINNER':<8}{w_nd:>12}{w_hvt:>16}{'-':>12}\n")

                rf.write("\n" + ("-" * 60) + "\n\n")
   
        else:
            print("      [!] No se generaron datos para ninguna run.")

    # ==========================================================
    # RESUMEN FINAL EN TABLA
    # ==========================================================
    print("\n========================================================================================================================================================\n")
    print(" RESUMEN FINAL (por instancia)")
    print("========================================================================================================================================================\n")

    if not summary_rows:
        print("No hay filas para resumir (no se procesó ninguna instancia con datos).")
    else:
        # Formato fijo
        header = (
            f"{'INSTANCIA':<{W_INST}}"
            f"{'HV_AMPL':>{W_HV}}{'HV_MOEAD':>{W_HV}}{'WIN_HV':>{W_WIN}}"
            f"{'TE_PROM_AMPL':>{W_TE}}{'TE_PROM_MOEAD':>{W_TE}}{'WIN_TE':>{W_WIN}}"
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
            inst = r["inst"]
            hv_a = r["hv_ampl"]
            hv_m = r["hv_moead"]
            te_a = r["te_ampl"]
            te_m = r["te_moead"]
            win_hv = r["win_hv"]
            win_te = r["win_te"]

            # contar wins
            if win_hv == "AMPL":
                hv_w_ampl += 1
            elif win_hv == "MOEAD":
                hv_w_moead += 1

            if win_te == "AMPL":
                te_w_ampl += 1
            elif win_te == "MOEAD":
                te_w_moead += 1


            # --- HV base (sin paréntesis todavía)
            hv_a_txt = "-" if pd.isna(hv_a) else f"{hv_a:.4f}"
            hv_m_txt = "-" if pd.isna(hv_m) else f"{hv_m:.4f}"

            hv_a_cell = cell(hv_a_txt, W_HV)
            hv_m_cell = cell(hv_m_txt, W_HV)

            # marcar ganador HV con ( ... ) usando ancho fijo
            if win_hv == "AMPL" and hv_a_txt != "-":
                hv_a_cell = mark_winner_cell(hv_a_txt, W_HV)
            elif win_hv == "MOEAD" and hv_m_txt != "-":
                hv_m_cell = mark_winner_cell(hv_m_txt, W_HV)

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


            line = (
                f"{inst:<{W_INST}}"
                f"{hv_a_cell}{hv_m_cell}{win_hv:>{W_WIN}}"
                f"{te_a_cell}{te_m_cell}{win_te:>{W_WIN}}"
            )
            print(line)
            summary_lines.append(strip_ansi(line))


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
    args = parser.parse_args()
    
    procesar_instancias(args.tipo, args.instancia)