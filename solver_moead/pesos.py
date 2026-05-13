"""
Genera vectores de peso 2D uniformemente espaciados para MOEA/D,
aplicando epsilon en los extremos en lugar de 0 y 1 absolutos.

Basado en gen_weightRecursive.m (H=100 -> 101 vectores para 2 objetivos)
y en la lógica de ampl/sigma.py.

Salida: W2D_100_modificado.dat en SETTINGS/weightvectors/
"""

import os

def gen_weight_modificado(H=749, epsilon=0.001, output_dir=None):
    if output_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "SETTINGS", "weightvectors")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "W2D_749_modificado.dat")

    vectores = []
    num_puntos = H + 1  # 750 vectores para H=749

    for k in range(num_puntos):
        w1 = k / H
        w2 = 1.0 - w1

        if k == 0:
            w1_final = epsilon
            w2_final = 1.0 - epsilon
        elif k == H:
            w1_final = 1.0 - epsilon
            w2_final = epsilon
        else:
            w1_final = w1
            w2_final = w2

        vectores.append((w1_final, w2_final))

    with open(output_path, "w") as f:
        for w1, w2 in vectores:
            f.write(f"{w1:.5f}  {w2:.5f}\n")

    print(f"Generados {len(vectores)} vectores -> '{output_path}'")
    print(f"Primer vector : {vectores[0][0]:.5f}  {vectores[0][1]:.5f}")
    print(f"Último vector : {vectores[-1][0]:.5f}  {vectores[-1][1]:.5f}")
    return output_path


if __name__ == "__main__":
    gen_weight_modificado()