#/bin/bash

#Directorio con casos de prueba para correr
dirInstances="Instances"
instanceList=$(ls ${dirInstances})

#Final best parameter configuration: a=0.4, p=48, pc=0.3, pi=0.75, pm=0.25, pw=0.3
#Parametros de acuerdo a tuning
p=48
gen=625000
no=2
pc=0.3
pm=0.25
pi=0.75
pw=0.3
a=0.4

params="${p} ${gen} ${no} ${pc} ${pm} ${pi} ${pw} ${a}"

resultsDir=Results
#rm -rf ${resultsDir}
#mkdir ${resultsDir}

dirhv="hv-1.3-src"

#Lista de semillas
seedList="129 137 2356 402 195 6666 429 762 887 843 999 7896 332 34966 287 2226 4636 555 58016 57396"

screen="out.out"

allOut="OUT_ALL"
for instance in ${instanceList}; do
    sumarizedOut="Out_${instance}"
    apf="Apf_${instance}"
    solver="Solver_${instance}"
    #rm -rf ${sumarizedOut} ${apf}

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

    totalHV=0
    for seed in ${seedList}; do
        pf="${resultsDir}/pf_${instance}_${seed}.out"
        #rm -rf ${pf} ${screen}

        #echo "./nsga2r 0.${seed} ${dirInstances}/${instance} ${params} > ${screen}"
        #./nsga2r 0.${seed} ${dirInstances}/${instance} ${params} > ${screen}

        rm -rf ${screen}
        if [ -s ${pf} ]; then
            echo "./${dirhv}/hv -r \"${pr1} ${pr2}\" ${pf} > ${screen}"
            ./${dirhv}/hv -r "${pr1} ${pr2}" ${pf} > ${screen}
            hv=$(tail -1 ${screen})
        fi

        totalHV=$(echo "$totalHV + $hv" |bc)
        ns=$(wc -l ${pf}) # |awk -F' '; '{print $1}';)


        echo "${seed} ${hv} ${ns}" >> ${sumarizedOut}
        #cat quality.out >> ${apf}
        #mv quality.out ${resultsDir}/${pf}
    done

  rm -rf ${screen}
    if [ -s ${solver} ]; then
        echo "./${dirhv}/hv -r \"${pr1} ${pr2}\" ${solver} > ${screen}"
        ./${dirhv}/hv -r "${pr1} ${pr2}" ${solver} > ${screen}
        hvSolver=$(tail -1 ${screen})
    fi

        rm -rf ${screen}
    if [ -s ${apf} ]; then
        echo "./${dirhv}/hv -r \"${pr1} ${pr2}\" ${apf} > ${screen}"
        ./${dirhv}/hv -r "${pr1} ${pr2}" ${apf} > ${screen}
        hvApf=$(tail -1 ${screen})
    fi

    totalHV=$(echo "scale=2; $totalHV / 20" |bc)
    echo "${hvSolver} ${hvApf} ${totalHV}" >> ${sumarizedOut}
    echo "${instance} ${hvSolver} ${hvApf} ${totalHV}" >> ${allOut}
    #mv ${sumarizedOut} ${resultsDir}
done

