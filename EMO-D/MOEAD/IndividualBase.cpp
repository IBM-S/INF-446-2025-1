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
	//std::cout << "x_var.size() = " << x_var.size() << ", total_locations = " << total_locations << ", num_AEDs = " << num_AEDs << std::endl;

	// Inicializa todo en 0
    std::fill(x_var.begin(), x_var.end(), 0.0);

	// 1. Crear lista de IDs
    std::vector<int> ids(total_locations);
    for (int i = 0; i < total_locations; ++i) {
        ids[i] = i;
    }

	// 2. Revolver los IDs
    std::random_shuffle(ids.begin(), ids.end()); // usa srand() antes si quieres control

	/* std::cout << "IDs mezclados: ";
	for (int id : ids) {
		std::cout << id << " ";
	}
	std::cout << std::endl; */


    // 3. Seleccionar los primeros `num_AEDs`
    for (int i = 0; i < num_AEDs && i < total_locations; ++i) {
        int pos = ids[i];
        x_var[pos] = 1.0;
		//std::cout << "i = " << i << std::endl;

    }
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


