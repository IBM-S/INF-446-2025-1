// UtilityTool.h: interface for the CUtilityToolBox class.
//
//////////////////////////////////////////////////////////////////////

#pragma once

#include <vector>
#include <algorithm>
#include <math.h>
#include "GlobalVariable.h"

using namespace std;

#define IM1 2147483563
#define IM2 2147483399
#define AM (1.0 / IM1)
#define IMM1 (IM1 - 1)
#define IA1 40014
#define IA2 40692
#define IQ1 53668
#define IQ2 52774
#define IR1 12211
#define IR2 3791
#define NTAB 32
#define NDIV (1 + IMM1 / NTAB)
#define EPS 1.2e-7
#define RNMX (1.0 - EPS)

class ProblemInstance;
class Node;

class CUtilityToolBox
{
public:
	CUtilityToolBox();
	virtual ~CUtilityToolBox();

public:
	double ScalarizingFunction(vector<double> &y_obj,
							   vector<double> &namda,
							   vector<double> &referencepoint,
							   int s_type);

	void RandomPermutation(vector<int> &permutation, int type);

	vector<int> IndexOfMinimumInt(vector<int> &vec);
	int IndexOfMinimumDouble(vector<double> &vec);

	void Minfastsort(vector<double> &x, vector<int> &idx, int n, int m);
	void Maxfastsort(vector<double> &x, vector<int> &idx, int n, int m);
	void Minfastsort(vector<int> &x, vector<int> &idx, int n, int m);

	void PolynomialMutation(vector<double> &x_var, double m_rate);
	void SimulatedBinaryCrossover(vector<double> &x_var1,
								  vector<double> &x_var2,
								  vector<double> &child);
	void DifferentialEvolution(vector<double> &x_var0,
							   vector<double> &x_var1,
							   vector<double> &x_var2,
							   vector<double> &child,
							   double rate);


							   

	void CruzamientoUniformeModificado(vector<double> &x_var1, vector<double> &x_var2, vector<double> &child);

	void CruzamientoUniformeModificado_sin_reubicacion(vector<double> &x_var1, vector<double> &x_var2, vector<double> &child, ProblemInstance *problemInstance);
	void MutacionModificada_sin_reubicacion(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *problemInstance);
	bool EsBuenCandidato(int idx_candidato, ProblemInstance *instance);

	// 2. Cruzamiento (State of the Art para Binario con Presupuesto)
    void CruzamientoInteligente(const vector<double> &p1, const vector<double> &p2, vector<double> &child, ProblemInstance *instance);
	
	// 1. Bit Flip Normal: cada bit tiene Prob (1 / N_movibles) de cambiar           utiliza es BuenCandidato
	void MutacionBitFlip_1_N(vector<double> &x_var, double mutation_rate, ProblemInstance *instance);

	// 2. Bit Flip Poblacional: cada bit tiene Prob (1 / M_poblacion) de cambiar     utiliza es BuenCandidato
	void MutacionBitFlip_1_M(vector<double> &x_var, double mutation_rate, int populationSize, ProblemInstance *instance);

	// 3. Bit Flip Fijo: cada bit tiene Prob fija de cambiar (mas alta que la 1 y 2) utiliza es BuenCandidato
	void MutacionBitFlip_Fijo(vector<double> &x_var, double mutation_rate, double fixed_prob, ProblemInstance *instance);

	// 4. Swap Probabilistica: cada bit que este activo tiene prob fija de mudarse a otra posicion (solo se muda si mejora)   utiliza es BuenCandidato
	void MutacionSwapProbabilistico(vector<double> &x_var, double mutation_rate, double MutProbSwap, ProblemInstance *instance);

	// 5. Mutacion Combinada (Elegir entre BitFlip y Swap segun probabilidad)
	void Mutacion_Swap_Porcentual_1_N(vector<double> &x_var, double mutation_rate, double ratio_swap, double mutPctSwap, ProblemInstance *instance);
	void Mutacion_Swap_Porcentual_1_M(vector<double> &x_var, double mutation_rate, double ratio_swap, double populationSize, double mutPctSwap, ProblemInstance *instance);
	void Mutacion_Swap_Porcentual_Fijo(vector<double> &x_var, double mutation_rate, double ratio_swap, double fixed_prob, double mutPctSwap, ProblemInstance *instance);

	void MutacionSwapPorcentual(vector<double> &x_var, double mutation_rate, double mutPctSwap, ProblemInstance *instance);

	// 4. Mutación Delete (Elimina un % de equipos al azar)
    // mutPctDelete: Porcentaje de equipos actuales a eliminar (ej: 0.1 para borrar el 10%)
    void MutacionDeletePorcentual(vector<double> &x_var, double mutation_rate, double mutPctDelete, ProblemInstance *instance);
	// 6. Mutacion Con Delete y Swap, pero variando el porcentaje
	void MutacionHibrida_location(vector<double> &x_var, double mutation_rate, double prob_delete, double mutPctDelete, double mutPctSwap, ProblemInstance *instance);

	void CruzamientoUniformeInteligente(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance);
	void CruzamientoUniformeSemiInteligente(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance);

	void RepararPresupuesto(vector<double> &x_var, ProblemInstance *instance);
	
	void CruzamientoUniformeModificado_con_reubicacion(vector<double> &x_var1, vector<double> &x_var2, vector<double> &child, ProblemInstance *problemInstance);
	void MutacionModificada_con_reubicacion(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *problemInstance);


	void CruzamientoUniformeReloc(const vector<double>& p1,
                              const vector<double>& p2,
                              vector<double>& c,
                              ProblemInstance* inst);
	void MutacionDeletePorcentualReloc(vector<double>& x, double mutation_rate,
                                  double delete_ratio, ProblemInstance* inst);
	void MutacionSwapPorcentualReloc(vector<double>& x, double mutation_rate,
								 double swap_ratio, ProblemInstance* inst);
	void MutacionHibridaReloc(std::vector<double>& x,
											double mutation_rate,
											double prob_delete,
											double mutPctDelete,
											double mutPctSwap,
											ProblemInstance* inst);
	void RepararPresupuesto_Relocation(vector<double>& x_var, ProblemInstance* instance);
	bool EsBuenCandidato_Relocation(int idx_candidato, ProblemInstance *instance);
	void CruzamientoUniformeInteligente_Relocation(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance);
	void CruzamientoUniformeSemiInteligente_Relocation(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance);
	void CruzamientoGeografico_Relocation(const vector<double> &p1, const vector<double> &p2, vector<double> &child, ProblemInstance *instance);

	void Mutacion_Reloc_Fusion_1_N(vector<double> &x_var, double mutation_rate, double ratio_split, double mutPctSwap, ProblemInstance *instance);
	void Mutacion_Reloc_Fusion_1_M(vector<double> &x_var, double mutation_rate, double ratio_split, int populationSize, double mutPctSwap, ProblemInstance *instance);
	void Mutacion_Reloc_Fusion_Fijo(vector<double> &x_var, double mutation_rate, double ratio_split, double fixed_prob, double mutPctSwap, ProblemInstance *instance);
	void MutacionBitFlip_Relocation(vector<double> &x_var, double mutation_rate, double bit_prob, ProblemInstance *instance);
	void MutacionSwapProbabilisticoReloc(vector<double> &x_var, double mutation_rate, double MutProbSwap, ProblemInstance *instance);


	void OnePointCrossover(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance);
	void OnePointCrossover_Relocation(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance);

	void TwoPointCrossover(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance);
	void TwoPointCrossover_Relocation(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance);

	int GetWeightNumber(int nobj, int H);

	double DistanceVectorNorm1(vector<double> &vec1, vector<double> &vec2);
	double DistanceVectorNorm2(vector<double> &vec1, vector<double> &vec2);
	double VectorNorm2(vector<double> &vec1);
	void NormalizeVector(vector<double> &vect);

	double DistanceVectorPBI(vector<double> &vec1, vector<double> &vec2);
	double InnerProduct(vector<double> &vec1, vector<double> &vec2);

	double MaxElementInVector(vector<double> &vect);

	double Rnd_Uni(long *idum);
	double Get_Random_Number();
};
