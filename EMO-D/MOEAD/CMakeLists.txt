#cmake_minimum_required(VERSION 2.6)
project(moead)

#set(CMAKE_BUILD_TYPE Release)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

if(CMAKE_COMPILER_IS_GNUCC OR CMAKE_COMPILER_IS_GNUCXX)
  # Update if necessary
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wno-long-long -pedantic")
endif()

#set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin")

set(SOURCE_FILES 
		 ALG_EMO_MAIN
		 ALG_EMO_MOEAD_DE
		 ALG_EMO_MOEAD
		 GlobalObject
		 GlobalVariable
		 IndividualBase
		 SubProblemBase
		 TestInstance
		 UtilityToolBox
		 ProblemInstance
		 Reader
		 Truck
		 Timeslot
		 Node
		 DRP_ProblemInstance
		 Node_DRP
		 Reader_DRP
        )

add_executable(moead ${SOURCE_FILES})
