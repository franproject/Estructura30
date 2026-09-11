cmake_minimum_required(VERSION 3.16)
project(PITA LANGUAGES CXX)

enable_testing()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compila el sistema académico PITA con sus tres unidades de traducción:
# PITA.cpp (núcleo académico), payroll_engine.cpp (motor de nómina) y
# payroll_cycle.cpp (ciclo de liquidación formal).
add_executable(PITA
    PITA.cpp
    payroll_engine.cpp
    payroll_cycle.cpp
)

if (MSVC)
    target_compile_options(PITA PRIVATE /W4)
else()
    target_compile_options(PITA PRIVATE -Wall -Wextra -Wpedantic)
endif()

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

add_test(NAME payroll_engine_tests COMMAND payroll_engine_tests)
add_test(NAME payroll_cycle_tests COMMAND payroll_cycle_tests)
add_test(NAME payroll_exhaustive_tests COMMAND payroll_exhaustive_tests)
add_test(NAME payroll_parity_probe COMMAND payroll_parity_probe)

configure_file(pita_datos.txt ${CMAKE_CURRENT_BINARY_DIR}/pita_datos.txt COPYONLY)

