cmake_minimum_required(VERSION 3.16)
project(PITA LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compile the complete academic system as one self-contained source file.
add_executable(PITA
    PITA.cpp
    payroll_engine.cpp
    payroll_cycle.cpp
)

add_executable(payroll_engine_tests
    payroll_engine.cpp
    payroll_engine_tests.cpp
)

add_executable(payroll_cycle_tests
    payroll_engine.cpp
    payroll_cycle.cpp
    payroll_cycle_tests.cpp
)

add_executable(payroll_parity_probe
    payroll_engine.cpp
    payroll_parity_probe.cpp
)

add_executable(payroll_exhaustive_tests
    payroll_engine.cpp
    payroll_cycle.cpp
    payroll_exhaustive_tests.cpp
)

