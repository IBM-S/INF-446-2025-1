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

void CUtilityToolBox::MutacionModificada(vector<double> &x_var, double rate)
{
	int n = x_var.size();

	if (Get_Random_Number() <= rate)
	{

		bool eliminarEstacion = (rand() % 2 == 1);

		if (eliminarEstacion)
		{
			int inicio1 = rand() % n;
			for (int i = 0; i < n; ++i)
			{
				int pos = (inicio1 + i) % n;
				if (x_var[pos] == 1)
				{
					x_var[pos] = 0;
					break;
				}
			}
		}
		else
		{

			// === Paso 1: buscar un 1 para cambiarlo a 0 ===
			int inicio1 = rand() % n;
			for (int i = 0; i < n; ++i)
			{
				int pos = (inicio1 + i) % n;
				if (x_var[pos] == 1)
				{
					x_var[pos] = 0;
					break;
				}
			}

			// === Paso 2: buscar un 0 para cambiarlo a 1 ===
			int inicio0 = rand() % n;
			for (int i = 0; i < n; ++i)
			{
				int pos = (inicio0 + i) % n;
				if (x_var[pos] == 0)
				{
					x_var[pos] = 1;
					break;
				}
			}
		}
	}
}

void CUtilityToolBox::MutacionBitFlip(vector<double> &x_var, double mutation_rate, double prob_bit_flip, ProblemInstance *problemInstance)
{
    // A. Probabilidad global de que el individuo mute
    if (Get_Random_Number() > mutation_rate) 
        return;

    int n = x_var.size();
    const auto &nodos = problemInstance->getNodes();
    
    // Probabilidad por gen: 1/N (Estándar).
    // Si quieres ser más agresivo, usa 2.0/N o 5.0/N.
    double prob_por_gen = 1.0 / (double)n;

    // B. Bucle de Mutación
    for (int i = 0; i < n; ++i)
    {
        // Nunca tocar nodos preinstalados (Cámaras)
        if (nodos[i]->getFlag() == 1) continue;

        if (Get_Random_Number() <= prob_por_gen)
        {
            if (x_var[i] == 1) {
                // Si está puesto, lo quitamos (Borrar siempre es válido).
                x_var[i] = 0;
            } 
            else {
                // Si está vacío, intentamos ponerlo.
                // AQUÍ USAMOS LA INTELIGENCIA: Solo poner si sirve de algo.
                if (EsBuenCandidato(i, problemInstance)) {
                    x_var[i] = 1;
                }
            }
        }
    }

    // C. Reparación de Presupuesto (Si nos pasamos)
    int max_presupuesto = problemInstance->getP(); 
    std::vector<int> aeds_activos;
    int contador_instalados = 0;

    for (int i = 0; i < n; ++i) {
        if (x_var[i] == 1) {
            contador_instalados++;
            // Solo podemos borrar los que no son fijos
            if (nodos[i]->getFlag() == 0) aeds_activos.push_back(i);
        }
    }

    if (contador_instalados > max_presupuesto)
    {
        int a_eliminar = contador_instalados - max_presupuesto;
        
        // Estrategia: Eliminar los que menos aportan (Calidad)
        std::vector<std::pair<double, int>> calidad_aeds;
        
        for (int idx_aed : aeds_activos) {
            // Calcular aporte marginal real
            double aporte = 0.0;
            const std::vector<int>& vecinos = problemInstance->getNodosCubiertosPor(idx_aed);
            
            for (int vec : vecinos) {
                // Sumar solo si no está cubierto por base (para ser justos en la eliminación)
                if (nodos[vec]->getFlag() == 0 && !problemInstance->isPreCubierto(vec)) {
                    aporte += nodos[vec]->getProbOhca();
                }
            }
            calidad_aeds.push_back({aporte, idx_aed});
        }

        // Ordenar menor a mayor (los peores al principio)
        std::sort(calidad_aeds.begin(), calidad_aeds.end());

        for (int k = 0; k < a_eliminar && k < (int)calidad_aeds.size(); ++k) {
            x_var[calidad_aeds[k].second] = 0;
        }
    }
}


// =========================================================================
// MUTACIÓN BIT FLIP V2 (Probabilidad Manual)
// =========================================================================
// A diferencia de la estándar (1/N), aquí tú defines la intensidad.
// prob_bit_flip: Probabilidad de que cada bit individual cambie.
// Ejemplo: Si prob_bit_flip = 0.01 y N=1000, cambiarán aprox 10 bits.
void CUtilityToolBox::MutacionBitFlip_v2(vector<double> &x_var, double mutation_rate, double prob_bit_flip, ProblemInstance *problemInstance)
{
    // 1. Probabilidad global de ejecutar el operador
    if (Get_Random_Number() > mutation_rate) 
        return;

    int n = x_var.size();
    const auto &nodos = problemInstance->getNodes();

    // 2. Recorrer cada gen (bit)
    for (int i = 0; i < n; ++i)
    {
        // Protección: Nunca tocar cámaras/preinstalados
        if (nodos[i]->getFlag() == 1) continue;

        // Evaluación de probabilidad independiente para cada bit
        if (Get_Random_Number() <= prob_bit_flip)
        {
            if (x_var[i] == 1) 
            {
                // Si estaba encendido -> Apagar (Delete)
                // Esto siempre es seguro y ayuda a bajar costos
                x_var[i] = 0;
            }
            else 
            {
                // Si estaba apagado -> Encender (Add)
                // AQUÍ USAMOS TU FILTRO INTELIGENTE
                // Solo permitimos el flip a 1 si el candidato aporta valor real.
                if (EsBuenCandidato(i, problemInstance)) 
                {
                    x_var[i] = 1;
                }
            }
        }
    }

    // 3. Reparación de Presupuesto (Vital en este operador)
    // Como la probabilidad es manual, es fácil pasarse del presupuesto.
    int max_presupuesto = problemInstance->getP(); 
    std::vector<int> aeds_activos;
    int contador_instalados = 0;

    for (int i = 0; i < n; ++i) {
        if (x_var[i] == 1) {
            contador_instalados++;
            if (nodos[i]->getFlag() == 0) aeds_activos.push_back(i);
        }
    }

    if (contador_instalados > max_presupuesto)
    {
        int a_eliminar = contador_instalados - max_presupuesto;
        
        // Calculamos la calidad marginal para borrar los peores
        std::vector<std::pair<double, int>> calidad_aeds;
        
        for (int idx_aed : aeds_activos) {
            double aporte = 0.0;
            const std::vector<int>& vecinos = problemInstance->getNodosCubiertosPor(idx_aed);
            
            for (int vec : vecinos) {
                // Solo sumamos si es demanda y NO está cubierta por la base
                if (nodos[vec]->getFlag() == 0 && !problemInstance->isPreCubierto(vec)) {
                    aporte += nodos[vec]->getProbOhca();
                }
            }
            calidad_aeds.push_back({aporte, idx_aed});
        }

        // Ordenar de menor a mayor (los de menor aporte al principio)
        std::sort(calidad_aeds.begin(), calidad_aeds.end());

        // Eliminar los sobrantes
        for (int k = 0; k < a_eliminar && k < (int)calidad_aeds.size(); ++k) {
            x_var[calidad_aeds[k].second] = 0;
        }
    }
}



// =========================================================================
// MUTACIÓN ADAPTATIVA POR FASES (Delete -> Swap)
// =========================================================================
void CUtilityToolBox::MutacionAdaptativaFases(vector<double> &x_var, double mutation_rate, double progress, ProblemInstance *problemInstance)
{
    // 1. Probabilidad global
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = problemInstance->getNodes();

    // 2. Identificar AEDs instalados (móviles)
    std::vector<int> instalados;
    std::vector<int> vacios;

    for (int i = 0; i < n; ++i) {
        if (nodos[i]->getFlag() == 1) continue; // Ignorar cámaras

        if (x_var[i] == 1) instalados.push_back(i);
        else vacios.push_back(i);
    }

    if (instalados.empty()) return;

    // 3. CALCULAR PROBABILIDAD DINÁMICA
    // Queremos que prob_solo_borrar sea ALTA al principio y BAJA al final.
    // progress va de 0.0 a 1.0
    // Fórmula: 1.0 - progress. 
    // Inicio (0.0) -> 100% chance de borrar.
    // Final (1.0) -> 0% chance de borrar (100% swap).
    
    // Le ponemos un pequeño margen (0.05) para que al final aun exista una 
    // pequeñisima posibilidad de borrar para salir de saturación.
    double prob_solo_borrar = 1.0 - progress; 
    if (prob_solo_borrar < 0.05) prob_solo_borrar = 0.05;

    bool modo_delete = (Get_Random_Number() <= prob_solo_borrar);

    // 4. Determinar Cantidad a Modificar
    // Cambiamos un % pequeño (ej. 1% o mínimo 1) para mantener estabilidad
    int cantidad = std::max(1, (int)(instalados.size() * 0.01)); 

    // Mezclar para aleatoriedad
    std::random_shuffle(instalados.begin(), instalados.end());

    // --- ACCIÓN: BORRAR (Común para Delete y la primera mitad de Swap) ---
    // Borramos los 'cantidad' primeros de la lista barajada
    // (O podrías usar una heurística para borrar los peores, pero aleatorio da velocidad)
    for (int k = 0; k < cantidad && k < (int)instalados.size(); ++k) {
        x_var[instalados[k]] = 0;
    }

    // --- ACCIÓN: INSERTAR (Solo si NO es modo delete -> es decir, es Swap) ---
    if (!modo_delete)
    {
        if (vacios.empty()) return;
        std::random_shuffle(vacios.begin(), vacios.end());

        int insertados = 0;
        int intentos = 0;
        int max_intentos = vacios.size(); 
        if (max_intentos > 500) max_intentos = 500; // Tope para velocidad

        int idx_vac = 0;
        while (insertados < cantidad && idx_vac < (int)vacios.size() && intentos < max_intentos)
        {
            int cand = vacios[idx_vac];
            idx_vac++;
            intentos++;

            // Usamos el filtro INTELIGENTE
            if (EsBuenCandidato(cand, problemInstance)) 
            {
                x_var[cand] = 1;
                insertados++;
            }
        }
    }

    // 5. REPARACIÓN DE PRESUPUESTO (Siempre necesaria por seguridad)
    // El código de reparación estándar que ya tienes...
    int max_P = problemInstance->getP();
    int current_P = 0;
    std::vector<int> final_instalados;
    
    for(int i=0; i<n; ++i) {
        if(x_var[i] == 1) {
            current_P++;
            if(nodos[i]->getFlag() == 0) final_instalados.push_back(i);
        }
    }

    if (current_P > max_P) {
        int eliminar = current_P - max_P;
        // Ordenamiento rápido por calidad para eliminar lo peor
        std::vector<std::pair<double, int>> calidad;
        for(int idx : final_instalados) {
            double aporte = 0;
            const auto& vec = problemInstance->getNodosCubiertosPor(idx);
            for(int v : vec) if(!problemInstance->isPreCubierto(v)) aporte += nodos[v]->getProbOhca();
            calidad.push_back({aporte, idx});
        }
        std::sort(calidad.begin(), calidad.end());
        for(int k=0; k<eliminar && k<(int)calidad.size(); ++k) {
            x_var[calidad[k].second] = 0;
        }
    }
}

void CUtilityToolBox::MutacionRefuerzoZonasDebiles(
    std::vector<double> &x_var,
    double mutation_rate,
	double prob_bit_flip,
    ProblemInstance *instance
) {
    // 1. Probabilidad global
    if (Get_Random_Number() > mutation_rate) return;
    int n = x_var.size();
    const auto &nodos = instance->getNodes();
    // 2. Construir conteo de cobertura actual por nodo de demanda
    int N = nodos.size();
    std::vector<int> cobertura(N, 0);
    // Cobertura por AEDs activos
    for (int i = 0; i < n; ++i) {
        if (x_var[i] == 1) {
            const std::vector<int> &vecinos = instance->getNodosCubiertosPor(i);
            for (int v : vecinos) {
                cobertura[v] += 1;
            }
        }
    }
    // 3. Buscar demandas débiles (no pre-cubiertas) con alta probabilidad
    int mejor_demanda = -1;
    double peor_score = -1.0;  // maximizamos prob / (1 + cobertura)
    for (int d = 0; d < N; ++d) {
        // Solo demandas
        if (nodos[d]->getFlag() != 0) continue;
        if (instance->isPreCubierto(d)) continue;  // ya la cubre la base
        double prob = nodos[d]->getProbOhca();
        if (prob <= 0.0) continue;
        int cov = cobertura[d];
        // Score: alta prob y poca cobertura -> valor muy grande
        double score = prob / (1.0 + (double)cov);
        if (score > peor_score) {
            peor_score = score;
            mejor_demanda = d;
        }
    }
    // Si no encontramos ninguna demanda interesante, no mutamos
    if (mejor_demanda == -1) return;
    // 4. Buscar mejor sitio para reforzar esa demanda
    int mejor_sitio = -1;
    double mejor_ganancia = -1.0;
    for (int j = 0; j < n; ++j) {
        // No usar cámaras ni sitios ya ocupados
        if (nodos[j]->getFlag() == 1) continue;
        if (x_var[j] == 1) continue;
        const std::vector<int> &vecinos = instance->getNodosCubiertosPor(j);
        // Este sitio debe cubrir a la demanda elegida
        bool cubre_demanda = false;
        for (int v : vecinos) {
            if (v == mejor_demanda) {
                cubre_demanda = true;
                break;
            }
        }
        if (!cubre_demanda) continue;
        // Estimamos ganancia total de este candidato (similar a lo que ya haces)
        double ganancia = 0.0;
        for (int v : vecinos) {
            if (nodos[v]->getFlag() == 0 && !instance->isPreCubierto(v)) {
                // Si ya tiene mucha cobertura de AEDs y base, podemos penalizar
                if (cobertura[v] == 0) {
                    ganancia += nodos[v]->getProbOhca();
                } else if (cobertura[v] == 1) {
                    ganancia += 0.5 * nodos[v]->getProbOhca();
                }
            }
        }
        if (ganancia > mejor_ganancia) {
            mejor_ganancia = ganancia;
            mejor_sitio = j;
        }
    }
    // Sin candidato útil → abortar
    if (mejor_sitio == -1 || mejor_ganancia <= 0.0) return;
    // 5. Verificar presupuesto actual
    int max_P = instance->getP();
    int current_P = 0;
    std::vector<int> instalados_moviles;
    for (int i = 0; i < n; ++i) {
        if (x_var[i] == 1) {
            current_P++;
            if (nodos[i]->getFlag() == 0) {
                instalados_moviles.push_back(i);
            }
        }
    }
    // 6. Si rompería el presupuesto, buscamos un AED malo para apagar
    int sitio_a_apagar = -1;
    if (current_P >= max_P) {
        double min_aporte = 1.0e30;
        // Muestra pequeña (para rapidez)
        std::random_shuffle(instalados_moviles.begin(), instalados_moviles.end());
        int sample_size = std::min((int)instalados_moviles.size(), 20);
        for (int k = 0; k < sample_size; ++k) {
            int idx = instalados_moviles[k];
            const std::vector<int> &vecinos = instance->getNodosCubiertosPor(idx);
            double aporte = 0.0;
            for (int v : vecinos) {
                if (nodos[v]->getFlag() == 0 && !instance->isPreCubierto(v)) {
                    aporte += nodos[v]->getProbOhca();
                }
            }
            if (aporte < min_aporte) {
                min_aporte = aporte;
                sitio_a_apagar = idx;
            }
        }
    }
    // 7. Aplicar mutación (swap o solo add si hay espacio)
    if (sitio_a_apagar != -1) {
        x_var[sitio_a_apagar] = 0;
    }
    x_var[mejor_sitio] = 1;
}

bool CUtilityToolBox::EsBuenCandidato(int idx_candidato, ProblemInstance *instance)
{
    const auto &nodos = instance->getNodes();
    
    // Regla 0: Si es una cámara existente (Flag 1), no podemos poner otro AED encima.
    if (nodos[idx_candidato]->getFlag() == 1) return false;

    // Regla 1: Usamos el mapa precalculado para velocidad.
    const std::vector<int>& vecinos = instance->getNodosCubiertosPor(idx_candidato);
    
    // Regla 2: Verificamos contra la cobertura base (cámaras).
    // Nota: isPreCubierto devuelve true si el nodo ya está cubierto por una cámara.
    // Nosotros queremos encontrar gente donde isPreCubierto == false.
    
    int ganancia_marginal = 0;
    
    for (int id_vecino : vecinos) 
    {
        // Solo cuenta si es Demanda (Flag 0) y NO está cubierto por base.
        if (nodos[id_vecino]->getFlag() == 0 && !instance->isPreCubierto(id_vecino)) 
        {
            // Opcional: Verificar que tenga probabilidad > 0
            if (nodos[id_vecino]->getProbOhca() > 0.0) {
                ganancia_marginal++;
                // Optimización: Con encontrar 1, ya sabemos que no es redundante.
                if (ganancia_marginal >= 1) return true;
            }
        }
    }
    
    // Si llegamos aquí, el candidato es inútil (solo cubre cámaras o gente ya salvada).
    return false;
}

void CUtilityToolBox::MutacionPorcentual(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *problemInstance)
{
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = problemInstance->getNodes();

    // 1. Clasificar
    std::vector<int> aeds_instalados;
    std::vector<int> espacios_vacios;

    for (int i = 0; i < n; ++i) {
        if (nodos[i]->getFlag() == 1) continue; // Ignorar cámaras

        if (x_var[i] == 1) aeds_instalados.push_back(i);
        else espacios_vacios.push_back(i);
    }

    int num_instalados = aeds_instalados.size();
    if (num_instalados == 0) return;

    // 2. Lógica Adaptativa (Ajustar intensidad según tamaño)
    double base_percentage = 0.05; // 5% por defecto
    double referencia_alta = 50.0; 
    
    // Si hay muchos equipos, somos más agresivos para limpiar
    double factor = 1.0 + (num_instalados / referencia_alta);
    if (factor > 4.0) factor = 4.0; 

    double porcentaje_final = base_percentage * factor;
    if (porcentaje_final > 0.4) porcentaje_final = 0.4; // Tope de seguridad

    int cantidad_cambios = static_cast<int>(std::ceil(num_instalados * porcentaje_final));
    if (cantidad_cambios < 1) cantidad_cambios = 1;

    // Aumentar probabilidad de borrado si estamos muy llenos
    double prob_borrar_dinamica = prob_op1_delete;
    if (num_instalados > referencia_alta * 2) prob_borrar_dinamica += 0.2;
    if (prob_borrar_dinamica > 0.8) prob_borrar_dinamica = 0.8;

    bool es_solo_borrar = (Get_Random_Number() <= prob_borrar_dinamica);

    // 3. Ejecutar Borrado
    std::random_shuffle(aeds_instalados.begin(), aeds_instalados.end());
    for (int k = 0; k < cantidad_cambios && k < (int)aeds_instalados.size(); ++k) {
        x_var[aeds_instalados[k]] = 0;
    }

    // 4. Ejecutar Inserción (Solo si es Swap)
    if (!es_solo_borrar) 
    {
        if (espacios_vacios.empty()) return;
        std::random_shuffle(espacios_vacios.begin(), espacios_vacios.end());

        int cantidad_poner = cantidad_cambios;
        
        // Bucle de búsqueda inteligente
        int instalados_ahora = 0;
        int idx_vec = 0;
        int max_intentos_totales = espacios_vacios.size(); 
        if (max_intentos_totales > 1000) max_intentos_totales = 1000; // Límite de seguridad

        while (instalados_ahora < cantidad_poner && idx_vec < (int)espacios_vacios.size())
        {
            int candidato = espacios_vacios[idx_vec];
            idx_vec++;

            // FILTRO INTELIGENTE:
            if (EsBuenCandidato(candidato, problemInstance)) 
            {
                x_var[candidato] = 1;
                instalados_ahora++;
            }
            // Si el candidato era malo (cubría cámaras), pasamos al siguiente en el vector barajado.
            
            if (idx_vec >= max_intentos_totales) break; // Evitar bucles infinitos
        }
    }
}


void CUtilityToolBox::MutacionIntercambioHeuristico(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *instance)
{
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = instance->getNodes();

    // 1. Identificar AEDs instalados (que no sean fijos)
    std::vector<int> instalados_moviles;
    std::vector<int> espacios_vacios;

    for(int i=0; i<n; ++i) {
        if (nodos[i]->getFlag() == 1) continue; // Ignorar cámaras
        
        if (x_var[i] == 1) instalados_moviles.push_back(i);
        else espacios_vacios.push_back(i);
    }

    if (instalados_moviles.empty() || espacios_vacios.empty()) return;

    // 2. ENCONTRAR EL "PEOR" INSTALADO (Para eliminarlo)
    // El "peor" es el que tiene menos ganancia marginal (aporta poco o nada nuevo)
    int peor_idx = -1;
    double min_aporte = 1.0e30;

    // Para no evaluar todos (lento), tomamos una muestra aleatoria (Torneo)
    int sample_size = std::min((int)instalados_moviles.size(), 10); // Miramos 10 al azar
    std::random_shuffle(instalados_moviles.begin(), instalados_moviles.end());

    for(int k=0; k<sample_size; ++k) 
    {
        int idx = instalados_moviles[k];
        const std::vector<int>& vecinos = instance->getNodosCubiertosPor(idx);
        
        double aporte_marginal = 0.0;
        for(int v : vecinos) {
            // Un nodo aporta valor si es demanda y NO está cubierto por las cámaras
            // NOTA: Para ser perfecto, deberíamos ver si no está cubierto por OTROS aeds, 
            // pero eso es costoso. Usar la base de cámaras es una buena heurística rápida.
            if(nodos[v]->getFlag() == 0 && !instance->isPreCubierto(v)) {
                aporte_marginal += nodos[v]->getProbOhca();
            }
        }

        // Buscamos el que tenga MENOR aporte para eliminarlo
        if(aporte_marginal < min_aporte) {
            min_aporte = aporte_marginal;
            peor_idx = idx;
            // Si encontramos uno que aporta 0 (totalmente inútil), lo borramos de inmediato.
            if (min_aporte <= 0.0001) break; 
        }
    }

    // 3. ENCONTRAR EL "MEJOR" CANDIDATO (Para agregarlo)
    int mejor_candidato = -1;
    // Usamos la función que ya hicimos para filtrar rápidos
    // Intentamos 10 veces encontrar algo bueno
    int intentos = 0;
    std::random_shuffle(espacios_vacios.begin(), espacios_vacios.end());

    while(intentos < 20 && intentos < espacios_vacios.size()) 
    {
        int cand = espacios_vacios[intentos];
        // Reutilizamos tu filtro inteligente
        if (EsBuenCandidato(cand, instance)) {
            mejor_candidato = cand;
            break; // Encontramos uno que sirve
        }
        intentos++;
    }

    // 4. APLICAR EL SWAP
    if (peor_idx != -1 && mejor_candidato != -1) {
        x_var[peor_idx] = 0;       // Quitamos el malo
        x_var[mejor_candidato] = 1; // Ponemos el bueno
    }
    // Si no encontramos mejor candidato, podríamos solo borrar el malo para ahorrar costo,
    // o hacer un movimiento aleatorio para mantener diversidad.
    else if (peor_idx != -1) {
        // Opción: Movimiento aleatorio si no hallamos uno "bueno" inteligente
        int random_pos = espacios_vacios[rand() % espacios_vacios.size()];
        x_var[peor_idx] = 0;
        x_var[random_pos] = 1; 
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
	bool esSwap = false ;

	if (rnd <= prob_op1_delete) {
        //Rango [0, prob_op1] -> Operador 1 (Solo Delete)
        esSwap = false; 
    } else {
        // Rango (prob_op1, 1.0] -> Operador 2 (Swap)
        esSwap = true;
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
	if (max_total > min_total)
	{
		max_instalaciones = min_total + rand() % (max_total - min_total + 1);
	}
	else
	{
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