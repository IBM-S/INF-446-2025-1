# ----------------- CONJUNTOS Y PARÁMETROS -----------------
param N_total;
set N := 1..N_total;
param cantobj :=  2 ;
param cantejc := 11 ;
set objetivos := {1..cantobj};
set ejecuciones := {1..cantejc};

param nombre_instancia symbolic;
param P;
param R;
param c1;
param c2;
param coordx {N};
param coordy {N};
param flag {N};
param prob_ohca {N};

param dist {i in N, j in N} := sqrt((coordx[i] - coordx[j])^2 + (coordy[i] - coordy[j])^2);
set PARES_CUBRIBLES within {N, N} = {i in N, j in N: dist[i,j] <= R};
param N0 := sum {i in N} flag[i]; # Número inicial de AEDs

# Parámetros multiobjetivo
param g default 0;
param sigma{ejecuciones,objetivos};
param betha {objetivos} default 0;
param MV {objetivos} default 999999999;
param PV {objetivos} default -1000;

# ----------------- VARIABLES -----------------
var y {N} binary;   # 1 si al final HAY un AED en la ubicación i.
var x {N} binary;   # 1 si el evento OHCA en el sitio j está cubierto.

# NUEVA VARIABLE AUXILIAR para contar los nuevos AEDs comprados
var N_nuevos integer >= 0;

var F {objetivos} >= -1000000;

# ----------------- OBJETIVOS -----------------
# O1: Maximizar cobertura (sin cambios)
subject to Objetivo_1:
    F[1] = - (sum {j in N} x[j] * prob_ohca[j]);

# O2: Minimizar el costo total (¡AQUÍ ESTÁ EL CAMBIO CLAVE!)
subject to Objetivo_2:
    F[2] = (c1 * N_nuevos)                                # Costo de los AEDs NUEVOS COMPRADOS
         + sum {i in N} ( c2 * flag[i] * (1 - y[i]) );    # Costo de MOVER existentes

# Funciones objetivo para AMPL (sin cambios)
minimize FO1: F[g];
minimize FO2: sum {i in objetivos} betha[i] * (if (PV[i] - MV[i]) <> 0 then (F[i] - MV[i]) / (PV[i] - MV[i]) else 0);

# ----------------- RESTRICCIONES -----------------
# R1: Definir el número de nuevos AEDs comprados.
# N_nuevos debe ser al menos el incremento en el total de AEDs.
subject to Define_Nuevos:
    N_nuevos >= (sum {i in N} y[i]) - N0;

# R2: Restricción de cobertura (sin cambios)
subject to Restriccion_Cobertura {j in N}:
    x[j] <= sum {(i,j) in PARES_CUBRIBLES} y[i];

# R3: Vínculo de cobertura (sin cambios)
subject to cobertura_minima { (i,j) in PARES_CUBRIBLES}:
    x[j] >= y[i];

# R4: Conservación del número de AEDs. Sigue siendo importante.
# Opcional, pero recomendable. Si la quitas, el modelo podría vender AEDs.
subject to Restriccion_Conservacion_AEDs:
    sum {i in N} y[i] >= N0;

# R5: Presupuesto (opcional, si quieres limitarlo ademas de minimizarlo)
subject to Restriccion_Presupuesto:
    F[2] <= P;