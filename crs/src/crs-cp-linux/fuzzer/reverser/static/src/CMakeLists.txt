set(PASS_MODULE ReverserPass)
add_library(${PASS_MODULE} MODULE
  Registry.cpp
  Reverser.cpp
)
llvm_map_components_to_libnames(llvm_libs bitwriter core ipo irreader instcombine instrumentation target linker analysis scalaropts support )
add_executable(macros Macros.cpp)
target_link_libraries(macros ${llvm_libs})
install(TARGETS ${PASS_MODULE} macros DESTINATION .)
