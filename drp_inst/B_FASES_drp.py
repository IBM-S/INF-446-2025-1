"""
B_FASES_drp.py
==============
Genera el plan de 4 fases de implementación para el problema DRP (NYC boroughs).

Las fases se obtienen del frente de Pareto combinado (ya calculado por ANN_drp.py)
seleccionando 4 puntos representativos por percentil de cobertura F1:
  Fase 0 -> 0%  de cobertura (menor |F1|, costo minimo)
  Fase 1 -> 33% del rango F1
  Fase 2 -> 66% del rango F1
  Fase 3 -> 100% (maxima cobertura)

Clasificacion de nodos en cada fase:
  existente -> flag=1 Y esta en la solucion        (se mantiene en su lugar)
  removido  -> flag=1 Y NO esta en la solucion     (se retira)
  nuevo     -> flag=0 Y esta en la solucion        (reubicacion o compra nueva)
  reubicado = min(removido, nuevo)
  comprado  = nuevo - reubicado

Prerequisito: ejecutar ANN_drp.py con la misma version para que existan
los archivos pareto_front_{version}.csv en drp_inst/drp/{stem}/.

Salidas:
  drp_inst/drp/{stem}/fases_{version}.csv     <- 4 fases por instancia
  drp_inst/drp/fases_all_{version}.csv        <- todas las instancias
  drp_inst/drp/fases_{version}.tex            <- tabla LaTeX general

Uso:
    python B_FASES_drp.py                     # version mas reciente
    python B_FASES_drp.py --version drp_v75
"""

import argparse
import re
from itertools import groupby
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Plan de fases DRP desde frente de Pareto MOEA/D.")
parser.add_argument("--version", default=None, metavar="FOLDER",
                    help="Version del frente (ej. drp_v76). Si se omite: mas reciente.")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE      = Path(__file__).parent
INST_DIR  = (HERE / "../datos/inst").resolve()
MOEAD_DIR = (HERE / "../datos/res/raw_moead").resolve()
OUT_BASE  = HERE / "drp"

BOROUGH_FILES = {
    "STATEN ISLAND": "drp_657_STATEN_ISLAND",
    "BRONX":         "drp_2151_BRONX",
    "QUEENS":        "drp_2885_QUEENS",
    "BROOKLYN":      "drp_3442_BROOKLYN",
    "MANHATTAN":     "drp_4432_MANHATTAN",
}

NOMBRES_FASE = [
    "Estado actual",
    "Intervencion prioritaria",
    "Expansion intermedia",
    "Cobertura completa",
]

NOMBRES_FASE_TEX = [
    "Estado actual",
    r"Intervenci\'{o}n prioritaria",
    r"Expansi\'{o}n intermedia",
    "Cobertura completa",
]


# ---------------------------------------------------------------------------
# Resolve version tag from existing pareto_front files or moead folders
# ---------------------------------------------------------------------------
def _resolve_version() -> str:
    first_stem = next(iter(BOROUGH_FILES.values()))
    candidates = sorted(
        (OUT_BASE / first_stem).glob("pareto_front_*.csv"),
        key=lambda p: p.name, reverse=True,
    )
    if candidates:
        return re.sub(r"^pareto_front_|\.csv$", "", candidates[0].name)
    version_dirs = sorted(
        [d for d in MOEAD_DIR.iterdir() if d.is_dir() and d.name.startswith("drp_v")],
        key=lambda d: d.name, reverse=True,
    )
    if not version_dirs:
        raise FileNotFoundError("No se encontro ninguna version drp_v* en raw_moead.")
    return version_dirs[0].name


VERSION_TAG = args.version or _resolve_version()
print("=" * 70)
print(f"B_FASES_drp.py  |  version: {VERSION_TAG}")
print("=" * 70)


# ---------------------------------------------------------------------------
# Parse ALL points from a .dat instance file
# Returns list of (x, y, flag) in 1-based order (index 0 = ID 1).
# ---------------------------------------------------------------------------
def parse_dat_all_points(filepath: Path) -> list[tuple]:
    with open(filepath, "r") as fh:
        lines = fh.readlines()
    points = []
    inside = False
    for line in lines:
        s = line.strip()
        if re.match(r"param\s*:\s*coordx\s+coordy\s+flag", s):
            inside = True
            continue
        if inside and s == ";":
            break
        if inside and s:
            parts = s.split()
            if len(parts) >= 4:
                points.append((float(parts[1]), float(parts[2]), int(parts[3])))
    return points


# ---------------------------------------------------------------------------
# Pick 4 representative solutions from the Pareto front by F1 percentile.
# F1 is negative (−coverage); more negative = better coverage.
#   Fase 0 -> least negative F1 (worst coverage, lowest cost)
#   Fase 3 -> most negative F1  (best coverage,  highest cost)
# Returns list of 4 row indices into the dataframe.
# ---------------------------------------------------------------------------
def pick_phase_indices(df: pd.DataFrame) -> list[int]:
    f1    = df["obj1"].values
    worst = float(f1.max())
    best  = float(f1.min())
    targets = [
        worst,
        worst + (best - worst) * 0.33,
        worst + (best - worst) * 0.66,
        best,
    ]
    return [int(np.argmin(np.abs(f1 - t))) for t in targets]


# ---------------------------------------------------------------------------
# Classify AEDs for a given installed ID set
# ---------------------------------------------------------------------------
def classify_aeds(ids_1b: set[int], all_points: list[tuple]) -> dict:
    n_existente = n_removido = n_nuevo = 0
    for i, (_, _, flag) in enumerate(all_points):
        id_1b = i + 1
        if flag == 1:
            if id_1b in ids_1b:
                n_existente += 1
            else:
                n_removido += 1
        elif id_1b in ids_1b:
            n_nuevo += 1
    n_reubicado = min(n_removido, n_nuevo)
    n_comprado  = n_nuevo - n_reubicado
    return {
        "N_active":    n_existente + n_nuevo,
        "N_existente": n_existente,
        "N_removido":  n_removido,
        "N_nuevo":     n_nuevo,
        "N_reubicado": n_reubicado,
        "N_comprado":  n_comprado,
    }


# ---------------------------------------------------------------------------
# LaTeX table builder (all boroughs in one table with \multirow)
# ---------------------------------------------------------------------------
def build_latex_table(all_rows: list[dict]) -> str:
    ver_label = VERSION_TAG.replace("_", r"\_")
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{Plan de implementaci\'on en fases --- DRP"
        rf" (\texttt{{{ver_label}}})" + r"}",
        rf"  \label{{tab:fases_drp_{VERSION_TAG}}}",
        r"  \footnotesize",
        r"  \setlength{\tabcolsep}{4pt}",
        r"  \begin{tabular}{llrrrrrr}",
        r"    \toprule",
        r"    \textbf{Borough} & \textbf{Fase} & \textbf{Cob.\,(\%)} "
        r"& \textbf{Act.} & \textbf{Rem.} & \textbf{Reub.} "
        r"& \textbf{Comp.} & \textbf{Costo} \\",
        r"    \midrule",
    ]

    for borough, group in groupby(all_rows, key=lambda r: r["borough"]):
        rows = list(group)
        bor_label = borough.title()
        for i, row in enumerate(rows):
            mr = rf"\multirow{{4}}{{*}}{{{bor_label}}}" if i == 0 else ""
            lines.append(
                rf"    {mr} & {NOMBRES_FASE_TEX[row['fase']]} "
                rf"& {row['cobertura_pct']:.2f} "
                rf"& {row['N_active']} & {row['N_removido']} "
                rf"& {row['N_reubicado']} & {row['N_comprado']} & {row['f2']:.1f} \\"
            )
        lines.append(r"    \midrule")

    lines[-1] = r"    \bottomrule"
    lines += [r"  \end{tabular}", r"\end{table}"]
    return "\n".join(lines)


# ===========================================================================
# Main loop — one borough at a time
# ===========================================================================
all_rows: list[dict] = []

for borough, stem in BOROUGH_FILES.items():
    pf_path  = OUT_BASE / stem / f"pareto_front_{VERSION_TAG}.csv"
    dat_path = INST_DIR / f"{stem}.dat"

    if not pf_path.exists():
        print(f"\n  SKIP {borough}: {pf_path.relative_to(HERE)} no encontrado.")
        print(f"  -> Ejecuta ANN_drp.py --version {VERSION_TAG} primero.")
        continue

    df_front   = pd.read_csv(pf_path)
    all_points = parse_dat_all_points(dat_path)
    n1         = sum(1 for _, _, f in all_points if f == 1)

    print(f"\n  {borough}  |  frente: {len(df_front)} pts  |  flag=1: {n1}")

    phase_idx  = pick_phase_indices(df_front)
    inst_rows: list[dict] = []

    for fase_num, row_idx in enumerate(phase_idx):
        row    = df_front.iloc[row_idx]
        f1     = float(row["obj1"])
        f2     = float(row["obj2"])
        ids_str = str(row["ids"]) if pd.notna(row["ids"]) else ""
        ids_1b  = {int(x) for x in ids_str.split() if x.isdigit()}

        counts = classify_aeds(ids_1b, all_points)
        cob    = abs(f1) * 100

        data = {
            "borough":       borough,
            "stem":          stem,
            "fase":          fase_num,
            "nombre":        NOMBRES_FASE[fase_num],
            "f1":            f1,
            "f2":            f2,
            "cobertura_pct": round(cob, 4),
            **counts,
        }
        inst_rows.append(data)
        all_rows.append(data)

        print(f"    Fase {fase_num}  {NOMBRES_FASE[fase_num]:<28s}  "
              f"cob={cob:>8.4f}%  act={counts['N_active']:>5d}  "
              f"rem={counts['N_removido']:>5d}  reub={counts['N_reubicado']:>4d}  "
              f"comp={counts['N_comprado']:>4d}  F2={f2:.2f}")

    # Per-instance CSV
    inst_df   = pd.DataFrame(inst_rows).drop(columns=["borough", "stem"])
    inst_path = OUT_BASE / stem / f"fases_{VERSION_TAG}.csv"
    inst_df.to_csv(inst_path, index=False)
    print(f"    -> {inst_path.relative_to(HERE)}")


# ---------------------------------------------------------------------------
# General outputs
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
if not all_rows:
    print("Sin datos. Ejecuta primero ANN_drp.py.")
else:
    general_df   = pd.DataFrame(all_rows)
    general_path = OUT_BASE / f"fases_all_{VERSION_TAG}.csv"
    general_df.to_csv(general_path, index=False)
    print(f"CSV general   -> {general_path.relative_to(HERE)}")

    latex_str  = build_latex_table(all_rows)
    latex_path = OUT_BASE / f"fases_{VERSION_TAG}.tex"
    latex_path.write_text(latex_str, encoding="utf-8")
    print(f"LaTeX completa-> {latex_path.relative_to(HERE)}")

    # ── Tabla simplificada ────────────────────────────────────────────────
    # Columnas: Borough | Fase | Cob.(%) | Reub. | Comp. | Costo (F2)
    # Filas de totales por fase + gran total al final.
    # "Reub." = N_reubicado (costo reubicación proxy)
    # "Comp." = N_comprado  (costo instalación proxy)
    def build_latex_table_simple(rows: list[dict]) -> str:
        from itertools import groupby
        ver_label = VERSION_TAG.replace("_", r"\_")
        FASE_TEX = NOMBRES_FASE_TEX

        lines = [
            r"\begin{table}[htbp]",
            r"  \centering",
            r"  \caption{Plan de fases simplificado --- DRP"
            rf" (\texttt{{{ver_label}}})" + r"}",
            rf"  \label{{tab:fases_simple_drp_{VERSION_TAG}}}",
            r"  \footnotesize",
            r"  \setlength{\tabcolsep}{4pt}",
            r"  \begin{tabular}{llrrrr}",
            r"    \toprule",
            r"    \textbf{Borough} & \textbf{Fase}"
            r" & \textbf{Cob.\,(\%)} & \textbf{Reub.} & \textbf{Comp.} & \textbf{Costo} \\",
            r"    \midrule",
        ]
        for borough, group in groupby(rows, key=lambda r: r["borough"]):
            bor_rows = list(group)
            for i, row in enumerate(bor_rows):
                mr = rf"\multirow{{4}}{{*}}{{{borough.title()}}}" if i == 0 else ""
                lines.append(
                    rf"    {mr} & {FASE_TEX[row['fase']]}"
                    rf" & {row['cobertura_pct']:.2f}"
                    rf" & {row['N_reubicado']} & {row['N_comprado']}"
                    rf" & {row['f2']:.1f} \\"
                )
            lines.append(r"    \midrule")

        # Totals per fase
        lines[-1] = r"    \midrule"
        for fase_num in range(4):
            fase_rows = [r for r in rows if r["fase"] == fase_num]
            t_reub = sum(r["N_reubicado"] for r in fase_rows)
            t_comp = sum(r["N_comprado"]  for r in fase_rows)
            t_cost = sum(r["f2"]          for r in fase_rows)
            lines.append(
                rf"    \textit{{Total Fase {fase_num}}}"
                rf" & {FASE_TEX[fase_num]}"
                rf" & --- & {t_reub} & {t_comp} & {t_cost:.1f} \\"
            )

        # Grand total
        gt_reub = sum(r["N_reubicado"] for r in rows)
        gt_comp = sum(r["N_comprado"]  for r in rows)
        gt_cost = sum(r["f2"]          for r in rows)
        lines += [
            r"    \midrule",
            rf"    \textbf{{Total general}} & & --- & {gt_reub} & {gt_comp} & {gt_cost:.1f} \\",
            r"    \bottomrule",
            r"  \end{tabular}",
            r"\end{table}",
        ]
        return "\n".join(lines)

    latex_simple      = build_latex_table_simple(all_rows)
    latex_simple_path = OUT_BASE / f"fases_simple_{VERSION_TAG}.tex"
    latex_simple_path.write_text(latex_simple, encoding="utf-8")
    print(f"LaTeX simple  -> {latex_simple_path.relative_to(HERE)}")

    print(f"\n{'─'*70}")
    print(latex_str)
    print(f"{'─'*70}")
    print(latex_simple)
    print(f"{'─'*70}")
