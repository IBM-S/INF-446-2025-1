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
    // 1. Verificar si se ejecuta el operador (Probabilidad global de mutación del individuo)
    if (Get_Random_Number() > mutation_rate) 
        return;

    int n = x_var.size();
    const auto &nodos = problemInstance->getNodes();
    
    // =========================================================================
    // CORRECCIÓN: La probabilidad estándar es 1/N.
    // Esto asegura que, en promedio, solo 1 bit cambie por mutación.
    // =========================================================================
    double prob_bit_flip_estandar = 10*(1.0 / (double)n);

    // 2. Realizar el Bit Flip
    for (int i = 0; i < n; ++i)
    {
        // No tocar nodos preinstalados (Flag 1)
        if (nodos[i]->getFlag() == 1) continue;

        // Evaluamos cada bit independientemente con la probabilidad 1/N
        if (Get_Random_Number() <= prob_bit_flip_estandar)
        {
            // Invertir el bit: si es 1 pasa a 0, si es 0 pasa a 1
            if (x_var[i] == 1) {
				x_var[i] = 0;
			} else {
				if (EsBuenCandidato(i, problemInstance)) {
                    x_var[i] = 1;
                }
			}
        }
    }

    // -------------------------------------------------------------------------
    // RESTRICCIÓN DE PRESUPUESTO Y REPARACIÓN
    // (El código original de reparación inteligente se mantiene porque es necesario)
    // -------------------------------------------------------------------------
    
    int max_presupuesto = problemInstance->getP(); 
    std::vector<int> aeds_activos;
    int contador_instalados = 0;

    // Contar activos
    for (int i = 0; i < n; ++i)
    {
        if (x_var[i] == 1)
        {
            contador_instalados++;
            if (nodos[i]->getFlag() != 1) { // Solo los movibles
                aeds_activos.push_back(i);
            }
        }
    }

    // Si nos pasamos del presupuesto, reparamos quitando los que menos cubren
    if (contador_instalados > max_presupuesto)
    {
        int a_eliminar = contador_instalados - max_presupuesto;
        
        // Estructura: <Cobertura, Indice>
        std::vector<std::pair<double, int>> calidad_aeds;
        double R = problemInstance->getR();
        double R2 = R * R;

        // Calcular calidad de cada AED instalado (solo si es necesario reparar)
        for (int idx_aed : aeds_activos)
        {
            double cobertura_total = 0.0;
            double ax = nodos[idx_aed]->getX();
            double ay = nodos[idx_aed]->getY();

            for (int j = 0; j < n; ++j)
            {
                if (nodos[j]->getFlag() == 0) // Nodos de demanda
                {
                    double dx = ax - nodos[j]->getX();
                    double dy = ay - nodos[j]->getY();
                    if ((dx*dx + dy*dy) <= R2)
                    {
                        cobertura_total += nodos[j]->getProbOhca();
                    }
                }
            }
            calidad_aeds.push_back({cobertura_total, idx_aed});
        }

        // Ordenar de MENOR a MAYOR cobertura (los peores primero)
        std::sort(calidad_aeds.begin(), calidad_aeds.end());

        // Eliminar los sobrantes
        for (int k = 0; k < a_eliminar && k < (int)calidad_aeds.size(); ++k)
        {
            int idx_a_borrar = calidad_aeds[k].second;
            x_var[idx_a_borrar] = 0;
        }
    }
}

double CUtilityToolBox::CalcularCoberturaYMapa(const vector<double> &x_var, const vector<Node*> &nodos, double R2, vector<int> &veces_cubierto)
{
    double cobertura_total = 0.0;
    int n = x_var.size();
    std::fill(veces_cubierto.begin(), veces_cubierto.end(), 0); // Reiniciar mapa

    // 1. Llenar el mapa de cobertura
    for (int i = 0; i < n; ++i)
    {
        // Si hay un AED (ya sea variable=1 o fijo=1)
        if (x_var[i] == 1 || nodos[i]->getFlag() == 1) 
        {
            double ax = nodos[i]->getX();
            double ay = nodos[i]->getY();

            for (int j = 0; j < n; ++j)
            {
                if (nodos[j]->getFlag() == 0) // Solo nodos de demanda
                {
                    double dx = ax - nodos[j]->getX();
                    double dy = ay - nodos[j]->getY();
                    if ((dx*dx + dy*dy) <= R2)
                    {
                        veces_cubierto[j]++;
                    }
                }
            }
        }
    }

    // 2. Calcular el valor total basado en el mapa
    for (int j = 0; j < n; ++j)
    {
        if (nodos[j]->getFlag() == 0 && veces_cubierto[j] > 0)
        {
            cobertura_total += nodos[j]->getProbOhca();
        }
    }
    return cobertura_total;
}



void CUtilityToolBox::MutacionIterativaDeleteSwap(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *problemInstance)
{
    // 1. Verificar si muta
    if (Get_Random_Number() > mutation_rate) return;

    int n = x_var.size();
    const auto &nodos = problemInstance->getNodes();
    double R = problemInstance->getR();
    double R2 = R * R;

    // Identificar activos para la fase de DELETE
    std::vector<int> aeds_instalados;
    for (int i = 0; i < n; ++i) {
        if (x_var[i] == 1 && nodos[i]->getFlag() != 1) {
            aeds_instalados.push_back(i);
        }
    }

    if (aeds_instalados.empty()) return;

    // =============================================================
    // FASE 1: DELETE (Reducir Costo)
    // =============================================================
    
    // Porcentaje agresivo si hay muchos, suave si hay pocos (Lógica adaptativa simple)
    double porcentaje_borrado = 0.05; // 5% base
    if (aeds_instalados.size() > 50) porcentaje_borrado = 0.50; // 10% si hay muchos
    
    int cantidad_borrar = std::ceil(aeds_instalados.size() * porcentaje_borrado);
    if (cantidad_borrar < 1) cantidad_borrar = 1;

    std::random_shuffle(aeds_instalados.begin(), aeds_instalados.end());
    
    // Aplicamos el borrado
    for (int k = 0; k < cantidad_borrar; ++k) {
        x_var[aeds_instalados[k]] = 0;
    }

    // =============================================================
    // FASE 2: SWAP ITERATIVO (Optimizar Cobertura)
    // =============================================================
    
    // Estructuras para evaluación rápida
    vector<int> veces_cubierto(n, 0);
    double mejor_cobertura = CalcularCoberturaYMapa(x_var, nodos, R2, veces_cubierto);
    
    // Volvemos a listar disponibles tras el borrado
    std::vector<int> actuales;
    std::vector<int> vacios;
    for (int i = 0; i < n; ++i) {
        if (nodos[i]->getFlag() == 1) continue;
        if (x_var[i] == 1) actuales.push_back(i);
        else vacios.push_back(i);
    }

    if (actuales.empty() || vacios.empty()) return;

    int max_intentos = 10;
    
    // Bucle de intentos (Hill Climbing / Steepest Descent)
    for (int iter = 0; iter < max_intentos; ++iter)
    {
        // 1. Seleccionar candidatos para el Swap
        int idx_quitar = actuales[rand() % actuales.size()];
        int idx_poner = vacios[rand() % vacios.size()];

        // 2. Evaluar cambio incrementalmente (Delta Evaluation)
        // No recalculamos todo, solo vemos qué ganamos y qué perdemos
        double delta_cobertura = 0.0;

        // A. Simular quitar 'idx_quitar'
        double ax_q = nodos[idx_quitar]->getX();
        double ay_q = nodos[idx_quitar]->getY();
        
        // Nodos que dejarían de estar cubiertos si quitamos este AED
        // (Solo perdemos cobertura si veces_cubierto == 1)
        for (int j = 0; j < n; ++j) {
            if (nodos[j]->getFlag() == 0) { // Demanda
                double dx = ax_q - nodos[j]->getX();
                double dy = ay_q - nodos[j]->getY();
                if ((dx*dx + dy*dy) <= R2) {
                    if (veces_cubierto[j] == 1) { 
                        delta_cobertura -= nodos[j]->getProbOhca(); // Perdida
                    }
                }
            }
        }

        // B. Simular poner 'idx_poner'
        double ax_p = nodos[idx_poner]->getX();
        double ay_p = nodos[idx_poner]->getY();

        // Nodos que ganarían cobertura
        // (Solo ganamos cobertura si veces_cubierto == 0, OJO: considerando que acabamos de quitar uno virtualmente)
        // Para hacerlo exacto sin modificar el vector 'veces_cubierto' aún, es complejo.
        // ESTRATEGIA SEGURA: Modificar vector temporalmente y revertir si falla.
        
        // Aplicar cambios temporales al mapa
        bool mejora = false;
        double cobertura_temp = mejor_cobertura;
        
        // -- Quitar del mapa --
        for (int j = 0; j < n; ++j) {
            if (nodos[j]->getFlag() != 0) continue;
            double dx = ax_q - nodos[j]->getX();
            double dy = ay_q - nodos[j]->getY();
            if ((dx*dx + dy*dy) <= R2) {
                veces_cubierto[j]--; // Reducimos contador
                if (veces_cubierto[j] == 0) cobertura_temp -= nodos[j]->getProbOhca();
            }
        }

        // -- Poner en el mapa --
        for (int j = 0; j < n; ++j) {
             if (nodos[j]->getFlag() != 0) continue;
            double dx = ax_p - nodos[j]->getX();
            double dy = ay_p - nodos[j]->getY();
            if ((dx*dx + dy*dy) <= R2) {
                if (veces_cubierto[j] == 0) cobertura_temp += nodos[j]->getProbOhca();
                veces_cubierto[j]++; // Aumentamos contador
            }
        }

        // 3. Verificar si mejoró
        if (cobertura_temp > mejor_cobertura) // + EPS si usas flotantes
        {
            // ACEPTAR CAMBIO
            mejor_cobertura = cobertura_temp;
            
            // Actualizar genotipo real
            x_var[idx_quitar] = 0;
            x_var[idx_poner] = 1;

            // Actualizar listas de indices para siguientes iteraciones
            // (Borrar y poner es costoso en vector, simplemente reemplazamos valores si iteramos mucho,
            // pero como son solo 10 veces, podemos dejarlo asi o actualizar listas).
            // Manera rapida: buscar y reemplazar en los vectores de indices
            std::replace(actuales.begin(), actuales.end(), idx_quitar, idx_poner);
            std::replace(vacios.begin(), vacios.end(), idx_poner, idx_quitar);
        }
        else
        {
            // RECHAZAR CAMBIO (Revertir mapa de cobertura)
            
            // -- Revertir poner --
             for (int j = 0; j < n; ++j) {
                if (nodos[j]->getFlag() != 0) continue;
                double dx = ax_p - nodos[j]->getX();
                double dy = ay_p - nodos[j]->getY();
                if ((dx*dx + dy*dy) <= R2) {
                    veces_cubierto[j]--; 
                }
            }
            // -- Revertir quitar --
            for (int j = 0; j < n; ++j) {
                if (nodos[j]->getFlag() != 0) continue;
                double dx = ax_q - nodos[j]->getX();
                double dy = ay_q - nodos[j]->getY();
                if ((dx*dx + dy*dy) <= R2) {
                    veces_cubierto[j]++;
                }
            }
        }
    }
}

bool CUtilityToolBox::EsBuenCandidato(int idx_candidato, ProblemInstance *instance)
{
    const auto &nodos = instance->getNodes();
    
    // 1. Si intento poner un AED sobre una cámara existente, es redundante.
    if (nodos[idx_candidato]->getFlag() == 1) return false;

    // 2. Obtener lista de demanda que este candidato cubriría
    const std::vector<int>& vecinos = instance->getNodosCubiertosPor(idx_candidato);
    const std::vector<bool>& base_covered = instance->getBaseCoverage();

    int ganancia_marginal = 0;

    for (int id_vecino : vecinos) 
    {
        // CONDICIÓN DE ORO:
        // El vecino debe ser demanda útil (prob > 0)
        // Y NO DEBE ESTAR CUBIERTO POR LA BASE (false en base_covered)
        
        if (nodos[id_vecino]->getProbOhca() > 0.0 && !base_covered[id_vecino]) 
        {
            ganancia_marginal++;
            
            // Si encontramos al menos 1 persona NUEVA que salvamos, vale la pena.
            if (ganancia_marginal >= 1) return true;
        }
    }

    // Si terminamos el bucle y ganancia_marginal es 0, significa que 
    // toda la gente que este candidato cubre YA ESTABA CUBIERTA por las cámaras.
    // Poner un AED aquí es tirar el dinero.
    return false;
}

void CUtilityToolBox::MutacionPorcentual(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *problemInstance)
{
	  double base_percentage = 0.5; // Base conservadora, el algoritmo la escala.
    
    // 1. Probabilidad global
    if (Get_Random_Number() > mutation_rate)
        return;

    int n = x_var.size();
    const auto &nodos = problemInstance->getNodes();
    double R = problemInstance->getR();
    double R2 = R * R;

    // 2. Clasificar índices
    std::vector<int> aeds_instalados;
    std::vector<int> espacios_vacios;

    for (int i = 0; i < n; ++i)
    {
        if (nodos[i]->getFlag() == 1) continue; // Ignorar preinstalados

        if (x_var[i] == 1) aeds_instalados.push_back(i);
        else espacios_vacios.push_back(i);
    }

    int num_instalados = aeds_instalados.size();
    if (num_instalados == 0) return;

    // =========================================================
    // LÓGICA ADAPTATIVA
    // =========================================================
    
    double referencia_alta = 50.0; 
    double factor_agresividad = 1.0 + (num_instalados / referencia_alta);
    
    // Topes de agresividad (ajustados a tu código previo)
    if (factor_agresividad > 5.0) factor_agresividad = 5.0;

    // A. Porcentaje Dinámico
    double porcentaje_final = base_percentage * factor_agresividad;
    if (porcentaje_final > 0.50) porcentaje_final = 0.50; // Ojo: 1.0 es borrar todo, 0.5 es más seguro

    int cantidad_cambios = static_cast<int>(std::ceil(num_instalados * porcentaje_final));
    if (cantidad_cambios < 1) cantidad_cambios = 1;

    // B. Probabilidad Dinámica de Borrado
    double prob_solo_borrar = 0.20 + (0.40 * (num_instalados / (referencia_alta * 2))); 
    if (prob_solo_borrar > 0.7) prob_solo_borrar = 0.7;

    // =========================================================

    // 3. Ejecución del Operador
    bool es_solo_borrar = (Get_Random_Number() <= prob_solo_borrar);

    // Mezclar instalados para borrar al azar
    std::random_shuffle(aeds_instalados.begin(), aeds_instalados.end());

    // Fase 1: Eliminar
    for (int k = 0; k < cantidad_cambios && k < aeds_instalados.size(); ++k) {
        x_var[aeds_instalados[k]] = 0;
    }

    // Fase 2: Insertar (Solo si es Swap) CON FILTRO INTELIGENTE
    if (!es_solo_borrar) 
    {
        if (espacios_vacios.empty()) return;

        // Mezclar espacios vacíos
        std::random_shuffle(espacios_vacios.begin(), espacios_vacios.end());

        int cantidad_poner = cantidad_cambios;
        
        // Ajuste: si hay muchos, ponemos un poquito menos para ayudar a bajar costos
        if (num_instalados > referencia_alta) {
             // Reducimos un 10% la reposición para generar presión de ahorro
             // cantidad_poner = (int)(cantidad_poner * 0.9);
             // if (cantidad_poner < 1) cantidad_poner = 1;
        }

        if (cantidad_poner > espacios_vacios.size()) cantidad_poner = espacios_vacios.size();

        // ---------------------------------------------------------
        // AQUI ESTA EL FILTRO (Similar a PARES_CUBRIBLES)
        // ---------------------------------------------------------
        int instalados_ahora = 0;
        int idx_vec = 0;
        int max_intentos_por_aed = 10; // Intentos para encontrar uno bueno

        while (instalados_ahora < cantidad_poner && idx_vec < espacios_vacios.size())
        {
            int candidato_final = -1;

            // Intentamos encontrar un buen candidato en los siguientes del vector
            for (int intento = 0; intento < max_intentos_por_aed; ++intento)
            {
                if (idx_vec >= espacios_vacios.size()) break;

                int candidato_temp = espacios_vacios[idx_vec];
                idx_vec++; // Avanzamos en la lista barajada

                // Verificamos si vale la pena (cubre a mas de 1 persona)
                if (EsBuenCandidato(candidato_temp, problemInstance))
                {
                    candidato_final = candidato_temp;
                    break; // Encontramos uno bueno
                }
                
                // Si no es bueno, el loop continua y probamos el siguiente vacío
                // Pero guardamos el último "malo" por si no encontramos ninguno bueno
                candidato_final = candidato_temp; 
            }

            // Instalamos el candidato elegido
            if (candidato_final != -1)
            {
                x_var[candidato_final] = 1;
                instalados_ahora++;
            }
        }
    }
}

void CUtilityToolBox::MutacionModificada_sin_reubicacion_Inteligente(vector<double> &x_var, double mutation_rate, double prob_op1_delete, ProblemInstance *problemInstance)
{
	// 1 Verificar probabilidad
	if (Get_Random_Number() > mutation_rate) return;

	const auto &nodos = problemInstance->getNodes();
	double R = problemInstance->getR();
	double R2 = R * R;
	int n = x_var.size();
	
	std::vector<int> aeds_activos;
	std::vector<int> candidatos_libres;
	std::vector<int> nodos_demanda;

	for (int i = 0; i < n; ++i)
	{
		if (nodos[i] -> getFlag() == 0) {
			nodos_demanda.push_back(i);
			if (x_var[i] == 1) {
				aeds_activos.push_back(i);
			} else {
				candidatos_libres.push_back(i);
			}
		}
		else if (nodos[i] -> getFlag() == 1) {
			// AED preinstalado, no se toca
		}
	}
	double rnd_op = Get_Random_Number();

	if (rnd_op < 0.5) {
		// Operador 1: Eliminar un AED activo
		std::vector<bool> is_covered(n, false);

		for (int i = 0; i < n;++i) {
			if (x_var[i] == 1 || nodos[i]-> getFlag() == 1) {
				double ax = nodos[i]->getX();
				double ay = nodos[i]->getY();

				for (int dem_idx : nodos_demanda) {
					if (is_covered[dem_idx]) continue;

					double dx = nodos[dem_idx]->getX();
					double dy = nodos[dem_idx]->getY();
					if ((dx*dx + dy*dy) <= R2) {
						is_covered[dem_idx] = true;
					}
				}
			}
		}

		// B. Buscar el candidato libre que cubra más demanda NO CUBIERTA
        int best_candidate = -1;
        double max_gain = -1.0;

        // Para no hacerlo eterno, probamos un subconjunto aleatorio si hay muchos candidatos
        int attempts = std::min((int)candidatos_libres.size(), 50); 
        // Si quieres precisión máxima, quita el límite y recorre todos, pero será lento.
        
        for (int k = 0; k < attempts; ++k) {
            // Selección aleatoria para diversidad o secuencial si son pocos
            int idx_cand = candidatos_libres[rand() % candidatos_libres.size()]; 

            double current_gain = 0.0;
            double cx = nodos[idx_cand]->getX();
            double cy = nodos[idx_cand]->getY();

            for (int dem_idx : nodos_demanda) {
                if (is_covered[dem_idx]) continue; // Solo nos importa la demanda virgen

                double dx = cx - nodos[dem_idx]->getX();
                double dy = cy - nodos[dem_idx]->getY();
                
                if ((dx*dx + dy*dy) <= R2) {
                    current_gain += nodos[dem_idx]->getProbOhca(); // Sumar probabilidad/importancia
                }
            }

            if (current_gain > max_gain) {
                max_gain = current_gain;
                best_candidate = idx_cand;
            }
        }

        // C. Aplicar cambio
        if (best_candidate != -1 && max_gain > 0) {
            x_var[best_candidate] = 1;
        } else {
            // Si no encontramos nada útil, agregar uno al azar para no estancarse
            if (!candidatos_libres.empty())
                x_var[candidatos_libres[rand() % candidatos_libres.size()]] = 1;
        }
    }

	else 
    {
        if (aeds_activos.empty()) return;

        // A. Contar cuántos AEDs cubren a cada nodo de demanda
        std::vector<int> cover_count(n, 0);

        for (int i = 0; i < n; ++i) {
            if (x_var[i] == 1 || nodos[i]->getFlag() == 1) { // AED activo o fijo
                double ax = nodos[i]->getX();
                double ay = nodos[i]->getY();
                for (int dem_idx : nodos_demanda) {
                    double dx = ax - nodos[dem_idx]->getX();
                    double dy = ay - nodos[dem_idx]->getY();
                    if ((dx*dx + dy*dy) <= R2) {
                        cover_count[dem_idx]++;
                    }
                }
            }
        }

        // B. Buscar el AED activo cuya eliminación cause la MENOR pérdida
        int best_victim = -1;
        double min_loss = 1.0e30; // Infinito

        // Revisamos un subconjunto para velocidad
        int attempts = std::min((int)aeds_activos.size(), 50);

        for (int k = 0; k < attempts; ++k) {
            int idx_aed = aeds_activos[rand() % aeds_activos.size()];
            
            double current_loss = 0.0;
            double ax = nodos[idx_aed]->getX();
            double ay = nodos[idx_aed]->getY();

            for (int dem_idx : nodos_demanda) {
                // Solo perdemos cobertura si este AED cubre el nodo Y es el ÚNICO que lo hace (count == 1)
                if (cover_count[dem_idx] == 1) {
                    double dx = ax - nodos[dem_idx]->getX();
                    double dy = ay - nodos[dem_idx]->getY();
                    if ((dx*dx + dy*dy) <= R2) {
                        current_loss += nodos[dem_idx]->getProbOhca();
                    }
                }
            }

            if (current_loss < min_loss) {
                min_loss = current_loss;
                best_victim = idx_aed;
                if (min_loss == 0.0) break; // Si encontramos uno redundante, borrarlo de inmediato
            }
        }

        // C. Aplicar cambio
        if (best_victim != -1) {
            x_var[best_victim] = 0;
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