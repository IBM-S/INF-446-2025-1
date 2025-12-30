// Individual.cpp: implementation of the CIndividualBase class.
//
//////////////////////////////////////////////////////////////////////
#include <iostream>
#include <random>
#include "IndividualBase.h"

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

// Con est funcion vamos a crear funciones factibles.
// A partir de la representacion binaria. Con k desfibriladores, con
// el presupuesto.

void CIndividualBase::GenerateSimpleFeasibleSolution(int num_AEDs, int total_locations)
{
	//std::cout << "\n DEBUG START " << std::endl;
	//std::cout << "Target num_AEDs a instalar: " << num_AEDs << std::endl;
	//std::cout << "Total locations disponibles: " << total_locations << std::endl;
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

void CIndividualBase::GenerateSimpleFeasibleSolution_For_Relocation(int budget_units, int total_locations)
{
    std::fill(x_var.begin(), x_var.end(), 0.0);

	total_locations = x_var.size();

    const auto &nodos = problemInstance->getNodes();

    std::vector<int> indices_preinstalados;
	indices_preinstalados.reserve(total_locations);
    for (int i = 0; i < total_locations; ++i) {
        if (nodos[i]->getFlag() == 1) indices_preinstalados.push_back(i);
    }
	int total_preinstalados = indices_preinstalados.size();

	double porcentaje_a_mover = UtilityToolBox.Get_Random_Number();

	int cantidad_a_mover = (int)(porcentaje_a_mover * total_preinstalados);

    std::random_shuffle(indices_preinstalados.begin(), indices_preinstalados.end());

	int cantidad_a_dejar = total_preinstalados - cantidad_a_mover;
	for (int i = 0; i < cantidad_a_dejar; ++i) {
		int idx = indices_preinstalados[i];
		x_var[idx] = 1.0; // Mantener en su lugar
	}

	int aeds_en_la_mano = cantidad_a_mover + budget_units;

	std::vector<int> espacios_libres;
	espacios_libres.reserve(total_locations);
	for (int i = 0; i < total_locations; ++i) {
		if (nodos[i]->getFlag() == 0 and x_var[i] < 0.5) espacios_libres.push_back(i);
	}

	std::random_shuffle(espacios_libres.begin(), espacios_libres.end());

	if (aeds_en_la_mano > espacios_libres.size()) {
		aeds_en_la_mano = espacios_libres.size();
	}

	for (int i = 0; i < aeds_en_la_mano; ++i) {
		int idx = espacios_libres[i];
		x_var[idx] = 1.0; // Instalar en nuevo lugar
	}
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
	// TestInstance.DRP_Evaluate(x_var, f_obj, problemInstance);
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


void CIndividualBase::GenerateGreedyFeasibleSolution(int num_AEDs, double randomness_factor){

 	// 1. Limpiar genotipo
    std::fill(x_var.begin(), x_var.end(), 0.0);

    const auto &nodos = problemInstance->getNodes();
    int n = x_var.size();
    
    // 2. Estado de cobertura actual (inicia con lo que cubren las cámaras fijas)
    // Usamos un vector auxiliar para saber qué nodos de demanda ya están salvados
    std::vector<bool> is_covered(n, false);
    int instalados = 0;

    // A. Pre-instalar infraestructura fija (Flag 1) y marcar su cobertura
    for (int i = 0; i < n; ++i) {
        if (nodos[i]->getFlag() == 1) {
            x_var[i] = 1.0;
            instalados++; // Generalmente no cuentan para el presupuesto P, pero depende de tu lógica
            
            // Marcar vecinos como cubiertos
            const std::vector<int>& vecinos = problemInstance->getNodosCubiertosPor(i);
            for (int v : vecinos) is_covered[v] = true;
        } else {
            // Si es demanda y ya está cubierto por base (cámaras), marcarlo
            if (problemInstance->isPreCubierto(i)) is_covered[i] = true;
        }
    }

    // B. Bucle Greedy: Instalar hasta llegar al objetivo
    // Ajustamos el objetivo restando los fijos si tu num_AEDs incluye fijos.
    // Asumiremos que num_AEDs es el TOTAL de equipos en el mapa.
    
    while (instalados < num_AEDs)
    {
        // Lista de candidatos potenciales (ID, Ganancia Marginal)
        std::vector<std::pair<double, int>> candidatos;

        // Recorremos todos los nodos candidatos (Flag 0 y que estén vacíos)
        for (int i = 0; i < n; ++i) 
        {
            if (x_var[i] == 0.0 && nodos[i]->getFlag() == 0) 
            {
                double ganancia = 0.0;
                const std::vector<int>& vecinos = problemInstance->getNodosCubiertosPor(i);
                
                // Calculamos cuánto aporta este candidato
                for (int v : vecinos) {
                    // Si es un nodo de demanda y NO está cubierto aun
                    if (!is_covered[v] && nodos[v]->getFlag() == 0) {
                        ganancia += nodos[v]->getProbOhca();
                    }
                }

                // Solo lo consideramos si aporta algo positivo
                if (ganancia > 0) {
                    candidatos.push_back({ganancia, i});
                }
            }
        }

        if (candidatos.empty()) {
            // Ya no hay nada útil que cubrir, rellenar con aleatorios para cumplir presupuesto
            std::vector<int> vacios;
            for(int i=0; i<n; ++i) if(x_var[i]==0 && nodos[i]->getFlag()==0) vacios.push_back(i);
            std::random_shuffle(vacios.begin(), vacios.end());
            
            for(int k=0; k < (int)vacios.size() && instalados < num_AEDs; ++k) {
                x_var[vacios[k]] = 1.0;
                instalados++;
            }
            break; 
        }

        // C. Selección (Greedy vs Aleatorio)
        int elegido_idx = -1;

        // Ordenamos de MAYOR ganancia a MENOR
        std::sort(candidatos.rbegin(), candidatos.rend());

        // randomness_factor: 
        // 0.0 = Greedy Puro (siempre el mejor)
        // 1.0 = Totalmente Aleatorio dentro de los candidatos útiles
        
        // Estrategia: Torneo o Selección de los "Top N"
        // Aquí usaremos selección dentro del Top %
        int top_k = std::max(1, (int)(candidatos.size() * randomness_factor));
        int r = rand() % top_k; // Elegir uno al azar entre los mejores
        
        elegido_idx = candidatos[r].second;

        // D. Instalar y Actualizar Cobertura
        x_var[elegido_idx] = 1.0;
        instalados++;

        const std::vector<int>& nuevos_cubiertos = problemInstance->getNodosCubiertosPor(elegido_idx);
        for (int v : nuevos_cubiertos) {
            is_covered[v] = true;
        }
    }
}