
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

AMPL_EXECUTABLE="./../../ampl.linux-intel64/ampl"

MODEL_FILE="mo_relocation_model_simple.mod"
RUN_FILE="mo_drp_relocation_simple.run"
CONFIG_FILE="conf_execution.dat" 

PROBLEM_TYPE="drp"

INSTANCES_DIR="${BASE_DIR}/datos/inst"
RESULTS_DIR="${BASE_DIR}/datos/res/raw_ampl/${PROBLEM_TYPE}"

NUM_RUNS=10

declare -a INSTANCE_ORDER=(
    "drp_657_STATEN_ISLAND.dat"
    "drp_2151_BRONX.dat"
    "drp_2885_QUEENS.dat"
    "drp_3442_BROOKLYN.dat"
    "drp_4432_MANHATTAN.dat"
)

# ================= INICIO DEL PROCESO =================
echo "---------------------------------------------------------"
echo " INICIANDO EXPERIMENTOS AMPL -TIPO: ${PROBLEM_TYPE}"
echo " Directorio Base: ${BASE_DIR}"
echo " Resultados en:   ${RESULTS_DIR}"
echo " Total Runs por instancia: ${NUM_RUNS}"
echo "---------------------------------------------------------"

mkdir -p ${RESULTS_DIR}

for instanceFile in ${INSTANCE_ORDER[@]}; do

    fullInstancePath="${INSTANCES_DIR}/${instanceFile}"

    if [ ! -f "${fullInstancePath}" ]; then
        echo "¡Advertencia! Archivo de instancia no encontrado: ${fullInstancePath}. Saltando..."
        continue
    fi

    instanceName=$(basename "$instanceFile" .dat)

    echo "================================================="
    echo "Procesando instancia: ${instanceFile} (${NUM_RUNS} veces)"
    echo "================================================="

    instanceResDir="${RESULTS_DIR}/${instanceName}"
    mkdir -p "${instanceResDir}"

    instanceLogFile="${instanceResDir}/execution_${instanceName}_summary.log"

    # Si existe el archivo de resumen anterior, LO BORRAMOS.
    if [ -f "${instanceLogFile}" ]; then
        # echo "   [Info] Borrando resumen anterior..."
        rm "${instanceLogFile}"
    fi

    # Creamos el archivo nuevo con el encabezado CSV
    echo "Run,Time_s" > "${instanceLogFile}"

    for (( run=1; run <=${NUM_RUNS}; run++)); do
        echo "  Ejecución ${run}/${NUM_RUNS} para la instancia ${instanceFile}..."
        startTime="$(date +%s.%N)"

        outputDir="${instanceResDir}/run_${run}"

        if [ -d "${outputDir}" ]; then
            rm -rf "${outputDir}"
        fi
        mkdir -p "${outputDir}"

        fullLogFile="${outputDir}/ampl_log_full.txt"
        paretoFile="${outputDir}/pareto_front.txt"

        ${AMPL_EXECUTABLE} <<EOF > "${fullLogFile}"
        reset;
        model ${MODEL_FILE};
        data "${fullInstancePath}";
        data "${CONFIG_FILE}";
        
        include "${RUN_FILE}";
EOF

        endTime="$(date +%s.%N)"
        duration=$(echo "$endTime - $startTime" | bc)

        paretoFile="$outputDir/pareto_front.txt"
        grep -A 999 "F1(Coverage) F2(Cost)" "${fullLogFile}" | tail -n +3 > "${paretoFile}"

        echo "${run},${duration}" >> ${instanceLogFile}
        echo "Completado en ${duration}s. Resultados guardados en ${outputDir}"

    done
    echo "Instancia ${instanceFile} procesada."
done

echo "--- Todas las instancias han sido procesadas. ---"