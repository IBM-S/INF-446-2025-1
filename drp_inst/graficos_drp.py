#!/usr/bin/env python3
"""
graficos_drp.py
===============
Genera mapas KDE continuos por borough (con boundaries de census tracts)
para las instancias DRP de Nueva York.

Uso:
    python3 graficos_drp.py                  # Staten Island (default)
    python3 graficos_drp.py --borough BRONX  # Otro borough
"""

import argparse
import json
from pathlib import Path

import contextily as ctx
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.stats import gaussian_kde

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE        = Path(__file__).resolve().parent
AED_CSV     = BASE / "NYC_AED_INVENTORY_clean_corrected.csv"
BORO_JSON   = BASE / "boundaries_borough_query.json"
QUERY_FILES = [BASE / f"final_query_{i}.json" for i in range(1, 5)]
OUT_DIR     = BASE / "maps"
OUT_DIR.mkdir(exist_ok=True)

# Archivos locales de geometría por borough (query con returnGeometry=true)
GEOM_FILES = {
    "STATEN ISLAND": BASE / "query_1_geom.json",
    # Agregar otros cuando estén disponibles:
    # "BROOKLYN":  BASE / "query_brooklyn_geom.json",
    # "BRONX":     BASE / "query_bronx_geom.json",
    # etc.
}

# ── Proyección WGS84 → Web Mercator ───────────────────────────────────────────
_tr_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

def to_webmercator(lon, lat):
    return _tr_3857.transform(lon, lat)

# ── Colormap (mismo estilo que expansion.py) ───────────────────────────────────
_HEAT_COLORS = [
    (0.0, (*plt.cm.Reds(0.0)[:3],    0.00)),
    (0.3, (*plt.cm.YlOrRd(0.35)[:3], 0.30)),
    (0.7, (*plt.cm.YlOrRd(0.70)[:3], 0.50)),
    (1.0, (*plt.cm.YlOrRd(1.00)[:3], 0.65)),
]
HEAT_CMAP = LinearSegmentedColormap.from_list(
    "demand_heat", [(v, c) for v, c in _HEAT_COLORS]
)

# ── Borough → county code (FIPS) + state code ─────────────────────────────────
BOROUGH_INFO = {
    "MANHATTAN":     {"county": "061", "state": "36"},
    "BRONX":         {"county": "005", "state": "36"},
    "BROOKLYN":      {"county": "047", "state": "36"},
    "QUEENS":        {"county": "081", "state": "36"},
    "STATEN ISLAND": {"county": "085", "state": "36"},
}

# ── Carga de datos ─────────────────────────────────────────────────────────────

def load_tract_centroids() -> pd.DataFrame:
    """Combina los 4 final_query_*.json; devuelve block groups únicos con centroid.
    Filtra TOTPOP10 > 0 igual que en veraed_data.py (elimina zonas sin población).
    """
    rows, seen = [], set()
    for qf in QUERY_FILES:
        with open(qf, encoding="utf-8") as f:
            data = json.load(f)
        for feat in data["features"]:
            attr  = feat["attributes"]
            geoid = attr["GEOID10"]
            if geoid in seen:
                continue
            seen.add(geoid)
            cent = feat["centroid"]
            rows.append({
                "COUNTY":    attr["COUNTY"],
                "GEOID10":   geoid,
                "TOTPOP10":  attr.get("TOTPOP10")  or 0,
                "POPDENS10": attr.get("POPDENS10") or 0,
                "lon": cent["x"],
                "lat": cent["y"],
            })
    df = pd.DataFrame(rows)
    df = df[df["TOTPOP10"] > 0].copy()   # mismo filtro que veraed_data.py
    return df


def load_aeds() -> pd.DataFrame:
    df = pd.read_csv(AED_CSV)
    df["boro_norm"]  = df["borough_geom"].astype(str).str.upper().str.strip()
    df["AED_NumAeds"] = pd.to_numeric(df["AED_NumAeds"], errors="coerce").fillna(1)
    return df.dropna(subset=["Latitude", "Longitude"])


def load_borough_boundaries() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(BORO_JSON, driver="ESRIJSON")
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    else:
        gdf = gdf.to_crs(epsg=4326)
    gdf["boro_norm"] = gdf["boro_name"].astype(str).str.upper().str.strip()
    return gdf


def load_bg_boundaries(borough_name: str) -> gpd.GeoDataFrame:
    """Carga los polígonos de block groups desde el JSON local con geometría."""
    geom_file = GEOM_FILES.get(borough_name)
    if geom_file is None or not geom_file.exists():
        raise FileNotFoundError(
            f"No hay archivo de geometría local para {borough_name!r}.\n"
            f"Descarga el JSON con returnGeometry=true y agrégalo a GEOM_FILES."
        )
    gdf = gpd.read_file(str(geom_file), driver="ESRIJSON")
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    else:
        gdf = gdf.to_crs(epsg=4326)
    return gdf


# ── Visualización ──────────────────────────────────────────────────────────────

def plot_borough_kde(
    borough_name: str,
    bw_method: float = 0.12,
    grid_res: int = 300,
    dpi: int = 150,
    show_aeds: bool = True,
):
    """
    Genera mapa KDE continuo para un borough con boundaries de census tracts.

    KDE: densidad de demanda OHCA estimada a partir de la densidad poblacional
    de cada tract (POPDENS10). AEDs se muestran como puntos rojos opcionales.
    """
    boro = borough_name.upper().strip()
    if boro not in BOROUGH_INFO:
        raise ValueError(f"Borough desconocido: {boro!r}. Opciones: {list(BOROUGH_INFO)}")

    info   = BOROUGH_INFO[boro]
    county = info["county"]
    state  = info["state"]

    print(f"\n[{boro}] Cargando datos...")

    # ── Datos ──────────────────────────────────────────────────────────────────
    df_tracts    = load_tract_centroids()
    df_boro      = df_tracts[df_tracts["COUNTY"] == county].copy()

    df_aeds      = load_aeds()
    df_aeds_boro = df_aeds[df_aeds["boro_norm"] == boro].copy()

    gdf_boro     = load_borough_boundaries()
    gdf_boro_1   = gdf_boro[gdf_boro["boro_norm"] == boro]

    gdf_bg       = load_bg_boundaries(boro)

    print(f"  block groups: {len(gdf_bg)}  |  centroides KDE: {len(df_boro)}  |  AEDs: {len(df_aeds_boro)}")

    # ── Proyectar a EPSG:3857 ──────────────────────────────────────────────────
    gdf_boro_3857 = gdf_boro_1.to_crs(epsg=3857)
    gdf_bg_3857   = gdf_bg.to_crs(epsg=3857)

    wx, wy  = to_webmercator(df_boro["lon"].values, df_boro["lat"].values)
    weights = np.clip(df_boro["POPDENS10"].values.astype(float), 0, None)

    if show_aeds:
        aed_wx, aed_wy = to_webmercator(
            df_aeds_boro["Longitude"].values,
            df_aeds_boro["Latitude"].values,
        )

    # ── Figura ─────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 10), dpi=dpi)

    minx, miny, maxx, maxy = gdf_boro_3857.total_bounds
    pad_x = (maxx - minx) * 0.04
    pad_y = (maxy - miny) * 0.04
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)

    # Basemap
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom="auto", zorder=0)

    # ── KDE heatmap ────────────────────────────────────────────────────────────
    if len(wx) > 2 and weights.sum() > 0:
        pts = np.vstack([wx, wy])
        w   = weights / weights.sum()
        kde = gaussian_kde(pts, weights=w, bw_method=bw_method)

        xl, yl = ax.get_xlim(), ax.get_ylim()
        gx = np.linspace(xl[0], xl[1], grid_res)
        gy = np.linspace(yl[0], yl[1], grid_res)
        GX, GY = np.meshgrid(gx, gy)
        Z = kde(np.vstack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
        Z = (Z - Z.min()) / (Z.max() - Z.min() + 1e-12)

        ax.imshow(
            Z, origin="lower",
            extent=[xl[0], xl[1], yl[0], yl[1]],
            cmap=HEAT_CMAP, vmin=0, vmax=1,
            aspect="auto", zorder=2, interpolation="bilinear",
        )

    # ── Boundaries de block groups ────────────────────────────────────────────
    gdf_bg_3857.boundary.plot(
        ax=ax, linewidth=0.7, edgecolor="#3a3a3a", alpha=0.45, zorder=3
    )

    # ── Boundary del borough ───────────────────────────────────────────────────
    gdf_boro_3857.boundary.plot(
        ax=ax, linewidth=2.0, edgecolor="#1a1a1a", alpha=0.9, zorder=4
    )

    # ── Centroides de tracts ───────────────────────────────────────────────────
    ax.scatter(
        wx, wy,
        s=10, c="white", edgecolors="#3a3a3a",
        linewidths=0.6, alpha=0.75, zorder=5, label="Centroide tract",
        marker="o",
    )

    # ── AEDs ───────────────────────────────────────────────────────────────────
    if show_aeds and len(df_aeds_boro) > 0:
        ax.scatter(
            aed_wx, aed_wy,
            s=18, c="crimson", edgecolors="white",
            linewidths=0.5, alpha=0.85, zorder=6, label="AED instalado",
        )
    #ax.legend(loc="lower left", fontsize=9, framealpha=0.7)

    ax.set_title(
        f"KDE demanda OHCA — {boro.title()}\n"
        f"block groups={len(gdf_bg)}, AEDs={len(df_aeds_boro)} ubicaciones",
        fontsize=13, pad=8,
    )
    ax.set_axis_off()

    slug = boro.lower().replace(" ", "_")
    out  = OUT_DIR / f"kde_{slug}.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] Guardado: {out}")
    return out


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mapas KDE por borough DRP")
    parser.add_argument(
        "--borough", default="STATEN ISLAND",
        help="Nombre del borough (default: 'STATEN ISLAND')"
    )
    parser.add_argument("--bw",  type=float, default=0.12, help="Bandwidth KDE")
    parser.add_argument("--dpi", type=int,   default=150,  help="DPI imagen")
    parser.add_argument("--no-aeds", on="store_true",  help="Ocultar AEDs")
    args = parser.parse_args()

    plot_borough_kde(
        borough_name=args.borough,
        bw_method=args.bw,
        dpi=args.dpi,
        show_aeds=not args.no_aeds,
    )
