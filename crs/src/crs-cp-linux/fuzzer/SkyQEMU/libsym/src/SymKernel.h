#ifdef __cplusplus
#include <cstddef>
#include <cstdint>
extern "C" {
#else
#include <stddef.h>
#include <stdint.h>
#endif

// path constraint
void sky_push_pc(SymExpr constraint, int taken, uintptr_t site_id);
// address constraint
void sky_push_ac(uint64_t addr, SymExpr addr_expr, uintptr_t site_id);
bool sky_check_sanitizer(SymExpr cond, uintptr_t site_id);

#ifdef __cplusplus
}
#endif
