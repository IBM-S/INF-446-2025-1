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
#include <libgen.h>
#include "Reader_DRP.h"
#include <stdlib.h>

#include <string>

std::string exe_dir_path;

void set_exe_path(const char* arg0){
	std::string path_str(arg0);
	size_t last_slash_idx = path_str.rfind("/");
	if (std::string::npos != last_slash_idx)
	{
		exe_dir_path = path_str.substr(0, last_slash_idx);
	} else {
		exe_dir_path = ".";
	}
}

std::string PrepararDirectorioSalida(std::string nombreInstancia) {
    
    // 1. Limpiar extensión .dat del nombre (ej: cam_1.dat -> cam_1)
    std::string nombreCarpeta = nombreInstancia;
    size_t lastindex = nombreCarpeta.find_last_of("."); 
    if (lastindex != std::string::npos) { 
        nombreCarpeta = nombreCarpeta.substr(0, lastindex); 
    }

    // 2. Construir la ruta completa
    // Usamos strings de C++ para concatenar fácil
    std::string rutaCompleta = exe_dir_path + "/../datos/res/raw_moead/" + nombreCarpeta;

    std::cout << "Preparando directorio: " << rutaCompleta << std::endl;

    // 3. Crear comando para crear directorio (mkdir -p crea toda la ruta si no existe)
    std::string cmd_mkdir = "mkdir -p \"" + rutaCompleta + "\"";
    int res_mk = system(cmd_mkdir.c_str());

    // 4. Crear comando para limpiar archivos .dat viejos (rm -f evita error si no hay archivos)
    // Borraremos rutaCompleta/*.dat
    std::string cmd_clean = "rm -f \"" + rutaCompleta + "\"/*.dat";
    int res_rm = system(cmd_clean.c_str());

    return rutaCompleta;
}

void ResetRandSeed();

int main(int argc, char *argv[])
{
	set_exe_path(argv[0]);
	// int total_run, numOfInstance;
	// std::ifstream readf("../../SETTINGS/instances/Instance.txt");
	// readf>>numOfInstance;
	// readf>>total_run;
	NumberOfObjectives = 2;
	NumberOfVariables = 324;
	NumberOfFuncEvals = 1000;

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


	srand(rnd_uni_seed);

	// Lectura de Instancia
	Reader r(instance);
	ProblemInstance *problemInstance;

	clock_t start_read = clock();
	problemInstance = r.readInputFile();
	clock_t end_read = clock();

	problemInstance->printAll();

	double read_duration = static_cast<double>(end_read - start_read) / CLOCKS_PER_SEC;
	
	std::cout << "------------------------------------------------" << std::endl;
    std::cout << "Instancia cargada: " << instance << std::endl;
    std::cout << "N (Puntos): " << NumberOfVariables << std::endl;
    std::cout << "Tiempo de lectura: " << read_duration << " s." << std::endl;
    std::cout << "------------------------------------------------" << std::endl;

	char* basec = strdup(instance);
	char* bname = basename(basec);
	strcpy(strTestInstance, bname);

	//strcpy(strTestInstance, basename(instance));

    std::string rutaSalida = PrepararDirectorioSalida(std::string(bname));


	clock_t start, temp, finish;
	double last = 0;
	start = clock();

	std::fstream fout;

	if (!strcmp(alg_name, "MOEAD"))
	{
		CALG_EMO_MOEAD MOEAD;
		MOEAD.problemInstance = problemInstance;
		MOEAD.SetOutputDirectory(rutaSalida);
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
	std::cout << "Seed: " << rnd_uni_seed << std::endl;
	std::cout << "Inst: " << instance << std::endl;

	// Guardar en archivo
	char timeLogFilename[1024];
	sprintf(timeLogFilename, "%s/execution_time.log", exe_dir_path.c_str());
	std::ofstream fout_time(timeLogFilename, std::ios::app);
	fout_time << "Inst: " << bname
			  << ", Seed: " << rnd_uni_seed
			  << ", Dest. Route: " << rutaSalida
			  << ", Tiempo (s): " << duration
			  << std::endl;
	fout_time.close();

	std::cout << "Done!" << std::endl;
	free(basec);

	return 0;
}

void ResetRandSeed()
{

	rnd_uni_seed = (rnd_uni_seed + 23) % 1377;
	rnd_uni_init = -(long)rnd_uni_seed;
}
