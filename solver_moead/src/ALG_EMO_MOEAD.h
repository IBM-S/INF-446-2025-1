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

	void InitializeNeighborhood();
	void InitializePopulation();
	void InitializeParameter();

	void UpdateReference(vector<double> &obj_vect);
	void UpdateProblem(CIndividualBase &child, unsigned sp_id);

	void FindNadirPoint();
	void NormalizeIndividual(CIndividualBase &ind);
	void NormalizeWeight();

	void SelectMatingPool(vector<unsigned> &pool, unsigned sp_id, unsigned selected_size);
	void EvolvePopulation();
	bool IsTerminated();

	void SaveObjSpace(char saveFilename[1024]);
	void SaveVarSpace(char saveFilename[1024]);
	void SavePopulation(int run_id);

	std::string outputDirectory;
	void SetOutputDirectory(std::string path) {
		this->outputDirectory = path;
	}

	void SetMutationRate(double r)     { m_MutationRate = r; }
    void SetCrossoverRate(double r)    { m_CrossoverRate = r; }
    void SetOp1MutationProb(double p)  { m_Op1MutationProb = p; } // Probabilidad del Operador 1
    
    void SetProblemType(std::string t) { m_ProblemType = t; }     // "cam" o "drp"
    void SetVariant(std::string v)     {                          // "location" o "relocation"
        if (v == "relocation" || v == "flexible") m_IsRelocation = true;
        else m_IsRelocation = false;
    }
	void SetPopulationSize(int p) { s_PopulationSize = p; }
    void SetNeighborhoodSize(int n) { s_NeighborhoodSize = n; }

public:
	ProblemInstance *problemInstance;

	vector<CSubProblemBase> m_PopulationSOP;
	vector<double> v_IdealPoint;
	vector<double> v_NadirPoint;

	unsigned int s_PopulationSize;
	unsigned int s_NeighborhoodSize;
	//	unsigned int     s_ReplacementLimit;
	//	double           s_LocalMatingRatio;
	int s_Fevals_Count;

	int s_PBI_type;

private:
    // Variables privadas para configuración
    double m_MutationRate;      // Probabilidad general de mutar
    double m_CrossoverRate;     // Probabilidad general de cruzar
    double m_Op1MutationProb;   // Probabilidad de usar Mutación Tipo 1 (vs Tipo 2)
    
    bool m_IsRelocation;        // true = con reubicación, false = sin reubicación
    std::string m_ProblemType;  // Para logs o lógica específica (CAM/DRP)


};
