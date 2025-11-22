
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

AMPL_EXECUTABLE="./../../ampl.linux-intel64/ampl"

MODEL_FILE="mo_location_model.mod"
RUN_FILE="mo_drp_location.run"
CONFIG_FILE="conf_execution.dat" 

PROBLEM_TYPE="cam"

INSTANCES_DIR="${BASE_DIR}/datos/inst"
RESULTS_DIR="${BASE_DIR}/datos/res/raw_ampl/${PROBLEM_TYPE}"

NUM_RUNS=2

declare -a INSTANCE_ORDER=(
    "cam_1390_MILPA_ALTA.dat"
    #"cam_1800_CUAJIMALPA_DE_MORELOS.dat"
    #"cam_3205_LA_MAGDALENA_CONTRERAS.dat"
    #"cam_7256_TLAHUAC.dat"
    #"cam_7408_XOCHIMILCO.dat"
    #"cam_9673_AZCAPOTZALCO.dat"
    #"cam_11096_IZTACALCO.dat"
    #"cam_11410_TLALPAN.dat"
    #"cam_11476_BENITO_JUAREZ.dat"
    #"cam_12319_COYOACAN.dat"
    #"cam_13802_MIGUEL_HIDALGO.dat"
    #"cam_14468_VENUSTIANO_CARRANZA.dat"
    #"cam_15743_ALVARO_OBREGON.dat"
    #"cam_22238_CUAUHTEMOC.dat"
    #"cam_24363_GUSTAVO_A._MADERO.dat"
    #"cam_40264_IZTAPALAPA.dat"
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

    if [ ! -f "${instanceLogFile}" ]; then
        echo "Run,Tiempo(s)" > "${instanceLogFile}"
    fi

    for (( run=1; run <=${NUM_RUNS}; run++)); do
        echo "  Ejecución ${run}/${NUM_RUNS} para la instancia ${instanceFile}..."
        startTime="$(date +%s.%N)"

        outputDir="${instanceResDir}/run_${run}"
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