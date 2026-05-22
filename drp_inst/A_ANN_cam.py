"""
ANN_cam.py
Average Nearest Neighbor (ANN) spatial index — BEFORE vs AFTER camera reallocation.
Study area: 16 alcaldías of Mexico City (CDMX).

Formula (Clark-Evans, 1954):
    R = mean_observed_distance / expected_distance
    expected_distance = 1 / (2 * sqrt(N / A))

R < 1  → clustered  |  R ≈ 1  → random (±0.05)  |  R > 1  → uniform

BEFORE : pre-installed cameras (flag == 1 in the instance .dat files)
AFTER  : best-coverage solution from the combined MOEA/D Pareto front
         (most recent cam_v* experiment folder, all 10 runs merged)

CRS used for metric computations: EPSG:32614 (UTM Zone 14N — standard for CDMX)

Boundary file: datos/viz/boundaries_alcaldias_4326.geojson
  - Built by visualizador_web/build_alcaldias_boundaries.py
  - Dissolves colonia-level polygons (DemograficosD_GJ.geojson) by alcaldia_norm
  - Stored in EPSG:4326; reprojected here to EPSG:32614 for area computation

Usage
-----
    python ANN_cam.py                        # uses most recent cam_v* folder
    python ANN_cam.py --version cam_v75      # explicit folder
    python ANN_cam.py --version cam_v75 --verbose
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
parser = argparse.ArgumentParser(description="Compute ANN index before/after MOEA/D optimisation (cameras).")
parser.add_argument(
    "--version", default=None, metavar="FOLDER",
    help="Name of the MOEA/D cam results subfolder (e.g. cam_v76). "
         "If omitted, the most recent cam_v* folder is used automatically.",
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
BOUNDS_FILE = (HERE / "../datos/viz/boundaries_alcaldias_4326.geojson").resolve()
INST_DIR    = (HERE / "../datos/inst").resolve()
MOEAD_DIR   = (HERE / "../datos/res/raw_moead").resolve()

# Output base: drp_inst/cam/
OUT_BASE = HERE / "cam"
OUT_BASE.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Build instance list dynamically from datos/inst/cam_*.dat
# Name mapping: cam_NNNN_SOME_NAME → "SOME NAME" (strip prefix, _ → space)
# This matches the alcaldia_norm property in the boundary GeoJSON.
# Example: cam_24363_GUSTAVO_A._MADERO → "GUSTAVO A. MADERO"
# ---------------------------------------------------------------------------
def stem_to_alcaldia(stem: str) -> str:
    return re.sub(r"^cam_\d+_", "", stem).replace("_", " ")


INSTANCE_STEMS: list[str] = sorted(
    (p.stem for p in INST_DIR.glob("cam_*.dat")),
    key=lambda s: int(re.search(r"^cam_(\d+)_", s).group(1)),
)

print("=" * 70)
print(f"Found {len(INSTANCE_STEMS)} camera instances in {INST_DIR.relative_to(HERE.parent)}")
for s in INSTANCE_STEMS:
    print(f"  {s:<45s}  → alcaldía: {stem_to_alcaldia(s)}")


# ===========================================================================
# STEP 1 — Load alcaldía boundaries and compute areas in EPSG:32614
#
# The boundary GeoJSON is in EPSG:4326 (built by build_alcaldias_boundaries.py).
# Reprojecting to UTM Zone 14N (EPSG:32614) — the standard metric CRS for
# Mexico City — is required so that .area returns square metres.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 1 — Loading alcaldía boundaries")
print("=" * 70)

boroughs_gdf = gpd.read_file(BOUNDS_FILE)              # EPSG:4326
boroughs_utm = boroughs_gdf.to_crs(epsg=32614)         # reproject → UTM 14N
boroughs_utm["area_m2"] = boroughs_utm.geometry.area

alcaldia_areas: dict[str, float] = dict(
    zip(boroughs_utm["alcaldia_norm"], boroughs_utm["area_m2"])
)

print(f"  Loaded {len(alcaldia_areas)} alcaldías (EPSG:32614)")
for name, area in sorted(alcaldia_areas.items()):
    print(f"  {name:<25s}  {area / 1e6:,.2f} km²")

# Check every instance has a matching boundary
print()
for stem in INSTANCE_STEMS:
    alc = stem_to_alcaldia(stem)
    if alc not in alcaldia_areas:
        print(f"  WARNING: no boundary found for '{alc}' (stem: {stem})")


# ===========================================================================
# STEP 2 — Parse instance .dat files — extract ALL points
#
# File format (AMPL/Gurobi .dat):
#   param : coordx coordy flag prob_ohca:=
#   <1-based-index>  <coordx>  <coordy>  <flag>  <prob_ohca>
#   ...
#   ;
#
# Coordinates are in EPSG:32614 (UTM Zone 14N, metres), confirmed by the
# value magnitudes (~490 000 easting, ~2 120 000 northing for CDMX).
#
# ALL points stored in 1-based order so that MOEA/D IDs map directly:
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


instance_all_points: dict[str, list[tuple]] = {}

for i, stem in enumerate(INSTANCE_STEMS):
    dat_path = INST_DIR / f"{stem}.dat"
    pts = parse_dat_all_points(dat_path, print_header=(i == 0 and args.verbose))
    instance_all_points[stem] = pts
    n1 = sum(1 for _, _, f in pts if f == 1)
    print(f"  {stem:<45s}  total={len(pts):>5d}  flag=1={n1:>5d}")


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
# Pre-installed cameras reflect historical/operational placement decisions.
# Their spatial pattern (R value) is the baseline for comparison.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 3 — ANN BEFORE (flag == 1 cameras)")
print("=" * 70)

before_results: dict[str, dict] = {}

for stem in INSTANCE_STEMS:
    alc = stem_to_alcaldia(stem)
    if alc not in alcaldia_areas:
        print(f"  SKIP {stem} — no boundary area available")
        continue

    area_m2 = alcaldia_areas[alc]
    coords  = np.array([(x, y) for x, y, f in instance_all_points[stem] if f == 1])

    if len(coords) < 2:
        print(f"  WARNING: {alc} — fewer than 2 flag-1 cameras, skipping.")
        continue

    mean_obs, expected, R = compute_ann(coords, area_m2)
    pat = pattern_label(R)
    before_results[stem] = {
        "N": len(coords), "mean_obs": mean_obs,
        "expected": expected, "R": R, "pattern": pat,
    }
    print(f"  {alc:<25s}  N={len(coords):>5d}  "
          f"d_obs={mean_obs:>8.2f} m  d_exp={expected:>8.2f} m  "
          f"R={R:.4f}  [{pat}]")


# ===========================================================================
# STEP 4 — Build combined Pareto front from MOEA/D results
#
# 1. Select the most recent cam_v* version folder (or use --version arg).
# 2. For each instance collect solutions from all 10 run folders by reading
#    last_gen_{stem}.dat.  Line format:
#      <obj1>  <obj2>  - IDs instalados: <id1> <id2> ...
#    IDs are 1-based indices into the full instance point list.
# 3. Deduplicate by exact (obj1, obj2) before filtering for non-dominance.
#    When duplicates exist, one is kept at random.
# 4. Filter for Pareto non-dominance (minimising both obj1 and obj2).
# 5. Select the solution with minimum obj1 (= maximum camera coverage).
# 6. Save the full Pareto front per instance for review.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 4 — Building combined Pareto front from MOEA/D results")
print("=" * 70)

# --- select version folder (only cam_v* folders) ---
cam_version_dirs = sorted(
    [d for d in MOEAD_DIR.iterdir() if d.is_dir() and d.name.startswith("cam_")],
    key=lambda d: d.name, reverse=True,
)
if args.version:
    chosen_version = MOEAD_DIR / args.version
    if not chosen_version.is_dir():
        raise FileNotFoundError(
            f"Version folder not found: {chosen_version}\n"
            f"Available cam folders: {[d.name for d in cam_version_dirs]}"
        )
else:
    chosen_version = cam_version_dirs[0]

VERSION_TAG = chosen_version.name
print(f"  Using version : {VERSION_TAG}")
print(f"  Available cam : {[d.name for d in cam_version_dirs]}")


def parse_last_gen(filepath: Path) -> list[dict]:
    """Parse a last_gen_*.dat file into a list of {obj1, obj2, ids} dicts."""
    solutions = []
    pattern = re.compile(
        r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+"
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
    Remove solutions with duplicate (obj1, obj2) pairs using exact float
    comparison (values come directly from the file — no rounding applied).
    When duplicates exist, one is kept at random.
    Returns (deduplicated list, number of duplicates removed).
    """
    groups: dict[tuple, list[dict]] = {}
    for sol in solutions:
        key = (sol["obj1"], sol["obj2"])    # exact float — no rounding
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

for stem in INSTANCE_STEMS:
    boro_dir = chosen_version / stem
    if not boro_dir.is_dir():
        print(f"  WARNING: {stem} — folder not found in {VERSION_TAG}, skipping.")
        continue

    all_sols = []
    for run_idx in range(1, 11):
        last_file = boro_dir / f"run_{run_idx}" / f"last_gen_{stem}.dat"
        if not last_file.exists():
            print(f"  WARNING: missing {last_file.relative_to(MOEAD_DIR)} — skipping run.")
            continue
        all_sols.extend(parse_last_gen(last_file))

    if not all_sols:
        print(f"  WARNING: no solutions found for {stem} — skipping.")
        continue

    unique_sols, n_dupes = dedup_solutions(all_sols)
    pareto = non_dominated(unique_sols)

    best = min(pareto, key=lambda s: s["obj1"])
    best_idx = pareto.index(best)
    after_solutions[stem] = best

    # Save Pareto front: drp_inst/cam/{stem}/pareto_front_{version}.csv
    inst_out = OUT_BASE / stem
    inst_out.mkdir(parents=True, exist_ok=True)

    pf_rows = [{
        "obj1":        sol["obj1"],
        "obj2":        sol["obj2"],
        "N_installed": len(sol["ids"]),
        "is_selected": (k == best_idx),
        "ids":         " ".join(map(str, sol["ids"])),
    } for k, sol in enumerate(pareto)]

    pf_df = pd.DataFrame(pf_rows).sort_values("obj1")
    pf_path = inst_out / f"pareto_front_{VERSION_TAG}.csv"
    pf_df.to_csv(pf_path, index=False)

    alc = stem_to_alcaldia(stem)
    print(
        f"  {alc:<25s}  pool={len(all_sols):>5d}  dupes={n_dupes:>4d}  "
        f"unique={len(unique_sols):>5d}  pareto={len(pareto):>4d}  "
        f"best → obj1={best['obj1']}  obj2={best['obj2']}  N={len(best['ids']):>5d}"
    )


# ===========================================================================
# STEP 5 — Compute ANN AFTER (optimised solution)
#
# IDs from the selected Pareto solution are 1-based → subtract 1 for the
# 0-based list index.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 5 — ANN AFTER (optimised MOEA/D solution)")
print("=" * 70)

after_results: dict[str, dict] = {}

for stem in INSTANCE_STEMS:
    if stem not in after_solutions:
        continue
    alc     = stem_to_alcaldia(stem)
    area_m2 = alcaldia_areas.get(alc)
    if area_m2 is None:
        continue

    pts    = instance_all_points[stem]
    ids_1b = after_solutions[stem]["ids"]

    coords = []
    for id_1b in ids_1b:
        idx = id_1b - 1
        if idx < 0 or idx >= len(pts):
            print(f"  WARNING: ID {id_1b} out of range for {alc} — skipping point.")
            continue
        x, y, _ = pts[idx]
        coords.append((x, y))

    coords = np.array(coords)
    if len(coords) < 2:
        print(f"  WARNING: {alc} — fewer than 2 AFTER cameras, skipping ANN.")
        continue

    mean_obs, expected, R = compute_ann(coords, area_m2)
    pat = pattern_label(R)
    after_results[stem] = {
        "N": len(coords), "mean_obs": mean_obs,
        "expected": expected, "R": R, "pattern": pat,
    }
    print(f"  {alc:<25s}  N={len(coords):>5d}  "
          f"d_obs={mean_obs:>8.2f} m  d_exp={expected:>8.2f} m  "
          f"R={R:.4f}  [{pat}]")


# ===========================================================================
# STEP 6 — Build comparison table, print, and save
#
# Outputs:
#   drp_inst/cam/ann_comparison_{version}.csv          ← all alcaldías, general
#   drp_inst/cam/{stem}/ann_results_{version}.csv      ← per-instance detail
#
# Delta_ANN = R_after − R_before.
# Positive Delta → optimisation moved distribution toward uniform.
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 6 — Comparison table")
print("=" * 70)

rows = []
for stem in INSTANCE_STEMS:
    if stem not in before_results or stem not in after_results:
        continue
    bef   = before_results[stem]
    aft   = after_results[stem]
    alc   = stem_to_alcaldia(stem)
    delta = aft["R"] - bef["R"]
    rows.append({
        "Alcaldia":       alc.title(),
        "Instance":       stem,
        "Version":        VERSION_TAG,
        "Area_km2":       round(alcaldia_areas[alc] / 1e6, 2),
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

print_cols = ["Alcaldia", "N_before", "ANN_before", "Pattern_before",
              "N_after",  "ANN_after",  "Pattern_after",  "Delta_ANN"]
print("\n" + df[print_cols].to_string(index=False))
print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)
for _, row in df.iterrows():
    direction = "more uniform" if row["Delta_ANN"] > 0 else "more clustered"
    print(
        f"  {row['Alcaldia']:<25s}  "
        f"R: {row['ANN_before']:.4f} → {row['ANN_after']:.4f}  "
        f"(Δ={row['Delta_ANN']:+.4f})  {direction}  "
        f"(N: {row['N_before']} → {row['N_after']})"
    )

# Save general comparison
general_path = OUT_BASE / f"ann_comparison_{VERSION_TAG}.csv"
df.to_csv(general_path, index=False)
print(f"\n  General results  → {general_path.relative_to(HERE)}")

# Save per-instance ANN results
for stem in INSTANCE_STEMS:
    if stem not in before_results or stem not in after_results:
        continue
    bef = before_results[stem]
    aft = after_results[stem]
    alc = stem_to_alcaldia(stem)
    inst_df = pd.DataFrame([
        {
            "state":           "before",
            "version":         "original (flag=1)",
            "N_cameras":       bef["N"],
            "Area_km2":        round(alcaldia_areas[alc] / 1e6, 2),
            "Mean_Obs_Dist_m": round(bef["mean_obs"], 2),
            "Expected_Dist_m": round(bef["expected"], 2),
            "ANN_Index_R":     round(bef["R"], 4),
            "Pattern":         bef["pattern"],
        },
        {
            "state":           "after",
            "version":         VERSION_TAG,
            "N_cameras":       aft["N"],
            "Area_km2":        round(alcaldia_areas[alc] / 1e6, 2),
            "Mean_Obs_Dist_m": round(aft["mean_obs"], 2),
            "Expected_Dist_m": round(aft["expected"], 2),
            "ANN_Index_R":     round(aft["R"], 4),
            "Pattern":         aft["pattern"],
        },
    ])
    inst_path = OUT_BASE / stem / f"ann_results_{VERSION_TAG}.csv"
    inst_df.to_csv(inst_path, index=False)
    print(f"  {alc:<25s}  → {inst_path.relative_to(HERE)}")

# --- LaTeX table (longtable — hasta 16 alcaldías) ---
def build_latex_table_ann(rows: list[dict]) -> str:
    ver_label = VERSION_TAG.replace("_", r"\_")
    header_row = (
        r"    \textbf{Alcald\'ia} & \textbf{\'Area (km$^2$)}"
        r" & $N$ & $\bar{d}$\,(m) & $R$"
        r" & $N$ & $\bar{d}$\,(m) & $R$ & $\Delta R$ \\"
    )
    lines = [
        r"\begin{longtable}{lrrrrrrrrr}",
        r"  \caption{\'Indice de Vecino M\'as Cercano (ANN) --- CAM"
        rf" (\texttt{{{ver_label}}})" + r"}",
        rf"  \label{{tab:ann_cam_{VERSION_TAG}}} \\",
        r"  \toprule",
        r"  & & \multicolumn{3}{c}{\textbf{Antes (flag=1)}}"
        r" & \multicolumn{3}{c}{\textbf{Despu\'es (MOEA/D)}} & \\",
        r"  \cmidrule(lr){3-5} \cmidrule(lr){6-8}",
        header_row,
        r"  \midrule",
        r"  \endfirsthead",
        r"  \toprule",
        r"  & & \multicolumn{3}{c}{\textbf{Antes (flag=1)}}"
        r" & \multicolumn{3}{c}{\textbf{Despu\'es (MOEA/D)}} & \\",
        r"  \cmidrule(lr){3-5} \cmidrule(lr){6-8}",
        header_row,
        r"  \midrule",
        r"  \endhead",
        r"  \midrule \multicolumn{9}{r}{\footnotesize\textit{(contin\'ua)}} \\",
        r"  \endfoot",
        r"  \bottomrule",
        r"  \endlastfoot",
    ]
    for row in rows:
        lines.append(
            rf"  {row['Alcaldia'].title()} & {row['Area_km2']:,.0f}"
            rf" & {row['N_before']} & {row['Mean_before_m']:,.0f} & {row['ANN_before']:.4f}"
            rf" & {row['N_after']} & {row['Mean_after_m']:,.0f} & {row['ANN_after']:.4f}"
            rf" & {row['Delta_ANN']:+.4f} \\"
        )
    lines.append(r"\end{longtable}")
    return "\n".join(lines)

latex_str  = build_latex_table_ann(rows)
latex_path = OUT_BASE / f"ann_{VERSION_TAG}.tex"
latex_path.write_text(latex_str, encoding="utf-8")
print(f"  LaTeX completa   → {latex_path.relative_to(HERE)}")

# --- LaTeX simple: solo Alcaldía | R_ant | R_opt | ΔR ---
def build_latex_table_ann_simple(rows: list[dict]) -> str:
    ver_label = VERSION_TAG.replace("_", r"\_")
    header_row = (
        r"    \textbf{Alcald\'ia} & \textbf{\'Area (km$^2$)} & $R_{\text{ant}}$ & $R_{\text{opt}}$ & $\Delta R$ \\"
    )
    lines = [
        r"\begin{longtable}{lrrrr}",
        r"  \caption{\'Indice ANN antes y despu\'es de MOEA/D --- CAM"
        rf" (\texttt{{{ver_label}}})" + r"}",
        rf"  \label{{tab:ann_simple_cam_{VERSION_TAG}}} \\",
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
    for row in rows:
        delta_sign = "+" if row["Delta_ANN"] >= 0 else ""
        lines.append(
            rf"  {row['Alcaldia'].title()} & {row['Area_km2']:,.0f}"
            rf" & {row['ANN_before']:.4f}"
            rf" & {row['ANN_after']:.4f} & {delta_sign}{row['Delta_ANN']:.4f} \\"
        )
    lines.append(r"\end{longtable}")
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
