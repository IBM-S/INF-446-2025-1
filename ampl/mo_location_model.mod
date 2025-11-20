/* CONJUNTOS */
param N_total;
set N := 1..N_total;     # Un sitio puede ser un punto de demanda y/o una ubicación candidata.

param cantobj ; # cantidad de objetivos del problema
param cantejc ; # cantidad de ejecuciones para la frontera de pareto

set objetivos :=  {1..cantobj} ; # conjunto de objetivos del problema
set ejecuciones := {1..cantejc} ; # conjunto de ejecuciones para la frontera de pareto

param nombre_instancia symbolic;

/* PARÁMETROS */
# Parámetros de la instancia
param P;               # Presupuesto disponible.
param R;               # Radio de cobertura de un AED.
param c1;              # Costo de instalar un nuevo desfibrilador.
param c2;              # Costo de mover un desfibrilador.
param coordx {N};      # coordenada x
param coordy {N};      # coordenada y
param flag {N};        # 1 si ya existe un AED en el sitio i, 0 si no.
param prob_ohca {N};   # prob de que ocurra un OHCA entre 0.1 y 1.0 en i

# Parámetros calculados
param dist {i in N, j in N} := sqrt((coordx[i] - coordx[j])^2 + (coordy[i] - coordy[j])^2);
set PARES_CUBRIBLES within {N, N} = {i in N, j in N: dist[i,j] <= R}; #<-- ¡Clave para la eficiencia!

# Parámetros para el método multiobjetivo
param g default 0;
param sigma{ejecuciones,objetivos} ; # ponderadores para la frontera de pareto
param betha {objetivos} default 0;
param MV {objetivos} default 999999999;
param PV {objetivos} default -1000;

# ----------------- VARIABLES -----------------
var x {i in N} binary;      #<-- Variable de decisión principal: x[i]=1 si se instala un NUEVO AED en el sitio i.
var z {j in N} binary;      #<-- Variable de estado: z[j]=1 si el sitio de demanda j está cubierto.

# ----------------- OBJETIVOS -----------------
var F {objetivos} >= -1000000; # Vector para almacenar los valores de los objetivos.

# O1: Maximizar cobertura probabilística (formulado para minimizar)
subject to Objetivo_1:
    F[1] = - (sum {j in N} z[j] * prob_ohca[j]);

# O2: Minimizar el costo total de las nuevas instalaciones.
subject to Objetivo_2:
    F[2] = sum {i in N} x[i] * c1;

# Funciones objetivo para AMPL
minimize FO1: F[g]; # Para encontrar los extremos de un solo objetivo (g=1 o g=2)
minimize FO2: sum {i in objetivos} betha[i] *
    ( if (PV[i] - MV[i]) <> 0 then
        (F[i] - MV[i]) / (PV[i] - MV[i])
      else
        0
    );

# ----------------- RESTRICCIONES -----------------

# R1: Un nuevo AED no puede ser instalado donde ya existe uno.
#     flag[i] es 1 si ya hay uno, 0 si no. 1-flag[i] invierte esto.
subject to Restriccion_No_Duplicar {i in N}:
     x[i] <= 1 - flag[i];

# R2: El costo total de las nuevas instalaciones no puede superar el presupuesto.
subject to Restriccion_Presupuesto:
    sum {i in N} x[i] * c1 <= P;

# R3: Un sitio de demanda 'j' está cubierto (z[j]=1) si hay un AED al alcance.
#     Un AED puede ser uno pre-existente (flag[i]=1) o uno nuevo (x[i]=1).
subject to Restriccion_Cobertura {j in N}:
    z[j] <= sum {(i,j) in PARES_CUBRIBLES} (x[i] + flag[i]);

# z[j] debe ser 1 si existe un i que cubre j (ya sea preinstalado o nuevo)
subject to cobertura_LB { (i,j) in PARES_CUBRIBLES }:
    z[j] >= x[i] + flag[i]; 