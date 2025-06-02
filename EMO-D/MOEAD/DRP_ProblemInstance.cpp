#include "DRP_ProblemInstance.h"
#include <iostream>
#include <cmath>

// Constructor
ProblemInstance::ProblemInstance() {
    P = 0;
    R = 0;
    c1 = 0;
    c2 = 0;
    /* alpha = 0;
    beta = 0; */
}

// Destructor
ProblemInstance::~ProblemInstance() {
    for (Node* node : nodes) {
        delete node;
    }
    nodes.clear();
}

// Añadir un nodo
void ProblemInstance::addNode(Node* node) {
    for (Node* existing : nodes) {
        if (existing->getId() == node->getId()) return;
    }
    nodes.push_back(node);
    if (node->getFlag() == 0) {
        candidateLocations.push_back(node->getId());
    }
}

// Getters de listas
std::vector<int> ProblemInstance::getCandidateLocations() {
    return candidateLocations;
}

std::vector<Node*>& ProblemInstance::getNodes() {
    return nodes;
}


// Setters y Getters
/* void ProblemInstance::setAlpha(int a) { alpha = a; }
void ProblemInstance::setBeta(int b) { beta = b; }
int ProblemInstance::getAlpha() { return alpha; }
int ProblemInstance::getBeta() { return beta; } */
// Parámetros
void ProblemInstance::setN(int n) { N = n;}

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
void ProblemInstance::printAll() {
    std::cout << "Instancia: " << nombre_instancia << "\n";
    std::cout << "Parámetros: P=" << P << ", R=" << R << ", c1=" << c1 << ", c2=" << c2 << "\n";
    //std::cout << "Alpha=" << alpha << ", Beta=" << beta << "\n";

    std::cout << "\nNodos:\n";
    for (auto* node : nodes) {
        std::cout << "ID: " << node->getId()
                  << ", Coord: (" << node->getX() << ", " << node->getY() << ")"
                  << ", Flag: " << node->getFlag()
                  << ", OHCA Prob: " << node->getProbOhca() << "\n";
    }

}
