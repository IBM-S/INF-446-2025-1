#cmake_minimum_required(VERSION 2.6)
project(solver_moead)

#set(CMAKE_BUILD_TYPE Release)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

if(CMAKE_COMPILER_IS_GNUCC OR CMAKE_COMPILER_IS_GNUCXX)
  # Update if necessary
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wno-long-long -pedantic")
endif()

#set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin")


# 1. Incluir el directorio src para que encuentre los headers (.h)
include_directories(src)

# 2. Buscar automáticamente todos los .cpp en src
# Esto reemplaza tu lista manual SOURCE_FILES
file(GLOB SOURCES "src/*.cpp")

# 3. Crear el ejecutable
add_executable(moead ${SOURCES})
