#include <Runtime.h>
#include "RuntimeCommon.h"
#include "SymKernel.h"

void sky_push_pc(SymExpr constraint, int taken, uintptr_t site_id) {
    if(constraint == NULL) return;
    _sym_push_constraint(constraint, taken, site_id);
}

void sky_push_ac(uint64_t addr, SymExpr addr_expr, uintptr_t site_id) {
    if(addr_expr == NULL) return;
    _sym_push_constraint(_sym_build_equal(BUILD_SYM64(addr), addr_expr), true, site_id);
}
