#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/raw_os_ostream.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include <utility>
#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>

using namespace llvm;
using std::pair;
using std::vector;
using std::string;
using json = nlohmann::json;

json getCaseValuesAndLines(SwitchInst *SWI) {
    json ret = json::array();
    for (auto casehandle : SWI->cases()) {
        ConstantInt *C = casehandle.getCaseValue();
        BasicBlock *BB = casehandle.getCaseSuccessor();
        unsigned val = C->getValue().getZExtValue();
        unsigned line;
        bool foundLine = false;
        for (auto &I : *BB) {
            if (I.hasMetadata()) {
                SmallVector<pair<unsigned, MDNode *>> smallvec{};
                // Get vec of all metadata for the instruction
                I.getAllMetadata(smallvec);
                for (auto &mdpair : smallvec) {
                    MDNode *metadata = mdpair.second;
                    // Dynamically cast to DILocation for file line information
                    if (auto *dbgLoc = dyn_cast<DILocation>(metadata)) {
                        line = dbgLoc->getLine();
                        foundLine = true;
                        break;
                    }
                }
            }
            if (foundLine) {
                break;
            }
        }
        if (!foundLine) {
            continue;
        }
        ret.push_back({{"line", line}, {"value", val}});
    }
    return ret;
}

int main(int argc, char** argv)
{
    if (argc < 4) {
        errs() << "Usage: ./a.out TEST_HARNESS LINES_FILE OUTPUT_FILE\n";
        exit(1);
    }


    std::string irpath{argv[1]};
    std::string locationspath{argv[2]};
    std::string outputpath{argv[3]};
    
    std::ifstream locationsFile(locationspath);
    if (!locationsFile.is_open()) {
        std::cerr << "Error: Unable to open lines file" << std::endl;
        return 1;
    }

    std::string line;
    vector<unsigned> lines;

    while (std::getline(locationsFile, line)) {
        unsigned linum;
        try {
            linum = std::stoi(line);
        }
        catch(...) {
            continue;
        }
        lines.push_back(linum);
    }

    // Close the locations file
    locationsFile.close();

    LLVMContext Context;
    SMDiagnostic Err;
    std::unique_ptr<Module> Mod = parseIRFile(argv[1], Err, Context);

    if (!Mod) {
        Err.print(argv[0], errs());
        return 1;
    }

    Function *harness = nullptr;
    for (Function &F : *Mod) {
        if (!F.isDeclaration()) {
            if (F.getName().equals("harness")) {
                harness = &F;
            }
        }
    }
    if (harness == nullptr) {
        return 1;
    }
    json output = json::array();
    for (BasicBlock &BB : *harness) {
        for (Instruction &instruction : BB) {
            if (instruction.hasMetadata()) {
                SmallVector<pair<unsigned, MDNode *>> smallvec{};
                // Get vec of all metadata for the instruction
                instruction.getAllMetadata(smallvec);
                for (auto &mdpair : smallvec) {
                    MDNode *metadata = mdpair.second;
                    // Dynamically cast to DILocation for file line information
                    if (auto *dbgLoc = dyn_cast<DILocation>(metadata)) {
                        unsigned line = dbgLoc->getLine();
                        for (auto arg_line : lines) {
                            if (arg_line == line) {
                                if (auto SWI = dyn_cast<SwitchInst>(&instruction)) {
                                    json cvl = getCaseValuesAndLines(SWI);
                                    output.insert(output.end(), cvl.begin(), cvl.end());
                                }
                                // outs() << instruction << "\n";
                            }
                        }
                    }
                }
            }
        }
    }
    std::ofstream outfile;
    outfile.open(outputpath);
    outfile << output << std::endl;
    outfile.close();
}
