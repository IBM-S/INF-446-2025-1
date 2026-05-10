#include "ALG_EMO_MOEAD.h"
#include <string.h>
#include <cmath>
#include <iomanip>
#include <random>

CALG_EMO_MOEAD::CALG_EMO_MOEAD(void)
{
	s_PBI_type = 1;
	m_MutationRate = 0.4;
    m_CrossoverRate = 0.7;
    m_Op1MutationProb = 0.5;
    m_IsRelocation = true; // Por defecto Location (fijo)
    m_ProblemType = "cam";
	s_PopulationSize = 0;
    s_NeighborhoodSize = 0;
	m_MaxTimeSeconds = 0; // Sin límite por defecto
	m_SaveInterval = 0;

	m_MutationType = 11;      // Híbrida por defecto
    m_CrossoverType = 3;     // Inteligente por defecto
    m_MutationPercentage = 0.05; 
    m_BitFlipProb = 0.001;

	m_MutPctDelete = 0.25; // 5% por defecto
	m_MutPctSwap   = 0.40; // 5% por defecto
	m_MutProbSwap  = 0.15;

	m_NeighborhoodSizePct = 0.0;

	m_InitDistributionStrategy = 2;
	m_PowerExp = 1.0;
	m_NoisePct = 0.1;
}

CALG_EMO_MOEAD::~CALG_EMO_MOEAD(void)
{
}

void CALG_EMO_MOEAD::Execute(int run_id)
{

	//this->InitializeParameter();
	this->InitializePopulation();
	this->InitializeNeighborhood();

	clock_t start_clock = clock();

	printf("Instance:  %s  RUN:  %d  GEN = 0 (Inicio)\n", strTestInstance, run_id);
	this->SavePopulation(0);

	printf("\n================================================\n");
    printf("  RESUMEN DE OPTIMIZACIÓN (Inicio)\n");
    printf("================================================\n");
    printf("  Punto      |  f1 (Obj 1)   |  f2 (Obj 2)\n");
    printf("  -----------|---------------|---------------\n");
    printf("  Nadir      |  %-12.7f |  %-12.1f\n", v_NadirPoint[0], v_NadirPoint[1]);
    printf("  Ideal      |  %-12.7f |  %-12.1f\n", v_IdealPoint[0], v_IdealPoint[1]);
    printf("================================================\n");

	int gen = 1;

	for (;;)
	{
		this->EvolvePopulation();

		if (m_SaveInterval > 0 && (gen % m_SaveInterval == 0)) 
        {
            printf("Instance:  %s  RUN:  %d  GEN = %d\n", strTestInstance, run_id, gen);
            this->SavePopulation(gen);
        }

		if (IsTerminated())
		{
			break;
		}

		if (m_MaxTimeSeconds > 0) {
            double elapsed = (double)(clock() - start_clock) / CLOCKS_PER_SEC;
            if (elapsed >= m_MaxTimeSeconds) {
                printf(">>> TIMEOUT ALCANZADO (%g s). Deteniendo en Gen %d.\n", elapsed, gen);
                break; // Salir del bucle
            }
        }

		gen++;
	}
	printf("Instance:  %s  RUN:  %d  GEN = %d (Final)\n", strTestInstance, run_id, gen);
	this->SavePopulation(gen);
	this->SaveFinalPopulation();

	printf("\n================================================\n");
    printf("  RESUMEN DE OPTIMIZACIÓN (Final)\n");
    printf("================================================\n");
    printf("  Punto      |  f1 (Obj 1)   |  f2 (Obj 2)\n");
    printf("  -----------|---------------|---------------\n");
    printf("  Nadir      |  %-12.7f |  %-12.1f\n", v_NadirPoint[0], v_NadirPoint[1]);
    printf("  Ideal      |  %-12.7f |  %-12.1f\n", v_IdealPoint[0], v_IdealPoint[1]);
    printf("================================================\n");

	m_PopulationSOP.clear();
	v_IdealPoint.clear();

	// numero total de gen
	std::cout << "Total de generaciones: " << gen << std::endl;
}

void CALG_EMO_MOEAD::InitializeNeighborhood()
{
	vector<double> v_dist = vector<double>(s_PopulationSize, 0);
	vector<int> v_indx = vector<int>(s_PopulationSize, 0);

	unsigned int i, j, k;
	for (i = 0; i < s_PopulationSize; i++)
	{
		for (j = 0; j < s_PopulationSize; j++)
		{
			v_dist[j] = UtilityToolBox.DistanceVectorNorm2(m_PopulationSOP[i].v_Weight_Vector,
														   m_PopulationSOP[j].v_Weight_Vector);
			v_indx[j] = j;
		}

		UtilityToolBox.Minfastsort(v_dist,
								   v_indx,
								   s_PopulationSize,
								   s_NeighborhoodSize);

		for (k = 0; k < s_NeighborhoodSize; k++)
		{
			m_PopulationSOP[i].v_Neighbor_Index.push_back(v_indx[k]); // save the indexes into neighborhood
		}
	}
	v_dist.clear();
	v_indx.clear();
}

void CALG_EMO_MOEAD::InitializeParameter()
{
	char filename[1024];

	//sprintf(filename, "SETTINGS/algorithms/MOEAD.txt");
	sprintf(filename, "%s/SETTINGS/algorithms/MOEAD.txt", exe_dir_path.c_str());

	// --- DEBUG: Avisar qué estamos buscando ---
	// std::cout << ">>> Leyendo configuracion desde: " << filename << std::endl;

	std::ifstream readf(filename);
	
	// --- VALIDACIÓN DE APERTURA ---
	if (!readf.is_open()) {
		std::cerr << "\n=======================================================" << std::endl;
		std::cerr << " ERROR FATAL: No se pudo abrir el archivo de configuración." << std::endl;
		std::cerr << " Ruta intentada: " << filename << std::endl;
		std::cerr << " Verifica que la carpeta SETTINGS este junto al ejecutable." << std::endl;
		std::cerr << "=======================================================\n" << std::endl;
		exit(1); // Detener programa con error
	} 

	int filePop, fileNeighbor;
		readf >> filePop;
		readf >> fileNeighbor;
		readf.close();
	
	if (s_PopulationSize == 0) {
        // No se pasó por consola, usamos el del archivo
        s_PopulationSize = filePop;
    } 
    // Si s_PopulationSize > 0, significa que se usó -pop, así que ignoramos filePop

	if (m_NeighborhoodSizePct > 0) {
		if (m_NeighborhoodSizePct > 1.0) m_NeighborhoodSizePct = 1.0; // Limitar a 100%
		// Se pasó un porcentaje, calcular tamaño del vecindario
		s_NeighborhoodSize = (int) std::ceil(s_PopulationSize * m_NeighborhoodSizePct);
		//printf(">>> Vecindario calculado por porcentaje (%g%%): %d\n", m_NeighborhoodSizePct * 100.0, s_NeighborhoodSize);
	} else if (s_NeighborhoodSize > 0) {
		// Ya fue definido en el Main
		//printf(">>> Vecindario fijo manual: %d\n", s_NeighborhoodSize);
	} else {
		// Usamos el del archivo
		s_NeighborhoodSize = fileNeighbor;
	}


	// Pop_Size     NeighborhoodSize
	//readf >> s_PopulationSize;
	//readf >> s_NeighborhoodSize;
	//readf.close();
}

void CALG_EMO_MOEAD::UpdateReference(vector<double> &obj_vect)
{
	for (unsigned n = 0; n < NumberOfObjectives; n++)
	{
		if (obj_vect[n] < v_IdealPoint[n])
		{
			v_IdealPoint[n] = obj_vect[n];
		}
	}
}

void CALG_EMO_MOEAD::InitializePopulation()
{
	unsigned i, j;

	s_Fevals_Count = 0;

	v_IdealPoint = vector<double>(NumberOfObjectives, 1.0e+30);

	char filename1[1024];
	//sprintf(filename1, "SETTINGS/weightvectors/W%dD_%d.dat", NumberOfObjectives, s_PopulationSize);
	
	sprintf(filename1, "%s/SETTINGS/weightvectors/W%dD_%d.dat", exe_dir_path.c_str(), NumberOfObjectives, s_PopulationSize);
	//std::cout << ">>> Cargando vectores de peso desde: " << filename1 << std::endl;

	std::ifstream readf(filename1);

	if (!readf.is_open())
	{
		std::cerr << "\n=======================================================" << std::endl;
		std::cerr << " ERROR FATAL: No se encontró el archivo de vectores de peso." << std::endl;
		std::cerr << " Ruta intentada: " << filename1 << std::endl;
		std::cerr << " Revisa que exista W" << NumberOfObjectives << "D_" << s_PopulationSize << ".dat en SETTINGS/weightvectors/" << std::endl;
		std::cerr << "=======================================================\n" << std::endl;
		exit(1); // Detener programa
	}

	//std::cout << "    Archivo de pesos encontrado. Inicializando poblacion..." << std::endl;

	const auto &nodos = this->problemInstance->getNodes();
	int total_nodos = nodos.size();
	int presupuesto = this->problemInstance->getP();

	auto ImprimirConteo = [&](const vector<double>& v, std::string label) {
        int pre = 0;           
        int inst = 0;          
        int moved_out = 0;     

        double c1 = this->problemInstance->getC1(); 
        double c2 = this->problemInstance->getC2(); 
        int max_P = this->problemInstance->getP();

        for(size_t k=0; k<v.size(); ++k) {
            bool is_active = (v[k] > 0.5);
            bool is_pre = (nodos[k]->getFlag() == 1);

            if(is_active) {
                if(is_pre) pre++;
                else inst++;
            }
            if(is_pre && !is_active) {
                moved_out++;
            }
        }
        
        int n_movidos = std::min(inst, moved_out);
        int n_nuevos = inst - n_movidos;
        double costo_total = (n_nuevos * c1) + (n_movidos * c2);
        std::string estado = (costo_total > max_P) ? "[VIOLA]" : "[OK]";
        
        std::cout << std::setw(20) << std::left << label 
                  << "| Pre: " << std::setw(4) << pre 
                  << "| Inst: " << std::setw(4) << inst 
                  << "(Mov:" << std::setw(3) << n_movidos << " New:" << std::setw(3) << n_nuevos << ") "
                  << "| Tot: " << std::setw(4) << (pre+inst)
                  << "| Costo: " << std::setw(6) << std::fixed << std::setprecision(1) << costo_total 
                  << " / " << max_P << " " << estado << std::endl;
    };

	int aeds_preinstalados = 0;
	for (const auto &nodo : nodos) if (nodo->getFlag() == 1) aeds_preinstalados++;
	int huecos_disponibles = total_nodos - aeds_preinstalados;

	// Configuracion estrategia de distribucion
	// 0: Aleatorio Uniforme entre 0 y max permitido
	// 1: Aleatoria Normal N(mu = max/2, sigma = max/6) 
	// 2: Normal con extremos anclados (0 y max)
	// 3: exponencial con ruido
	//int m_InitDistributionStrategy = 2;
	//double m_PowerExp = 5.0;   //(1.0 linspace, 3.0, curva agresiva)
	//double m_NoisePct = 0.20;  // Para el ruido

	bool useFullRange = false;
	if (this->m_InitializationTypeRelocation == 10) useFullRange = true;

	for (i = 0; i < s_PopulationSize; i++)
	{
		CSubProblemBase SP;
		SP.m_BestIndividual.problemInstance = this->problemInstance;

		

		int max_limit = 0;
		
		
		if (useFullRange) {
			// Modo full range: desde 0 hasta todos los nodos
			max_limit = total_nodos;
			printf("Limite full range true\n");
		} else {
			// Modo normal: limitado por presupuesto o huecos disponibles
		if (m_IsRelocation) {
			max_limit = presupuesto;
			//printf("Limite relocation %d\n", max_limit);
		} else {
			max_limit = (presupuesto < huecos_disponibles) ? presupuesto : huecos_disponibles;
			//printf("presupuesto %d      huecos disponibles %d\n", presupuesto, huecos_disponibles);
			//printf("Limite location %d\n", max_limit);
		}}


		// Calcular la cantidad a usar
		int nums_AEDs_instalar = 0;

		if (m_InitDistributionStrategy == 0){
			// Una cantidad aleatoria entre 0 y el máximo permitido
			nums_AEDs_instalar = rand() % (max_limit + 1);

		} else if (m_InitDistributionStrategy == 1) {
			// Normal sin extremos: N(mu = P/2, sigma = P/6) pero con extremos fijos en 0 y max_limit
			std::mt19937 rng(rand());
			std::normal_distribution<double> dist((double)max_limit / 2.0, (double)max_limit / 6.0);
			double muestra;
			int intentos = 0;
			do {
				muestra = dist(rng);
				intentos++;
			} while ((muestra < 0 || muestra > max_limit) && intentos < 100); 
			muestra = std::max(0.0, std::min((double)max_limit, muestra)); // Clamping final 
			nums_AEDs_instalar = (int)std::round(muestra);
			
		} else if (m_InitDistributionStrategy == 2){
			// Normal con extremos anclados
			if (i == 0) {
				nums_AEDs_instalar = 0;
			} else if (i == s_PopulationSize - 1) {
				nums_AEDs_instalar = max_limit;
			} else {
				std::mt19937 rng(rand());
				std::normal_distribution<double> dist((double)max_limit / 2.0, (double)max_limit / 6.0);
				double muestra;
				int intentos = 0;
				do {
					muestra = dist(rng);
					intentos++;
				} while ((muestra < 0 || muestra > max_limit) && intentos < 100); 
				muestra = std::max(0.0, std::min((double) max_limit, muestra)); // Clamping final 
				nums_AEDs_instalar = (int)std::round(muestra);
			}
		} else if (m_InitDistributionStrategy == 3) {
			// Exponencial con ruido, pero con extremos fijos en 0 y max_limit
			if (i == 0) {
				nums_AEDs_instalar = 0;
			} else if (i == s_PopulationSize - 1) {
				nums_AEDs_instalar = max_limit;
			} else {
				// a. Posición normalizada (0 a 1)
				double t = (double)i / (double)(s_PopulationSize - 1);

				// b. curva
				double base = std::pow(t, m_PowerExp) * (double)max_limit;
				
				// c. Ruido
				double rango = base * m_NoisePct;
				double aleatorio = ((double)rand() / (double) RAND_MAX) * 2.0 - 1.0;
				double resultado = base + (rango * aleatorio);

				// d. Clampling
				if (resultado < 1.0) resultado = 1.0;
				if (resultado > max_limit) resultado = (double)max_limit;

				nums_AEDs_instalar = (int)resultado;
			} 
		}

		//printf("Indiv %d: Estrategia %d -> Cantidad %d (Max %d)\n", i, m_InitDistributionStrategy, nums_AEDs_instalar, max_limit);

		bool log_initialization = false;
		if (m_IsRelocation) {
			switch (this->m_InitializationTypeRelocation) {
				case 1:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_OnlyMove(nums_AEDs_instalar);
					if (log_initialization) printf("1    relocation initialization\n");
					break;
				case 2:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_OnlyBuy(nums_AEDs_instalar);
					if (log_initialization) printf("2    relocation initialization\n");
					break;
				case 3:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_Choose_Move_or_Buy(nums_AEDs_instalar, this->m_ProbChooseMoveRelocation);
					if (log_initialization) printf("3    relocation initialization\n");
					break;
				case 4:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_HybridCount(nums_AEDs_instalar, this->m_SplitPctRelocation);
					if (log_initialization) printf("4    relocation initialization\n");
					break;
				// Las siguientes son funciones de prueba que ya no se utilizan en los experimentos finales, pero las dejo por si quiero hacer debug o análisis adicionales.
				case 5:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_HybridSplit(nums_AEDs_instalar, this->m_SplitPctRelocation);
					if (log_initialization) printf("5    relocation initialization\n");
					break;
				case 6:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_OnlyMove_Aleatorio(nums_AEDs_instalar);
					if (log_initialization) printf("6    relocation initialization\n");
					break;
				case 7:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_OnlyBuy_Aleatorio(nums_AEDs_instalar);
					if (log_initialization) printf("7    relocation initialization\n");
					break;
				case 8:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_Choose_Move_or_Buy_Aleatorio(nums_AEDs_instalar, this->m_ProbChooseMoveRelocation);
					if (log_initialization) printf("8    relocation initialization\n");
					break;
				case 9:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_HybridSplit_Aleatorio(nums_AEDs_instalar, this->m_SplitPctRelocation);
					if (log_initialization) printf("9    relocation initialization\n");
					break;
				case 10:
					SP.m_BestIndividual.GenerateSimpleFeasible_Random(nums_AEDs_instalar, aeds_preinstalados);
					if (log_initialization) printf("10    relocation initialization\n");
					break;
				case 11:
					SP.m_BestIndividual.GenerateRandomFullRange(nums_AEDs_instalar);
					if (log_initialization) printf("11    relocation initialization\n");
					break;
				case 12:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_BalancedQuantity(nums_AEDs_instalar, this->m_SplitPctRelocation);
					if (log_initialization) printf("12    relocation initialization\n");
					break;
				case 13: {
					double factor = 0.15; // 15% de aleatoriedad
					SP.m_BestIndividual.GenerateGreedyFeasibleSolution(nums_AEDs_instalar, factor);
					if (log_initialization) printf("13    relocation initialization\n");
					break;}
				default:
					SP.m_BestIndividual.GenerateSimpleFeasible_Reloc_OnlyBuy(nums_AEDs_instalar);
					if (log_initialization) printf("default    relocation initialization\n");
					break;
			}
		} else {			
			SP.m_BestIndividual.GenerateSimpleFeasibleSolution(nums_AEDs_instalar);
			if (log_initialization) printf("default location initialization\n");
		}

		if (i < 0) {
             if (i==0) std::cout << "\n--- DEBUG INICIALIZACION (Primeros 5) ---" << std::endl;
             std::string label = "Init Indiv " + std::to_string(i);
             ImprimirConteo(SP.m_BestIndividual.x_var, label);
        }


		// Sin contar el presupuesto
		// SP.m_BestIndividual.GenerateSimpleFeasibleSolution(num_AEDs, huecos_disponibles);
		SP.m_BestIndividual.Evaluate();
		s_Fevals_Count++;

		/* std::cout << "Individuo #" << i << ": ";
		for (double val : SP.m_BestIndividual.x_var)
		{
			std::cout << val << " ";
		}
		std::cout << std::endl;

		std::cout << "f_obj = ";
		for (double f : SP.m_BestIndividual.f_obj)
		{
			std::cout << f << " ";
		}
		std::cout << std::endl; */

		UpdateReference(SP.m_BestIndividual.f_obj); // update reference point

		for (j = 0; j < NumberOfObjectives; j++)
		{
			readf >> SP.v_Weight_Vector[j];
		}

		// SP.Show_Weight_Vector();  	getchar();

		m_PopulationSOP.push_back(SP);
	}

	readf.close();

	this->FindNadirPoint();

	// if(s_PBI_type==3) 	NormalizeWeight();
	
	//std::cout << "    Poblacion inicializada con exito (" << s_PopulationSize << " individuos)." << std::endl;
	//std::cerr << "--------------------------------------------------------\n" << std::endl;
}

void CALG_EMO_MOEAD::FindNadirPoint()
{
	// 1. Inicializamos el Nadir con un valor muy pequeño
	v_NadirPoint = vector<double>(NumberOfObjectives, -1.0e+30);

	// 2. Recorremos toda la población
	for (int i = 0; i < s_PopulationSize; i++)
	{
		for (int j = 0; j < NumberOfObjectives; j++)
		{
			// 3. Buscamos el MÁXIMO valor (el peor) para cada objetivo
			if (m_PopulationSOP[i].m_BestIndividual.f_obj[j] > v_NadirPoint[j])
			{
				v_NadirPoint[j] = m_PopulationSOP[i].m_BestIndividual.f_obj[j];
			}
		}
	}
    
    // DEBUG: Descomenta esto si quieres ver como se corrige en consola
    // printf("DEBUG Nadir Actualizado: %f, %f\n", v_NadirPoint[0], v_NadirPoint[1]);
}

void CALG_EMO_MOEAD::NormalizeWeight()
{

	for (int s = 0; s < s_PopulationSize; s++)
	{
		for (int j = 0; j < NumberOfObjectives; j++)
		{
			m_PopulationSOP[s].v_Weight_Vector2[j] = m_PopulationSOP[s].v_Weight_Vector[j] * (v_NadirPoint[j] - v_IdealPoint[j]);
		}
		UtilityToolBox.NormalizeVector(m_PopulationSOP[s].v_Weight_Vector2);
	}
}

void CALG_EMO_MOEAD::NormalizeIndividual(CIndividualBase &ind)
{
	// ind.Show(1);
	for (int i = 0; i < NumberOfObjectives; i++)
	{
		if (abs(v_NadirPoint[i] - v_IdealPoint[i]) < 1.0e-6)
			ind.f_normal[i] = (ind.f_obj[i] - v_IdealPoint[i]) / 1.0e-6;
		else
			ind.f_normal[i] = (ind.f_obj[i] - v_IdealPoint[i]) / (v_NadirPoint[i] - v_IdealPoint[i] + 1.0e-6);
		// printf("%f ", ind.f_normal[i]);
	}
	// getchar();
}


void CALG_EMO_MOEAD::UpdateNadirPoint(vector<double> &obj_vect)
{
	for (unsigned n = 0; n < NumberOfObjectives; n++)
	{
		if (obj_vect[n] > v_NadirPoint[n])
		{
			v_NadirPoint[n] = obj_vect[n];
		}
	}
}

void CALG_EMO_MOEAD::UpdateProblem_modificado(CIndividualBase &child,
									   unsigned sp_id)
{
	double f1, f2;

	int id1 = sp_id, id2;

	vector<double> norm_child(NumberOfObjectives);
	for(int k = 0;k<NumberOfObjectives;k++)
	{
		double range = v_NadirPoint[k] - v_IdealPoint[k];
		if(range<1.0e-6) range=1.0e-6;
		norm_child[k] = (child.f_obj[k]-v_IdealPoint[k])/range;
	}

	vector<double> zero_point(NumberOfObjectives, 0);



	for (int i = 0; i < s_NeighborhoodSize; i++)
	{

		id2 = m_PopulationSOP[id1].v_Neighbor_Index[i];
		vector<double> norm_parent(NumberOfObjectives);
		for(int k = 0;k<NumberOfObjectives;k++)
		{
			double range = v_NadirPoint[k] - v_IdealPoint[k];
			if(range<1.0e-6) range=1.0e-6;
			norm_parent[k] = (m_PopulationSOP[id2].m_BestIndividual.f_obj[k]-v_IdealPoint[k])/range;
		}

		f1 = UtilityToolBox.ScalarizingFunction(norm_parent,
												m_PopulationSOP[id2].v_Weight_Vector,
												zero_point,
												s_PBI_type); // 1 - TCH  3 - PBI

		f2 = UtilityToolBox.ScalarizingFunction(norm_child,
												m_PopulationSOP[id2].v_Weight_Vector,
												zero_point,
												s_PBI_type);
		
		// print all values for debugging
		//printf("\n\n  Updating Subproblem %d ...\n", id2);
		//printf("obj parent: %f %f", norm_parent[0], norm_parent[1]);
		//printf("vs\n");
		//printf("obj child: %f %f\n", norm_child[0], norm_child[1]);
		//printf("weight vector: %f, %f \n", m_PopulationSOP[id2].v_Weight_Vector[0], m_PopulationSOP[id2].v_Weight_Vector[1]);
		//printf("ideal point: %f  %f\n", zero_point[0], zero_point[1]);
		//printf("f1 parent: %f  f2 child: %f\n", f1, f2);

		if (f2 < f1)
		{	
			//printf("  Reemplazando en subproblema %d: f1=%f  f2=%f\n", id2, f1, f2);
			m_PopulationSOP[id2].m_BestIndividual = child;
		}
	}
}

void CALG_EMO_MOEAD::UpdateProblem_original(CIndividualBase &child,
								   unsigned sp_id)
{	
	double f1, f2;

	int id1 = sp_id, id2;

	vector<double> referencepoint = vector<double>(NumberOfObjectives, 0);

	for (int i = 0; i < s_NeighborhoodSize; i++)
	{

		id2 = m_PopulationSOP[id1].v_Neighbor_Index[i];
		printf("\n\n  Updating Subproblem %d ...\n", id2);
		printf("obj1 padre: %f  %f\n", m_PopulationSOP[id2].m_BestIndividual.f_obj[0], m_PopulationSOP[id2].m_BestIndividual.f_obj[1]);
		printf("vs\n");
		printf("obj child: %f  %f\n", child.f_obj[0], child.f_obj[1]);
		printf("weight vector: %f, %f \n", m_PopulationSOP[id2].v_Weight_Vector[0], m_PopulationSOP[id2].v_Weight_Vector[1]);
		printf("ideal point: %f  %f\n", v_IdealPoint[0], v_IdealPoint[1]);

		
		f1 = UtilityToolBox.ScalarizingFunction(m_PopulationSOP[id2].m_BestIndividual.f_obj,
												m_PopulationSOP[id2].v_Weight_Vector,
												v_IdealPoint,
												s_PBI_type); // 1 - TCH  3 - PBI

		f2 = UtilityToolBox.ScalarizingFunction(child.f_obj,
												m_PopulationSOP[id2].v_Weight_Vector,
												v_IdealPoint,
												s_PBI_type);
		
		printf("f1 padre: %f  f2 child: %f\n", f1, f2);
												
		
		/*
		if(s_PBI_type==1)
		{

			f1 = UtilityToolBox.ScalarizingFunction(m_PopulationSOP[id2].m_BestIndividual.f_obj,
				m_PopulationSOP[id2].v_Weight_Vector,
				v_IdealPoint,
				3);  // 1 - TCH  3 - PBI


			f2 = UtilityToolBox.ScalarizingFunction(child.f_obj,
				m_PopulationSOP[id2].v_Weight_Vector,
				v_IdealPoint,
				3);
		}


		if(s_PBI_type==2)
		{
			vector<double> referencepoint = vector<double>(NumberOfObjectives, 0);
			this->NormalizeIndividual(m_PopulationSOP[id2].m_BestIndividual);
			f1 = UtilityToolBox.ScalarizingFunction(m_PopulationSOP[id2].m_BestIndividual.f_normal,
				m_PopulationSOP[id2].v_Weight_Vector,
				referencepoint,
				3);  // 1 - TCH  3 - PBI


			this->NormalizeIndividual(child);
			f2 = UtilityToolBox.ScalarizingFunction(child.f_normal,
				m_PopulationSOP[id2].v_Weight_Vector,
				referencepoint,
				3);
		}

		if(s_PBI_type==3)
		{

			f1 = UtilityToolBox.ScalarizingFunction(m_PopulationSOP[id2].m_BestIndividual.f_obj,
				m_PopulationSOP[id2].v_Weight_Vector2,
				v_IdealPoint,
				3);  // 1 - TCH  3 - PBI


			f2 = UtilityToolBox.ScalarizingFunction(child.f_obj,
				m_PopulationSOP[id2].v_Weight_Vector2,
				v_IdealPoint,
				3);
		}*/
		

		if (f2 < f1)
		{	
			printf("  Reemplazando en subproblema %d: f1=%f  f2=%f\n", id2, f1, f2);
			m_PopulationSOP[id2].m_BestIndividual = child;
		}
	}
}

void CALG_EMO_MOEAD::SelectMatingPool(vector<unsigned> &pool,
									  unsigned sp_id,
									  unsigned selected_size)
{
	unsigned id, p;
	while (pool.size() < selected_size)
	{
		id = int(s_NeighborhoodSize * UtilityToolBox.Get_Random_Number());
		p = m_PopulationSOP[sp_id].v_Neighbor_Index[id];

		bool flag = true;
		for (unsigned i = 0; i < pool.size(); i++)
		{
			if (pool[i] == p) // parent is in the list
			{
				flag = false;
				break;
			}
		}

		if (flag)
		{
			pool.push_back(p);
		}
	}
}

void CALG_EMO_MOEAD::EvolvePopulation()
{

	if (IsTerminated())
		return;

	std::vector<int> order(std::vector<int>(s_PopulationSize, 0));
	UtilityToolBox.RandomPermutation(order, 0);

	CIndividualBase child;
	int p1, p2;
	vector<unsigned> mating_pool;

	auto ImprimirConteo = [&](const vector<double>& v, std::string label) {
        int pre = 0;           // Bases activas
        int inst = 0;          // Sitios nuevos activos
        int moved_out = 0;     // Bases que se apagaron (disponibles para mover)

        const auto& nodes = this->problemInstance->getNodes();
        double c1 = this->problemInstance->getC1(); // Costo Compra
        double c2 = this->problemInstance->getC2(); // Costo Movimiento
        int max_P = this->problemInstance->getP();

        for(size_t i=0; i<v.size(); ++i) {
            bool is_active = (v[i] > 0.5);
            bool is_pre = (nodes[i]->getFlag() == 1);

            if(is_active) {
                if(is_pre) pre++;
                else inst++;
            }

            // Contar cuántos preinstalados se quitaron (son la fuente de los "Movidos")
            if(is_pre && !is_active) {
                moved_out++;
            }
        }

        // --- CALCULO DE ORIGEN (Movidos vs Nuevos) ---
        // Cuantos instalados provienen de una reubicación:
        int n_movidos = std::min(inst, moved_out);
        
        // Cuantos son compras totalmente nuevas:
        int n_nuevos = inst - n_movidos;
        
        // Calculo de Costo
        double costo_total = (n_nuevos * c1) + (n_movidos * c2);

        // Estado del presupuesto
        std::string estado = (costo_total > max_P) ? "[VIOLA]" : "[OK]";
        
        // --- IMPRESION FORMATEADA ---
        std::cout << std::setw(20) << std::left << label 
                  << "| Pre: " << std::setw(4) << pre 
                  << "| Inst: " << std::setw(4) << inst 
                  << "(Mov:" << std::setw(3) << n_movidos << " New:" << std::setw(3) << n_nuevos << ") "
                  << "| Tot: " << std::setw(4) << (pre+inst)
                  << "| Costo: " << std::setw(6) << std::fixed << std::setprecision(1) << costo_total 
                  << " / " << max_P << " " << estado << std::endl;
    };

	int num_ind = 0;

	for (unsigned int s = 0; s < s_PopulationSize; s++)
	{
		unsigned int id_c = order[s];

		// 2 Seleccion de padres
		SelectMatingPool(mating_pool, id_c, 2);
		p1 = mating_pool[0];
		p2 = mating_pool[1];
		mating_pool.clear();

		if (s < num_ind) { // Limite para no saturar consola
            std::cout << "\n-----------------------------------------------------------" << std::endl;
            std::cout << "DEBUG EVOLUCION - Individuo " << s << " (Gen actual)" << std::endl;
            ImprimirConteo(m_PopulationSOP[p1].m_BestIndividual.x_var, "Padre 1 (P1)");
            ImprimirConteo(m_PopulationSOP[p2].m_BestIndividual.x_var, "Padre 2 (P2)");
        }

		child.problemInstance = this->problemInstance;

		// 3 CRUZAMIENTO
		bool log_cross = false;
		double rand_cross = UtilityToolBox.Get_Random_Number();
		if (rand_cross <= m_CrossoverRate) {
			if (m_IsRelocation) {
				switch (m_CrossoverType) {

					case 6:
						UtilityToolBox.CruzamientoUniformeModificado_con_reubicacion(m_PopulationSOP[p1].m_BestIndividual.x_var,
																			m_PopulationSOP[p2].m_BestIndividual.x_var,
																			child.x_var, this->problemInstance);
						if (log_cross) printf("6 relocation cross\n");
						break;
					case 7:
						UtilityToolBox.CruzamientoUniformeInteligente_Relocation(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("7 relocation cross\n");
						break;
					case 8:
						UtilityToolBox.CruzamientoUniformeReloc(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("8 relocation cross\n");
						break;
					case 9: 
							UtilityToolBox.OnePointCrossover_Relocation(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("9 relocation cross\n");
						break;
					case 10: 
							UtilityToolBox.TwoPointCrossover_Relocation(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("10 relocation cross\n");
						break;
					case 11:
						UtilityToolBox.CruzamientoGeografico_Relocation(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("11 relocation cross\n");
						break;
					default:
						UtilityToolBox.CruzamientoUniformeReloc(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("default relocation cross\n");
						break;
					/* case 6:
						UtilityToolBox.CruzamientoUniformeModificado_con_reubicacion(m_PopulationSOP[p1].m_BestIndividual.x_var,
																			m_PopulationSOP[p2].m_BestIndividual.x_var,
																			child.x_var, this->problemInstance);
						if (log_cross) printf("6 relocation cross\n");
						break;
					case 7:
						UtilityToolBox.CruzamientoUniformeReloc(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("7 relocation cross\n");
						break;
					case 8:
						UtilityToolBox.CruzamientoUniformeInteligente_Relocation(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("8 relocation cross\n");
						break;
					case 9:
						UtilityToolBox.CruzamientoGeografico_Relocation(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("9 relocation cross\n");
						break;
					case 10: 
							UtilityToolBox.OnePointCrossover_Relocation(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("10 relocation cross\n");
						break;
					case 11: 
							UtilityToolBox.TwoPointCrossover_Relocation(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("11 relocation cross\n");
						break;
					default:
						UtilityToolBox.CruzamientoUniformeReloc(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("default relocation cross\n");
						break; */
				}
			} else {
				switch (m_CrossoverType) {
					case 1:
						UtilityToolBox.CruzamientoUniformeModificado_sin_reubicacion(m_PopulationSOP[p1].m_BestIndividual.x_var,
																								m_PopulationSOP[p2].m_BestIndividual.x_var,
																								child.x_var, this->problemInstance);
						if (log_cross) printf("1 location cross\n");
						break;
					case 2:
						UtilityToolBox.CruzamientoUniformeInteligente(m_PopulationSOP[p1].m_BestIndividual.x_var,
																m_PopulationSOP[p2].m_BestIndividual.x_var,
																child.x_var, this->problemInstance);
						if (log_cross) printf("2 location cross\n");
						break;
					case 3:
						UtilityToolBox.CruzamientoUniforme(m_PopulationSOP[p1].m_BestIndividual.x_var,
															m_PopulationSOP[p2].m_BestIndividual.x_var,
															child.x_var, this->problemInstance);
						if (log_cross) printf("3 location cross\n");
						break;
					case 4: 
						UtilityToolBox.OnePointCrossover(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("4 location cross\n");
						break;
					case 5:
						UtilityToolBox.TwoPointCrossover(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("5 location cross\n");
						break;
					default:
						UtilityToolBox.CruzamientoUniforme(m_PopulationSOP[p1].m_BestIndividual.x_var,
															m_PopulationSOP[p2].m_BestIndividual.x_var,
															child.x_var, this->problemInstance);
						if (log_cross) printf("default location cross\n");
						break;
				}
			}
		} else {
			if (UtilityToolBox.Get_Random_Number() < 0.5) {
				child.x_var = m_PopulationSOP[p1].m_BestIndividual.x_var;
			} else {
				child.x_var = m_PopulationSOP[p2].m_BestIndividual.x_var;
			}
		}

		// -------------------------------------------------------------
        // IMPRESION DEBUG: HIJO POST-CROSSOVER
        // -------------------------------------------------------------
        if (s < num_ind) {
            ImprimirConteo(child.x_var, "Hijo (Despues Cruce)");
        }
        // -------------------------------------------------------------

		bool log_mut = false;
		if (m_IsRelocation) {
			switch (m_MutationType)
			{	
				case 12:
					UtilityToolBox.MutacionModificada_con_reubicacion(child.x_var, m_MutationRate, m_Op1MutationProb, this->problemInstance);
					if (log_mut) printf("12 relocation mut\n");
					break;
				case 13:
					UtilityToolBox.MutacionSwapProbabilisticoReloc(child.x_var, m_MutationRate, m_MutProbSwap, this->problemInstance);
					if (log_mut) printf("13 relocation mut\n");
					break;
				case 14:
					UtilityToolBox.MutacionSwapPorcentualReloc(child.x_var, m_MutationRate, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("14 relocation mut\n");
					break;
				case 15:
					UtilityToolBox.MutacionDeletePorcentualReloc(child.x_var, m_MutationRate, m_MutPctDelete, this->problemInstance);
					if (log_mut) printf("15 relocation mut\n");
					break;
				case 16:{
					double p = 1.0 / (double)child.x_var.size();
					UtilityToolBox.MutacionBitFlip_Relocation(child.x_var, m_MutationRate, p, this->problemInstance);
					if (log_mut) printf("16 relocation mut\n");
					break;}
				case 17:{
					double p = 1.0 / (double)s_PopulationSize;
					UtilityToolBox.MutacionBitFlip_Relocation(child.x_var, m_MutationRate, p, this->problemInstance);
					if (log_mut) printf("17 relocation mut\n");
					break;}
				case 18:
					UtilityToolBox.MutacionBitFlip_Relocation(child.x_var, m_MutationRate, m_BitFlipProb, this->problemInstance);
					if (log_mut) printf("18 relocation mut\n");
					break;
				case 19:
					UtilityToolBox.Mutacion_Reloc_Fusion_1_N(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("19 relocation fusion 1/N\n");
					break;
				case 20:
					UtilityToolBox.Mutacion_Reloc_Fusion_1_M(child.x_var, m_MutationRate, m_Op1MutationProb, s_PopulationSize, m_MutPctSwap, this->problemInstance);
    				if (log_mut) printf("20 relocation fusion 1/M\n");
					break;
				case 21:
					UtilityToolBox.Mutacion_Reloc_Fusion_Fijo(child.x_var, m_MutationRate, m_Op1MutationProb, m_BitFlipProb, m_MutPctSwap, this->problemInstance);
    				if (log_mut) printf("21 relocation fusion Fixed\n");
					break;
				case 22:
					UtilityToolBox.MutacionHibridaReloc(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctDelete, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("22 relocation mut\n");
					break;
				default:{
					double p = 1.0 / (double)s_PopulationSize;
					UtilityToolBox.MutacionBitFlip_Relocation(child.x_var, m_MutationRate, p, this->problemInstance);
					if (log_mut) printf("default relocation mut\n");
					break;} 

				/* case 12:
					UtilityToolBox.MutacionModificada_con_reubicacion(child.x_var, m_MutationRate, m_Op1MutationProb, this->problemInstance);
					if (log_mut) printf("12 relocation mut\n");
					break;
				case 13:
					UtilityToolBox.MutacionSwapPorcentualReloc(child.x_var, m_MutationRate, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("13 relocation mut\n");
					break;
				case 14:
					UtilityToolBox.MutacionDeletePorcentualReloc(child.x_var, m_MutationRate, m_MutPctDelete, this->problemInstance);
					if (log_mut) printf("14 relocation mut\n");
					break;
				case 15:
					UtilityToolBox.MutacionHibridaReloc(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctDelete, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("15 relocation mut\n");
					break;
				case 16:{
					double p = 1.0 / (double)child.x_var.size();
					UtilityToolBox.MutacionBitFlip_Relocation(child.x_var, m_MutationRate, p, this->problemInstance);
					if (log_mut) printf("16 relocation mut\n");
					break;
				}
				case 17:
					UtilityToolBox.MutacionBitFlip_Relocation(child.x_var, m_MutationRate, m_BitFlipProb, this->problemInstance);
					if (log_mut) printf("17 relocation mut\n");
					break;
				case 18:{
					double p = 1.0 / (double)s_PopulationSize;
					UtilityToolBox.MutacionBitFlip_Relocation(child.x_var, m_MutationRate, p, this->problemInstance);
					if (log_mut) printf("18 relocation mut\n");
					break;
				}
				case 19:
					UtilityToolBox.MutacionSwapProbabilisticoReloc(child.x_var, m_MutationRate, m_MutProbSwap, this->problemInstance);
					if (log_mut) printf("19 relocation mut\n");
					break;
				case 20:
					UtilityToolBox.Mutacion_Reloc_Fusion_1_N(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("20 relocation fusion 1/N\n");
					break;
				case 21:
					UtilityToolBox.Mutacion_Reloc_Fusion_1_M(child.x_var, m_MutationRate, m_Op1MutationProb, s_PopulationSize, m_MutPctSwap, this->problemInstance);
    				if (log_mut) printf("21 relocation fusion 1/M\n");
					break;
				case 22:
					UtilityToolBox.Mutacion_Reloc_Fusion_Fijo(child.x_var, m_MutationRate, m_Op1MutationProb, m_BitFlipProb, m_MutPctSwap, this->problemInstance);
    				if (log_mut) printf("22 relocation fusion Fixed\n");
					break;
				default:
					{
					double p = 1.0 / (double)s_PopulationSize;
					UtilityToolBox.MutacionBitFlip_Relocation(child.x_var, m_MutationRate, p, this->problemInstance);
					if (log_mut) printf("default relocation mut\n");
					break;
				} */
				}
		} else {
			switch (m_MutationType)
			{	
				case 1:
					UtilityToolBox.MutacionModificada_sin_reubicacion(child.x_var, m_MutationRate, m_Op1MutationProb, this->problemInstance);
					if (log_mut) printf("1 location mut\n");
					break;
				case 2:
					UtilityToolBox.MutacionSwapProbabilistico(child.x_var, m_MutationRate, m_MutProbSwap, this->problemInstance);
					if (log_mut) printf("2 location mut\n");
					break;
				case 3:
					UtilityToolBox.MutacionSwapPorcentual(child.x_var, m_MutationRate, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("3 location mut\n");
					break;
				case 4:
					UtilityToolBox.MutacionDeletePorcentual(child.x_var, m_MutationRate, m_MutPctDelete, this->problemInstance);
					if (log_mut) printf("4 location mut\n");
					break;
				case 5:
					UtilityToolBox.MutacionBitFlip_1_N(child.x_var, m_MutationRate, this->problemInstance);
					if (log_mut) printf("5 location mut\n");
					break;
				case 6:
					UtilityToolBox.MutacionBitFlip_1_M(child.x_var, m_MutationRate, s_PopulationSize, this->problemInstance);
					if (log_mut) printf("6 location mut\n");
					break;
				case 7:
					UtilityToolBox.MutacionBitFlip_Fijo(child.x_var, m_MutationRate, m_BitFlipProb, this->problemInstance);
					if (log_mut) printf("7 location mut\n");
					break;
				case 8:
					UtilityToolBox.Mutacion_Swap_Porcentual_1_N(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("8 location mut\n");
					break;
				case 9:
					UtilityToolBox.Mutacion_Swap_Porcentual_1_M(child.x_var, m_MutationRate, m_Op1MutationProb, s_PopulationSize, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("9 location mut\n");
					break;
				case 10:
					UtilityToolBox.Mutacion_Swap_Porcentual_Fijo(child.x_var, m_MutationRate, m_Op1MutationProb, m_BitFlipProb, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("10 location mut\n");
					break;
				case 11:
					UtilityToolBox.MutacionHibrida_location(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctDelete, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("11 location mut\n");
					break;
				default:
					UtilityToolBox.MutacionBitFlip_Fijo(child.x_var, m_MutationRate, m_BitFlipProb, this->problemInstance);
					if (log_mut) printf("default location mut\n");
					break;

				/* case 1:
					UtilityToolBox.MutacionBitFlip_1_N(child.x_var, m_MutationRate, this->problemInstance);
					if (log_mut) printf("1 location mut\n");
					break;
				case 2:
					UtilityToolBox.MutacionBitFlip_1_M(child.x_var, m_MutationRate, s_PopulationSize, this->problemInstance);
					if (log_mut) printf("2 location mut\n");
					break;
				case 3:
					UtilityToolBox.MutacionBitFlip_Fijo(child.x_var, m_MutationRate, m_BitFlipProb, this->problemInstance);
					if (log_mut) printf("3 location mut\n");
					break;
				case 4:
					UtilityToolBox.MutacionSwapProbabilistico(child.x_var, m_MutationRate, m_MutProbSwap, this->problemInstance);
					if (log_mut) printf("4 location mut\n");
					break;
				case 5:
					UtilityToolBox.Mutacion_Swap_Porcentual_1_N(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("5 location mut\n");
					break;
				case 6:
					UtilityToolBox.Mutacion_Swap_Porcentual_1_M(child.x_var, m_MutationRate, m_Op1MutationProb, s_PopulationSize, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("6 location mut\n");
					break;
				case 7:
					UtilityToolBox.Mutacion_Swap_Porcentual_Fijo(child.x_var, m_MutationRate, m_Op1MutationProb, m_BitFlipProb, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("7 location mut\n");
					break;
				case 8:
					UtilityToolBox.MutacionModificada_sin_reubicacion(child.x_var, m_MutationRate, m_Op1MutationProb, this->problemInstance);
					if (log_mut) printf("8 location mut\n");
					break;
				case 9:
					UtilityToolBox.MutacionSwapPorcentual(child.x_var, m_MutationRate, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("9 location mut\n");
					break;
				case 10:
					UtilityToolBox.MutacionDeletePorcentual(child.x_var, m_MutationRate, m_MutPctDelete, this->problemInstance);
					if (log_mut) printf("10 location mut\n");
					break;
				case 11:
					UtilityToolBox.MutacionHibrida_location(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctDelete, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("11 location mut\n");
					break;
				default:
					UtilityToolBox.MutacionBitFlip_Fijo(child.x_var, m_MutationRate, m_BitFlipProb, this->problemInstance);
					if (log_mut) printf("default location mut\n");
					break; */
				}
		}

		// -------------------------------------------------------------
        // IMPRESION DEBUG: HIJO POST-MUTACION
        // -------------------------------------------------------------
        if (s < num_ind) {
            ImprimirConteo(child.x_var, "Hijo (Despues Mutac)");
            std::cout << "-----------------------------------------------------------\n" << std::endl;
        }
        // -------------------------------------------------------------


		child.Evaluate();
		s_Fevals_Count++;

		// this->NormalizeIndividual(child);

		// child.Show(0); getchar();

		UpdateReference(child.f_obj);
		UpdateNadirPoint(child.f_obj);
		UpdateProblem_modificado(child, id_c);

		if (IsTerminated())
			break;
	}

	this->FindNadirPoint();

	// if(s_PBI_type==3)  this->NormalizeWeight();
}

bool CALG_EMO_MOEAD::IsTerminated()
{
	if (s_Fevals_Count >= NumberOfFuncEvals)
	{
		return true;
	}
	else
	{
		return false;
	}
}

void CALG_EMO_MOEAD::SaveObjSpace(char saveFilename[1024])
{
	std::fstream fout;
	fout.open(saveFilename, std::ios::out);

	if (!fout.is_open()) {
        std::cout << ">>> ERROR AL GUARDAR: No se pudo crear el archivo: " << saveFilename << std::endl;
        std::cout << "    (Verifica que la carpeta exista y tengas permisos)" << std::endl;
        return;
    }

	fout << std::fixed;

	for (unsigned n = 0; n < s_PopulationSize; n++)
	{
		for (unsigned int k = 0; k < NumberOfObjectives; k++)
		{	
			if (m_ProblemType == "cam") {
				if (k == 1) {
					fout << std::setprecision(0);
				} else {
					fout << std::setprecision(4);
				}
			} else if (m_ProblemType == "drp") {
				if (k == 1) {
					fout << std::setprecision(1);
				} else {
					fout << std::setprecision(7);
				}
			} else {
				fout << std::setprecision(7);
			}
			fout << m_PopulationSOP[n].m_BestIndividual.f_obj[k] << "  ";
		}

		fout << "- IDs instalados: ";
		const auto &x = m_PopulationSOP[n].m_BestIndividual.x_var;
		for (unsigned int i = 0; i < x.size(); i++)
		{
			if (x[i] >= 0.5) // binario (1 instalado)
			{
				fout << i + 1 << " ";
			}
		}

		fout << "\n";
	}
	fout.close();
}

void CALG_EMO_MOEAD::SaveVarSpace(char saveFilename[1024])
{
	std::fstream fout;
	fout.open(saveFilename, std::ios::out);
	for (unsigned n = 0; n < s_PopulationSize; n++)
	{
		for (unsigned k = 0; k < NumberOfVariables; k++)
		{
			fout << m_PopulationSOP[n].m_BestIndividual.x_var[k] << "  ";
		}
		fout << "\n";
	}
	fout.close();
}

void CALG_EMO_MOEAD::SavePopulation(int run_id)
{
	char filename[2048];

	if (this->outputDirectory.empty()) {
		this->outputDirectory = "SAVING/MOEAD/POF";
	}

	std::string cleanName= strTestInstance;
	size_t lastindex = cleanName.find_last_of(".");
	if (lastindex != std::string::npos) {
		cleanName = cleanName.substr(0, lastindex);
	}

	sprintf(filename, "%s/POF_%s_SEED_%d_GEN_%d.dat", this->outputDirectory.c_str(), cleanName.c_str(), rnd_uni_seed, run_id);

	// sprintf(filename, "%s/SAVING/MOEAD/POF/POF_%s_GEN_%d.dat", exe_dir_path.c_str(), strTestInstance, run_id);

	SaveObjSpace(filename); // ��ǰ��Ⱥ���

	// sprintf_s(filename,"Saving/MOEAD/POS_%s_RUN%d.dat",strTestInstance, run_id);
	// SaveVarSpace(filename);
}

void CALG_EMO_MOEAD::SaveFinalPopulation()
{
	char filename[2048];

	if (this->outputDirectory.empty()) {
		this->outputDirectory = "SAVING/MOEAD/POF";
	}

	std::string cleanName = strTestInstance;
	size_t lastindex = cleanName.find_last_of(".");
	if (lastindex != std::string::npos) {
		cleanName = cleanName.substr(0, lastindex);
	}

	sprintf(filename, "%s/last_gen_%s.dat", this->outputDirectory.c_str(), cleanName.c_str());

	SaveObjSpace(filename);

	std::cout << ">>> Copia de ultima gen guardada en: " << filename << std::endl;
}