cmake_minimum_required(VERSION 3.5 FATAL_ERROR)
project(LightTrapSimulation)

find_package(Geant4 REQUIRED ui_all vis_all)
include(${Geant4_USE_FILE})

# Add the include directory so that header files in "include/" are found.
include_directories(${PROJECT_SOURCE_DIR}/include)

# Gather all source files from the "src/" directory.
file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.cc)
# (Optional) Gather header files for IDE indexing purposes.
file(GLOB headers ${PROJECT_SOURCE_DIR}/include/*.hh)

# Locate all macro files from the "mac/" directory.
file(GLOB MACRO_FILES ${PROJECT_SOURCE_DIR}/mac/*.mac)
# Copy macro files to the binary directory.
file(COPY ${MACRO_FILES} DESTINATION ${PROJECT_BINARY_DIR})

# If you have any data files (e.g., ".dat"), update the search path if needed.
file(GLOB DATA_FILES ${PROJECT_SOURCE_DIR}/input/*.dat)
file(COPY ${DATA_FILES} DESTINATION ${PROJECT_BINARY_DIR})

# Build the executable using the source and header files.
add_executable(sim_lighttrap ${sources} ${headers})
target_link_libraries(sim_lighttrap ${Geant4_LIBRARIES})

add_custom_target(LightTrapSimulation DEPENDS sim_lighttrap)
