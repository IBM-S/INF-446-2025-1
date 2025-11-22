#include <iostream>
#include <fstream>
#include <string>
#include <cstdlib>  // Para system()

int main(int argc, char* argv[]) {
    std::string nombreArchivo;

    // Manejo de argumentos
    if (argc > 1) {
        if (argc == 3 && std::string(argv[1]) == "-caso") {
            nombreArchivo = argv[2];
        } else if (argc == 2) {
            nombreArchivo = argv[1];
        } else {
            std::cerr << "Uso: " << argv[0] << " [nombreArchivo | -caso nombreArchivo]" << std::endl;
            return 1;
        }

        std::ifstream archivo(nombreArchivo);
        if (!archivo) {
            std::cerr << "No se pudo abrir el archivo: " << nombreArchivo << std::endl;
            return 1;
        }

        std::string linea;
        while (std::getline(archivo, linea)) {
            if (!linea.empty()) {
                std::cout << "Ejecutando: " << linea << std::endl;
                int resultado = system(linea.c_str());
                if (resultado != 0) {
                    std::cerr << "Error al ejecutar: " << linea << std::endl;
                }
            }
        }

        archivo.close();
    } else {
        std::cerr << "Uso: " << argv[0] << " [nombreArchivo | -caso nombreArchivo]" << std::endl;
        return 1;
    }

    return 0;
}
