#!/usr/bin/env python3
"""
expansion.py
============
Dos opciones de visualización de la evolución del frente de Pareto.

OPCIÓN 1 – generate_evolution()
  Una imagen por solución, mostrando el mapa completo con:
  · Mapa base OSM (CartoDB Positron)
  · Heatmap de incidencia/demanda (prob_ohca)
  · Círculos de cobertura de radio R (azul translúcido)
  · Pre-existentes → ● rojo  |  Nuevas instalaciones → □ blanco

OPCIÓN 2 – generate_pareto_panel()
  Una imagen por solución con DOS paneles:
  · Izquierda: Frente de Pareto completo (cobertura vs F2).
    La solución actual se resalta con un marcador coloreado que avanza
    de azul (pocos equipos) a rojo (muchos equipos), mostrando
    exactamente dónde estás en el compromiso cobertura ↔ costo.
    Las zonas del frente se sombrean para identificar el "codo" óptimo.
  · Derecha: Mapa de cobertura de esa solución (mismo estilo Op.1).
  Útil para decisiones de diseño: ves el trade-off Y el mapa juntos.

Uso CLI (--mode 1 ó 2):
  python3 expansion.py cam_1390_MILPA_ALTA
  python3 expansion.py cam_1390_MILPA_ALTA --mode 2 --max-images 40
  python3 expansion.py drp_657_STATEN_ISLAND --mode 2 --run 2
  python3 expansion.py cam_7256_TLAHUAC --mode 1 --output /tmp/imgs

Como módulo:
  from expansion import generate_evolution, generate_pareto_panel
  generate_evolution("cam_1390_MILPA_ALTA", problem_type="cam")
  generate_pareto_panel("drp_657_STATEN_ISLAND", problem_type="drp")
"""

import re
import sys
import argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe
from scipy.stats import gaussian_kde
from pyproj import Transformer
import contextily as ctx

# ── Rutas base ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
INST_DIR = BASE_DIR / "datos" / "inst"
RES_CAM  = BASE_DIR / "datos" / "res" / "raw_moead" / "cam_final"
RES_DRP  = BASE_DIR / "datos" / "res" / "raw_moead" / "drp_final"

# Colormap heatmap (transparente → amarillo → rojo)
_HEAT_COLORS = [
    (0.0, (*plt.cm.Reds(0.0)[:3], 0.00)),
    (0.3, (*plt.cm.YlOrRd(0.35)[:3], 0.45)),
    (0.7, (*plt.cm.YlOrRd(0.70)[:3], 0.65)),
    (1.0, (*plt.cm.YlOrRd(1.00)[:3], 0.80)),
]
HEAT_CMAP = LinearSegmentedColormap.from_list(
    "demand_heat",
    [(v, c) for v, c in _HEAT_COLORS],
)


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_instance(inst_path: Path) -> dict:
    """Lee .dat de instancia AMPL. Devuelve dict con params y nodes."""
    text = Path(inst_path).read_text(encoding="utf-8", errors="replace")
    data: dict = {}
    for key in ("N_total", "P", "R", "c1", "c2"):
        m = re.search(rf"param\s+{key}\s*:=\s*([\d.]+)", text)
        if m:
            data[key] = float(m.group(1))

    nodes: dict = {}
    m = re.search(
        r"param\s*:\s*coordx\s+coordy\s+flag\s+prob_ohca\s*:=(.*?)(?=\s*;|\Z)",
        text, re.DOTALL,
    )
    if m:
        for line in m.group(1).splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].isdigit():
                nid = int(parts[0])
                nodes[nid] = dict(
                    x=float(parts[1]), y=float(parts[2]),
                    flag=int(parts[3]), prob=float(parts[4]),
                )
    data["nodes"] = nodes
    return data


def parse_last_gen(path: Path) -> list:
    """Lee last_gen_*.dat → lista de {f1, f2, ids}."""
    pattern = re.compile(
        r"^([-\d.eE+]+)\s+([-\d.eE+]+)\s+.*IDs instalados:\s*(.*)"
    )
    solutions = []
    for line in Path(path).read_text().splitlines():
        m = pattern.match(line.strip())
        if m:
            ids = list(map(int, m.group(3).split()))
            solutions.append(
                dict(f1=float(m.group(1)), f2=float(m.group(2)), ids=ids)
            )
    return solutions


def deduplicate_pareto(solutions: list) -> list:
    """Conserva la mejor F1 por valor único de F2. Ordena F2 asc."""
    best: dict = {}
    for sol in solutions:
        k = round(sol["f2"], 6)
        if k not in best or sol["f1"] < best[k]["f1"]:
            best[k] = sol
    return sorted(best.values(), key=lambda s: s["f2"])


# ── Proyección ────────────────────────────────────────────────────────────────

def _detect_epsg(nodes: dict) -> int:
    """Infiere zona UTM por coordenadas Y (heurística)."""
    if not nodes:
        return 32614
    avg_y = np.mean([n["y"] for n in nodes.values()])
    return 32618 if avg_y > 3_000_000 else 32614  # NYC vs México


def _to_webmercator(xs, ys, epsg_utm: int):
    """UTM → Web Mercator (EPSG:3857)."""
    tr = Transformer.from_crs(f"EPSG:{epsg_utm}", "EPSG:3857", always_xy=True)
    return tr.transform(xs, ys)


# ── Helpers visualización ─────────────────────────────────────────────────────

def _add_compass(ax, x=0.97, y=0.97, size=0.05):
    """Rosa de los vientos simple en coordenadas de ejes (axes fraction)."""
    ax_x = ax.get_xlim()[0] + x * (ax.get_xlim()[1] - ax.get_xlim()[0])
    ax_y = ax.get_ylim()[0] + y * (ax.get_ylim()[1] - ax.get_ylim()[0])
    span_x = (ax.get_xlim()[1] - ax.get_xlim()[0]) * size
    span_y = (ax.get_ylim()[1] - ax.get_ylim()[0]) * size

    # Flecha N
    ax.annotate(
        "", xy=(ax_x, ax_y), xytext=(ax_x, ax_y - span_y),
        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5),
        zorder=10,
    )
    ax.text(ax_x, ax_y + span_y * 0.3, "N", ha="center", va="bottom",
            fontsize=9, fontweight="bold", color="black", zorder=10,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])


def _add_scalebar(ax, length_m: float, label: str, color="black"):
    """Barra de escala horizontal simple."""
    xl = ax.get_xlim()
    yl = ax.get_ylim()
    x0 = xl[0] + 0.05 * (xl[1] - xl[0])
    x1 = x0 + length_m
    y0 = yl[0] + 0.04 * (yl[1] - yl[0])
    ax.plot([x0, x1], [y0, y0], color=color, lw=3, zorder=10,
            solid_capstyle="butt")
    ax.text((x0 + x1) / 2, y0, f"\n{label}", ha="center", va="top",
            fontsize=7, color=color, zorder=10,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])


# ── Plot principal ────────────────────────────────────────────────────────────

def _plot_solution(
    ax,
    nodes: dict,
    sol_ids: set,
    R: float,
    epsg_utm: int,
    title: str,
    problem_type: str,
) -> None:
    """Dibuja una solución sobre los ejes ax (ya en Web Mercator)."""

    # ── Separar nodos ─────────────────────────────────────────────────────────
    dem_x, dem_y, dem_p = [], [], []
    pre_x, pre_y        = [], []   # flag=1 en solución
    new_x, new_y        = [], []   # flag=0 en solución

    for nid, n in nodes.items():
        wx, wy = _to_webmercator([n["x"]], [n["y"]], epsg_utm)
        wx, wy = wx[0], wy[0]
        if n["flag"] == 0:
            dem_x.append(wx); dem_y.append(wy); dem_p.append(n["prob"])
        if nid in sol_ids:
            (pre_x if n["flag"] == 1 else new_x).append(wx)
            (pre_y if n["flag"] == 1 else new_y).append(wy)

    # ── Heatmap de demanda ───────────────────────────────────────────────────
    if dem_x and max(dem_p) > 0:
        pts = np.vstack([dem_x, dem_y])
        weights = np.array(dem_p, dtype=float)
        weights = weights / weights.sum()
        kde = gaussian_kde(pts, weights=weights,
                           bw_method=0.08)   # ajusta suavidad

        xl, yl = ax.get_xlim(), ax.get_ylim()
        gx = np.linspace(xl[0], xl[1], 250)
        gy = np.linspace(yl[0], yl[1], 250)
        GX, GY = np.meshgrid(gx, gy)
        Z = kde(np.vstack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
        Z = (Z - Z.min()) / (Z.max() - Z.min() + 1e-12)

        ax.imshow(
            Z, origin="lower", extent=[xl[0], xl[1], yl[0], yl[1]],
            cmap=HEAT_CMAP, vmin=0, vmax=1,
            aspect="auto", zorder=2, interpolation="bilinear",
        )

    # ── Radio de cobertura en Web Mercator ───────────────────────────────────
    # R está en metros UTM; en Web Mercator se estira con la latitud.
    # Para una aproximación razonable usamos el R directamente (error < 2% en México/NYC)
    for nid in sol_ids:
        if nid not in nodes:
            continue
        n = nodes[nid]
        wx, wy = _to_webmercator([n["x"]], [n["y"]], epsg_utm)
        ax.add_patch(Circle(
            (wx[0], wy[0]), R,
            color="steelblue", fill=True,  alpha=0.12, zorder=3,
        ))
        ax.add_patch(Circle(
            (wx[0], wy[0]), R,
            color="steelblue", fill=False, alpha=0.45,
            linewidth=0.6, zorder=3,
        ))

    # ── Instalaciones pre-existentes ─────────────────────────────────────────
    if pre_x:
        ax.scatter(pre_x, pre_y, s=28, c="crimson", edgecolors="white",
                   linewidths=0.4, marker="o", alpha=0.92, zorder=5)

    # ── Nuevas instalaciones ─────────────────────────────────────────────────
    if new_x:
        ax.scatter(new_x, new_y, s=40, c="white", edgecolors="black",
                   linewidths=0.9, marker="s", alpha=0.95, zorder=6)

    ax.set_title(title, fontsize=9, pad=4)
    ax.set_axis_off()


# ── API pública ───────────────────────────────────────────────────────────────

def generate_evolution(
    inst_name: str,
    problem_type: str = "cam",
    run: int = 1,
    output_dir=None,
    max_images=None,
    dpi: int = 130,
) -> Path:
    """
    Genera secuencia de PNGs con evolución del mapa de cobertura.

    Args:
        inst_name:    Nombre sin extensión (ej. 'cam_1390_MILPA_ALTA').
        problem_type: 'cam' o 'drp'.
        run:          Run del MOEA/D (1-10).
        output_dir:   Carpeta de salida (default: expansion_images/<inst_name>/).
        max_images:   Número máximo de imágenes (muestreo uniforme si hay más).
        dpi:          Resolución PNG.

    Returns:
        Path de la carpeta de salida.
    """
    inst_path = INST_DIR / f"{inst_name}.dat"
    res_base  = RES_CAM if problem_type == "cam" else RES_DRP
    last_gen  = res_base / inst_name / f"run_{run}" / f"last_gen_{inst_name}.dat"

    if not inst_path.exists():
        raise FileNotFoundError(f"Instancia no encontrada: {inst_path}")
    if not last_gen.exists():
        raise FileNotFoundError(f"Resultados no encontrados: {last_gen}")

    if output_dir is None:
        output_dir = BASE_DIR / "visualizador_web" / "expansion_images" / inst_name
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Leer datos ────────────────────────────────────────────────────────────
    print(f"[{inst_name}] Leyendo instancia...")
    data  = parse_instance(inst_path)
    nodes = data["nodes"]
    R     = data["R"]
    epsg  = _detect_epsg(nodes)

    n_pre = sum(1 for n in nodes.values() if n["flag"] == 1)
    print(f"  {len(nodes)} nodos  |  {n_pre} pre-existentes  |  R={R} m  |  EPSG:{epsg}")

    print(f"[{inst_name}] Leyendo soluciones (run {run})...")
    solutions = deduplicate_pareto(parse_last_gen(last_gen))
    print(f"  {len(solutions)} soluciones en el frente de Pareto")

    if max_images and len(solutions) > max_images:
        idx = np.linspace(0, len(solutions) - 1, max_images, dtype=int)
        solutions = [solutions[i] for i in idx]
        print(f"  Muestreando {len(solutions)} imágenes")

    # ── Bounding box en Web Mercator ──────────────────────────────────────────
    all_x = [n["x"] for n in nodes.values()]
    all_y = [n["y"] for n in nodes.values()]
    pad   = R * 3
    wx0, wy0 = _to_webmercator([min(all_x) - pad], [min(all_y) - pad], epsg)
    wx1, wy1 = _to_webmercator([max(all_x) + pad], [max(all_y) + pad], epsg)
    bbox_wm = (wx0[0], wy0[0], wx1[0], wy1[0])

    # ── Descargar tiles una sola vez ──────────────────────────────────────────
    print("[contextily] Descargando mapa base...")
    _fig_tmp, _ax_tmp = plt.subplots(figsize=(1, 1))
    _ax_tmp.set_xlim(bbox_wm[0], bbox_wm[2])
    _ax_tmp.set_ylim(bbox_wm[1], bbox_wm[3])
    try:
        ctx.add_basemap(_ax_tmp, crs="EPSG:3857",
                        source=ctx.providers.CartoDB.Positron, zoom="auto")
        tile_img  = _ax_tmp.images[0].get_array()
        tile_ext  = _ax_tmp.images[0].get_extent()
        use_tiles = True
    except Exception as e:
        print(f"  Advertencia: no se pudo descargar mapa base ({e}). Fondo blanco.")
        use_tiles = False
    plt.close(_fig_tmp)

    # ── Leyenda (handles) ─────────────────────────────────────────────────────
    equipo = "cámaras" if problem_type == "cam" else "desfibriladores"
    legend_handles = [
        mpatches.Patch(facecolor="steelblue", alpha=0.35,
                       label=f"Cobertura (R={int(R)} m)"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="crimson",
                   markeredgecolor="white", markersize=7,
                   label=f"Pre-existentes"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="white",
                   markeredgecolor="black", markersize=7,
                   label=f"Nuevos {equipo}"),
    ]

    # ── Generar imágenes ──────────────────────────────────────────────────────
    print(f"[{inst_name}] Generando {len(solutions)} imágenes → {output_dir}")

    for i, sol in enumerate(solutions):
        sol_ids  = set(sol["ids"])
        coverage = -sol["f1"]
        n_new    = sum(1 for nid in sol_ids
                       if nodes.get(nid, {}).get("flag", 0) == 0)

        title = (
            f"{inst_name.replace('_', ' ')}  —  "
            f"Solución {i+1}/{len(solutions)}\n"
            f"Cobertura: {coverage:.4f}   ·   "
            f"F₂={sol['f2']:.2f}   ·   "
            f"Nuevos {equipo}: {n_new}"
        )

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_xlim(bbox_wm[0], bbox_wm[2])
        ax.set_ylim(bbox_wm[1], bbox_wm[3])

        # Mapa base
        if use_tiles:
            ax.imshow(tile_img, extent=tile_ext, origin="upper",
                      aspect="auto", zorder=0)
        else:
            ax.set_facecolor("#f0f0f0")

        _plot_solution(ax, nodes, sol_ids, R, epsg, title, problem_type)

        # Leyenda
        ax.legend(handles=legend_handles, loc="upper left",
                  fontsize=7.5, framealpha=0.85, edgecolor="gray",
                  fancybox=False)

        # Rosa de los vientos y escala
        _add_compass(ax)
        scale_m = R * 5 if R < 500 else R * 2
        _add_scalebar(ax, scale_m, f"{int(scale_m)} m")

        fig.tight_layout(pad=0.3)
        fname = output_dir / f"sol_{i+1:04d}_f2_{sol['f2']:.2f}.png"
        fig.savefig(fname, dpi=dpi, bbox_inches="tight")
        plt.close(fig)

        if (i + 1) % 10 == 0 or (i + 1) == len(solutions):
            print(f"  {i+1}/{len(solutions)} listas")

    print(f"[{inst_name}] ¡Listo! → {output_dir}")
    return output_dir


# ══════════════════════════════════════════════════════════════════════════════
# OPCIÓN 2 – Panel doble: Frente de Pareto + Mapa
# ══════════════════════════════════════════════════════════════════════════════

def _plot_pareto_panel(
    ax,
    solutions: list,
    current_idx: int,
    equipo: str,
) -> None:
    """
    Dibuja el frente de Pareto completo en `ax`, resaltando la solución actual.

    Esquema visual:
      · Curva gris de fondo uniendo todas las soluciones (step-post)
      · Sombreado del área bajo la curva (zona de cobertura alcanzable)
      · Todos los puntos como pequeños círculos grises
      · Punto actual como marcador grande coloreado (azul→rojo según posición)
      · Líneas punteadas que proyectan el punto actual a ambos ejes
    """
    f2_all  = np.array([s["f2"]  for s in solutions])
    cov_all = np.array([-s["f1"] for s in solutions])   # positivo = mejor

    n = len(solutions)
    t = current_idx / max(n - 1, 1)                     # 0→1 a lo largo del frente
    color_actual = plt.cm.RdYlBu_r(t)                   # azul=pocos, rojo=muchos

    # ── Área sombreada ────────────────────────────────────────────────────────
    ax.fill_between(f2_all, cov_all, cov_all.min() * 0.995,
                    alpha=0.08, color="steelblue", step="post")

    # ── Curva del frente ──────────────────────────────────────────────────────
    ax.step(f2_all, cov_all, where="post",
            color="#999999", lw=1.2, alpha=0.7, zorder=2)

    # ── Todos los puntos ──────────────────────────────────────────────────────
    ax.scatter(f2_all, cov_all, s=18, c="#aaaaaa",
               edgecolors="none", alpha=0.55, zorder=3)

    # ── Punto actual ──────────────────────────────────────────────────────────
    sol = solutions[current_idx]
    cx, cy = sol["f2"], -sol["f1"]
    ax.scatter([cx], [cy], s=160, c=[color_actual],
               edgecolors="white", linewidths=1.2, zorder=5)

    # Proyecciones punteadas al punto actual
    ax.plot([f2_all.min(), cx], [cy, cy], "--",
            color=color_actual, lw=0.9, alpha=0.6, zorder=4)
    ax.plot([cx, cx], [cov_all.min() * 0.995, cy], "--",
            color=color_actual, lw=0.9, alpha=0.6, zorder=4)

    # Anotación del valor de cobertura actual
    ax.annotate(
        f"  {cy:.4f}",
        xy=(cx, cy), xytext=(cx, cy),
        fontsize=8, color=color_actual, fontweight="bold",
        va="center",
    )

    # Barra de color lateral (indica posición en el frente)
    sm = plt.cm.ScalarMappable(cmap="RdYlBu_r",
                               norm=plt.Normalize(vmin=f2_all.min(),
                                                  vmax=f2_all.max()))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label(f"F₂ — costo / # nuevos {equipo}", fontsize=7)
    cbar.ax.tick_params(labelsize=6)

    # Etiquetas y estilo
    ax.set_xlabel(f"F₂  (costo / # nuevos {equipo})", fontsize=9)
    ax.set_ylabel("Cobertura  (−F₁)", fontsize=9)
    ax.set_title("Frente de Pareto", fontsize=10, fontweight="bold")
    ax.tick_params(labelsize=8)
    ax.grid(True, alpha=0.25, linestyle="--")

    # Destacar zona "codo" (máxima ganancia marginal de cobertura)
    # Usamos el punto con mayor distancia a la línea extremo-extremo
    if n > 2:
        p0 = np.array([f2_all[0],  cov_all[0]])
        p1 = np.array([f2_all[-1], cov_all[-1]])
        line = p1 - p0
        dists = [
            abs(line[0] * (p0[1] - cov_all[j]) - line[1] * (p0[0] - f2_all[j]))
            / (np.linalg.norm(line) + 1e-12)
            for j in range(n)
        ]
        knee = int(np.argmax(dists))
        ax.scatter([f2_all[knee]], [cov_all[knee]], s=90, marker="D",
                   c="gold", edgecolors="darkorange", linewidths=1.2,
                   zorder=6, label="Codo del frente")
        ax.legend(fontsize=7, loc="lower right")


def generate_pareto_panel(
    inst_name: str,
    problem_type: str = "cam",
    run: int = 1,
    output_dir=None,
    max_images=None,
    dpi: int = 130,
) -> Path:
    """
    OPCIÓN 2: Panel doble por solución.

    Izquierda → Frente de Pareto con la solución actual resaltada.
    Derecha   → Mapa de cobertura de esa solución.

    Permite ver simultáneamente el trade-off cobertura↔costo y su
    impacto geográfico. El color del marcador en el frente va de azul
    (pocos equipos) a rojo (muchos), alineado con el eje de evolución.

    Args y Returns: igual que generate_evolution().
    """
    inst_path = INST_DIR / f"{inst_name}.dat"
    res_base  = RES_CAM if problem_type == "cam" else RES_DRP
    last_gen  = res_base / inst_name / f"run_{run}" / f"last_gen_{inst_name}.dat"

    if not inst_path.exists():
        raise FileNotFoundError(f"Instancia no encontrada: {inst_path}")
    if not last_gen.exists():
        raise FileNotFoundError(f"Resultados no encontrados: {last_gen}")

    if output_dir is None:
        output_dir = (BASE_DIR / "visualizador_web" / "expansion_images"
                      / f"{inst_name}_panel")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Datos ─────────────────────────────────────────────────────────────────
    print(f"[{inst_name}] Opción 2 – Leyendo instancia...")
    data  = parse_instance(inst_path)
    nodes = data["nodes"]
    R     = data["R"]
    epsg  = _detect_epsg(nodes)

    n_pre = sum(1 for n in nodes.values() if n["flag"] == 1)
    print(f"  {len(nodes)} nodos  |  {n_pre} pre-existentes  |  R={R} m  |  EPSG:{epsg}")

    print(f"[{inst_name}] Leyendo soluciones (run {run})...")
    solutions = deduplicate_pareto(parse_last_gen(last_gen))
    print(f"  {len(solutions)} soluciones en el frente de Pareto")

    if max_images and len(solutions) > max_images:
        idx = np.linspace(0, len(solutions) - 1, max_images, dtype=int)
        solutions = [solutions[i] for i in idx]
        print(f"  Muestreando {len(solutions)} imágenes")

    # ── Bounding box + tiles ──────────────────────────────────────────────────
    all_x = [n["x"] for n in nodes.values()]
    all_y = [n["y"] for n in nodes.values()]
    pad   = R * 3
    wx0, wy0 = _to_webmercator([min(all_x) - pad], [min(all_y) - pad], epsg)
    wx1, wy1 = _to_webmercator([max(all_x) + pad], [max(all_y) + pad], epsg)
    bbox_wm = (wx0[0], wy0[0], wx1[0], wy1[0])

    print("[contextily] Descargando mapa base...")
    _fig_tmp, _ax_tmp = plt.subplots(figsize=(1, 1))
    _ax_tmp.set_xlim(bbox_wm[0], bbox_wm[2])
    _ax_tmp.set_ylim(bbox_wm[1], bbox_wm[3])
    try:
        ctx.add_basemap(_ax_tmp, crs="EPSG:3857",
                        source=ctx.providers.CartoDB.Positron, zoom="auto")
        tile_img  = _ax_tmp.images[0].get_array()
        tile_ext  = _ax_tmp.images[0].get_extent()
        use_tiles = True
    except Exception as e:
        print(f"  Advertencia: sin mapa base ({e}). Fondo blanco.")
        use_tiles = False
    plt.close(_fig_tmp)

    # ── Leyenda mapa ──────────────────────────────────────────────────────────
    equipo = "cámaras" if problem_type == "cam" else "desfibriladores"
    legend_map = [
        mpatches.Patch(facecolor="steelblue", alpha=0.35,
                       label=f"Cobertura (R={int(R)} m)"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="crimson",
                   markeredgecolor="white", markersize=7, label="Pre-existentes"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="white",
                   markeredgecolor="black", markersize=7,
                   label=f"Nuevos {equipo}"),
    ]

    # ── Generar imágenes ──────────────────────────────────────────────────────
    print(f"[{inst_name}] Generando {len(solutions)} paneles → {output_dir}")

    for i, sol in enumerate(solutions):
        sol_ids  = set(sol["ids"])
        coverage = -sol["f1"]
        n_new    = sum(1 for nid in sol_ids
                       if nodes.get(nid, {}).get("flag", 0) == 0)

        # Figura ancha: izquierda=Pareto (38%), derecha=Mapa (62%)
        fig = plt.figure(figsize=(15, 7))
        gs  = fig.add_gridspec(1, 2, width_ratios=[5, 8],
                               left=0.06, right=0.97,
                               bottom=0.10, top=0.88, wspace=0.08)
        ax_pareto = fig.add_subplot(gs[0])
        ax_map    = fig.add_subplot(gs[1])

        # Título global
        fig.suptitle(
            f"{inst_name.replace('_', ' ')}  —  "
            f"Solución {i+1}/{len(solutions)}    "
            f"Cobertura: {coverage:.4f}   ·   "
            f"F₂={sol['f2']:.2f}   ·   "
            f"Nuevos {equipo}: {n_new}",
            fontsize=10, y=0.97,
        )

        # Panel izquierdo: Pareto
        _plot_pareto_panel(ax_pareto, solutions, i, equipo)

        # Panel derecho: Mapa
        ax_map.set_xlim(bbox_wm[0], bbox_wm[2])
        ax_map.set_ylim(bbox_wm[1], bbox_wm[3])
        if use_tiles:
            ax_map.imshow(tile_img, extent=tile_ext, origin="upper",
                          aspect="auto", zorder=0)
        else:
            ax_map.set_facecolor("#f0f0f0")

        _plot_solution(ax_map, nodes, sol_ids, R, epsg, "", problem_type)
        ax_map.legend(handles=legend_map, loc="upper left",
                      fontsize=7, framealpha=0.85, edgecolor="gray",
                      fancybox=False)
        _add_compass(ax_map)
        scale_m = R * 5 if R < 500 else R * 2
        _add_scalebar(ax_map, scale_m, f"{int(scale_m)} m")

        fname = output_dir / f"panel_{i+1:04d}_f2_{sol['f2']:.2f}.png"
        fig.savefig(fname, dpi=dpi, bbox_inches="tight")
        plt.close(fig)

        if (i + 1) % 10 == 0 or (i + 1) == len(solutions):
            print(f"  {i+1}/{len(solutions)} listas")

    print(f"[{inst_name}] ¡Listo! → {output_dir}")
    return output_dir


# ── CLI ───────────────────────────────────────────────────────────────────────

def _auto_type(name: str) -> str:
    if name.startswith("cam"): return "cam"
    if name.startswith("drp"): return "drp"
    raise ValueError(f"No se puede inferir el tipo de '{name}'. Usa --type.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Genera imágenes de evolución del mapa de cobertura.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modos:
  --mode 1  (default) Una imagen por solución: mapa completo con heatmap.
  --mode 2            Una imagen por solución: panel Pareto + mapa.

Ejemplos:
  python3 expansion.py cam_1390_MILPA_ALTA
  python3 expansion.py cam_1390_MILPA_ALTA --mode 2 --max-images 40
  python3 expansion.py drp_657_STATEN_ISLAND --mode 2 --run 2
  python3 expansion.py cam_7256_TLAHUAC --mode 1 --output /tmp/imgs
        """,
    )
    ap.add_argument("inst_name", help="Nombre de instancia sin extensión")
    ap.add_argument("--mode", type=int, choices=[1, 2], default=1,
                    help="Opción de visualización: 1=mapa solo, 2=pareto+mapa")
    ap.add_argument("--type", choices=["cam", "drp"], default=None,
                    dest="prob_type", help="Tipo (default: auto)")
    ap.add_argument("--run",  type=int, default=1)
    ap.add_argument("--output", type=str, default=None)
    ap.add_argument("--max-images", type=int, default=None, dest="max_images")
    ap.add_argument("--dpi", type=int, default=130)
    args = ap.parse_args()

    prob_type = args.prob_type or _auto_type(args.inst_name)
    out_dir   = Path(args.output) if args.output else None
    kwargs    = dict(inst_name=args.inst_name, problem_type=prob_type,
                     run=args.run, output_dir=out_dir,
                     max_images=args.max_images, dpi=args.dpi)

    if args.mode == 1:
        generate_evolution(**kwargs)
    else:
        generate_pareto_panel(**kwargs)
