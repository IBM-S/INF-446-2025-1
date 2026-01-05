// Individual.h: interface for the CIndividualBase class.
//
//////////////////////////////////////////////////////////////////////
#pragma once

#include "GlobalVariable.h"
#include "GlobalObject.h"
#include <vector>
#include <string.h>
using namespace std;

class CIndividualBase
{
public:
	CIndividualBase();
	virtual ~CIndividualBase();

	ProblemInstance *problemInstance;

	vector<double> x_var;
	vector<double> f_obj;
	vector<double> f_normal;

	unsigned int rank;
	unsigned int count;
	unsigned int type;
	double density;

	void Randomize();
	void GenerateSimpleFeasibleSolution(int num_AEDs);

	void GenerateSimpleFeasible_Reloc_OnlyMove(double presupuesto_disponible);
	void GenerateSimpleFeasible_Reloc_OnlyBuy(double presupuesto_disponible);
	void GenerateSimpleFeasible_Reloc_Choose_Move_or_Buy(double presupuesto_disponible, double prob_choose_move);
	void GenerateSimpleFeasible_Reloc_HybridSplit(double presupuesto_disponible, double split_pct);

	void InstalarEnHuecosLibres(int cantidad_a_instalar);

	void GenerateSimpleFeasible_Reloc_OnlyMove_Aleatorio(double presupuesto_disponible);
	void GenerateSimpleFeasible_Reloc_OnlyBuy_Aleatorio(double presupuesto_disponible);
	void GenerateSimpleFeasible_Reloc_Choose_Move_or_Buy_Aleatorio(double presupuesto_disponible, double prob_choose_move);
	void GenerateSimpleFeasible_Reloc_HybridSplit_Aleatorio(double presupuesto_disponible, double split_pct);

	
	void GenerateSimpleFeasibleSolution_v2(int num_AEDs, int total_locations);
	void GenerateGreedyFeasibleSolution(int num_AEDs, double randomness_factor);
	void Evaluate();
	void Show(int type);

	bool operator<(const CIndividualBase &ind2);
	bool operator<<(const CIndividualBase &ind2);
	bool operator==(const CIndividualBase &ind2);
	void operator=(const CIndividualBase &ind2);
};
