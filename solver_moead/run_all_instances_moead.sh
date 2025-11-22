#!/bin/bash

# ================= CONFIGURACIÓN DE RUTAS =================
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
EXECUTABLE="./MOEAD"

# Rutas relativas a TT2
INSTANCES_DIR="${BASE_DIR}/../datos/inst"
RAW_RESULTS_DIR="${BASE_DIR}/../datos/res/raw_moead"

# ================= PARÁMETROS =================
PROBLEM_TYPE="cam"       
VARIANT="location"       
NUM_RUNS=2              

# Parámetros Algoritmo
POPULATION=100
NEIGHBOR=20
NEVALS=100000    # Criterio de parada por evaluaciones
MAX_TIME=0      # Criterio de parada por tiempo (0 = desactivado)
MUTATION=0.05
CROSSOVER=1.0
OP1_PROB=0.5

# Lista de Instancias
declare -a INSTANCE_ORDER=(
    "cam_1390_MILPA_ALTA.dat"
    # Agrega el resto aquí...
)

# ================= INICIO =================
echo "---------------------------------------------------------"
echo " INICIANDO EXPERIMENTOS MOEA/D - TIPO: ${PROBLEM_TYPE}"
echo " Variantes: ${VARIANT}"
echo " Runs por instancia: ${NUM_RUNS}"
echo "---------------------------------------------------------"

for instanceFile in "${INSTANCE_ORDER[@]}"; do

    fullInstancePath="${INSTANCES_DIR}/${instanceFile}"

    if [ ! -f "${fullInstancePath}" ]; then
        echo "[ALERTA] Instancia no encontrada: ${fullInstancePath}. Saltando..."
        continue
    fi

    instanceName=$(basename "${instanceFile}" .dat)

    echo "================================================="
    echo " Procesando: ${instanceName}"
    echo "================================================="

    # Directorio base para esta instancia
    instanceResDir="${RAW_RESULTS_DIR}/${PROBLEM_TYPE}/${instanceName}"
    
    # Crear directorio padre si no existe
    mkdir -p "${instanceResDir}"
    
    # Log resumen
    summaryLog="${instanceResDir}/execution_summary.csv"
    if [ ! -f "${summaryLog}" ]; then
        echo "Run,Seed,Time_s" > "${summaryLog}"
    fi

    for (( run=1; run <=${NUM_RUNS}; run++)); do
        
        currentSeed=$((100 + run))
        
        echo "  > Run ${run}/${NUM_RUNS} (Seed: ${currentSeed})..."
        
        runDir="${instanceResDir}/run_${run}"

        # --- LIMPIEZA DE CORRIDAS ANTERIORES ---
        # Si la carpeta run_X ya existe, la borramos completa para evitar mezclar datos.
        if [ -d "${runDir}" ]; then
            # echo "    [Limpieza] Borrando resultados previos en ${runDir}..."
            rm -rf "${runDir}"
        fi
        # Creamos la carpeta limpia
        mkdir -p "${runDir}"
        # ---------------------------------------

        consoleLog="${runDir}/console_output.txt"

        startT=$(date +%s.%N)

        ${EXECUTABLE} \
            -inst "${fullInstancePath}" \
            -seed ${currentSeed} \
            -type ${PROBLEM_TYPE} \
            -variant ${VARIANT} \
            -pop ${POPULATION} \
            -neighbor ${NEIGHBOR} \
            -neval ${NEVALS} \
            -time ${MAX_TIME} \
            -mut ${MUTATION} \
            -cross ${CROSSOVER} \
            -op1 ${OP1_PROB} \
            > "${consoleLog}" 2>&1

        endT=$(date +%s.%N)
        duration=$(echo "$endT - $startT" | bc)

        # --- MOVER RESULTADOS ---
        # C++ deja los archivos en la carpeta de la instancia (instanceResDir)
        # Los movemos a la carpeta específica del run (runDir)
        mv "${instanceResDir}"/POF_*.dat "${runDir}/" 2>/dev/null
        
        # --- CREAR PARETO_FRONT.TXT ---
        # Buscamos el archivo con el número de generación más alto (la última población)
        # sort -V ordena "naturalmente" (Gen_2 va antes que Gen_10)
        lastGenFile=$(ls "${runDir}"/POF_*_GEN_*.dat 2>/dev/null | sort -V | tail -n 1)

        if [ -f "${lastGenFile}" ]; then
            # Copiamos ese archivo como pareto_front.txt para estandarizar con AMPL
            cp "${lastGenFile}" "${runDir}/pareto_front.txt"
            # echo "    [Info] Generado pareto_front.txt desde $(basename "$lastGenFile")"
        else
            echo "    [Error] No se generaron archivos POF. Revisa console_output.txt"
        fi

        echo "${run},${currentSeed},${duration}" >> "${summaryLog}"

    done
    echo "  [OK] Instancia finalizada."
    echo ""
done

echo "--- Todos los experimentos MOEA/D finalizados. ---"