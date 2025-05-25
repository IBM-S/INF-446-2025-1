#pragma once
#include <iostream>
#include <vector>
#include "Node.h"
#include "Truck.h"
#include "Timeslot.h"

using namespace std;

class ProblemInstance {
public:
    int ***distances;
    
    vector<Depot *> depots;
    vector<Client *> clients;
    vector<Truck *> trucks;
    vector<Timeslot *> timeslots;
    int maxRounds = 100;
    float hInicio = 8.0;
    float mInicio = 20.0;

public:
    explicit ProblemInstance();
    ~ProblemInstance();
    Node* getNode(int id);
    Node* getNodeByName(int name);
    int *** getDistances(void);

    int getNumberOfNodes(void);
    int getNumberOfDepots(void);
    int getNumberOfTrucks(void);
    int getMaxRounds(void);
    int getMinTime(void); //Inicio del intervalo de tiempo
    int getMaxTime(void); //Inicio del intervalo de tiempo
    
    int getHInicio(void);
    int getMInicio(void);
    
    int getSlotDuration(int slotIndex);

    void addDepot(Depot *depot);
    void addClient(Client *client);
    void addTimeslot(Timeslot *timeslot);
    
    void addTruck(Truck *truck);
    Truck* getTruck(int id);
    void setTrucksCapacities(int capacity);
        
    void setDistance(int row, int col, int distance);
    int getDistance(int initialNode, int finalNode);
    void showDistances(void);  

    void printAll(void);
    
    int computeTime(int from, int to);
    int computeTimeslot(int from, int to);
    int computeBestTimeToDend(int from, Truck *truck);

    vector <Depot *> getDepots(void);
    vector <Client *> getClients(void);
//     int computeExactTime(int from, int to, int start);
    void printTime(int segundos);
    void printHrsMns(int segundos);

    bool isADepot(int id);
    
};
