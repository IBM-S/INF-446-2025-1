#pragma once
#include <iostream>
#include <vector>

using namespace std;

class Node {
private:
    int id; //index times matrix
    int name;

public:
    void setId(int id);
    int getId();    
    void setName(int name);
    int getName();

    Node *getNode(int id);
    
};

class Depot: public Node {
private:
    vector <int> names;
public:
    Depot(int id, int name);
    ~Depot();
    void addName(int name);
    void addAlternativeName(int name);
    vector <int> getAlternativeNames(void);
    void printAll();
};


class Client: public Node {
private:
        int demand;

public:
    Client(int id, int name, int demand);
    ~Client();
    
    void printAll();
    void setDemand(int demand);
    int getDemand();
};
