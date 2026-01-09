#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path

# Captura: ./hv -r "X  Y"  PATH
CMD_RE = re.compile(
    r'^\s*\./hv\s+-r\s+"(?P<rx>[^"]+?)\s+(?P<ry>[^"]+?)"\s+(?P<path>\S+)\s*$'
)

def extract_instance_from_path(p: str) -> str:
    """
    Ej: ../../datos/res/raw_ampl/cam/cam_1390_MILPA_ALTA/run_1/pareto_front.txt
    -> cam_1390_MILPA_ALTA
    """
    parts = Path(p).parts
    # Busca "run_1" y toma el elemento anterior como nombre de instancia
    for i in range(len(parts) - 1):
        if parts[i] == "run_1" and i - 1 >= 0:
            return parts[i - 1]
    # fallback: si no está run_1, usa el padre del archivo
    return Path(p).parent.name

def run_commands(txt_path: Path, out_path: Path | None, stop_on_error: bool, dry_run: bool):
    lines = txt_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    rows = []  # (inst_dat, hv, ref_x, ref_y)

    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        m = CMD_RE.match(line)
        if not m:
            print(f"[SKIP] Línea {lineno}: formato no reconocido -> {line}")
            continue

        ref_x = m.group("rx").strip()
        ref_y = m.group("ry").strip()
        pf_path = m.group("path").strip()

        inst = extract_instance_from_path(pf_path)
        inst_dat = f"{inst}.dat"

        if dry_run:
            hv_out = "DRY_RUN"
            code = 0
        else:
            p = subprocess.run(line, shell=True, text=True, capture_output=True)
            code = p.returncode
            hv_out = (p.stdout or "").strip()

            if code != 0:
                err = (p.stderr or "").strip()
                print(f"[ERR ] Línea {lineno}: returncode={code}")
                if err:
                    print(f"       stderr: {err}")
                if stop_on_error:
                    raise SystemExit(f"Abortando por error en línea {lineno}")

        rows.append((inst_dat, hv_out, ref_x, ref_y))

    lines_out = []

    if rows:
        parsed = []
        for inst_dat, hv_out, ref_x, ref_y in rows:
            hv_val = float(hv_out)
            rx_val = float(ref_x)
            ry_val = float(ref_y)
            kind = "cam" if inst_dat.startswith("cam_") else "drp"
            parsed.append((inst_dat, kind, hv_val, rx_val, ry_val))

        w_inst = max(len(r[0]) for r in parsed)

        def int_len(x: float) -> int:
            return len(str(int(abs(x)))) + (1 if x < 0 else 0)

        max_hv_int = max(int_len(r[2]) for r in parsed)
        max_rx_int = max(int_len(r[3]) for r in parsed)
        max_ry_int = max(int_len(r[4]) for r in parsed)

        w_hv = max_hv_int + 1 + 6   # 6 dec
        w_rx = max_rx_int + 1 + 7   # reservamos 7 dec para alinear CAM/DRP
        w_ry = max_ry_int + 1 + 3   # 3 dec

        for inst_dat, kind, hv_val, rx_val, ry_val in parsed:
            hv_s = f"{hv_val:.6f}".rjust(w_hv)

            dec = 4 if kind == "cam" else 7
            rx_s = f"{rx_val:.{dec}f}"
            if dec < 7:
                rx_s += " " * (7 - dec)  # padding para que CAM calce con 7 dec
            rx_s = rx_s.rjust(w_rx)

            ry_s = f"{ry_val:.3f}".rjust(w_ry)

            line = f"{inst_dat:<{w_inst}}  {hv_s}  {rx_s}  {ry_s}"
            print(line)
            lines_out.append(line)

    # Guardar el MISMO formato alineado al archivo
    if out_path is not None:
        out_path.write_text("\n".join(lines_out) + ("\n" if lines_out else ""),
                            encoding="utf-8")
        print(f"\n[INFO] Guardado en: {out_path}")

def main():
    ap = argparse.ArgumentParser(description="Ejecuta comandos ./hv desde un .txt y resume resultados.")
    ap.add_argument("txt", type=Path, help="Archivo .txt con líneas tipo: ./hv -r \"x y\" path")
    ap.add_argument("-o", "--out", type=Path, default=None, help="Archivo de salida (opcional)")
    ap.add_argument("--stop-on-error", action="store_true", help="Detenerse si un comando falla")
    ap.add_argument("--dry-run", action="store_true", help="No ejecuta, solo imprime lo que haría")
    args = ap.parse_args()

    if not args.txt.exists():
        raise SystemExit(f"No existe: {args.txt}")

    run_commands(args.txt, args.out, args.stop_on_error, args.dry_run)

if __name__ == "__main__":
    main()

# python3 run_hv_from_txt.py hv_commands.txt -o hv_results.txt

# python3 run_hv_from_txt.py hv_commands.txt --dry-run
