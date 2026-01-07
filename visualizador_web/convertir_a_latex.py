#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
from pathlib import Path

def detect_sep(sample: str) -> str:
    # intenta detectar separador mirando la primera línea no vacía
    candidates = ["\t", ";", ",", " "]
    counts = {c: sample.count(c) for c in candidates}
    # si no hay ninguno, default espacio
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else " "

def split_line(line: str, sep: str) -> list[str]:
    line = line.rstrip("\n")
    if sep == " ":
        # colapsa múltiples espacios
        return re.split(r"\s+", line.strip()) if line.strip() else []
    return [x.strip() for x in line.split(sep)]

def escape_latex(s: str) -> str:
    # escape básico de caracteres especiales
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in s)

def normalize_table(cells: list[list[str]], rows: int, cols: int) -> list[list[str]]:
    # asegurar tamaño rows x cols
    out = []
    for r in range(rows):
        if r < len(cells):
            row = cells[r][:cols] + [""] * max(0, cols - len(cells[r]))
        else:
            row = [""] * cols
        out.append(row)
    return out

def to_latex_tabular(table: list[list[str]], header: bool, align: str | None, booktabs: bool,
                     caption: str | None, label: str | None) -> str:
    cols = len(table[0]) if table else 0
    if align:
        spec = align
        if len(spec) != cols:
            raise ValueError(f"--align tiene largo {len(spec)} pero cols={cols}. Ej: {'c'*cols}")
    else:
        spec = "c" * cols

    lines = []
    if caption or label:
        lines.append(r"\begin{table}[ht]")
        lines.append(r"\centering")

    if booktabs:
        lines.append(rf"\begin{{tabular}}{{{spec}}}")
        lines.append(r"\toprule")
    else:
        # con bordes verticales
        spec2 = "|" + "|".join(list(spec)) + "|"
        lines.append(rf"\begin{{tabular}}{{{spec2}}}")
        lines.append(r"\hline")

    for i, row in enumerate(table):
        row_esc = [escape_latex(x) for x in row]
        lines.append(" " + " & ".join(row_esc) + r" \\")
        if header and i == 0:
            lines.append(r"\midrule" if booktabs else r"\hline")
        else:
            # opcional: línea por fila solo si NO booktabs
            if not booktabs:
                lines.append(r"\hline")

    if booktabs:
        lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")

    if caption:
        lines.append(rf"\caption{{{escape_latex(caption)}}}")
    if label:
        lines.append(rf"\label{{{label}}}")

    if caption or label:
        lines.append(r"\end{table}")

    return "\n".join(lines)

def is_number_token(s: str) -> bool:
    # permite +/-, decimales, y notación científica
    return bool(re.fullmatch(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?", s.strip()))

def format_number_str(s: str, precision: int, thousands_sep: str, decimal_sep: str) -> str:
    x = float(s)
    # formatea con miles usando "," internamente y "." como decimal
    fmt = f"{{:,.{precision}f}}".format(x)  # ej: 2,357,772.568341
    # ahora ajusta separadores si el usuario pidió otros
    if thousands_sep == "," and decimal_sep == ".":
        return fmt
    # truco con placeholder para no pisar reemplazos
    fmt = fmt.replace(",", "__TH__").replace(".", "__DE__")
    fmt = fmt.replace("__TH__", thousands_sep).replace("__DE__", decimal_sep)
    return fmt


def main():
    ap = argparse.ArgumentParser(description="Genera una tabla LaTeX desde un archivo de texto.")
    ap.add_argument("--file", required=True, help="Ruta al archivo (txt/csv/etc.)")
    ap.add_argument("--rows", type=int, required=True, help="Número de filas a generar")
    ap.add_argument("--cols", type=int, required=True, help="Número de columnas a generar")
    ap.add_argument("--sep", default=None, help=r"Separador: '\t', ',', ';' o ' ' (default autodetecta)")
    ap.add_argument("--header", action="store_true", help="Trata la primera fila como encabezado")
    ap.add_argument("--align", default=None, help="Especificación de alineación, ej: lcrcc")
    ap.add_argument("--caption", default=None, help="Caption para el entorno table")
    ap.add_argument("--label", default=None, help="Label (sin espacios), ej: tab:mi_tabla")
    ap.add_argument("--booktabs", action="store_true", help="Usa booktabs (\\toprule, \\midrule, \\bottomrule)")
    ap.add_argument("--format_numbers", action="store_true", help="Formatea tokens numéricos con separador de miles.")
    ap.add_argument("--precision", type=int, default=6, help="Cantidad de decimales al formatear números (default 6).")
    ap.add_argument("--thousands", default=",", help="Separador de miles (default ','). Ej: '.'")
    ap.add_argument("--decimal", default=".", help="Separador decimal (default '.'). Ej: ','")
    ap.add_argument("--format_cols", default=None, help="Columnas (1-index) a formatear, ej: '2,3,4'. Default: todas menos la 1.")
    args = ap.parse_args()

    path = Path(args.file)
    text = path.read_text(encoding="utf-8", errors="replace")
    raw_lines = [ln for ln in text.splitlines() if ln.strip() != ""]

    if not raw_lines:
        raise SystemExit("El archivo no tiene líneas con contenido.")

    sep = args.sep
    if sep is None:
        sep = detect_sep(raw_lines[0])
    # permitir que el usuario pase '\t'
    if sep == r"\t":
        sep = "\t"

    cells = [split_line(ln, sep) for ln in raw_lines]
    table = normalize_table(cells, args.rows, args.cols)

    if args.format_numbers:
        if args.format_cols:
            cols_to_fmt = {int(c.strip()) - 1 for c in args.format_cols.split(",") if c.strip()}
        else:
            cols_to_fmt = set(range(1, args.cols))  # por defecto: todas menos la primera

        for r in range(len(table)):
            for c in range(len(table[r])):
                if c in cols_to_fmt:
                    tok = table[r][c]
                    if is_number_token(tok):
                        table[r][c] = format_number_str(tok, args.precision, args.thousands, args.decimal)


    latex = to_latex_tabular(
        table=table,
        header=args.header,
        align=args.align,
        booktabs=args.booktabs,
        caption=args.caption,
        label=args.label
    )

    print(latex)

if __name__ == "__main__":
    main()
