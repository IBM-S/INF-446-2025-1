import numpy as np
import pandas as pd

def  dominates(a: np.array, b: np.array) -> int:
    """
    Function to determine dominance between a and b
    Args:
        a: point
        b: point

    Returns:
    @ 1 If a dominates b
    @ 0 If b dominates a
    @ -1 If they are nondominated
    """

    n = len(a) #Cantidad de funciones objetivo

    #Si los puntos son iguales
    if (a==b).all():
        return -1

    #Si A domina a B
    if sum(a<=b) == n:
        return 1
    #Si B domina a A
    elif sum(b<=a) == n:
        return 0

    #Si no, no son comparables
    return -1


def two_set_coverage(A, B):
    count = 0
    for b in B:
        for a in A:
            #print(a,b)
            if dominates(a,b) == 1:
                count += 1
                break
    return count / len(B)


def filter_dominated(pf):
    res = set()
    for sol1 in pf:
        for sol2 in pf:
            if dominates (sol1, sol2) == 1:
                #print ("sol1 dominates sol2")
                res.add((sol1[0], sol1[1]))
            elif dominates (sol2, sol1) == 1:
                #print ("sol1 dominates sol2")
                res.add((sol2[0], sol2[1]))
            else:
                res.add((sol1[0], sol1[1]))
                res.add((sol2[0], sol2[1]))

    print(sorted(res))


def load_file(my_file):
    f = open(my_file)
    A = []
    while True:
        line = f.readline()
        if line == "":
            return A
        vector = line.split()
        if len(vector) > 1:
            A.append(np.array(list(map(float, vector))))


if __name__ == '__main__':
    instances = [(144,3), (144, 8), (192,4),(216,9),(240,5), (48,1), (72,7),(96,2) ]
    seeds = (129, 137, 195, 2226, 2356, 287, 332, 34966, 402, 429, 4636, 555, 57396, 58016, 6666, 762, 7896, 843, 887, 999)
    AB = []
    BA = []

    for e in instances:
        A = load_file("Apf_bomctop_2_"+str(e[0])+"_"+str(e[1])+".dat")
        #print(A)
        #print(A[0])
        #filter_dominated(A)
        #exit()


        B = load_file("Solver_bomctop_2_"+str(e[0])+"_"+str(e[1])+".dat")
        AB.append(two_set_coverage(A,B))
        BA.append(two_set_coverage(B,A))
        #HV
        #compute maximum values
        #for seed in seeds:
        #    pf=load_file("Results/pf_bomctop_2_"+str(e[0])+"_"+str(e[1])+".dat_"+str(seed)+".out")
        #    print("Results/pf_bomctop_2_"+str(e[0])+"_"+str(e[1])+".dat_"+str(seed)+".out")
        #    filter_dominated(pf)

    df = pd.DataFrame()
    df["I_SC(A,B)"] = AB
    df["I_SC(B,A)"] = BA
    df.style.to_latex("table_tsc.tex")
