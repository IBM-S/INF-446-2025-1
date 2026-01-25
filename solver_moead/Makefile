CXX      = g++
CXXFLAGS = -std=c++1y -O3 -g -ggdb -fprofile-use -Isrc

#Directorios
SRCDIR = src
OBJDIR = obj
BINDIR = .

TARGET = MOEAD

INSTANCE    = ../datos/inst/DRP.dat
TYPE        = drp
VARIANT     = relocation
alg         = MOEAD
pop 	    = 100
neighbors   = 20
SEED        = 1
N_EVAL      = 1000
ARGS        = -inst $(INSTANCE) -seed $(SEED) -neval $(N_EVAL) -type $(TYPE) -variant $(VARIANT) -alg $(alg) -pop $(pop) -neighbors $(neighbors)

SOURCES := $(wildcard $(SRCDIR)/*.cpp)
OBJECTS := $(patsubst $(SRCDIR)/%.cpp, $(OBJDIR)/%.o, $(SOURCES))

all: create_dirs $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) -o $(TARGET) $(OBJECTS) $(CXXFLAGS)

$(OBJDIR)/%.o: $(SRCDIR)/%.cpp
	@mkdir -p $(OBJDIR)
	$(CXX) -c $(CXXFLAGS) $< -o $@

create_dirs:
	@mkdir -p $(OBJDIR)

clean:
	rm -f $(OBJDIR)/*.o
	rm -f $(TARGET) core


exe: $(TARGET)
	./$(TARGET) ${ARGS}

#exe:
#	./MOEAD ${ARGS}
