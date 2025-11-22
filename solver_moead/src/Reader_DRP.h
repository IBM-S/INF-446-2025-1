#pragma once
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <cmath>
#include <list>
#include <vector>
#include "DRP_ProblemInstance.h"

using namespace std;

class Reader
{
private:
    string filePath;
    ifstream input;

public:
    explicit Reader(string option);
    ~Reader();

    ProblemInstance *readInputFile();
    void readOutputs(vector<unsigned int> seeds, size_t beta, int gamma, int epsilon, bool corte);

private:
    void findDef(string def);
    ProblemInstance *createInstance();
    
    void readSet(ProblemInstance *problemInstance);
    void readScalarParams(ProblemInstance *problemInstance);
    void readOHCAs(ProblemInstance *problemInstance);
};
