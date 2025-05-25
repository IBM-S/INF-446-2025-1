#ifndef DRP_PROBLEMINSTANCE_H
#define DRP_PROBLEMINSTANCE_H

#include <vector>
#include <string>
#include <map>
#include "Node_DRP.h"

class ProblemInstance {
public:
    ProblemInstance();
    ~ProblemInstance();

    std::vector<Node*> nodes;

    std::vector<int> candidateLocations; // I

    //int alpha; // Número de desfibriladores a ubicar
    //int beta;  // Número de desfibriladores disponibles por escenario

    double P, c1, c2;
    int R, N;
    std::string nombre_instancia;


    void addNode(Node* node);

    /* void setAlpha(int a);
    void setBeta(int b);
    int getAlpha();
    int getBeta(); */

    void setP(double p);
    double getP();
    void setR(int r);
    int getR();
    void setC1(double c1);
    double getC1();
    void setC2(double c2);
    double getC2();
    void setNombreInstancia(std::string nombre);
    std::string getNombreInstancia();

    std::vector<Node*>& getNodes();
    std::vector<int> getCandidateLocations();
    void printAll();
};

#endif
