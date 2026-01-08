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

std::string PrepararDirectorioSalida(std::string nombreInstancia, std::string tipoProblema, std::string subCarpeta) {
    
    // 1. Limpiar extensión .dat del nombre (ej: cam_1.dat -> cam_1)
    std::string nombreCarpeta = nombreInstancia;
    size_t lastindex = nombreCarpeta.find_last_of("."); 
    if (lastindex != std::string::npos) { 
        nombreCarpeta = nombreCarpeta.substr(0, lastindex); 
    }

    // 2. Construir la ruta completa
    // Usamos strings de C++ para concatenar fácil
    std::string rutaBase = exe_dir_path + "/../datos/res/raw_moead/" + tipoProblema + "/" + nombreCarpeta;

    std::string rutaCompleta = rutaBase;

    if (!subCarpeta.empty()) {
        rutaCompleta += "/" + subCarpeta;
    }

    // 3. Crear comando para crear directorio (mkdir -p crea toda la ruta si no existe)
    std::string cmd_mkdir = "mkdir -p \"" + rutaCompleta + "\"";
    int res_mk = system(cmd_mkdir.c_str());

    // 4. Crear comando para limpiar archivos .dat viejos (rm -f evita error si no hay archivos)
    // Borraremos rutaCompleta/*.dat
    std::string cmd_clean = "rm -f \"" + rutaCompleta + "\"/*.dat";
    int res_rm = system(cmd_clean.c_str());

    return rutaCompleta;
}

// ... includes y funciones previas (set_exe_path, PrepararDirectorioSalida) ...

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
    std::cout << "  -pop <int>        : Tamaño Población (Sobrescribe MOEAD.txt)" << std::endl;
    std::cout << "  -neighbor <int>   : Tamaño Vecindario Fijo (ej: 20) (Sobrescribe MOEAD.txt)" << std::endl;
    std::cout << "  -neighborPct <dbl>: Tamaño Vecindario Porcentual (ej: 0.2 = 20%) (Prioridad sobre -neighbor)" << std::endl;
    std::cout << "  -decomp <int>     : Tipo Descomposicion (1: TCH, 2: Mod, 3: PBI) (Defecto: 1)" << std::endl;
    std::cout << "  -save <int>       : Guardar cada X gens (0 = Solo Inicio/Fin) (Defecto: 0)" << std::endl;
    
    std::cout << "\n--- Criterios de Parada ---" << std::endl;
    std::cout << "  -neval <int>      : Número máx. de evaluaciones (Defecto: 1000)" << std::endl;
    std::cout << "  -time <double>    : Tiempo máx. de ejecución en segundos (0 = Sin límite) (Defecto: 0)" << std::endl;

    std::cout << "\n--- Parámetros Evolutivos ---" << std::endl;
    std::cout << "  -mut <double>     : Tasa de Mutación Global [0.0 - 1.0] (Defecto: 0.5)" << std::endl;
    std::cout << "  -cross <double>   : Tasa de Cruzamiento [0.0 - 1.0] (Defecto: 0.7)" << std::endl;
    
    std::cout << "\n--- Operadores Avanzados ---" << std::endl;
    std::cout << "  -mutType <int>    : 1:BitFlip (1/N), 2:BitFlip (1/M), 3:BitFlip (Fijo), 4:Intelligent, 5:Pct, 6:Hybrid (Def: 6)" << std::endl;
    std::cout << "  -crossType <int>  : 1:Modificado Uniforme, 2:Inteligente, 3: SemiInteligente (Def: 3)" << std::endl;
    std::cout << "  -op1 <double>     : Prob. Op1 en Híbrido (Def: 0.2)" << std::endl;
    std::cout << "  -mutPct <double>  : % Intensidad (Para MutType 4, 5, 6, 7, 9, 10, 11) (Def: 0.2)" << std::endl;
    std::cout << "  -mutPctDelete <double>: % Intensidad Delete (Para MutType 10, 11. Si no se define, usa mutPct)" << std::endl;
    std::cout << "  -mutPctSwap <double>  : % Intensidad Swap (Para MutType 4, 5, 6 ,7, 9, 11. Si no se define, usa mutPct)" << std::endl;
    std::cout << "  -bitprob <double> : Prob. BitFlip individual (Def: 0.01)" << std::endl;

    std::cout << "\n--- Parámetros Distribución Inicial de Recursos ---" << std::endl;
    std::cout << "  -initDist <int>   : Estrategia Distribución (0:Rand, 1:Extremos, 2:Curva+Ruido) (Def: 2)" << std::endl;
    std::cout << "  -powerExp <dbl>   : Exponente para la curva en Estrategia 2 (Def: 5.0)" << std::endl;
    std::cout << "  -noisePct <dbl>   : Porcentaje de ruido en Estrategia 2 (0.0 - 1.0) (Def: 0.20)" << std::endl;

    std::cout << "\n--- Parámetros de Inicialización (Relocación) ---" << std::endl;
    std::cout << "  -initTypeRelocation <int>   : Estrategia: 1:Orig, 2:Mix, 3:Move, 4:Buy, 5:M/B, 6:Hyb, 7:M/B_Rnd, 8:Hyb_Rnd (Def: 3)" << std::endl;
    std::cout << "  -probMoveRelocation <double>: Probabilidad de elegir 'Solo Mover' en estrategia 5 y 7 (Def: 0.5)" << std::endl;
    std::cout << "  -splitPctRelocation <double>: Porcentaje de presupuesto para mover en estrategia 6 y 8 (Def: 0.5)" << std::endl;

    
    std::cout << "\n--- Salida de Datos ---" << std::endl;
    std::cout << "  -outDir <string>  : Directorio específico donde guardar resultados (Opcional)" << std::endl;
    std::cout << "==========================================================" << std::endl;
}

void ResetRandSeed();

int main(int argc, char *argv[])
{
	set_exe_path(argv[0]);
	// --- VALORES POR DEFECTO --- 
    int userPop = 0;
    int userNeighbor = 0;

    std::string instancePath = "";
    rnd_uni_seed = 123;
    NumberOfVariables = 324;
    
    // Parámetros Algoritmo
    double mutationRate = 0.5;
    double crossoverRate = 0.7;
    double op1Prob = 0.5; // 20% delete, 80% swap (por ejemplo)

	NumberOfObjectives = 2;
    NumberOfFuncEvals = 40000; 

    std::string variant = "location"; // o "relocation"
    std::string problemType = "cam";  // o "drp"
    std::string algName = "MOEAD";

    double maxTime = 0; 

    std::string userOutputDir = ""; 

    int decompType = 1;   // 1 por defecto (Tchebycheff)
    int saveInterval = 0; // 0 por defecto (Solo guarda Gen 0 y Gen Final)

    int mutType = 16;     // Default: Híbrida
    int crossType = 9;    // Default: Inteligente
    double mutPct = 0.2; // Default: 5% intensidad para operadores porcentuales
    double bitFlipProb = 0.01; // Default: 1% probabilidad para BitFlip Fijo

    double userNeighborPct = 0.0; // 0 = usar archivo, >0 usar porcentaje
    double userMutPctDelete = 0.1; // 0 = usar default
    double userMutPctSwap = 0.4;   // 0 = usar default

    int initTypeRelocation = 2;           // Default: Solo Mover (o el que prefieras como base)
    double probMoveRelocation = 0.5;      // Default: 50%
    double splitPctRelocation = 0.5;      // Default: 50% split

    int initDist = 2;
    double powerExp = 5.0;
    double noisePct = 0.20;

	if (argc < 2) {
        PrintUsage();
        return 0;
    }


    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        
        if (arg == "-inst") { if (i + 1 < argc) instancePath = argv[++i]; }
        else if (arg == "-seed") { if (i + 1 < argc) rnd_uni_seed = atoi(argv[++i]); }
        else if (arg == "-nvars") { if (i + 1 < argc) NumberOfVariables = atoi(argv[++i]); }
        
        // Criterios de parada
		else if (arg == "-neval") { if (i + 1 < argc) NumberOfFuncEvals = atoi(argv[++i]); } 
        else if (arg == "-time") { if (i + 1 < argc) maxTime = atof(argv[++i]); } 
        
        // Configuración Algoritmo
        else if (arg == "-pop") { if (i + 1 < argc) userPop = atoi(argv[++i]); }
        else if (arg == "-neighbor") { if (i + 1 < argc) userNeighbor = atoi(argv[++i]); }
        else if (arg == "-neighborPct") { if (i + 1 < argc) userNeighborPct = atof(argv[++i]); }
        else if (arg == "-decomp") { if (i + 1 < argc) decompType = atoi(argv[++i]); }
        else if (arg == "-save") { if (i + 1 < argc) saveInterval = atoi(argv[++i]); }

        // Evolutivos
        else if (arg == "-mut") { if (i + 1 < argc) mutationRate = atof(argv[++i]); }
        else if (arg == "-cross") { if (i + 1 < argc) crossoverRate = atof(argv[++i]); }
        else if (arg == "-op1") { if (i + 1 < argc) op1Prob = atof(argv[++i]); }

        // Tipos
        else if (arg == "-variant") { if (i + 1 < argc) variant = argv[++i]; }
        else if (arg == "-type") { if (i + 1 < argc) problemType = argv[++i]; }
        else if (arg == "-alg") { if (i + 1 < argc) algName = argv[++i]; }

        else if (arg == "-outDir") { if (i + 1 < argc) userOutputDir = argv[++i]; }
        else if (arg == "-mutType") { if (i + 1 < argc) mutType = atoi(argv[++i]); }
        else if (arg == "-crossType") { if (i + 1 < argc) crossType = atoi(argv[++i]); }
        else if (arg == "-mutPct") { if (i + 1 < argc) mutPct = atof(argv[++i]); }
        else if (arg == "-bitprob") { if (i + 1 < argc) bitFlipProb = atof(argv[++i]); }
        else if (arg == "-mutPctDelete") { if (i + 1 < argc) userMutPctDelete = atof(argv[++i]); }
        else if (arg == "-mutPctSwap") { if (i + 1 < argc) userMutPctSwap = atof(argv[++i]); }

        else if (arg == "-initTypeRelocation") { if (i + 1 < argc) initTypeRelocation = atoi(argv[++i]); }
        else if (arg == "-probMoveRelocation") { if (i + 1 < argc) probMoveRelocation = atof(argv[++i]); }
        else if (arg == "-splitPctRelocation") { if (i + 1 < argc) splitPctRelocation = atof(argv[++i]); }

        else if (arg == "-initDist") { if (i + 1 < argc) initDist = atoi(argv[++i]); }
        else if (arg == "-powerExp") { if (i + 1 < argc) powerExp = atof(argv[++i]); }
        else if (arg == "-noisePct") { if (i + 1 < argc) noisePct = atof(argv[++i]); }
    }

    if (userMutPctDelete < 0) userMutPctDelete = mutPct;
    if (userMutPctSwap < 0)   userMutPctSwap = mutPct;


	if (instancePath == "") {
        std::cerr << "Error: Debes especificar una instancia con -inst" << std::endl;
        return 1;
    }

	srand(rnd_uni_seed);

	// 1 Lectura de Instancia
	Reader r(instancePath.c_str());
	ProblemInstance *problemInstance;
	clock_t start_read = clock();
	problemInstance = r.readInputFile();
    problemInstance->PrecalcularCoberturas();
	clock_t end_read = clock();

	double read_duration = static_cast<double>(end_read - start_read) / CLOCKS_PER_SEC;

    if (problemInstance->getNodes().size() > 0) {
        NumberOfVariables = problemInstance->getNodes().size();
    }

	char* basec = strdup(instancePath.c_str());
	char* bname = basename(basec);
	strcpy(strTestInstance, bname);
    std::string rutaSalida = PrepararDirectorioSalida(std::string(bname), problemType, userOutputDir);

    // 2 Configuracion del algoritmo
    CALG_EMO_MOEAD* algoritmo = nullptr; // Puntero base (si usaras polimorfismo sería ideal)
    CALG_EMO_MOEAD MOEAD;
    CALG_EMO_MOEAD_DE MOEAD_DE; // Asumiendo que hereda o tiene estructura similar

    int populationSize = 0;
    int neighborSize = 0;

    if (algName == "MOEAD") {
        MOEAD.problemInstance = problemInstance;
        MOEAD.SetOutputDirectory(rutaSalida);

        if (userPop > 0) MOEAD.SetPopulationSize(userPop);
        if (userNeighbor > 0) MOEAD.SetNeighborhoodSize(userNeighbor);
        if (userNeighborPct > 0.0) MOEAD.SetNeighborhoodSizePct(userNeighborPct);

        MOEAD.SetInitDistributionStrategy(initDist);
        MOEAD.SetPowerExp(powerExp);
        MOEAD.SetNoisePct(noisePct);
        
        MOEAD.InitializeParameter(); 
        
        populationSize = MOEAD.s_PopulationSize;
        neighborSize = MOEAD.s_NeighborhoodSize;
    }
    else if (algName == "MOEAD-DE") {
        // Repetir lógica para DE si es necesario
        MOEAD_DE.problemInstance = problemInstance;
        // MOEAD_Differential.InitializeParameter(); 
    }

    int finalPop = (algName == "MOEAD") ? MOEAD.s_PopulationSize : 0; // Ajustar para DE
    int finalNeighbor = (algName == "MOEAD") ? MOEAD.s_NeighborhoodSize : 0;

    std::string strDecomp = "Desconocido";
    if (decompType == 1) strDecomp = "Tchebycheff (TCH)";
    else if (decompType == 2) strDecomp = "TCH Modificado";
    else if (decompType == 3) strDecomp = "PBI (Penalty-based Boundary)";

    std::string strSave = (saveInterval > 0) ? "Cada " + std::to_string(saveInterval) + " gens" : "Solo Inicio/Fin";

    // 3. IMPRESIÓN DEL RESUMEN UNIFICADO
    std::cout << "\n==========================================================" << std::endl;
    std::cout << "               REPORTE DE EJECUCIÓN MOEAD                 " << std::endl;
    std::cout << "==========================================================" << std::endl;
    
    std::cout << " [1] INFORMACIÓN DE LA INSTANCIA" << std::endl;
    std::cout << "     Archivo       : " << bname << std::endl;
    std::cout << "     Tiempo Lectura: " << read_duration << " s" << std::endl;
    problemInstance->printAll(); 

    std::cout << "\n [2] CONFIGURACIÓN DEL ALGORITMO" << std::endl;
    std::cout << "     Algoritmo     : " << algName << std::endl;
    std::cout << "     Tipo Problema : " << problemType << std::endl;
    std::cout << "     Variante      : " << variant << (variant == "relocation" ? " (Flexible)" : " (Fija)") << std::endl;
    std::cout << "     Semilla (Seed): " << rnd_uni_seed << std::endl;
    std::cout << "     Población     : " << finalPop << (userPop > 0 ? " (Manual)" : " (Archivo)") << std::endl;
    std::cout << "     Vecindario (T): " << finalNeighbor;
    if (userNeighborPct > 0.0) {
        std::cout << " (Calc. " << userNeighborPct * 100.0 << "%)";
    } else if (userNeighbor > 0) {
        std::cout << " (Manual Fijo)";
    } else {
        std::cout << " (Archivo)";
    }
    std::cout << std::endl;
    std::cout << "     N de variables: " << NumberOfVariables << std::endl;
    std::cout << "     Decomposition : " << strDecomp << " (" << decompType << ")" << std::endl;
    
    std::cout << "\n [3] CRITERIOS DE PARADA" << std::endl;
    std::cout << "     Evaluaciones  : " << NumberOfFuncEvals << std::endl;
    std::cout << "     Tiempo Máx    : " << (maxTime > 0 ? std::to_string(maxTime) + " s" : "Sin Límite") << std::endl;

    std::cout << "\n [4] PARÁMETROS EVOLUTIVOS" << std::endl;
    std::cout << "     Mutación Global : " << mutationRate * 100.0 << "%" << std::endl;
    std::cout << "     Mutation Type   : " << mutType << std::endl; 
    std::cout << "       -> Pct Delete : " << userMutPctDelete * 100.0 << "%" << std::endl;
    std::cout << "       -> Pct Swap   : " << userMutPctSwap * 100.0 << "%" << std::endl;
    std::cout << "       -> Bit Prob   : " << bitFlipProb << std::endl;

    std::cout << "     Prob. Op1 (Del) : " << op1Prob * 100.0 << "%" << std::endl;
    std::cout << "     Prob. Op2 (Swap): " << (1.0 - op1Prob) * 100.0 << "%" << std::endl;
    std::cout << "     Cruzamiento     : " << crossoverRate * 100.0 << "%" << std::endl;
    std::cout << "     Crossover Type  : " << crossType << std::endl;
    
    std::cout << "\n [5] SALIDA DE DATOS" << std::endl;
    std::cout << "     Destino       : " << rutaSalida << std::endl;
    std::cout << "     Intervalo     : " << strSave << std::endl; 

    std::cout << "\n [6] CONFIGURACIÓN INICIALIZACIÓN (RELOCACIÓN)" << std::endl;
    std::cout << "     Tipo de inicio: " << initTypeRelocation << std::endl;
    std::cout << "     Exp           : " << probMoveRelocation << std::endl;
    std::cout << "     Ruido Pct     : " << splitPctRelocation << std::endl;

    std::cout << "\n [7] ESTRATEGIA DE DISTRIBUCIÓN INICIAL" << std::endl;
    std::cout << "     Estrategia    : " << initDist;
    if (initDist == 0) std::cout << " (Random Puro)";
    else if (initDist == 1) std::cout << " (Random c/ Extremos)";
    else if (initDist == 2) std::cout << " (Exponencial c/ Ruido)";
    std::cout << std::endl;
    
    if (initDist == 2) {
        std::cout << "     Exponente (p) : " << powerExp << std::endl;
        std::cout << "     Ruido (%)     : " << noisePct * 100.0 << "%" << std::endl;
    }
    std::cout << "==========================================================\n" << std::endl;

	clock_t start, temp, finish;
	double last = 0;
	start = clock();

	std::fstream fout;

	if (algName == "MOEAD")  
	{
		MOEAD.SetMutationRate(mutationRate);
        MOEAD.SetCrossoverRate(crossoverRate);
        MOEAD.SetOp1MutationProb(op1Prob);
        MOEAD.SetProblemType(problemType);
        MOEAD.SetVariant(variant); // Configura m_IsRelocation internamente
        MOEAD.SetOutputDirectory(rutaSalida);
        MOEAD.SetMaxTime(maxTime);
        MOEAD.SetDecompositionType(decompType);
        MOEAD.SetSaveInterval(saveInterval);
        MOEAD.SetMutationType(mutType);
        MOEAD.SetCrossoverType(crossType);
        MOEAD.SetMutationPercentage(mutPct);
        MOEAD.SetBitFlipProb(bitFlipProb);
        MOEAD.SetMutPctDelete(userMutPctDelete);
        MOEAD.SetMutPctSwap(userMutPctSwap);
        MOEAD.SetNeighborhoodSizePct(userNeighborPct);

        MOEAD.SetInitializationTypeRelocation(initTypeRelocation);
        MOEAD.SetProbChooseMoveRelocation(probMoveRelocation);
        MOEAD.SetSplitPctRelocation(splitPctRelocation);

    

        
		MOEAD.Execute(1); // Se ejecuta solo una vez
	}

	if (algName == "MOEAD-DE")
	{
		MOEAD_DE.Execute(1); // Se ejecuta solo una vez
	}

	finish = clock(); // Tiempo final
	double duration = static_cast<double>(finish - start) / CLOCKS_PER_SEC;

	// Mostrar por consola
	std::cout << "\n------------------------------------------------" << std::endl;
    std::cout << " ESTADO FINAL: TERMINADO" << std::endl;
    if (maxTime > 0 && duration >= maxTime) std::cout << " NOTA: Detenido por Límite de Tiempo." << std::endl;
    std::cout << " Tiempo Total: " << duration << " segundos." << std::endl;
    std::cout << "------------------------------------------------" << std::endl;

	// Guardar en archivo
	char timeLogFilename[1024];
	sprintf(timeLogFilename, "%s/execution_log.csv", exe_dir_path.c_str());
    bool writeHeader = false;
    std::ifstream checkFile(timeLogFilename);
    if (!checkFile.good() || checkFile.peek() == std::ifstream::traits_type::eof()) writeHeader = true;
    checkFile.close();

	std::ofstream fout_time(timeLogFilename, std::ios::app);
        if (writeHeader) fout_time << "Instance,Alg,Type,Variant,Pop,Neigh,NVars,NEvals,MaxTime,Seed,Mut,Op1,Cross,DecomType,SaveInterval,Time_s,OutDir" << std::endl;

	fout_time << bname << "," << algName << "," << problemType << "," << variant << ","
              << finalPop << "," << finalNeighbor << "," << NumberOfVariables << ","
              << NumberOfFuncEvals << "," << maxTime << "," << rnd_uni_seed << "," 
              << mutationRate << "," << op1Prob << "," << crossoverRate << "," 
              << decompType << "," << saveInterval << ","
              << duration << "," << rutaSalida << std::endl;
	fout_time.close();

	std::cout << "Log guardado en execution_log.csv" << std::endl;

	std::cout << "Done!" << std::endl;
	free(basec);

	return 0;
}

void ResetRandSeed()
{

	rnd_uni_seed = (rnd_uni_seed + 23) % 1377;
	rnd_uni_init = -(long)rnd_uni_seed;
}
