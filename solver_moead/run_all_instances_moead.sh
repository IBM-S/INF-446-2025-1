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
NUM_RUNS=10          

# Parámetros Algoritmo
POPULATION=300
NEIGHBOR=10
NEVALS=150000    # Criterio de parada por evaluaciones
MAX_TIME=3600      # Criterio de parada por tiempo (0 = desactivado)
MUTATION=0.5
CROSSOVER=0.7
OP1_PROB=0.5
SAVE=0
MUTTYPE=11
CROSSTYPE=3
MUTPCT=0.2
BITPROB=0.1


# Lista de Instancias
declare -a INSTANCE_ORDER=(
    "cam_1390_MILPA_ALTA.dat"
    "cam_1800_CUAJIMALPA_DE_MORELOS.dat"
    "cam_3205_LA_MAGDALENA_CONTRERAS.dat"
    "cam_7256_TLAHUAC.dat"
    "cam_7408_XOCHIMILCO.dat"
    "cam_9673_AZCAPOTZALCO.dat"
    "cam_11096_IZTACALCO.dat"
    "cam_11410_TLALPAN.dat"
    "cam_11476_BENITO_JUAREZ.dat"
    "cam_12319_COYOACAN.dat"
    "cam_13802_MIGUEL_HIDALGO.dat"
    "cam_14468_VENUSTIANO_CARRANZA.dat"
    "cam_15743_ALVARO_OBREGON.dat"
    "cam_22238_CUAUHTEMOC.dat"
    "cam_24363_GUSTAVO_A._MADERO.dat"
    "cam_40264_IZTAPALAPA.dat"
)

# ================= INICIO =================cd
echo "---------------------------------------------------------"
echo " INICIANDO EXPERIMENTOS MOEA/D - TIPO: ${PROBLEM_TYPE}"
echo " Variantes: ${VARIANT}"
echo " Tiempo Máximo: ${MAX_TIME}s"
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
    summaryLog="${instanceResDir}/execution_${instanceName}_summary.log"
    if [ ! -f "${summaryLog}" ]; then
        echo "Run,Seed,Time_s" > "${summaryLog}"
    fi

    for (( run=1; run <=${NUM_RUNS}; run++)); do
        
        currentSeed=$RANDOM
        
        echo "  > Run ${run}/${NUM_RUNS} (Seed: ${currentSeed})..."
        
        subFolder="run_${run}"

        runDir="${instanceResDir}/${subFolder}"

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
            -save ${SAVE} \
            -mutType ${MUTTYPE} \
            -crossType ${CROSSTYPE} \
            -mutPct ${MUTPCT} \
            -bitprob ${BITPROB} \
            -outDir "${subFolder}" \
            > "${consoleLog}" 2>&1

        endT=$(date +%s.%N)
        duration=$(echo "$endT - $startT" | bc)
        
        # --- CREAR PARETO_FRONT.TXT ---
        # Buscamos el archivo con el número de generación más alto (la última población)
        # sort -V ordena "naturalmente" (Gen_2 va antes que Gen_10)
        lastGenFile="${runDir}"/last_gen_${instanceName}.dat"
        # Copiamos ese archivo como pareto_front.txt para estandarizar con AMPL

        if [ -f "${lastGenFile}" ]; then
            # Extrae SOLO los primeros 2 números de cada línea (F1 y F2), ignorando "- IDs instalados..."
            awk '
            {
            n=0
            for(i=1;i<=NF;i++){
                if($i ~ /^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/){
                a[++n]=$i
                if(n==2){ print a[1], a[2]; break }
                }
            }
            }' "${lastGenFile}" > "${runDir}/pareto_front.txt"
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