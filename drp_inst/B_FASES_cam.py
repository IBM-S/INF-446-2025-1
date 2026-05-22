"""
B_FASES_cam.py
==============
Genera el plan de 4 fases de implementacion para el problema CAM (alcaldias CDMX).

Misma logica que B_FASES_drp.py, adaptada a las 16 alcaldias de camara.
Las instancias se descubren dinamicamente desde datos/inst/cam_*.dat.

Prerequisito: ejecutar ANN_cam.py con la misma version para que existan
los archivos pareto_front_{version}.csv en drp_inst/cam/{stem}/.

Salidas:
  drp_inst/cam/{stem}/fases_{version}.csv     <- 4 fases por instancia
  drp_inst/cam/fases_all_{version}.csv        <- todas las instancias
  drp_inst/cam/fases_{version}.tex            <- tabla LaTeX general

Uso:
    python B_FASES_cam.py                     # version mas reciente
    python B_FASES_cam.py --version cam_v75
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
parser = argparse.ArgumentParser(description="Plan de fases CAM desde frente de Pareto MOEA/D.")
parser.add_argument("--version", default=None, metavar="FOLDER",
                    help="Version del frente (ej. cam_v76). Si se omite: mas reciente.")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE      = Path(__file__).parent
INST_DIR  = (HERE / "../datos/inst").resolve()
MOEAD_DIR = (HERE / "../datos/res/raw_moead").resolve()
OUT_BASE  = HERE / "cam"

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

# Instance list: discovered dynamically from datos/inst/cam_*.dat
INSTANCE_STEMS: list[str] = sorted(
    (p.stem for p in INST_DIR.glob("cam_*.dat")),
    key=lambda s: int(re.search(r"^cam_(\d+)_", s).group(1)),
)


def stem_to_alcaldia(stem: str) -> str:
    """cam_NNNN_SOME_NAME -> 'SOME NAME' (matches alcaldia_norm in boundary GeoJSON)."""
    return re.sub(r"^cam_\d+_", "", stem).replace("_", " ")


# ---------------------------------------------------------------------------
# Resolve version tag from existing pareto_front files or moead folders
# ---------------------------------------------------------------------------
def _resolve_version() -> str:
    # Look for pareto_front files in the first instance that has them
    for stem in INSTANCE_STEMS:
        candidates = sorted(
            (OUT_BASE / stem).glob("pareto_front_*.csv"),
            key=lambda p: p.name, reverse=True,
        )
        if candidates:
            return re.sub(r"^pareto_front_|\.csv$", "", candidates[0].name)
    # Fallback: most recent cam_v* folder
    version_dirs = sorted(
        [d for d in MOEAD_DIR.iterdir() if d.is_dir() and d.name.startswith("cam_v")],
        key=lambda d: d.name, reverse=True,
    )
    if not version_dirs:
        raise FileNotFoundError("No se encontro ninguna version cam_v* en raw_moead.")
    return version_dirs[0].name


VERSION_TAG = args.version or _resolve_version()
print("=" * 70)
print(f"B_FASES_cam.py  |  version: {VERSION_TAG}")
print(f"Instancias descubiertas: {len(INSTANCE_STEMS)}")
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
# Classify cameras for a given installed ID set
# ---------------------------------------------------------------------------
def classify_cameras(ids_1b: set[int], all_points: list[tuple]) -> dict:
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
# LaTeX table (all alcaldias, one per section block with \multirow)
# ---------------------------------------------------------------------------
def build_latex_table(all_rows: list[dict]) -> str:
    ver_label = VERSION_TAG.replace("_", r"\_")
    lines = [
        r"\begin{longtable}{llrrrrrr}",
        r"  \caption{Plan de implementaci\'on en fases --- CAM"
        rf" (\texttt{{{ver_label}}})" + r"}",
        rf"  \label{{tab:fases_cam_{VERSION_TAG}}} \\",
        r"  \toprule",
        r"  \textbf{Alcald\'ia} & \textbf{Fase} & \textbf{Cob.\,(\%)} "
        r"& \textbf{Act.} & \textbf{Rem.} & \textbf{Reub.} "
        r"& \textbf{Comp.} & \textbf{Costo} \\",
        r"  \midrule",
        r"  \endfirsthead",
        r"  \toprule",
        r"  \textbf{Alcald\'ia} & \textbf{Fase} & \textbf{Cob.\,(\%)} "
        r"& \textbf{Act.} & \textbf{Rem.} & \textbf{Reub.} "
        r"& \textbf{Comp.} & \textbf{Costo} \\",
        r"  \midrule",
        r"  \endhead",
        r"  \midrule \multicolumn{8}{r}{\footnotesize\textit{(contin\'ua)}} \\",
        r"  \endfoot",
        r"  \bottomrule",
        r"  \endlastfoot",
    ]

    for alcaldia, group in groupby(all_rows, key=lambda r: r["alcaldia"]):
        rows = list(group)
        alc_label = alcaldia.title()
        for i, row in enumerate(rows):
            mr = rf"\multirow{{4}}{{*}}{{{alc_label}}}" if i == 0 else ""
            lines.append(
                rf"  {mr} & {NOMBRES_FASE_TEX[row['fase']]} "
                rf"& {row['cobertura_pct']:.2f} "
                rf"& {row['N_active']} & {row['N_removido']} "
                rf"& {row['N_reubicado']} & {row['N_comprado']} & {row['f2']:.1f} \\"
            )
        lines.append(r"  \midrule")

    lines[-1] = r"  \bottomrule"  # last \midrule -> \bottomrule (longtable uses \endlastfoot)
    lines.append(r"\end{longtable}")
    # Note: longtable already ends with \bottomrule via \endlastfoot
    return "\n".join(lines)


# ===========================================================================
# Main loop
# ===========================================================================
all_rows: list[dict] = []

for stem in INSTANCE_STEMS:
    alcaldia = stem_to_alcaldia(stem)
    pf_path  = OUT_BASE / stem / f"pareto_front_{VERSION_TAG}.csv"
    dat_path = INST_DIR / f"{stem}.dat"

    if not pf_path.exists():
        print(f"\n  SKIP {alcaldia}: {pf_path.relative_to(HERE)} no encontrado.")
        continue

    df_front   = pd.read_csv(pf_path)
    if df_front.empty:
        print(f"\n  SKIP {alcaldia}: pareto_front vacio.")
        continue

    all_points = parse_dat_all_points(dat_path)
    n1         = sum(1 for _, _, f in all_points if f == 1)

    print(f"\n  {alcaldia:<25s}  |  frente: {len(df_front):>4d} pts  |  flag=1: {n1:>5d}")

    phase_idx  = pick_phase_indices(df_front)
    f1_fase3   = float(df_front["obj1"].min())  # most negative = best coverage (Fase 3)
    inst_rows: list[dict] = []

    for fase_num, row_idx in enumerate(phase_idx):
        row     = df_front.iloc[row_idx]
        f1      = float(row["obj1"])
        f2      = float(row["obj2"])
        ids_str = str(row["ids"]) if pd.notna(row["ids"]) else ""
        ids_1b  = {int(x) for x in ids_str.split() if x.isdigit()}

        counts = classify_cameras(ids_1b, all_points)
        cob    = abs(f1) / abs(f1_fase3) * 100  # % del maximo alcanzable (Fase 3)

        data = {
            "alcaldia":      alcaldia,
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
              f"cob={cob:>9.4f}%  act={counts['N_active']:>6d}  "
              f"rem={counts['N_removido']:>6d}  reub={counts['N_reubicado']:>5d}  "
              f"comp={counts['N_comprado']:>5d}  F2={f2:.1f}")

    # Per-instance CSV
    inst_df   = pd.DataFrame(inst_rows).drop(columns=["alcaldia", "stem"])
    inst_path = OUT_BASE / stem / f"fases_{VERSION_TAG}.csv"
    inst_df.to_csv(inst_path, index=False)
    print(f"    -> {inst_path.relative_to(HERE)}")


# ---------------------------------------------------------------------------
# General outputs
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
if not all_rows:
    print("Sin datos. Ejecuta primero ANN_cam.py.")
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
    # Columnas: Alcaldía | Fase | Cob.(%) | Comp. (= F2, cámaras nuevas)
    # Filas de totales por fase + gran total al final.
    def build_latex_table_simple(rows: list[dict]) -> str:
        from itertools import groupby
        ver_label = VERSION_TAG.replace("_", r"\_")
        FASE_TEX  = NOMBRES_FASE_TEX

        header_row = (
            r"  \textbf{Alcald\'ia} & \textbf{Fase}"
            r" & \textbf{Cob.\,(\%)} & \textbf{C\'am. nuevas} \\"
        )
        lines = [
            r"\begin{longtable}{llrr}",
            r"  \caption{Plan de fases simplificado --- CAM"
            rf" (\texttt{{{ver_label}}})" + r"}",
            rf"  \label{{tab:fases_simple_cam_{VERSION_TAG}}} \\",
            r"  \toprule",
            header_row,
            r"  \midrule",
            r"  \endfirsthead",
            r"  \toprule",
            header_row,
            r"  \midrule",
            r"  \endhead",
            r"  \midrule \multicolumn{4}{r}{\footnotesize\textit{(contin\'ua)}} \\",
            r"  \endfoot",
            r"  \bottomrule",
            r"  \endlastfoot",
        ]
        for alcaldia, group in groupby(rows, key=lambda r: r["alcaldia"]):
            alc_rows = list(group)
            alc_label = alcaldia.title()
            for i, row in enumerate(alc_rows):
                mr = rf"\multirow{{4}}{{*}}{{{alc_label}}}" if i == 0 else ""
                lines.append(
                    rf"  {mr} & {FASE_TEX[row['fase']]}"
                    rf" & {row['cobertura_pct']:.2f} & {row['N_comprado']} \\"
                )
            lines.append(r"  \midrule")

        # Totals per fase
        lines[-1] = r"  \midrule"
        for fase_num in range(4):
            fase_rows = [r for r in rows if r["fase"] == fase_num]
            t_comp = sum(r["N_comprado"] for r in fase_rows)
            lines.append(
                rf"  \textit{{Total Fase {fase_num}}}"
                rf" & {FASE_TEX[fase_num]}"
                rf" & --- & {t_comp} \\"
            )

        # Grand total
        gt_comp = sum(r["N_comprado"] for r in rows)
        lines += [
            r"  \midrule",
            rf"  \textbf{{Total general}} & & --- & {gt_comp} \\",
        ]
        lines.append(r"\end{longtable}")
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
