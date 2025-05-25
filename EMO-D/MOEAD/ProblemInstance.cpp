#include "ProblemInstance.h"
#include <algorithm>

ProblemInstance::ProblemInstance(){
}

ProblemInstance::~ProblemInstance(){
    //cout << "Deleting Problem Instance" << endl;

    for (int i = 0; i < this->getNumberOfNodes(); ++i){
        delete[] this->distances[i];
    }
    delete[] distances;

    for (Truck *truck: this->trucks){
        delete truck;
    }
    this->trucks.clear();
    this->trucks.shrink_to_fit();
    
    for (Depot *depot: this->depots){
        delete depot;
    }
    this->depots.clear();
    this->depots.shrink_to_fit();

    for (Client *client: this->clients){
        delete client;
    }
    this->clients.clear();
    this->clients.shrink_to_fit();
    
}

int ProblemInstance::getNumberOfNodes(){ //Considera todos los nodos, clientes y depositos.
    return (int)(this->clients.size() + this->depots.size()) ;
}


int ProblemInstance::getNumberOfDepots(){ //Considera todos los nodos, clientes y depositos.
    return (int)(this->depots.size()) ;
}

Node* ProblemInstance::getNode(int id){
    for (Depot *depot: this->depots){
        if (depot->getId() == id)
            return (Node*)depot;
    }
    
    for (Client *client: this->clients){
        if (client->getId() == id)
            return (Node*)client;
    }
    return nullptr;
}


Node* ProblemInstance::getNodeByName(int name){
    bool debug = false;
    if (debug) cout << "ProblemInstance::getNodeByName" << endl;
    for (Depot *depot: this->depots){
        if (depot->getName() == name)
            return (Node*)depot;
        for (int n: depot->getAlternativeNames())
            if (n == name)
                return (Node*)depot;
    }

    for (Client *client: this->clients){
        if (debug) cout << client->getName() << endl;
        if (client->getName() == name)
            return (Node*)client;
    }
    return nullptr;
}

vector <Depot *> ProblemInstance::getDepots(){
    return this->depots;
}
vector <Client *> ProblemInstance::getClients(){
    return this->clients;
}

int ProblemInstance::getMaxRounds(){
    return this->maxRounds;
}

int ProblemInstance::getMaxTime(){
    return this->timeslots.back()->getEnd();
}

int ProblemInstance::getMinTime(){
    return this->timeslots.at(0)->getStart();
}

int ProblemInstance::getHInicio(void){ //Tiempo en segundos
    return this->timeslots.at(0)->getStart()/60;
}

int ProblemInstance::getMInicio(void){ //Tiempo en segundos
    return this->timeslots.at(0)->getStart()%60;
}

int ProblemInstance::getSlotDuration(int slotIndex){
    return (this->timeslots.at(slotIndex)->getEnd() - this->timeslots.at(slotIndex)->getStart());
}

int ProblemInstance::getNumberOfTrucks(){
    return this->trucks.size();
}

void ProblemInstance::addDepot(Depot *depot){
    this->depots.push_back(depot);
}

void ProblemInstance::addClient(Client *client){
    this->clients.push_back(client); 
}

void ProblemInstance::addTruck(Truck *truck){
    this->trucks.push_back(truck); 
}

Truck* ProblemInstance::getTruck(int id){
    return this->trucks.at(id); 
}

int *** ProblemInstance::getDistances(void){
    return this->distances;
}


void ProblemInstance::setDistance(int row, int col, int distance) {
    cout << "row: " << row << ", col: " << col << ", distance: " << distance << endl;
    this->distances[row][col][0] = distance;
}

int ProblemInstance::getDistance(int initialNode, int finalNode) {
    //cout << endl << "From: " << initialNode << " To: " << finalNode << ": " << this->distances[initialNode][finalNode][timeslot] << endl;
    return this->distances[initialNode][finalNode][0];
}

void ProblemInstance::showDistances(void) {  
    for (Timeslot *t: this->timeslots){
        cout << t->getId() << endl;
        int count1 = 0;
        while (count1 < this->getNumberOfNodes()) {
            cout << count1;
            int count = 0;
            while (count < this->getNumberOfNodes()) {
                cout << "\t" << this->distances[count1][count][t->getId()];
                count++;
            }
            cout << endl;
            count1++;
        }
    }
}

void ProblemInstance::printTime(int segundos){
    cout << segundos;
    return;
}

void ProblemInstance::printHrsMns(int segundos){
    /**/

}


int ProblemInstance::computeTime(int from, int to){
    bool debug = false;
    int start = 0;
    if (debug) cout << "computeTime" << endl;
    if (debug) cout << "from: " << from  << ", to: " << to  << ", start: " << start << endl;
    for (Timeslot * ts: this->timeslots){
        if (debug) ts->printAll();
        if (start <= ts->getEnd()) { //TODO: Revisar si se considera el borde dentro o fuera del intervalo
            if (debug) cout << "Slot: " << ts->getId()  << " | " ;
            int time = this->getDistance(from, to);
            if (time < 0){
                cout << "time: " << time << endl;
                getchar();
            }
            if (debug) cout << "time: " << time << endl;
            //if (debug) getchar();
            return time;
        }
    }
    //Si no encuentra un timeslot.
    return -1;
}

int ProblemInstance::computeBestTimeToDend(int from, Truck *truck){
    bool debug = false;
    if (debug) cout << "computeBestTimeToDend" << endl;
    int time, bestTime = INT_MAX;
    for (Depot * depot: truck->getDends()){
        if (debug) cout << "from: " << from  << ", to: " << depot->getId() << endl;
        time = computeTime(from, depot->getId());
        if (time < bestTime)
            bestTime = time;
    }
    return bestTime; //El mejor de todos.
}


int ProblemInstance::computeTimeslot(int from, int to){
    bool debug = false;
    if (debug) cout << "computeTime" << endl;
    return 0; // No time-dependant
}

void ProblemInstance::printAll(){
    cout << endl;
    cout << "**Problem Instance**" << endl;
    
    for(Depot *depot: this->depots){
        depot->printAll();
    }

    for(Client *client: this->clients){
        client->printAll();
    }

    for(Truck *t: this->trucks){
        t->printAll();
    }

    cout << "Matrix[0][0][0]: " << this->distances[0][0][0] << endl; //matriz con diagonal de ceros
    return;
}

void ProblemInstance::setTrucksCapacities(int capacity){
    for(Truck *t: this->trucks){
        t->setCapacity(capacity);
    }
    return;
}

bool ProblemInstance::isADepot(int index){
    if(index < this->getNumberOfDepots())
        return true;
    else
        return false;


}
