from pathlib import Path
import geopandas as gpd
import pandas as pd
import unicodedata

# =========================
# PATHS (TT2/)
# =========================
BASE_DIR = Path(__file__).resolve().parent          # TT2/visualizacion_web
TT2_DIR  = BASE_DIR.parent                         # TT2
GEO_DIR  = TT2_DIR / "datos" / "geo"               # TT2/datos/geo
VIZ_DIR  = TT2_DIR / "datos" / "viz"               # TT2/datos/viz
VIZ_DIR.mkdir(parents=True, exist_ok=True)

DELITOS_GEOJSON = GEO_DIR / "reportes_incidenciaU.geojson"
CAMARAS_GEOJSON = GEO_DIR / "camaraPosU.geojson"

OUT_POINTS_CSV = VIZ_DIR / "points_cams_delitos.csv"

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

def cargar_points(path: Path, name: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    print(f"[{name}] read: {len(gdf)}")

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=CRS_IN)
    else:
        gdf = gdf.to_crs(epsg=CRS_IN)

    # solo Points + geometry no nula
    n_null = gdf.geometry.isna().sum()
    gdf = gdf[~gdf.geometry.isna()].copy()
    gdf = gdf[gdf.geometry.type == "Point"].copy()
    print(f"[{name}] geometry_null dropped: {n_null}, kept_points: {len(gdf)}")
    return gdf

def probs_por_categoria(df: pd.DataFrame) -> dict:
    vc = df["categoria_delito"].value_counts()
    total = vc.sum()
    return {} if total == 0 else (vc / total).to_dict()

def main():
    # ==========
    # CAMARAS
    # ==========
    cam = cargar_points(CAMARAS_GEOJSON, "CAMARAS")

    if "alcaldia" not in cam.columns:
        raise ValueError("[CAMARAS] falta columna 'alcaldia'")

    cam["alcaldia_norm"] = cam["alcaldia"].apply(normalizar_texto)

    # filtro: alcaldia no puede ser null/None/""  (esto te elimina esos 35)
    before = len(cam)
    cam = cam[cam["alcaldia_norm"].astype(str).str.strip() != ""].copy()
    print(f"[CAMARAS] dropped alcaldia null/empty: {before - len(cam)} -> kept: {len(cam)}")

    cam_4326 = cam.to_crs(epsg=CRS_OUT)

    cam_df = pd.DataFrame({
        "flag": 1,
        "prob": 0.0,
        "alcaldia_norm": cam_4326["alcaldia_norm"],
        "categoria_delito": "",
        "lon": cam_4326.geometry.x,
        "lat": cam_4326.geometry.y,
    })

    # ==========
    # DELITOS
    # ==========
    del_gdf = cargar_points(DELITOS_GEOJSON, "DELITOS")

    for col in ["alcaldia", "categoria_delito"]:
        if col not in del_gdf.columns:
            raise ValueError(f"[DELITOS] falta columna '{col}'")

    del_gdf["alcaldia_norm"] = del_gdf["alcaldia"].apply(normalizar_texto)

    # filtro alto impacto (si existe)
    if "impacto_delito" in del_gdf.columns:
        before = len(del_gdf)
        del_gdf = del_gdf[del_gdf["impacto_delito"].astype(str).str.upper().str.strip() == "DELITO DE ALTO IMPACTO"].copy()
        print(f"[DELITOS] filtered not-alto-impacto: {before - len(del_gdf)} -> kept: {len(del_gdf)}")

    # filtro: alcaldia no null/empty (esto te elimina ~170)
    before = len(del_gdf)
    del_gdf = del_gdf[del_gdf["alcaldia_norm"].astype(str).str.strip() != ""].copy()
    print(f"[DELITOS] dropped alcaldia null/empty: {before - len(del_gdf)} -> kept: {len(del_gdf)}")

    # filtro: categoria no vacía (por sanidad)
    before = len(del_gdf)
    del_gdf = del_gdf[del_gdf["categoria_delito"].astype(str).str.strip() != ""].copy()
    print(f"[DELITOS] dropped categoria empty: {before - len(del_gdf)} -> kept: {len(del_gdf)}")

    probs = probs_por_categoria(del_gdf)

    del_4326 = del_gdf.to_crs(epsg=CRS_OUT)
    del_df = pd.DataFrame({
        "flag": 0,
        "prob": del_4326["categoria_delito"].map(lambda c: float(probs.get(c, 0.0))),
        "alcaldia_norm": del_4326["alcaldia_norm"],
        "categoria_delito": del_4326["categoria_delito"].fillna(""),
        "lon": del_4326.geometry.x,
        "lat": del_4326.geometry.y,
    })

    # ==========
    # MERGE FINAL
    # ==========
    out = pd.concat([cam_df, del_df], ignore_index=True)
    out.insert(0, "id", range(1, len(out) + 1))
    out.to_csv(OUT_POINTS_CSV, index=False, encoding="utf-8")

    print(f"[FINAL] cams={len(cam_df)} delitos={len(del_df)} total={len(out)}")
    print(f"[OK] wrote: {OUT_POINTS_CSV}")

if __name__ == "__main__":
    main()
