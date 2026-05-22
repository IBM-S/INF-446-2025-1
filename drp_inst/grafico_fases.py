#!/usr/bin/env python3
"""
grafico_fases.py
================
Genera un panel 2×2 con las 4 fases del plan de implementación.

Cada subfigura muestra:
  · Basemap CartoDB Positron
  · KDE semitransparente de la demanda OHCA
  · AEDs coloreados por tipo:
      azul   → existente (se mantiene en su lugar)
      gris   → removido  (desinstalado de su lugar original)
      verde  → nuevo     (nueva ubicación, reubicación o compra)
  · Círculo de cobertura alrededor de cada AED activo
  · Título de fase + métricas (AEDs activos, cobertura estimada)
  · Leyenda y barra de color KDE compartidas

Uso:
    python3 grafico_fases.py drp_657_STATEN_ISLAND
    python3 grafico_fases.py cam_1390_MILPA_ALTA --type cam --run 2
"""

import argparse
from pathlib import Path

import contextily as ctx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle
import numpy as np
from pyproj import Transformer
from scipy.stats import gaussian_kde

from fase_parser import parse_plan

# ── Rutas ──────────────────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).resolve().parent / "maps"
OUT_DIR.mkdir(exist_ok=True)

# ── Estilo por tipo de AED ─────────────────────────────────────────────────────
# color       → color del marcador (fill)
# edgecolor   → borde del marcador
# circle_color→ color del círculo de cobertura (independiente del fill)
# marker      → forma del marcador
TIPO_STYLE = {
    "existente": {
        "color":        "#d62728",   # rojo
        "edgecolor":    "white",
        "circle_color": "#d62728",
        "marker":       "o",
        "label":        "AED preinstalado (se mantiene)",
    },
    "removido": {
        "color":        "#888888",   # gris
        "edgecolor":    "none",
        "circle_color": "#888888",   # (no se dibuja círculo para removidos)
        "marker":       "x",
        "label":        "AED removido de su lugar",
    },
    "nuevo": {
        "color":        "white",     # cuadrado blanco
        "edgecolor":    "#333333",   # borde oscuro visible sobre cualquier fondo
        "circle_color": "#1a9641",   # verde para los círculos de cobertura
        "marker":       "s",
        "label":        "AED reubicado/instalado",
    },
}

# ── Colormap KDE ───────────────────────────────────────────────────────────────
_HEAT_COLORS = [
    (0.0, (*plt.cm.Reds(0.0)[:3],    0.00)),
    (0.3, (*plt.cm.YlOrRd(0.35)[:3], 0.30)),
    (0.7, (*plt.cm.YlOrRd(0.70)[:3], 0.50)),
    (1.0, (*plt.cm.YlOrRd(1.00)[:3], 0.65)),
]
HEAT_CMAP = LinearSegmentedColormap.from_list(
    "demand_heat", [(v, c) for v, c in _HEAT_COLORS]
)

FASE_TITLES = [
    "Fase 0: Estado actual",
    "Fase 1: Intervención prioritaria",
    "Fase 2: Expansión intermedia",
    "Fase 3: Cobertura completa",
]


# ── Proyección ─────────────────────────────────────────────────────────────────

def _make_transformer(epsg_utm: int):
    return Transformer.from_crs(f"EPSG:{epsg_utm}", "EPSG:3857", always_xy=True)


def _proj(tr, xs, ys):
    return tr.transform(np.asarray(xs), np.asarray(ys))


# ── Cobertura estimada ─────────────────────────────────────────────────────────

def _coverage(aeds: list[dict], demand: list[dict], radio: float) -> float:
    """Fracción de demanda cubierta (prob-weighted) por los AEDs activos."""
    active = [(a["x"], a["y"]) for a in aeds if a["tipo"] in ("existente", "nuevo")]
    if not active or not demand:
        return 0.0
    total_prob = sum(d["prob"] for d in demand)
    if total_prob == 0:
        return 0.0
    covered = 0.0
    for d in demand:
        for ax, ay in active:
            if (d["x"] - ax) ** 2 + (d["y"] - ay) ** 2 <= radio ** 2:
                covered += d["prob"]
                break
    return covered / total_prob


# ── Dibujado de una subfigura ──────────────────────────────────────────────────

def _draw_phase(ax, fase: dict, demand_nodes: list[dict], radio: float,
                tr, kde_Z, kde_extent, bw_method: float):
    """Dibuja una sola fase en el axis dado."""

    # KDE heatmap (pre-calculado)
    ax.imshow(
        kde_Z, origin="lower", extent=kde_extent,
        cmap=HEAT_CMAP, vmin=0, vmax=1,
        aspect="auto", zorder=2, interpolation="bilinear",
    )

    # Círculos de cobertura (solo AEDs activos: existente y nuevo)
    for aed in fase["aeds"]:
        if aed["tipo"] not in ("existente", "nuevo"):
            continue
        wx, wy = _proj(tr, [aed["x"]], [aed["y"]])
        cc = TIPO_STYLE[aed["tipo"]]["circle_color"]
        ax.add_patch(Circle((wx[0], wy[0]), radio,
                             color=cc, fill=True,  alpha=0.10, zorder=3))
        ax.add_patch(Circle((wx[0], wy[0]), radio,
                             color=cc, fill=False, alpha=0.40,
                             linewidth=0.5, zorder=3))

    # Puntos AED
    for tipo, style in TIPO_STYLE.items():
        pts = [(a["x"], a["y"]) for a in fase["aeds"] if a["tipo"] == tipo]
        if not pts:
            continue
        xs, ys = zip(*pts)
        wx, wy = _proj(tr, xs, ys)
        s = 28 if tipo != "removido" else 18
        ax.scatter(wx, wy, s=s,
                   c=style["color"], marker=style["marker"],
                   edgecolors=style["edgecolor"],
                   linewidths=0.5, alpha=0.90, zorder=5)

    # Métricas
    n_active = sum(1 for a in fase["aeds"] if a["tipo"] in ("existente", "nuevo"))
    cov      = _coverage(fase["aeds"], demand_nodes, radio)
    #ax.text(0.02, 0.03,
    #        f"AEDs activos: {n_active}\nCobertura: {cov*100:.1f}%",
    #        transform=ax.transAxes, fontsize=7.5,
    #        verticalalignment="bottom",
    #        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.75))

    ax.set_title(
        f"{FASE_TITLES[fase['numero']]}\n"
        f"F1={abs(fase['f1']):.3f}  F2={fase['f2']:.1f}",
        fontsize=9, pad=4,
    )
    ax.set_axis_off()


# ── Función principal ──────────────────────────────────────────────────────────

def plot_fases(
    inst_name: str,
    problem_type: str = "drp",
    run: int = 1,
    bw_method: float = 0.10,
    grid_res: int = 280,
    dpi: int = 150,
):
    plan = parse_plan(inst_name, problem_type, run)

    tr      = _make_transformer(plan["epsg_utm"])
    radio   = plan["radio"]
    demand  = plan["demand_nodes"]
    fases   = plan["fases"]

    # ── Bounds globales (todos los nodos) ──────────────────────────────────────
    all_x = [d["x"] for d in demand] + [a["x"] for f in fases for a in f["aeds"]]
    all_y = [d["y"] for d in demand] + [a["y"] for f in fases for a in f["aeds"]]
    pad   = radio * 8
    wx0, wy0 = _proj(tr, [min(all_x) - pad], [min(all_y) - pad])
    wx1, wy1 = _proj(tr, [max(all_x) + pad], [max(all_y) + pad])
    extent_wm = (wx0[0], wy0[0], wx1[0], wy1[0])

    # ── KDE global (mismo para todas las fases) ────────────────────────────────
    d_wx, d_wy = _proj(tr, [d["x"] for d in demand], [d["y"] for d in demand])
    weights    = np.array([d["prob"] for d in demand], dtype=float)

    if weights.sum() > 0 and len(d_wx) > 2:
        w   = weights / weights.sum()
        kde = gaussian_kde(np.vstack([d_wx, d_wy]), weights=w, bw_method=bw_method)
        gx  = np.linspace(wx0[0], wx1[0], grid_res)
        gy  = np.linspace(wy0[0], wy1[0], grid_res)
        GX, GY = np.meshgrid(gx, gy)
        Z  = kde(np.vstack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
        Z  = (Z - Z.min()) / (Z.max() - Z.min() + 1e-12)
    else:
        Z = np.zeros((grid_res, grid_res))

    kde_extent = [wx0[0], wx1[0], wy0[0], wy1[0]]

    # ── Figura 1×4 ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 4, figsize=(28, 8), dpi=dpi)
    axes = axes.flatten()

    print(f"[{inst_name}] Descargando basemap y dibujando 4 fases...")

    for ax, fase in zip(axes, fases):
        ax.set_xlim(wx0[0], wx1[0])
        ax.set_ylim(wy0[0], wy1[0])
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron,
                        zoom="auto", zorder=0)
        _draw_phase(ax, fase, demand, radio, tr, Z, kde_extent, bw_method)

    # ── Leyenda y colorbar compartidos ─────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(color=s["color"], label=s["label"])
        for s in TIPO_STYLE.values()
    ]
    fig.legend(handles=legend_handles, loc="lower center",
               ncol=3, fontsize=9, framealpha=0.85,
               bbox_to_anchor=(0.5, -0.02))

    # Colorbar KDE (a la derecha del último panel)
    sm = plt.cm.ScalarMappable(cmap=HEAT_CMAP, norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes[-1], shrink=0.75, pad=0.02, aspect=25)
    cbar.set_label("Densidad OHCA (KDE norm.)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    fig.suptitle(
        f"Plan de implementación — {inst_name.replace('_', ' ').title()}",
        fontsize=13, y=1.01,
    )
    fig.subplots_adjust(wspace=0.04, bottom=0.12)

    slug = inst_name.lower()
    out  = OUT_DIR / f"fases_{slug}_run{run}.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] Guardado: {out}")
    return out


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Panel 2×2 de fases de implementación")
    ap.add_argument("inst", help="Nombre instancia (ej. drp_657_STATEN_ISLAND)")
    ap.add_argument("--type", default="drp", choices=["drp", "cam"],
                    dest="problem_type")
    ap.add_argument("--run",  type=int,   default=1)
    ap.add_argument("--bw",   type=float, default=0.10, help="Bandwidth KDE")
    ap.add_argument("--dpi",  type=int,   default=150)
    args = ap.parse_args()

    plot_fases(
        inst_name=args.inst,
        problem_type=args.problem_type,
        run=args.run,
        bw_method=args.bw,
        dpi=args.dpi,
    )
