"""
ANN_drp.py
Average Nearest Neighbor (ANN) spatial index — BEFORE vs AFTER AED reallocation.

Formula (Clark-Evans, 1954):
    R = mean_observed_distance / expected_distance
    expected_distance = 1 / (2 * sqrt(N / A))

R < 1  → clustered  |  R ≈ 1  → random (±0.05)  |  R > 1  → uniform

BEFORE : pre-installed AEDs (flag == 1 in the instance .dat files)
AFTER  : best-coverage solution from the combined MOEA/D Pareto front

Usage
-----
    python ANN_drp.py                        # uses most recent version folder
    python ANN_drp.py --version drp_v75      # explicit folder
    python ANN_drp.py --version drp_v75 --verbose   # also prints file headers
"""

import argparse
import random
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# ---------------------------------------------------------------------------
# CLI arguments
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Compute ANN index before/after MOEA/D optimisation.")
parser.add_argument(
    "--version", default=None, metavar="FOLDER",
    help="Name of the MOEA/D results subfolder (e.g. drp_v76). "
         "If omitted, the most recent folder is used automatically.",
)
parser.add_argument(
    "--verbose", action="store_true",
    help="Print the first 30 lines of the first instance file for format inspection.",
)
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Fixed paths
# ---------------------------------------------------------------------------
HERE        = Path(__file__).parent
BOUNDS_FILE = HERE / "boundaries_borough_query.json"
INST_DIR    = (HERE / "../datos/inst").resolve()
MOEAD_DIR   = (HERE / "../datos/res/raw_moead").resolve()

# Output base: drp_inst/drp/   (general and per-instance results go here)
OUT_BASE = HERE / "drp"
OUT_BASE.mkdir(parents=True, exist_ok=True)

# Map boro_name (GeoJSON) → instance filename stem
BOROUGH_FILES = {
    "STATEN ISLAND": "drp_657_STATEN_ISLAND",
    "BRONX":         "drp_2151_BRONX",
    "QUEENS":        "drp_2885_QUEENS",
    "BROOKLYN":      "drp_3442_BROOKLYN",
    "MANHATTAN":     "drp_4432_MANHATTAN",
}

EXPECTED_N_BEFORE = {
    "STATEN ISLAND": 350,
    "BRONX":        1028,
    "QUEENS":       1191,
    "BROOKLYN":     1399,
    "MANHATTAN":    3347,
}

# ===========================================================================
# STEP 1 — Load borough boundaries and compute areas in EPSG:32618
#
# The boundary file is in geographic EPSG:4326.  Reprojecting to UTM Zone 18N
# (EPSG:32618) is necessary so that .area returns square metres, not degrees².
# ===========================================================================
print("=" * 70)
print("STEP 1 — Loading borough boundaries")
print("=" * 70)

boroughs_gdf = gpd.read_file(BOUNDS_FILE)
boroughs_utm = boroughs_gdf.to_crs(epsg=32618)
boroughs_utm["area_m2"] = boroughs_utm.geometry.area

borough_areas: dict[str, float] = dict(
    zip(boroughs_utm["boro_name"], boroughs_utm["area_m2"])
)

for name, area in sorted(borough_areas.items()):
    print(f"  {name:<15s}  {area / 1e6:,.2f} km²")


# ===========================================================================
# STEP 2 — Parse instance .dat files — extract ALL points
#
# File format (AMPL/Gurobi .dat):
#   param : coordx coordy flag prob_ohca:=
#   <1-based-index>  <coordx>  <coordy>  <flag>  <prob_ohca>
#   ...
#   ;
#
# Coordinates are already in EPSG:32618 (UTM easting/northing, metres),
# confirmed by the value magnitudes (~5×10⁵ easting, ~4.5×10⁶ northing).
#
# ALL points are stored (flag 0 and 1) in original order.  This is required
# because the MOEA/D last_gen IDs are 1-based indices into this full list:
#   all_points[id - 1]  →  (x, y, flag)
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 2 — Parsing instance files (all points)")
print("=" * 70)


def parse_dat_all_points(filepath: Path, print_header: bool = False) -> list[tuple]:
    """
    Return a list of (x, y, flag) tuples for every point in the .dat file,
    in 1-based order (list index 0 corresponds to point ID 1).
    """
    with open(filepath, "r") as fh:
        lines = fh.readlines()

    if print_header:
        print(f"\n  --- first 30 lines of {filepath.name} ---")
        for line in lines[:30]:
            print("  " + line, end="")
        print("  ---\n")

    points = []
    inside_param = False
    for line in lines:
        s = line.strip()
        if re.match(r"param\s*:\s*coordx\s+coordy\s+flag", s):
            inside_param = True
            continue
        if inside_param and s == ";":
            break
        if inside_param and s:
            parts = s.split()
            if len(parts) < 4:
                continue
            points.append((float(parts[1]), float(parts[2]), int(parts[3])))
    return points


borough_all_points: dict[str, list[tuple]] = {}

for i, (boro_name, stem) in enumerate(BOROUGH_FILES.items()):
    dat_path = INST_DIR / f"{stem}.dat"
    pts = parse_dat_all_points(dat_path, print_header=(i == 0 and args.verbose))
    borough_all_points[boro_name] = pts
    n1 = sum(1 for _, _, f in pts if f == 1)
    exp = EXPECTED_N_BEFORE[boro_name]
    ok  = "OK" if n1 == exp else f"WARNING: expected {exp}"
    print(f"  {boro_name:<15s}  total={len(pts):>4d}  flag=1={n1:>4d}  [{ok}]")


# ===========================================================================
# Helpers — ANN computation and pattern label
# ===========================================================================
def compute_ann(coords: np.ndarray, area_m2: float) -> tuple[float, float, float]:
    """
    Return (mean_observed_m, expected_dist_m, R) using a cKDTree.
    k=2 so that the self-distance (always 0) is skipped.
    """
    N = len(coords)
    if N < 2:
        raise ValueError(f"Need at least 2 points, got {N}")
    tree = cKDTree(coords)
    dist, _ = tree.query(coords, k=2)
    mean_obs = float(np.mean(dist[:, 1]))
    expected = 1.0 / (2.0 * np.sqrt(N / area_m2))
    return mean_obs, expected, mean_obs / expected


def pattern_label(R: float) -> str:
    if R < 0.95:
        return "Clustered"
    if R > 1.05:
        return "Uniform"
    return "Random"


# ===========================================================================
# STEP 3 — Compute ANN BEFORE (flag == 1 points only)
#
# These are the real-world, historically installed AEDs.  Their strong
# clustering (R << 1) reflects organic, demand-driven installation patterns
# rather than spatial planning.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 3 — ANN BEFORE (flag == 1 AEDs)")
print("=" * 70)

before_results: dict[str, dict] = {}

for boro_name in BOROUGH_FILES:
    area_m2 = borough_areas[boro_name]
    coords  = np.array([(x, y) for x, y, f in borough_all_points[boro_name] if f == 1])
    if len(coords) < 2:
        print(f"  WARNING: {boro_name} — fewer than 2 AEDs, skipping.")
        continue
    mean_obs, expected, R = compute_ann(coords, area_m2)
    pat = pattern_label(R)
    before_results[boro_name] = {
        "N": len(coords), "mean_obs": mean_obs,
        "expected": expected, "R": R, "pattern": pat,
    }
    print(f"  {boro_name:<15s}  N={len(coords):>4d}  "
          f"d_obs={mean_obs:>8.2f} m  d_exp={expected:>8.2f} m  "
          f"R={R:.4f}  [{pat}]")


# ===========================================================================
# STEP 4 — Build combined Pareto front from MOEA/D results
#
# 1. Select the experiment version folder (--version arg or most recent).
# 2. For each borough collect solutions from all 10 run folders by reading
#    last_gen_{instance}.dat.  Lines have the format:
#      <obj1>  <obj2>  - IDs instalados: <id1> <id2> ...
#    NOTE: IDs are 1-based (confirmed empirically — they start at 1 and
#    match the 1-based indexing of the instance .dat file).
# 3. Filter the merged pool for non-dominated solutions (both objectives
#    are minimised; obj1 = −coverage, obj2 = cost).
# 4. Select the solution with minimum obj1 (= maximum AED coverage).
# 5. Save the full Pareto front per instance so the selected point can be
#    reviewed and a different one chosen if needed.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 4 — Building combined Pareto front from MOEA/D results")
print("=" * 70)

# --- select version folder ---
version_dirs = sorted(
    [d for d in MOEAD_DIR.iterdir() if d.is_dir()],
    key=lambda d: d.name, reverse=True,
)
if args.version:
    chosen_version = MOEAD_DIR / args.version
    if not chosen_version.is_dir():
        raise FileNotFoundError(
            f"Version folder not found: {chosen_version}\n"
            f"Available: {[d.name for d in version_dirs]}"
        )
else:
    chosen_version = version_dirs[0]

VERSION_TAG = chosen_version.name   # used in all output filenames
print(f"  Using version: {VERSION_TAG}")
print(f"  Available    : {[d.name for d in version_dirs[:6]]}")


def parse_last_gen(filepath: Path) -> list[dict]:
    """Parse a last_gen_*.dat file into a list of {obj1, obj2, ids} dicts."""
    solutions = []
    pattern = re.compile(
        r"^([+-]?\d+\.\d+(?:[eE][+-]?\d+)?)\s+"
        r"([+-]?\d+\.\d+(?:[eE][+-]?\d+)?)\s+"
        r"-\s+IDs instalados:\s*(.*)$"
    )
    with open(filepath, "r") as fh:
        for line in fh:
            m = pattern.match(line.strip())
            if m:
                solutions.append({
                    "obj1": float(m.group(1)),
                    "obj2": float(m.group(2)),
                    "ids":  [int(x) for x in m.group(3).split() if x],
                })
    return solutions


def dedup_solutions(solutions: list[dict]) -> tuple[list[dict], int]:
    """
    Remove solutions with duplicate (obj1, obj2) pairs.
    Comparison uses 7 decimal places — the same precision stored in the files —
    so that genuinely equal objective values are recognised as duplicates
    regardless of minor float-representation noise.
    When duplicates exist, one is kept at random.
    Returns (deduplicated list, number of duplicates removed).
    """
    groups: dict[tuple, list[dict]] = {}
    for sol in solutions:
        key = (sol["obj1"], sol["obj2"])   # exact float — no rounding
        groups.setdefault(key, []).append(sol)
    deduped = [random.choice(group) for group in groups.values()]
    return deduped, len(solutions) - len(deduped)


def non_dominated(solutions: list[dict]) -> list[dict]:
    """Return Pareto-non-dominated solutions (minimising obj1 and obj2)."""
    dominated = [False] * len(solutions)
    for i, a in enumerate(solutions):
        if dominated[i]:
            continue
        for j, b in enumerate(solutions):
            if i == j or dominated[j]:
                continue
            if (a["obj1"] <= b["obj1"] and a["obj2"] <= b["obj2"] and
                    (a["obj1"] < b["obj1"] or a["obj2"] < b["obj2"])):
                dominated[j] = True
    return [s for i, s in enumerate(solutions) if not dominated[i]]


after_solutions: dict[str, dict] = {}

for boro_name, stem in BOROUGH_FILES.items():
    boro_dir = chosen_version / stem
    all_sols = []

    for run_idx in range(1, 11):
        last_file = boro_dir / f"run_{run_idx}" / f"last_gen_{stem}.dat"
        if not last_file.exists():
            print(f"  WARNING: missing {last_file.relative_to(MOEAD_DIR)} — skipping run.")
            continue
        all_sols.extend(parse_last_gen(last_file))

    if not all_sols:
        print(f"  WARNING: no solutions found for {boro_name} — skipping.")
        continue

    unique_sols, n_dupes = dedup_solutions(all_sols)
    pareto = non_dominated(unique_sols)

    # Select solution with maximum coverage (minimum obj1)
    best = min(pareto, key=lambda s: s["obj1"])
    best_idx = pareto.index(best)
    after_solutions[boro_name] = best

    # ------------------------------------------------------------------
    # Save Pareto front for this instance
    # drp_inst/drp/{stem}/pareto_front_{version}.csv
    # Columns: obj1, obj2, N_installed, is_selected, ids
    # ------------------------------------------------------------------
    inst_out = OUT_BASE / stem
    inst_out.mkdir(parents=True, exist_ok=True)

    pf_rows = []
    for k, sol in enumerate(pareto):
        pf_rows.append({
            "obj1":        sol["obj1"],
            "obj2":        sol["obj2"],
            "N_installed": len(sol["ids"]),
            "is_selected": (k == best_idx),
            "ids":         " ".join(map(str, sol["ids"])),
        })
    pf_df = pd.DataFrame(pf_rows).sort_values("obj1")
    pf_path = inst_out / f"pareto_front_{VERSION_TAG}.csv"
    pf_df.to_csv(pf_path, index=False)

    print(
        f"  {boro_name:<15s}  pool={len(all_sols):>5d}  dupes={n_dupes:>4d}  "
        f"unique={len(unique_sols):>4d}  pareto={len(pareto):>4d}  "
        f"best → obj1={best['obj1']:.7f}  obj2={best['obj2']:.7f}  "
        f"N={len(best['ids']):>4d}  → {pf_path.relative_to(HERE)}"
    )


# ===========================================================================
# STEP 5 — Compute ANN AFTER (optimised solution)
#
# IDs from the selected Pareto solution are 1-based → convert to 0-based
# to index into the borough_all_points list.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 5 — ANN AFTER (optimised MOEA/D solution)")
print("=" * 70)

after_results: dict[str, dict] = {}

for boro_name, stem in BOROUGH_FILES.items():
    if boro_name not in after_solutions:
        continue
    area_m2 = borough_areas[boro_name]
    pts      = borough_all_points[boro_name]
    ids_1b   = after_solutions[boro_name]["ids"]

    coords = []
    for id_1b in ids_1b:
        idx = id_1b - 1
        if idx < 0 or idx >= len(pts):
            print(f"  WARNING: ID {id_1b} out of range for {boro_name} — skipping.")
            continue
        x, y, _ = pts[idx]
        coords.append((x, y))

    coords = np.array(coords)
    if len(coords) < 2:
        print(f"  WARNING: {boro_name} — fewer than 2 AFTER AEDs, skipping.")
        continue

    mean_obs, expected, R = compute_ann(coords, area_m2)
    pat = pattern_label(R)
    after_results[boro_name] = {
        "N": len(coords), "mean_obs": mean_obs,
        "expected": expected, "R": R, "pattern": pat,
    }
    print(f"  {boro_name:<15s}  N={len(coords):>4d}  "
          f"d_obs={mean_obs:>8.2f} m  d_exp={expected:>8.2f} m  "
          f"R={R:.4f}  [{pat}]")


# ===========================================================================
# STEP 6 — Build comparison table, print, and save
#
# Outputs:
#   drp_inst/drp/ann_comparison_{version}.csv        ← all boroughs, general
#   drp_inst/drp/{instance}/ann_results_{version}.csv ← per-instance detail
#
# Delta_ANN = R_after − R_before.
# Positive Delta → optimisation moved distribution toward uniform.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 6 — Comparison table")
print("=" * 70)

rows = []
for boro_name, stem in BOROUGH_FILES.items():
    if boro_name not in before_results or boro_name not in after_results:
        continue
    bef   = before_results[boro_name]
    aft   = after_results[boro_name]
    delta = aft["R"] - bef["R"]
    rows.append({
        "Borough":        boro_name.title(),
        "Version":        VERSION_TAG,
        "Area_km2":       round(borough_areas[boro_name] / 1e6, 2),
        "N_before":       bef["N"],
        "Mean_before_m":  round(bef["mean_obs"], 2),
        "Exp_before_m":   round(bef["expected"], 2),
        "ANN_before":     round(bef["R"], 4),
        "Pattern_before": bef["pattern"],
        "N_after":        aft["N"],
        "Mean_after_m":   round(aft["mean_obs"], 2),
        "Exp_after_m":    round(aft["expected"], 2),
        "ANN_after":      round(aft["R"], 4),
        "Pattern_after":  aft["pattern"],
        "Delta_ANN":      round(delta, 4),
    })

df = pd.DataFrame(rows)

# Print compact version (subset of columns for readability)
print_cols = ["Borough", "N_before", "ANN_before", "Pattern_before",
              "N_after",  "ANN_after",  "Pattern_after",  "Delta_ANN"]
print("\n" + df[print_cols].to_string(index=False))
print()

# Summary interpretation
print("=" * 70)
print("SUMMARY")
print("=" * 70)
for _, row in df.iterrows():
    direction = "more uniform" if row["Delta_ANN"] > 0 else "more clustered"
    print(
        f"  {row['Borough']:<15s}  "
        f"R: {row['ANN_before']:.4f} → {row['ANN_after']:.4f}  "
        f"(Δ={row['Delta_ANN']:+.4f})  {direction}  "
        f"(N: {row['N_before']} → {row['N_after']})"
    )

# --- Save general comparison ---
general_path = OUT_BASE / f"ann_comparison_{VERSION_TAG}.csv"
df.to_csv(general_path, index=False)
print(f"\n  General results  → {general_path.relative_to(HERE)}")

# --- Save per-instance ANN results ---
for boro_name, stem in BOROUGH_FILES.items():
    if boro_name not in before_results or boro_name not in after_results:
        continue
    bef = before_results[boro_name]
    aft = after_results[boro_name]
    inst_df = pd.DataFrame([
        {
            "state":          "before",
            "version":        "original (flag=1)",
            "N_AEDs":         bef["N"],
            "Area_km2":       round(borough_areas[boro_name] / 1e6, 2),
            "Mean_Obs_Dist_m": round(bef["mean_obs"], 2),
            "Expected_Dist_m": round(bef["expected"], 2),
            "ANN_Index_R":    round(bef["R"], 4),
            "Pattern":        bef["pattern"],
        },
        {
            "state":          "after",
            "version":        VERSION_TAG,
            "N_AEDs":         aft["N"],
            "Area_km2":       round(borough_areas[boro_name] / 1e6, 2),
            "Mean_Obs_Dist_m": round(aft["mean_obs"], 2),
            "Expected_Dist_m": round(aft["expected"], 2),
            "ANN_Index_R":    round(aft["R"], 4),
            "Pattern":        aft["pattern"],
        },
    ])
    inst_path = OUT_BASE / stem / f"ann_results_{VERSION_TAG}.csv"
    inst_df.to_csv(inst_path, index=False)
    print(f"  {boro_name:<15s}  → {inst_path.relative_to(HERE)}")

# --- LaTeX table ---
def build_latex_table_ann(rows: list[dict]) -> str:
    ver_label = VERSION_TAG.replace("_", r"\_")
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{\'Indice de Vecino M\'as Cercano (ANN) --- DRP"
        rf" (\texttt{{{ver_label}}})" + r"}",
        rf"  \label{{tab:ann_drp_{VERSION_TAG}}}",
        r"  \footnotesize",
        r"  \setlength{\tabcolsep}{4pt}",
        r"  \begin{tabular}{lrrrrrrrrr}",
        r"    \toprule",
        r"    & & \multicolumn{3}{c}{\textbf{Antes (flag=1)}}"
        r" & \multicolumn{3}{c}{\textbf{Despu\'es (MOEA/D)}} & \\",
        r"    \cmidrule(lr){3-5} \cmidrule(lr){6-8}",
        r"    \textbf{Borough} & \textbf{\'Area (km$^2$)}"
        r" & $N$ & $\bar{d}$\,(m) & $R$"
        r" & $N$ & $\bar{d}$\,(m) & $R$ & $\Delta R$ \\",
        r"    \midrule",
    ]
    for row in rows:
        lines.append(
            rf"    {row['Borough'].title()} & {row['Area_km2']:,.0f}"
            rf" & {row['N_before']} & {row['Mean_before_m']:,.0f} & {row['ANN_before']:.4f}"
            rf" & {row['N_after']} & {row['Mean_after_m']:,.0f} & {row['ANN_after']:.4f}"
            rf" & {row['Delta_ANN']:+.4f} \\"
        )
    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)

latex_str  = build_latex_table_ann(rows)
latex_path = OUT_BASE / f"ann_{VERSION_TAG}.tex"
latex_path.write_text(latex_str, encoding="utf-8")
print(f"  LaTeX completa   → {latex_path.relative_to(HERE)}")

# --- LaTeX simple: solo Borough | R_ant | R_opt | ΔR ---
def build_latex_table_ann_simple(rows: list[dict]) -> str:
    ver_label = VERSION_TAG.replace("_", r"\_")
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{\'Indice ANN antes y despu\'es de MOEA/D --- DRP"
        rf" (\texttt{{{ver_label}}})" + r"}",
        rf"  \label{{tab:ann_simple_drp_{VERSION_TAG}}}",
        r"  \small",
        r"  \begin{tabular}{lrrrr}",
        r"    \toprule",
        r"    \textbf{Borough} & \textbf{\'Area (km$^2$)} & $R_{\text{ant}}$ & $R_{\text{opt}}$ & $\Delta R$ \\",
        r"    \midrule",
    ]
    for row in rows:
        delta_sign = "+" if row["Delta_ANN"] >= 0 else ""
        lines.append(
            rf"    {row['Borough'].title()} & {row['Area_km2']:,.0f}"
            rf" & {row['ANN_before']:.4f}"
            rf" & {row['ANN_after']:.4f} & {delta_sign}{row['Delta_ANN']:.4f} \\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    return "\n".join(lines)

latex_simple      = build_latex_table_ann_simple(rows)
latex_simple_path = OUT_BASE / f"ann_simple_{VERSION_TAG}.tex"
latex_simple_path.write_text(latex_simple, encoding="utf-8")
print(f"  LaTeX simple     → {latex_simple_path.relative_to(HERE)}")
print(f"\n{'─'*70}")
print(latex_str)
print(f"{'─'*70}")
print(latex_simple)
print(f"{'─'*70}")
