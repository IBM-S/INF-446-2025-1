import argparse
import os
import random

def parse_txt_file(txt_path):
    with open(txt_path, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]

    cantidad_ohcas, presupuesto, radio = map(int, lines[0].split())

    coordenadas = []
    for line in lines[1:]:
        x, y, flag = map(int, line.split())
        prob = round(random.uniform(0.1, 1.0), 2)
        coordenadas.append((x, y, flag, prob))

    return cantidad_ohcas, presupuesto, radio, coordenadas

def write_dat_file(dat_path, cantidad_ohcas, presupuesto, radio, coordenadas, c1, c2, instance_name):
    with open(dat_path, 'w') as f:
        # Pesos Funciones Objetivo
        f.write("/* PESOS FO */\n")
        f.write("param sigma\n")
        f.write(":	1	2 :=\n")
        f.write("1	0.00001	0.99999\n")
        f.write("2	0.1	0.9\n")
        f.write("3	0.2	0.8\n")
        f.write("4	0.3	0.7\n")
        f.write("5	0.4	0.6\n")
        f.write("6	0.5	0.5\n")
        f.write("7	0.6	0.4\n")
        f.write("8	0.7	0.3\n")
        f.write("9	0.8	0.2\n")
        f.write("10	0.9	0.1\n")
        f.write("11	0.99999	0.00001\n")
        f.write(";\n\n")
        # Conjuntos
        f.write("/* CONJUNTOS */\n")
        f.write("set N := " + ' '.join(map(str, range(1, cantidad_ohcas + 1))) + " ;\n\n")

        # Parámetros
        f.write("/* PARAMETROS */\n")
        f.write(f"param P := {presupuesto} ;\n")
        f.write(f"param R := {radio} ;\n")
        f.write(f"param c1 := {c1} ;\n")
        f.write(f"param c2 := {c2} ;\n")
        f.write(f"param nombre_instancia := \"{instance_name}\" ;\n\n")

        # Coordenadas con probabilidad
        f.write("param : coordx coordy flag prob_ohca :=\n")
        for idx, (x, y, flag, prob) in enumerate(coordenadas, 1):
            f.write(f"{idx} {x} {y} {flag} {prob}\n")
        f.write(";\n")

def main():
    parser = argparse.ArgumentParser(description="Convertir múltiples archivos .txt a .dat")
    parser.add_argument("input_folder", help="Ruta a la carpeta con archivos .txt")
    parser.add_argument("output_folder", help="Ruta para guardar los archivos .dat")
    parser.add_argument("-c1", type=float, default=1, help="Costo c1 (default = 1)")
    parser.add_argument("-c2", type=float, default=0.2, help="Costo c2 (default = 0.2)")

    args = parser.parse_args()

    abs_input = os.path.abspath(args.input_folder)
    abs_output = os.path.abspath(args.output_folder)

    print(f"📂 Leyendo archivos desde: {abs_input}")
    print(f"📁 Archivos .dat se guardarán en: {abs_output}\n")

    os.makedirs(args.output_folder, exist_ok=True)

    for filename in os.listdir(args.input_folder):
        if filename.endswith(".txt"):
            input_path = os.path.join(args.input_folder, filename)
            output_filename = os.path.splitext(filename)[0] + ".dat"
            output_path = os.path.join(args.output_folder, output_filename)

            print(f"🔍 Procesando: {input_path}")
            cantidad_ohcas, presupuesto, radio, coordenadas = parse_txt_file(input_path)
            instance_name = filename
            write_dat_file(output_path, cantidad_ohcas, presupuesto, radio, coordenadas, args.c1, args.c2, instance_name)
            print(f"✅ Generado: {output_path}\n")

if __name__ == "__main__":
    main()
