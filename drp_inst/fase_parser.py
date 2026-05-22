#!/usr/bin/env python3
"""
fase_parser.py
==============
Lee una instancia (.dat) + pareto_front.txt + ampl_log_full.txt y produce
un dict con los datos de 4 fases del plan de implementación.

Flujo:
  1. Lee pareto_front.txt → filtra duplicados y puntos dominados → frente real
  2. Selecciona 4 puntos representativos por percentil de F2 (costo)
  3. Para cada punto, busca en ampl_log_full.txt la solución con F2 más cercano
  4. Extrae posiciones de AEDs de esa solución

Esto evita que los dos puntos extremos calculados al inicio del log
(Objetivo 1 / Objetivo 2) contaminen la selección de fases.

Fases:
  Fase 0 → F2 mínimo   (estado actual, sin cambios)
  Fase 1 → ~33% de rango F2
  Fase 2 → ~66% de rango F2
  Fase 3 → F2 máximo   (máxima cobertura en el frente real)

Clasificación de AEDs en cada fase (respecto a Fase 0):
  "existente" → nodo flag=1 que se mantiene en su lugar       (azul)
  "removido"  → nodo flag=1 que fue desinstalado de su lugar  (gris)
  "nuevo"     → nodo flag=0 que fue ocupado (reubicación o compra) (verde)

Uso:
    from fase_parser import parse_plan
    plan = parse_plan("drp_657_STATEN_ISLAND", problem_type="drp")
"""

import re
from pathlib import Path

import numpy as np

# ── Rutas base ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
INST_DIR  = BASE_DIR / "datos" / "inst"
RES_AMPL  = BASE_DIR / "datos" / "res" / "raw_ampl"


# ── Parser de instancia .dat ──────────────────────────────────────────────────

def parse_instance(inst_name: str) -> dict:
    """Lee el archivo .dat y devuelve parámetros + nodos."""
    path = INST_DIR / f"{inst_name}.dat"
    text = path.read_text(encoding="utf-8", errors="replace")

    params = {}
    for key in ("N_total", "P", "R", "c1", "c2"):
        m = re.search(rf"param\s+{key}\s*:=\s*([\d.]+)", text)
        if m:
            params[key] = float(m.group(1))

    nodes = {}
    m = re.search(
        r"param\s*:\s*coordx\s+coordy\s+flag\s+prob_ohca\s*:=(.*?)(?=\s*;|\Z)",
        text, re.DOTALL,
    )
    if m:
        for line in m.group(1).splitlines():
            parts = line.split()
            if len(parts) == 5:
                nid = int(parts[0])
                nodes[nid] = {
                    "id":   nid,
                    "x":    float(parts[1]),
                    "y":    float(parts[2]),
                    "flag": int(parts[3]),
                    "prob": float(parts[4]),
                }

    # UTM zone: NYC (>3M northing) = 32618, México = 32614
    avg_y = sum(n["y"] for n in nodes.values()) / max(len(nodes), 1)
    epsg  = 32618 if avg_y > 3_000_000 else 32614

    return {"params": params, "nodes": nodes, "epsg_utm": epsg}


# ── Lectura y filtrado del frente de Pareto ───────────────────────────────────

def _read_front(pf_path: Path) -> np.ndarray:
    """
    Lee pareto_front.txt (formato 'F1 F2' o 'idx F1 F2').
    Devuelve array (N, 2) con columnas [F1, F2].
    """
    rows = []
    for line in pf_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            rows.append((float(parts[0]), float(parts[1])))
        elif len(parts) == 3:
            rows.append((float(parts[1]), float(parts[2])))
    return np.array(rows) if rows else np.empty((0, 2))


def _pareto_nondom(pts: np.ndarray) -> np.ndarray:
    """
    Devuelve subconjunto de puntos no dominados (minimización en ambos objetivos).
    También elimina duplicados exactos.
    """
    if len(pts) == 0:
        return pts
    pts = np.unique(pts, axis=0)
    dominated = np.zeros(len(pts), dtype=bool)
    for i, p in enumerate(pts):
        if dominated[i]:
            continue
        mask = np.all(pts <= p, axis=1) & np.any(pts < p, axis=1)
        dominated[mask] = True
    return pts[~dominated]


def _pick_phase_targets(front: np.ndarray, n: int = 4) -> list[tuple[float, float]]:
    """
    Selecciona n puntos del frente por percentil de cobertura |F1|.

    F1 es negativo (minimización). Más negativo = mayor cobertura.
    Fase 0 → peor cobertura (F1 más cercano a 0, costo mínimo).
    Fase n-1 → mejor cobertura (F1 más negativo, costo máximo).
    Devuelve lista de (F1, F2).
    """
    f1 = front[:, 0]
    f1_worst = float(f1.max())   # menos negativo → menor cobertura
    f1_best  = float(f1.min())   # más negativo   → mayor cobertura
    targets = [f1_worst + (f1_best - f1_worst) * k / (n - 1) for k in range(n)]
    result = []
    for t in targets:
        idx = int(np.argmin(np.abs(f1 - t)))
        result.append((float(front[idx, 0]), float(front[idx, 1])))
    return result


# ── Parser del log AMPL ───────────────────────────────────────────────────────

def _parse_ids(text: str) -> set[int]:
    """Extrae IDs numéricos de una línea tipo '1, 2, 3, ...' o 'None'."""
    text = text.strip()
    if not text or text.lower() == "none":
        return set()
    return {int(x) for x in re.findall(r"\d+", text)}


def parse_ampl_log(log_path: Path) -> list[dict]:
    """
    Parsea ampl_log_full.txt y devuelve lista de TODAS las soluciones
    (incluye los dos puntos extremos iniciales y las iteraciones epsilon).
    Cada solución: {f1, f2, kept, removed, new_locs}
    """
    text = log_path.read_text(encoding="utf-8", errors="replace")

    block_re = re.compile(
        r"Objective Values:\s*F1\(Coverage\)=(-?[\d.]+),\s*F2\(Cost\)=([\d.]+)"
        r"(.*?)"
        r"(?=Objective Values:|==> Ejecucion|\Z)",
        re.DOTALL,
    )

    solutions = []
    for m in block_re.finditer(text):
        f1   = float(m.group(1))
        f2   = float(m.group(2))
        body = m.group(3)

        mk = re.search(r"Pre-existing AEDs kept \(\d+\):\s*(.*)", body)
        kept = _parse_ids(mk.group(1)) if mk else set()

        mr = re.search(r"AEDs Removed from old spots \(\d+\).*?:\s*(.*)", body)
        removed = _parse_ids(mr.group(1)) if mr else set()

        mn = re.search(r"IDs(?:\s+of\s+new\s+locations)?:\s*(.*)", body)
        new_locs = _parse_ids(mn.group(1)) if mn else set()

        solutions.append({
            "f1": f1, "f2": f2,
            "kept": kept, "removed": removed, "new_locs": new_locs,
        })

    return solutions


def _find_solution(solutions: list[dict], f2_target: float) -> dict:
    """Devuelve la solución del log con F2 más cercano a f2_target."""
    return min(solutions, key=lambda s: abs(s["f2"] - f2_target))


# ── Clasificación de AEDs por fase ───────────────────────────────────────────

def _classify_aeds(sol: dict, nodes: dict) -> list[dict]:
    """
    Devuelve lista de dicts {id, x, y, tipo} para una solución.
    tipos: 'existente', 'removido', 'nuevo'
    """
    aeds = []
    for nid in sol["kept"]:
        if nid in nodes:
            n = nodes[nid]
            aeds.append({"id": nid, "x": n["x"], "y": n["y"], "tipo": "existente"})
    for nid in sol["removed"]:
        if nid in nodes:
            n = nodes[nid]
            aeds.append({"id": nid, "x": n["x"], "y": n["y"], "tipo": "removido"})
    for nid in sol["new_locs"]:
        if nid in nodes:
            n = nodes[nid]
            aeds.append({"id": nid, "x": n["x"], "y": n["y"], "tipo": "nuevo"})
    return aeds


# ── API principal ─────────────────────────────────────────────────────────────

NOMBRES_FASE = [
    "Estado actual",
    "Intervención prioritaria",
    "Expansión intermedia",
    "Cobertura completa",
]


def parse_plan(inst_name: str, problem_type: str = "drp", run: int = 1) -> dict:
    """
    Construye el plan de 4 fases para una instancia AMPL.

    Usa pareto_front.txt para seleccionar los 4 puntos representativos
    (evita que los puntos extremos del log contaminen la selección).

    Parámetros
    ----------
    inst_name    : nombre de la instancia (ej. 'drp_657_STATEN_ISLAND')
    problem_type : 'drp' o 'cam'
    run          : número de run AMPL (1-10)

    Devuelve dict con:
      instance, problem_type, epsg_utm, radio,
      demand_nodes: [{id, x, y, prob}, ...]   # nodos flag=0
      fases: [{numero, nombre, f1, f2, aeds: [{id, x, y, tipo}]}, ...]
    """
    inst   = parse_instance(inst_name)
    nodes  = inst["nodes"]
    params = inst["params"]

    run_dir = RES_AMPL / problem_type / inst_name / f"run_{run}"

    # ── 1. Frente de Pareto desde pareto_front.txt ────────────────────────────
    pf_path = run_dir / "pareto_front.txt"
    if not pf_path.exists():
        raise FileNotFoundError(f"pareto_front.txt no encontrado: {pf_path}")

    raw   = _read_front(pf_path)
    front = _pareto_nondom(raw)
    front = front[front[:, 1].argsort()]   # ordenar por F2 ascendente

    if len(front) == 0:
        raise ValueError(f"Frente de Pareto vacío en: {pf_path}")

    # ── 2. Seleccionar 4 fases por percentil de F2 ───────────────────────────
    phase_targets = _pick_phase_targets(front, n=4)

    # ── 3. Leer soluciones del log para obtener posiciones de AEDs ───────────
    log_path = run_dir / "ampl_log_full.txt"
    if not log_path.exists():
        raise FileNotFoundError(f"Log no encontrado: {log_path}")

    all_solutions = parse_ampl_log(log_path)
    if not all_solutions:
        raise ValueError(f"No se encontraron soluciones en: {log_path}")

    # ── 4. Construir las 4 fases ──────────────────────────────────────────────
    fases = []
    for i, (f1_t, f2_t) in enumerate(phase_targets):
        sol = _find_solution(all_solutions, f2_t)
        fases.append({
            "numero": i,
            "nombre": NOMBRES_FASE[i],
            "f1":     sol["f1"],
            "f2":     sol["f2"],
            "aeds":   _classify_aeds(sol, nodes),
        })

    demand_nodes = [
        {"id": nid, "x": n["x"], "y": n["y"], "prob": n["prob"]}
        for nid, n in nodes.items()
        if n["flag"] == 0
    ]

    return {
        "instance":     inst_name,
        "problem_type": problem_type,
        "epsg_utm":     inst["epsg_utm"],
        "radio":        params.get("R", 100.0),
        "demand_nodes": demand_nodes,
        "fases":        fases,
        "front_size":   len(front),
    }


# ── CLI de diagnóstico ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("inst", help="Nombre instancia (ej. drp_657_STATEN_ISLAND)")
    ap.add_argument("--type", default="drp", choices=["drp", "cam"])
    ap.add_argument("--run",  type=int, default=1)
    args = ap.parse_args()

    plan = parse_plan(args.inst, args.type, args.run)

    print(f"Instancia  : {plan['instance']}")
    print(f"EPSG UTM   : {plan['epsg_utm']}")
    print(f"Radio      : {plan['radio']} m")
    print(f"Nodos dem. : {len(plan['demand_nodes'])}")
    print(f"Frente     : {plan['front_size']} puntos no dominados")
    for f in plan["fases"]:
        tipos = {}
        for a in f["aeds"]:
            tipos[a["tipo"]] = tipos.get(a["tipo"], 0) + 1
        cob = abs(f["f1"]) * 100
        print(f"  Fase {f['numero']} ({f['nombre']}): cob={cob:.2f}%  F2={f['f2']:.1f}  AEDs={tipos}")
