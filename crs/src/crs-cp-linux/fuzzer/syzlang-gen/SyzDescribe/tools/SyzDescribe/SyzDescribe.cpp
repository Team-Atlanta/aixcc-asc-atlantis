//
// Created by yhao on 3/3/21.
//

#include "../../lib/ManagerLib/Manager.h"
#include "../../lib/ToolLib/basic.h"
#include "../../lib/ToolLib/log.h"

llvm::cl::opt<std::string> config(
    "config", llvm::cl::desc("The configuration json file."),
    llvm::cl::value_desc("file name"), llvm::cl::init("./config.json"));

llvm::cl::opt<std::string> name_script(
    "name-script", llvm::cl::desc("The script to run to infer driver name with LLM."),
    llvm::cl::value_desc("file name"), llvm::cl::init("get_driver_name.py"));

llvm::cl::opt<std::string> handler_script(
    "handler-script", llvm::cl::desc("The script to run to infer handler with LLM."),
    llvm::cl::value_desc("file name"), llvm::cl::init("get_driver_handler.py"));

llvm::cl::opt<std::string> kernel_src(
    "kernel-src", llvm::cl::desc("Kernel source base"),
    llvm::cl::value_desc("directory path"), llvm::cl::Required);


int main(int argc, char **argv) {
  llvm::cl::ParseCommandLineOptions(argc, argv, "");
  start_log(argv);

  auto manager = new sd::Manager();
  manager->setup(config, name_script, handler_script, kernel_src);
  manager->analysis();

  return 0;
}
