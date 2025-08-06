enum InstallType {
  IN_SYM,
  KEEP_SYM,
  ALWAYS,
};

typedef struct {
  const char* name;
  target_ulong pc;
  int argc;
  enum InstallType type;
  void *pre;
  void *post;
} SymFunc;

__attribute__ ((unused)) static SymFunc SYMFUNCS[] = {
    (SymFunc) {
      .name = "__kmalloc",
      .pc = 0,
      .argc = 1,
      .type = ALWAYS,
      .pre = &gen_helper_pre_kmalloc,
      .post = &gen_helper_post_kmalloc,
    },
    (SymFunc) {
      .name = "kfree",
      .pc = 0,
      .argc = 1,
      .type = ALWAYS,
      .pre = &gen_helper_pre_kfree,
      .post = NULL,
    },
    (SymFunc) {
      .name = "strcmp",
      .pc = 0,
      .argc = 2,
      .type = KEEP_SYM,
      .pre = &gen_helper_pre_strcmp,
      .post = NULL,
    },
};

extern SymFunc* symfuncs;
#define SYMFUNC_CNT (sizeof(SYMFUNCS) / sizeof(SymFunc))

static int symfunc_cmp(const void *a, const void* b) {
    target_ulong pc1 = ((SymFunc *) a)->pc;
    target_ulong pc2 = ((SymFunc *) b)->pc;
    return pc1 - pc2;
}
