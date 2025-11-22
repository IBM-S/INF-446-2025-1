def generar_pesos_ampl(num_puntos=51, epsilon=0.00001):
    """
    Genera el bloque de datos 'param sigma' para AMPL con 'num_puntos' ejecuciones.
    Mantiene el formato de usar epsilon en los extremos en lugar de 0 absoluto.
    """
    print(f"# --- Copia esto en tu archivo .dat o en tu modelo ---")
    print(f"param cantejc := {num_puntos};")
    print("\nparam sigma")
    print(":    1        2 :=")
    
    for i in range(num_puntos):
        # Índice de ejecución (AMPL usa base 1)
        ejecucion = i + 1
        
        # Calcular pesos puros entre 0.0 y 1.0
        # Si solo hay 1 punto, evitar división por cero (caso raro)
        if num_puntos > 1:
            w1 = i / (num_puntos - 1)
        else:
            w1 = 0.5 
            
        w2 = 1.0 - w1
        
        # Aplicar el 'epsilon' en los extremos para replicar tu formato exacto
        # Si prefieres 0 absoluto, puedes comentar este bloque if/elif.
        if i == 0:
            w1_final = epsilon
            w2_final = 1.0 - epsilon
        elif i == num_puntos - 1:
            w1_final = 1.0 - epsilon
            w2_final = epsilon
        else:
            w1_final = w1
            w2_final = w2
            
        # Imprimir con formato alineado
        print(f"{ejecucion:<4} {w1_final:.5f}  {w2_final:.5f}")
        
    print(";")
    print(f"# ----------------------------------------------------")

# =====================================================
# CONFIGURACIÓN: Cambia este número por el que desees
# Recomendado para comparar con MOEA/D: 51 o 101
CANTIDAD_DE_PUNTOS = 11 
# =====================================================

generar_pesos_ampl(CANTIDAD_DE_PUNTOS)