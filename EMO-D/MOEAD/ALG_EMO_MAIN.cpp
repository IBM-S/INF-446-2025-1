// ************************************************************
// Code:   The new C++ implementation of MOEA/D and MOEA/D-DE
// Author: Dr. Hui Li
// Institude: Xi'an Jiaotong University
// DATE: 2020.2.18
// References:
// [1] Qingfu Zhang, Hui Li: MOEA/D: A Multiobjective Evolutionary Algorithm Based on Decomposition. IEEE Trans. Evolutionary Computation 11(6): 712-731 (2007)
// [2] Hui Li, Qingfu Zhang: Multiobjective Optimization Problems With Complicated Pareto Sets, MOEA/D and NSGA-II. IEEE Trans. Evolutionary Computation 13(2):284-302  (2009)
// ************************************************************

#include "GlobalVariable.h"
#include "ALG_EMO_MOEAD.h"
#include "ALG_EMO_MOEAD_DE.h"
#include <time.h>
#include <string.h>
#include "DRP_ProblemInstance.h"

#include "Reader_DRP.h"

void ResetRandSeed();

int main(int argc, char *argv[])
{
	// int total_run, numOfInstance;
	// std::ifstream readf("../../SETTINGS/instances/Instance.txt");
	// readf>>numOfInstance;
	// readf>>total_run;
	NumberOfObjectives = 2;
	NumberOfVariables = 324;
	NumberOfFuncEvals = 12500;

	char alg_name[1024];

	sprintf(alg_name, "MOEAD");
	// sprintf(alg_name,"MOEAD-DE");

	if (argc < 2)
	{
		cout << "Wrong number of parameters! " << endl;
		cout << "Usage: ./MOEAD <instance_file> <random_seed> <num_variables>" << endl;
		return 0;
	}
	char *instance(argv[1]);
	rnd_uni_seed = atoi(argv[2]);
	NumberOfVariables = atoi(argv[3]);

	Reader r(instance);

	ProblemInstance *problemInstance;
	problemInstance = r.readInputFile();
	problemInstance->printAll();

	sprintf(strTestInstance, instance);

	clock_t start, temp, finish;
	double last = 0;
	start = clock();

	std::fstream fout;
	char logFilename[1024];
	sprintf(logFilename, "SAVING/%s/LOG/LOG_%s.dat", alg_name, strTestInstance);
	fout.open(logFilename, std::ios::out);

	if (!strcmp(alg_name, "MOEAD"))
	{
		CALG_EMO_MOEAD MOEAD;
		MOEAD.problemInstance = problemInstance;
		MOEAD.Execute(1); // Se ejecuta solo una vez
	}

	if (!strcmp(alg_name, "MOEAD-DE"))
	{
		CALG_EMO_MOEAD_DE MOEAD_DE;
		MOEAD_DE.problemInstance = problemInstance;
		MOEAD_DE.Execute(1); // Se ejecuta solo una vez
	}

	finish = clock(); // Tiempo final
	double duration = static_cast<double>(finish - start) / CLOCKS_PER_SEC;

	// Mostrar por consola
	std::cout << "Tiempo de ejecución: " << duration << " segundos." << std::endl;
	std::cout << "Semilla: " << rnd_uni_seed << std::endl;
	std::cout << "Instancia: " << instance << std::endl;

	// Guardar en archivo
	std::ofstream fout_time("execution_time.log", std::ios::app);
	fout_time << "Instancia: " << instance
			  << ", Semilla: " << rnd_uni_seed
			  << ", Tiempo (s): " << duration
			  << std::endl;
	fout_time.close();

	std::cout << "Done!" << std::endl;

	return 0;
}

void ResetRandSeed()
{

	rnd_uni_seed = (rnd_uni_seed + 23) % 1377;
	rnd_uni_init = -(long)rnd_uni_seed;
}
