#ifndef SYMSAN_H
#define SYMSAN_H

typedef struct {
  uint64_t value;
  SymExpr expr;
} SymValue;

typedef struct {
  uint64_t addr;
  SymValue size;
} MemChunk;

#ifdef __cplusplus
#include <cstddef>
#include <cstdint>
extern "C" {
#else
#include <stddef.h>
#include <stdint.h>
#endif
MemChunk *sym_new_mem(uint64_t addr, uint64_t size, SymExpr size_expr);
void sym_add_mem(uint64_t addr, MemChunk* mem);

void sym_kfree(uint64_t addr, SymExpr addr_expr);
void sym_kasan(uint64_t addr, SymExpr addr_expr, uint64_t size, SymExpr size_expr, uintptr_t site_id);

#ifdef __cplusplus
}
#endif
#endif
