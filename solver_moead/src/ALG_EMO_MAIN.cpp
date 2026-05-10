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
#include <iomanip>

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

// helpers

static std::string pct(double x) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2) << (x * 100.0) << "%";
    return oss.str();
}

static std::string dbl(double x, int prec=6) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(prec) << x ;
    return oss.str();
}
// Mutation
static std::string MutName(int mutType, bool isReloc){
    if (!isReloc) {
        switch(mutType){
            case 1: return "Mutacion modificada (sin reubicacion) (op1)";
            case 2: return "SwapBitFlip (p = ProbSwap)";
            case 3: return "Swap% (mutPctSwap)";
            case 4: return "Delete% (mutPctDelete)";
            case 5: return "BitFlip (p = 1/N)";
            case 6: return "BitFlip (p = 1/M)";
            case 7: return "BitFlip (p = fijo = bitprob)";
            case 8: return "Fusion (Swap% + BitFlip p = 1/N) (op1)";
            case 9: return "Fusion (Swap% + BitFlip p = 1/M) (op1)";
            case 10: return "Fusion (Swap% + BitFlip p = fijo) (op1)";
            case 11: return "Hibrida (Delete%/Swap%) (op1)";
            default: return "DEFAULT -> BitFlip (p = fijo)";
        }
    } else {
        switch(mutType) {
            case 12: return "Mutacion modificada (con reubicacion) (op1)";
            case 13: return "SwapBitFlip Reloc (p = ProbSwap)";
            case 14: return "Swap% Reloc (mutPctSwap)";
            case 15: return "Delete% Reloc (mutPctDelete)";
            case 16: return "BitFlip Reloc (p = 1/N)";
            case 17: return "BitFlip Reloc (p = 1/M)";
            case 18: return "BitFlip Reloc (p = fijo = bitprob)";
            case 19: return "Fusion Reloc (Swap% Reloc + BitFlip Reloc p = 1/N) (op1)";
            case 20: return "Fusion Reloc (Swap% Reloc + BitFlip Reloc p = 1/M) (op1)";
            case 21: return "Fusion Reloc (Swap% Reloc + BitFlip Reloc p = fijo) (op1)";
            case 22: return "Hibrida Reloc (Delete% Reloc/Swap% Reloc) (op1)";
            default: return "DEFAULT -> BitFlip Reloc (p = 1/M)";
        }
    }
}

static std::vector<std::string> MutParamsLines(
    int mutType, bool isReloc, double mutationRate, double op1Prob, double mutPctDelete, double mutPctSwap,
    double ProbSwap, double bitFlipProb, int popSize, int nVars
){
    std::vector<std::string> L;
    L.push_back("Tasa global (mut)       : " + pct(mutationRate));

    auto add_op1       = [&](){ L.push_back("Prob op1: " + pct(op1Prob) + "            Prob op2 (1 - op1): " + pct(1-op1Prob) ); };
    auto add_pct_del   = [&](){ L.push_back("mutPctDelete            : " + pct(mutPctDelete)); };
    auto add_pct_swap  = [&](){ L.push_back("mutPctSwap              : " + pct(mutPctSwap)); };
    auto add_prob_swap = [&](){ L.push_back("ProbSwap                : " + pct(ProbSwap)); };
    auto add_bit       = [&](){ L.push_back("bitprob (p fijo)        : " + dbl(bitFlipProb, 6)); };
    auto add_p_1N      = [&](){
        double p = (nVars > 0) ? (1.0 / (double)nVars) : 0.0; 
        L.push_back("p usado     : 1/N = " + dbl(p, 10) + " (N=" + std::to_string(nVars) + ")"); };
    
    auto add_p_1M      = [&](){
        double p = (popSize > 0) ? (1.0 / (double)popSize) : 0.0; 
        L.push_back("p usado     : 1/M = " + dbl(p, 10) + " (M=" + std::to_string(popSize) + ")"); };

    if (!isReloc) {
        switch(mutType) {
            case 1: add_op1(); break;
            case 2: add_prob_swap(); break;
            case 3: add_pct_swap(); break;
            case 4: add_pct_del(); break;
            case 5: add_p_1N(); break;
            case 6: add_p_1M(); break;
            case 7: add_bit(); break;
            case 8: add_op1(); add_pct_swap(); add_p_1N(); break;
            case 9: add_op1(); add_pct_swap(); add_p_1M(); break;
            case 10: add_op1(); add_pct_swap(); add_bit(); break;
            case 11: add_op1(); add_pct_del(); add_pct_swap(); break;
            default: add_bit(); break;
        }
    } else {
        switch(mutType) {
            case 12: add_op1(); break;
            case 13: add_prob_swap(); break;
            case 14: add_pct_swap(); break;
            case 15: add_pct_del(); break;
            case 16: add_p_1N(); break;
            case 17: add_p_1M(); break;
            case 18: add_bit(); break;
            case 19: add_op1(); add_pct_swap(); add_p_1N(); break;
            case 20: add_op1(); add_pct_swap(); add_p_1M(); break;
            case 21: add_op1(); add_pct_swap(); add_bit(); break;
            case 22: add_op1(); add_pct_del(); add_pct_swap(); break;
            default: add_p_1M(); break;
        }
    }

    return L;
}

// Crossover

static std::string CrossName(int crossType, bool isReloc){
    if (!isReloc) {
        switch(crossType){
            case 1: return "Uniforme modificado (sin reubicacion)";
            case 2: return "Uniforme inteligente";
            case 3: return "Uniforme";
            case 4: return "One-point crossover";
            case 5: return "Two-point crossover";
            default: return "DEFAULT -> Uniforme";
        }
    } else {
        switch(crossType){
            case 6: return "Uniforme modificado (con reubicacion)";
            case 7: return "Uniforme inteligente Reloc";
            case 8: return "Uniforme";
            case 9: return "One-point crossover Reloc";
            case 10: return "Two-point crossover Reloc";
            case 11: return "Uniforme Geografico Reloc";
            default: return "DEFAULT -> Uniforme";
        }
    }
}

// Distribucion inicial
static std::string InitDistName(int initDist){
    switch(initDist){
        case 0: return "Aleatoria Uniforme - U(0, P)";
        case 1: return "Aleatoria Normal - N(P/2, P/6) truncada a [0, P]";
        case 2: return "Aleatoria Normal con extremos anclados a 0 y P";
        case 3: return "Curva exponencial + ruido";
        default: return "Desconocida";
    }
}

static std::vector<std::string> InitDistParamsLines(int initDist, double powerExp, double noisePct){
    std::vector<std::string> L;
    L.push_back("Estrategia (initDist): " + std::to_string(initDist) + " (" + InitDistName(initDist) + ")");
    if (initDist == 3){
        L.push_back("powerExp       : " + dbl(powerExp, 3));
        L.push_back("noisePct       : " + pct(noisePct));
    }
    return L;
}

// relocation initialization 
static std::string InitRelocName(int t){
    switch(t){
        case 1: return "OnlyMove (deterministico)";
        case 2: return "OnlyBuy (deterministico)";
        case 3: return "Choose Move/Buy (probMoveRelocation)";
        case 4: return "HybridCount (splitPctRelocation)";
        case 5: return "HybridSplit (splitPctRelocation)";
        case 6: return "OnlyMove (aleatorio)";
        case 7: return "OnlyBuy (aleatorio)";
        case 8: return "Choose Move/Buy (aleatorio) (probMoveRelocation)";
        case 9: return "HybridSplit (aleatorio) (splitPctRelocation)";
        case 10: return "Random instala pre mas una cantidad aleatoria";
        case 11: return "Random instala de 0 a total nodos incremental";
        case 12: return "BalancedQuantity incremental (splitPctRelocation)";
        case 13: return "Greedy incremental (factor aleatoriedad)";
        default: return "DEFAULT -> OnlyBuy (deterministico)";
    }
}

static std::vector<std::string> InitRelocParamsLines(int t, double probMoveRelocation, double splitPctRelocation){
    std::vector<std::string> L;
    L.push_back("initTypeRelocation      : " + std::to_string(t) + " (" + InitRelocName(t) + ")");

    if (t == 3 || t == 8){
        L.push_back("probMoveRelocation     : " + pct(probMoveRelocation));
    }
    if (t == 4 || t == 5 || t == 9 || t == 12){
        L.push_back("splitPctRelocation     : " + pct(splitPctRelocation));
    }
    return L;
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
    std::cout << "  -mutProbSwap <double> : Probabilidad individual para Swap Probabilistico (Def: 0.05)" << std::endl;
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
    
	NumberOfObjectives = 2;
    NumberOfFuncEvals = 40000; 

    std::string variant = "location"; // o "relocation"
    std::string problemType = "cam";  // o "drp"
    std::string algName = "MOEAD";

    double maxTime = 0; 

    std::string userOutputDir = ""; 

    // Parámetros Algoritmo
    double bitFlipProb = 0.001; // Default: 1% probabilidad para BitFlip Fijo
    double crossoverRate = 0.8;
    int crossType = 7;    // Default: Inteligente
    int initDist = 2;
    int initTypeRelocation = 3;           // Default: Solo Mover (o el que prefieras como base)
    double mutationRate = 0.9;

    double mutPct = 0.4; // Default: 5% intensidad para operadores porcentuales
    double userMutPctDelete = 0.25; // 0 = usar default
    double userMutPctSwap = 0.4;   // 0 = usar default

    double userMutProbSwap = 0.15;
    int mutType = 12;     // Default: Híbrida
    double userNeighborPct = 0.0; // 0 = usar archivo, >0 usar porcentaje
    double noisePct = 0.1;
    double op1Prob = 0.5; // 20% delete, 80% swap (por ejemplo)
    double powerExp = 1.0;
    double probMoveRelocation = 0.4;      // Default: 50%
    double splitPctRelocation = 0.5;      // Default: 50% split


    int decompType = 1;   // 1 por defecto (Tchebycheff)
    int saveInterval = 0; // 0 por defecto (Solo guarda Gen 0 y Gen Final)

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
        else if (arg == "-mutProbSwap") { if (i + 1 < argc) userMutProbSwap = atof(argv[++i]); }

        else if (arg == "-initTypeRelocation") { if (i + 1 < argc) initTypeRelocation = atoi(argv[++i]); }
        else if (arg == "-probMoveRelocation") { if (i + 1 < argc) probMoveRelocation = atof(argv[++i]); }
        else if (arg == "-splitPctRelocation") { if (i + 1 < argc) splitPctRelocation = atof(argv[++i]); }

        else if (arg == "-initDist") { if (i + 1 < argc) initDist = atoi(argv[++i]); }
        else if (arg == "-powerExp") { if (i + 1 < argc) powerExp = atof(argv[++i]); }
        else if (arg == "-noisePct") { if (i + 1 < argc) noisePct = atof(argv[++i]); }
    }

    if (userMutPctDelete < 0) userMutPctDelete = mutPct;
    if (userMutPctSwap < 0)   userMutPctSwap = mutPct;

    bool isRelocation = (variant == "relocation");


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

    std::cout << "\n [4] OPERADORES  (MUTACION /CRUZAMIENTO)" << std::endl;

    std::cout << "     Mutacion Type: " << mutType << " (" << MutName(mutType, isRelocation) << ")" << std::endl;
    
    auto mutLines = MutParamsLines(
        mutType, isRelocation, mutationRate, op1Prob, userMutPctDelete, userMutPctSwap, userMutProbSwap,
        bitFlipProb, finalPop, NumberOfVariables
    );
    for (const auto &ln : mutLines) {
        std::cout << "      - " << ln << std::endl;
    }

    std::cout << "     Crossover Type  : " << crossType << " (" << CrossName(crossType, isRelocation) << ")" << std::endl;
    std::cout << "     Cruzamiento     : " << pct(crossoverRate) << std::endl;
    
    std::cout << "\n [5] SALIDA DE DATOS" << std::endl;
    std::cout << "     Destino       : " << rutaSalida << std::endl;
    std::cout << "     Intervalo     : " << strSave << std::endl; 

    std::cout << "\n [6] INICIALIZACIÓN (SOLO RELOCACIÓN)" << std::endl;
    if (isRelocation) {
        auto initRelLines = InitRelocParamsLines(initTypeRelocation, probMoveRelocation, splitPctRelocation);
        for (const auto &ln : initRelLines){
            std::cout << "     " << ln << std::endl;
        }
    } else {
        std::cout << "    (N/A) Variante = location (no aplica initTypeRelocation)" << std::endl;
    } 

    std::cout << "\n [7] DISTRIBUCIÓN INICIAL DE #AEDs (initDist)" << std::endl;
    auto initDistLines = InitDistParamsLines(initDist, powerExp, noisePct);
    for (const auto &ln : initDistLines) {
        std::cout << "     " << ln << std::endl;
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
        MOEAD.SetMutProbSwap(userMutProbSwap);
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
