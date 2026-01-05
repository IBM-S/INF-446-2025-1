#!/bin/bash

dirSolver="../solver_moead"
dirInstances="../datos/inst"
dirhv="../material/hv-1.3-src"

dirOutput="../datos/res/raw_moead"

# Máximo de evaluaciones totales
evaluaciones=100000

type=drp
variant=relocation

# Inicialización de variables
pop=0
neighborPct=0

mut=0
cross=0

mutType=0
crossType=0

op1=0
bitprob=0

mutPctDelete=0
mutPctSwap=0

initTypeRelocation=0
probMoveRelocation=0
splitPctRelocation=0


instance=""
execution_params=()

# Verificar que se proporcionen argumentos
if [ $# -lt 1 ]; then
    echo "Error: se requiere al menos la instancia como argumento."
    exit 1
fi

# El primer argumento es la instancia
instance=$1
seed=$5
shift 5

instanceName="${instance%.*}"

# Procesar los argumentos restantes
while [ $# -gt 0 ]; do
    flag="$1"
    
    # Verificar si el argumento actual es un flag (-pm, -pc, -p, -s, etc.)
    case "$flag" in
        -type) type="$2"; shift 2 ;;
        -variant) variant="$2"; shift 2 ;;

        -pop) pop="$2"; shift 2 ;;
        -neighborPct) neighborPct="$2"; shift 2 ;;

        -mut) mut="$2"; shift 2 ;;
        -cross) cross="$2"; shift 2 ;;

        -mutType) mutType="$2"; shift 2 ;;
        -crossType) crossType="$2"; shift 2 ;;

        -op1) op1="$2"; shift 2 ;;
        -bitprob) bitprob="$2"; shift 2 ;;

        -mutPctDelete) mutPctDelete="$2"; shift 2 ;;
        -mutPctSwap) mutPctSwap="$2"; shift 2 ;;

        -initTypeRelocation) initTypeRelocation="$2"; shift 2 ;;
        -probMoveRelocation) probMoveRelocation="$2"; shift 2 ;;
        -splitPctRelocation) splitPctRelocation="$2"; shift 2 ;;
        *)
            # Si el argumento es numérico o una cadena vacía, lo añadimos a la lista de parámetros de ejecución
            if [[ "$flag" =~ ^[0-9]+(\.[0-9]+)?$ ]] || [ "$flag" = "" ]; then
                execution_params+=("$flag")
                shift
            else
                echo "Unrecognized flag or argument: $flag"
                exit 1
            fi
            ;;
    esac
done

# Calcular mi, número de objetivos y parámetros
no=2 # número de objetivos
params="-type ${type} -variant ${variant} -neval ${evaluaciones} -pop ${pop} -neighborPct ${neighborPct} -mut ${mut} -cross ${cross} -mutType ${mutType} -crossType ${crossType} -op1 ${op1} -bitprob ${bitprob} -mutPctDelete ${mutPctDelete} -mutPctSwap ${mutPctSwap} -initTypeRelocation ${initTypeRelocation} -probMoveRelocation ${probMoveRelocation} -splitPctRelocation ${splitPctRelocation} "
echo "Parámetros: ${params}"

screen="salida_consola.txt"
screen2="salida_hv.txt"
archivo_resultados="of.out"

# Borrar archivo de salida anterior
rm -rf ${screen} ${screen2} ${archivo_resultados}

# Ejecutar NSGA2
cmd="./${dirSolver}/MOEAD -inst ${dirInstances}/${instance} -seed ${seed} ${params}"

echo "Ejecutando: $cmd"
${cmd} > ${screen}

archivo_generado="${dirOutput}/${type}/${instanceName}/last_gen_${instanceName}".dat

if [ ! -f "$archivo_generado" ]; then
    echo "Error: No se encontro el archivo de resultados: $archivo_generado"
    echo "Result for ParamILS: SAT, 0, 1000000, 0 , ${seed}"
    exit 1
fi

echo "Archivo encontrado. Copiando para procesar..."

cp "$archivo_generado" of.out

# 1. Extraer solo columnas 1 y 2 (quita IDs y basura)
awk '{print $1, $2}' "$archivo_generado" > temp_cols.out

# 2. Eliminar duplicados exactos (sort -u) y guardar en of.out
sort -u temp_cols.out > of.out

# Borrar temporal
rm temp_cols.out


# Buscar óptimo en archivo
exec<"optimos.txt"
# nombreinstancia hv pr1 pr2
while read line; do
    set -- $line
    name=$1
    if [[ ${instance} == ${name} ]]; then
        optimo=$2
        pr1=$3
        pr2=$4
        echo "nombre: ${name}, optimo: ${optimo}, pr1: ${pr1}, pr2: ${pr2}"
    fi
done

# Calcular hv y guardar en quality
echo ${pr1}
echo ${pr2}
factor_pr1=1
factor_pr2=1
pr1=$(awk "BEGIN {printf \"%.6f\",${pr1}*${factor_pr1}}" | sed 's/,/./')
pr2=$(awk "BEGIN {printf \"%.6f\",${pr2}*${factor_pr2}}" | sed 's/,/./')
echo ${pr1}
echo ${pr2}

echo "./${dirhv}/hv -r \"${pr1} ${pr2}\" of.out > ${screen2}"
./${dirhv}/hv -r "${pr1} ${pr2}" of.out > ${screen2}

hv=$(tail -1 ${screen2})
gap=$(awk "BEGIN {printf \"%.4f\",100.00*(${optimo}-${hv})/${optimo}}")
runlength=$(echo ${gap} | sed 's/,/./')
# Para el caso mas grande, probarlo solo, solo minimizar el HV.

solved="SAT"
runtime=0
best_sol=0

echo "Result for ParamILS: ${solved}, ${runtime}, ${runlength}, ${best_sol}, ${seed}"
