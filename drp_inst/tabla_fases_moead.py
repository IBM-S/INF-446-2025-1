#!/usr/bin/env python3
"""
tabla_fases_moead.py
====================
Genera una tabla LaTeX con las 4 fases del plan de implementación MOEA/D.

Lee los archivos last_gen_*.dat de todos los runs de una instancia en una
subcarpeta de datos/res/raw_moead/, combina las soluciones, filtra los puntos
no dominados y selecciona 4 fases por percentil de cobertura (F1).

Para cada fase muestra: cobertura (%), AEDs removidos, AEDs instalados, costo.

Uso:
    python3 tabla_fases_moead.py drp_657_STATEN_ISLAND --subdir drp_v75
    python3 tabla_fases_moead.py drp_657_STATEN_ISLAND --subdir drp_v75 --out tabla.tex
"""

import argparse
import re
from pathlib import Path

import numpy as np

from fase_parser import parse_instance   # reutilizar parser del archivo .dat

# ── Rutas base ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
RES_MOEAD = BASE_DIR / "datos" / "res" / "raw_moead"

NOMBRES_FASE = [
    "Estado actual",
    "Intervención prioritaria",
    "Expansión intermedia",
    "Cobertura completa",
]


# ── Parser de last_gen_*.dat ──────────────────────────────────────────────────

def parse_last_gen(path: Path) -> list[dict]:
    """
    Parsea un archivo last_gen_*.dat.
    Formato de línea: F1  F2  - IDs instalados: id1 id2 ...
    Devuelve lista de {f1, f2, installed: set[int]}.
    """
    solutions = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or "IDs instalados:" not in line:
            continue
        obj_part, ids_part = line.split("IDs instalados:", 1)
        parts = obj_part.split()
        if len(parts) < 2:
            continue
        try:
            f1 = float(parts[0])
            f2 = float(parts[1])
        except ValueError:
            continue
        installed = {int(x) for x in ids_part.split() if x.strip().isdigit()}
        solutions.append({"f1": f1, "f2": f2, "installed": installed})
    return solutions


# ── Filtro de no-dominados sobre objetos solución ────────────────────────────

def _pareto_filter_solutions(solutions: list[dict]) -> list[dict]:
    """
    Elimina duplicados (misma F1, F2) y luego filtra dominados.
    Devuelve lista de soluciones no dominadas, ordenadas por F2 ascendente.
    """
    if not solutions:
        return []

    # Deduplicar por (f1, f2): conservar primera ocurrencia de cada par
    seen: dict[tuple, dict] = {}
    for s in solutions:
        key = (round(s["f1"], 7), round(s["f2"], 4))
        if key not in seen:
            seen[key] = s
    deduped = list(seen.values())

    pts = np.array([[s["f1"], s["f2"]] for s in deduped])
    dominated = np.zeros(len(pts), dtype=bool)
    for i, p in enumerate(pts):
        if dominated[i]:
            continue
        mask = np.all(pts <= p, axis=1) & np.any(pts < p, axis=1)
        dominated[mask] = True

    front = [s for s, d in zip(deduped, dominated) if not d]
    front.sort(key=lambda s: s["f2"])
    return front


# ── Carga y combinación de todos los runs ─────────────────────────────────────

def load_moead_front(inst_name: str, subdir: str) -> list[dict]:
    """
    Lee los last_gen_*.dat de todos los runs, combina y devuelve
    el frente de Pareto no dominado como lista de soluciones.
    """
    inst_dir = RES_MOEAD / subdir / inst_name
    if not inst_dir.exists():
        raise FileNotFoundError(f"Directorio no encontrado: {inst_dir}")

    all_solutions: list[dict] = []
    for run_dir in sorted(inst_dir.glob("run_*")):
        for lg_path in run_dir.glob("last_gen_*.dat"):
            sols = parse_last_gen(lg_path)
            all_solutions.extend(sols)

    if not all_solutions:
        raise FileNotFoundError(f"No se encontraron last_gen_*.dat en: {inst_dir}")

    return _pareto_filter_solutions(all_solutions)


# ── Clasificación de AEDs ─────────────────────────────────────────────────────

def classify_aeds(solution: dict, nodes: dict) -> list[dict]:
    """
    Clasifica los AEDs de una solución MOEAD en existente/removido/nuevo.

    existente → nodo flag=1 cuyo ID está en installed  (se mantiene)
    removido  → nodo flag=1 cuyo ID NO está en installed (desinstalado)
    nuevo     → nodo flag=0 cuyo ID está en installed   (reubicado/comprado)
    """
    installed = solution["installed"]
    aeds = []
    for nid, n in nodes.items():
        if n["flag"] == 1:
            tipo = "existente" if nid in installed else "removido"
            aeds.append({"id": nid, "x": n["x"], "y": n["y"], "tipo": tipo})
        elif n["flag"] == 0 and nid in installed:
            aeds.append({"id": nid, "x": n["x"], "y": n["y"], "tipo": "nuevo"})
    return aeds


# ── Selección de 4 fases por percentil de cobertura ──────────────────────────

def pick_phases(front: list[dict], nodes: dict, n: int = 4) -> list[dict]:
    """
    Selecciona n soluciones representativas del frente por percentil de |F1|.

    Fase 0 → peor cobertura (F1 menos negativo, costo mínimo).
    Fase n-1 → mejor cobertura (F1 más negativo, costo máximo).

    Devuelve lista de dicts enriquecidos con: numero, nombre, aeds.
    """
    f1_vals  = np.array([s["f1"] for s in front])
    f1_worst = float(f1_vals.max())
    f1_best  = float(f1_vals.min())
    targets  = [f1_worst + (f1_best - f1_worst) * k / (n - 1) for k in range(n)]

    fases = []
    for i, t in enumerate(targets):
        idx = int(np.argmin(np.abs(f1_vals - t)))
        sol = front[idx]
        fases.append({
            "numero":  i,
            "nombre":  NOMBRES_FASE[i],
            "f1":      sol["f1"],
            "f2":      sol["f2"],
            "installed": sol["installed"],
            "aeds":    classify_aeds(sol, nodes),
        })
    return fases


# ── Generación de tabla LaTeX ─────────────────────────────────────────────────

def _tex(s: str) -> str:
    return (s.replace("á", r"\'{a}").replace("é", r"\'{e}")
             .replace("í", r"\'{i}").replace("ó", r"\'{o}")
             .replace("ú", r"\'{u}").replace("ñ", r"\~{n}"))


def build_latex_table(inst_name: str, fases: list[dict], c1: float = 1.0, c2: float = 0.2) -> str:
    label = inst_name.replace("_", r"\_")
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        rf"  \caption{{Plan de implementación MOEA/D --- \texttt{{{label}}}}}",
        rf"  \label{{tab:moead_fases_{inst_name}}}",
        r"  \small",
        r"  \begin{tabular}{clrrrrrr}",
        r"    \toprule",
        r"    \textbf{Fase} & \textbf{Nombre} "
        r"& \textbf{Cob. (\%)} & \textbf{Act.} & \textbf{Rem.} & \textbf{Reub.} & \textbf{Nuevos} & \textbf{Costo} \\",
        r"    \midrule",
    ]
    for f in fases:
        cob  = abs(f["f1"]) * 100
        act  = sum(1 for a in f["aeds"] if a["tipo"] in ("existente", "nuevo"))
        rem  = sum(1 for a in f["aeds"] if a["tipo"] == "removido")
        ins  = sum(1 for a in f["aeds"] if a["tipo"] == "nuevo")
        reub = min(ins, rem)
        nvo  = ins - reub
        lines.append(
            rf"    {f['numero']} & {_tex(f['nombre'])} "
            rf"& {cob:.2f} & {act} & {rem} & {reub} & {nvo} & {f['f2']:.1f} \\"
        )
    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Tabla LaTeX de fases MOEA/D")
    ap.add_argument("inst",      help="Nombre de instancia (ej. drp_657_STATEN_ISLAND)")
    ap.add_argument("--subdir",  required=True, help="Subcarpeta en raw_moead (ej. drp_v75)")
    ap.add_argument("--type",    default="drp", choices=["drp", "cam"], dest="ptype")
    ap.add_argument("--out",     default=None, help="Archivo .tex de salida (opcional)")
    args = ap.parse_args()

    print(f"[MOEAD] Cargando instancia {args.inst} desde {args.subdir}...")
    inst     = parse_instance(args.inst)
    nodes    = inst["nodes"]

    print(f"[MOEAD] Leyendo last_gen de todos los runs y filtrando no-dominados...")
    front    = load_moead_front(args.inst, args.subdir)
    fases    = pick_phases(front, nodes)

    params  = inst["params"]
    c1_val  = params.get("c1", 1.0)
    c2_val  = params.get("c2", 0.2)
    n_flag1 = sum(1 for n in nodes.values() if n["flag"] == 1)
    print(f"\n  Frente no dominado: {len(front)} puntos")
    print(f"  AEDs preinstalados en instancia: {n_flag1}  |  c1={c1_val}  c2={c2_val}\n")

    for f in fases:
        act  = sum(1 for a in f["aeds"] if a["tipo"] in ("existente", "nuevo"))
        rem  = sum(1 for a in f["aeds"] if a["tipo"] == "removido")
        ins  = sum(1 for a in f["aeds"] if a["tipo"] == "nuevo")
        reub = min(ins, rem)
        nvo  = ins - reub
        print(f"  Fase {f['numero']} ({f['nombre']}): "
              f"cob={abs(f['f1'])*100:.2f}%  act={act}  rem={rem}  "
              f"reub={reub}  nuevos={nvo}  F2={f['f2']:.1f}")

    tabla = build_latex_table(args.inst, fases, c1_val, c2_val)

    if args.out:
        Path(args.out).write_text(tabla, encoding="utf-8")
        print(f"\n[OK] Guardado: {args.out}")
    else:
        print(f"\n{'─'*60}\n{tabla}\n{'─'*60}")


if __name__ == "__main__":
    main()
