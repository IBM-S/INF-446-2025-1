#include "DRP_ProblemInstance.h"
#include <iostream>
#include <cmath>

// Constructor
ProblemInstance::ProblemInstance()
{
    P = 0;
    R = 0;
    c1 = 0;
    c2 = 0;
}

// Destructor
ProblemInstance::~ProblemInstance()
{
    for (Node *node : nodes)
    {
        delete node;
    }
    nodes.clear();
}

// Añadir un nodo
void ProblemInstance::addNode(Node *node)
{
    for (Node *existing : nodes)
    {
        if (existing->getId() == node->getId())
            return;
    }
    nodes.push_back(node);
    if (node->getFlag() == 0)
    {
        candidateLocations.push_back(node->getId());
    }
}

// Getters de listas
std::vector<int> ProblemInstance::getCandidateLocations()
{
    return candidateLocations;
}

std::vector<Node *> &ProblemInstance::getNodes()
{
    return nodes;
}

// Setters y Getters
/* void ProblemInstance::setAlpha(int a) { alpha = a; }
void ProblemInstance::setBeta(int b) { beta = b; }
int ProblemInstance::getAlpha() { return alpha; }
int ProblemInstance::getBeta() { return beta; } */
// Parámetros
void ProblemInstance::setN(int n) { N = n; }

int ProblemInstance::getN() { return N; }

void ProblemInstance::setP(double p) { P = p; }
double ProblemInstance::getP() { return P; }

void ProblemInstance::setR(int r) { R = r; }
int ProblemInstance::getR() { return R; }

void ProblemInstance::setC1(double c) { c1 = c; }
double ProblemInstance::getC1() { return c1; }

void ProblemInstance::setC2(double c) { c2 = c; }
double ProblemInstance::getC2() { return c2; }

void ProblemInstance::setNombreInstancia(std::string nombre) { nombre_instancia = nombre; }
std::string ProblemInstance::getNombreInstancia() { return nombre_instancia; }

// Debug: imprimir todo
void ProblemInstance::printAll()
{
    std::cout << "\n  > Propiedades Instancia: " << nombre_instancia << std::endl;
    std::cout << "    - Presupuesto (P)   : " << P << std::endl;
    std::cout << "    - Radio (R)         : " << R << " m" << std::endl;
    std::cout << "    - Costos (c1/c2)    : " << c1 << " / " << c2 << std::endl;

    int preinstalados = 0;
    for(auto n : nodes) if(n->getFlag() == 1) preinstalados++;
    
    std::cout << "    - Total Nodos       : " << nodes.size() << std::endl;
    std::cout << "    - Pre-instalados    : " << preinstalados << std::endl;
    std::cout << "    - Candidatos Libres : " << nodes.size() - preinstalados << std::endl;

    std::cout << "\n  > Nodos (mostrando los primeros 3 de " << nodes.size() << "):\n";
    int nodos_a_mostrar = std::min((size_t)3, nodes.size());

    for (int i = 0; i < nodos_a_mostrar; i++)
    {
        Node *node = nodes[i];
        std::cout << "    - ID: " << node->getId()
                  << ", Coord: (" << node->getX() << ", " << node->getY() << ")"
                  << ", Flag: " << node->getFlag()
                  << ", OHCA Prob: " << node->getProbOhca() << "\n";
    }
    if (nodes.size() > 3)
    {
        std::cout << "    - ...\n\n";
    }
}

void ProblemInstance::PrecalcularCoberturas()
{
    //std::cout << ">>> Precalculando PARES_CUBRIBLES (Esto puede tardar unos segundos)..." << std::endl;
    int n = nodes.size();
    coverageMap.assign(n, std::vector<int>());
    is_base_covered.assign(n, false);


    double R2 = (double)R * (double)R; // Usamos radio al cuadrado para evitar sqrt

    for (int i = 0; i < n; ++i) 
    {
        // Si el nodo i es un candidato (flag=0 o flag=1 si queremos saber a quién cubre la cámara)
        double ax = nodes[i]->getX();
        double ay = nodes[i]->getY();

        for (int j = 0; j < n; ++j) 
        {
            // Calculamos distancia al cuadrado
            double dx = ax - nodes[j]->getX();
            double dy = nodes[j]->getY() - ay;
            
            // Distancia euclidiana optimizada
            if ((dx*dx + dy*dy) <= R2) 
            {
                // El nodo i puede cubrir al nodo j
                coverageMap[i].push_back(j);
            }
        }
    }
    // 3. Pre-calcular qué está cubierto por la infraestructura FIJA (Cámaras/Flag 1)
    //    Esto servirá para que la Mutación sea inteligente.
    for (int i = 0; i < n; ++i)
    {
        if (nodes[i]->getFlag() == 1) // Es una cámara / Preinstalado
        {
            // Todos los vecinos de esta camara ya estan cubiertos
            const std::vector<int>& vecinos = coverageMap[i];
            for (int vecino_id : vecinos) {
                is_base_covered[vecino_id] = true;
            }
        }
    }
    
    // std::cout << ">>> Precalculo terminado (Mapa + Cobertura Base)." << std::endl;
}

const std::vector<int>& ProblemInstance::getNodosCubiertosPor(int aed_id) {
    return coverageMap[aed_id];
}

const std::vector<bool>& ProblemInstance::getBaseCoverage() {
    return is_base_covered;
}

bool ProblemInstance::isPreCubierto(int node_id) 
{
    // Validación de seguridad por si acaso mandan un ID inválido
    if (node_id < 0 || node_id >= (int)is_base_covered.size()) 
    {
        return false;
    }
    
    // Retorna true si el nodo está cubierto por infraestructura fija (cámaras)
    // Retorna false si el nodo está desprotegido (aquí es donde queremos poner AEDs)
    return is_base_covered[node_id];
}