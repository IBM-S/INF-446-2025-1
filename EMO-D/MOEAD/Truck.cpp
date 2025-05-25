#include "Truck.h"

Truck::Truck(int id, int capacity): id(id), capacity(capacity) {}

Truck::~Truck() = default;

int Truck::getId() const{
    return this->id; 
}

int Truck::getCapacity() const{
    return this->capacity; 
}

void Truck::setCapacity(int capacity){
    this->capacity = capacity; 
}

void Truck::addDstart(Depot * depot){
    this->dstart.push_back(depot);
}

void Truck::addDin(Depot * depot){
    this->din.push_back(depot);
}

void Truck::addDend(Depot * depot){
    this->dend.push_back(depot);
}

vector <Depot *> Truck::getDstarts(void){
    return this->dstart;
}

vector <Depot *> Truck::getDins(void){
    return this->din;
}

vector <Depot *> Truck::getDends(void){
    return this->dend;
}

Depot * Truck::getRandomDstart(void){
    /**/
}

Depot * Truck::getRandomDin(void){
    /**/
}

Depot * Truck::getRandomDend(void){
    /**/
}


Depot *Truck::getBestDstart(Client *client, int ***distances){
    Depot * bestDepot;
    int minDistance = INT_MAX;
    for (Depot *depot: this->dstart){
        if (minDistance > distances[depot->getId()][client->getId()][0])
            minDistance = distances[depot->getId()][client->getId()][0];
            bestDepot = depot;
    }
    return bestDepot;
}


Depot *Truck::getBestDend(Client *client, int ***distances){
    Depot * bestDepot;
    int minDistance = INT_MAX;
    for (Depot *depot: this->dend){
        if (minDistance > distances[client->getId()][depot->getId()][0])
            minDistance = distances[client->getId()][depot->getId()][0];
            bestDepot = depot;
    }
    return bestDepot;
}

Depot *Truck::getBestDin(Client *client1, Client *client2, int ***distances){
    Depot * bestDepot;
    int minDistance = INT_MAX;
    for (Depot *depot: this->din){
        if (minDistance > distances[client1->getId()][depot->getId()][0] + distances[depot->getId()][client2->getId()][0])
            minDistance = distances[client1->getId()][depot->getId()][0] + distances[depot->getId()][client2->getId()][0];
            bestDepot = depot;
    }
    return bestDepot;
}

void Truck::printAll(){
    cout << "Truck: " << this->getId() 
    << " TC: " << this->getCapacity() << endl
    << " Dstart: " ;
    for (Depot * depot: this->dstart)
        cout << depot->getName() << " ";
    cout << endl;
    cout << " Din: " ;
    for (Depot * depot: this->din)
        cout << depot->getName() << " ";
    cout << endl;
    cout << " Dend: " ;
    for (Depot * depot: this->dend)
        cout << depot->getName() << " ";
    cout << endl;
}
