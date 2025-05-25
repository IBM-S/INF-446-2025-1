#pragma once
#include <iostream>
#include <climits>
#include "Node.h"

using namespace std;

class Truck
{
private:
    int id;
    int capacity;
    vector <Depot *> dstart;
    vector <Depot *> din;
    vector <Depot *> dend;

public:
    Truck(int id, int capacity);
    ~Truck();

    int getId() const;
    int getCapacity() const;
    void setCapacity(int capacity);
    
    void addDstart(Depot *);
    void addDin(Depot *);
    void addDend(Depot *);

    vector <Depot *> getDstarts(void);
    vector <Depot *> getDins(void);
    vector <Depot *> getDends(void);

    Depot * getRandomDstart(void);
    Depot * getRandomDin(void);
    Depot * getRandomDend(void);

    Depot * getBestDstart(Client *client, int ***distances);
    Depot * getBestDend(Client *client, int ***distances);
    Depot * getBestDin(Client *client1, Client *client2, int ***distances);

    void printAll();

    bool operator==(const Truck& truck) const{return this->getId() == truck.getId();}
    bool operator!=(const Truck& truck) const{ return !operator==(truck);}
    bool operator>(const Truck& truck) const{ return this->getCapacity() > truck.getCapacity();}
    bool operator<(const Truck& truck) const{ return !operator>(truck);}
};
