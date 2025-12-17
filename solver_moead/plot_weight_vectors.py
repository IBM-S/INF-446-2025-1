#!/usr/bin/env python3
import os
import glob
import argparse
import numpy as np
import matplotlib.pyplot as plt

def _load_numeric(path: str) -> np.ndarray:
    # soporta espacios, tabs, comas, y comentarios estilo '#'
    # intenta varias lecturas por robustez
    raw = []
    with open(path, "r", encoding="utf-8", errors="help") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            s = s.replace(",", " ")
            parts = s.split()
            try:
                row = [float(x) for x in parts]
                raw.append(row)
            except:
                # línea no numérica => la ignoramos
                continue
    if not raw:
        return np.empty((0, 0), dtype=float)
    # normaliza largo de filas (por si hay líneas raras)
    maxlen = max(len(r) for r in raw)
    raw2 = [r + [np.nan]*(maxlen-len(r)) for r in raw]
    arr = np.array(raw2, dtype=float)
    # elimina columnas completamente NaN
    keep = ~np.all(np.isnan(arr), axis=0)
    arr = arr[:, keep]
    # elimina filas con NaN (por seguridad)
    arr = arr[~np.any(np.isnan(arr), axis=1)]
    return arr

def _detect_weights(arr: np.ndarray, tol=1e-3) -> np.ndarray:
    """Si la 1ra columna parece ser un índice, la descarta."""
    if arr.size == 0:
        return arr
    if arr.shape[1] <= 1:
        return arr
    # caso A: usar todas las columnas como pesos
    sum_all = np.mean(np.abs(arr.sum(axis=1) - 1.0))
    # caso B: descartar primera col
    sum_drop = np.mean(np.abs(arr[:, 1:].sum(axis=1) - 1.0))
    # heurística: si al dropear mejora mucho, era índice
    if sum_drop + 1e-12 < 0.2 * sum_all and arr.shape[1] >= 3:
        return arr[:, 1:]
    return arr

def summarize(W: np.ndarray, name: str, tol=1e-6):
    if W.size == 0:
        print(f"[{name}] vacío o no numérico.")
        return

    sums = W.sum(axis=1)
    mins = W.min(axis=0)
    maxs = W.max(axis=0)

    neg = np.sum(W < -tol)
    nonneg_viol = np.sum(W < -1e-9)
    sum_err = np.abs(sums - 1.0)

    print(f"\n=== {name} ===")
    print(f"  shape: {W.shape}  (n_vectores={W.shape[0]}, dim={W.shape[1]})")
    print(f"  sum(w)  : mean={sums.mean():.6f}  min={sums.min():.6f}  max={sums.max():.6f}")
    print(f"  |sum-1| : mean={sum_err.mean():.6e}  max={sum_err.max():.6e}")
    print(f"  negativos(<-tol): {neg}  (violaciones no-neg: {nonneg_viol})")
    print(f"  min por dim: {mins}")
    print(f"  max por dim: {maxs}")

def plot_2d(W: np.ndarray, title: str, outpath: str):
    w1, w2 = W[:, 0], W[:, 1]
    plt.figure()
    plt.scatter(w1, w2, s=18)
    # linea simplex w1+w2=1
    t = np.linspace(0, 1, 200)
    plt.plot(t, 1 - t)
    plt.xlabel("w1")
    plt.ylabel("w2")
    plt.title(title)
    plt.axis("equal")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()

    # espaciado (si debería ser uniforme)
    idx = np.argsort(w1)
    w1s = w1[idx]
    dif = np.diff(w1s)
    plt.figure()
    plt.plot(dif)
    plt.xlabel("i (ordenado por w1)")
    plt.ylabel("Δw1[i]")
    plt.title(title + " — espaciado en w1 (ideal: casi constante)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath.replace(".png", "_spacing.png"), dpi=160)
    plt.close()

def plot_3d_simplex(W: np.ndarray, title: str, outpath: str):
    # proyección barycéntrica al triángulo equilátero
    w1, w2, w3 = W[:, 0], W[:, 1], W[:, 2]
    x = w2 + 0.5 * w3
    y = (np.sqrt(3)/2) * w3

    plt.figure()
    plt.scatter(x, y, s=18)
    # triángulo
    tri = np.array([[0,0],[1,0],[0.5,np.sqrt(3)/2],[0,0]])
    plt.plot(tri[:,0], tri[:,1])
    plt.title(title + " — proyección simplex (3D→2D)")
    plt.axis("equal")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()

def plot_pca(W: np.ndarray, title: str, outpath: str):
    # PCA simple con SVD
    X = W - W.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    Z = X @ Vt[:2].T

    plt.figure()
    plt.scatter(Z[:,0], Z[:,1], s=18)
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.title(title + " — PCA (dim>3)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="SETTINGS/weightvectors", help="Directorio de weight vectors")
    ap.add_argument("--glob", default="*", help="Patrón glob (ej: *.dat, *.txt)")
    ap.add_argument("--out", default="weightvector_plots", help="Carpeta salida")
    args = ap.parse_args()

    base = args.dir
    paths = sorted(glob.glob(os.path.join(base, args.glob)))
    os.makedirs(args.out, exist_ok=True)

    if not paths:
        print(f"No encontré archivos en {base} con glob={args.glob}")
        return

    for p in paths:
        arr = _load_numeric(p)
        W = _detect_weights(arr)
        name = os.path.basename(p)
        summarize(W, name)

        if W.size == 0:
            continue

        outpng = os.path.join(args.out, name + ".png")
        if W.shape[1] == 2:
            plot_2d(W, name, outpng)
        elif W.shape[1] == 3:
            plot_3d_simplex(W, name, outpng)
        else:
            plot_pca(W, name, outpng)

    print(f"\nListo. Gráficos en: {args.out}/")

if __name__ == "__main__":
    main()
