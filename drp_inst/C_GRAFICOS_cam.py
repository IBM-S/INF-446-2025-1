#!/usr/bin/env python3
"""
C_GRAFICOS_cam.py
=================
Genera mapas ANTES y DESPUÉS (Fase 3 de MOEA/D) para cada alcaldía CDMX.

ANTES  : KDE de demanda + cámaras preinstaladas (flag=1, todas como ●).
DESPUÉS: KDE de demanda + solución Fase 3 del frente de Pareto, con
         puntos clasificados en 3 categorías:
           Kept    (●) — flag=1 Y en la solución optimizada
           New     (■) — flag=0,  en la solución optimizada
           Removed (✕) — flag=1, NO en la solución optimizada
         (Para CAM, Removed siempre es 0 — las cámaras no se retiran.)

Fuentes de datos:
    datos/inst/cam_*.dat                          — nodos candidatos + cámaras
    datos/viz/boundaries_alcaldias_4326.geojson   — boundaries CDMX (EPSG:4326)
    drp_inst/cam/{stem}/pareto_front_{v}.csv      — frente MOEA/D

Salidas (drp_inst/figures/):
    cam_before_{stem}.png    — estado inicial por alcaldía
    cam_fase3_{stem}.png     — Fase 3 por alcaldía
    cam_before_ALL.png       — panel combinado ANTES (grilla dinámica)
    cam_fase3_ALL.png        — panel combinado Fase 3 (grilla dinámica)

Uso:
    python C_GRAFICOS_cam.py
    python C_GRAFICOS_cam.py --version cam_v76
    python C_GRAFICOS_cam.py --no-legend
    python C_GRAFICOS_cam.py --no-basemap
"""

import argparse
import math
import re
from pathlib import Path

import contextily as ctx
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.stats import gaussian_kde

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
HERE       = Path(__file__).parent
BOUNDS_FILE = (HERE / "../datos/viz/boundaries_alcaldias_4326.geojson").resolve()
INST_DIR    = (HERE / "../datos/inst").resolve()
OUT_BASE    = HERE / "cam"
OUT_DIR     = HERE / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EPSG_UTM = 32614
_TR = Transformer.from_crs(f"EPSG:{EPSG_UTM}", "EPSG:3857", always_xy=True)

# Instances ordered by size (numeric part of stem)
INSTANCE_STEMS: list[str] = sorted(
    (p.stem for p in INST_DIR.glob("cam_*.dat")),
    key=lambda s: int(re.search(r"^cam_(\d+)_", s).group(1)),
)

def stem_to_alcaldia(stem: str) -> str:
    """cam_NNNN_SOME_NAME → 'SOME NAME'."""
    return re.sub(r"^cam_\d+_", "", stem).replace("_", " ")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Mapas ANTES/DESPUÉS CAM (CDMX alcaldías)")
parser.add_argument("--version",    default=None, metavar="FOLDER",
                    help="Version del frente (ej. cam_v76). Defecto: más reciente.")
parser.add_argument("--no-legend",   action="store_true", help="Ocultar leyenda")
parser.add_argument("--no-title",    action="store_true", help="Ocultar títulos")
parser.add_argument("--no-colorbar", action="store_true", help="Ocultar colorbar")
parser.add_argument("--no-basemap",  action="store_true", help="Sin basemap CartoDB")
parser.add_argument("--dpi",  type=int,   default=200)
parser.add_argument("--bw",   type=float, default=0.12, help="Bandwidth KDE")
parser.add_argument("--grid", type=int,   default=300,  help="Resolución grilla KDE")
args = parser.parse_args()

SHOW_LEGEND   = not args.no_legend
SHOW_TITLE    = not args.no_title
SHOW_COLORBAR = not args.no_colorbar
SHOW_BASEMAP  = not args.no_basemap

# ---------------------------------------------------------------------------
# Colormap KDE
# ---------------------------------------------------------------------------
_HC = [
    (0.0, (*plt.cm.Blues(0.05)[:3],   0.00)),
    (0.3, (*plt.cm.YlOrRd(0.35)[:3], 0.35)),
    (0.7, (*plt.cm.YlOrRd(0.70)[:3], 0.55)),
    (1.0, (*plt.cm.YlOrRd(1.00)[:3], 0.75)),
]
HEAT_CMAP = LinearSegmentedColormap.from_list("demand_heat", [(v, c) for v, c in _HC])

# ---------------------------------------------------------------------------
# Version resolution
# ---------------------------------------------------------------------------
def _resolve_version() -> str:
    for stem in INSTANCE_STEMS:
        candidates = sorted(
            (OUT_BASE / stem).glob("pareto_front_*.csv"),
            key=lambda p: p.name, reverse=True,
        )
        if candidates:
            return re.sub(r"^pareto_front_|\.csv$", "", candidates[0].name)
    raise FileNotFoundError("No se encontró pareto_front_*.csv. Ejecuta ANN_cam.py primero.")

VERSION_TAG = args.version or _resolve_version()
OUT_DIR = OUT_DIR / VERSION_TAG
OUT_DIR.mkdir(parents=True, exist_ok=True)
print("=" * 70)
print(f"C_GRAFICOS_cam.py  |  version: {VERSION_TAG}")
print(f"Instancias: {len(INSTANCE_STEMS)}")
print("=" * 70)

# ---------------------------------------------------------------------------
# Helper functions  (identical logic to C_GRAFICOS_drp.py, CRS differs)
# ---------------------------------------------------------------------------

def parse_dat(filepath: Path) -> list[tuple]:
    """Return list of (x, y, flag, prob) in 1-based order (UTM EPSG:32614)."""
    pts, inside = [], False
    with open(filepath) as fh:
        for line in fh:
            s = line.strip()
            if re.match(r"param\s*:\s*coordx\s+coordy\s+flag", s):
                inside = True; continue
            if inside and s == ";":
                break
            if inside and s:
                p = s.split()
                if len(p) >= 5:
                    pts.append((float(p[1]), float(p[2]), int(p[3]), float(p[4])))
                elif len(p) >= 4:
                    pts.append((float(p[1]), float(p[2]), int(p[3]), 1.0))
    return pts


def _proj(xs, ys):
    """UTM EPSG:32614 → Web Mercator EPSG:3857."""
    return _TR.transform(np.asarray(xs, float), np.asarray(ys, float))


def _ids_to_wm(id_set: set[int], pts: list[tuple]):
    coords = [(pts[i - 1][0], pts[i - 1][1]) for i in id_set if 0 < i <= len(pts)]
    if not coords:
        return np.array([]), np.array([])
    xs, ys = zip(*coords)
    return _proj(xs, ys)


def _poly_to_mpl_path(geom) -> MplPath:
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    verts, codes = [], []
    for poly in polys:
        coords = np.array(poly.exterior.coords)
        verts.extend(coords.tolist())
        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY]
    return MplPath(np.array(verts), codes)


def _build_kde(wx, wy, weights, bounds, grid_res, bw_method):
    wx0, wy0, wx1, wy1 = bounds
    gx = np.linspace(wx0, wx1, grid_res)
    gy = np.linspace(wy0, wy1, grid_res)
    GX, GY = np.meshgrid(gx, gy)
    if weights.sum() > 0 and len(wx) > 2:
        w   = weights / weights.sum()
        kde = gaussian_kde(np.vstack([wx, wy]), weights=w, bw_method=bw_method)
        Z   = kde(np.vstack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
        Z   = (Z - Z.min()) / (Z.max() - Z.min() + 1e-12)
    else:
        Z = np.zeros((grid_res, grid_res))
    return Z, [wx0, wx1, wy0, wy1]


def _legend_handle(label: str, color: str, marker: str, size: int = 9) -> Line2D:
    if marker == "x":
        return Line2D([0], [0], marker="x", color=color, linestyle="none",
                      markersize=size, markeredgewidth=1.5, label=label)
    if marker == "s":
        return Line2D([0], [0], marker="s", color="w", linestyle="none",
                      markerfacecolor=color, markeredgecolor="#222222",
                      markersize=size, label=label)
    return Line2D([0], [0], marker=marker, color="w", linestyle="none",
                  markerfacecolor=color, markeredgecolor="white",
                  markersize=size, label=label)


def _draw_ax(ax, gdf_3857, clip_path, kde_Z, kde_extent,
             scatter_groups, title, colorbar=False):
    """Draw one map panel (see C_GRAFICOS_drp.py for full doc)."""
    minx, miny, maxx, maxy = gdf_3857.total_bounds
    pad = max(maxx - minx, maxy - miny) * 0.04
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)

    if SHOW_BASEMAP:
        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                            zoom="auto", zorder=0)
        except Exception as e:
            print(f"  WARNING basemap: {e}")

    img = ax.imshow(
        kde_Z, origin="lower", extent=kde_extent,
        cmap=HEAT_CMAP, vmin=0, vmax=1,
        aspect="auto", zorder=2, interpolation="bilinear", alpha=0.85,
    )
    clip_patch = PathPatch(clip_path, transform=ax.transData,
                           facecolor="none", edgecolor="none")
    ax.add_patch(clip_patch)
    img.set_clip_path(clip_patch)

    gdf_3857.boundary.plot(ax=ax, linewidth=1.2, color="black", zorder=4)

    legend_handles = []
    for g in scatter_groups:
        wx, wy = g["wx"], g["wy"]
        if len(wx) > 0:
            ax.scatter(wx, wy, zorder=6, **g["scatter_kw"])
        legend_handles.append(
            _legend_handle(g["legend_label"], g["legend_color"], g["legend_marker"])
        )

    if SHOW_LEGEND:
        ax.legend(handles=legend_handles, loc="lower left",
                  fontsize=7, framealpha=0.85)

    if colorbar and SHOW_COLORBAR:
        sm = plt.cm.ScalarMappable(cmap=HEAT_CMAP, norm=plt.Normalize(0, 1))
        sm.set_array([])
        cax = ax.inset_axes([0.03, 0.04, 0.04, 0.25])
        cbar = plt.colorbar(sm, cax=cax)
        cbar.set_ticks([0, 1])
        cbar.set_ticklabels(["Low", "High"])
        cbar.ax.tick_params(labelsize=7, colors="white")
        cbar.outline.set_edgecolor("white")

    if SHOW_TITLE:
        ax.set_title(title, fontsize=9, pad=4)
    ax.set_axis_off()


# ===========================================================================
# STEP 1 — Load alcaldía boundaries (EPSG:4326 → 3857)
# ===========================================================================
print("\nSTEP 1 — Loading alcaldía boundaries")
alc_4326 = gpd.read_file(BOUNDS_FILE)
if alc_4326.crs is None:
    alc_4326 = alc_4326.set_crs(epsg=4326)
alc_3857 = alc_4326.to_crs(epsg=3857)
alc_3857["alc_norm"] = alc_3857["alcaldia_norm"].str.upper().str.strip()
print(f"  {len(alc_3857)} alcaldías cargadas")

# ===========================================================================
# STEP 2 — Parse .dat files
# ===========================================================================
print("\nSTEP 2 — Parsing instance files")
all_pts: dict[str, list[tuple]] = {}
for stem in INSTANCE_STEMS:
    pts = parse_dat(INST_DIR / f"{stem}.dat")
    all_pts[stem] = pts
    n0 = sum(1 for _, _, f, _ in pts if f == 0)
    n1 = sum(1 for _, _, f, _ in pts if f == 1)
    alc = stem_to_alcaldia(stem)
    print(f"  {alc:<25s}  total={len(pts):>5d}  demand={n0:>5d}  cam={n1:>4d}")

# ===========================================================================
# STEP 3 — Load Pareto fronts, extract Fase 3 (min obj1 = max coverage)
# ===========================================================================
print("\nSTEP 3 — Loading Pareto fronts")
fase3: dict[str, dict] = {}
for stem in INSTANCE_STEMS:
    pf_path = OUT_BASE / stem / f"pareto_front_{VERSION_TAG}.csv"
    if not pf_path.exists():
        print(f"  SKIP {stem_to_alcaldia(stem)}: {pf_path.name} no encontrado.")
        continue
    df = pd.read_csv(pf_path)
    if df.empty:
        print(f"  SKIP {stem_to_alcaldia(stem)}: frente vacío.")
        continue
    best    = df.loc[df["obj1"].idxmin()]
    ids_str = str(best["ids"]) if pd.notna(best["ids"]) else ""
    ids_1b  = {int(x) for x in ids_str.split() if x.isdigit()}
    # Normalized coverage: |F1| / |F1_fase3| * 100 = 100% by definition here
    # Store raw f1 for potential comparison; show N_installed in titles
    fase3[stem] = {"f1": float(best["obj1"]), "f2": float(best["obj2"]), "ids": ids_1b}
    alc = stem_to_alcaldia(stem)
    print(f"  {alc:<25s}  obj1={best['obj1']:.4f}  obj2={best['obj2']:.0f}  "
          f"N={len(ids_1b)}")

# ===========================================================================
# STEP 4 — Classify points and compute KDE per alcaldía
# ===========================================================================
print("\nSTEP 4 — Classifying points and computing KDE")
data: dict[str, dict] = {}

for stem in INSTANCE_STEMS:
    if stem not in fase3:
        continue

    alc  = stem_to_alcaldia(stem)
    pts  = all_pts[stem]
    sol  = fase3[stem]

    # Match boundary by alcaldia_norm (case-insensitive)
    alc_upper = alc.upper()
    gdf1 = alc_3857[alc_3857["alc_norm"] == alc_upper]
    if gdf1.empty:
        # Try partial match (for names with dots/accents)
        matches = alc_3857[alc_3857["alc_norm"].str.contains(alc_upper[:8], na=False)]
        if not matches.empty:
            gdf1 = matches.iloc[[0]]
        else:
            print(f"  WARNING: boundary not found for {alc!r}")
            continue

    flag1_ids     = {i + 1 for i, (_, _, f, _) in enumerate(pts) if f == 1}
    optimized_ids = sol["ids"]
    kept_ids      = flag1_ids & optimized_ids
    new_ids       = optimized_ids - flag1_ids
    removed_ids   = flag1_ids - optimized_ids

    print(f"  {alc:<25s}  kept={len(kept_ids):>4d}  "
          f"new={len(new_ids):>5d}  removed={len(removed_ids):>4d}")

    # Demand KDE
    demand = [(x, y, prob) for _, (x, y, f, prob) in enumerate(pts) if f == 0]
    if demand:
        dx, dy, dw = zip(*demand)
        dwx, dwy   = _proj(dx, dy)
        weights    = np.array(dw, float)
    else:
        dwx, dwy, weights = np.array([]), np.array([]), np.array([])

    minx, miny, maxx, maxy = gdf1.total_bounds
    pad    = max(maxx - minx, maxy - miny) * 0.05
    bounds = (minx - pad, miny - pad, maxx + pad, maxy + pad)
    kde_Z, kde_extent = _build_kde(dwx, dwy, weights, bounds, args.grid, args.bw)

    try:
        boundary_geom = gdf1.union_all()
    except AttributeError:
        boundary_geom = gdf1.unary_union
    clip_path = _poly_to_mpl_path(boundary_geom)

    kept_wx,    kept_wy    = _ids_to_wm(kept_ids,    pts)
    new_wx,     new_wy     = _ids_to_wm(new_ids,     pts)
    removed_wx, removed_wy = _ids_to_wm(removed_ids, pts)
    before_wx,  before_wy  = _ids_to_wm(flag1_ids,   pts)

    scatter_before = [
        dict(wx=before_wx, wy=before_wy,
             scatter_kw=dict(marker="o", color="#d62728", edgecolors="white",
                             linewidths=0.5, s=14, alpha=0.90),
             legend_label=f"Cámara instalada (N={len(flag1_ids)})",
             legend_color="#d62728", legend_marker="o"),
    ]

    scatter_after = [
        dict(wx=kept_wx, wy=kept_wy,
             scatter_kw=dict(marker="o", color="#d62728", edgecolors="white",
                             linewidths=0.5, s=14, alpha=0.90),
             legend_label=f"Kept ● (N={len(kept_ids)})",
             legend_color="#d62728", legend_marker="o"),
        dict(wx=new_wx, wy=new_wy,
             scatter_kw=dict(marker="s", color="#d62728", edgecolors="#222222",
                             linewidths=0.5, s=16, alpha=0.90),
             legend_label=f"New ■ (N={len(new_ids)})",
             legend_color="#ffffff", legend_marker="s"),
        dict(wx=removed_wx, wy=removed_wy,
             scatter_kw=dict(marker="x", color="#8b0000",
                             linewidths=1.5, s=22, alpha=0.85),
             legend_label=f"Removed ✕ (N={len(removed_ids)})",
             legend_color="#8b0000", legend_marker="x"),
    ]

    data[stem] = dict(
        alc=alc, gdf1=gdf1, clip_path=clip_path,
        kde_Z=kde_Z, kde_extent=kde_extent,
        scatter_before=scatter_before, scatter_after=scatter_after,
        flag1_ids=flag1_ids, sol=sol,
    )

# ===========================================================================
# STEP 5 — Individual figures (BEFORE + AFTER per alcaldía)
# ===========================================================================
print("\nSTEP 5 — Generating individual figures")
for stem in INSTANCE_STEMS:
    if stem not in data:
        continue
    d   = data[stem]
    alc = d["alc"]

    # BEFORE
    fig, ax = plt.subplots(1, 1, figsize=(8, 8), dpi=args.dpi)
    _draw_ax(ax, d["gdf1"], d["clip_path"], d["kde_Z"], d["kde_extent"],
             d["scatter_before"],
             f"{alc.title()} — Estado actual  (N={len(d['flag1_ids'])} cámaras)",
             colorbar=True)
    out = OUT_DIR / f"cam_before_{stem}.png"
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {out.name}")

    # AFTER (Fase 3)
    sol = d["sol"]
    fig, ax = plt.subplots(1, 1, figsize=(8, 8), dpi=args.dpi)
    _draw_ax(ax, d["gdf1"], d["clip_path"], d["kde_Z"], d["kde_extent"],
             d["scatter_after"],
             f"{alc.title()} — Fase 3  N={len(sol['ids'])} cámaras  F2={sol['f2']:.0f}",
             colorbar=True)
    out = OUT_DIR / f"cam_fase3_{stem}.png"
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {out.name}")

# ===========================================================================
# STEP 6 — Combined panels (dynamic grid: 4 columns)
# ===========================================================================
print("\nSTEP 6 — Generating combined panels")
stems_ok = [s for s in INSTANCE_STEMS if s in data]
n        = len(stems_ok)

if n > 0:
    NCOLS  = 4
    NROWS  = math.ceil(n / NCOLS)

    for mode in ("before", "fase3"):
        fig, axes = plt.subplots(NROWS, NCOLS,
                                 figsize=(NCOLS * 7, NROWS * 7), dpi=args.dpi)
        axes_flat = axes.flatten() if NROWS > 1 else list(axes)

        for ax, stem in zip(axes_flat, stems_ok):
            d  = data[stem]
            sg = d["scatter_before"] if mode == "before" else d["scatter_after"]
            sol = d["sol"]
            if mode == "before":
                title = f"{d['alc'].title()}\nEstado actual (N={len(d['flag1_ids'])})"
            else:
                title = f"{d['alc'].title()}\nFase 3  N={len(sol['ids'])}  F2={sol['f2']:.0f}"
            _draw_ax(ax, d["gdf1"], d["clip_path"], d["kde_Z"], d["kde_extent"],
                     sg, title, colorbar=False)

        # Hide unused axes
        for ax in axes_flat[n:]:
            ax.set_visible(False)

        # Shared colorbar (inset on last axis)
        if SHOW_COLORBAR:
            sm = plt.cm.ScalarMappable(cmap=HEAT_CMAP, norm=plt.Normalize(0, 1))
            sm.set_array([])
            cax = axes_flat[n - 1].inset_axes([0.03, 0.04, 0.04, 0.25])
            cbar = plt.colorbar(sm, cax=cax)
            cbar.set_ticks([0, 1])
            cbar.set_ticklabels(["Low", "High"])
            cbar.ax.tick_params(labelsize=7, colors="white")
            cbar.outline.set_edgecolor("white")

        if SHOW_TITLE:
            label = "ANTES" if mode == "before" else "Fase 3 (MOEA/D)"
            fig.suptitle(f"CAM — {label} — {VERSION_TAG}", fontsize=14, y=1.01)
        fig.subplots_adjust(wspace=0.04, hspace=0.10)

        out = OUT_DIR / f"cam_{mode}_ALL.png"
        fig.savefig(out, dpi=args.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  [OK] {out.name}")

print(f"\n{'=' * 70}")
print(f"Figuras guardadas en: {OUT_DIR.relative_to(HERE)}")
print("=" * 70)
