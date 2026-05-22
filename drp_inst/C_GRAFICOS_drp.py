#!/usr/bin/env python3
"""
C_GRAFICOS_drp.py
=================
Genera mapas ANTES y DESPUÉS (Fase 3 de MOEA/D) para cada borough NYC.

ANTES  : KDE de demanda OHCA + AEDs preinstalados (flag=1, todos como ●).
DESPUÉS: KDE de demanda OHCA + solución Fase 3 del frente de Pareto, con
         puntos clasificados en 3 categorías:
           Kept    (●) — flag=1 Y en la solución optimizada
           New     (■) — flag=0,  en la solución optimizada
           Removed (✕) — flag=1, NO en la solución optimizada

Fuentes de datos:
    datos/inst/drp_*.dat                      — nodos candidatos + AEDs
    drp_inst/boundaries_borough_query.json    — boundaries NYC (EPSG:4326)
    drp_inst/drp/{stem}/pareto_front_{v}.csv  — frente MOEA/D

Salidas (drp_inst/figures/):
    drp_before_{stem}.png    — estado inicial por borough
    drp_fase3_{stem}.png     — Fase 3 por borough
    drp_before_ALL.png       — panel combinado ANTES (1×5)
    drp_fase3_ALL.png        — panel combinado Fase 3 (1×5)

Uso:
    python C_GRAFICOS_drp.py
    python C_GRAFICOS_drp.py --version drp_v76
    python C_GRAFICOS_drp.py --no-legend
    python C_GRAFICOS_drp.py --no-basemap
"""

import argparse
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
HERE        = Path(__file__).parent
BOUNDS_FILE = HERE / "boundaries_borough_query.json"
INST_DIR    = (HERE / "../datos/inst").resolve()
OUT_BASE    = HERE / "drp"
OUT_DIR     = HERE / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BOROUGH_FILES = {
    "STATEN ISLAND": "drp_657_STATEN_ISLAND",
    "BRONX":         "drp_2151_BRONX",
    "QUEENS":        "drp_2885_QUEENS",
    "BROOKLYN":      "drp_3442_BROOKLYN",
    "MANHATTAN":     "drp_4432_MANHATTAN",
}

EPSG_UTM = 32618
_TR = Transformer.from_crs(f"EPSG:{EPSG_UTM}", "EPSG:3857", always_xy=True)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Mapas ANTES/DESPUÉS DRP (NYC boroughs)")
parser.add_argument("--version",    default=None, metavar="FOLDER",
                    help="Version del frente (ej. drp_v76). Defecto: más reciente.")
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
# Colormap KDE (azul→amarillo→rojo con transparencia creciente)
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
    first_stem = next(iter(BOROUGH_FILES.values()))
    candidates = sorted(
        (OUT_BASE / first_stem).glob("pareto_front_*.csv"),
        key=lambda p: p.name, reverse=True,
    )
    if candidates:
        return re.sub(r"^pareto_front_|\.csv$", "", candidates[0].name)
    raise FileNotFoundError("No se encontró pareto_front_*.csv. Ejecuta A_ANN_drp.py primero.")

VERSION_TAG = args.version or _resolve_version()
OUT_DIR = OUT_DIR / VERSION_TAG
OUT_DIR.mkdir(parents=True, exist_ok=True)
print("=" * 70)
print(f"C_GRAFICOS_drp.py  |  version: {VERSION_TAG}")
print("=" * 70)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def parse_dat(filepath: Path) -> list[tuple]:
    """Return list of (x, y, flag, prob) in 1-based order (UTM EPSG:32618)."""
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
    """UTM EPSG:32618 → Web Mercator EPSG:3857."""
    return _TR.transform(np.asarray(xs, float), np.asarray(ys, float))


def _ids_to_wm(id_set: set[int], pts: list[tuple]):
    """Return (wx, wy) arrays in Web Mercator for a given set of 1-based IDs."""
    coords = [(pts[i - 1][0], pts[i - 1][1]) for i in id_set if 0 < i <= len(pts)]
    if not coords:
        return np.array([]), np.array([])
    xs, ys = zip(*coords)
    return _proj(xs, ys)


def _poly_to_mpl_path(geom) -> MplPath:
    """Shapely polygon/multipolygon → matplotlib Path (used for KDE clip_path)."""
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    verts, codes = [], []
    for poly in polys:
        coords = np.array(poly.exterior.coords)
        verts.extend(coords.tolist())
        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY]
    return MplPath(np.array(verts), codes)


def _build_kde(wx, wy, weights, bounds, grid_res, bw_method):
    """
    Weighted 2-D KDE in Web Mercator space.
    Returns (Z, extent=[wx0,wx1,wy0,wy1]) with Z normalised to [0,1].
    """
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
    """Create a Line2D legend handle with the correct marker appearance."""
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
    """
    Draw one map panel.

    scatter_groups: list of dicts with keys:
      wx, wy           — Web Mercator coordinates
      scatter_kw       — kwargs for ax.scatter
      legend_label     — text for legend entry
      legend_color     — fill color for legend handle
      legend_marker    — marker char for legend handle
    """
    minx, miny, maxx, maxy = gdf_3857.total_bounds
    pad = max(maxx - minx, maxy - miny) * 0.04
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)

    # Basemap
    if SHOW_BASEMAP:
        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                            zoom="auto", zorder=0)
        except Exception as e:
            print(f"  WARNING basemap: {e}")

    # KDE heatmap clipped to borough polygon
    img = ax.imshow(
        kde_Z, origin="lower", extent=kde_extent,
        cmap=HEAT_CMAP, vmin=0, vmax=1,
        aspect="auto", zorder=2, interpolation="bilinear", alpha=0.85,
    )
    clip_patch = PathPatch(clip_path, transform=ax.transData,
                           facecolor="none", edgecolor="none")
    ax.add_patch(clip_patch)
    img.set_clip_path(clip_patch)

    # Borough boundary
    gdf_3857.boundary.plot(ax=ax, linewidth=1.2, color="black", zorder=4)

    # Points overlay
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
# STEP 1 — Load borough boundaries (EPSG:4326 → 3857)
# ===========================================================================
print("\nSTEP 1 — Loading borough boundaries")
boroughs_4326 = gpd.read_file(BOUNDS_FILE)
if boroughs_4326.crs is None:
    boroughs_4326 = boroughs_4326.set_crs(epsg=4326)
boroughs_4326["boro_norm"] = boroughs_4326["boro_name"].str.upper().str.strip()
boroughs_3857 = boroughs_4326.to_crs(epsg=3857)
print(f"  {len(boroughs_3857)} boundaries cargadas")

# ===========================================================================
# STEP 2 — Parse .dat files (all points: flag=0 demand, flag=1 AEDs)
# ===========================================================================
print("\nSTEP 2 — Parsing instance files")
all_pts: dict[str, list[tuple]] = {}
for boro_name, stem in BOROUGH_FILES.items():
    pts = parse_dat(INST_DIR / f"{stem}.dat")
    all_pts[stem] = pts
    n0 = sum(1 for _, _, f, _ in pts if f == 0)
    n1 = sum(1 for _, _, f, _ in pts if f == 1)
    print(f"  {boro_name:<15s}  total={len(pts):>4d}  demand(f=0)={n0:>4d}  AEDs(f=1)={n1:>4d}")

# ===========================================================================
# STEP 3 — Load Pareto fronts and extract Fase 3 (min obj1 = max coverage)
# ===========================================================================
print("\nSTEP 3 — Loading Pareto fronts")
fase3: dict[str, dict] = {}
for boro_name, stem in BOROUGH_FILES.items():
    pf_path = OUT_BASE / stem / f"pareto_front_{VERSION_TAG}.csv"
    if not pf_path.exists():
        print(f"  SKIP {boro_name}: {pf_path.name} no encontrado.")
        continue
    df = pd.read_csv(pf_path)
    if df.empty:
        print(f"  SKIP {boro_name}: frente vacío.")
        continue
    best     = df.loc[df["obj1"].idxmin()]
    ids_str  = str(best["ids"]) if pd.notna(best["ids"]) else ""
    ids_1b   = {int(x) for x in ids_str.split() if x.isdigit()}
    fase3[stem] = {"f1": float(best["obj1"]), "f2": float(best["obj2"]), "ids": ids_1b}
    print(f"  {boro_name:<15s}  obj1={best['obj1']:.6f}  obj2={best['obj2']:.1f}  "
          f"N={len(ids_1b)}")

# ===========================================================================
# STEP 4 — Classify points and compute KDE per borough
# ===========================================================================
print("\nSTEP 4 — Classifying points and computing KDE")
data: dict[str, dict] = {}

for boro_name, stem in BOROUGH_FILES.items():
    if stem not in fase3:
        continue

    pts = all_pts[stem]
    sol = fase3[stem]
    gdf1 = boroughs_3857[boroughs_3857["boro_norm"] == boro_name]
    if gdf1.empty:
        print(f"  WARNING: boundary not found for {boro_name}")
        continue

    # Classify IDs
    flag1_ids     = {i + 1 for i, (_, _, f, _) in enumerate(pts) if f == 1}
    optimized_ids = sol["ids"]
    kept_ids      = flag1_ids & optimized_ids
    new_ids       = optimized_ids - flag1_ids
    removed_ids   = flag1_ids - optimized_ids

    print(f"  {boro_name:<15s}  kept={len(kept_ids):>4d}  "
          f"new={len(new_ids):>4d}  removed={len(removed_ids):>4d}")

    # Demand points (flag=0) for KDE
    demand = [(x, y, prob) for _, (x, y, f, prob) in enumerate(pts) if f == 0]
    if demand:
        dx, dy, dw = zip(*demand)
        dwx, dwy   = _proj(dx, dy)
        weights    = np.array(dw, float)
    else:
        dwx, dwy, weights = np.array([]), np.array([]), np.array([])

    # KDE bounds from boundary + padding
    minx, miny, maxx, maxy = gdf1.total_bounds
    pad    = max(maxx - minx, maxy - miny) * 0.05
    bounds = (minx - pad, miny - pad, maxx + pad, maxy + pad)
    kde_Z, kde_extent = _build_kde(dwx, dwy, weights, bounds, args.grid, args.bw)

    # Clip path (polygon for masking KDE)
    try:
        boundary_geom = gdf1.union_all()
    except AttributeError:
        boundary_geom = gdf1.unary_union
    clip_path = _poly_to_mpl_path(boundary_geom)

    # Project ID sets to Web Mercator
    kept_wx,    kept_wy    = _ids_to_wm(kept_ids,    pts)
    new_wx,     new_wy     = _ids_to_wm(new_ids,     pts)
    removed_wx, removed_wy = _ids_to_wm(removed_ids, pts)
    before_wx,  before_wy  = _ids_to_wm(flag1_ids,   pts)

    # Scatter groups — BEFORE
    scatter_before = [
        dict(wx=before_wx, wy=before_wy,
             scatter_kw=dict(marker="o", color="#d62728", edgecolors="white",
                             linewidths=0.5, s=18, alpha=0.90),
             legend_label=f"AED instalado (N={len(flag1_ids)})",
             legend_color="#d62728", legend_marker="o"),
    ]

    # Scatter groups — AFTER (Fase 3)
    cob = abs(sol["f1"]) * 100
    scatter_after = [
        dict(wx=kept_wx, wy=kept_wy,
             scatter_kw=dict(marker="o", color="#d62728", edgecolors="white",
                             linewidths=0.5, s=18, alpha=0.90),
             legend_label=f"Kept AED ● (N={len(kept_ids)})",
             legend_color="#d62728", legend_marker="o"),
        dict(wx=new_wx, wy=new_wy,
             scatter_kw=dict(marker="s", color="#d62728", edgecolors="#222222",
                             linewidths=0.5, s=22, alpha=0.90),
             legend_label=f"New AED ■ (N={len(new_ids)})",
             legend_color="#ffffff", legend_marker="s"),
        dict(wx=removed_wx, wy=removed_wy,
             scatter_kw=dict(marker="x", color="#8b0000",
                             linewidths=1.5, s=30, alpha=0.85),
             legend_label=f"Removed AED ✕ (N={len(removed_ids)})",
             legend_color="#8b0000", legend_marker="x"),
    ]

    data[stem] = dict(
        boro_name=boro_name, gdf1=gdf1, clip_path=clip_path,
        kde_Z=kde_Z, kde_extent=kde_extent,
        scatter_before=scatter_before, scatter_after=scatter_after,
        flag1_ids=flag1_ids, sol=sol, cob=cob,
    )

# ===========================================================================
# STEP 5 — Individual figures (BEFORE + AFTER per borough)
# ===========================================================================
print("\nSTEP 5 — Generating individual figures")
for stem, d in data.items():
    boro_name = d["boro_name"]

    # BEFORE
    fig, ax = plt.subplots(1, 1, figsize=(8, 8), dpi=args.dpi)
    _draw_ax(ax, d["gdf1"], d["clip_path"], d["kde_Z"], d["kde_extent"],
             d["scatter_before"],
             f"{boro_name.title()} — Estado actual  (N={len(d['flag1_ids'])} AEDs)",
             colorbar=True)
    out = OUT_DIR / f"drp_before_{stem}.png"
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {out.name}")

    # AFTER (Fase 3)
    fig, ax = plt.subplots(1, 1, figsize=(8, 8), dpi=args.dpi)
    _draw_ax(ax, d["gdf1"], d["clip_path"], d["kde_Z"], d["kde_extent"],
             d["scatter_after"],
             f"{boro_name.title()} — Fase 3  "
             f"cob={d['cob']:.1f}%  F2={d['sol']['f2']:.1f}",
             colorbar=True)
    out = OUT_DIR / f"drp_fase3_{stem}.png"
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {out.name}")

# ===========================================================================
# STEP 6 — Combined panels (1×N for BEFORE and AFTER)
# ===========================================================================
print("\nSTEP 6 — Generating combined panels")
stems_ok = [s for s in BOROUGH_FILES.values() if s in data]
n = len(stems_ok)

if n > 0:
    for mode in ("before", "fase3"):
        fig, axes = plt.subplots(1, n, figsize=(n * 7, 7), dpi=args.dpi)
        if n == 1:
            axes = [axes]
        for ax, stem in zip(axes, stems_ok):
            d  = data[stem]
            sg = d["scatter_before"] if mode == "before" else d["scatter_after"]
            if mode == "before":
                title = f"{d['boro_name'].title()}\nEstado actual (N={len(d['flag1_ids'])})"
            else:
                title = (f"{d['boro_name'].title()}\n"
                         f"Fase 3  cob={d['cob']:.1f}%  F2={d['sol']['f2']:.1f}")
            _draw_ax(ax, d["gdf1"], d["clip_path"], d["kde_Z"], d["kde_extent"],
                     sg, title, colorbar=False)

        # Shared colorbar on last axis (inset)
        if SHOW_COLORBAR:
            sm = plt.cm.ScalarMappable(cmap=HEAT_CMAP, norm=plt.Normalize(0, 1))
            sm.set_array([])
            cax = axes[-1].inset_axes([0.03, 0.04, 0.04, 0.25])
            cbar = plt.colorbar(sm, cax=cax)
            cbar.set_ticks([0, 1])
            cbar.set_ticklabels(["Low", "High"])
            cbar.ax.tick_params(labelsize=7, colors="white")
            cbar.outline.set_edgecolor("white")

        if SHOW_TITLE:
            label = "ANTES" if mode == "before" else "Fase 3 (MOEA/D)"
            fig.suptitle(f"DRP — {label} — {VERSION_TAG}", fontsize=13, y=1.01)
        fig.subplots_adjust(wspace=0.04)

        out = OUT_DIR / f"drp_{mode}_ALL.png"
        fig.savefig(out, dpi=args.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  [OK] {out.name}")

print(f"\n{'=' * 70}")
print(f"Figuras guardadas en: {OUT_DIR.relative_to(HERE)}")
print("=" * 70)
