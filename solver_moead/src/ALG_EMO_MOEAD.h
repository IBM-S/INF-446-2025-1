#pragma once

#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <algorithm>

#include "GlobalVariable.h"
#include "IndividualBase.h"
#include "SubProblemBase.h"

class CALG_EMO_MOEAD
{
public:
	CALG_EMO_MOEAD(void);
	~CALG_EMO_MOEAD(void);

	void Execute(int run_id);

	void InitializeParameter();
	void SetOutputDirectory(std::string path) {
		this->outputDirectory = path;
	}

	// Setters para configuración del algoritmo
	void SetPopulationSize(int p) { s_PopulationSize = p; }
    void SetNeighborhoodSize(int n) { s_NeighborhoodSize = n; }

	void SetNeighborhoodSizePct(double n) { m_NeighborhoodSizePct = n; }

	void SetMutationRate(double r)     { m_MutationRate = r; }
    void SetCrossoverRate(double r)    { m_CrossoverRate = r; }
    void SetOp1MutationProb(double p)  { m_Op1MutationProb = p; } // Probabilidad del Operador 1
	void SetProblemType(std::string t) { m_ProblemType = t; }     // "cam" o "drp"
    void SetVariant(std::string v)     {                          // "location" o "relocation"
        if (v == "relocation") m_IsRelocation = true;
        else m_IsRelocation = false;
    }
	void SetMaxTime(double t) { m_MaxTimeSeconds = t; }
	void SetDecompositionType(int type) { s_PBI_type = type; }
	void SetSaveInterval(int interval) { m_SaveInterval = interval; }

	// Setters para operadores avanzados
	void SetMutationType (int type) {m_MutationType = type;}
	void SetCrossoverType(int type) {m_CrossoverType = type;}
	void SetMutationPercentage(double perc) {m_MutationPercentage = perc;}
	void SetBitFlipProb(double prob) { m_BitFlipProb = prob; }

	void SetMutPctDelete (double pct) { m_MutPctDelete = pct; }
	void SetMutPctSwap   (double pct) { m_MutPctSwap = pct; }
	void SetMutProbSwap (double prob) { m_MutProbSwap = prob;}

	void SetMutHybridSplit(double split) { m_MutHybridSplit = split; }
	void SetMutOp1(int op) { m_MutOp1 = op; }
	void SetMutOp2(int op) { m_MutOp2 = op; }

	void SetInitializationTypeRelocation(int type) { m_InitializationTypeRelocation = type; }
    void SetProbChooseMoveRelocation(double prob) { m_ProbChooseMoveRelocation = prob; }
    void SetSplitPctRelocation(double pct) { m_SplitPctRelocation = pct; }

	void SetInitDistributionStrategy(int strategy) { m_InitDistributionStrategy = strategy; }
    void SetPowerExp(double exp) { m_PowerExp = exp; }
    void SetNoisePct(double pct) { m_NoisePct = pct; }

	int s_PopulationSize;
	int s_NeighborhoodSize;
	ProblemInstance *problemInstance;

protected:
	void InitializePopulation();
	void InitializeNeighborhood();
	void EvolvePopulation();

	// Funciones internas
	void UpdateReference(vector<double> &obj_vect);
	void FindNadirPoint();
	void UpdateNadirPoint(vector <double> &obj_vect);
	void NormalizeWeight();
	void NormalizeIndividual(CIndividualBase &ind);

	// Seleccion y Reemplazo
	void SelectMatingPool(vector<unsigned> &pool, unsigned sp_id, unsigned selected_size);
	void UpdateProblem_original(CIndividualBase &child, unsigned sp_id);
	void UpdateProblem_modificado(CIndividualBase &child, unsigned sp_id);
	void UpdateProblem_modificado_v2(CIndividualBase &child, unsigned sp_id);

	bool IsTerminated();
	void SaveObjSpace(char saveFilename[1024]);
	void SaveVarSpace(char saveFilename[1024]);
	void SavePopulation(int run_id);
	void SaveFinalPopulation();

	// Variables Algoritmicas
	vector<CSubProblemBase> m_PopulationSOP;
	vector<double> v_IdealPoint;
	vector<double> v_NadirPoint;


	// Configuracion
	int s_PBI_type;
	int s_Fevals_Count;
	std::string outputDirectory;
    std::string m_ProblemType;  // Para logs o lógica específica (CAM/DRP)
    bool m_IsRelocation;        // true = con reubicación, false = sin reubicación
	
	double m_NeighborhoodSizePct;

	// Parametros Evolutivos
    double m_MutationRate;      // Probabilidad general de mutar
    double m_CrossoverRate;     // Probabilidad general de cruzar
    double m_Op1MutationProb;   // Probabilidad de usar Mutación Tipo 1 (vs Tipo 2)


	// Parametros de los operadores avanzados
	int m_MutationType;   // ID del operador de mutación
    int m_CrossoverType;  // ID del operador de cruzamiento
    double m_MutationPercentage; // Para operadores porcentuales (ej. 0.1 para 10%)
	double m_BitFlipProb; 

	double m_MutPctDelete;
	double m_MutPctSwap;
	double m_MutProbSwap;

	double m_MutHybridSplit;
	int m_MutOp1;
	int m_MutOp2;

	int m_InitializationTypeRelocation;
    double m_ProbChooseMoveRelocation;
    double m_SplitPctRelocation;

	int m_InitDistributionStrategy;
    double m_PowerExp;
    double m_NoisePct;
	
	double m_MaxTimeSeconds; // Tiempo máximo en segundos (0 = sin límite)
	int m_SaveInterval;
};
