#include "Node_DRP.h"

// Constructor
Node::Node(int id) : id(id), x(0.0), y(0.0), flag(0), prob_ohca(0.0) {}


// Getters
int Node::getId() const { return id; }
double Node::getX() const { return x; }
double Node::getY() const { return y; }
int Node::getFlag() const { return flag; }
double Node::getProbOhca() const { return prob_ohca; }

// Setters
void Node::setId(int id) { this->id = id; }
void Node::setX(double x) { this->x = x; }
void Node::setY(double y) { this->y = y; }
void Node::setFlag(int flag) { this->flag = flag; }
void Node::setProbOhca(double prob) { this->prob_ohca = prob; }
