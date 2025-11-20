import random

def agregar_probabilidades(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()

    new_lines = []
    in_coord_section = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("param : coordx coordy flag :="):
            in_coord_section = True
            new_lines.append("param : coordx coordy flag prob_ohca :=\n")
            continue

        if in_coord_section:
            if stripped == ";":
                in_coord_section = False
                new_lines.append(";\n")
                continue

            parts = stripped.split()
            if len(parts) == 4:
                idx, x, y, flag = parts
                prob = round(random.uniform(0.1, 1.0), 2)
                new_line = f"{idx} {x} {y} {flag} {prob}\n"
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(output_file, 'w') as f:
        f.writelines(new_lines)

    print(f"✅ Archivo generado correctamente con probabilidades: {output_file}")

# Ejecutar con los archivos que desees
agregar_probabilidades("DRP.dat", "DRP_con_probs.dat")
