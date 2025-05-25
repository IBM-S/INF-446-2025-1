#include "Reader.h"
#include "algorithm"

Reader::Reader(string option): filePath(string(option)) {}

Reader::~Reader() { }

ProblemInstance *Reader::readInputFile() {
    bool debug=true;

    string filePath = this->filePath;
    input.open(filePath);

    if (!input.is_open()) {
        cerr << "Could not open the file: " << filePath << std::endl;
        exit(EXIT_FAILURE);
    }

    string line;
    //getline(input, line);
    if(debug) cout << "Reading: " << filePath << endl;

    //vector<string> data;
    auto *problemInstance = new ProblemInstance();

    this->findDef("D_start:=");
    this->readDepots(problemInstance);
    if(debug) cout << "End readDepots! " << endl;

    this->findDef("C:=");
    this->readClients(problemInstance);
    if(debug) cout << "End readClients! " << endl;

    this->findDef("D_in:=");
    this->readAlternativeNames(problemInstance);
    if(debug) cout << "readNames! " << endl;

    this->findDef("D_end:=");
    this->readAlternativeNames(problemInstance);
    if(debug) cout << "readNames! " << endl;

    this->findDef("K:=");
    this->readTrucks(problemInstance);
    if(debug) cout << "End readTrucks! " << endl;

    this->findDef("tmax:=");
    this->readTimeslots(problemInstance);
    if(debug) cout << "End readTimeslots! " << endl;
    
    this->findDef("time_:=");
    this->readDistances(problemInstance);
    if(debug) cout << "End readDistances! " << endl;

    this->findDef("dem:=");
    this->readDemands(problemInstance);
    if(debug) cout << "End readDemands! " << endl;
    
    this->findDef("cap:=");
    this->readTrucksCapacity(problemInstance);
    if(debug) cout << "End readTrucksCapacity! " << endl;
    
    this->findDef("ava_start:=");
    this->readTrucksDepots(problemInstance, "start");
    if(debug) cout << "End readTrucksDepots! " << endl;

    this->findDef("ava_end:=");
    this->readTrucksDepots(problemInstance, "end");
    if(debug) cout << "End readTrucksDepots! " << endl;

    this->findDef("com:=");
    this->readTrucksDepots(problemInstance, "in");
    if(debug) cout << "End readTrucksDepots! " << endl;
    
    input.close();
    if(debug) cout << "End Reading! " << endl;
    return problemInstance;
}

void Reader::findDef(string def) {
    string word;
    while (true) {
        input >> word;
        if (word.find(def) != std::string::npos) {
            break;
        }
    }
}


void Reader::readTrucks(ProblemInstance *problemInstance) {
    bool debug = false;
    if (debug) cout << "readTrucks " << endl;
    string read;
    int ntrucks(0);
    while (true) {
        input >> read;
        if (debug) cout << read << " ->";
        ntrucks++;
        if (read.find(';') != std::string::npos) {
            break;
        }
        
        auto *truck = new Truck(stoi(read) -1, 0); //Numerados desde cero en adelante
        problemInstance->addTruck(truck);
    }
    if (debug) cout << "trucks.size(): " << problemInstance->trucks.size() << endl;
    if (debug) getchar();
    return;
}

void Reader::readTrucksCapacity(ProblemInstance *problemInstance) {
    string capacity;
    input >> capacity;
    for (Truck *t: problemInstance->trucks){
        t->setCapacity(stoi(capacity));
        cout << "Truck: " << t->getId() << ", capacity: " << capacity << endl;
    }
    return;
}

void Reader::readTrucksDepots(ProblemInstance *problemInstance, string type){
    float debug = true;
    string depot, truck, flag;

    while (true) {
        input >> depot;
        if (depot.find(';') != std::string::npos) {
            break;
        }
        input >> truck >> flag;
        if (flag == "1"){
            cout << "Depot: " << depot << ", Truck: " << truck << endl;
            if (type == "start"){
                if (debug) cout << "type == start" << endl;
                problemInstance->getTruck(stoi(truck)-1)->addDstart((Depot *)problemInstance->getNodeByName(stoi(depot)));
            }
            if (type == "end"){
                if (debug) cout << "type == end" << endl;
                problemInstance->getTruck(stoi(truck)-1)->addDend((Depot *)problemInstance->getNodeByName(stoi(depot)));
            }
            if (type == "in"){
                if (debug) cout << "type == in" << endl;
                problemInstance->getTruck(stoi(truck)-1)->addDin((Depot *)problemInstance->getNodeByName(stoi(depot)));
            }
        }

    }

    if (debug) getchar();
}



void Reader::readDepots(ProblemInstance *problemInstance) {
    float debug = false;
    int id = 0;
    string name;

    while (true) {
        input >> name;
        if (name.find(';') != std::string::npos) {
            break;
        }
        cout << "Depot id: " << id << ", name: " << name << endl;

        auto *depot = new Depot(id, stoi(name));
        problemInstance->addDepot(depot);
        id++;
    }
    if (debug) cout << "depots.size(): " << problemInstance->depots.size() << endl;
    if (debug) getchar();
}


void Reader::readAlternativeNames(ProblemInstance *problemInstance) {
    float debug = false;
    int id = 0;
    string name;

    while (true) {
        input >> name;
        if (name.find(';') != std::string::npos) {
            break;
        }
        cout << "Depot id: " << id << ", name: " << name << endl;


        auto *depot = (Depot*)problemInstance->getNode(id);
        depot->addAlternativeName(stoi(name));
        id++;
    }
    if (debug) cout << "depots.size(): " << problemInstance->depots.size() << endl;
    if (debug) getchar();
}



void Reader::readClients(ProblemInstance *problemInstance) {
    float debug = false;
    int id = problemInstance->depots.size();
    string name;

    while (true) {
        input >> name;
        if (name.find(';') != std::string::npos) {
            break;
        }
        cout << "Client id: " << id << ", name: " << name << endl;

        auto *client = new Client(id, stoi(name),0);
        problemInstance->addClient(client);
        id++;
    }
    if (debug) cout << "clients.size(): " << problemInstance->clients.size() << endl;
    if (debug) getchar();
}


void Reader::readDemands(ProblemInstance *problemInstance) {
    float debug = false;
    if (debug) cout << "readDemands" << endl;
    string name;
    int demand;
    for(Depot *depot: problemInstance->getDepots()){
        input >> name >> demand;
        if (demand != 0) {
            cout << "ERROR: La produccion de la planta debiera ser cero" << endl;
            getchar();
        }
    }

    for(Client *client: problemInstance->getClients()){
        input >> name >> demand;
        ((Client*)problemInstance->getNodeByName(stoi(name)))->setDemand(demand);
        if(debug) ((Client*)problemInstance->getNodeByName(stoi(name)))->printAll();
    }
}

void Reader::readTimeslots(ProblemInstance *problemInstance) {
    float debug = false;
    string time;

    while (true) {
        input >> time;
        if (time.find(';') != std::string::npos) {
            break;
        }
        if (debug) cout << "id: 0, time: " << time << endl;
        auto *timeslot = new Timeslot(0, 0, stoi(time));
        problemInstance->timeslots.push_back(timeslot);
        timeslot->printAll();
    }
    if (debug) cout << "timeslots.size(): " << problemInstance->timeslots.size() << endl;
    if (debug) getchar();    
}



void Reader::readDistances(ProblemInstance *problemInstance) {
    bool debug = false;
    int totalNodes = problemInstance->getNumberOfNodes();

    problemInstance->distances = new int **[totalNodes];
    for (int i = 0; i < totalNodes; ++i){
        problemInstance->distances[i] = new int *[totalNodes];
        for (int j = 0; j < totalNodes; ++j){
            problemInstance->distances[i][j] = new int[1]; //TODO: checar que es la dimensión correcta, queremos solo un timeslot
        }
    }

    string from, to, distance;

    input >> from;
    while (true){
        if (from.find(';') != std::string::npos) {
                break;
        }
        input >> to >> distance;
        if (debug) cout << "from: " << from << ", to:" << to << ", distance: " << distance << endl;
        if (debug) cout << "from: " << problemInstance->getNodeByName(stoi(from))->getId() << endl;
        if (debug) cout << "to: " << problemInstance->getNodeByName(stoi(to))->getId() << endl;
        problemInstance->setDistance(problemInstance->getNodeByName(stoi(from))->getId(), problemInstance->getNodeByName(stoi(to))->getId(), stoi(distance));
        input >> from;

    }
}
