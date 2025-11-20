import os 
import time
import subprocess


MODEL_FILE = "mo_location_model.mod"
RUN_FILE_CLEAN = "solve_pareto_location.run"
INSTANCES_DIR = "./casos_dats_prob/"
RESULTS_DIR = "./results_ampl/"
LOG_FILE = "execution_time__model_location.log"

print("Iniciando la ejecución de modelos AMPL...")

# Crear el directorio principal de resultados y el archivo de log
os.makedirs(RESULTS_DIR, exist_ok=True)
with open(LOG_FILE, 'w') as f:
    f.write("--- Log de Ejecución del Modelo de Localización ---\n")

# Encontrar todas las instancias .dat en el directorio
try:
    instance_files = [f for f in os.listdir(INSTANCES_DIR) if f.endswith('.dat')]
except FileNotFoundError:
    print(f"Error: La carpeta de instancias '{INSTANCES_DIR}' no existe.")
    exit()

# Iterar sobre cada archivo de instancia
for instance_file in instance_files:
    start_time = time.time()
    
    # Crear el nombre de la instancia sin la extensión .dat
    instance_name = os.path.splitext(instance_file)[0]
    
    # Crear la carpeta de resultados para esta instancia
    instance_result_dir = os.path.join(RESULTS_DIR, instance_name)
    os.makedirs(instance_result_dir, exist_ok=True)
    
    # El archivo de salida será el .csv con la frontera de Pareto
    output_file = os.path.join(instance_result_dir, "pareto_front.csv")

    print(f"Procesando {instance_file}...")

    # Crear el bloque de comandos completo que se pasará a AMPL
    ampl_commands = f"""
    reset;
    model {MODEL_FILE};
    data {os.path.join(INSTANCES_DIR, instance_file)};
    include {RUN_FILE_CLEAN};
    """

    # Ejecutar AMPL como un subproceso y redirigir su salida al archivo
    with open(output_file, "w") as out_f:
        subprocess.run(
            ["../../../../../AMPL/ampl.exe"],                   # El comando para ejecutar AMPL
            input=ampl_commands.encode(), # Pasa los comandos a AMPL
            stdout=out_f,               # Guarda la salida estándar en el archivo
            stderr=subprocess.STDOUT    # Guarda también los errores en el mismo archivo
        )

    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"Completado en {total_time:.2f}s. Resultados guardados en {output_file}")
    
    # Guardar el tiempo en el archivo de log
    log_message = f"Instancia: {instance_file}, Tiempo (s): {total_time:.6f}\n"
    with open(LOG_FILE, 'a') as log_f:
        log_f.write(log_message)

print("\n--- Todas las instancias han sido procesadas. ---")