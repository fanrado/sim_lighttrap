cmake_minimum_required(VERSION 3.5 FATAL_ERROR)
project(LightTrapSimulation)

# ── Geant4 discovery (portable) ──────────────────────────────────────────────
# Do NOT hardcode a machine-specific install path. Let the build find Geant4 via
# the standard mechanisms, in priority order:
#   1. -DGeant4_DIR=/path/to/lib/cmake/Geant4      (cmake command line)
#   2. -DCMAKE_PREFIX_PATH=/path/to/geant4/prefix  (cmake command line)
#   3. GEANT4_CMAKE_DIR environment variable pointing at .../lib/cmake/Geant4
#      (e.g. `spack load geant4` exports this, or set it in your shell rc)
# Anything provided is appended as a hint before find_package so cmake can use it.
if(DEFINED ENV{GEANT4_CMAKE_DIR})
  list(APPEND CMAKE_PREFIX_PATH "$ENV{GEANT4_CMAKE_DIR}")
endif()

find_package(Geant4 REQUIRED ui_all vis_all)
include(${Geant4_USE_FILE})

# ── yaml-cpp (YAML configuration support) ────────────────────────────────────
# Try a system installation first; fall back to fetching from source.
find_package(yaml-cpp QUIET)
if (NOT yaml-cpp_FOUND)
  include(FetchContent)
  FetchContent_Declare(
    yaml-cpp
    GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
    GIT_TAG        0.8.0
  )
  set(YAML_CPP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
  set(YAML_CPP_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(yaml-cpp)
endif()

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

# Copy data files and the YAML configuration to the build directory.
file(GLOB DATA_FILES ${PROJECT_SOURCE_DIR}/input/*.dat)
file(COPY ${DATA_FILES} DESTINATION ${PROJECT_BINARY_DIR})
file(COPY ${PROJECT_SOURCE_DIR}/sim_config.yaml DESTINATION ${PROJECT_BINARY_DIR})

# Build the executable.
add_executable(sim_lighttrap ${sources} ${headers})
target_link_libraries(sim_lighttrap ${Geant4_LIBRARIES} yaml-cpp::yaml-cpp)

add_custom_target(LightTrapSimulation DEPENDS sim_lighttrap)

