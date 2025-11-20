/* CONJUNTOS */
set N ; # conjuntos eventos
set obj ; # Objetivos
param nombre_instancia symbolic;


/* PARAMETROS */
param P ; # presupuesto
param R ; # radio
param c1 ; # costo de instalar un desfibrilador
param c2 ; # costo de mover un desfibrilador
param coordx{N} ; # coordenada x
param coordy{N} ; # coordenada y
param flag{N} ; # 1 si exite un defilador instalado en el sitio del evento
param prob_ohca{N} ; # prob de que ocurra un OHCA entre 0.1 y 1.0

param dist {i in N, j in N} := sqrt((coordx[i] - coordx[j])^2 + (coordy[i] - coordy[j])^2) ;

param cantobj :=  2    ; # cantidad de objetivos del problema
set objetivos :=  {1..cantobj} ; # conjunto de objetivos del problema
param g default 1 ;

/* VARIABLES */
var w{N} binary		; # 1 si el desfibrilador se mantiene en el sitio del evento i
var t{N,N} binary 	; # 1 si el desfibrilador del sitio del evento i se desplaza al sitio del evento j
var x{N} binary 	; # 1 si se instala un desfibrilador en el sitio del evento i
var y{N, N} binary	; # 1 si el sitio de evento j se cubre con el desfibrilador del sitio del evento i
var z{N} binary 	; # 1 si el sitio j esta cubierto
var F{objetivos} >=  -1000000  ; # funciones objetivos del problema

/* FUNCION OBJETIVO */
# maximize FO1 : F[1] ;

/* Objetivos */
# MAX cobertura probabilistica
# O1 : F[1] = (sum {j in N} z[j]*prob_ohca[j])*-1 ; 
# MIN costos
# O2: F[2] = sum {j in N} x[j]*c1 + sum {i in N, j in N} t[i,j]*c2 ; 

minimize FO1 : F[g] ;

subject to

 O1 : F[1] = (sum {j in N} z[j]*prob_ohca[j])*-1 ; 
 O2 : F[2] = sum {j in N} x[j]*c1 + sum {i in N, j in N} t[i,j]*c2 ; 

 # normalizar

 /* RESTRICCIONES */
 # un desfibrilador ya instalado en un sitio puede mantenerse ahí o desplazarse a otro sitio cualquiera (solo a un sitio)
 r1 {i in N} : w[i] + sum {j in N} t[i,j] = flag[i] ;

 # se puede intalar un desfibrilador en el sitio de un evento si y solo si (2 razones):
 # 1. si al sitio no se desplazó un desfibrilador
 # 2. si el sitio no tenia un desfibrilador previamente intalado, ya que:
 #	2a. si existia un desfibrilador y se mantuvo, entonces no se puede instalar otro (se asume capacidad para un desfibrilador por sitio)
 #	2b. si existia un desfibrilador y se desplazó, entonces no tiene sentido instalar algo nuevamente, pues solo representa un aumento del costo
 r2 {i in N} : x[i] + sum {k in N} t[k,i] <= 1 - flag[i] ;

 # el costo de los desfibriladores instalados y desplazados no puede superar el presupuesto
 #r3 : sum {i in N} c1*x[i] + sum {i in N, j in N} c2*t[i,j]  <= P ;
 r3 : sum {i in N} c1*x[i] + sum {i in N} c2*(1-w[i])*flag[i] <= P ;

 # un sitio con un desfibrilador puede cubrir a otro solo si existe un desfibrilador (ya sea por instalación, desplazamiento o porque se mantuvo)
 r4 {i in N, j in N} :  y[i,j] <= x[i] + w[i] + sum {k in N} t[k,i] ;

 # un sitio esta cubierto por otro solo si cumple el umbral de distancia
 r5 {i in N, j in N} :  y[i,j]*dist[i,j] <= R ;

 # un sitio esta cubierto si existe almenos un sitio que lo cubra
 r6 {j in N} : z[j] <= sum {i in N} y[i,j] ; 
