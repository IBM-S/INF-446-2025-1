#include "Timeslot.h"

Timeslot::Timeslot(int id, int start, int end): id(id), start(start), end(end) {}

Timeslot::~Timeslot() = default;

int Timeslot::getId() {
    return this->id; 
}

int Timeslot::getStart() {
    return this->start; 
}

int Timeslot::getEnd() {
    return this->end; 
}

void Timeslot::printAll(){
    cout << "Timeslot: " << this->getId() 
    << " [" << this->getStart() << ":" << this->getEnd() << "] " << endl;
}
