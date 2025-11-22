#include "Reader_DRP.h"
#include "algorithm"

Reader::Reader(string option) : filePath(string(option)) {}

Reader::~Reader() {}

ProblemInstance *Reader::readInputFile()
{
    bool debug = false;

    string filePath = this->filePath;
    input.open(filePath);

    if (!input.is_open())
    {
        cerr << "Could not open the file: " << filePath << std::endl;
        exit(EXIT_FAILURE);
    }

    string line;
    // getline(input, line);
    if (debug)
        cout << "Reading: " << filePath << endl;

    // vector<string> data;
    auto *problemInstance = new ProblemInstance();

    problemInstance->nombre_instancia = filePath;

    this->findDef("N_total:=");
    this->readSet(problemInstance);
    if (debug)
        cout << "End readSet! " << endl;

    this->readScalarParams(problemInstance);

    this->findDef("prob_ohca:=");
    this->readOHCAs(problemInstance);
    if (debug)
        cout << "End readInfoOhca! " << endl;

    input.close();
    if (debug)
        cout << "End Reading! " << endl;
    return problemInstance;
}

void Reader::findDef(string def)
{
    string word;
    while (true)
    {
        input >> word;
        if (word.find(def) != std::string::npos)
        {
            // std::cout << "Leí la línea: " << def << std::endl;
            break;
        }
    }
}

void Reader::readSet(ProblemInstance *problemInstance)
{
    int N;
    input >> N;
    problemInstance->setN(N);

    // Leer punto y coma final
    std::string dummy;
    input >> dummy;

    for (int i = 0; i < problemInstance->N; ++i)
    {
        Node *node = new Node(i); // solo id, sin atributos
        problemInstance->addNode(node);
    }
}

void Reader::readScalarParams(ProblemInstance *problemInstance)
{
    this->findDef("P:=");
    input >> problemInstance->P;

    this->findDef("R:=");
    input >> problemInstance->R;

    this->findDef("c1:=");
    input >> problemInstance->c1;

    this->findDef("c2:=");
    input >> problemInstance->c2;
}

void Reader::readOHCAs(ProblemInstance *problemInstance)
{
    int id;
    double x, y, flag, prob;

    while (input >> id && input.peek() != ';')
    {
        input >> x >> y >> flag >> prob;
        // std::cout << "Leí la línea: " << x << " " << y << " " << flag << " " << prob << std::endl;

        std::vector<Node *> &nodes = problemInstance->getNodes();
        if (id >= 1 && id <= nodes.size())
        {
            Node *node = nodes[id - 1]; // id empieza en 1

            node->setX(x);
            node->setY(y);
            node->setFlag(flag);
            node->setProbOhca(prob);
        }
        else
        {
            std::cerr << "Error: id fuera de rango: " << id << std::endl;
        }
    }
    std::string dummy;
    input >> dummy;
}
