import random

# Parámetros de entrada
instancias = [
    ("SJC324-3.dat", 324)
]

num_semillas = 10  # Cuántas semillas generar por instancia
semilla_min = 1
semilla_max = 1000

output_file = "ejecuciones_v2.txt"

# Generar archivo
with open(output_file, "w") as f:
    for instancia, n_vars in instancias:
        semillas = random.sample(range(semilla_min, semilla_max), num_semillas)
        for seed in semillas:
            linea = f"./MOEAD {instancia} {seed} {n_vars}\n"
            f.write(linea)

print(f"Archivo generado: {output_file}")
