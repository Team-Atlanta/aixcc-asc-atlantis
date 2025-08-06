#include "Reverser.h"
#include "llvm/Transforms/Scalar/GVN.h"
#include "llvm/Transforms/Utils/Mem2Reg.h"

using namespace llvm;

// This is the core interface for pass plugins. It guarantees that 'opt' will
// be able to recognize HelloWorld when added to the pass pipeline on the
// command line, i.e. via '-passes=hello-world'
extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo
llvmGetPassPluginInfo() {
    return {LLVM_PLUGIN_API_VERSION, "ReverserPass", LLVM_VERSION_STRING,
          [](PassBuilder &PB) {
              PB.registerPipelineParsingCallback([](StringRef Name, ModulePassManager &MPM,                     
                                                    ArrayRef<PassBuilder::PipelineElement>)
                  {                     
                      if (Name == "reverser") {                                           
                          MPM.addPass(createModuleToFunctionPassAdaptor(PromotePass()));
                          MPM.addPass(createModuleToFunctionPassAdaptor(GVNPass()));
                          MPM.addPass(Reverser());                                        
                          return true;                                                 
                      }                                                              
                      return false;                                                  
                  });                                                              
          }};
}
