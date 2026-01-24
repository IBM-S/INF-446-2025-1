// TestInstance.cpp: implementation of the CTestInstance class.
//
//////////////////////////////////////////////////////////////////////

#include "TestInstance.h"
#include <iostream>

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

CTestInstance::CTestInstance()
{

}

CTestInstance::~CTestInstance()
{

}

// Final evaluation function for the DRP and CAM problem

void CTestInstance::DRP_Evaluate(const vector<double>& x, vector<double>& f, ProblemInstance* instance)
{
	double cobertura_total = 0.0;
	double aeds_totales = 0.0;

    // 1. OPTIMIZACIÓN DE MEMORIA
    static std::vector<bool> is_covered; 
    if (is_covered.size() != x.size()) {
        is_covered.resize(x.size());
    }
    // Reiniciamos el mapa de cobertura a false
    std::fill(is_covered.begin(), is_covered.end(), false);

    const auto& nodos = instance->getNodes();
    double c1 = instance->getC1(); // Costo de instalación nueva
    double c2 = instance->getC2(); // Costo de reubicación

	// -----------------------------------------------------------
	// 2. CÁLCULO DE COSTOS (Lógica de Reubicación vs Nuevo)
	// -----------------------------------------------------------
	int count_removidos = 0; // Estaba (Flag 1) y ahora es 0
	int count_nuevos = 0;    // No estaba (Flag 0) y ahora es 1

	for (size_t i = 0; i < x.size(); ++i) {
        bool es_preinstalado = (nodos[i]->getFlag() == 1);
        bool esta_activo = (x[i] >= 0.5);

		if (es_preinstalado && !esta_activo) {
			count_removidos++; 
		}
		if (!es_preinstalado && esta_activo) {
			count_nuevos++; 
		}
	}

    // Si quitamos 3 y ponemos 5 nuevos:
    // 3 se consideran "reubicaciones" (costo c2)
    // 2 se consideran "compras nuevas" (costo c1)
	int reubicaciones = std::min(count_removidos, count_nuevos);
	int solo_nuevos = count_nuevos - reubicaciones;

	aeds_totales = (reubicaciones * c2) + (solo_nuevos * c1);

    // -----------------------------------------------------------
    // 3. CÁLCULO DE COBERTURA (Usando Mapa Pre-Calculado)
    // -----------------------------------------------------------
    
    // A. Marcar cobertura en el mapa booleano
    for (size_t i = 0; i < x.size(); ++i) 
    {
        if (x[i] >= 0.5) // Si hay un AED activo en el nodo i
        {
            // Obtenemos la lista de vecinos que este nodo cubre (Pre-calculada en ProblemInstance)
            const std::vector<int>& vecinos = instance->getNodosCubiertosPor(i);
            
            // Marcamos a todos los vecinos como cubiertos
            for (int vecino_id : vecinos) {
                is_covered[vecino_id] = true;
            }
        }
    }

    // B. Sumar probabilidades
    // sumamos todo lo que esté marcado.
    for (size_t j = 0; j < x.size(); ++j) 
    {
        if (is_covered[j]) 
        {
            cobertura_total += nodos[j]->getProbOhca();
        }
    }

    f[0] = -cobertura_total; 
    f[1] = aeds_totales;    
}


// Firsts versions of the evaluation function

void CTestInstance::DRP_Evaluate_v2(const vector<double>& x, vector<double>& f, ProblemInstance* instance)
{
	double cobertura_total = 0.0;
	double aeds_totales = 0.0;

    const auto& nodos = instance->getNodes();
    int R = instance->getR();
    double c1 = instance->getC1();
    double c2 = instance->getC2();

	std::vector<int> removidos; // AEDs preinstalados que ya no están
	std::vector<int> nuevos;    // AEDs nuevos que no estaban antes

	// Paso 1: identificar removidos y nuevos
	for (size_t i = 0; i < x.size(); ++i) {
		if (nodos[i]->getFlag() == 1 && x[i] < 0.5) {
			removidos.push_back(i); // Se quitó un AED preinstalado
		}
		if (nodos[i]->getFlag() == 0 && x[i] >= 0.5) {
			nuevos.push_back(i); // Se instaló un nuevo AED
		}
	}

	// Paso 2: calcular reubicaciones
	int reubicaciones = std::min(removidos.size(), nuevos.size());
	int solo_nuevos = nuevos.size() - reubicaciones;

	aeds_totales += reubicaciones * c2;  // Reubicación = solo c2
	aeds_totales += solo_nuevos * c1;    // Nuevas instalaciones reales
	/* std::cout << aeds_totales << " ";
	std::cout << std::endl; */

    // Para cada nodo con OHCA, verificar si está cubierto por algún AED
    for (auto* nodo_ohca : nodos) {
        if (nodo_ohca->getProbOhca() <= 0.0) continue;

        double px = nodo_ohca->getX();
        double py = nodo_ohca->getY();

        bool cubierto = false;

        for (size_t i = 0; i < x.size(); ++i) {
            if (x[i] >= 0.5) {
                Node* aed = nodos[i];
                double dx = px - aed->getX();
                double dy = py - aed->getY();
                double distancia = sqrt(dx*dx + dy*dy);

                if (distancia <= R) {
                    cubierto = true;
                    break;
                }
            }
        }

        if (cubierto) {
            cobertura_total += nodo_ohca->getProbOhca();  // o simplemente +1
        }
    }

	/* double budget = instance->getP(); // Supón que lo tienes definido en tu instancia
	if (aeds_totales > budget) {
		f[0] = 1e9;         // Pésima cobertura
		f[1] = 1e9;         // Costo altísimo para forzar descarte
		return;
	} */

    f[0] = -cobertura_total;
    f[1] = aeds_totales;  // usar negativo si vas a minimizar ambos objetivos
}

void CTestInstance::DRP_Evaluate_v6(const vector<double>& x, vector<double>& f, ProblemInstance* instance)
{
    double cobertura_total = 0.0;
    double aeds_totales = 0.0;

    const auto& nodos = instance->getNodes();
    double c1 = instance->getC1();
    double c2 = instance->getC2();

    // ---------------------------------------------------------------------
    // 1. COBERTURA (Lógica de Conjuntos)
    // ---------------------------------------------------------------------
    
    // Paso A: Cargamos la "Lista de ya cubiertos" precalculada
    // Esto incluye la demanda cubierta por flag=1 y las cámaras mismas.
    // Usamos 'static' para no reasignar memoria, pero COPIAMOS el estado base.
    static std::vector<bool> current_covered;
    current_covered = instance->getBaseCoverage(); // Copia rápida del vector base

    // Paso B: Agregar la cobertura de los NUEVOS equipos (Marginal)
    for (size_t i = 0; i < x.size(); ++i) 
    {
        // Si es un sitio NUEVO (flag=0) y decidimos poner un AED (x >= 0.5)
        // (Nota: Los flag=1 ya están considerados en getBaseCoverage, no los procesamos aquí)
        if (nodos[i]->getFlag() == 0 && x[i] >= 0.5) 
        {
            const std::vector<int>& vecinos = instance->getNodosCubiertosPor(i);
            for (int vecino_id : vecinos) {
                current_covered[vecino_id] = true;
            }
        }
    }

    // Paso C: Sumar Probabilidades (Igual que AMPL)
    for (size_t j = 0; j < current_covered.size(); ++j) 
    {
        if (current_covered[j]) {
            cobertura_total += nodos[j]->getProbOhca();
        }
    }

    // ---------------------------------------------------------------------
    // 2. COSTOS (Lógica de Reubicación)
    // ---------------------------------------------------------------------
    int count_removidos = 0;
    int count_nuevos = 0;

    for (size_t i = 0; i < x.size(); ++i) {
        if (nodos[i]->getFlag() == 1 && x[i] < 0.5) count_removidos++;
        if (nodos[i]->getFlag() == 0 && x[i] >= 0.5) count_nuevos++;
    }
    
    int reubicaciones = std::min(count_removidos, count_nuevos);
    int solo_nuevos = count_nuevos - reubicaciones;
    aeds_totales = (reubicaciones * c2) + (solo_nuevos * c1);

    f[0] = -cobertura_total; 
    f[1] = aeds_totales;     
}

void CTestInstance::fdvrp(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	unsigned int j;
	double sum1,g;

	sum1 = 0.0;
	for(j = 1; j <= nx-1; j++)
	{
		sum1 += x[j];
	}
	g=1+9*sum1/(nx-1);
	f[0] = x[0];
	f[1] = g*(1-sqrt(x[0]/g));
}

void CTestInstance::DTLZ1(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(3, 0);

	double g = 0, z;
	int count = 0;

	for(unsigned int j = 3; j <=nx; j++) 
	{
		z = x[j-1]-0.5;
		g += z*z - cos(20*PI*z);
		count++;
	}
	g = 100*(count + g);

	f[0] = (1+g)*1*x[0]*x[1];
	f[1] = (1+g)*2*x[0]*(1-x[1]);
	f[2] = (1+g)*10*(1-x[0]);
}

void CTestInstance::DTLZ2(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(3, 0);

	double g = 0, z;

	for(unsigned int j = 3; j <=nx; j++) 
	{
		z = 2*(x[j-1]-0.5);
		g = g + z*z;
	}

	f[0] = (1+g)*cos(x[0]*PI/2)*cos(x[1]*PI/2);
	f[1] = (1+g)*2*cos(x[0]*PI/2)*sin(x[1]*PI/2);
	f[2] = (1+g)*10*sin(x[0]*PI/2);
}


void CTestInstance::ZDT1(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	unsigned int j;
	double sum1,g;

	sum1 = 0.0;
	for(j = 1; j <= nx-1; j++) 
	{
		sum1 += x[j];
	}
	g=1+9*sum1/(nx-1);
	f[0] = x[0];
	f[1] = g*(1-sqrt(x[0]/g));
}



void CTestInstance::ZDT2(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	unsigned int j;
	double sum1,g;

	sum1 = 0.0;
	for(j = 1; j <= nx-1; j++) 
	{
		sum1 += x[j];
	}
	g=1+9*sum1/(nx-1);
	f[0] = x[0];
	f[1] = g*(1-(x[0]/g)*(x[0]/g));
}


void CTestInstance::ZDT3(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	unsigned int i;
	double sum1,g,h;

	sum1=0.0;
	for(i=1;i<=nx-1;i++)
	{
		sum1 += x[i];
	}
	g=1+9*sum1/(nx-1);
	h=1-sqrt(x[0]/g)-(x[0]/g)*sin(10*PI*x[0]);
	f[0]=x[0];
	f[1]=g*h;
}



void CTestInstance::TEC09_LZ1(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	double       sum1   = 0.0,  sum2   = 0.0, yj, theta;
	unsigned int count1 = 0,    count2 = 0;

	//printf("%f ", x[0]);
	for(unsigned int j = 2; j <=nx; j++) 
	{
		theta = 1.0 + 3.0*(j-2)/(double)(nx - 2);
		yj    = x[j-1] - pow(x[0], 0.5*theta);
		yj    = yj * yj;
		//printf("%f ", x[j-1]);
		if(j % 2 == 0) 
		{
			sum2 += yj;
			count2++;
		} 
		else {
			sum1 += yj;
			count1++;
		}
	}
	f[0] = x[0]				+ 2.0 * sum1 / (double)count1;
	f[1] = 1.0 - sqrt(x[0]) + 2.0 * sum2 / (double)count2;

}

void CTestInstance::TEC09_LZ2(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);
	//f = std::vector<double>(10, 0);

	double       sum1   = 0.0, sum2   = 0.0, xj, yj, theta;
	unsigned int count1 = 0,   count2 = 0;

	for(unsigned int j = 2; j <=nx; j++) 
	{
		xj    = -1.0 + 2.0*x[j-1];
		theta = 6*PI*x[0] + j*PI/nx;
		yj    = xj - sin(theta);
		yj    = yj * yj;
		if(j % 2 == 0) 
		{
			sum2 += yj;
			count2++;
		} 
		else 
		{
			sum1 += yj;
			count1++;
		}
	}
	f[0] = x[0]				+ 2.0 * sum1 / (double)count1;
	f[1] = 1.0 - sqrt(x[0]) + 2.0 * sum2 / (double)count2;
}



void CTestInstance::TEC09_LZ3(vector<double> &x, vector<double> &f, const unsigned int nx)
{

	f = std::vector<double>(2, 0);

	double       sum1   = 0.0, sum2   = 0.0, xj, yj, theta;
	unsigned int count1 = 0,   count2 = 0;

	for(unsigned int j = 2; j <=nx; j++) 
	{
		xj    = -1.0 + 2.0*x[j-1];
		theta = 6*PI*x[0] + j*PI/nx;
		if(j % 2 == 0) {		
			yj    = xj - 0.8*x[0]*cos(theta);
			sum2 += yj*yj;
			count2++;
		} 
		else 
		{
			yj    = xj - 0.8*x[0]*sin(theta);
			sum1 += yj*yj;
			count1++;
		}
	}
	f[0] = x[0]				+ 2.0 * sum1 / (double)count1;
	f[1] = 1.0 - sqrt(x[0]) + 2.0 * sum2 / (double)count2;
}

void CTestInstance::TEC09_LZ4(vector<double> &x, vector<double> &f, const unsigned int nx)
{	
	f = std::vector<double>(2, 0);

	double       sum1   = 0.0, sum2   = 0.0, xj, yj, theta;
	unsigned int count1 = 0,   count2 = 0;

	for(unsigned int j = 2; j <=nx; j++) 
	{
		xj    = -1.0 + 2.0*x[j-1];
		theta = 6*PI*x[0] + j*PI/nx;
		if(j % 2 == 0) 
		{		
			yj    = xj - 0.8*x[0]*cos(theta/3);
			sum2 += yj*yj;
			count2++;
		} 
		else 
		{
			yj    = xj - 0.8*x[0]*sin(theta);
			sum1 += yj*yj;
			count1++;
		}
	}
	f[0] = x[0]				+ 2.0 * sum1 / (double)count1;
	f[1] = 1.0 - sqrt(x[0]) + 2.0 * sum2 / (double)count2;
}

void CTestInstance::TEC09_LZ5(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	double       sum1   = 0.0, sum2   = 0.0, xj, yj, theta;
	unsigned int count1 = 0,   count2 = 0;

	for(unsigned int j = 2; j <=nx; j++) 
	{
		xj    = -1.0 + 2.0*x[j-1];
		theta = 6*PI*x[0] + j*PI/nx;
		if(j % 2 == 0) 
		{		
			yj = xj - (0.3*x[0]*x[0]*cos(4*theta) + 0.6*x[0])*sin(theta);
			sum2 += yj*yj;
			count2++;
		} 
		else 
		{
			yj = xj - (0.3*x[0]*x[0]*cos(4*theta) + 0.6*x[0])*cos(theta);
			sum1 += yj*yj;
			count1++;
		}
	}
	f[0] = x[0]				+ 2.0 * sum1 / (double)count1;
	f[1] = 1.0 - sqrt(x[0]) + 2.0 * sum2 / (double)count2;
}


void CTestInstance::TEC09_LZ6(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(3, 0);

	double sum1 = 0.0, sum2 = 0.0, sum3 = 0.0, xj, yj, theta;
	int    count1 = 0, count2 = 0, count3 = 0;

	for(unsigned int j = 3; j <=nx; j++) 
	{
		xj    = -2.0 + 4.0*x[j-1];
		theta = 2*PI*x[0] + j*PI/nx;
		yj    = xj - 2*x[1]*sin(theta);
		if(j % 3 == 0) {		
			sum3 += yj*yj;
			count3++;
		} 
		else if(j % 3 ==1){
			sum2 += yj*yj;
			count2++;
		} 
		else
		{
			sum1 += yj*yj;
			count1++;
		}
	}
	f[0] = cos(0.5*x[0]*PI)*cos(0.5*x[1]*PI) + 2.0 * sum1 / (double)count1;
	f[1] = cos(0.5*x[0]*PI)*sin(0.5*x[1]*PI) + 2.0 * sum2 / (double)count2;
	f[2] = sin(0.5*x[0]*PI)                  + 2.0 * sum3 / (double)count3;
}

void CTestInstance::TEC09_LZ7(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	double       sum1 = 0.0, sum2 = 0.0,  yj, theta;
	unsigned int count1 = 0, count2 = 0;

	for(unsigned int j = 2; j <=nx; j++) 
	{
		theta = 1.0 + 3.0*(j-2)/(double)(nx - 2); 
		yj    = x[j-1] -  pow(x[0], 0.5*theta);
		yj    = 4*yj*yj - cos(8*yj*PI) + 1.0;
		if(j % 2 == 0) 
		{
			sum2 += yj;
			count2++;
		} 
		else {
			sum1 += yj;
			count1++;
		}
	}
	f[0] = x[0]				+ 2.0 * sum1 / (double)count1;
	f[1] = 1.0 - sqrt(x[0]) + 2.0 * sum2 / (double)count2;
}


void CTestInstance::TEC09_LZ8(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	unsigned int count1 = 0,   count2 = 0;
	double       prod1  = 1.0, prod2  = 1.0;	
	double       sum1   = 0.0, sum2   = 0.0, yj, theta;

	for(unsigned int j = 2; j <=nx; j++) 
	{
		theta = 1.0 + 3.0*(j-2)/(double)(nx - 2);; 
		yj    = x[j-1] - pow(x[0], 0.5*theta);
		if(j % 2 == 0) 
		{
			sum2 += yj*yj;
			prod2*=cos(20*yj*PI/sqrt(j));
			count2++;
		} 
		else {
			sum1 += yj*yj;
			prod1*=cos(20*yj*PI/sqrt(j));
			count1++;
		}
	}
	f[0] = x[0]				+ 2.0 * (4*sum1 - 2*prod1 + 2) / (double)count1;
	f[1] = 1.0 - sqrt(x[0]) + 2.0 * (4*sum2 - 2*prod2 + 2) / (double)count2;
}

void CTestInstance::TEC09_LZ9(vector<double> &x, vector<double> &f, const unsigned int nx)
{
	f = std::vector<double>(2, 0);

	double       sum1   = 0.0, sum2   = 0.0, xj, yj, theta;
	unsigned int count1 = 0,   count2 = 0;

	for(unsigned int j = 2; j <=nx; j++) 
	{
		xj    = -1.0 + 2.0*x[j-1];
		theta = 6*PI*x[0] + j*PI/nx;
		yj    = xj - sin(theta);
		yj    = yj * yj;
		if(j % 2 == 0) {
			sum2 += yj;
			count2++;
		} 
		else {
			sum1 += yj;
			count1++;
		}
	}
	f[0] = x[0]				+ 2.0 * sum1 / (double)count1;
	f[1] = 1.0 - x[0]*x[0]  + 2.0 * sum2 / (double)count2;
}

