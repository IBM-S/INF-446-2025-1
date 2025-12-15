#!/bin/bash

dirSolver="../solver_moead"
dirInstances="../datos/inst"
dirhv="../material/hv-1.3-src"

dirOutput="../datos/res/raw_moead"

# Máximo de evaluaciones totales
evaluaciones=100000

# Inicialización de variables
pop=0
neighbor=0
mut=0
cross=0
op1=0
ngen=0
descomposition=0

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
        -pop) pop="$2"; shift 2 ;;
        -neighbor) neighbor="$2"; shift 2 ;;
        -mut) mut="$2"; shift 2 ;;
        -cross) cross="$2"; shift 2 ;;
        -op1) op1="$2"; shift 2 ;;
        -ngen) ngen="$2"; shift 2 ;;
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
# gen=$(awk "BEGIN {printf \"%d\",(${ngen}*${pop})}")
no=2 # número de objetivos
params="-neval ${evaluaciones} -pop ${pop} -neighbor ${neighbor} -mut ${mut} -cross ${cross} -op1 ${op1}"
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

archivo_generado="${dirOutput}/cam/${instanceName}/last_gen_${instanceName}".dat

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
pr1=$(awk "BEGIN {printf \"%.1f\",${pr1}*${factor_pr1}}" | sed 's/,/./')
pr2=$(awk "BEGIN {printf \"%.1f\",${pr2}*${factor_pr2}}" | sed 's/,/./')
echo ${pr1}
echo ${pr2}

echo "./${dirhv}/hv -r \"${pr1} ${pr2}\" of.out > ${screen2}"
./${dirhv}/hv -r "${pr1} ${pr2}" of.out > ${screen2}

hv=$(tail -1 ${screen2})
gap=$(awk "BEGIN {printf \"%.2f\",100.00*(${optimo}-${hv})/${optimo}}")
runlength=$(echo ${gap} | sed 's/,/./')
# Para el caso mas grande, probarlo solo, solo minimizar el HV.

solved="SAT"
runtime=0
best_sol=0

echo "Result for ParamILS: ${solved}, ${runtime}, ${runlength}, ${best_sol}, ${seed}"
