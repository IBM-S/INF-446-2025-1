#pragma once
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <cmath>
#include <list>
#include <vector>
#include "ProblemInstance.h"

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

    void readTrucks(ProblemInstance *problemInstance);
    void readTrucksCapacity(ProblemInstance *problemInstance);
    void readTrucksDepots(ProblemInstance *problemInstance, string type);
    
    void readTimeslots(ProblemInstance *problemInstance);
        
    void readClients(ProblemInstance *problemInstance);
    void readDepots(ProblemInstance *problemInstance);
    void readAlternativeNames(ProblemInstance *problemInstance);
    void readDistances(ProblemInstance *problemInstance);
    void readDemands(ProblemInstance *problemInstance);
};
