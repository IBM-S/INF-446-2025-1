#!/usr/bin/env python3
"""
tabla_fases.py
==============
Genera una tabla LaTeX comparando las 4 fases del plan de implementación
entre AMPL y MOEA/D para una instancia dada.

AMPL  → usa parse_plan() (fase_parser.py): lee pareto_front.txt + ampl_log_full.txt
        para obtener cobertura, costo y conteo de AEDs removidos/instalados.
MOEAD → combina pareto_front.txt de todos los runs, filtra no-dominados,
        selecciona 4 fases por percentil de cobertura F1.
        (sin detalle de posiciones, solo F1/F2)

Uso:
    python3 tabla_fases.py drp_657_STATEN_ISLAND
    python3 tabla_fases.py cam_1390_MILPA_ALTA --type cam
    python3 tabla_fases.py drp_657_STATEN_ISLAND --out tabla.tex
"""

import argparse
from pathlib import Path

import numpy as np

from fase_parser import parse_plan   # AMPL: frente + posiciones AED

# ── Rutas base ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
RES_MOEAD = BASE_DIR / "datos" / "res" / "raw_moead"

MOEAD_SUBDIRS = {"drp": "drp_final", "cam": "cam_final"}

NOMBRES_FASE = [
    "Estado actual",
    "Intervención prioritaria",
    "Expansión intermedia",
    "Cobertura completa",
]


# ── Lectura de pareto_front.txt (para MOEAD) ──────────────────────────────────

def read_pareto_front(path: Path) -> np.ndarray:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 3:
            rows.append((float(parts[1]), float(parts[2])))
        elif len(parts) == 2:
            rows.append((float(parts[0]), float(parts[1])))
    return np.array(rows) if rows else np.empty((0, 2))


# ── Filtro de no-dominados ────────────────────────────────────────────────────

def pareto_filter(points: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return points
    pts = np.unique(points, axis=0)
    dominated = np.zeros(len(pts), dtype=bool)
    for i, p in enumerate(pts):
        if dominated[i]:
            continue
        dom_mask = np.all(pts <= p, axis=1) & np.any(pts < p, axis=1)
        dominated[dom_mask] = True
    return pts[~dominated]


# ── Selección de 4 fases por percentil de cobertura F1 ───────────────────────

def pick_four_phases(front: np.ndarray) -> list[dict]:
    """
    Selecciona 4 puntos del frente por percentil de cobertura |F1|.
    Fase 0 → peor cobertura (F1 menos negativo).
    Fase 3 → mejor cobertura (F1 más negativo).
    """
    f1_vals  = front[:, 0]
    f1_worst = float(f1_vals.max())
    f1_best  = float(f1_vals.min())
    targets = [
        f1_worst,
        f1_worst + (f1_best - f1_worst) * 0.33,
        f1_worst + (f1_best - f1_worst) * 0.66,
        f1_best,
    ]
    fases = []
    for i, t in enumerate(targets):
        idx = int(np.argmin(np.abs(f1_vals - t)))
        fases.append({
            "numero": i,
            "nombre": NOMBRES_FASE[i],
            "f1":     float(front[idx, 0]),
            "f2":     float(front[idx, 1]),
        })
    return fases


# ── MOEAD: combinar todos los runs → filtrar no-dominados ────────────────────

def load_moead_front(inst_name: str, problem_type: str) -> np.ndarray:
    subdir   = MOEAD_SUBDIRS.get(problem_type, f"{problem_type}_final")
    inst_dir = RES_MOEAD / subdir / inst_name

    all_pts = []
    for run_dir in sorted(inst_dir.glob("run_*")):
        pf = run_dir / "pareto_front.txt"
        if pf.exists():
            pts = read_pareto_front(pf)
            if len(pts) > 0:
                all_pts.append(pts)

    if not all_pts:
        raise FileNotFoundError(f"No se encontraron pareto_front.txt en: {inst_dir}")

    combined = np.vstack(all_pts)
    front    = pareto_filter(combined)
    return front[front[:, 1].argsort()]


# ── Generación de tabla LaTeX ─────────────────────────────────────────────────

def _tex_name(nombre: str) -> str:
    return (nombre
            .replace("á", r"\'{a}").replace("é", r"\'{e}")
            .replace("í", r"\'{i}").replace("ó", r"\'{o}")
            .replace("ú", r"\'{u}").replace("ñ", r"\~{n}"))


def build_latex_table(
    inst_name:   str,
    fases_ampl:  list[dict],   # dicts con keys: numero, nombre, f1, f2, aeds
    fases_moead: list[dict],   # dicts con keys: numero, nombre, f1, f2
) -> str:
    label = inst_name.replace("_", r"\_")

    lines = []
    lines += [
        r"\begin{table}[htbp]",
        r"  \centering",
        rf"  \caption{{Plan de implementación en fases --- \texttt{{{label}}}}}",
        rf"  \label{{tab:fases_{inst_name}}}",
        r"  \small",
        r"  \begin{tabular}{clrrrrrrr}",
        r"    \toprule",
        r"    & & \multicolumn{5}{c}{\textbf{AMPL (Gurobi)}} "
        r"& \multicolumn{2}{c}{\textbf{MOEA/D}} \\",
        r"    \cmidrule(lr){3-7} \cmidrule(lr){8-9}",
        r"    \textbf{Fase} & \textbf{Nombre} "
        r"& \textbf{Cob. (\%)} & \textbf{Act.} & \textbf{Rem.} & \textbf{Ins.} & \textbf{Costo} "
        r"& \textbf{Cob. (\%)} & \textbf{Costo} \\",
        r"    \midrule",
    ]

    for fa, fm in zip(fases_ampl, fases_moead):
        cob_a  = abs(fa["f1"]) * 100
        cob_m  = abs(fm["f1"]) * 100
        act    = sum(1 for a in fa["aeds"] if a["tipo"] in ("existente", "nuevo"))
        rem    = sum(1 for a in fa["aeds"] if a["tipo"] == "removido")
        ins    = sum(1 for a in fa["aeds"] if a["tipo"] == "nuevo")
        nombre = _tex_name(fa["nombre"])
        lines.append(
            rf"    {fa['numero']} & {nombre} "
            rf"& {cob_a:.2f} & {act} & {rem} & {ins} & {fa['f2']:.1f} "
            rf"& {cob_m:.2f} & {fm['f2']:.1f} \\"
        )

    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Tabla LaTeX de fases AMPL vs MOEAD")
    ap.add_argument("inst", help="Nombre de la instancia (ej. drp_657_STATEN_ISLAND)")
    ap.add_argument("--type",  default="drp", choices=["drp", "cam"], dest="ptype")
    ap.add_argument("--run",   type=int, default=1, help="Run AMPL a usar (default 1)")
    ap.add_argument("--out",   default=None, help="Archivo .tex de salida (opcional)")
    args = ap.parse_args()

    print(f"[AMPL]  Cargando plan (run {args.run})...")
    ampl_plan  = parse_plan(args.inst, args.ptype, args.run)
    fases_ampl = ampl_plan["fases"]

    print(f"[MOEAD] Combinando {args.inst} (todos los runs) y filtrando no-dominados...")
    moead_front = load_moead_front(args.inst, args.ptype)
    fases_moead = pick_four_phases(moead_front)

    print(f"\n  Puntos AMPL  (frente no-dom.): {ampl_plan['front_size']}")
    print(f"  Puntos MOEAD (no-dom. combinado): {len(moead_front)}\n")

    for fa, fm in zip(fases_ampl, fases_moead):
        rem = sum(1 for a in fa["aeds"] if a["tipo"] == "removido")
        ins = sum(1 for a in fa["aeds"] if a["tipo"] == "nuevo")
        print(f"  Fase {fa['numero']}:  AMPL  cob={abs(fa['f1'])*100:.2f}%  "
              f"rem={rem}  ins={ins}  F2={fa['f2']:.1f}"
              f"   |  MOEAD  cob={abs(fm['f1'])*100:.2f}%  F2={fm['f2']:.1f}")

    tabla = build_latex_table(args.inst, fases_ampl, fases_moead)

    if args.out:
        Path(args.out).write_text(tabla, encoding="utf-8")
        print(f"\n[OK] Guardado: {args.out}")
    else:
        print(f"\n{'─'*60}\n{tabla}\n{'─'*60}")


if __name__ == "__main__":
    main()
