#!/bin/bash
export LC_NUMERIC=C

# ================= CONFIGURACIÓN =================
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROYECTO_ROOT="${BASE_DIR}/.."

DIR_AMPL="${PROYECTO_ROOT}/datos/res/raw_ampl"
DIR_MOEAD="${PROYECTO_ROOT}/datos/res/raw_moead"
DIR_ANALISIS="${PROYECTO_ROOT}/datos/res/analisis"
HV_EXEC="${PROYECTO_ROOT}/material/hv-1.3-src/hv"

TIPO="cam"
INSTANCIA_TARGET=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --instancia) INSTANCIA_TARGET="$2"; shift ;;
        --tipo) TIPO="$2"; shift ;;
    esac
    shift
done

# AWK: Limpiar números
AWK_CLEAN='
{
  n=0
  for(i=1;i<=NF;i++){
    if($i ~ /^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/){
      a[++n]=$i
      if(n==2){ print a[1], a[2]; break }
    }
  }
}'


# AWK: Calcular Máximos
AWK_MAX='
BEGIN {mx=-1e30; my=-1e30; found=0}
{ if($1>mx) mx=$1; if($2>my) my=$2; found=1 }
END { if(found) print mx, my; else print "NaN NaN" }'

# AWK: Filtrar No Dominados
AWK_FILTER_ND='
{ x[NR]=$1; y[NR]=$2; count++ }
END {
    for(i=1; i<=count; i++) {
        dom=0
        for(j=1; j<=count; j++) {
            if(i==j) continue;
            if(x[j]<=x[i] && y[j]<=y[i] && (x[j]<x[i] || y[j]<y[i])) { dom=1; break; }
        }
        if(!dom) { k=x[i]","y[i]; if(!s[k]++) print x[i], y[i] }
    }
}'

# ================= PROCESO =================

folders_ampl=$(ls "${DIR_AMPL}/${TIPO}" 2>/dev/null)
folders_moead=$(ls "${DIR_MOEAD}/${TIPO}" 2>/dev/null)
INSTANCIAS=$(echo -e "${folders_ampl}\n${folders_moead}" | sort | uniq | grep -v "^$")

echo "========================================"
echo " ANALIZANDO: ${TIPO^^}"
echo "========================================"

for inst in $INSTANCIAS; do
    if [ ! -z "$INSTANCIA_TARGET" ] && [ "$inst" != "$INSTANCIA_TARGET" ]; then continue; fi

    echo -e "\n>>> Procesando: ${inst}"
    OUT_DIR="${DIR_ANALISIS}/${TIPO}/${inst}"
    mkdir -p "${OUT_DIR}"
    
    # ---------------------------------------------------------
    # 1. PUNTOS MÁXIMOS (NADIR)
    # ---------------------------------------------------------
    echo "  [1] Análisis de Puntos Extremos"
    tmp_max="${OUT_DIR}/tmp_max.dat"
    
    # AMPL
    path_ampl="${DIR_AMPL}/${TIPO}/${inst}"
    max_ax="NaN"; max_ay="NaN"
    if [ -d "$path_ampl" ]; then
        cat "${path_ampl}"/run_*/pareto_front.txt 2>/dev/null | awk "$AWK_CLEAN" > "$tmp_max"
        read max_ax max_ay <<< $(awk "$AWK_MAX" "$tmp_max")
    fi
    echo "      -> AMPL Max : F1=$max_ax, F2=$max_ay"

    # MOEAD
    path_moead="${DIR_MOEAD}/${TIPO}/${inst}"
    max_mx="NaN"; max_my="NaN"

    tmp_moead="${OUT_DIR}/tmp_moead_max.dat"   # <-- definirlo

    if [ -d "$path_moead" ]; then
        cat "${path_moead}"/run_*/last_gen_"${inst}".dat 2>/dev/null \
            | awk "$AWK_CLEAN" > "$tmp_moead"

        read max_mx max_my <<< $(awk "$AWK_MAX" "$tmp_moead")   # <-- usar tmp_moead
    fi

    echo "      -> MOEAD Max: F1=$max_mx, F2=$max_my"


    # CALCULO GLOBAL
    echo "$max_ax $max_ay" > "$tmp_max"
    echo "$max_mx $max_my" >> "$tmp_max"
    
    read ref_x ref_y <<< $(awk '
        BEGIN {mx=-1e30; my=-1e30; f=0}
        {
            if($1!="NaN" && $2!="NaN") {
                if($1>mx) mx=$1; if($2>my) my=$2; f=1
            }
        }
        END {
            if(f) {
                rx = mx + (mx!=0 ? ((mx<0)?-mx:mx)*0.01 : 0.1);
                ry = my + (my!=0 ? ((my<0)?-my:my)*0.01 : 0.1);
                printf "%.10f %.10f\n", rx, ry
            } else print "NaN NaN"
        }' "$tmp_max")

    if [ "$ref_x" == "NaN" ]; then echo "      [!] Sin datos válidos."; continue; fi

    echo "      -> PUNTO REF: ($ref_x, $ref_y)"
    echo "$ref_x $ref_y" > "${OUT_DIR}/reference_point.txt"

    # ---------------------------------------------------------
    # 2. MÉTRICAS POR RUN
    # ---------------------------------------------------------
    echo -e "\n  [2] Calculando Métricas por Run"
    csv_out="${OUT_DIR}/final_summary.csv"
    echo "metodo,run,time_ejec,hv,time_hv,nd_points" > "$csv_out"
    
    printf "%-10s %-5s %-15s %-15s %-15s\n" "Metodo" "Run" "Time(Ejec)" "HV" "Time(HV)"
    echo "-----------------------------------------------------------------"

    for metodo in "AMPL" "MOEAD"; do
        base_path=""
        if [ "$metodo" == "AMPL" ]; then base_path="$path_ampl"; else base_path="$path_moead"; fi
        if [ ! -d "$base_path" ]; then continue; fi

        t_log=$(find "$base_path" -maxdepth 1 -name "execution*summary.*" | head -n 1)

        for run_dir in $(ls -d "${base_path}"/run_* 2>/dev/null | sort -V); do
            run_id=$(basename "$run_dir" | cut -d'_' -f2)
            
            # Tiempo Ejecución
            t_exec="NaN"
            if [ -f "$t_log" ]; then
                col=2
                head=$(head -n 1 "$t_log")
                if [[ "$head" == *"Seed"* ]]; then col=3; fi
                val=$(grep "^${run_id}," "$t_log" | cut -d',' -f$col)
                if [ ! -z "$val" ]; then t_exec=$val; fi
            fi

            # HV
            pf_file="${run_dir}/pareto_front.txt"
            if [ -f "$pf_file" ]; then
                tmp_run="${OUT_DIR}/tmp_run.dat"
                awk "$AWK_CLEAN" "$pf_file" | awk "$AWK_FILTER_ND" > "$tmp_run"
                
                pts=$(wc -l < "$tmp_run")
                if [ "$pts" -gt 0 ]; then
                    ts=$(date +%s.%N)
                    hv_val=$(${HV_EXEC} -r "$ref_x $ref_y" "$tmp_run")
                    te=$(date +%s.%N)
                    t_hv=$(echo "$te - $ts" | bc -l)
                else
                    hv_val="0.0"; t_hv="0.0"
                fi
                
                if [[ $t_exec != "NaN" ]]; then p_exec=$(printf "%.4f" $t_exec); else p_exec="-"; fi
                p_hv=$(printf "%.4f" $hv_val)
                p_thv=$(printf "%.6f" $t_hv)

                printf "%-10s %-5s %-15s %-15s %-15s\n" "$metodo" "$run_id" "$p_exec" "$p_hv" "$p_thv"
                echo "${metodo},${run_id},${t_exec},${hv_val},${t_hv},${pts}" >> "$csv_out"
            fi
        done
    done
    echo "-----------------------------------------------------------------"

    # ---------------------------------------------------------
    # 3. BEST FRONTS & GUARDADO CSV
    # ---------------------------------------------------------
    echo -e "\n  [3] BEST FRONTS (Frentes Unificados)"
    echo "-----------------------------------------------------------------"
    printf "%-10s %-15s %-15s %-15s\n" "Metodo" "Puntos ND" "HV Total" "Time(HV)"
    echo "-----------------------------------------------------------------"
    
    # CSV para Best Fronts Metrics
    best_csv="${OUT_DIR}/best_fronts_metrics.csv"
    echo "metodo,nd_points,hv_total,time_hv" > "$best_csv"

    # Función helper
    calc_best() {
        m=$1; f=$2
        if [ -f "$f" ]; then
            pts=$(wc -l < "$f")
            if [ "$pts" -gt 0 ]; then
                ts=$(date +%s.%N)
                hv=$(${HV_EXEC} -r "$ref_x $ref_y" "$f")
                te=$(date +%s.%N)
                thv=$(echo "$te - $ts" | bc -l)
                
                printf "%-10s %-15s %-15.4f %-15.6f\n" "$m" "$pts" "$hv" "$thv"
                echo "${m},${pts},${hv},${thv}" >> "$best_csv"
            else
                echo "${m},0,0.0,0.0" >> "$best_csv"
                printf "%-10s %-15s %-15s %-15s\n" "$m" "0" "0.0" "-"
            fi
        else
            echo "${m},0,0.0,0.0" >> "$best_csv"
            printf "%-10s %-15s %-15s %-15s\n" "$m" "-" "-" "-"
        fi
    }

    # AMPL
    if [ -d "$path_ampl" ]; then
        cat "${path_ampl}"/run_*/pareto_front.txt 2>/dev/null | awk "$AWK_CLEAN" | awk "$AWK_FILTER_ND" > "${OUT_DIR}/best_front_ampl.txt"
        calc_best "AMPL" "${OUT_DIR}/best_front_ampl.txt"
    fi

    # MOEAD
    if [ -d "$path_moead" ]; then
        cat "${path_moead}"/run_*/pareto_front.txt 2>/dev/null | awk "$AWK_CLEAN" | awk "$AWK_FILTER_ND" > "${OUT_DIR}/best_front_moead.txt"
        calc_best "MOEAD" "${OUT_DIR}/best_front_moead.txt"
    fi
    echo "-----------------------------------------------------------------"
    echo "  -> CSV Detallado: ${csv_out}"
    echo "  -> CSV Best Fronts: ${best_csv}"

    rm -f "$tmp_max" "$tmp_moead" "${OUT_DIR}/tmp_run.dat"
done