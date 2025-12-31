#include "ALG_EMO_MOEAD.h"
#include <string.h>
#include <cmath>

CALG_EMO_MOEAD::CALG_EMO_MOEAD(void)
{
	s_PBI_type = 1;
	m_MutationRate = 0.3;
    m_CrossoverRate = 1.0;
    m_Op1MutationProb = 0.2;
    m_IsRelocation = true; // Por defecto Location (fijo)
    m_ProblemType = "cam";
	s_PopulationSize = 0;
    s_NeighborhoodSize = 0;
	m_MaxTimeSeconds = 0; // Sin límite por defecto
	m_SaveInterval = 0;

	m_MutationType = 11;      // Híbrida por defecto
    m_CrossoverType = 3;     // Inteligente por defecto
    m_MutationPercentage = 0.05; 
    m_BitFlipProb = 0.01;

	m_MutPctDelete = 0.05; // 5% por defecto
	m_MutPctSwap   = 0.05; // 5% por defecto

	m_NeighborhoodSizePct = 0.0;
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

	printf("\nNadir Point Inicial\n"); // Son los peores valores de objetivos
	printf("%f", v_NadirPoint[0]);
	printf("\n");
	printf("%f", v_NadirPoint[1]);
	printf("\nIdeal Point Inicial\n");  // Son los mejores valores de objetivos
	printf("%f", v_IdealPoint[0]);
	printf("\n");
	printf("%f\n", v_IdealPoint[1]);


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

	printf("\nNadir Point Final\n"); // Son los peores valores de objetivos
	printf("%f", v_NadirPoint[0]);
	printf("\n");
	printf("%f", v_NadirPoint[1]);
	printf("\nIdeal Point Final\n");  // Son los mejores valores de objetivos
	printf("%f", v_IdealPoint[0]);
	printf("\n");
	printf("%f\n", v_IdealPoint[1]);

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

	int aeds_preinstalados = 0;
	if (!m_IsRelocation) {
		for (const auto &nodo : nodos) if (nodo->getFlag() == 1) aeds_preinstalados++;
	}
	int huecos_disponibles = total_nodos - aeds_preinstalados;

	for (i = 0; i < s_PopulationSize; i++)
	{
		CSubProblemBase SP;
		SP.m_BestIndividual.problemInstance = this->problemInstance;

		bool log_initialization = false;
		if (m_IsRelocation) {
			int m_InitializationType = 1;
			int num_nuevos = rand() % (presupuesto + 1);
			switch (m_InitializationType) {
				case 1: 
					SP.m_BestIndividual.GenerateSimpleFeasibleSolution_For_Relocation(num_nuevos, presupuesto,total_nodos);
					if (log_initialization) printf("1   relocation initialization\n");
					break;
				case 2:
					SP.m_BestIndividual.GenerateSimpleFeasibleSolution_Mixed_Split(num_nuevos, total_nodos);
					if (log_initialization) printf("2    relocation initialization\n");
					break;
				default:
					SP.m_BestIndividual.GenerateSimpleFeasibleSolution_For_Relocation(num_nuevos, presupuesto,total_nodos);
					if (log_initialization) printf("default    relocation initialization\n");
					break;
			}
		} else {
			int num_a_instalar = rand() % (presupuesto + 1); // genera número entre 0 y presupuesto
			if (num_a_instalar > huecos_disponibles) num_a_instalar = huecos_disponibles;
			SP.m_BestIndividual.GenerateSimpleFeasibleSolution(num_a_instalar, huecos_disponibles);
			if (log_initialization) printf("default location initialization\n");

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

	for (unsigned int s = 0; s < s_PopulationSize; s++)
	{
		unsigned int id_c = order[s];

		// 2 Seleccion de padres
		SelectMatingPool(mating_pool, id_c, 2);
		p1 = mating_pool[0];
		p2 = mating_pool[1];
		mating_pool.clear();

		child.problemInstance = this->problemInstance;

		// 3 CRUZAMIENTO
		bool log_cross = false;
		double rand_cross = UtilityToolBox.Get_Random_Number();
		if (rand_cross <= m_CrossoverRate) {
			if (m_IsRelocation) {
				switch (m_CrossoverType) {
					case 4:
						UtilityToolBox.CruzamientoUniformeModificado_con_reubicacion(m_PopulationSOP[p1].m_BestIndividual.x_var,
																			m_PopulationSOP[p2].m_BestIndividual.x_var,
																			child.x_var, this->problemInstance);
						if (log_cross) printf("4 relocation cross\n");
						break;
					case 5:
						UtilityToolBox.CruzamientoUniformeReloc(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("5 relocation cross\n");
						break;
					default:
						UtilityToolBox.CruzamientoUniformeReloc(m_PopulationSOP[p1].m_BestIndividual.x_var,
														  m_PopulationSOP[p2].m_BestIndividual.x_var,
														  child.x_var, this->problemInstance);
						if (log_cross) printf("default relocation cross\n");
						break;
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
						UtilityToolBox.CruzamientoUniformeSemiInteligente(m_PopulationSOP[p1].m_BestIndividual.x_var,
															m_PopulationSOP[p2].m_BestIndividual.x_var,
															child.x_var, this->problemInstance);
						if (log_cross) printf("3 location cross\n");
						break;
					default:
						UtilityToolBox.CruzamientoUniformeSemiInteligente(m_PopulationSOP[p1].m_BestIndividual.x_var,
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
		bool log_mut = false;
		if (m_IsRelocation) {
			switch (m_MutationType)
			{
				case 12:
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
				default:
					UtilityToolBox.MutacionHibridaReloc(child.x_var, m_MutationRate, m_Op1MutationProb, m_MutPctDelete, m_MutPctSwap, this->problemInstance);
					if (log_mut) printf("default relocation mut\n");
					break;
				}
		} else {
			switch (m_MutationType)
			{
				case 1:
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
					UtilityToolBox.MutacionSwapProbabilistico(child.x_var, m_MutationRate, m_MutPctSwap, this->problemInstance);
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
					break;
				}
		}


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

	for (unsigned n = 0; n < s_PopulationSize; n++)
	{
		for (unsigned int k = 0; k < NumberOfObjectives; k++)
		{
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