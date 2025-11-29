
# ejecutar hipervolumen:  ../material/hv-1.3-src/hv -r "-3742.3881 12420.98" ../datos/res/analisis/cam/cam_14468_VENUSTIANO_CARRANZA/best_front_moead.txt

import os
import glob
import subprocess
import pandas as pd
import numpy as np
import argparse
import sys
import time

# ================= CONFIGURACIÓN DE RUTAS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.join(BASE_DIR, "..") 

DIR_RES = os.path.join(PROYECTO_ROOT, "datos", "res")
DIR_AMPL = os.path.join(DIR_RES, "raw_ampl")
DIR_MOEAD = os.path.join(DIR_RES, "raw_moead")
DIR_ANALISIS = os.path.join(DIR_RES, "analisis")

HV_EXEC = os.path.join(PROYECTO_ROOT, "material", "hv-1.3-src", "hv")

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
    todas_instancias = sorted(list(set(insts_ampl + insts_moead)))

    if not todas_instancias:
        print("No se encontraron instancias en raw_ampl ni raw_moead.")
        return

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
            moead_all_gens = glob.glob(os.path.join(path_inst_moead, "run_*", "POF_*.dat"))
            max_x_moead, max_y_moead, _ = get_max_values_and_points(moead_all_gens)
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
            
            # --- TABLA 1: PROMEDIOS POR ALGORITMO ---
            print(f"\n  [3] RESUMEN PROMEDIO (Por Run):")
            print("-" * 75)
            print(f"{'Metodo':<10} {'T. Ejec prom':<15} {'HV Promedio':<15} {'T. HV prom':<15}")
            print("-" * 75)
            
            resumen = df.groupby("metodo")[["time_ejec", "hv", "time_hv"]].mean()
            
            # Forzar mostrar ambas filas
            for metodo_nombre in ["AMPL", "MOEAD"]:
                if metodo_nombre in resumen.index:
                    fila = resumen.loc[metodo_nombre]
                    t_e = f"{fila['time_ejec']:.4f} s" if pd.notna(fila['time_ejec']) else "NaN"
                    hv  = f"{fila['hv']:.4f}"
                    t_h = f"{fila['time_hv']:.6f} s"
                    print(f"{metodo_nombre:<10} {t_e:<15} {hv:<15} {t_h:<15}")
                else:
                    # Si no hay datos para el método, imprimir guiones
                    print(f"{metodo_nombre:<10} {'-':<15} {'-':<15} {'-':<15}")
            print("-" * 75)

            # --- TABLA 2: BEST FRONTS UNIFICADOS ---
            print(f"\n  [4] COMPARACIÓN DE BEST FRONTS (Frentes Unificados):")
            print("-" * 75)
            print(f"{'Metodo':<10} {'Puntos ND':<15} {'HV Total':<15} {'Tiempo HV':<15}")
            print("-" * 75)

            # Helper para imprimir fila de best front
            def print_best_row(name, points, ref):
                if points:
                    temp_f = os.path.join(out_dir, f"temp_best_{name.lower()}.dat")
                    hv, t = calculate_hv_transparent(points, ref, temp_f)
                    print(f"{name:<10} {len(points):<15} {hv:<15.4f} {t:<15.6f}")
                    return len(points), hv, t
                else:
                    print(f"{name:<10} {'-':<15} {'-':<15} {'-':<15}")
                    return 0, 0.0, 0.0

            n_a, h_a, t_a = print_best_row("AMPL", ampl_best, (ref_x, ref_y))
            n_m, h_m, t_m = print_best_row("MOEAD", moead_best, (ref_x, ref_y))
            print("-" * 75)

            # Guardar metrics de Best Fronts
            best_csv = os.path.join(out_dir, "best_fronts_metrics.csv")
            with open(best_csv, 'w') as f:
                f.write("Metodo,Puntos_ND,HV_Total,Tiempo_HV\n")
                if ampl_best: f.write(f"AMPL,{n_a},{h_a},{t_a}\n")
                if moead_best: f.write(f"MOEAD,{n_m},{h_m},{t_m}\n")
                
        else:
            print("      [!] No se generaron datos para ninguna run.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--instancia', type=str, default=None)
    parser.add_argument('--tipo', type=str, default="cam")
    args = parser.parse_args()
    
    procesar_instancias(args.tipo, args.instancia)