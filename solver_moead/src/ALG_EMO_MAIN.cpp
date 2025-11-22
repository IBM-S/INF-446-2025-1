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

void PrintUsage() {
    std::cout << "\n==========================================================" << std::endl;
    std::cout << "      MOEA/D - Location & Relocation (CAM / DRP)          " << std::endl;
    std::cout << "==========================================================" << std::endl;
    std::cout << "Uso: ./MOEAD -inst <archivo.dat> [opciones]" << std::endl;

    std::cout << "\n--- Configuración del Problema ---" << std::endl;
    std::cout << "  -inst <string>    : Ruta del archivo de instancia (OBLIGATORIO)" << std::endl;
    std::cout << "  -type <string>    : Tipo: 'cam' o 'drp' (Defecto: cam)" << std::endl;
    std::cout << "  -variant <string> : Variante: 'location' (fijo) o 'relocation' (flexible) (Defecto: location)" << std::endl;
    std::cout << "  -nvars <int>      : Número de variables/nodos (Defecto: 324)" << std::endl;

    std::cout << "\n--- Configuración del Algoritmo ---" << std::endl;
    std::cout << "  -alg <string>     : Algoritmo: 'MOEAD' o 'MOEAD-DE' (Defecto: MOEAD)" << std::endl;
    std::cout << "  -seed <int>       : Semilla aleatoria (Defecto: 123)" << std::endl;
    std::cout << "  -neval <int>      : Número máx. de evaluaciones (Criterio de parada) (Defecto: 1000)" << std::endl;

    std::cout << "\n--- Parámetros Evolutivos ---" << std::endl;
    std::cout << "  -mut <double>     : Tasa de Mutación Global [0.0 - 1.0] (Defecto: 0.05)" << std::endl;
    std::cout << "  -cross <double>   : Tasa de Cruzamiento [0.0 - 1.0] (Defecto: 1.0)" << std::endl;
    std::cout << "  -op1 <double>     : Probabilidad del Operador 1 de Mutación [0.0 - 1.0] (Defecto: 0.5)" << std::endl;
    std::cout << "                      (Si op1=1.0 solo se usa Delete, si op1=0.0 solo Swap)" << std::endl;
    std::cout << "==========================================================" << std::endl;
}

void ResetRandSeed();

int main(int argc, char *argv[])
{
	set_exe_path(argv[0]);
	// --- VALORES POR DEFECTO ---
    std::string instancePath = "";
    rnd_uni_seed = 123;
    NumberOfVariables = 324;
    
    // Parámetros Algoritmo
    double mutationRate = 0.05;
    double crossoverRate = 1.0;
    double op1Prob = 0.5; // 50% swap, 50% bitflip (por ejemplo)

	NumberOfObjectives = 2;
    NumberOfFuncEvals = 1000; 

    std::string variant = "location"; // o "relocation"
    std::string problemType = "cam";  // o "drp"
    std::string algName = "MOEAD";

	if (argc < 2) {
        PrintUsage();
        return 0;
    }


    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        
        if (arg == "-inst") { if (i + 1 < argc) instancePath = argv[++i]; }
        else if (arg == "-seed") { if (i + 1 < argc) rnd_uni_seed = atoi(argv[++i]); }
        else if (arg == "-nvars") { if (i + 1 < argc) NumberOfVariables = atoi(argv[++i]); }
        else if (arg == "-neval") { if (i + 1 < argc) NumberOfFuncEvals = atoi(argv[++i]); } 

        else if (arg == "-mut") { if (i + 1 < argc) mutationRate = atof(argv[++i]); }
        else if (arg == "-cross") { if (i + 1 < argc) crossoverRate = atof(argv[++i]); }
        else if (arg == "-op1") { if (i + 1 < argc) op1Prob = atof(argv[++i]); }

        else if (arg == "-variant") { if (i + 1 < argc) variant = argv[++i]; }
        else if (arg == "-type") { if (i + 1 < argc) problemType = argv[++i]; }

        else if (arg == "-alg") { if (i + 1 < argc) algName = argv[++i]; }
    }


	if (instancePath == "") {
        std::cerr << "Error: Debes especificar una instancia con -inst" << std::endl;
        return 1;
    }

	srand(rnd_uni_seed);

	// Lectura de Instancia
	Reader r(instancePath.c_str());
	ProblemInstance *problemInstance;

	clock_t start_read = clock();
	problemInstance = r.readInputFile();
	clock_t end_read = clock();

	// problemInstance->printAll();

	double read_duration = static_cast<double>(end_read - start_read) / CLOCKS_PER_SEC;
	
	std::cout << "=== CONFIGURACION MOEAD ===" << std::endl;
    std::cout << " Instancia   : " << instancePath << std::endl;
    std::cout << " Tipo        : " << problemType << " | Variante: " << variant << std::endl;
	std::cout << " N (Puntos)  : " << NumberOfVariables << std::endl;
	std::cout << " Evaluaciones: " << NumberOfFuncEvals << std::endl;
    std::cout << " Mutacion    : " << mutationRate << " (Op1 Prob: " << op1Prob << ")" << std::endl;
    std::cout << " Crossover   : " << crossoverRate << std::endl;
	std::cout << "Tiempo de lectura: " << read_duration << " s." << std::endl;
    std::cout << "===========================" << std::endl;

	char* basec = strdup(instancePath.c_str());
	char* bname = basename(basec);
	strcpy(strTestInstance, bname);

    std::string rutaSalida = PrepararDirectorioSalida(std::string(bname));


	clock_t start, temp, finish;
	double last = 0;
	start = clock();

	std::fstream fout;

	if (algName == "MOEAD")
	{
		CALG_EMO_MOEAD MOEAD;
		MOEAD.problemInstance = problemInstance;

		MOEAD.SetMutationRate(mutationRate);
        MOEAD.SetCrossoverRate(crossoverRate);
        MOEAD.SetOp1MutationProb(op1Prob);
        MOEAD.SetProblemType(problemType);
        MOEAD.SetVariant(variant); // Configura m_IsRelocation internamente
        MOEAD.SetOutputDirectory(rutaSalida);

		MOEAD.Execute(1); // Se ejecuta solo una vez
	}

	if (algName == "MOEAD-DE")
	{
		CALG_EMO_MOEAD_DE MOEAD_DE;
		MOEAD_DE.problemInstance = problemInstance;
		MOEAD_DE.Execute(1); // Se ejecuta solo una vez
	}

	finish = clock(); // Tiempo final
	double duration = static_cast<double>(finish - start) / CLOCKS_PER_SEC;

	// Mostrar por consola
	std::cout << "------------------------------------------------" << std::endl;
	std::cout << " Algoritmo : " << algName << std::endl;
    std::cout << " Instancia : " << bname << std::endl;
    std::cout << " N (Puntos): " << NumberOfVariables << std::endl;
	std::cout << " Seed      : " << rnd_uni_seed << std::endl;
    std::cout << " Mutacion  : " << mutationRate << std::endl;
    std::cout << " Crossover : " << crossoverRate << std::endl;
    std::cout << " Duracion  : " << duration << " segundos." << std::endl;
    std::cout << "------------------------------------------------" << std::endl;

	// Guardar en archivo
	char timeLogFilename[1024];
	sprintf(timeLogFilename, "%s/execution_time.log", exe_dir_path.c_str());
	std::ofstream fout_time(timeLogFilename, std::ios::app);
	fout_time << "Inst: " << bname
			  << ", Problem Type: " << problemType
			  << ", variant: " << variant
              << ", N Var: " << NumberOfVariables
              << ", N Eval: " << NumberOfFuncEvals
			  << ", Seed: " << rnd_uni_seed
			  << ", Mutation Rate: " << mutationRate
			  << ", Op1 Prob: " << op1Prob
              << ", Crossover Rate: " << crossoverRate
              << ", Time: " << duration
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
