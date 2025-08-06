#include "Reverser.h"

using namespace llvm;

PreservedAnalyses Reverser::run(Module &M, ModuleAnalysisManager &AM) {
    errs() << M.getName() << "\n";

    // Search for harness function
    // First check if function with name 'harness' exists
    // Then search for main function
    // If still no, search for function with byte array and size as input
    // If no, search for function with byte array as input
    // Else output a grammar for completely arbitrary blob (cannot represent in grammar rn?)
    
    return PreservedAnalyses::all();
}
