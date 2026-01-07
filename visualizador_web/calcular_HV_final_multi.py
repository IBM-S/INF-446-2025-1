#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import subprocess
import pandas as pd
import numpy as np
import argparse
import time
import re
from typing import Dict, List, Tuple, Optional

# ================= CONFIGURACIÓN DE RUTAS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.join(BASE_DIR, "..")

DIR_RES = os.path.join(PROYECTO_ROOT, "datos", "res")
DIR_AMPL = os.path.join(DIR_RES, "raw_ampl")

# OJO: los MOEAD sets se resuelven dinámicamente (ver resolve_moead_base)
DIR_ANALISIS_FINAL = os.path.join(DIR_RES, "analisis_final")

HV_EXEC = os.path.join(PROYECTO_ROOT, "material", "hv-1.3-src", "hv")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)

# ================= UTILIDADES =================

def read_points(filepath: str) -> List[List[float]]:
    points = []
    if not os.path.exists(filepath):
        return points
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                continue
            # igual que tu script: ignora líneas que empiezan con letras (por si hay headers)
            if s[0].isalpha():
                continue
            try:
                parts = s.split()
                x, y = float(parts[0]), float(parts[1])
                points.append([x, y])
            except Exception:
                pass
    return points

def filter_nondominated(points: List[List[float]]) -> List[List[float]]:
    if not points:
        return []
    pts = np.array(points, dtype=float)
    clean = []
    for i, p1 in enumerate(pts):
        dominated = False
        for j, p2 in enumerate(pts):
            if i == j:
                continue
            if (p2[0] <= p1[0] and p2[1] <= p1[1]) and (p2[0] < p1[0] or p2[1] < p1[1]):
                dominated = True
                break
        if not dominated:
            clean.append(p1)

    # únicos
    uniq = []
    seen = set()
    for p in clean:
        t = (float(p[0]), float(p[1]))
        if t not in seen:
            uniq.append([float(p[0]), float(p[1])])
            seen.add(t)
    return uniq

def save_points_to_file(points: List[List[float]], filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for p in points:
            f.write(f"{p[0]:.10f} {p[1]:.10f}\n")

def calculate_hv(points: List[List[float]], ref_point: Tuple[float, float], temp_file_path: str) -> Tuple[float, float]:
    """
    Igual idea que calculate_hv_transparent: escribe temporal, llama hv -r, mide tiempo.
    """
    if not points:
        return 0.0, 0.0

    save_points_to_file(points, temp_file_path)
    ref_string = f"{ref_point[0]} {ref_point[1]}"
    cmd = [HV_EXEC, "-r", ref_string, temp_file_path]

    hv_start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        hv_duration = time.time() - hv_start
        if result.returncode != 0:
            return 0.0, hv_duration
        return float(result.stdout.strip()), hv_duration
    except Exception:
        return 0.0, 0.0
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def get_execution_times(folder_path: str) -> Dict[int, float]:
    summary_file = os.path.join(folder_path, "execution_summary.csv")
    if not os.path.exists(summary_file):
        candidates = glob.glob(os.path.join(folder_path, "execution*summary.*"))
        if candidates:
            summary_file = candidates[0]

    times: Dict[int, float] = {}
    if os.path.exists(summary_file):
        try:
            df = pd.read_csv(summary_file)
            df.columns = [c.strip().lower() for c in df.columns]
            col_run, col_time = None, None
            for c in df.columns:
                if c == "run":
                    col_run = c
                if c in ["time_s", "time", "duration"]:
                    col_time = c
            if col_run and col_time:
                for _, row in df.iterrows():
                    try:
                        times[int(row[col_run])] = float(row[col_time])
                    except Exception:
                        continue
        except Exception:
            pass
    return times

def get_max_values_and_points(file_list: List[str]) -> Tuple[Optional[float], Optional[float], List[List[float]]]:
    max_x, max_y = -1e30, -1e30
    all_points: List[List[float]] = []
    found = False

    for fpath in file_list:
        pts = read_points(fpath)
        if not pts:
            continue
        found = True
        all_points.extend(pts)
        for p in pts:
            if p[0] > max_x:
                max_x = p[0]
            if p[1] > max_y:
                max_y = p[1]

    if not found:
        return None, None, []
    return max_x, max_y, all_points

def load_instance_order_from_all_inst(all_inst_path: str) -> List[str]:
    order = []
    if not os.path.exists(all_inst_path):
        return order
    with open(all_inst_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            base = os.path.basename(s)
            name, _ext = os.path.splitext(base)
            order.append(name)
    return order

def fmt_seconds_with_minutes(sec, dec_s=4, dec_m=2) -> str:
    if sec is None or (isinstance(sec, float) and np.isnan(sec)):
        return "-"
    try:
        s = float(sec)
    except Exception:
        return "-"
    m = s / 60.0
    return f"{s:.{dec_s}f} s ({m:.{dec_m}f} min)"

def _is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v))

def winner_min(values: Dict[str, float], tol=1e-12) -> str:
    # menor es mejor; ignora NaN
    best_m = None
    best_v = None
    for m, v in values.items():
        if _is_missing(v):
            continue
        if best_v is None or v < best_v - tol:
            best_v = v
            best_m = m
    return best_m or "-"

def winner_max(values: Dict[str, float], tol=1e-12) -> str:
    # mayor es mejor; ignora NaN
    best_m = None
    best_v = None
    for m, v in values.items():
        if _is_missing(v):
            continue
        if best_v is None or v > best_v + tol:
            best_v = v
            best_m = m
    return best_m or "-"

def resolve_moead_base(set_token: str) -> Optional[str]:
    """
    Devuelve la carpeta del set MOEAD que contiene directamente las instancias:
    .../raw_moead/<SET>/<inst>/run_*/...
    """
    tok = os.path.expanduser(set_token)

    # Si el usuario pasó una ruta (contiene / o empieza con . o ~)
    if os.sep in tok or tok.startswith(".") or tok.startswith("~"):
        p = os.path.abspath(tok)
        return p if os.path.isdir(p) else None

    # Si pasó solo el nombre del set (ej: drp_100000)
    candidates = [
        os.path.join(DIR_RES, "raw_moead", set_token),
        os.path.join(DIR_RES, f"raw_moead_{set_token}"),
        os.path.join(DIR_RES, set_token),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None

def list_instance_dirs(base_path: str) -> List[str]:
    """Devuelve subcarpetas que parecen instancias (tienen run_*/ o al menos son directorios)."""
    if not base_path or not os.path.isdir(base_path):
        return []
    insts = []
    for d in os.listdir(base_path):
        p = os.path.join(base_path, d)
        if not os.path.isdir(p):
            continue
        # filtro suave: que tenga al menos un run_* o que tenga subcarpetas
        if glob.glob(os.path.join(p, "run_*")) or any(os.path.isdir(os.path.join(p, x)) for x in os.listdir(p)):
            insts.append(d)
    return sorted(insts)


# ================= MAIN LOGIC =================

def procesar_instancias_multi(problem_type: str,
                             moead_sets: List[str],
                             target_instance: Optional[str] = None) -> None:
    os.makedirs(DIR_ANALISIS_FINAL, exist_ok=True)
    report_path = os.path.join(DIR_ANALISIS_FINAL, f"reporte_{problem_type}_mega_resumen.txt")

    # Resolver bases MOEAD
    moead_bases: List[Tuple[str, str]] = []  # (LABEL, BASE_PATH)
    for i, s in enumerate(moead_sets, start=1):
        label = f"MOEAD_{i}"
        base = resolve_moead_base(s)
        if base is None:
            print(f"[WARN] No encontré carpeta para set '{s}'. Se omitirá.")
            continue
        moead_bases.append((label, base))

    if not moead_bases:
        print("[ERROR] No hay sets MOEAD válidos. Revisa nombres/rutas.")
        return

    # Bases AMPL
    path_ampl_base = os.path.join(DIR_AMPL, problem_type)

    # Instancias: unión de AMPL + todas las MOEAD sets
    insts_set = set()
    if os.path.isdir(path_ampl_base):
        insts_set |= set([d for d in os.listdir(path_ampl_base) if os.path.isdir(os.path.join(path_ampl_base, d))])
    for _label, base in moead_bases:
        if os.path.isdir(base):
            insts_set |= set([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])

    # ====== DIAGNÓSTICO DE RUTAS (MOEAD + AMPL) ======
    print("\n" + "=" * 90)
    print(f"[INFO] Tipo: {problem_type}")
    print(f"[INFO] Carpeta salida analisis_final: {DIR_ANALISIS_FINAL}")

    # AMPL base
    print(f"[INFO] AMPL base: {path_ampl_base}")
    ampl_insts = list_instance_dirs(path_ampl_base) if os.path.isdir(path_ampl_base) else []
    if ampl_insts:
        print(f"[OK]   AMPL instancias encontradas: {len(ampl_insts)} (ej: {', '.join(ampl_insts[:5])}{'...' if len(ampl_insts)>5 else ''})")
    else:
        print("[WARN] AMPL: no se encontraron instancias (o carpeta no existe).")

    # MOEAD bases
    for label, base in moead_bases:
        insts = list_instance_dirs(base)
        if insts:
            print(f"[OK]   {label} base = {base} (instancias encontradas: {len(insts)}; ej: {', '.join(insts[:5])}{'...' if len(insts)>5 else ''})")
        else:
            print(f"[WARN] {label} base = {base} (0 instancias detectadas). Revisa estructura: <base>/<inst>/run_*/...")
    print("=" * 90 + "\n")


    # Orden por All.inst (mismo criterio que tu script) :contentReference[oaicite:3]{index=3}
    all_inst_path = os.path.join(BASE_DIR, "All.inst")
    order_from_file = load_instance_order_from_all_inst(all_inst_path)
    instancias = [x for x in order_from_file if x in insts_set]
    instancias += sorted(list(insts_set - set(instancias)))

    if not instancias:
        print("No se encontraron instancias (ni en AMPL ni en los MOEAD sets).")
        return

    # Reset reporte si no hay filtro
    if target_instance is None:
        with open(report_path, "w", encoding="utf-8") as rf:
            rf.write(f"REPORTE MEGA RESUMEN - TIPO {problem_type.upper()}\n")
            rf.write(f"SETS MOEAD: {', '.join([f'{lb}:{bp}' for lb, bp in moead_bases])}\n\n")

    # Para mega resumen final
    summary_rows = []

    for inst in instancias:
        if target_instance and inst != target_instance:
            continue

        print(f"\n>>> Procesando: {inst}")
        out_dir = os.path.join(DIR_ANALISIS_FINAL, problem_type, inst)
        os.makedirs(out_dir, exist_ok=True)

                # =========================
        # [1] NADIR/MAX + REF POINTS (POR PAR AMPL–MOEAD_i)
        # =========================
        # AMPL máximos desde pareto_front
        max_x_ampl, max_y_ampl, all_ampl_points = None, None, []
        path_inst_ampl = os.path.join(path_ampl_base, inst)
        if os.path.isdir(path_inst_ampl):
            ampl_files = glob.glob(os.path.join(path_inst_ampl, "run_*", "pareto_front.txt"))
            max_x_ampl, max_y_ampl, all_ampl_points = get_max_values_and_points(ampl_files)

        # MOEAD sets máximos desde last_gen + puntos finales desde pareto_front
        moead_info = {}
        for label, base in moead_bases:
            path_inst_m = os.path.join(base, inst)
            max_x_m, max_y_m, all_final = None, None, []
            if os.path.isdir(path_inst_m):
                last_gens = glob.glob(os.path.join(path_inst_m, "run_*", f"last_gen_{inst}.dat"))
                max_x_m, max_y_m, _ = get_max_values_and_points(last_gens)

                final_files = glob.glob(os.path.join(path_inst_m, "run_*", "pareto_front.txt"))
                _, _, all_final = get_max_values_and_points(final_files)

            moead_info[label] = {
                "base": base,
                "path_inst": path_inst_m,
                "max_x": max_x_m,
                "max_y": max_y_m,
                "all_final_points": all_final,
            }

        # Ref points por PAR: AMPL–MOEAD_i
        # Guardamos 1 archivo por MOEAD_i como pediste
        ref_pair = {}  # label -> (refx, refy)
        for label in moead_info:
            vx = [v for v in [max_x_ampl, moead_info[label]["max_x"]] if v is not None]
            vy = [v for v in [max_y_ampl, moead_info[label]["max_y"]] if v is not None]
            if not vx or not vy:
                continue
            mx = max(vx); my = max(vy)
            rx = mx + (abs(mx) * 0.01 if mx != 0 else 0.1)
            ry = my + (abs(my) * 0.01 if my != 0 else 0.1)
            ref_pair[label] = (rx, ry)

            with open(os.path.join(out_dir, f"reference_point_{label}.txt"), "w", encoding="utf-8") as f:
                f.write(f"{rx} {ry}\n")

        if not ref_pair:
            print("  [!] No se pudo construir ningún punto de referencia AMPL–MOEAD_i. Saltando instancia.")
            continue

        # =========================
        # [2] BEST FRONTS (unificados)
        # =========================
        ampl_best = filter_nondominated(all_ampl_points)
        if ampl_best:
            save_points_to_file(ampl_best, os.path.join(out_dir, "best_front_ampl.txt"))

        moead_best_map = {}
        for label in moead_info:
            pts = moead_info[label]["all_final_points"]
            best = filter_nondominated(pts)
            moead_best_map[label] = best
            if best:
                save_points_to_file(best, os.path.join(out_dir, f"best_front_moead_{label}.txt"))

        # =========================
        # [3] MÉTRICAS POR RUN (AMPL + MOEAD_1..n)
        # =========================
        final_data = []

        # AMPL runs
        if os.path.isdir(path_inst_ampl):
            times_dict = get_execution_times(path_inst_ampl)
            run_folders = sorted(glob.glob(os.path.join(path_inst_ampl, "run_*")),
                                 key=lambda p: int(os.path.basename(p).split("_")[1]) if "_" in os.path.basename(p) else 99999)
            for rf in run_folders:
                try:
                    run_id = int(os.path.basename(rf).split("_")[1])
                except Exception:
                    continue
                pareto_file = os.path.join(rf, "pareto_front.txt")
                points = read_points(pareto_file)
                if not points:
                    final_data.append({"metodo": "AMPL", "run": run_id, "time_ejec": times_dict.get(run_id, np.nan),
                                       "nd_points": 0, "hv": 0.0, "time_hv": 0.0})
                    continue
                clean = filter_nondominated(points)
                temp_file = os.path.join(out_dir, f"temp_AMPL_{run_id}.dat")
                hv_val, hv_time = (np.nan, np.nan)
                final_data.append({"metodo": "AMPL", "run": run_id, "time_ejec": times_dict.get(run_id, np.nan),
                                   "nd_points": len(clean), "hv": hv_val, "time_hv": hv_time})

        # MOEAD runs por set
        for label, base in moead_bases:
            path_inst_m = os.path.join(base, inst)
            if not os.path.isdir(path_inst_m):
                continue
            times_dict = get_execution_times(path_inst_m)
            run_folders = sorted(glob.glob(os.path.join(path_inst_m, "run_*")),
                                 key=lambda p: int(os.path.basename(p).split("_")[1]) if "_" in os.path.basename(p) else 99999)
            for rf in run_folders:
                try:
                    run_id = int(os.path.basename(rf).split("_")[1])
                except Exception:
                    continue
                pareto_file = os.path.join(rf, "pareto_front.txt")
                points = read_points(pareto_file)
                if not points:
                    final_data.append({"metodo": label, "run": run_id, "time_ejec": times_dict.get(run_id, np.nan),
                                       "nd_points": 0, "hv": 0.0, "time_hv": 0.0})
                    continue
                clean = filter_nondominated(points)
                temp_file = os.path.join(out_dir, f"temp_{label}_{run_id}.dat")
                hv_val, hv_time = (np.nan, np.nan)
                final_data.append({"metodo": label, "run": run_id, "time_ejec": times_dict.get(run_id, np.nan),
                                   "nd_points": len(clean), "hv": hv_val, "time_hv": hv_time})

        if final_data:
            df = pd.DataFrame(final_data)
            df.to_csv(os.path.join(out_dir, "final_summary.csv"), index=False)

            # Promedios por método
            resumen = df.groupby("metodo")[["time_ejec", "hv", "time_hv", "nd_points"]].mean().reset_index()
            resumen.to_csv(os.path.join(out_dir, "final_summary_methods.csv"), index=False)
        else:
            df = pd.DataFrame(columns=["metodo","run","time_ejec","nd_points","hv","time_hv"])
            resumen = pd.DataFrame(columns=["metodo","time_ejec","hv","time_hv","nd_points"])

        # =========================
        # [4] BEST FRONT METRICS POR PAR (AMPL–MOEAD_i)
        # =========================
        ampl_best = filter_nondominated(all_ampl_points)
        if ampl_best:
            save_points_to_file(ampl_best, os.path.join(out_dir, "best_front_ampl.txt"))

        moead_best_map = {}
        for label in moead_info:
            best = filter_nondominated(moead_info[label]["all_final_points"])
            moead_best_map[label] = best
            if best:
                save_points_to_file(best, os.path.join(out_dir, f"best_front_moead_{label}.txt"))

        def gap_pct(hv_ampl: float, hv_m: float) -> float:
            # GAP% relativo a AMPL. Si AMPL=0, devolvemos NaN.
            if hv_ampl is None or hv_ampl == 0 or np.isnan(hv_ampl):
                return np.nan
            return (( hv_ampl - hv_m)/hv_ampl) * 100.0

        # HV best-front por combinación
        pair_rows = []
        for label in [lb for lb, _ in moead_bases]:
            if label not in ref_pair:
                continue
            ref = ref_pair[label]

            # HV(AMPL) con ref de ESTE par
            hv_ampl, thv_a = (np.nan, np.nan)
            if ampl_best:
                hv_ampl, thv_a = calculate_hv(ampl_best, ref, os.path.join(out_dir, f"temp_best_AMPL_{label}.dat"))

            # HV(MOEAD_i) con ref de ESTE par
            hv_m, thv_m = (np.nan, np.nan)
            best_m = moead_best_map.get(label, [])
            if best_m:
                hv_m, thv_m = calculate_hv(best_m, ref, os.path.join(out_dir, f"temp_best_{label}.dat"))

            pair_rows.append({
                "pair": f"AMPL-{label}",
                "label": label,
                "ref_x": ref[0],
                "ref_y": ref[1],
                "hv_ampl": hv_ampl,
                "hv_moead": hv_m,
                "gap_pct": gap_pct(hv_ampl, hv_m),
                "nd_ampl": len(ampl_best) if ampl_best else 0,
                "nd_moead": len(best_m) if best_m else 0,
                "time_hv_ampl": thv_a,
                "time_hv_moead": thv_m,
            })

        pair_df = pd.DataFrame(pair_rows)
        pair_df.to_csv(os.path.join(out_dir, "best_fronts_metrics_pairs.csv"), index=False)

        # También guardar en best_front_metrics/MOEAD_i/ como pediste
        bfm_root = os.path.join(out_dir, "best_front_metrics")
        os.makedirs(bfm_root, exist_ok=True)
        for _, r in pair_df.iterrows():
            label = r["label"]
            mdir = os.path.join(bfm_root, label)
            os.makedirs(mdir, exist_ok=True)
            pd.DataFrame([r]).to_csv(os.path.join(mdir, "best_front_metrics.csv"), index=False)

   
        # T.Ejec promedio por método (desde resumen)
        # =========================
        # [5] TIEMPOS PROMEDIO (AMPL + MOEAD_i)
        # =========================
        te_avg = {}

        # AMPL
        if os.path.isdir(path_inst_ampl):
            tdict = get_execution_times(path_inst_ampl)
            if tdict:
                te_avg["AMPL"] = float(np.mean(list(tdict.values())))
            else:
                te_avg["AMPL"] = np.nan
        else:
            te_avg["AMPL"] = np.nan

        # MOEAD_i
        for label, base in moead_bases:
            path_inst_m = os.path.join(base, inst)
            if os.path.isdir(path_inst_m):
                tdict = get_execution_times(path_inst_m)
                te_avg[label] = float(np.mean(list(tdict.values()))) if tdict else np.nan
            else:
                te_avg[label] = np.nan

        pd.DataFrame([{"metodo": k, "time_ejec_avg": v} for k, v in te_avg.items()]) \
          .to_csv(os.path.join(out_dir, "execution_times_avg.csv"), index=False)

        summary_rows.append({
            "inst": inst,
            "pair_df": pair_df.copy(),
            "te_avg": te_avg.copy(),
        })


    # =========================
    # [6] PRINT MEGA RESUMEN TABULAR
    # =========================
    methods_order = [lb for lb, _ in moead_bases]  # ['MOEAD_1', 'MOEAD_2', ...]


    print("\n" + "=" * 120)
    print("TABLA 1 - HV (best-front) y GAP% por par AMPL–MOEAD_i (ref por par)")
    print("=" * 120)

    W_INST = 32
    W_NUM  = 14
    W_GAP  = 10

    header = f"{'INST':<{W_INST}}"
    for m in methods_order:
        header += f"{('HV_A_'+m):>{W_NUM}}{('HV_'+m):>{W_NUM}}{('GAP%_'+m):>{W_GAP}}"
    print(header)
    print("-" * len(header))

    for row in summary_rows:
        inst = row["inst"]
        pair_df = row["pair_df"]
        line = f"{inst:<{W_INST}}"

        for m in methods_order:
            r = pair_df[pair_df["label"] == m]
            if len(r) == 0:
                line += f"{'-':>{W_NUM}}{'-':>{W_NUM}}{'-':>{W_GAP}}"
                continue

            r0 = r.iloc[0]
            hv_a = r0["hv_ampl"]
            hv_m = r0["hv_moead"]
            gp   = r0["gap_pct"]

            line += f"{(f'{hv_a:.4f}' if pd.notna(hv_a) else '-'):>{W_NUM}}"
            line += f"{(f'{hv_m:.4f}' if pd.notna(hv_m) else '-'):>{W_NUM}}"
            # GAP con signo
            line += f"{(f'{gp:+.2f}' if pd.notna(gp) else '-'):>{W_GAP}}"

        print(line)

    print("=" * 120)

    print("\n" + "=" * 120)
    print("TABLA 2 - Tiempo de ejecución promedio (por run)")
    print("=" * 120)

    W_INST = 32
    W_TE   = 22

    header = f"{'INST':<{W_INST}}{'TE_AMPL':>{W_TE}}"
    for m in methods_order:
        header += f"{('TE_'+m):>{W_TE}}"
    print(header)
    print("-" * len(header))

    for row in summary_rows:
        inst = row["inst"]
        te_avg = row["te_avg"]
        line = f"{inst:<{W_INST}}"
        line += f"{fmt_seconds_with_minutes(te_avg.get('AMPL', np.nan)):>{W_TE}}"
        for m in methods_order:
            line += f"{fmt_seconds_with_minutes(te_avg.get(m, np.nan)):>{W_TE}}"
        print(line)

    print("=" * 120)


    print("\n" + "=" * 120)
    print("TABLA 3 - Número de puntos no dominados (best-front unificado)")
    print("=" * 120)

    W_INST = 32
    W_ND   = 12

    header = f"{'INST':<{W_INST}}{'ND_AMPL':>{W_ND}}"
    for m in methods_order:
        header += f"{('ND_'+m):>{W_ND}}"
    print(header)
    print("-" * len(header))

    for row in summary_rows:
        inst = row["inst"]
        pair_df = row["pair_df"]

        # ND AMPL lo tomamos de cualquier fila (es el mismo best-front)
        nd_ampl = "-"
        if not pair_df.empty and "nd_ampl" in pair_df.columns:
            v = pair_df.iloc[0]["nd_ampl"]
            nd_ampl = str(int(v)) if pd.notna(v) else "-"

        line = f"{inst:<{W_INST}}{nd_ampl:>{W_ND}}"

        for m in methods_order:
            r = pair_df[pair_df["label"] == m]
            if len(r) == 0:
                line += f"{'-':>{W_ND}}"
                continue
            v = r.iloc[0]["nd_moead"]
            line += f"{(str(int(v)) if pd.notna(v) else '-'):>{W_ND}}"

        print(line)

    print("=" * 120)

    print(f"[OK] Reporte mega guardado en: {report_path}")

# ================= ENTRYPOINT =================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tipo", type=str, default="drp", help="Tipo de problema: drp/cam")
    parser.add_argument("--instancia", type=str, default=None, help="Nombre de instancia (sin .dat)")
    parser.add_argument("--moead_sets", nargs="+", required=True,
                        help="Lista de sets MOEAD (nombres o rutas), ej: drp_100000 drp_200000 drp_400000")
    args = parser.parse_args()

    procesar_instancias_multi(args.tipo, args.moead_sets, args.instancia)
