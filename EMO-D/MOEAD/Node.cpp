#include "Node.h"

void Node::setId(int id) {
    this->id = id; 
}

int Node::getId() {
    return this->id; 
}

void Node::setName(int name) {
    this->name = name; 
}

int Node::getName() {
    return this->name; 
}

Depot::Depot(int id, int name){
    this->setId(id);
    this->setName(name);
}

Depot::~Depot() = default;

void Depot::printAll() {
    cout << "Depot:  " << this->getId() <<
    "\tN: " << this->getName() << endl;
    return;
}

void Depot::addAlternativeName(int name){
    this->names.push_back(name);
}

vector <int> Depot::getAlternativeNames(void){
    return this->names;
}

Client::Client(int id, int name, int demand){
    this->setId(id);
    this->setName(name);
    this->setDemand(demand);
}

Client::~Client() = default;

void Client::printAll() {
    cout << "Client:  " << this->getId() <<
    "\tN: " << this->getName() <<
    "\tD: " << this->getDemand() << endl;
    return;
}

void Client::setDemand(int demand) {
    this->demand = demand;
}

int Client::getDemand() {
    return this->demand;
}
