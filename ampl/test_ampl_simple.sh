#!/bin/bash

# --- CONFIGURACIÓN RÁPIDA ---
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AMPL_EXE="./../../ampl.linux-intel64/ampl"
MODEL="mo_location_model.mod"
RUN_FILE="mo_drp_location.run"
DATA_FILE="conf_execution.dat"

# Instancia de prueba
INSTANCE="cam_1390_MILPA_ALTA.dat"
FULL_INST_PATH="${BASE_DIR}/datos/inst/${INSTANCE}"
RESULT_DIR="${BASE_DIR}/datos/res/raw_ampl/cam/TEST_$(basename ${INSTANCE} .dat)"

echo ">>> INICIANDO TEST AMPL (2 Runs) para: $INSTANCE"
echo ">>> Destino: $RESULT_DIR"

# 1. Preparar carpeta y log resumen
mkdir -p "${RESULT_DIR}"
echo "Run,Time_s" > "${RESULT_DIR}/execution_summary.csv"

# 2. Bucle de 2 corridas
for (( run=1; run <=2; run++)); do
    echo "  > Ejecutando Run $run..."
    
    # Carpeta específica del run
    runDir="${RESULT_DIR}/run_${run}"
    if [ -d "${runDir}" ]; then rm -rf "${runDir}"; fi
    mkdir -p "${runDir}"

    # Archivos de salida
    log="${runDir}/ampl_log.txt"
    pareto="${runDir}/pareto_front.txt"

    startT=$(date +%s.%N)

    # Ejecutar AMPL
    ${AMPL_EXE} <<EOF > "${log}"
    reset;
    model ${MODEL};
    data "${FULL_INST_PATH}";
    data "${DATA_FILE}";
    option gurobi_options 'timelim=10'; # Limite corto para test
    include "${RUN_FILE}";
EOF

    endT=$(date +%s.%N)
    duration=$(echo "$endT - $startT" | bc)

    # Extraer Pareto
    grep -A 999 "F1(Coverage) F2(Cost)" "${log}" | \
    grep -E "^[[:space:]]*[0-9.-]+" | \
    awk '{print $1, $2}' > "${pareto}"

    # Guardar resumen
    echo "${run},${duration}" >> "${RESULT_DIR}/execution_summary.csv"
    
    count=$(wc -l < "${pareto}")
    echo "    [OK] Terminado en ${duration}s. Puntos: $count"
done

echo ">>> TEST AMPL FINALIZADO."