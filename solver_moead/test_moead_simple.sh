#!/bin/bash

# --- CONFIGURACIÓN RÁPIDA ---
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
MOEAD_EXE="./MOEAD"

# Instancia de prueba
INSTANCE="cam_1390_MILPA_ALTA.dat"
FULL_INST_PATH="${BASE_DIR}/../datos/inst/${INSTANCE}"

# --- CORRECCIÓN: Apuntamos a la carpeta REAL que usa el C++ ---
INSTANCE_NAME=$(basename "${INSTANCE}" .dat)
RESULT_DIR="${BASE_DIR}/../datos/res/raw_moead/cam/${INSTANCE_NAME}"

echo ">>> INICIANDO TEST MOEA/D (2 Runs) para: $INSTANCE"
echo ">>> Los resultados quedarán en subcarpetas 'TEST_run_X' dentro de:"
echo ">>> $RESULT_DIR"

# 1. Preparar carpeta y log resumen
mkdir -p "${RESULT_DIR}"
# Usamos un log especifico de test para no ensuciar el real
echo "Run,Seed,Time_s" > "${RESULT_DIR}/execution_summary_TEST.csv"

# 2. Bucle de 2 corridas
for (( run=1; run <=2; run++)); do
    seed=$((500 + run)) 
    echo "  > Ejecutando Run $run (Seed: $seed)..."

    # --- CORRECCIÓN: Usamos un nombre de subcarpeta distintivo ---
    subFolder="TEST_run_${run}"
    
    # Ruta absoluta para gestión de Bash
    runDir="${RESULT_DIR}/${subFolder}"
    
    # Limpieza profunda
    if [ -d "${runDir}" ]; then rm -rf "${runDir}"; fi
    mkdir -p "${runDir}"

    log="${runDir}/console_output.txt"
    startT=$(date +%s.%N)

    # Ejecutar MOEA/D 
    # Pasamos solo el nombre de la subcarpeta (-outDir "TEST_run_1")
    ${MOEAD_EXE} \
        -inst "${FULL_INST_PATH}" \
        -seed ${seed} \
        -type "cam" \
        -variant "location" \
        -pop 100 \
        -neighbor 20 \
        -neval 500 \
        -outDir "${subFolder}" \
        > "${log}" 2>&1

    endT=$(date +%s.%N)
    duration=$(echo "$endT - $startT" | bc)

    # Verificar resultados
    lastPOF=$(ls "${runDir}"/POF_*_GEN_*.dat 2>/dev/null | sort -V | tail -n 1)
    if [ -f "${lastPOF}" ]; then
        cp "${lastPOF}" "${runDir}/pareto_front.txt"
        echo "    [OK] Archivo generado en: ${subFolder}"
    else
        echo "    [ERROR] No se generó el archivo POF. Revisa: ${log}"
    fi

    echo "${run},${seed},${duration}" >> "${RESULT_DIR}/execution_summary_TEST.csv"
done

echo ">>> TEST MOEA/D FINALIZADO."