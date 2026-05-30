cmake_minimum_required(VERSION 3.10)
project(SampleCppProject LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(sample_lib INTERFACE)
target_include_directories(sample_lib INTERFACE include)
