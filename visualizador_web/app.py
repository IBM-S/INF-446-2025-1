import os
import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import uvicorn
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from pyproj import Transformer
from shapely.geometry import shape as shp_shape, mapping as shp_mapping, Point
from shapely.ops import unary_union, transform as shp_transform
from shapely.strtree import STRtree

from pydantic import BaseModel, Field

# ===== NUEVO: Modelos Pydantic para la creación de instancias =====
class InstancePoint(BaseModel):
    lat: float
    lon: float
    flag: int  # 0 para demanda (delitos), 1 para preinstalado (cámaras)
    prob: float

class InstancePayload(BaseModel):
    name: str = Field(..., description="Nombre del archivo, ej: MiInstancia.dat")
    points: List[InstancePoint]
    presupuesto: float = Field(alias="P")
    radio: float = Field(alias="R")
    c1: float
    c2: float

# ===================== Config =====================
BASE = Path(__file__).resolve().parent

# Archivos de entrada (puedes sobreescribir con variables de entorno)
GEO_PATH = Path(os.getenv("CAMARA_FILE", BASE / "INSTANCES Camera/DatosProcesadosGeoJSON/GeoJSON/camaraPosU.geojson"))
DEMOG_PATH = Path(os.getenv("DEMOG_FILE", BASE / "INSTANCES Camera/DatosProcesadosGeoJSON/GeoJSON/DemograficosD_GJ.geojson"))
COLONIAS_PATH = Path(os.getenv("COLONIAS_FILE", BASE / "INSTANCES Camera/DatosProcesadosGeoJSON/GeoJSON/GeoColonias.geojson"))
REPORTES_PATH = Path(os.getenv("REPORTES_FILE", BASE / "INSTANCES Camera/DatosProcesadosGeoJSON/GeoJSON/reportes_incidenciaU.geojson"))

app = FastAPI(title="Cámaras CDMX – Instancias")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Proyecciones
_tf_utm2wgs = Transformer.from_crs(32614, 4326, always_xy=True)  # (x,y m)->(lon,lat)
_tf_wgs2utm = Transformer.from_crs(4326, 32614, always_xy=True)  # (lon,lat)->(x,y m)

# Caches
_cache_points: Dict[str, Any] | None = None
_meta_cache: Dict[str, List[str]] | None = None
_hulls_cache: Dict[str, Any] | None = None  # fronteras por alcaldía (WGS84)
_colonias_cache: Dict[str, Any] | None = None  # colonias (WGS84)
_reportes_cache: Dict[str, Any] | None = None  # reportes (WGS84)

# ===================== Utiles =====================
def _normalize(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.casefold()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _geom_utm_to_wgs(geom):
    return shp_transform(lambda x, y, z=None: _tf_utm2wgs.transform(x, y), geom)

def _geom_wgs_to_utm(geom):
    return shp_transform(lambda lon, lat, z=None: _tf_wgs2utm.transform(lon, lat), geom)

# ===================== Puntos existentes =====================
def _transform_points_geojson(data: Dict[str, Any]) -> Dict[str, Any]:
    feats = data.get("features", [])
    for f in feats:
        g = f.get("geometry")
        if not g or g.get("type") != "Point": continue
        coords = g.get("coordinates") or []
        if len(coords) < 2: continue
        x, y = coords[0], coords[1]
        try:
            lon, lat = _tf_utm2wgs.transform(float(x), float(y))
            g["coordinates"] = [lon, lat]
        except Exception:
            p = f.get("properties", {})
            lat2 = p.get("latitud"); lon2 = p.get("longitud")
            if isinstance(lat2, (int,float)) and isinstance(lon2, (int,float)):
                g["coordinates"] = [float(lon2), float(lat2)]
            else:
                f["geometry"] = None
    data["crs"] = {"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::4326"}}
    return data

def _load_points() -> Dict[str, Any]:
    if not GEO_PATH.exists():
        raise FileNotFoundError(f"No se encontró camaraPosU.geojson en: {GEO_PATH}")
    with open(GEO_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return _transform_points_geojson(raw)

def _ensure_points_meta():
    global _cache_points, _meta_cache
    if _cache_points is None:
        _cache_points = _load_points()
        alcaldias = set()
        for f in _cache_points.get("features", []):
            p = f.get("properties", {})
            if isinstance(p.get("alcaldia"), str):
                alcaldias.add(p["alcaldia"].strip())
        _meta_cache = {"alcaldias": sorted(alcaldias)}

def _filter_points_by_alcaldia(feats: List[Dict[str, Any]], alcaldia: Optional[str]) -> List[Dict[str, Any]]:
    if not alcaldia: return []
    n_alc = _normalize(alcaldia)
    out = []
    for f in feats:
        p = f.get("properties", {})
        if n_alc in _normalize(p.get("alcaldia","")):
            out.append(f)
    return out

# ===== NUEVO: Carga y procesamiento de reportes de incidencia =====
def _load_reports() -> Dict[str, Any]:
    if not REPORTES_PATH.exists():
        raise FileNotFoundError(f"No se encontró reportes_incidenciaU.geojson en: {REPORTES_PATH}")
    with open(REPORTES_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    # Reutilizamos la misma lógica de transformación de coordenadas
    return _transform_points_geojson(raw)

def _ensure_reports_meta():
    global _reportes_cache, _meta_cache
    if _reportes_cache is None:
        _reportes_cache = _load_reports()
        impactos = set()
        for f in _reportes_cache.get("features", []):
            props = f.get("properties", {})
            impacto = props.get("impacto_delito")
            if isinstance(impacto, str) and impacto.strip():
                impactos.add(impacto.strip())
        # Asegurarnos que el meta_cache ya existe
        if _meta_cache is None: _meta_cache = {}
        _meta_cache["impactos_delito"] = sorted(list(impactos))

# ===== NUEVO: Filtrado de reportes por alcaldía e impacto =====
def _filter_reports(feats: List[Dict[str, Any]], alcaldia: Optional[str], impacto: Optional[str]) -> List[Dict[str, Any]]:
    results = feats
    if alcaldia:
        n_alc = _normalize(alcaldia)
        results = [f for f in results if _normalize(f.get("properties", {}).get("alcaldia", "")) == n_alc]
    
    if impacto:
        # No normalizamos el impacto para mantener las categorías exactas
        impacto_clean = impacto.strip()
        results = [f for f in results if (f.get("properties", {}).get("impacto_delito", "") or "").strip() == impacto_clean]
        
    return results

# ===================== Fronteras (disolver colonias) =====================
def _build_hulls_from_demog() -> Dict[str, Any]:
    if not DEMOG_PATH.exists():
        raise FileNotFoundError(f"No se encontró DemograficosD_GJ.geojson en: {DEMOG_PATH}")
    with open(DEMOG_PATH, "r", encoding="utf-8") as fh:
        gj = json.load(fh)

    groups: Dict[str, List] = {}
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        alc = (props.get("alcaldia") or "").strip()
        geom = feat.get("geometry")
        if not alc or not geom: continue
        try:
            g_utm = shp_shape(geom)  # EPSG:32614
        except Exception:
            continue
        if g_utm.is_empty: continue
        groups.setdefault(alc, []).append(g_utm)

    out_features: List[Dict[str, Any]] = []
    for alc, geoms in groups.items():
        dissolved_utm = unary_union(geoms)
        dissolved_wgs = _geom_utm_to_wgs(dissolved_utm)
        if dissolved_wgs.is_empty: continue
        out_features.append({
            "type":"Feature",
            "properties":{"alcaldia": alc, "source":"DEMOG_dissolve"},
            "geometry": shp_mapping(dissolved_wgs)
        })

    return {
        "type":"FeatureCollection",
        "name":"alcaldias_fronteras",
        "crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::4326"}},
        "features": out_features
    }

def _ensure_hulls():
    global _hulls_cache
    if _hulls_cache is not None: return
    _hulls_cache = _build_hulls_from_demog()

def _get_hull_geometry_wgs(alcaldia: str):
    _ensure_hulls()
    for f in _hulls_cache.get("features", []):
        if (f.get("properties", {}) or {}).get("alcaldia") == alcaldia:
            return shp_shape(f["geometry"])  # WGS
    return None

# ===================== Colonias (polígonos) =====================
def _ensure_colonias():
    """Carga GeoColonias.json (EPSG:32614), transforma a WGS84 y agrupa por alcaldía."""
    global _colonias_cache
    if _colonias_cache is not None:
        return
    if not COLONIAS_PATH.exists():
        raise FileNotFoundError(f"No se encontró GeoColonias.json en: {COLONIAS_PATH}")
    with open(COLONIAS_PATH, "r", encoding="utf-8") as fh:
        gj = json.load(fh)

    feats_wgs: List[Dict[str, Any]] = []
    by_alc: Dict[str, List[Dict[str, Any]]] = {}
    names: Dict[str, List[str]] = {}

    for feat in gj.get("features", []):
        props = feat.get("properties", {}) or {}
        alc = (props.get("alcaldia") or "").strip()
        col = (props.get("colonia") or "").strip()
        geom = feat.get("geometry")
        if not alc or not col or not geom:
            continue
        try:
            g_utm = shp_shape(geom)
            g_wgs = _geom_utm_to_wgs(g_utm)
            if g_wgs.is_empty:
                continue
            f_wgs = {"type":"Feature","properties":{"alcaldia":alc,"colonia":col},"geometry":shp_mapping(g_wgs)}
            feats_wgs.append(f_wgs)
            by_alc.setdefault(alc, []).append(f_wgs)
            names.setdefault(alc, set()).add(col)
        except Exception:
            continue

    names = {k: sorted(list(v)) for k, v in names.items()}
    _colonias_cache = {
        "type":"FeatureCollection",
        "crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::4326"}},
        "features": feats_wgs,
        "by_alc": by_alc,
        "names": names
    }

# ===================== Malla de candidatos =====================
def _grid_points_in_polygon_utm(poly_utm, spacing: float) -> List[Tuple[float, float]]:
    """
    Malla cuadrada dentro del polígono UTM (spacing en metros). Incluye borde (.covers).
    """
    minx, miny, maxx, maxy = poly_utm.bounds
    xs = int((maxx - minx) // spacing) + 1
    ys = int((maxy - miny) // spacing) + 1
    pts: List[Tuple[float, float]] = []
    y = miny
    for _ in range(ys):
        x = minx
        for _ in range(xs):
            p = Point(x, y)
            if poly_utm.covers(p):
                pts.append((x, y))
            x += spacing
        y += spacing
    return pts

def _generate_candidates_for_alcaldia(alcaldia: str, spacing_m: float, min_dist_m: float, limit: Optional[int]) -> Dict[str, Any]:
    """
    Crea candidatos:
      - malla con 'spacing_m'
      - excluye puntos a menos de 'min_dist_m' de cámaras existentes (si > 0)
    """
    _ensure_points_meta()
    hull_wgs = _get_hull_geometry_wgs(alcaldia)
    if hull_wgs is None:
        return {"type":"FeatureCollection","features":[]}

    hull_utm = _geom_wgs_to_utm(hull_wgs)

    feats = _filter_points_by_alcaldia(_cache_points.get("features", []), alcaldia)
    existing_pts_utm = []
    for f in feats:
        g = f.get("geometry") or {}
        if g.get("type") != "Point": continue
        lonlat = g.get("coordinates") or []
        if len(lonlat) < 2: continue
        lon, lat = float(lonlat[0]), float(lonlat[1])
        x, y = _tf_wgs2utm.transform(lon, lat)
        existing_pts_utm.append(Point(x, y))
    tree = STRtree(existing_pts_utm) if existing_pts_utm else None

    grid_xy = _grid_points_in_polygon_utm(hull_utm, spacing_m)

    candidates: List[Dict[str, Any]] = []
    for (x, y) in grid_xy:
        pt = Point(x, y)

        # filtro de distancia mínima robusto
        if tree is not None and float(min_dist_m) > 0:
            try:
                buf = pt.buffer(float(min_dist_m))
                near = tree.query(buf)  # len(...) > 0 si hay algo cerca
                n = len(near) if hasattr(near, "__len__") else (0 if near is None else 1)
                if n > 0:
                    continue
            except Exception:
                # fallback
                if any(pt.distance(g) < float(min_dist_m) for g in existing_pts_utm):
                    continue

        lon, lat = _tf_utm2wgs.transform(x, y)
        candidates.append({
            "type":"Feature",
            "properties":{
                "alcaldia": alcaldia,
                "generated": True,
                "spacing_m": spacing_m,
                "min_dist_m": min_dist_m
            },
            "geometry":{"type":"Point","coordinates":[lon, lat]}
        })
        if limit and len(candidates) >= limit:
            break

    return {
        "type":"FeatureCollection",
        "name": f"candidatos_{alcaldia}",
        "crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::4326"}},
        "features": candidates
    }

# ===================== Rutas =====================
@app.get("/")
async def index():
    return FileResponse(BASE / "index.html")

@app.get("/meta")
async def meta():
    _ensure_points_meta()
    return JSONResponse(_meta_cache)

@app.get("/hulls")
async def hulls():
    _ensure_hulls()
    return JSONResponse(_hulls_cache)

@app.get("/colonias")
async def colonias(alcaldia: str = Query(..., description="Alcaldía exacta para limitar la respuesta")):
    """Devuelve las colonias (polígonos) de la alcaldía dada."""
    _ensure_colonias()
    feats = _colonias_cache["by_alc"].get(alcaldia, [])
    return JSONResponse({
        "type":"FeatureCollection",
        "crs": _colonias_cache["crs"],
        "features": feats,
    })

@app.get("/reportes")
async def reportes(
    alcaldia: str = Query(..., description="Alcaldía exacta para filtrar"),
    impacto_delito: Optional[str] = Query(None, description="Filtrar por 'DELITO DE ALTO IMPACTO' o 'DELITO DE BAJO IMPACTO'")
):
    _ensure_reports_meta()
    feats = _reportes_cache.get("features", [])
    filtered = _filter_reports(feats, alcaldia, impacto_delito)
    return JSONResponse({
        "type": "FeatureCollection",
        "name": "reportes_filtrados",
        "crs": _reportes_cache.get("crs"),
        "features": filtered,
        "count": len(filtered),
    })

@app.post("/create_instance")
async def create_instance(payload: InstancePayload = Body(...)):
    """
    Recibe puntos y parámetros, los transforma a UTM y guarda el archivo .dat.
    """
    if not payload.name.endswith(".dat"):
        payload.name += ".dat"
        
    if not payload.points:
        return JSONResponse(status_code=400, content={"error": "La lista de puntos no puede estar vacía."})

    # Transformar coordenadas de WGS84 (lat,lon) a UTM (x,y)
    transformed_points = []
    for i, p in enumerate(payload.points):
        try:
            x, y = _tf_wgs2utm.transform(p.lon, p.lat)
            transformed_points.append({
                "id": i + 1,
                "x": x,
                "y": y,
                "flag": p.flag,
                "prob": p.prob
            })
        except Exception as e:
            print(f"Error transformando punto: {p}, error: {e}")
            continue # Ignorar puntos con error de transformación

    N = len(transformed_points)
    nombre_instancia = payload.name

    # Crear el contenido del archivo .dat
    content_lines = [
        "/* CONJUNTOS */",
        f"set N:= {N} ;",
        "",
        "/* PARAMETROS */",
        f"param P:= {payload.presupuesto} ;",
        f"param R:= {payload.radio} ;",
        f"param c1:= {payload.c1} ;",
        f"param c2:= {payload.c2} ;",
        f'param nombre_instancia := "{nombre_instancia}" ;',
        "",
        "param : coordx coordy flag prob_ohca:="
    ]

    for p in transformed_points:
        line = f"{p['id']} {p['x']:.6f} {p['y']:.6f} {p['flag']} {p['prob']:.2f}"
        content_lines.append(line)
    
    content_lines.append(";")

    # Guardar el archivo
    try:
        instance_dir = BASE / "INSTANCES"
        instance_dir.mkdir(exist_ok=True)
        file_path = instance_dir / payload.name
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))
            
        return {
            "ok": True, 
            "message": f"Instancia '{payload.name}' creada con {N} puntos.",
            "path": str(file_path)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Error al guardar el archivo: {e}"})



@app.get("/data")
async def data(
    alcaldia: Optional[str] = Query(default=None, description="Alcaldía exacta"),
    limit: Optional[int] = Query(default=None, ge=1, le=100000),
):
    _ensure_points_meta()
    feats = _cache_points.get("features", [])
    feats = _filter_points_by_alcaldia(feats, alcaldia) if alcaldia else []
    if limit: feats = feats[:limit]
    return JSONResponse({
        "type":"FeatureCollection",
        "name": _cache_points.get("name","camaraPosU"),
        "crs": _cache_points.get("crs"),
        "features": feats,
        "count": len(feats),
    })

@app.get("/grid")
async def grid(
    alcaldia: str = Query(...),
    spacing_m: float = Query(250, ge=10, le=2000),
    min_dist_m: float = Query(0, ge=0, le=2000),
    limit: Optional[int] = Query(None, ge=1, le=100000),
):
    _ensure_points_meta()
    _ensure_hulls()
    fc = _generate_candidates_for_alcaldia(alcaldia, spacing_m, min_dist_m, limit)
    return JSONResponse(fc)

if __name__ == "__main__":
    # uvicorn app:app --reload --host 127.0.0.1 --port 8000
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)