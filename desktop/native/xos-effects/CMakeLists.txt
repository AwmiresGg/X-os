# XOS.Effects — compositor effects for the X-OS shell that have no Python/QML API:
# background blur behind a (non-rectangular) region via KWindowEffects (KWin blur protocol).
cmake_minimum_required(VERSION 3.20)
project(xos-effects LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 6.4 REQUIRED COMPONENTS Quick Qml)
find_package(KF6WindowSystem REQUIRED)

qt_add_qml_module(xoseffects
    URI XOS.Effects
    VERSION 1.0
    PLUGIN_TARGET xoseffects
    SOURCES blurbehind.h blurbehind.cpp
)
target_link_libraries(xoseffects PRIVATE Qt6::Quick Qt6::Qml KF6::WindowSystem)
