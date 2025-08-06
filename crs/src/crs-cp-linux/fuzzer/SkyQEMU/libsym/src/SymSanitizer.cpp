#include <search.h>
#include <Runtime.h>
#include "RuntimeCommon.h"
#include "SymSanitizer.h"
#include "SymKernel.h"

void *mem_root = NULL;

int mem_cmp (const void *a, const void *b) {
    return ((MemChunk *) a)->addr - ((MemChunk *) b)->addr;
}

#define END_ADDR(m) m->addr + m->size.value
int mem_include (const void *a, const void *b) {
    MemChunk * m1 = (MemChunk *) a;
    MemChunk * m2 = (MemChunk *) b;
    if (m1->addr <= m2->addr && END_ADDR(m2) <= END_ADDR(m1)) return 0;
    return m1->addr - m2->addr;
}

MemChunk *sym_new_mem(uint64_t addr, uint64_t size, SymExpr size_expr) {
    MemChunk *ret = (MemChunk *) malloc(sizeof(MemChunk));
    ret->addr = addr;
    ret->size.value = size;
    ret->size.expr = size_expr;
    return ret;
}

void sym_add_mem(uint64_t addr, MemChunk* mem) {
    mem->addr = addr;
    pthread_mutex_lock(&mem_lock);
    tsearch(mem, &mem_root, mem_cmp);
    pthread_mutex_unlock(&mem_lock);
}

void print_mem(MemChunk *mem, FILE *file) {
    if(mem == NULL) return;
    fprintf(file, "[MemChunk] addr: %lx, size: %lx size_expr: %p\n",
            mem->addr, mem->size.value, mem->size.expr);
    if (mem->size.expr) {
        fprintf(file, "[MemChunk] size_expr: %s\n",
                _sym_expr_to_string(mem->size.expr));
    }
}

MemChunk* find_mem(uint64_t addr) {
    MemChunk tmp;
    tmp.addr = addr;
    pthread_mutex_lock(&mem_lock);
    void *ret = tfind(&tmp, &mem_root, mem_include);
    pthread_mutex_unlock(&mem_lock);
    if (ret) return *(MemChunk **)ret;
    return nullptr;
}

void sym_kfree(uint64_t addr, SymExpr addr_expr) {
    if(addr_expr != nullptr) {
        fprintf(stderr,  "TODO: sym_kfree %s\n", _sym_expr_to_string(addr_expr));
        return;
    }
    MemChunk tmp;
    tmp.addr = addr;
    pthread_mutex_lock(&mem_lock);
    tdelete(&tmp, &mem_root, mem_cmp);
    pthread_mutex_unlock(&mem_lock);
}

void sym_kasan(uint64_t addr, SymExpr addr_expr,
               uint64_t size, SymExpr size_expr, uintptr_t site_id) {
    if(addr_expr != NULL || size_expr != NULL) {
        MemChunk *mem = find_mem(addr);
        if(mem == NULL) return;
        TO_SYM64(mem->size.expr, mem->size.value);
        SymExpr mem_end = _sym_build_add(BUILD_SYM64(mem->addr), mem->size.expr);

        TO_SYM64(addr_expr, addr);
        TO_SYM64(size_expr, size);
        SymExpr end_expr = _sym_build_add(addr_expr, size_expr);

        _sym_check_kasan(
            _sym_build_unsigned_greater_than(end_expr, mem_end),
            site_id);
    }
    sky_push_ac(addr, addr_expr, site_id);
}
