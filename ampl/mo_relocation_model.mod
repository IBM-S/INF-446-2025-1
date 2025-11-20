# Modelo_Reubicacion.mod
# Modelo Multiobjetivo para Ubicación y Reubicación Flexible de AEDs.

# ----------------- CONJUNTOS (Igual que antes) -----------------
param N_total;
set N := 1..N_total;
param cantobj :=  2 ;
param cantejc := 11 ;
set objetivos := {1..cantobj};
set ejecuciones := {1..cantejc};

param nombre_instancia symbolic;

# ----------------- PARÁMETROS (Igual que antes, con c2) -----------------
param P;
param R;
param c1;
param c2; #<-- Costo de reubicación, ahora es necesario.
param coordx {N};
param coordy {N};
param flag {N};
param prob_ohca {N};
param dist {i in N, j in N} := sqrt((coordx[i] - coordx[j])^2 + (coordy[i] - coordy[j])^2);
set PARES_CUBRIBLES within {N, N} = {i in N, j in N: dist[i,j] <= R};

# Parámetros multiobjetivo (igual que antes)
param g default 0;
param sigma{ejecuciones,objetivos};
param betha {objetivos} default 0;
param MV {objetivos} default 999999999;
param PV {objetivos} default -1000;

# ----------------- VARIABLES (Reintroducimos w y t) -----------------
var w {N} binary;   # 1 si el desfibrilador pre-existente en i SE MANTIENE.
var t {N,N} binary; # 1 si el desfibrilador de i SE MUEVE a j.
var x {N} binary;   # 1 si se instala un desfibrilador NUEVO en i.
var z {N} binary;   # 1 si el sitio j está cubierto.

# ----------------- OBJETIVOS -----------------
var F {objetivos} >= -1000000;

# O1: Maximizar cobertura probabilística (igual que antes)
subject to Objetivo_1:
    F[1] = - (sum {j in N} z[j] * prob_ohca[j]);

# O2: Minimizar el costo total de instalaciones Y reubicaciones.
#     Esto corresponde a la Ecuación (4) del paper.
subject to Objetivo_2:
    F[2] = (sum {i in N} x[i] * c1) + (sum {i in N} (1 - w[i]) * flag[i] * c2);
    # Explicación:
    # (sum x[i] * c1) -> Costo de todos los AEDs nuevos.
    # (1 - w[i]) * flag[i] -> Es 1 SOLO si había un AED (flag=1) y NO se mantuvo (w=0), es decir, se movió.
    # Se multiplica por c2, el costo de reubicación.

# Funciones objetivo para AMPL (igual que antes)
minimize FO1: F[g];
minimize FO2: sum {i in objetivos} betha[i] * (if (PV[i] - MV[i]) <> 0 then (F[i] - MV[i]) / (PV[i] - MV[i]) else 0);

# ----------------- RESTRICCIONES -----------------

# R1: Un desfibrilador pre-existente (flag=1) o se mantiene (w=1) o se mueve a algún otro sitio (sum t=1).
#     Si no había desfibrilador (flag=0), no se puede ni mantener ni mover.
subject to Restriccion_Gestion_Existentes {i in N}:
    w[i] + sum {j in N} t[i,j] = flag[i];

# R2: Se puede instalar un AED nuevo (x=1) en un sitio i SOLO si:
#     1. No se movió un AED a ese sitio (sum t[k,i]=0).
#     2. No había un AED pre-existente en ese sitio (flag=i=0).
subject to Restriccion_Lugar_Instalacion {i in N}:
    x[i] + sum {k in N} t[k,i] <= 1 - flag[i];

# R3: El presupuesto no debe ser superado. Corresponde a la Ecuación (4).
subject to Restriccion_Presupuesto:
    F[2] <= P;

# R4: Un sitio j está cubierto (z=1) si hay un AED al alcance.
#     Un AED está en 'i' si se mantuvo (w=1), se instaló uno nuevo (x=1) o se movió uno allí (sum t[k,i]=1).
subject to Restriccion_Cobertura {j in N}:
    z[j] <= sum {(i,j) in PARES_CUBRIBLES} (w[i] + x[i] + sum {k in N} t[k,i]);

# R5 (NUEVA): El número total de AEDs al final debe ser al menos el número de AEDs que había al principio.
#            Corresponde a la Ecuación (5) del paper.
param N0 := sum {i in N} flag[i]; # Calculamos el número inicial de AEDs
subject to Restriccion_Conservacion_AEDs:
    sum {i in N} (w[i] + x[i] + sum {k in N} t[k,i]) >= N0;

# z[j] debe ser 1 si existe un i que cubre j (ya sea preinstalado o nuevo)
subject to cobertura_LB { (i,j) in PARES_CUBRIBLES }:
    z[j] >= w[i] + x[i] + sum {k in N} t[k,i];