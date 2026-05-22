#!/usr/bin/env python3
"""
grafico_fases_moead.py
======================
Genera un panel 1×4 (o imágenes separadas) con las 4 fases del plan de
implementación MOEA/D para una instancia dada.

Lee los archivos last_gen_*.dat de todos los runs, combina el frente de Pareto
no dominado y selecciona 4 fases por percentil de cobertura (F1).

Cada subfigura muestra:
  · Basemap CartoDB Positron
  · KDE semitransparente de la demanda OHCA
  · AEDs coloreados por tipo:
      rojo    ●  → preinstalado que se mantiene
      gris    ×  → AED removido de su lugar original
      blanco  □  → AED reubicado/instalado en nueva ubicación
  · Círculos de cobertura alrededor de cada AED activo
  · Título de fase + métricas (AEDs activos, cobertura estimada)

Uso:
    python3 grafico_fases_moead.py drp_657_STATEN_ISLAND --subdir drp_v75
    python3 grafico_fases_moead.py drp_657_STATEN_ISLAND --subdir drp_v75 --split
    python3 grafico_fases_moead.py drp_657_STATEN_ISLAND --subdir drp_v75 --dpi 200
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

from fase_parser import parse_instance
from tabla_fases_moead import load_moead_front, pick_phases

# ── Rutas ──────────────────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).resolve().parent / "maps"
OUT_DIR.mkdir(exist_ok=True)

# ── Estilo por tipo de AED ─────────────────────────────────────────────────────
TIPO_STYLE = {
    "existente": {
        "color":        "#d62728",
        "edgecolor":    "white",
        "circle_color": "#d62728",
        "marker":       "o",
        "label":        "AED preinstalado (se mantiene)",
    },
    "removido": {
        "color":        "#888888",
        "edgecolor":    "none",
        "circle_color": "#888888",
        "marker":       "x",
        "label":        "AED removido de su lugar",
    },
    "nuevo": {
        "color":        "white",
        "edgecolor":    "#333333",
        "circle_color": "#1a9641",
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
                tr, kde_Z, kde_extent):
    """Dibuja una sola fase en el axis dado."""

    ax.imshow(
        kde_Z, origin="lower", extent=kde_extent,
        cmap=HEAT_CMAP, vmin=0, vmax=1,
        aspect="auto", zorder=2, interpolation="bilinear",
    )

    # Círculos de cobertura (existente y nuevo)
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
    rem      = sum(1 for a in fase["aeds"] if a["tipo"] == "removido")
    ins      = sum(1 for a in fase["aeds"] if a["tipo"] == "nuevo")
    reub     = min(ins, rem)
    nvo      = ins - reub
    ax.text(0.02, 0.03,
            f"Activos: {n_active}  |  Cob: {cov*100:.1f}%\n"
            f"Rem: {rem}  Reub: {reub}  Nuevos: {nvo}",
            transform=ax.transAxes, fontsize=7,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.80))

    ax.set_title(
        f"{FASE_TITLES[fase['numero']]}\n"
        f"F1={abs(fase['f1']):.4f}  F2={fase['f2']:.1f}",
        fontsize=9, pad=4,
    )
    ax.set_axis_off()


# ── KDE global ────────────────────────────────────────────────────────────────

def _build_kde(demand: list[dict], tr, wx0, wy0, wx1, wy1,
               bw_method: float, grid_res: int):
    d_wx, d_wy = _proj(tr, [d["x"] for d in demand], [d["y"] for d in demand])
    weights    = np.array([d["prob"] for d in demand], dtype=float)

    if weights.sum() > 0 and len(d_wx) > 2:
        w   = weights / weights.sum()
        kde = gaussian_kde(np.vstack([d_wx, d_wy]), weights=w, bw_method=bw_method)
        gx  = np.linspace(wx0, wx1, grid_res)
        gy  = np.linspace(wy0, wy1, grid_res)
        GX, GY = np.meshgrid(gx, gy)
        Z  = kde(np.vstack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
        Z  = (Z - Z.min()) / (Z.max() - Z.min() + 1e-12)
    else:
        Z = np.zeros((grid_res, grid_res))

    return Z, [wx0, wx1, wy0, wy1]


# ── Leyenda y colorbar compartidos ────────────────────────────────────────────

def _add_legend_colorbar(fig, axes):
    handles = [
        mpatches.Patch(color=s["color"] if s["color"] != "white" else "#cccccc",
                       label=s["label"])
        for s in TIPO_STYLE.values()
    ]
    fig.legend(handles=handles, loc="lower center",
               ncol=3, fontsize=9, framealpha=0.85,
               bbox_to_anchor=(0.5, -0.02))

    sm = plt.cm.ScalarMappable(cmap=HEAT_CMAP, norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes[-1], shrink=0.75, pad=0.02, aspect=25)
    cbar.set_label("Densidad OHCA (KDE norm.)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)


# ── Función principal ──────────────────────────────────────────────────────────

def plot_fases(
    inst_name:    str,
    subdir:       str,
    split:        bool  = False,
    bw_method:    float = 0.10,
    grid_res:     int   = 280,
    dpi:          int   = 150,
):
    """
    Genera el mapa de fases MOEAD.

    split=True → guarda también cada fase como imagen separada.
    """
    inst   = parse_instance(inst_name)
    nodes  = inst["nodes"]
    params = inst["params"]
    radio  = params.get("R", 100.0)

    avg_y = sum(n["y"] for n in nodes.values()) / max(len(nodes), 1)
    epsg  = 32618 if avg_y > 3_000_000 else 32614
    tr    = _make_transformer(epsg)

    demand = [
        {"id": nid, "x": n["x"], "y": n["y"], "prob": n["prob"]}
        for nid, n in nodes.items() if n["flag"] == 0
    ]

    print(f"[{inst_name}] Cargando frente MOEAD desde {subdir}...")
    front = load_moead_front(inst_name, subdir)
    fases = pick_phases(front, nodes)
    print(f"  Frente no dominado: {len(front)} puntos")

    # Bounds globales
    all_x = ([d["x"] for d in demand]
             + [a["x"] for f in fases for a in f["aeds"]])
    all_y = ([d["y"] for d in demand]
             + [a["y"] for f in fases for a in f["aeds"]])
    pad   = radio * 8
    wx0, wy0 = _proj(tr, [min(all_x) - pad], [min(all_y) - pad])
    wx1, wy1 = _proj(tr, [max(all_x) + pad], [max(all_y) + pad])

    kde_Z, kde_extent = _build_kde(
        demand, tr, wx0[0], wy0[0], wx1[0], wy1[0], bw_method, grid_res
    )

    slug = inst_name.lower()

    # ── Panel 1×4 ──────────────────────────────────────────────────────────────
    print(f"[{inst_name}] Descargando basemap y dibujando 4 fases (panel 1×4)...")
    fig, axes = plt.subplots(1, 4, figsize=(28, 8), dpi=dpi)
    axes = axes.flatten()

    for ax, fase in zip(axes, fases):
        ax.set_xlim(wx0[0], wx1[0])
        ax.set_ylim(wy0[0], wy1[0])
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron,
                        zoom="auto", zorder=0)
        _draw_phase(ax, fase, demand, radio, tr, kde_Z, kde_extent)

    _add_legend_colorbar(fig, axes)
    fig.suptitle(
        f"MOEA/D — Plan de implementación — {inst_name.replace('_', ' ').title()}"
        f"  [{subdir}]",
        fontsize=13, y=1.01,
    )
    fig.subplots_adjust(wspace=0.04, bottom=0.12)

    out_panel = OUT_DIR / f"moead_fases_{slug}_{subdir}.png"
    fig.savefig(out_panel, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] Panel guardado: {out_panel}")

    # ── Imágenes separadas por fase ────────────────────────────────────────────
    if split:
        print(f"[{inst_name}] Generando imágenes separadas...")
        for fase in fases:
            fig_s, ax_s = plt.subplots(1, 1, figsize=(8, 8), dpi=dpi)
            ax_s.set_xlim(wx0[0], wx1[0])
            ax_s.set_ylim(wy0[0], wy1[0])
            ctx.add_basemap(ax_s, source=ctx.providers.CartoDB.Positron,
                            zoom="auto", zorder=0)
            _draw_phase(ax_s, fase, demand, radio, tr, kde_Z, kde_extent)

            # Leyenda individual
            handles = [
                mpatches.Patch(color=s["color"] if s["color"] != "white" else "#cccccc",
                               label=s["label"])
                for s in TIPO_STYLE.values()
            ]
            ax_s.legend(handles=handles, loc="lower left",
                        fontsize=8, framealpha=0.85)

            sm = plt.cm.ScalarMappable(cmap=HEAT_CMAP, norm=plt.Normalize(0, 1))
            sm.set_array([])
            cbar = fig_s.colorbar(sm, ax=ax_s, shrink=0.75, pad=0.02, aspect=25)
            cbar.set_label("Densidad OHCA (KDE norm.)", fontsize=8)
            cbar.ax.tick_params(labelsize=7)

            fig_s.suptitle(
                f"MOEA/D — {inst_name.replace('_', ' ').title()} [{subdir}]\n"
                f"{FASE_TITLES[fase['numero']]}  "
                f"F1={abs(fase['f1']):.4f}  F2={fase['f2']:.1f}",
                fontsize=11,
            )
            out_s = OUT_DIR / f"moead_fase{fase['numero']}_{slug}_{subdir}.png"
            fig_s.savefig(out_s, dpi=dpi, bbox_inches="tight", facecolor="white")
            plt.close(fig_s)
            print(f"  [OK] Fase {fase['numero']}: {out_s}")

    return out_panel


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Panel MOEA/D de fases de implementación")
    ap.add_argument("inst",     help="Nombre instancia (ej. drp_657_STATEN_ISLAND)")
    ap.add_argument("--subdir", required=True, help="Subcarpeta en raw_moead (ej. drp_v75)")
    ap.add_argument("--split",  action="store_true",
                    help="Guardar también cada fase como imagen separada")
    ap.add_argument("--bw",     type=float, default=0.10, help="Bandwidth KDE")
    ap.add_argument("--dpi",    type=int,   default=150)
    args = ap.parse_args()

    plot_fases(
        inst_name=args.inst,
        subdir=args.subdir,
        split=args.split,
        bw_method=args.bw,
        dpi=args.dpi,
    )
