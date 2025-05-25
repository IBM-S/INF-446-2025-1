#pragma once
#include <iostream>

using namespace std;

class Timeslot
{
private:
    int id;
    int start;
    int end;

public:
    Timeslot(int id, int start, int end);
    ~Timeslot();

    int getId();
    int getStart();
    int getEnd();

    void printAll();

};
