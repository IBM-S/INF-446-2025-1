// UtilityTool.cpp: implementation of the CUtilityToolBox class.
//
//////////////////////////////////////////////////////////////////////

#include "UtilityToolBox.h"
#include <iostream>
#include <cmath>
#include "DRP_ProblemInstance.h"

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

CUtilityToolBox::CUtilityToolBox()
{
}

CUtilityToolBox::~CUtilityToolBox()
{
}

double CUtilityToolBox::DistanceVectorPBI(vector<double> &vec1, vector<double> &vec2)
{
	int dim = vec1.size();
	double sum = 0.;
	double lambda = InnerProduct(vec1, vec2) / InnerProduct(vec2, vec2);
	for (int i = 0; i < dim; i++)
		sum += (vec1[i] - lambda * vec2[i]) * (vec1[i] - lambda * vec2[i]);
	return sum;
}

void CUtilityToolBox::NormalizeVector(vector<double> &vect)
{
	double sum = 0;
	for (int i = 0; i < vect.size(); i++)
	{
		sum += vect[i];
	}

	for (int j = 0; j < vect.size(); j++)
	{
		vect[j] = vect[j] / sum;
	}
}

double CUtilityToolBox::InnerProduct(vector<double> &vec1, vector<double> &vec2)
{
	int dim = vec1.size();
	double sum = 0;
	for (int n = 0; n < dim; n++)
		sum += vec1[n] * vec2[n];
	return sum;
}

double CUtilityToolBox::DistanceVectorNorm2(vector<double> &vec1, vector<double> &vec2)
{
	int dim = vec1.size();
	double sum = 0;
	for (int n = 0; n < dim; n++)
		sum += (vec1[n] - vec2[n]) * (vec1[n] - vec2[n]);
	return sqrt(sum);
}

double CUtilityToolBox::VectorNorm2(vector<double> &vec1)
{
	int dim = vec1.size();
	double sum = 0;
	for (int n = 0; n < dim; n++)
		sum += vec1[n] * vec1[n];
	return sqrt(sum);
}

double CUtilityToolBox::DistanceVectorNorm1(vector<double> &vec1,
											vector<double> &vec2)
{
	int dim = vec1.size();
	double sum = 0;
	for (int n = 0; n < dim; n++)
		sum += fabs(vec1[n] - vec2[n]);
	return sum;
}

double CUtilityToolBox::ScalarizingFunction(vector<double> &y_obj,
											vector<double> &namda,
											vector<double> &referencepoint,
											int s_type)
{

	// Chebycheff Scalarizing Function

	unsigned n, nobj = y_obj.size();

	double max_fun = -1.0e+30, diff, feval, scalar_obj;

	if (s_type == 1)
	{
		for (n = 0; n < nobj; n++)
		{
			diff = fabs(y_obj[n] - referencepoint[n] + 0.01);
			if (namda[n] == 0)
				feval = 0.001 * diff;
			else
				feval = namda[n] * diff;

			if (feval > max_fun)
			{
				max_fun = feval;
			}
		}
		scalar_obj = max_fun;
	}

	if (s_type == 2)
	{
		double alpha = 0.1;

		for (n = 0; n < nobj; n++)
		{
			diff = y_obj[n] - referencepoint[n];
			feval = diff * (1.0 / nobj + alpha * namda[n]);
			if (feval > max_fun)
			{
				max_fun = feval;
			}
		}
		scalar_obj = max_fun;
	}

	if (s_type == 3) // PBI
	{
		vector<double> vect_normal = vector<double>(nobj, 0);
		double namda_norm = this->VectorNorm2(namda);
		for (int n = 0; n < nobj; n++)
		{
			vect_normal[n] = namda[n] / namda_norm;
		}

		double d1_proj = abs(this->InnerProduct(y_obj, vect_normal) - this->InnerProduct(referencepoint, vect_normal));
		double temp = d1_proj * d1_proj - 2 * d1_proj * (this->InnerProduct(y_obj, vect_normal) - this->InnerProduct(referencepoint, vect_normal)) + (this->InnerProduct(y_obj, y_obj) + this->InnerProduct(referencepoint, referencepoint) - 2 * this->InnerProduct(y_obj, referencepoint));
		double d2_pred = sqrt(temp);
		scalar_obj = d1_proj + 20 * d2_pred;
	}
	return scalar_obj;
}

void CUtilityToolBox::RandomPermutation(vector<int> &permutation, int type)
{
	if (type == 0)
	{
		for (unsigned k = 0; k < permutation.size(); k++)
			permutation[k] = k;
	}
	random_shuffle(permutation.begin(), permutation.end());
}

vector<int> CUtilityToolBox::IndexOfMinimumInt(vector<int> &vec)
{
	vector<int> I;
	I.clear();
	int id = -1;
	int min_value = 1e9; // �������Ϊ2^32
	for (int i = 0; i < vec.size(); i++)
	{
		if (vec[i] < min_value)
		{
			min_value = vec[i];
			id = i;
		}
	}
	for (int i = 0; i < vec.size(); i++)
		if (vec[i] == min_value)
			I.push_back(i);
	return I;
}

int CUtilityToolBox::IndexOfMinimumDouble(vector<double> &vec)
{
	int id = 0;
	double minvalue = 1.0e30;
	for (int i = 0; i < vec.size(); i++)
	{
		if (vec[i] < minvalue)
		{
			minvalue = vec[i];
			id = i;
		}
	}
	return id;
}

void CUtilityToolBox::Minfastsort(vector<double> &x, vector<int> &idx, int n, int m)
{
	for (int i = 0; i < m; i++)
	{
		for (int j = i + 1; j < n; j++)
			if (x[i] > x[j])
			{
				double temp = x[i];
				x[i] = x[j];
				x[j] = temp;
				int id = idx[i];
				idx[i] = idx[j];
				idx[j] = id;
			}
	}
}
void CUtilityToolBox::Maxfastsort(vector<double> &x, vector<int> &idx, int n, int m)
{
	for (int i = 0; i < m; i++)
	{
		for (int j = i + 1; j < n; j++)
			if (x[i] < x[j])
			{
				double temp = x[i];
				x[i] = x[j];
				x[j] = temp;
				int id = idx[i];
				idx[i] = idx[j];
				idx[j] = id;
			}
	}
}

void CUtilityToolBox::MutacionModificada_sin_reubicacion(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *problemInstance)
{
	// 1 Verificar probabilidad
	double prob_mutation_rate = Get_Random_Number();
	if (prob_mutation_rate > mutation_rate)
	{
		//printf("No hay mutacion\n");
		return;
	}

	int n = x_var.size();
	const auto &nodos = problemInstance->getNodes();

	// 2 Identificar candidatos
	std::vector<int> candidatos_borrar; // Donde hay 1s
	std::vector<int> candidatos_poner; // Donde hay 0s
	
	for (int i = 0; i < n; ++i)
	{
		if (x_var[i] == 1 && nodos[i]->getFlag() == 0)
		{
			candidatos_borrar.push_back(i);
		}
		else {
			candidatos_poner.push_back(i);
		}
	}

	if (candidatos_borrar.empty())
	{
		// No hay 1s para eliminar
		return;
	}

	// 3 Decidir operador (Delete vs swap)

	double rnd = Get_Random_Number();
	bool esSwap = true ;

	if (rnd <= prob_op1_delete) {
        //Rango [0, prob_op1] -> Operador 1 (Solo Delete)
        esSwap = true; 
    } else {
        // Rango (prob_op1, 1.0] -> Operador 2 (Swap)
        esSwap = false;
    }

	if (esSwap && candidatos_poner.empty())
	{
		// No hay 0s para poner
		return;
	}

	int idx_borrar = candidatos_borrar[rand() % candidatos_borrar.size()];
	x_var[idx_borrar] = 0;

	if (esSwap)
	{
		int idx_poner = candidatos_poner[rand() % candidatos_poner.size()];
		x_var[idx_poner] = 1;
	}

}

void CUtilityToolBox::MutacionModificada_con_reubicacion(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *problemInstance)
{
	// 1 Verificar probabilidad
	double prob_mutation_rate = Get_Random_Number();
	if (prob_mutation_rate > mutation_rate)
	{
		return;
	}

	int n = x_var.size();

	// 2 Identificar candidatos
	std::vector<int> candidatos_borrar; // Donde hay 1s
	std::vector<int> candidatos_poner; // Donde hay 0s

	for (int i = 0; i < n; ++i)
	{
		if (x_var[i] == 1)
		{
			candidatos_borrar.push_back(i);
		}
		else {
			candidatos_poner.push_back(i);
		}
	}

	if (candidatos_borrar.empty())
	{
		// No hay 1s para eliminar
		return;
	}

	// 3 Decidir operador (Delete vs swap)
	double rnd = Get_Random_Number();
    bool esSwap = false;

    if (rnd <= prob_op1_delete) {
        // Rango [0, prob_op1] -> Operador 1 (Solo Delete)
        esSwap = false; 
    } else {
        // Rango (prob_op1, 1.0] -> Operador 2 (Swap)
        esSwap = true;
    }

	if (esSwap && candidatos_poner.empty()) {
        return; // No hay huecos para mover, abortar swap.
    }

	int idx_borrar = candidatos_borrar[rand() % candidatos_borrar.size()];
    x_var[idx_borrar] = 0;

	// Agregar (Swap)
    if (esSwap) {
        int idx_poner = candidatos_poner[rand() % candidatos_poner.size()];
        x_var[idx_poner] = 1;
    }

	// imprmir x_var
	/* std::cout << "Solución mutada (x_var): ";
	for (double val : x_var)
	{
		std::cout << val << " ";
	}
	std::cout << std::endl; */
}

void CUtilityToolBox::PolynomialMutation(vector<double> &x_var, double rate)
{
	double rand1, rand2, delta1, delta2, mut_pow, deltaq;
	double y, yl, yu, val, xy, lowBound = 0, uppBound = 1;
	double eta_m = 20;

	int nvar = x_var.size();

	for (unsigned int j = 0; j < nvar; j++)
	{
		rand1 = Get_Random_Number();
		if (rand1 <= rate)
		{
			y = x_var[j];
			yl = lowBound;
			yu = uppBound;
			delta1 = (y - yl) / (yu - yl);
			delta2 = (yu - y) / (yu - yl);
			rand2 = Get_Random_Number();
			mut_pow = 1.0 / (eta_m + 1.0);
			if (rand2 <= 0.5)
			{
				xy = 1.0 - delta1;
				val = 2.0 * rand2 + (1.0 - 2.0 * rand2) * (pow(xy, (eta_m + 1.0)));
				deltaq = pow(val, mut_pow) - 1.0;
			}
			else
			{
				xy = 1.0 - delta2;
				val = 2.0 * (1.0 - rand2) + 2.0 * (rand2 - 0.5) * (pow(xy, (eta_m + 1.0)));
				deltaq = 1.0 - (pow(val, mut_pow));
			}
			y = y + deltaq * (yu - yl);
			if (y < yl)
				y = yl;
			if (y > yu)
				y = yu;

			x_var[j] = y;
		}
	}
	return;
}

void CUtilityToolBox::CruzamientoUniformeModificado(vector<double> &x_var1, vector<double> &x_var2, vector<double> &child)
{
	int count1 = std::count(x_var1.begin(), x_var1.end(), 1.0);
	int count2 = std::count(x_var2.begin(), x_var2.end(), 1.0);

	int min_val = std::min(count1, count2);
	int max_val = std::max(count1, count2);
	int max_instalaciones = min_val + rand() % (max_val - min_val + 1); // incluye ambos extremos

	bool flag = false;

	if (flag)
	{
		max_instalaciones = static_cast<int>(std::round((count1 + count2) / 2.0));
	}

	int nvar = x_var1.size();
	child.assign(nvar, 0); // inicializa en 0s

	int instalaciones = 0;

	int start = rand() % nvar;

	for (int i = 0; i < nvar && instalaciones < max_instalaciones; ++i)
	{
		int idx = (start + i) % nvar;

		// std::cout << "Revisando índice idx = " << idx << std::endl;
		//  Si el padre1 tiene un 1, lo tomamos
		if (x_var1[idx] == 1)
		{
			child[idx] = 1;
			instalaciones++;
			// std::cout << "→ Se tomó de padre1 en idx = " << idx << std::endl;
		}
		else if (x_var2[idx] == 1)
		{
			child[idx] = 1;
			instalaciones++;
			// std::cout << "→ Se tomó de padre2 en idx = " << idx << std::endl;
		}
		// Si ambos son 0, se imprime pero no se instala
		else
		{
			// std::cout << "→ Ninguno tiene AED en idx = " << idx << std::endl;
		}
	}
}

void CUtilityToolBox::CruzamientoUniformeModificado_sin_reubicacion(vector<double> &x_var1, vector<double> &x_var2, vector<double> &child, ProblemInstance *problemInstance)
{
	int nvar = x_var1.size();
	child.assign(nvar, 0); // inicializa en 0s

	// Asegurar que los nodos preinstalados permanezcan como 1
	const auto &nodos = problemInstance->getNodes();
	int pre_instalados = 0;
	for (int i = 0; i < nvar; ++i)
	{
		if (nodos[i]->getFlag() == 1) // preinstalado
		{
			child[i] = 1;
			pre_instalados++;
		}
	}

	int count1 = std::count(x_var1.begin(), x_var1.end(), 1.0);
	int count2 = std::count(x_var2.begin(), x_var2.end(), 1.0);
	int min_total = std::min(count1, count2);
	int max_total = std::max(count1, count2);

	int max_instalaciones = 0;
	if (max_total > min_total)
	{
		max_instalaciones = min_total + rand() % (max_total - min_total + 1);
	}
	else
	{
		max_instalaciones = min_total; // ambos iguales
	}

	int a_instalar = max_instalaciones - pre_instalados;

	int start = rand() % nvar;
	int instalados = 0;
	for (int i = 0; i < nvar && instalados < a_instalar; ++i)
	{
		int idx = (start + i) % nvar;

		if (child[idx] == 1)
			continue; // ya es preinstalado, no cambiar

		if (x_var1[idx] == 1 || x_var2[idx] == 1)
		{
			child[idx] = 1;
			instalados++;
		}
	}
	// imprimir child
	/* std::cout << "Hijo generado (child): ";
	for (double val : child)
	{
		std::cout << val << " ";
	}
	std::cout << std::endl;
	// contar aeds instalados
	int total_aeds = std::count(child.begin(), child.end(), 1.0);
	std::cout << "Total AEDs instalados en el hijo: " << total_aeds;
	std::cout << std::endl; */
}

void CUtilityToolBox::CruzamientoUniformeModificado_con_reubicacion(vector<double> &x_var1, vector<double> &x_var2, vector<double> &child, ProblemInstance *problemInstance)
{
	int nvar = x_var1.size();
	child.assign(nvar, 0); // inicializa en 0s

	int count1 = std::count(x_var1.begin(), x_var1.end(), 1.0);
	int count2 = std::count(x_var2.begin(), x_var2.end(), 1.0);
	int min_total = std::min(count1, count2);
	int max_total = std::max(count1, count2);

	int max_instalaciones = 0;
	if (max_total > min_total) {
		max_instalaciones = min_total + rand() % (max_total - min_total + 1);
	} else {
		max_instalaciones = min_total; // ambos iguales
	}

	int start = rand() % nvar;
	int instalados = 0;
	for (int i = 0; i < nvar && instalados < max_instalaciones; ++i)
	{
		int idx = (start + i) % nvar;

		if (x_var1[idx] == 1 || x_var2[idx] == 1)
		{
			child[idx] = 1;
			instalados++;
		}
	}
	// imprimir child
	/* std::cout << "Hijo generado (child): ";
	for (double val : child)
	{
		std::cout << val << " ";
	}
	std::cout << std::endl;
	// contar aeds instalados
	int total_aeds = std::count(child.begin(), child.end(), 1.0);
	std::cout << "Total AEDs instalados en el hijo: " << total_aeds;
	std::cout << std::endl; */
	RepararPresupuesto_Relocation(child, problemInstance);
}

void CUtilityToolBox::SimulatedBinaryCrossover(vector<double> &x_var1, vector<double> &x_var2, vector<double> &x_var3)
{
	double rnd;
	double y1, y2, yl, yu;
	double c1, c2;
	double alpha, beta, betaq;
	double eta_c = 20;
	double lowBound = 0,
		   uppBound = 1;
	int nvar = x_var1.size();
	if (Get_Random_Number() <= 1.0)
	{
		for (int i = 0; i < nvar; i++)
		{
			if (Get_Random_Number() <= 0.5)
			{
				if (fabs(x_var1[i] - x_var2[i]) > EPS)
				{
					if (x_var1[i] < x_var2[i])
					{
						y1 = x_var1[i];
						y2 = x_var2[i];
					}
					else
					{
						y1 = x_var2[i];
						y2 = x_var1[i];
					}
					yl = lowBound;
					yu = uppBound;
					rnd = Get_Random_Number();
					beta = 1.0 + (2.0 * (y1 - yl) / (y2 - y1));
					alpha = 2.0 - pow(beta, -(eta_c + 1.0));
					if (rnd <= (1.0 / alpha))
					{
						betaq = pow((rnd * alpha), (1.0 / (eta_c + 1.0)));
					}
					else
					{
						betaq = pow((1.0 / (2.0 - rnd * alpha)), (1.0 / (eta_c + 1.0)));
					}
					c1 = 0.5 * ((y1 + y2) - betaq * (y2 - y1));
					beta = 1.0 + (2.0 * (yu - y2) / (y2 - y1));
					alpha = 2.0 - pow(beta, -(eta_c + 1.0));
					if (rnd <= (1.0 / alpha))
					{
						betaq = pow((rnd * alpha), (1.0 / (eta_c + 1.0)));
					}
					else
					{
						betaq = pow((1.0 / (2.0 - rnd * alpha)), (1.0 / (eta_c + 1.0)));
					}
					c2 = 0.5 * ((y1 + y2) + betaq * (y2 - y1));
					if (c1 < yl)
						c1 = yl;
					if (c2 < yl)
						c2 = yl;
					if (c1 > yu)
						c1 = yu;
					if (c2 > yu)
						c2 = yu;
					// if(rand()<=0.5)
					if (Get_Random_Number() <= 0.5)
					{
						x_var3[i] = c2;
						// child2.x_var[i] = c1;
					}
					else
					{
						x_var3[i] = c1;
						// child2.x_var[i] = c2;
					}
				}
				else
				{
					x_var3[i] = x_var1[i];
					// child2.x_var[i] = parent2.x_var[i];
				}
			}
			else
			{
				x_var3[i] = x_var1[i];
				// child2.x_var[i] = parent2.x_var[i];
			}
		}
	}
	else
	{
		for (int i = 0; i < nvar; i++)
		{
			x_var3[i] = x_var1[i];
			// child2.x_var[i] = parent2.x_var[i];
		}
	}
	return;
}

void CUtilityToolBox::DifferentialEvolution(vector<double> &x_var0, vector<double> &x_var1, vector<double> &x_var2, vector<double> &x_var, double rate)
{
	double rand0 = Get_Random_Number();
	int idx_rnd = int(rand0 * x_var.size());

	double lowBound = 0, uppBound = 1;

	for (unsigned int n = 0; n < x_var.size(); n++)
	{
		/*Selected Two Parents*/

		// strategy one
		// x_var[n] = x_var0[n] + rate*(x_var2[n] - x_var1[n]);

		//*
		// strategy two
		double rand1 = Get_Random_Number();

		double CR = 1.0;
		if (rand1 < CR || n == idx_rnd)
			x_var[n] = x_var0[n] + rate * (x_var2[n] - x_var1[n]);
		else
			x_var[n] = x_var0[n];
		//*/

		// handle the boundary voilation
		if (x_var[n] < lowBound)
		{
			double rand2 = Get_Random_Number();
			x_var[n] = lowBound + rand2 * (x_var0[n] - lowBound);
		}
		if (x_var[n] > uppBound)
		{
			double rand3 = Get_Random_Number();
			x_var[n] = uppBound - rand3 * (uppBound - x_var0[n]);
		}
	}
}

int CUtilityToolBox::GetWeightNumber(int nobj, int H)
{
	int a = H + nobj - 1, b = nobj - 1, prod1 = 1, prod2 = 1;

	for (int i = 1; i <= b; i++)
		prod1 *= (a - i + 1);
	for (int j = 1; j <= b; j++)
		prod2 *= j;

	return int(1.0 * prod1 / prod2);
}

double CUtilityToolBox::MaxElementInVector(vector<double> &vect)
{
	double max_e = vect[0];
	for (unsigned n = 1; n < vect.size(); n++)
	{
		if (vect[n] > max_e)
		{
			max_e = vect[n];
		}
	}
	return max_e;
}

double CUtilityToolBox::Get_Random_Number()
{
	return Rnd_Uni(&rnd_uni_init);
}

double CUtilityToolBox::Rnd_Uni(long *idum)
{

	long j;
	long k;
	static long idum2 = 123456789;
	static long iy = 0;
	static long iv[NTAB];
	double temp;

	if (*idum <= 0)
	{
		if (-(*idum) < 1)
			*idum = 1;
		else
			*idum = -(*idum);
		idum2 = (*idum);
		for (j = NTAB + 7; j >= 0; j--)
		{
			k = (*idum) / IQ1;
			*idum = IA1 * (*idum - k * IQ1) - k * IR1;
			if (*idum < 0)
				*idum += IM1;
			if (j < NTAB)
				iv[j] = *idum;
		}
		iy = iv[0];
	}
	k = (*idum) / IQ1;
	*idum = IA1 * (*idum - k * IQ1) - k * IR1;
	if (*idum < 0)
		*idum += IM1;
	k = idum2 / IQ2;
	idum2 = IA2 * (idum2 - k * IQ2) - k * IR2;
	if (idum2 < 0)
		idum2 += IM2;
	j = iy / NDIV;
	iy = iv[j] - idum2;
	iv[j] = *idum;
	if (iy < 1)
		iy += IMM1;
	if ((temp = AM * iy) > RNMX)
		return RNMX;
	else
		return temp;
}


// =========================================================================
// 1. FILTRO INTELIGENTE
// =========================================================================
bool CUtilityToolBox::EsBuenCandidato(int idx_candidato, ProblemInstance *instance)
{
    const auto &nodos = instance->getNodes();
    
    // Si es cámara, no poner otro.
    if (nodos[idx_candidato]->getFlag() == 1) return false;

    const std::vector<int>& vecinos = instance->getNodosCubiertosPor(idx_candidato);
    
    int ganancia = 0;
    for (int id_vecino : vecinos) 
    {
        // Es buen candidato si cubre demanda (Flag 0) que NO está pre-cubierta por cámaras
        if (nodos[id_vecino]->getFlag() == 0 && !instance->isPreCubierto(id_vecino)) 
        {
            ganancia++;
            if (ganancia >= 1) return true; // Con cubrir a 1 nuevo basta
        }
    }
    return false;
}

bool CUtilityToolBox::EsBuenCandidato_Relocation(int idx_candidato, ProblemInstance *instance)
{
	const auto &nodos = instance->getNodes();

    const std::vector<int>& vecinos = instance->getNodosCubiertosPor(idx_candidato);
    double ganancia = 0.0;
    ganancia += nodos[idx_candidato]->getProbOhca();
    for (int id_vecino : vecinos) 
    {
        // Buscamos si cubre a alguien con demanda
        // (Nota: Si tu instancia tiene "PreCubierto" real por cosas externas al problema, mantenlo.
        //  Si "PreCubierto" se refería a los AEDs Flag=1, quítalo).
        ganancia += nodos[id_vecino]->getProbOhca();
    }
    if (ganancia >= 1.0e-9){
        return true;
    }

    return false;
}

// =========================================================================
// 2. CRUZAMIENTO INTELIGENTE (Preserva estructuras)
// =========================================================================
void CUtilityToolBox::CruzamientoInteligente(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance)
{
    int n = parent1.size();
    child.assign(n, 0.0);
    const auto &nodos = instance->getNodes();

    std::vector<int> pool_disputa; 
    int c1 = 0, c2 = 0, herencia_comun = 0;

    for (int i = 0; i < n; ++i) {
        if (nodos[i]->getFlag() == 1) { child[i] = 1.0; continue; } // Heredar Cámaras

        bool p1 = (parent1[i] == 1);
        bool p2 = (parent2[i] == 1);
        if (p1) c1++;
        if (p2) c2++;

        if (p1 && p2) { // Intersección: Ambos padres lo tienen -> Heredar
            child[i] = 1.0;
            herencia_comun++;
        } else if (p1 || p2) { // Unión: Solo uno -> Disputa
            pool_disputa.push_back(i);
        }
    }

    // Objetivo: Promedio de padres, limitado por presupuesto
    int target = std::min((c1 + c2) / 2, (int)instance->getP());
    int faltan = target - herencia_comun;

    if (faltan > 0) {
        std::random_shuffle(pool_disputa.begin(), pool_disputa.end());
        int agregados = 0;
        
        // Ronda 1: Solo los buenos
        for (int idx : pool_disputa) {
            if (agregados >= faltan) break;
            if (EsBuenCandidato(idx, instance)) {
                child[idx] = 1.0;
                agregados++;
            }
        }
        // Ronda 2: Relleno si falta
        if (agregados < faltan) {
            for (int idx : pool_disputa) {
                if (agregados >= faltan) break;
                if (child[idx] == 0) { child[idx] = 1.0; agregados++; }
            }
        }
    }
}




// =========================================================================
//  NEW
// =========================================================================

void CUtilityToolBox::RepararPresupuesto(vector<double> &x_var, ProblemInstance *instance)
{
    int max_P = instance->getP();
    const auto &nodos = instance->getNodes();
    int n = x_var.size();

    // 1. Identificar activos que se pueden borrar (flag 0)
    std::vector<int> activos_moviles;
    int total_activos = 0;

    for(int i=0; i<n; ++i) {
        if(x_var[i] == 1) {
            total_activos++;
            if(nodos[i]->getFlag() == 0) activos_moviles.push_back(i);
        }
    }

    // 2. Si nos pasamos, eliminar los peores
    if (total_activos > max_P) {
        int a_quitar = total_activos - max_P;
        
        // Calcular aporte marginal
        std::vector<std::pair<double, int>> calidad;
        for(int idx : activos_moviles) {
            double aporte = 0.0;
            const auto& vec = instance->getNodosCubiertosPor(idx);
            for(int v : vec) {
                if(!instance->isPreCubierto(v)) aporte += nodos[v]->getProbOhca();
            }
            calidad.push_back({aporte, idx});
        }
        
        // Ordenar menor a mayor calidad
        std::sort(calidad.begin(), calidad.end());

        // Apagar los primeros 'a_quitar'
        for(int k=0; k<a_quitar && k<(int)calidad.size(); ++k) {
            x_var[calidad[k].second] = 0;
        }
    }
}

void CUtilityToolBox::MutacionBitFlip_1_N(vector<double> &x_var, double mutation_rate, ProblemInstance *instance)
{
    // A. Verificar tasa global
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = instance->getNodes();

    // B. Calcular N efectivo (Solo nodos movibles, excluyendo cámaras)
    int n_efectivo = 0;
    for(auto* node : nodos) {
        if (node->getFlag() == 0) n_efectivo++;
    }
    if (n_efectivo == 0) n_efectivo = 1; // Evitar división por cero

    double prob = 1.0 / (double)n_efectivo;

    // C. Iterar y mutar
    for (int i = 0; i < n; ++i)
    {
        if (nodos[i]->getFlag() == 1) continue; // Saltar fijos

        if (Get_Random_Number() <= prob)
        {
            if (x_var[i] == 1) x_var[i] = 0; // Apagar
            else {
                // Encender solo si sirve
                if (EsBuenCandidato(i, instance)) x_var[i] = 1;
            }
        }
    }

    // D. Reparar
    RepararPresupuesto(x_var, instance);
}

void CUtilityToolBox::MutacionBitFlip_1_M(vector<double> &x_var, double mutation_rate, int populationSize, ProblemInstance *instance)
{
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = instance->getNodes();

    // Probabilidad basada en el tamaño de la población
    // Esto suele ser MUCHO más agresivo que 1/N.
    double prob = 1.0 / (double)populationSize;

    for (int i = 0; i < n; ++i)
    {
        if (nodos[i]->getFlag() == 1) continue;

        if (Get_Random_Number() <= prob)
        {
            if (x_var[i] == 1) x_var[i] = 0;
            else {
                if (EsBuenCandidato(i, instance)) x_var[i] = 1;
            }
        }
    }

    RepararPresupuesto(x_var, instance);
}

void CUtilityToolBox::MutacionBitFlip_Fijo(vector<double> &x_var, double mutation_rate, double fixed_prob, ProblemInstance *instance)
{
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = instance->getNodes();

    // Probabilidad fija (ej. 0.01, 0.3, etc.)
    double prob = fixed_prob;

    for (int i = 0; i < n; ++i)
    {
        if (nodos[i]->getFlag() == 1) continue;

        if (Get_Random_Number() <= prob)
        {
            if (x_var[i] == 1) x_var[i] = 0;
            else {
                if (EsBuenCandidato(i, instance)) x_var[i] = 1;
            }
        }
    }

    RepararPresupuesto(x_var, instance);
}


void CUtilityToolBox::MutacionSwapProbabilistico(vector<double> &x_var, double mutation_rate, double MutProbSwap, ProblemInstance *instance)
{
    // 1. Probabilidad Global
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = instance->getNodes();

    // Creamos una lista de espacios vacíos para no buscarlos a ciegas
    std::vector<int> espacios_vacios;
    for(int i=0; i<n; ++i) {
        if(x_var[i] == 0 && nodos[i]->getFlag() == 0) {
            espacios_vacios.push_back(i);
        }
    }
    
    // Barajamos los vacíos para elegir al azar rápido
    if (espacios_vacios.empty()) return;
    std::random_shuffle(espacios_vacios.begin(), espacios_vacios.end());
    int idx_vacio = 0;

    // 2. Recorremos los equipos instalados
    for (int i = 0; i < n; ++i)
    {
        // Solo tocamos equipos activos que NO sean cámaras
        if (x_var[i] == 1 && nodos[i]->getFlag() == 0)
        {
            // ¿Este equipo se muda?
            if (Get_Random_Number() <= MutProbSwap)
            {
                // PASO A: Apagar el equipo actual (Delete)
                x_var[i] = 0; 

                // PASO B: Buscar un nuevo lugar (Add)
                // Buscamos en la lista de vacíos hasta encontrar uno BUENO
                bool reubicado = false;
                
                while (idx_vacio < (int)espacios_vacios.size())
                {
                    int candidato = espacios_vacios[idx_vacio];
                    idx_vacio++;

                    // Usamos tu filtro: Solo nos mudamos si el nuevo lugar aporta valor
                    if (EsBuenCandidato(candidato, instance)) 
                    {
                        x_var[candidato] = 1;
                        reubicado = true;
                        break; // ¡Mudanza exitosa! Pasamos al siguiente equipo
                    }
                }

                // Si se nos acabaron los candidatos buenos en todo el mapa (raro),
                // volvemos a encender el original para no perder el equipo.
                if (!reubicado) {
                    x_var[i] = 1;
                }
            }
        }
    }
    
    // (Opcional) Reparar presupuesto por si acaso algo falló, aunque el swap mantiene la cuenta.
    RepararPresupuesto(x_var, instance);
}


void CUtilityToolBox::Mutacion_Swap_Porcentual_1_N(vector<double> &x_var, double mutation_rate, double ratio_swap, double mutPctSwap, ProblemInstance *instance)
{
    // Tiramos una moneda para decidir qué estrategia usar
    double dado = Get_Random_Number();

    if (dado <= ratio_swap){
        MutacionBitFlip_1_N(x_var, mutation_rate, instance);
    }
    else {
        MutacionSwapPorcentual(x_var, mutation_rate, mutPctSwap, instance);
    }
}

void CUtilityToolBox::Mutacion_Swap_Porcentual_1_M(vector<double> &x_var, double mutation_rate, double ratio_swap, double populationSize, double mutPctSwap, ProblemInstance *instance)
{
    // Tiramos una moneda para decidir qué estrategia usar
    double dado = Get_Random_Number();

    if (dado <= ratio_swap)
    {
        MutacionBitFlip_1_M(x_var, mutation_rate, populationSize, instance);
    }
    else
    {
        MutacionSwapPorcentual(x_var, mutation_rate, mutPctSwap, instance);
    }
}

void CUtilityToolBox::Mutacion_Swap_Porcentual_Fijo(vector<double> &x_var, double mutation_rate, double ratio_swap, double fixed_prob, double mutPctSwap, ProblemInstance *instance)
{
    // Tiramos una moneda para decidir qué estrategia usar
    double dado = Get_Random_Number();

    if (dado <= ratio_swap)
    {
        MutacionBitFlip_Fijo(x_var, mutation_rate, fixed_prob, instance);
    }
    else
    {
        MutacionSwapPorcentual(x_var, mutation_rate, mutPctSwap, instance);
    }
}


void CUtilityToolBox::CruzamientoUniformeInteligente(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance)
{
    int n = parent1.size();
    child.assign(n, 0.0);
    const auto &nodos = instance->getNodes();

    for (int i = 0; i < n; ++i)
    {
        // 1. Siempre heredar infraestructura fija (Cámaras)
        if (nodos[i]->getFlag() == 1) {
            child[i] = 1.0;
            continue; 
        }

        bool p1_has = (parent1[i] == 1);
        bool p2_has = (parent2[i] == 1);

        if (p1_has && p2_has) 
        {
            // A. Intersección: Ambos padres lo tienen -> Heredar seguro.
            // (Asumimos que si ambos lo tienen, es un buen lugar)
            child[i] = 1.0;
        }
        else if (p1_has || p2_has) 
        {
            // B. Unión: Solo uno lo tiene -> Probabilidad 50%
            if (Get_Random_Number() < 0.5) 
            {
                // C. FILTRO INTELIGENTE:
                // Solo lo heredamos si realmente aporta valor.
                // Si el padre lo tenía pero era redundante (cubría cámaras),
                // el hijo NO lo hereda. ¡Limpieza genética!
                if (EsBuenCandidato(i, instance)) {
                    child[i] = 1.0;
                }
            }
        }
    }

    // 2. Reparación de Presupuesto (Por si la unión generó demasiados)
    RepararPresupuesto(child, instance);
}

void CUtilityToolBox::CruzamientoUniformeSemiInteligente(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance)
{
    int n = parent1.size();
    child.assign(n, 0.0);
    const auto &nodos = instance->getNodes();

    for (int i = 0; i < n; ++i)
    {
        // 1. Siempre heredar infraestructura fija (Cámaras)
        if (nodos[i]->getFlag() == 1) {
            child[i] = 1.0;
            continue; 
        }

        bool p1_has = (parent1[i] == 1);
        bool p2_has = (parent2[i] == 1);

        if (p1_has && p2_has) 
        {
            // A. Intersección: Ambos padres lo tienen -> Heredar seguro.
            // (Asumimos que si ambos lo tienen, es un buen lugar)
            child[i] = 1.0;
        }
        else if (p1_has || p2_has) 
        {
            // B. Unión: Solo uno lo tiene -> Probabilidad 50%
            if (Get_Random_Number() < 0.5) 
            {
				// C. SIN FILTRO INTELIGENTE:
                    child[i] = 1.0;
            }
        }
    }

    // 2. Reparación de Presupuesto (Por si la unión generó demasiados)
    RepararPresupuesto(child, instance);
}



void CUtilityToolBox::MutacionDeletePorcentual(vector<double> &x_var, double mutation_rate, double mutPctDelete, ProblemInstance *instance)
{
    // 1. Probabilidad global
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = instance->getNodes();

    // 2. Identificar víctimas (AEDs móviles activos)
    std::vector<int> instalados_moviles;
    
    for (int i = 0; i < n; ++i) {
        // Solo consideramos si está activo (1) y es móvil (Flag 0)
        if (x_var[i] == 1 && nodos[i]->getFlag() == 0) {
            instalados_moviles.push_back(i);
        }
    }

    if (instalados_moviles.empty()) return; // Nada que borrar

    // 3. Calcular cantidad a eliminar
    // Mínimo 1 si hay al menos un equipo y el ratio > 0
    int total_actual = instalados_moviles.size();
    int a_borrar = static_cast<int>(std::ceil(total_actual * mutPctDelete));
    
    if (a_borrar < 1) a_borrar = 1;
    if (a_borrar > total_actual) a_borrar = total_actual;

    // 4. Ejecutar borrado aleatorio
    // Usamos shuffle para que la eliminación sea impredecible (exploración)
    std::random_shuffle(instalados_moviles.begin(), instalados_moviles.end());

    for (int k = 0; k < a_borrar; ++k) {
        int idx_victima = instalados_moviles[k];
        x_var[idx_victima] = 0;
    }
}

void CUtilityToolBox::MutacionSwapPorcentual(vector<double> &x_var, double mutation_rate, double mutPctSwap, ProblemInstance *instance)
{
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = instance->getNodes();
    
    // 1. Identificar activos para mover y huecos para poner
    std::vector<int> instalados;
    std::vector<int> vacios;

    for (int i = 0; i < n; ++i) {
        if (nodos[i]->getFlag() == 1) continue;
        if (x_var[i] == 1) instalados.push_back(i);
        else vacios.push_back(i);
    }

    if (instalados.empty() || vacios.empty()) return;

    // 2. Calcular cantidad
    int cantidad = std::max(1, (int)(instalados.size() * mutPctSwap));
    
    // 3. Ejecutar el movimiento (Borrar + Insertar Inteligente)
    std::random_shuffle(instalados.begin(), instalados.end());
    std::random_shuffle(vacios.begin(), vacios.end());

    // Borrar
    for (int k = 0; k < cantidad; ++k) x_var[instalados[k]] = 0;

    // Insertar (Solo si es buen candidato)
    int puestos = 0;
    int idx = 0;
    while (puestos < cantidad && idx < (int)vacios.size()) {
        int cand = vacios[idx++];
        if (EsBuenCandidato(cand, instance)) {
            x_var[cand] = 1;
            puestos++;
        }
    }
}

void CUtilityToolBox::MutacionHibrida_location(vector<double> &x_var, double mutation_rate, double prob_delete, double mutPctDelete, double mutPctSwap, ProblemInstance *instance)
{
    double rnd = Get_Random_Number();

    if (rnd <= prob_delete) 
    {
        // CAMINO A: SOLO BORRAR (Reducir costos / Limpiar)
        MutacionDeletePorcentual(x_var, mutation_rate, mutPctDelete, instance);
    } 
    else 
    {
        // CAMINO B: SWAP (Optimizar cobertura manteniendo costos)
        MutacionSwapPorcentual(x_var, mutation_rate, mutPctSwap, instance);
    }
}





void CUtilityToolBox::CruzamientoUniformeReloc(const vector<double>& p1,
                              const vector<double>& p2,
                              vector<double>& child,
                              ProblemInstance* inst)
{
    int n = p1.size();
    child.assign(n, 0.0);

    for (int i=0;i<n;++i){
        bool p1_tiene = (p1[i] > 0.5);
        bool p2_tiene = (p2[i] > 0.5);

        if (p1_tiene && p2_tiene) child[i] = 1.0;
        else if (p1_tiene || p2_tiene) {
			if (Get_Random_Number() < 0.5) {
				child[i] = 1.0;
			};
    	}
	}

    RepararPresupuesto_Relocation(child, inst); // NUEVA
}

void CUtilityToolBox::MutacionDeletePorcentualReloc(vector<double>& x, double mutation_rate,
                                  double delete_ratio, ProblemInstance* inst)
{
    if (Get_Random_Number() > mutation_rate) return;

    int n = x.size();
    vector<int> activos;
    activos.reserve(n);
    for(int i=0;i<n;++i) {
        if (x[i] > 0.5) activos.push_back(i);
	}

    if (activos.empty()) return;

	int stock_original = 0;
	const auto&nodos = inst->getNodes();
	for (auto* nodo : nodos) {
		if (nodo->getFlag() == 1) stock_original++;
	}

	int excedente = activos.size() - stock_original;

	if (excedente <= 0) {
		return;
	}

    int a_borrar_deseado = (int)std::ceil(activos.size() * delete_ratio);

    int a_borrar_real = std::min(a_borrar_deseado, excedente);

	if (a_borrar_real < 1) return;

    std::random_shuffle(activos.begin(), activos.end());
    for(int k=0;k<a_borrar_real;++k) x[activos[k]] = 0.0;

}

void CUtilityToolBox::MutacionSwapPorcentualReloc(vector<double>& x_var, double mutation_rate,
                                double swap_ratio, ProblemInstance* inst)
{
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    vector<int> activos, vacios;
    activos.reserve(n); vacios.reserve(n);

    for(int i=0;i<n;++i){
        if (x_var[i] > 0.5) activos.push_back(i);
        else vacios.push_back(i);
    }
    if (activos.empty() || vacios.empty()) return;

    int cant = std::max(1, (int)(activos.size()*swap_ratio));

    std::random_shuffle(activos.begin(), activos.end());
    std::random_shuffle(vacios.begin(), vacios.end());

	// Desactivamos activos
    for(int k=0; k < cant && k < activos.size(); ++k){
        x_var[activos[k]] = 0.0;
    }

	int puestos = 0;
	int idx = 0;

	while (puestos < cant && idx < vacios.size()) {
		int cand = vacios[idx++];
		if (EsBuenCandidato_Relocation(cand, inst)) {
			x_var[cand] = 1.0;
			puestos++;
		}
	}
}

void CUtilityToolBox::MutacionHibridaReloc(std::vector<double>& x,
                                          double mutation_rate,
                                          double prob_delete,
                                          double mutPctDelete,
                                          double mutPctSwap,
                                          ProblemInstance* inst)
{
    // 1) Gate global (igual que tus otras mutaciones)
    if (Get_Random_Number() > mutation_rate) return;

    // 2) Elegir camino
    double rnd = Get_Random_Number();

    if (rnd <= prob_delete)
    {
        // Camino A: Delete (reduce n_new, cambia r dependiendo de qué borre)
        // Nota: aquí pasamos mutation_rate=1 porque ya aplicamos el gate arriba
        MutacionDeletePorcentualReloc(x, 1.0, mutPctDelete, inst);
		//MutacionSwapPorcentualReloc(x, 1.0, mutPctSwap, inst);
    }
    else
    {
        // Camino B: Swap (mueve masa, mantiene total, puede cambiar r)
        MutacionSwapPorcentualReloc(x, 1.0, mutPctSwap, inst);
    }

    // 3) Por seguridad: una reparación final (aunque las hijas ya reparan)
    RepararPresupuesto_Relocation(x, inst);
}


void CUtilityToolBox::RepararPresupuesto_Relocation(vector<double> &x_var,
                                             ProblemInstance* instance)
{
    int max_P = instance->getP();
    const auto &nodos = instance->getNodes();
    int n = x_var.size();


	std::vector<int> indices_activos;
	for(int i = 0; i< n; ++i) {
		if (x_var[i] > 0.5) {
			indices_activos.push_back(i);
		}
	}
	int total_activos = indices_activos.size();

	if (total_activos > max_P) {
		int a_quitar = total_activos - max_P;
		std::vector<std::pair<double, int>> calidad;
		calidad.reserve(total_activos);

		for(int idx : indices_activos) {
            double aporte = 0.0;
            // Obtenemos vecinos que cubre este nodo
            const auto& vecinos = instance->getNodosCubiertosPor(idx);
            
            for(int v : vecinos) {
                // Sumamos probabilidad solo si NO está cubierto por otros FIJOS externos
                // (En relocación asumimos que todo se puede mover, así que calculamos aporte bruto)
                // OJO: Si usas isPreCubierto aquí, asegúrate que se refiera a cosas externas al problema.
                aporte += nodos[v]->getProbOhca();
            }
            calidad.push_back({aporte, idx});
        }
		std::sort(calidad.begin(), calidad.end());

        // 5. Apagar los peores
        for(int k=0; k<a_quitar && k<(int)calidad.size(); ++k) {
            x_var[calidad[k].second] = 0.0;
        }
	}
}



void CUtilityToolBox::CruzamientoUniformeSemiInteligente_Relocation(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance)
{
    int n = parent1.size();
    child.assign(n, 0.0);
    const auto &nodos = instance->getNodes();

    for (int i = 0; i < n; ++i)
    {
        bool p1_has = (parent1[i] == 1);
        bool p2_has = (parent2[i] == 1);

        if (p1_has && p2_has) 
        {
            child[i] = 1.0;
        }
        else if (p1_has || p2_has) 
        {
            if (Get_Random_Number() < 0.5) 
            {
                    child[i] = 1.0;
            }
        }
    }

    // 2. Reparación de Presupuesto (Por si la unión generó demasiados)
    RepararPresupuesto_Relocation(child, instance);
}



void CUtilityToolBox::CruzamientoUniformeInteligente_Relocation(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance)
{
    int n = parent1.size();
    child.assign(n, 0.0);

    for (int i = 0; i < n; ++i)
    {
        bool p1_has = (parent1[i] > 0.5);
        bool p2_has = (parent2[i] > 0.5);

        if (p1_has && p2_has) 
        {
            // Intersección -> Heredar
            child[i] = 1.0;
        }
        else if (p1_has || p2_has) 
        {
            // Unión -> Heredar con probabilidad, PERO FILTRADO
            if (Get_Random_Number() < 0.5) 
            {
                // Solo lo ponemos si realmente cubre a alguien
                // Usamos la versión _Relocation de la heurística
                if (EsBuenCandidato_Relocation(i, instance)) {
                    child[i] = 1.0;
                }
            }
        }
    }

    RepararPresupuesto_Relocation(child, instance);
}


void CUtilityToolBox::CruzamientoGeografico_Relocation(const vector<double> &p1, const vector<double> &p2, vector<double> &child, ProblemInstance *instance)
{
    int n = p1.size();
    child.assign(n, 0.0);
    const auto &nodos = instance->getNodes();

    // 1. Determinar límites del mapa (bounding box) para saber dónde cortar
    // (Esto se podría pre-calcular en ProblemInstance para eficiencia, pero lo hacemos aquí por simplicidad)
    double min_x = 1e9, max_x = -1e9;
    double min_y = 1e9, max_y = -1e9;
    
    // Muestreo rápido para estimar límites (o recorrer todo si N es pequeño)
    for(int i=0; i<n; i+=5) { // saltamos de 5 en 5 para rapidez
        double x = nodos[i]->getX();
        double y = nodos[i]->getY();
        if(x < min_x) min_x = x; if(x > max_x) max_x = x;
        if(y < min_y) min_y = y; if(y > max_y) max_y = y;
    }

    // 2. Elegir tipo de corte (Vertical u Horizontal) aleatoriamente
    bool corte_vertical = (Get_Random_Number() < 0.5);
    
    // 3. Elegir punto de corte
    double punto_corte;
    if(corte_vertical) {
        punto_corte = min_x + Get_Random_Number() * (max_x - min_x);
    } else {
        punto_corte = min_y + Get_Random_Number() * (max_y - min_y);
    }

    // 4. Construir hijo
    for(int i=0; i<n; ++i) {
        double pos = corte_vertical ? nodos[i]->getX() : nodos[i]->getY();
        
        if (pos < punto_corte) {
            // Zona Izquierda/Arriba -> Hereda de Padre 1
            if (p1[i] > 0.5) child[i] = 1.0;
        } else {
            // Zona Derecha/Abajo -> Hereda de Padre 2
            if (p2[i] > 0.5) child[i] = 1.0;
        }
    }

    // 5. Reparar (Siempre necesario en relocación)
    RepararPresupuesto_Relocation(child, instance);
}


void CUtilityToolBox::MutacionBitFlip_Relocation(vector<double> &x_var, double mutation_rate, double bit_prob, ProblemInstance *instance)
{
    // Gate global
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();

    for (int i = 0; i < n; ++i)
    {
        // EN RELOCACIÓN: NO hay "continue" para flags. Todos son mutables.
        
        if (Get_Random_Number() <= bit_prob)
        {
            if (x_var[i] > 0.5) {
                x_var[i] = 0.0; // Apagar (Ahorra costo, pierde cobertura)
            } else {
                // Encender (Gasta costo, gana cobertura)
                // Opcional: Solo encender si es "Buen Candidato" para no llenar de basura
                if (EsBuenCandidato_Relocation(i, instance)) {
                    x_var[i] = 1.0;
                }
            }
        }
    }

    // Reparar es vital porque BitFlip puede agregar muchos costos nuevos
    RepararPresupuesto_Relocation(x_var, instance);
}

void CUtilityToolBox::MutacionSwapProbabilisticoReloc(vector<double> &x_var, double mutation_rate, double MutProbSwap, ProblemInstance *instance)
{
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    
    // 1. Identificar vacíos (sin importar flags)
    std::vector<int> espacios_vacios;
    espacios_vacios.reserve(n);
    for(int i=0; i<n; ++i) {
        if(x_var[i] < 0.5) espacios_vacios.push_back(i);
    }
    
    if (espacios_vacios.empty()) return;
    std::random_shuffle(espacios_vacios.begin(), espacios_vacios.end());
    int idx_vacio = 0;

    // 2. Recorrer activos
    // Creamos una lista de activos para no modificar x_var mientras iteramos linealmente
    std::vector<int> activos;
    for(int i=0; i<n; ++i) if(x_var[i] > 0.5) activos.push_back(i);
    
    // Barajamos activos para no privilegiar el orden de los nodos
    std::random_shuffle(activos.begin(), activos.end());

    for (int i : activos)
    {
        // ¿Este equipo se muda?
        if (Get_Random_Number() <= MutProbSwap)
        {
            // PASO A: Apagar (Delete)
            x_var[i] = 0.0; 

            // PASO B: Buscar nuevo lugar (Add)
            bool reubicado = false;
            
            while (idx_vacio < (int)espacios_vacios.size())
            {
                int candidato = espacios_vacios[idx_vacio];
                idx_vacio++;

                // Verificar si el candidato sigue vacío (podría haberse llenado en otro swap)
                if (x_var[candidato] > 0.5) continue;

                if (EsBuenCandidato_Relocation(candidato, instance)) 
                {
                    x_var[candidato] = 1.0;
                    reubicado = true;
                    break;
                }
            }

            // Si no encontramos casa, devolvemos el AED a su lugar original (deshacer delete)
            if (!reubicado) {
                x_var[i] = 1.0;
            }
        }
    }
    // Swap no altera el costo total (generalmente), pero por seguridad:
    RepararPresupuesto_Relocation(x_var, instance);
}


// Fusión 1: BitFlip (1/N) vs Swap Porcentual
void CUtilityToolBox::Mutacion_Reloc_Fusion_1_N(vector<double> &x_var, double mutation_rate, double ratio_split, double mutPctSwap, ProblemInstance *instance)
{
    // ratio_split decide: ¿Hago BitFlip o hago Swap?
    double dado = Get_Random_Number();

    if (dado <= ratio_split) {
        // Opción A: BitFlip 1/N (Agresividad baja dependiente del tamaño)
        double prob = 1.0 / (double)x_var.size();
        MutacionBitFlip_Relocation(x_var, mutation_rate, prob, instance);
    }
    else {
        // Opción B: Mover equipos existentes
        MutacionSwapPorcentualReloc(x_var, mutation_rate, mutPctSwap, instance);
    }
}

// Fusión 2: BitFlip (1/M) vs Swap Porcentual (M = Población)
void CUtilityToolBox::Mutacion_Reloc_Fusion_1_M(vector<double> &x_var, double mutation_rate, double ratio_split, int populationSize, double mutPctSwap, ProblemInstance *instance)
{
    double dado = Get_Random_Number();

    if (dado <= ratio_split) {
        // Opción A: BitFlip 1/M (Agresividad depende de la población)
        double prob = 1.0 / (double)populationSize;
        MutacionBitFlip_Relocation(x_var, mutation_rate, prob, instance);
    }
    else {
        MutacionSwapPorcentualReloc(x_var, mutation_rate, mutPctSwap, instance);
    }
}

// Fusión 3: BitFlip (Fijo) vs Swap Porcentual
void CUtilityToolBox::Mutacion_Reloc_Fusion_Fijo(vector<double> &x_var, double mutation_rate, double ratio_split, double fixed_prob, double mutPctSwap, ProblemInstance *instance)
{
    double dado = Get_Random_Number();

    if (dado <= ratio_split) {
        // Opción A: BitFlip Fijo (ej. 1% por gen)
        MutacionBitFlip_Relocation(x_var, mutation_rate, fixed_prob, instance);
    }
    else {
        MutacionSwapPorcentualReloc(x_var, mutation_rate, mutPctSwap, instance);
    }
}


void CUtilityToolBox::OnePointCrossover(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance){

    const int n = (int)parent1.size();
    child.assign(n, 0.0);

    int start = -1, end = -1;

    for (int i = 0; i < n; ++i){
        if (instance->getNodes()[i]->getFlag() == 0){
            start = i; break;
        }
    }
    for (int i = n-1; i >= 0; --i){
        if (instance->getNodes()[i]->getFlag() == 0){
            end = i; break;
        }
    }
    if (start == -1 || end == -1 || end <= start){
        child = parent1;
        return;
    }

    const int span = (end - start);
    int cut = start + (int)(Get_Random_Number() * span);

    for (int i = 0; i < start; ++i) child[i] = parent1[i];

    for (int i = start; i <= cut; ++i) child[i] = parent1[i];
    for (int i = cut+1; i <= end; ++i) child[i] = parent2[i];

    for (int i = end+1; i < n; ++i) child[i] = parent1[i];

    for (int i = 0; i < n; ++i) child[i] = (child[i] > 0.5) ? 1.0 : 0.0; 
}



void CUtilityToolBox::OnePointCrossover_Relocation(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance){

    const int n = (int)parent1.size();
    child.assign(n, 0.0);

    int start = 0, end = n-1;

    const int span = (end - start);
    int cut = start + (int)(Get_Random_Number() * span);

    for (int i = 0; i < start; ++i) child[i] = parent1[i];

    for (int i = start; i <= cut; ++i) child[i] = parent1[i];
    for (int i = cut+1; i <= end; ++i) child[i] = parent2[i];

    for (int i = end+1; i < n; ++i) child[i] = parent1[i];

    for (int i = 0; i < n; ++i) child[i] = (child[i] > 0.5) ? 1.0 : 0.0; 
}

void CUtilityToolBox::TwoPointCrossover(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance){

    const int n = (int)parent1.size();
    child.assign(n, 0.0);

    int start = -1, end = -1;

    const auto& nodes = instance->getNodes();

    for (int i = 0; i < n; ++i){
        if (nodes[i]->getFlag() == 0){
            start = i; break;
        }
    }
    for (int i = n-1; i >= 0; --i){
        if (nodes[i]->getFlag() == 0){
            end = i; break;
        }
    }
    if (start == -1 || end == -1 || (end - start) < 2){
        child = parent1;
        return;
    }

    int cut1 = start + (int)(Get_Random_Number() * (end - start));
    if (cut1 > end - 2) cut1 = end - 2;

    int cut2 = (cut1 + 1) + (int)(Get_Random_Number() * (end - (cut1 + 1)));

    for (int i = 0; i < start; ++i) child[i] = parent1[i];

    for (int i = start; i <= cut1; ++i) child[i] = parent1[i];
    for (int i = cut1 + 1; i <= cut2; ++i) child[i] = parent2[i];
    for (int i = cut2 + 1; i < end; ++i) child[i] = parent1[i];

    for (int i = end + 1; i < n; ++i) child[i] = (child[i] > 0.5) ? 1.0 : 0.0; 
}

void CUtilityToolBox::TwoPointCrossover_Relocation(const vector<double> &parent1, const vector<double> &parent2, vector<double> &child, ProblemInstance *instance){

    const int n = (int)parent1.size();
    child.assign(n, 0.0);

    int start = 0, end = n-1;

    int cut1 = start + (int)(Get_Random_Number() * (end - start));
    if (cut1 > end - 2) cut1 = end - 2;

    int cut2 = (cut1 + 1) + (int)(Get_Random_Number() * (end - (cut1 + 1)));

    for (int i = 0; i < start; ++i) child[i] = parent1[i];

    for (int i = start; i <= cut1; ++i) child[i] = parent1[i];
    for (int i = cut1 + 1; i <= cut2; ++i) child[i] = parent2[i];
    for (int i = cut2 + 1; i < end; ++i) child[i] = parent1[i];

    for (int i = end + 1; i < n; ++i) child[i] = (child[i] > 0.5) ? 1.0 : 0.0; 
}