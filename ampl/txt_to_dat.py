import argparse
import os

def parse_txt_file(txt_path):
    with open(txt_path, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]

    cantidad_ohcas, presupuesto, radio = map(int, lines[0].split())
    coordenadas = [tuple(map(int, line.split())) for line in lines[1:]]

    return cantidad_ohcas, presupuesto, radio, coordenadas

def write_dat_file(dat_path, cantidad_ohcas, presupuesto, radio, coordenadas, c1, c2, instance_name):
    with open(dat_path, 'w') as f:
        # Conjuntos
        f.write("/* CONJUNTOS */\n")
        f.write("set N := " + ' '.join(map(str, range(1, cantidad_ohcas + 1))) + " ;\n\n")

        # Parámetros
        f.write("/* PARAMETROS */\n")
        f.write(f"param P := {presupuesto} ;\n")
        f.write(f"param R := {radio} ;\n")
        f.write(f"param c1 := {c1} ;\n")
        f.write(f"param c2 := {c2} ;\n")
        f.write(f"param nombre_instancia := \"{instance_name}\" ;\n\n")  # Nueva línea añadida

        # Coordenadas
        f.write("param : coordx coordy flag :=\n")
        for idx, (x, y, flag) in enumerate(coordenadas, 1):
            f.write(f"{idx} {x} {y} {flag}\n")
        f.write(";\n")

def main():
    parser = argparse.ArgumentParser(description="Convertir múltiples archivos .txt a .dat")
    parser.add_argument("input_folder", help="Ruta a la carpeta con archivos .txt")
    parser.add_argument("output_folder", help="Ruta para guardar los archivos .dat")
    parser.add_argument("-c1", type=float, default=1, help="Costo c1 (default = 1)")
    parser.add_argument("-c2", type=float, default=0.2, help="Costo c2 (default = 0.2)")

    args = parser.parse_args()

    # Crear carpeta de salida si no existe
    os.makedirs(args.output_folder, exist_ok=True)

    # Procesar cada archivo .txt de la carpeta
    for filename in os.listdir(args.input_folder):
        if filename.endswith(".txt"):
            input_path = os.path.join(args.input_folder, filename)
            output_filename = os.path.splitext(filename)[0] + ".dat"
            output_path = os.path.join(args.output_folder, output_filename)

            cantidad_ohcas, presupuesto, radio, coordenadas = parse_txt_file(input_path)
            instance_name = filename  # Nombre del archivo .txt
            write_dat_file(output_path, cantidad_ohcas, presupuesto, radio, coordenadas, args.c1, args.c2, instance_name)

            print(f"✅ Convertido: {filename} → {output_filename}")

if __name__ == "__main__":
    main()
