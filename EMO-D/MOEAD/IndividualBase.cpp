// Individual.cpp: implementation of the CIndividualBase class.
//
//////////////////////////////////////////////////////////////////////
#include <iostream>
#include <random>
#include "IndividualBase.h"

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

CIndividualBase::CIndividualBase()
{
	x_var    = vector<double>(NumberOfVariables, 0);
    f_obj    = vector<double>(NumberOfObjectives, 0);
	f_normal = vector<double>(NumberOfObjectives, 0);
}

CIndividualBase::~CIndividualBase()
{
	
}

void CIndividualBase::Randomize()
{
	int lowBound = 0, uppBound = 1;	

	unsigned int n;

    for(n=0; n<NumberOfVariables; n++)
	{
		x_var[n] = lowBound + UtilityToolBox.Get_Random_Number()*(uppBound - lowBound);    
	}
}

// Con est funcion vamos a crear funciones factibles.
// A partir de la representacion binaria. Con k desfibriladores, con
// el presupuesto.

void CIndividualBase::GenerateSimpleFeasibleSolution(int num_AEDs, int total_locations)
{
	// Inicializa todo en 0
    std::fill(x_var.begin(), x_var.end(), 0.0);

    for (int i = 0; i < num_AEDs && i < total_locations; ++i) {
        // Elegimos un ID aleatorio de los filtrados
        int idx_filtrado = rand() % total_locations;  // Índice aleatorio entre [0, tamaño de ids_filtrados-1]
        int id = idx_filtrado;  // Obtenemos el ID filtrado
		int pos = id;
        x_var[pos] = 1.0;
    }

    //this->Evaluate(); // Muy importante
}

void CIndividualBase::Evaluate()
{

	//if(!strcmp("ZDT1", strTestInstance))   TestInstance.ZDT1(x_var, f_obj, x_var.size());
	//TestInstance.fdvrp(x_var, f_obj, x_var.size());

    TestInstance.DRP_Evaluate(x_var, f_obj, problemInstance);

}


void CIndividualBase::Show(int type)
{

	unsigned int n;
	if(type==0)
	{
		for(n=0; n<NumberOfObjectives; n++)
			std::cout << f_obj[n] << " ";
		std::cout << endl;
	}
	else
	{
		for(n=0; n<NumberOfVariables; n++)
			printf("%f ",x_var[n]);
		printf("\n");	
	}
}


void CIndividualBase::operator=(const CIndividualBase &ind2)
{
    x_var = ind2.x_var;
	f_obj = ind2.f_obj;
	f_normal = ind2.f_normal;
	rank  = ind2.rank;
	type  = ind2.type;
	count = ind2.count;
	density = ind2.density;
}

bool CIndividualBase::operator<(const CIndividualBase &ind2)
{
	bool dominated = true;
	unsigned int n;
    for(n=0; n<NumberOfObjectives; n++)
	{
		if(ind2.f_obj[n]<f_obj[n]) return false;
	}
	if(ind2.f_obj==f_obj) return false;
	return dominated;
}


bool CIndividualBase::operator<<(const CIndividualBase &ind2)
{
	bool dominated = true;
	unsigned int n;
    for(n=0; n<NumberOfObjectives; n++)
	{
		if(ind2.f_obj[n]<f_obj[n]  - 0.0001) return false;
	}
	if(ind2.f_obj==f_obj) return false;
	return dominated;
}

bool CIndividualBase::operator==(const CIndividualBase &ind2)
{
	if(ind2.f_obj==f_obj) return true;
	else return false;
}


