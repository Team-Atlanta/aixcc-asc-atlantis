//
// Created by yu on 6/19/21.
//

#ifndef INC_2021_TEMPLATE_TASK_H
#define INC_2021_TEMPLATE_TASK_H

#include "../ToolLib/basic.h"
#include "../ToolLib/json.hpp"
#include "checker.h"

namespace sd {
class task {
 public:
  explicit task(nlohmann::json j);

  task(const std::string &entryFunction, sd::checker_result *cr);

 public:
  uint64_t hash{};
  std::string task_str;
  std::string bitcode;
  std::string entry_function;
  std::string work_dir;
  std::string knowledge_file;
  std::string name_script;
  std::string handler_script;
  std::string kernel_src;
  checker_result *cr;

  nlohmann::json *to_json();

  std::string print();

  void from_json(nlohmann::json j);

  void compute_hash();

  void update_checker_inst(llvm::Module *m);
};
}  // namespace sd

#endif  // INC_2021_TEMPLATE_TASK_H
