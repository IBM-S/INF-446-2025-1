
AMPL_EXECUTABLE="../../../../../AMPL/ampl.exe"

MODEL_FILE="mo_location_model.mod"
RUN_FILE="mo_drp_location.run"
CONFIG_FILE="conf_execution.dat" 

INSTANCES_DIR="./casos_dats_prob"
RESULTS_DIR="./results_ampl"

NUM_RUNS=2

echo "Iniciando la ejecución de todas las instancias AMPL..."

mkdir -p ${RESULTS_DIR}

for fullInstancePath in ${INSTANCES_DIR}/*.dat; do

    instanceFile=$(basename "${fullInstancePath}")

    echo "================================================="
    echo "Procesando instancia: ${instanceFile} (${NUM_RUNS} veces)"
    echo "================================================="

    instanceLogFile="${RESULTS_DIR}/${instanceFile}/${instanceFile}_execution.log"
    mkdir -p "${RESULTS_DIR}/${instanceFile}"
    echo "--- Log de Ejecución para ${instanceFile} ---" > "${instanceLogFile}"
    echo "Run,Tiempo(s)" >> "${instanceLogFile}"


    for (( run=1; run <=${NUM_RUNS}; run++)); do
        echo "  Ejecución ${run} de ${NUM_RUNS} para la instancia ${instanceFile}..."
        startTime="$(date +%s.%N)"

        outputDir="${RESULTS_DIR}/${instanceFile}/run_${run}"
        mkdir -p "${outputDir}"

        fullLogFile="$outputDir/fulllog.txt"

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