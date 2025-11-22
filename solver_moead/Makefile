CXX      = g++
CXXFLAGS = -std=c++1y -O3 -g -ggdb -fprofile-use -Isrc

#Directorios
SRCDIR = src
OBJDIR = obj
BINDIR = .

TARGET = MOEAD

INSTANCE    = ../datos/inst/150-11.dat
SEED        = 123
N_VARIABLES = 150
N_EVAL      = 1000
ARGS        = -inst $(INSTANCE) -seed $(SEED) -nvars $(N_VARIABLES) -neval $(N_EVAL)

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
