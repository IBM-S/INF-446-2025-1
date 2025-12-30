from pathlib import Path
import geopandas as gpd
import unicodedata

# =========================
# PATHS (TT2/)
# =========================
BASE_DIR = Path(__file__).resolve().parent
TT2_DIR  = BASE_DIR.parent
GEO_DIR  = TT2_DIR / "datos" / "geo"
VIZ_DIR  = TT2_DIR / "datos" / "viz"
VIZ_DIR.mkdir(parents=True, exist_ok=True)

COLONIAS_GEOJSON = GEO_DIR / "DemograficosD_GJ.geojson"

OUT_ALCALDIAS_GEOJSON = VIZ_DIR / "boundaries_alcaldias_4326.geojson"
OUT_ALCALDIAS_GPKG    = VIZ_DIR / "boundaries_alcaldias_4326.gpkg"  # opcional

CRS_IN = 32614
CRS_OUT = 4326

def normalizar_texto(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("utf-8")
    s = s.upper().strip()
    if "MIGUEL HIDALGO" in s: return "MIGUEL HIDALGO"
    if "CUAJIMALPA" in s: return "CUAJIMALPA DE MORELOS"
    return s

def main():
    gdf = gpd.read_file(COLONIAS_GEOJSON)
    print(f"[COLONIAS] read: {len(gdf)}")

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=CRS_IN)
    else:
        gdf = gdf.to_crs(epsg=CRS_IN)

    if "alcaldia" not in gdf.columns:
        raise ValueError("No encuentro columna 'alcaldia' en DemograficosD_GJ.geojson")

    gdf["alcaldia_norm"] = gdf["alcaldia"].apply(normalizar_texto)

    # ✅ eliminar filas con alcaldia null/empty (esto evita DESCONOCIDO)
    before = len(gdf)
    gdf = gdf[gdf["alcaldia_norm"].astype(str).str.strip() != ""].copy()
    print(f"[COLONIAS] dropped alcaldia null/empty: {before - len(gdf)} -> kept: {len(gdf)}")

    # (opcional) si alguna geometría viene nula
    before = len(gdf)
    gdf = gdf[~gdf.geometry.isna()].copy()
    print(f"[COLONIAS] dropped geometry null: {before - len(gdf)} -> kept: {len(gdf)}")

    # dissolve a alcaldías
    gdf_alc = gdf.dissolve(by="alcaldia_norm", as_index=False)
    print(f"[ALCALDIAS] after dissolve: {len(gdf_alc)}")

    gdf_alc = gdf_alc.to_crs(epsg=CRS_OUT)

    gdf_alc.to_file(OUT_ALCALDIAS_GEOJSON, driver="GeoJSON")
    print(f"[OK] wrote: {OUT_ALCALDIAS_GEOJSON}")

    # opcional
    gdf_alc.to_file(OUT_ALCALDIAS_GPKG, driver="GPKG")
    print(f"[OK] wrote: {OUT_ALCALDIAS_GPKG}")

if __name__ == "__main__":
    main()
