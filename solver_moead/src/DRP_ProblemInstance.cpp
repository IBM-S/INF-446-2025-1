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
