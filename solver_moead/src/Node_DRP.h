#ifndef NODE_H
#define NODE_H

class Node {

public:
    int id;
    double x;
    double y;
    int flag;         // 0 = libre (candidato), 1 = ocupado (con desfibrilador)
    double prob_ohca;
    // Constructor
    Node(int id);  // constructor minimalista

    // Getters
    int getId() const;
    double getX() const;
    double getY() const;
    int getFlag() const;
    double getProbOhca() const;

    // Setters
    void setId(int id);
    void setX(double x);
    void setY(double y);
    void setFlag(int flag);
    void setProbOhca(double prob);
};

#endif
