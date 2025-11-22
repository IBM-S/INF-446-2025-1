# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import geopandas as gpd
import os

# -----------------------------
# Configuración de rutas
# -----------------------------
BASE = Path(__file__).resolve().parent

GEO_DIR = BASE.parent / "datos" / "geo"

CRIMES_PATH = Path(os.getenv("REPORTES_FILE", GEO_DIR / "reportes_incidenciaU.geojson"))
DEMOS_PATH  = Path(os.getenv("DEMOG_FILE",    GEO_DIR / "DemograficosD_GJ.geojson"))
CAMS_PATH   = Path(os.getenv("CAMARA_FILE",   GEO_DIR / "camaraPosU.geojson"))

OUT_DIR = BASE / "resultados_resumen"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_TXT = OUT_DIR / "resumen_alcaldias.txt"

# -----------------------------
# Helpers
# -----------------------------
def find_alcaldia_col(df, prefer="alcaldia"):
    """
    Intenta identificar la columna 'alcaldia' (insensible a mayúsculas).
    Fallbacks comunes: 'ALCALDIA','nomgeo','NOMGEO','municipio','NOM_MUN'.
    """
    cols = {c.lower(): c for c in df.columns}
    if prefer in cols:
        return cols[prefer]
    for cand in ["alcaldía", "alcaldia", "nomgeo", "nom_mun", "nom_mun_",
                 "municipio", "nom_deleg", "delegacion", "nom_alc", "nommun",
                 "alcaldia_nombre", "alcaldia_nom", "NOM_MUN".lower()]:
        if cand in cols:
            return cols[cand]
    # Si no se encuentra, devuelve None
    return None

def normalize_alcaldia(series):
    """Normaliza strings de alcaldía para agrupar de forma robusta."""
    return (series.astype(str)
                  .str.strip()
                  .str.upper()
                  .str.replace(r"\s+", " ", regex=True))

def ensure_projected(gdf, target_epsg=32614):
    """
    Asegura que un GeoDataFrame esté en un CRS proyectado (para áreas).
    Si no tiene CRS, asume target_epsg. Si tiene CRS diferente, reproyecta.
    """
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=target_epsg, allow_override=True)
    elif gdf.crs.to_epsg() != target_epsg:
        try:
            gdf = gdf.to_crs(epsg=target_epsg)
        except Exception:
            # Último recurso: fuerza target
            gdf = gdf.set_crs(epsg=target_epsg, allow_override=True)
    return gdf

# -----------------------------
# 1) Delitos de ALTO impacto por alcaldía
# -----------------------------
crimes = gpd.read_file(CRIMES_PATH)
col_alc_crimes = find_alcaldia_col(crimes)
if not col_alc_crimes:
    raise ValueError("No se encontró columna de alcaldía en reportes_incidenciaU.geojson")

# Filtrar por ALTO IMPACTO (insensible a mayúsculas)
if "impacto_delito" not in crimes.columns:
    raise ValueError("No se encontró columna 'impacto_delito' en reportes_incidenciaU.geojson")

mask_alto = crimes["impacto_delito"].astype(str).str.upper().str.contains("ALTO IMPACTO", na=False)
crimes_alto = crimes.loc[mask_alto].copy()

crimes_alto["__alc"] = normalize_alcaldia(crimes_alto[col_alc_crimes])
delitos_por_alc = (crimes_alto.groupby("__alc")
                              .size()
                              .rename("#delitos_alto")
                              .reset_index())

# -----------------------------
# 2) Área (km²) por alcaldía desde polígonos
# -----------------------------
demos = gpd.read_file(DEMOS_PATH)
col_alc_demos = find_alcaldia_col(demos)
if not col_alc_demos:
    raise ValueError("No se encontró columna de alcaldía en DemograficosD_GJ.geojson")

demos = ensure_projected(demos, 32614)
demos["__alc"] = normalize_alcaldia(demos[col_alc_demos])

# Área en km² (sumar por si una alcaldía tiene múltiples polígonos)
demos["area_km2"] = demos.geometry.area / 1_000_000.0
area_por_alc = (demos.groupby("__alc")["area_km2"]
                .sum()
                .reset_index())

# -----------------------------
# 3) # Cámaras por alcaldía
# -----------------------------
cams = gpd.read_file(CAMS_PATH)
col_alc_cams = find_alcaldia_col(cams)

if col_alc_cams:
    # Si ya viene la alcaldía en el punto, agrupar directo
    cams["__alc"] = normalize_alcaldia(cams[col_alc_cams])
    cams_por_alc = (cams.groupby("__alc")
                         .size()
                         .rename("#camaras")
                         .reset_index())
else:
    # Si no hay alcaldía en puntos, hacer spatial join con polígonos de 'demos'
    # Asegurar CRS compatible
    cams = ensure_projected(cams, 32614)
    demos_sj = demos[["__alc", "geometry"]].copy()
    joined = gpd.sjoin(cams, demos_sj, how="left", predicate="within")
    cams_por_alc = (joined.groupby("__alc")
                          .size()
                          .rename("#camaras")
                          .reset_index())

# -----------------------------
# 4) Unir todo y exportar TXT
# -----------------------------
res = (pd.DataFrame({"__alc": pd.unique(
                        pd.concat([delitos_por_alc["__alc"],
                                   area_por_alc["__alc"],
                                   cams_por_alc["__alc"]], ignore_index=True)
                      )})
       .merge(delitos_por_alc, on="__alc", how="left")
       .merge(area_por_alc,    on="__alc", how="left")
       .merge(cams_por_alc,    on="__alc", how="left")
      )

# Limpiar y formatear
res = res.rename(columns={
    "__alc": "alcaldia",
    "#delitos_alto": "#delitos de alto impacto",
    "area_km2": "km2",
    "#camaras": "#camaras"
})
res["#delitos de alto impacto"] = res["#delitos de alto impacto"].fillna(0).astype(int)
res["#camaras"] = res["#camaras"].fillna(0).astype(int)
res["km2"] = res["km2"].fillna(0.0).round(2)

# Orden alfabético por alcaldía
res = res.sort_values("alcaldia").reset_index(drop=True)

# Escribir TXT con columnas alineadas
with OUT_TXT.open("w", encoding="utf-8") as f:
    col1, col2, col3, col4 = 30, 26, 10, 10
    header = (f"{'alcaldia'.ljust(col1)}"
              f"{'#delitos de alto impacto'.rjust(col2)}"
              f"{'km2'.rjust(col3)}"
              f"{'#camaras'.rjust(col4)}")
    f.write(header + "\n")
    f.write("-" * (col1 + col2 + col3 + col4) + "\n")
    for _, row in res.iterrows():
        f.write(
            f"{str(row['alcaldia']).ljust(col1)}"
            f"{str(row['#delitos de alto impacto']).rjust(col2)}"
            f"{str(row['km2']).rjust(col3)}"
            f"{str(row['#camaras']).rjust(col4)}\n"
        )

print(f"Listo. Archivo generado en: {OUT_TXT.resolve()}")
