cmake_minimum_required(VERSION 3.16)
project(PITA LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compile the complete academic system as one self-contained source file.
add_executable(PITA
    PITA.cpp
)

