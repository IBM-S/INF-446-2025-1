// Individual.cpp: implementation of the CIndividualBase class.
//
//////////////////////////////////////////////////////////////////////
#include <iostream>
#include <random>
#include "IndividualBase.h"

#include <algorithm>
#include <vector>
#include <utility> // para std::pair

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

CIndividualBase::CIndividualBase()
{
	x_var = vector<double>(NumberOfVariables, 0);
	f_obj = vector<double>(NumberOfObjectives, 0);
	f_normal = vector<double>(NumberOfObjectives, 0);
}

CIndividualBase::~CIndividualBase()
{
}

void CIndividualBase::Randomize()
{
	int lowBound = 0, uppBound = 1;

	unsigned int n;

	for (n = 0; n < NumberOfVariables; n++)
	{
		x_var[n] = lowBound + UtilityToolBox.Get_Random_Number() * (uppBound - lowBound);
	}
}

// Con esta funcion vamos a crear funciones factibles.
// A partir de la representacion binaria. Con k equipos, con
// el presupuesto.

void CIndividualBase::GenerateSimpleFeasibleSolution(int num_AEDs)
{
	//std::cout << "\n DEBUG START " << std::endl;
	//std::cout << "Target num_AEDs a instalar: " << num_AEDs << std::endl;
	//std::cout << "Total locations disponibles: " << std::endl;
	//std::cout << "x_var.size() = " << x_var.size() << std::endl;

	// Inicializa todo en 0
	std::fill(x_var.begin(), x_var.end(), 0.0);
	int largo_vector = x_var.size();

	const auto &nodos = problemInstance->getNodes();

	std::vector<int> candidate_ids;
	candidate_ids.reserve(largo_vector);

	// 1 Recorrer nodos: Marcar los fijos y guardar los que no tienen AED preinstalado
	for (int i = 0; i < largo_vector; ++i)
	{
		if (nodos[i]->getFlag() == 1)
		{ // o el valor que indica AED preinstalado
			x_var[i] = 1.0;
		} else {
			candidate_ids.push_back(i);
		}
	}

	if (num_AEDs > candidate_ids.size()) {
		num_AEDs = candidate_ids.size();
	}
		
	// 2 Mezclar los IDs candidatos
	std::random_shuffle(candidate_ids.begin(), candidate_ids.end()); // usa srand() antes si quieres control

	// 3 Instalar AEDs restantes (sin sobrescribir los ya fijos)
	for (int i = 0; i < num_AEDs; ++i)
	{
		int pos = candidate_ids[i];
		x_var[pos] = 1.0; // Instala un AED
		//printf("  Instalado AED en posición %d (Total instalados: %d)\n", pos, instalados);
	}


	// 1. Crear lista de IDs
	/*std::vector<int> ids(largo_vector);
	for (int i = 0; i < largo_vector; ++i)
	{
		ids[i] = i;
	}*/
	// print variable ids
	/* std::cout << "IDs disponibles: ";
	for (int id : ids) {
		std::cout << id << " ";
	}
	std::cout << std::endl; */

	// 2. Marcar posiciones obligatorias (AEDs preinstalados desde la instancia)
	/* int pre_instalados = 0;

	for (int i = 0; i < largo_vector; ++i)
	{
		if (nodos[i]->getFlag() == 1)
		{ // o el valor que indica AED preinstalado
			x_var[i] = 1.0;
			pre_instalados++;
		}
	} */
	//std::cout << "AEDs preinstalados marcados: " << pre_instalados << std::endl;

	// 3. Revolver los IDs
	// std::random_shuffle(ids.begin(), ids.end()); // usa srand() antes si quieres control

	/* std::cout << "IDs mezclados: ";
	for (int id : ids) {
		std::cout << id << " ";
	}
	std::cout << std::endl; */
	/*
	int instalados = 0;
	if (!(instalados < num_AEDs))
	{
		std::cout << "DEBUG END \n" << std::endl;
		return; // ya se cumplieron los AEDs necesarios
	}

	// 4.  Instalar AEDs restantes (sin sobrescribir los ya fijos)
	for (int i = 0; instalados < num_AEDs && i < largo_vector; ++i)
	{
		int pos = ids[i];
		if (x_var[pos] < 0.5) // Busca un lugar libre
		{
			x_var[pos] = 1.0; // Instala un AED
			instalados++;
			//printf("  Instalado AED en posición %d (Total instalados: %d)\n", pos, instalados);
		}
		//printf("x_var[%d] = %f\n", pos, x_var[pos]);
		//printf("i: %d, instalados: %d, num_AEDs: %d\n", i, instalados, num_AEDs);
	}
	// imprimir x_var
	/* std::cout << "\n";
	std::cout << "Solución generada (x_var): ";
	for (double val : x_var)
	{
		std::cout << val << " ";
	}
	std::cout << std::endl;

	std::cout << "DEBUG END \n" << std::endl; */
}

void CIndividualBase::InstalarEnHuecosLibres(int cantidad_a_instalar)
{

	////////////////////////////
    if (cantidad_a_instalar <= 0) return; 

    std::vector<int> vacios;
    vacios.reserve(x_var.size());
    
    // Un hueco es libre si x_var es 0 (independiente del Flag original)
    for(size_t i=0; i<x_var.size(); ++i) {
        if(x_var[i] < 0.5) vacios.push_back(i);
    }

    std::random_shuffle(vacios.begin(), vacios.end());
    
    int real_count = std::min(cantidad_a_instalar, (int)vacios.size());
    for(int i=0; i<real_count; ++i) x_var[vacios[i]] = 1.0;
}

void CIndividualBase::GenerateSimpleFeasible_Reloc_OnlyMove(double presupuesto_disponible)
{
	std::fill(x_var.begin(), x_var.end(), 0.0);
	const auto &nodos = problemInstance->getNodes();
	int largo_vector = x_var.size();
	std::vector<int> pre_instalados;
	pre_instalados.reserve(largo_vector);

	// 1 Recorrer nodos: Marcar los fijos y guardar los que no tienen AED preinstalado
	for (int i = 0; i < largo_vector; ++i)
	{
		if (nodos[i]->getFlag() == 1)
		{ // o el valor que indica AED preinstalado
			pre_instalados.push_back(i);
		}
	}

	double c2 = problemInstance->getC2();
	int total_pre = pre_instalados.size();

	int max_moves = (int)(presupuesto_disponible / c2);
	int moves_count = std::min(max_moves, total_pre);
		
	std::vector<int> actual_pre = pre_instalados;
	std::random_shuffle(actual_pre.begin(), actual_pre.end());

	int keep = total_pre - moves_count;
	for (int i =0; i < keep; ++i) x_var[actual_pre[i]] = 1.0;

	InstalarEnHuecosLibres(moves_count);
}

void CIndividualBase::GenerateSimpleFeasible_Reloc_OnlyBuy(double presupuesto_disponible)
{
	std::fill(x_var.begin(), x_var.end(), 0.0);
	const auto &nodos = problemInstance->getNodes();
	int largo_vector = x_var.size();
	int total_pre = 0;

	// 1 Recorrer nodos: Marcar los fijos y guardar los que no tienen AED preinstalado
	for (int i = 0; i < largo_vector; ++i)
	{
		if (nodos[i]->getFlag() == 1)
		{ // o el valor que indica AED preinstalado
			x_var[i] = 1.0;
			total_pre++;
		}
	}

	double c1 = problemInstance->getC1();

	int max_new = (int)(presupuesto_disponible / c1);

	int huecos_disponibles = largo_vector - total_pre;
	int install_count = std::min(max_new, huecos_disponibles);

	int new_count = install_count;

	InstalarEnHuecosLibres(new_count);
}

void CIndividualBase::GenerateSimpleFeasible_Reloc_Choose_Move_or_Buy(double presupuesto_disponible, double prob_choose_move)
{
	if (UtilityToolBox.Get_Random_Number() < prob_choose_move) {
        GenerateSimpleFeasible_Reloc_OnlyMove((double)presupuesto_disponible);
    } else {
        GenerateSimpleFeasible_Reloc_OnlyBuy((double)presupuesto_disponible);
    }
}

void CIndividualBase::GenerateSimpleFeasible_Reloc_HybridSplit(double presupuesto_disponible, double split_pct)
{
    std::fill(x_var.begin(), x_var.end(), 0.0);
    const auto &nodos = problemInstance->getNodes();
    int n = x_var.size();
    double c2 = problemInstance->getC2();
    double P_total = (double)presupuesto_disponible;

    std::vector<int> pre;
    for(int i=0; i<n; ++i) if(nodos[i]->getFlag() == 1) pre.push_back(i);
    int total_pre = pre.size();

    // 1. FASE MOVER
    double budget_move = P_total * split_pct;
    int max_moves = (int)(budget_move / c2);
    int moves_count = std::min(max_moves, total_pre);

    // Ejecutar movimiento
    std::vector<int> current_pre = pre;
    std::random_shuffle(current_pre.begin(), current_pre.end());

    int keep = total_pre - moves_count;
    for(int i=0; i<keep; ++i) x_var[current_pre[i]] = 1.0;

    double gastado_moves = moves_count * c2;

    // 2. FASE COMPRAR (Con el vuelto real)
    double budget_buy = P_total - gastado_moves; // Lo que sobró
    
    double c1 = problemInstance->getC1();
    int max_new = (int)(budget_buy / c1);
	int huecos_para_nuevos = n - total_pre;
    int new_count = std::min(max_new, huecos_para_nuevos);

    int total_to_place = moves_count + new_count;
	
    InstalarEnHuecosLibres(total_to_place);
}

void CIndividualBase::GenerateSimpleFeasible_Reloc_HybridSplit_Aleatorio(double presupuesto_disponible, double split_pct)
{
    std::fill(x_var.begin(), x_var.end(), 0.0);
    const auto &nodos = problemInstance->getNodes();
    int n = x_var.size();
    double c2 = problemInstance->getC2();
    double P_total = (double)presupuesto_disponible;

    std::vector<int> pre;
    for(int i=0; i<n; ++i) if(nodos[i]->getFlag() == 1) pre.push_back(i);
    int total_pre = pre.size();

    // 1. FASE MOVER
    double budget_move = P_total * split_pct;
    int max_moves = (int)(budget_move / c2);
    int moves_count = std::min(max_moves, total_pre);
    
    // Aleatoriedad
    if(moves_count > 0) moves_count = rand() % (moves_count + 1);

    // Ejecutar movimiento
    std::vector<int> current_pre = pre;
    std::random_shuffle(current_pre.begin(), current_pre.end());

    int keep = total_pre - moves_count;
    for(int i=0; i<keep; ++i) x_var[current_pre[i]] = 1.0;

    double gastado_moves = moves_count * c2;

    // 2. FASE COMPRAR (Con el vuelto real)
    double budget_buy = P_total - gastado_moves; 
    
    double c1 = problemInstance->getC1();
    int max_new = (int)(budget_buy / c1);
    
    int new_count = 0;
    // Aleatoriedad
    if(max_new > 0) new_count = rand() % (max_new + 1);

    int total_to_place = moves_count + new_count;
    
    InstalarEnHuecosLibres(total_to_place);
}

void CIndividualBase::GenerateSimpleFeasible_Reloc_OnlyBuy_Aleatorio(double presupuesto_disponible)
{
    std::fill(x_var.begin(), x_var.end(), 0.0);
    const auto &nodos = problemInstance->getNodes();
    int largo_vector = x_var.size();

    // 1. Fijar TODOS los preinstalados (Flag 1)
    // En estrategia "Solo Comprar", no tocamos los viejos.
    for (int i = 0; i < largo_vector; ++i)
    {
        if (nodos[i]->getFlag() == 1) {
            x_var[i] = 1.0;
        }
    }

    double c1 = problemInstance->getC1();

    // 2. Calcular cuántos nuevos podemos comprar
    int max_new = (int)(presupuesto_disponible / c1);
    
    // Calcular huecos reales disponibles
    // (Ya marcamos con 1.0 los fijos, así que contamos los 0.0)
    int huecos_libres = 0;
    for(double val : x_var) if(val < 0.5) huecos_libres++;

    // El límite es el mínimo entre lo que puedo pagar y el espacio físico
    int limit_count = std::min(max_new, huecos_libres);

    int new_count = 0;
    // Aleatoriedad para diversidad
    if (limit_count > 0) new_count = rand() % (limit_count + 1);

    InstalarEnHuecosLibres(new_count);
}

void CIndividualBase::GenerateSimpleFeasible_Reloc_OnlyMove_Aleatorio(double presupuesto_disponible)
{
    std::fill(x_var.begin(), x_var.end(), 0.0);
    const auto &nodos = problemInstance->getNodes();
    int largo_vector = x_var.size();
    
    std::vector<int> pre_instalados;
    pre_instalados.reserve(largo_vector);

    // Identificar preinstalados
    for (int i = 0; i < largo_vector; ++i) {
        if (nodos[i]->getFlag() == 1) {
            pre_instalados.push_back(i);
        }
    }

    double c2 = problemInstance->getC2();
    int total_pre = pre_instalados.size();

    // 1. Calcular máximo teórico
    int max_moves = (int)(presupuesto_disponible / c2);
    int moves_count = std::min(max_moves, total_pre);
    
    // 2. IMPORTANTE: Aleatoriedad para diversidad
    // Si podemos mover 10, elegimos al azar entre 0 y 10.
    if (moves_count > 0) moves_count = rand() % (moves_count + 1);
    
    // 3. Ejecutar
    std::vector<int> actual_pre = pre_instalados;
    std::random_shuffle(actual_pre.begin(), actual_pre.end());

    int keep = total_pre - moves_count;
    for (int i = 0; i < keep; ++i) x_var[actual_pre[i]] = 1.0;

    InstalarEnHuecosLibres(moves_count);
}


void CIndividualBase::GenerateSimpleFeasible_Reloc_Choose_Move_or_Buy_Aleatorio(double presupuesto_disponible, double prob_choose_move)
{
	if (UtilityToolBox.Get_Random_Number() < prob_choose_move) {
        GenerateSimpleFeasible_Reloc_OnlyMove_Aleatorio((double)presupuesto_disponible);
    } else {
        GenerateSimpleFeasible_Reloc_OnlyBuy_Aleatorio((double)presupuesto_disponible);
    }
}

void CIndividualBase::GenerateSimpleFeasible_Random(double num_AEDs, double nums_Preinstalados)
{
	const auto &nodos = problemInstance->getNodes();
	int largo_vector = x_var.size();

	int total_a_instalar = num_AEDs + nums_Preinstalados;

	//printf("a instalar: %d\n", total_a_instalar);

	std::fill(x_var.begin(), x_var.end(), 0.0);

	std::vector<int> candidate_ids(largo_vector);
	for (int i = 0; i < largo_vector; ++i)
	{
		candidate_ids[i] = i;
	}

	std::random_shuffle(candidate_ids.begin(), candidate_ids.end());
	int limit = std::min(total_a_instalar, largo_vector);

	for (int i = 0; i < limit; ++i)
	{
		int idx = candidate_ids[i];
		x_var[idx] = 1.0;
	}
}

void CIndividualBase::GenerateRandomFullRange(int nums_AEDs_instalar)
{
    // 1. Limpieza
    std::fill(x_var.begin(), x_var.end(), 0.0);
    int total_nodes = x_var.size();

    // 2. Determinar aleatoriamente CUÁNTOS instalar
    // rand() % (total_nodes + 1) genera un número entre 0 y total_nodes (inclusive).
    int random_count = nums_AEDs_instalar;

    // 3. Generar lista de candidatos completa
    std::vector<int> candidates(total_nodes);
    for (int i = 0; i < total_nodes; ++i) {
        candidates[i] = i;
    }

    // 4. Mezclar aleatoriamente (Shuffle)
    std::random_shuffle(candidates.begin(), candidates.end());

    // 5. Instalar la cantidad aleatoria seleccionada
    for (int i = 0; i < random_count; ++i) {
        int idx = candidates[i];
        x_var[idx] = 1.0;
    }
}


void CIndividualBase::GenerateGreedyFeasibleSolution(int num_AEDs, double randomness_factor)
{
    // 1. Limpieza Total (Tabula Rasa)
    std::fill(x_var.begin(), x_var.end(), 0.0);
    int n = x_var.size();

    // 2. Control de estado de cobertura
    // Vector auxiliar para saber qué nodos de demanda ya están cubiertos
    std::vector<bool> is_covered(n, false);
    
    // Empezamos con el mapa vacío.
    
    int instalados = 0;
    const auto &nodos = problemInstance->getNodes();

    // 3. Bucle Constructivo
    while (instalados < num_AEDs)
    {
        // Lista de candidatos: Pareja <Ganancia Marginal, ID del Nodo>
        std::vector<std::pair<double, int>> candidates;
        candidates.reserve(n - instalados);

        // A. Evaluar ganancia marginal de cada sitio posible
        for (int i = 0; i < n; ++i) 
        {
            // Solo considerar si el sitio está vacío (x_var[i] == 0)
            if (x_var[i] < 0.5) 
            {
                double ganancia_marginal = 0.0;
                
                // Obtenemos a quiénes cubriría si instalamos aquí
                const std::vector<int>& alcanzables = problemInstance->getNodosCubiertosPor(i);

                for (int target_id : alcanzables) 
                {
                    // Sumamos valor solo si el objetivo NO está cubierto ya
                    if (!is_covered[target_id]) {
                        ganancia_marginal += nodos[target_id]->getProbOhca();
                    }
                }

                // Solo añadimos a la lista si aporta algo nuevo
                if (ganancia_marginal > 0.0) {
                    candidates.push_back({ganancia_marginal, i});
                }
            }
        }

        // B. Criterio de Parada temprano: Ya no hay ganancia posible
        if (candidates.empty()) {
            break; // Salimos al relleno aleatorio
        }

        // C. Ordenar candidatos por Ganancia (Mayor a Menor)
        // std::pair ordena por el primer elemento por defecto
        std::sort(candidates.rbegin(), candidates.rend());

        // D. Selección RCL (Restricted Candidate List)
        // randomness_factor (0.0 a 1.0) define qué tan larga es la lista de finalistas.
        // 0.0 = Greedy Puro (Top 1). 1.0 = Cualquier candidato útil.
        int rcl_size = std::max(1, (int)(candidates.size() * randomness_factor));
        
        // Elegir aleatoriamente dentro del top
        int selected_idx = rand() % rcl_size;
        int node_to_install = candidates[selected_idx].second;

        // E. Instalar y Actualizar Cobertura
        x_var[node_to_install] = 1.0;
        instalados++;

        // Marcar los nodos recién cubiertos
        const std::vector<int>& nuevos_cubiertos = problemInstance->getNodosCubiertosPor(node_to_install);
        for (int covered_node : nuevos_cubiertos) {
            is_covered[covered_node] = true;
        }
    }

    // 4. Relleno Aleatorio (Si el greedy paró antes de llenar el cupo)
    // Llenamos para cumplir la restricción estricta de num_AEDs.
    if (instalados < num_AEDs) 
    {
        std::vector<int> vacios;
        for(int i=0; i<n; ++i) {
            if(x_var[i] < 0.5) vacios.push_back(i);
        }
        
        std::random_shuffle(vacios.begin(), vacios.end());

        int faltantes = num_AEDs - instalados;
        int limit = std::min(faltantes, (int)vacios.size());

        for(int k=0; k<limit; ++k) {
            x_var[vacios[k]] = 1.0;
        }
    }
}

void CIndividualBase::GenerateSimpleFeasible_Reloc_BalancedQuantity(double presupuesto_disponible, double split_pct)
{
    // Limpieza inicial
    std::fill(x_var.begin(), x_var.end(), 0.0);
    
    const auto &nodos = problemInstance->getNodes();
    int n = x_var.size();
    double P = (double)presupuesto_disponible;
    double c1 = problemInstance->getC1(); // Costo Nuevo (Caro)
    double c2 = problemInstance->getC2(); // Costo Mover (Barato)

    // Identificar preinstalados
    std::vector<int> pre_indices;
    for(int i=0; i<n; ++i) if(nodos[i]->getFlag() == 1) pre_indices.push_back(i);
    int total_pre = (int)pre_indices.size();

    // -----------------------------------------------------------------
    // CÁLCULO DE CANTIDADES BALANCEADAS
    // -----------------------------------------------------------------
    // split_pct define qué proporción de las ACCIONES totales deben ser MOVER.
    // Ejemplo: 0.5 => Queremos misma cantidad de mover que de comprar.
    //          0.8 => Queremos mover mucho y comprar poco.
    
    // Evitamos división por cero si split_pct es extremo
    if (split_pct <= 0.0) split_pct = 0.01;
    if (split_pct >= 1.0) split_pct = 0.99;

    // Ratio deseado: N_move / N_new
    // Si split = 0.5 -> ratio = 0.5/0.5 = 1.0
    // Si split = 0.8 -> ratio = 0.8/0.2 = 4.0
    double ratio = split_pct / (1.0 - split_pct);

    // Costo promedio ponderado por acción según el ratio deseado
    // "Costo del paquete" (1 nuevo + R movidos) = c1 + R*c2
    double package_cost = c1 + (ratio * c2);

    // Cuántos "paquetes" caben en el presupuesto
    double num_packages = P / package_cost;

    // Desglosamos en cantidades enteras ideales
    int target_new = (int)num_packages;
    int target_move = (int)(num_packages * ratio);

    // -----------------------------------------------------------------
    // APLICACIÓN DE LÍMITES FÍSICOS
    // -----------------------------------------------------------------
    
    // 1. Limite de Mover: No podemos mover más de los que existen
    if (target_move > total_pre) {
        target_move = total_pre;
    }

    // 2. Recalcular reales según presupuesto exacto
    // Aseguramos que la combinación calculada entre en el dinero
    double cost_curr = (target_new * c1) + (target_move * c2);
    while (cost_curr > P) {
        // Si nos pasamos (por redondeo), reducimos proporcionalmente
        if (target_new > 0) { target_new--; cost_curr -= c1; }
        else if (target_move > 0) { target_move--; cost_curr -= c2; }
        else break;
    }
    
    // Opcional: Gastar remanente. Si sobra dinero tras topar los Moves, compramos más News.
    double remanente = P - cost_curr;
    while (remanente >= c1) {
        target_new++;
        remanente -= c1;
    }

    // -----------------------------------------------------------------
    // ALEATORIEDAD
    // -----------------------------------------------------------------
    if (target_move > 0) target_move = rand() % (target_move + 1);
    if (target_new > 0) target_new = rand() % (target_new + 1);


    // -----------------------------------------------------------------
    // EJECUCIÓN FÍSICA
    // -----------------------------------------------------------------

    // A. Gestionar los que se quedan quietos
    // Se quedan = Total - Mover
    int keep_count = total_pre - target_move;
    if (keep_count < 0) keep_count = 0;

    std::random_shuffle(pre_indices.begin(), pre_indices.end());
    for(int i=0; i<keep_count; ++i) {
        x_var[pre_indices[i]] = 1.0;
    }

    // B. Instalar los "Muebles" (Mover + Nuevos)
    // Estos se colocan en huecos libres aleatorios
    int total_to_place = target_move + target_new;
    
    InstalarEnHuecosLibres(total_to_place);
}

void CIndividualBase::GenerateSimpleFeasibleSolution_v2(int num_AEDs, int total_locations)
{
	std::fill(x_var.begin(), x_var.end(), 0.0);

	std::vector<int> ids(total_locations);
	for (int i = 0; i < total_locations; ++i)
	{
		ids[i] = i;
	}

	const auto &nodos = problemInstance->getNodes();
	int pre_instalados = 0;
	std::vector<int> pre_ids;

	for (int i = 0; i < total_locations; ++i)
	{
		if (nodos[i]->getFlag() == 1)
		{
			x_var[i] = 1.0;
			pre_instalados++;
			pre_ids.push_back(i);
		}
	}

	std::random_shuffle(ids.begin(), ids.end());
	std::random_shuffle(pre_ids.begin(), pre_ids.end());

	int restante = num_AEDs - pre_instalados;
	if (restante <= 0)
		return;

	bool instalar = true;
	if (pre_instalados > 0)
	{
		instalar = (rand() % 2 == 0); // 50/50 solo si hay posibilidad real de reubicar
	}
	if (instalar)
	{
		// MODO 1: instalar AEDs nuevos
		int instalados = 0;
		for (int i = 0; instalados < restante && i < total_locations; ++i)
		{
			int pos = ids[i];
			if (x_var[pos] == 0.0)
			{
				x_var[pos] = 1.0;
				instalados++;
			}
		}
	}
	else
	{
		// MODO 2: reubicar AEDs preinstalados
		int reubicados = 0;
		for (int i = 0; reubicados < restante && i < (int)pre_ids.size(); ++i)
		{
			int pre_idx = pre_ids[i];

			// Buscar una nueva ubicación libre
			for (int j = 0; j < total_locations; ++j)
			{
				int new_pos = ids[j];
				if (x_var[new_pos] == 0.0)
				{
					x_var[pre_idx] = 0.0;
					x_var[new_pos] = 1.0;
					reubicados++;
					break;
				}
			}
		}
	}
}

void CIndividualBase::Evaluate()
{

	// if(!strcmp("ZDT1", strTestInstance))   TestInstance.ZDT1(x_var, f_obj, x_var.size());
	// TestInstance.fdvrp(x_var, f_obj, x_var.size());

	TestInstance.DRP_Evaluate(x_var, f_obj, problemInstance);
}

void CIndividualBase::Show(int type)
{

	unsigned int n;
	if (type == 0)
	{
		for (n = 0; n < NumberOfObjectives; n++)
			std::cout << f_obj[n] << " ";
		std::cout << endl;
	}
	else
	{
		for (n = 0; n < NumberOfVariables; n++)
			printf("%f ", x_var[n]);
		printf("\n");
	}
}

void CIndividualBase::operator=(const CIndividualBase &ind2)
{
	x_var = ind2.x_var;
	f_obj = ind2.f_obj;
	f_normal = ind2.f_normal;
	rank = ind2.rank;
	type = ind2.type;
	count = ind2.count;
	density = ind2.density;
}

bool CIndividualBase::operator<(const CIndividualBase &ind2)
{
	bool dominated = true;
	unsigned int n;
	for (n = 0; n < NumberOfObjectives; n++)
	{
		if (ind2.f_obj[n] < f_obj[n])
			return false;
	}
	if (ind2.f_obj == f_obj)
		return false;
	return dominated;
}

bool CIndividualBase::operator<<(const CIndividualBase &ind2)
{
	bool dominated = true;
	unsigned int n;
	for (n = 0; n < NumberOfObjectives; n++)
	{
		if (ind2.f_obj[n] < f_obj[n] - 0.0001)
			return false;
	}
	if (ind2.f_obj == f_obj)
		return false;
	return dominated;
}

bool CIndividualBase::operator==(const CIndividualBase &ind2)
{
	if (ind2.f_obj == f_obj)
		return true;
	else
		return false;
}
