"""
D_MIN_DIST.py
=============
Minimize-Maximum Distance (Z1) indicator before and after AED/camera
reallocation, for each borough (DRP) or alcaldía (CAM).

  Z1 = max_i  min_j  d(i, j)          [metres]

  i ∈ ALL points in the instance (demand proxy)
  j ∈ installed facilities
  d(i,j): Euclidean distance in the instance CRS (metres)
           DRP → EPSG:32618 (UTM 18N)
           CAM → EPSG:32614 (UTM 14N)

BEFORE: j = flag==1 points   (existing installations)
AFTER : j = Fase-3 solution  (min obj1 from pareto_front_{version}.csv)

Outputs:
  drp_inst/{problem}/minmax_dist_{version}.csv
  drp_inst/{problem}/minmax_dist_{version}.tex

Usage
-----
    python D_MIN_DIST.py --problem drp
    python D_MIN_DIST.py --problem cam
    python D_MIN_DIST.py --problem drp --version drp_v80_150k
    python D_MIN_DIST.py --problem cam --version cam_v80_150k
"""

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Minimize-Maximum Distance (Z1) before/after MOEA/D."
)
parser.add_argument(
    "--problem", required=True, choices=["drp", "cam"],
    help="Problem type: 'drp' (NYC boroughs) or 'cam' (CDMX alcaldías).",
)
parser.add_argument(
    "--version", default=None, metavar="FOLDER",
    help="Version tag (e.g. drp_v80_150k). If omitted: most recent.",
)
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE      = Path(__file__).parent
INST_DIR  = (HERE / "../datos/inst").resolve()
MOEAD_DIR = (HERE / "../datos/res/raw_moead").resolve()
OUT_BASE  = HERE / args.problem

# ---------------------------------------------------------------------------
# Problem-specific config
# ---------------------------------------------------------------------------
if args.problem == "drp":
    BOROUGH_MAP = {
        "STATEN ISLAND": "drp_657_STATEN_ISLAND",
        "BRONX":         "drp_2151_BRONX",
        "QUEENS":        "drp_2885_QUEENS",
        "BROOKLYN":      "drp_3442_BROOKLYN",
        "MANHATTAN":     "drp_4432_MANHATTAN",
    }
    INSTANCE_STEMS = list(BOROUGH_MAP.values())
    LABEL_MAP      = {v: k.title() for k, v in BOROUGH_MAP.items()}
    ENTITY_COL     = "Borough"
    VERSION_PREFIX = "drp_"
else:
    INSTANCE_STEMS = sorted(
        (p.stem for p in INST_DIR.glob("cam_*.dat")),
        key=lambda s: int(re.search(r"^cam_(\d+)_", s).group(1)),
    )
    LABEL_MAP = {
        s: re.sub(r"^cam_\d+_", "", s).replace("_", " ").title()
        for s in INSTANCE_STEMS
    }
    ENTITY_COL     = "Alcaldia"
    VERSION_PREFIX = "cam_"


# ---------------------------------------------------------------------------
# Resolve version from existing pareto_front files or raw_moead folders
# ---------------------------------------------------------------------------
def _resolve_version() -> str:
    for stem in INSTANCE_STEMS:
        candidates = sorted(
            (OUT_BASE / stem).glob("pareto_front_*.csv"),
            key=lambda p: p.name, reverse=True,
        )
        if candidates:
            return re.sub(r"^pareto_front_|\.csv$", "", candidates[0].name)
    version_dirs = sorted(
        [d for d in MOEAD_DIR.iterdir()
         if d.is_dir() and d.name.startswith(VERSION_PREFIX + "v")],
        key=lambda d: d.name, reverse=True,
    )
    if not version_dirs:
        raise FileNotFoundError(
            f"No version folders found for problem '{args.problem}'."
        )
    return version_dirs[0].name


VERSION_TAG = args.version or _resolve_version()

print("=" * 70)
print(f"D_MIN_DIST.py  |  problem: {args.problem}  |  version: {VERSION_TAG}")
print(f"Instances: {len(INSTANCE_STEMS)}")
print("=" * 70)


# ---------------------------------------------------------------------------
# Parse ALL points from a .dat instance file
# Returns list of (x, y, flag) in 1-based order.
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
# Z1 = max over all demand points of the nearest-facility distance
# ---------------------------------------------------------------------------
def compute_z1(demand_coords: np.ndarray, facility_coords: np.ndarray) -> float:
    if len(facility_coords) == 0:
        return float("inf")
    tree = cKDTree(facility_coords)
    dist, _ = tree.query(demand_coords, k=1)
    return float(np.max(dist))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
rows: list[dict] = []

for stem in INSTANCE_STEMS:
    label    = LABEL_MAP[stem]
    dat_path = INST_DIR / f"{stem}.dat"
    pf_path  = OUT_BASE / stem / f"pareto_front_{VERSION_TAG}.csv"

    if not dat_path.exists():
        print(f"\n  SKIP {label}: {dat_path.name} not found.")
        continue
    if not pf_path.exists():
        print(f"\n  SKIP {label}: pareto_front not found — "
              f"run A_ANN_{args.problem}.py --version {VERSION_TAG} first.")
        continue

    all_points = parse_dat_all_points(dat_path)
    all_coords = np.array([(x, y) for x, y, _ in all_points])

    # BEFORE: flag==1 points are the existing facilities
    before_coords = np.array([(x, y) for x, y, f in all_points if f == 1])

    # AFTER: Fase 3 = solution with is_selected==True (min obj1)
    df_pf = pd.read_csv(pf_path)
    sel   = df_pf[df_pf["is_selected"] == True]
    if sel.empty:
        sel = df_pf.loc[[df_pf["obj1"].idxmin()]]
    best_row  = sel.iloc[0]
    ids_str   = str(best_row["ids"]) if pd.notna(best_row["ids"]) else ""
    ids_1b    = [int(x) for x in ids_str.split() if x.isdigit()]
    after_coords = np.array([
        (all_points[i - 1][0], all_points[i - 1][1])
        for i in ids_1b
        if 0 < i <= len(all_points)
    ])

    z1_before = compute_z1(all_coords, before_coords)
    z1_after  = compute_z1(all_coords, after_coords)
    delta_m   = z1_after - z1_before
    delta_pct = delta_m / z1_before * 100 if z1_before > 0 else 0.0

    n1  = len(before_coords)
    naf = len(after_coords)

    print(f"\n  {label}")
    print(f"    N_antes={n1:>5d}   Z1_antes={z1_before:>10,.1f} m")
    print(f"    N_desp ={naf:>5d}   Z1_desp ={z1_after:>10,.1f} m")
    print(f"    ΔZ1 = {delta_m:+,.1f} m  ({delta_pct:+.1f}%)")

    rows.append({
        ENTITY_COL:    label,
        "Stem":        stem,
        "Version":     VERSION_TAG,
        "N_antes":     n1,
        "Z1_antes_m":  round(z1_before, 1),
        "N_desp":      naf,
        "Z1_desp_m":   round(z1_after, 1),
        "Delta_m":     round(delta_m, 1),
        "Delta_pct":   round(delta_pct, 2),
    })


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)

if not rows:
    print(f"Sin datos. Ejecuta A_ANN_{args.problem}.py primero.")
else:
    df = pd.DataFrame(rows)

    # CSV
    csv_path = OUT_BASE / f"minmax_dist_{VERSION_TAG}.csv"
    df.to_csv(csv_path, index=False)
    print(f"CSV   → {csv_path.relative_to(HERE)}")

    # Summary table in console
    print_cols = [ENTITY_COL, "N_antes", "Z1_antes_m", "N_desp", "Z1_desp_m",
                  "Delta_m", "Delta_pct"]
    print("\n" + df[print_cols].to_string(index=False))

    # ── LaTeX ────────────────────────────────────────────────────────────────
    def build_latex(rows_list: list[dict]) -> str:
        ver_label  = VERSION_TAG.replace("_", r"\_")
        prob_label = "DRP" if args.problem == "drp" else "CAM"

        if args.problem == "drp":
            col_header = r"\textbf{Borough}"
            lines = [
                r"\begin{table}[htbp]",
                r"  \centering",
                r"  \caption{Distancia m\'axima m\'inima ($Z_1$) antes y"
                r" despu\'es de MOEA/D --- " + prob_label
                + rf" (\texttt{{{ver_label}}})" + r"}",
                rf"  \label{{tab:minmax_{args.problem}_{VERSION_TAG}}}",
                r"  \small",
                r"  \begin{tabular}{lrrrr}",
                r"    \toprule",
                rf"    {col_header} & $Z_{{1,\text{{ant}}}}$\,(m)"
                r" & $Z_{1,\text{opt}}$\,(m)"
                r" & $\Delta Z_1$\,(m) & $\Delta Z_1$\,(\%) \\",
                r"    \midrule",
            ]
            for row in rows_list:
                lines.append(
                    rf"    {row[ENTITY_COL]}"
                    rf" & {row['Z1_antes_m']:,.0f}"
                    rf" & {row['Z1_desp_m']:,.0f}"
                    rf" & {row['Delta_m']:+,.0f}"
                    rf" & {row['Delta_pct']:+.1f} \\"
                )
            lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]

        else:  # longtable for CAM
            col_header = r"\textbf{Alcald\'ia}"
            header_row = (
                rf"  {col_header} & $Z_{{1,\text{{ant}}}}$\,(m)"
                r" & $Z_{1,\text{opt}}$\,(m)"
                r" & $\Delta Z_1$\,(m) & $\Delta Z_1$\,(\%) \\"
            )
            lines = [
                r"\begin{longtable}{lrrrr}",
                r"  \caption{Distancia m\'axima m\'inima ($Z_1$) antes y"
                r" despu\'es de MOEA/D --- " + prob_label
                + rf" (\texttt{{{ver_label}}})" + r"}",
                rf"  \label{{tab:minmax_{args.problem}_{VERSION_TAG}}} \\",
                r"  \toprule",
                header_row,
                r"  \midrule",
                r"  \endfirsthead",
                r"  \toprule",
                header_row,
                r"  \midrule",
                r"  \endhead",
                r"  \midrule \multicolumn{5}{r}{\footnotesize\textit{(contin\'ua)}} \\",
                r"  \endfoot",
                r"  \bottomrule",
                r"  \endlastfoot",
            ]
            for row in rows_list:
                lines.append(
                    rf"  {row[ENTITY_COL]}"
                    rf" & {row['Z1_antes_m']:,.0f}"
                    rf" & {row['Z1_desp_m']:,.0f}"
                    rf" & {row['Delta_m']:+,.0f}"
                    rf" & {row['Delta_pct']:+.1f} \\"
                )
            lines.append(r"\end{longtable}")

        return "\n".join(lines)

    latex_str  = build_latex(rows)
    latex_path = OUT_BASE / f"minmax_dist_{VERSION_TAG}.tex"
    latex_path.write_text(latex_str, encoding="utf-8")
    print(f"LaTeX → {latex_path.relative_to(HERE)}")

    print(f"\n{'─'*70}")
    print(latex_str)
    print(f"{'─'*70}")
