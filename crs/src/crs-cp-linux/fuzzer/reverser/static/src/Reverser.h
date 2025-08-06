#ifndef REVERSER_H
#define REVERSER_H

#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"

class Reverser : public llvm::PassInfoMixin<Reverser> {
public:
  llvm::PreservedAnalyses run(llvm::Module &M, llvm::ModuleAnalysisManager &MAM);
  static bool isRequired() { return true; }
};

#endif
