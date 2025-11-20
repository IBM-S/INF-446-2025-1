#include "ALG_EMO_MOEAD.h"
#include <string.h>

CALG_EMO_MOEAD::CALG_EMO_MOEAD(void)
{
	s_PBI_type = 3;
}

CALG_EMO_MOEAD::~CALG_EMO_MOEAD(void)
{
}

void CALG_EMO_MOEAD::Execute(int run_id)
{

	this->InitializeParameter();
	this->InitializePopulation();
	this->InitializeNeighborhood();

	int gen = 0;

	for (;;)
	{
		std::cout << "Generación: " << gen << std::endl;
		gen++;
		this->EvolvePopulation();

		if (IsTerminated())
		{
			break;
		}

		/* if((gen%25)==0)
		{
			printf("Instance:  %s  RUN:  %d  GEN = %d\n", strTestInstance, run_id, gen);
			this->SavePopulation(run_id);
		}
		*/

		/* if ((gen % 1) == 0) // cada 1 generación
		{
			char filename[1024];
			sprintf(filename, "SAVING/MOEAD/POF/POF_%s_%d_GEN%d.dat", strTestInstance, rnd_uni_seed, gen);
			SaveObjSpace(filename); // Guardar la población actual en el archivo
		} */
		// imprimir poblacion de la generacion 10

		printf("Instance:  %s  RUN:  %d  GEN = %d\n", strTestInstance, run_id, gen);
		this->SavePopulation(gen);
	}

	this->SavePopulation(gen);

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

	char str_temp[1024];
	std::ifstream readf(filename);
	// Pop_Size     NeighborhoodSize
	readf >> s_PopulationSize;
	readf >> s_NeighborhoodSize;
	readf.close();
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

	std::ifstream readf(filename1);
	if (!readf.is_open())
	{
		printf("ERROR: No se pudo abrir archivo de pesos: %s\n", filename1);
	}

	for (i = 0; i < s_PopulationSize; i++)
	{
		CSubProblemBase SP;

		const auto &nodos = this->problemInstance->getNodes();

		int aeds_preinstalados = 0;
		for (const auto &nodo : nodos)
		{
			if (nodo->getFlag() == 1)
			{
				aeds_preinstalados++;
			}
		}

		int total_locations = nodos.size() - aeds_preinstalados;

		int num_AEDs = rand() % (total_locations + 1); // genera número entre 0 y total_locations

		SP.m_BestIndividual.problemInstance = this->problemInstance;

		// Con contar presupuesto
		int presupuesto = this->problemInstance->getP();
		num_AEDs = rand() % (presupuesto + 1);
		SP.m_BestIndividual.GenerateSimpleFeasibleSolution(num_AEDs, total_locations);
		// Sin contar el presupuesto
		// SP.m_BestIndividual.GenerateSimpleFeasibleSolution(num_AEDs, total_locations);
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

	// this->FindNadirPoint();

	// if(s_PBI_type==3) 	NormalizeWeight();
}

void CALG_EMO_MOEAD::FindNadirPoint()
{

	v_NadirPoint = vector<double>(NumberOfObjectives, -1.0e30);

	for (int j = 0; j < NumberOfObjectives; j++)
	{
		//*
		vector<double> weight_tch = vector<double>(NumberOfObjectives, 10e-6);
		weight_tch[j] = 1;

		double asf_min = 1.0e+30;
		int asf_id = 0;
		for (int s = 0; s < s_PopulationSize; s++)
		{
			double tch_max = -1.0e+30;
			for (int k = 0; k < NumberOfObjectives; k++)
			{
				double temp = m_PopulationSOP[s].m_BestIndividual.f_obj[k] / weight_tch[k];
				if (temp > tch_max)
				{
					tch_max = temp;
				}
			}
			if (tch_max < asf_min)
			{
				asf_min = tch_max;
				asf_id = s;
			}
		}
		v_NadirPoint[j] = m_PopulationSOP[asf_id].m_BestIndividual.f_obj[j];
	}

	/*
	for(int s=0; s<s_PopulationSize; s++)
	{
		this->NormalizeIndividual(m_PopulationSOP[s].m_BestIndividual);
	}
	*/
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

void CALG_EMO_MOEAD::UpdateProblem(CIndividualBase &child,
								   unsigned sp_id)
{

	double f1, f2;

	int id1 = sp_id, id2;

	vector<double> referencepoint = vector<double>(NumberOfObjectives, 0);

	for (int i = 0; i < s_NeighborhoodSize; i++)
	{

		id2 = m_PopulationSOP[id1].v_Neighbor_Index[i];

		//*
		f1 = UtilityToolBox.ScalarizingFunction(m_PopulationSOP[id2].m_BestIndividual.f_obj,
												m_PopulationSOP[id2].v_Weight_Vector,
												v_IdealPoint,
												1); // 1 - TCH  3 - PBI

		f2 = UtilityToolBox.ScalarizingFunction(child.f_obj,
												m_PopulationSOP[id2].v_Weight_Vector,
												v_IdealPoint,
												1);
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
		}
		//*/

		if (f2 < f1)
		{
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

		SelectMatingPool(mating_pool, id_c, 2);
		p1 = mating_pool[0];
		p2 = mating_pool[1];
		mating_pool.clear();

		/* std::cout << "\n=== Reproducción " << s << " ===" << std::endl;

		std::cout << "Padre 1 (ID " << p1 << "): ";
		for (double val : m_PopulationSOP[p1].m_BestIndividual.x_var)
		{
			std::cout << val << " ";
		}
		std::cout << std::endl;

		std::cout << "Padre 2 (ID " << p2 << "): ";
		for (double val : m_PopulationSOP[p2].m_BestIndividual.x_var)
		{
			std::cout << val << " ";
		}
		std::cout << std::endl; */

		bool con_reubicacion = false;

		if (con_reubicacion)
		{
			UtilityToolBox.CruzamientoUniformeModificado_con_reubicacion(m_PopulationSOP[p1].m_BestIndividual.x_var,
																		 m_PopulationSOP[p2].m_BestIndividual.x_var,
																		 child.x_var, this->problemInstance);
		}
		else
		{
			UtilityToolBox.CruzamientoUniformeModificado_sin_reubicacion(m_PopulationSOP[p1].m_BestIndividual.x_var,
																		 m_PopulationSOP[p2].m_BestIndividual.x_var,
																		 child.x_var, this->problemInstance);
		}

		/* UtilityToolBox.CruzamientoUniformeModificado(m_PopulationSOP[p1].m_BestIndividual.x_var,
													 m_PopulationSOP[p2].m_BestIndividual.x_var,
													 child.x_var); */

		child.problemInstance = this->problemInstance;

		/* std::cout << "Hijo generado antes de la mutacion:   ";
		for (double val : child.x_var)
		{
			std::cout << val << " ";
		}
		std::cout << std::endl; */

		// UtilityToolBox.MutacionModificada(child.x_var, 1.0);
		if (con_reubicacion)
		{
			UtilityToolBox.MutacionModificada_con_reubicacion(child.x_var, 1.0, this->problemInstance);
		}
		else
		{
			UtilityToolBox.MutacionModificada_sin_reubicacion(child.x_var, 1.0, this->problemInstance);
		}

		/* std::cout << "Hijo generado despues de la mutacion: ";
		for (double val : child.x_var)
		{
			std::cout << val << " ";
		}
		std::cout << std::endl; */

		/*
		Aqui modificar Utility Box y agregar la mutation y crossover
		Ya agregado
		Ahora considerar la representacion binaria

		*/

		child.Evaluate();
		s_Fevals_Count++;

		/* std::cout << "hijo f_obj = ";
		for (double f : child.f_obj) {
			std::cout << f << " ";
		}
		std::cout << std::endl; */

		// this->NormalizeIndividual(child);

		// child.Show(0); getchar();

		UpdateReference(child.f_obj);

		UpdateProblem(child, id_c);

		if (IsTerminated())
			break;
	}

	// this->FindNadirPoint();

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
	char filename[1024];
	// sprintf(filename,"SAVING/MOEAD/POF/POF_%s_RUN%d.dat",strTestInstance, run_id);
	// sprintf(filename, "SAVING/MOEAD/POF/POF_%s_GEN_%d.dat", strTestInstance, run_id);
	sprintf(filename, "%s/SAVING/MOEAD/POF/POF_%s_GEN_%d.dat", exe_dir_path.c_str(), strTestInstance, run_id);

	SaveObjSpace(filename); // ��ǰ��Ⱥ���

	// sprintf_s(filename,"Saving/MOEAD/POS_%s_RUN%d.dat",strTestInstance, run_id);
	// SaveVarSpace(filename);
}
