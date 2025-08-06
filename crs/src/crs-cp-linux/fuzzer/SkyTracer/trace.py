import struct

SYSCALL = b"\x00"
INMEM   = b"\x01"
OUTMEM  = b"\x02"
SYSRET  = b"\x03"
SYS_ARGC = [ 3, 3, 3, 1, 2, 2, 2, 3, 3, 6, 3, 2, 1, 4, 4, 1, 3, 4, 4,
  3, 3, 2, 1, 5, 0, 5, 3, 3, 3, 3, 3, 3, 1, 2, 0, 2, 2, 1, 3, 0, 4, 3, 3, 3, 6,
  6, 3, 3, 2, 3, 2, 3, 3, 4, 5, 5, 5, 0, 0, 3, 1, 4, 2, 1, 3, 3, 4, 1, 2, 4, 5,
  3, 3, 2, 1, 1, 2, 2, 3, 2, 1, 1, 2, 2, 1, 2, 2, 1, 2, 3, 2, 2, 3, 3, 3, 1, 2,
  2, 2, 1, 1, 4, 0, 3, 0, 1, 1, 0, 0, 2, 0, 0, 0, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1,
  1, 1, 2, 2, 2, 4, 3, 2, 2, 2, 3, 1, 1, 2, 2, 2, 3, 2, 3, 2, 2, 3, 1, 1, 1, 2,
  2, 2, 1, 0, 0, 3, 2, 1, 6, 3, 1, 2, 1, 0, 1, 2, 5, 2, 2, 1, 4, 2, 2, 2, 3, 1,
  3, 2, 1, 1, 4, 1, 1, 1, 1, 1, 1, 0, 3, 5, 5, 5, 4, 4, 4, 3, 3, 3, 2, 2, 2, 2,
  1, 6, 3, 3, 1, 2, 1, 4, 3, 3, 1, 3, 1, 1, 1, 5, 3, 1, 0, 4, 4, 3, 4, 2, 1, 1,
  2, 2, 2, 4, 1, 4, 4, 3, 2, 1, 6, 3, 5, 4, 1, 5, 5, 2, 3, 4, 5, 4, 4, 5, 3, 2,
  0, 3, 2, 4, 4, 3, 4, 5, 3, 4, 3, 4, 5, 3, 4, 3, 3, 6, 5, 1, 2, 3, 6, 4, 4, 4,
  6, 4, 6, 3, 2, 1, 4, 4, 2, 4, 4, 2, 1, 3, 2, 1, 5, 5, 4, 5, 5, 2, 5, 4, 5, 5,
  2, 1, 4, 2, 3, 6, 6, 5, 3, 3, 4, 5, 3, 3, 2, 5, 3, 5, 1, 2, 3, 6, 6, 6, 4, 2,
  1, 5, 6, 4 ]
SYS_ARGC += [6] * 89  # 89 = 423 - 334 (reserved number 335 to 423)
SYS_ARGC += [4, 2, 6, 4, 3, 5, 2, 5, 3, 3, 2, 2, 3, 4, 3, 4, 5, 6, 5, 4, 3, 4,
             2, 1, 2, 5, 4, 4, 4, 3, 4, 6, 4, 4, 4, 4, 4, 3, 3]
BAR = "="*30 + "\n"

class Mem:
    def __init__(self, addr, data):
        self.addr = addr
        self.data = data
        self.size = len(data)

    def __str__(self):
        ret = "Addr: 0x%x, size: 0x%x\n"%(self.addr, self.size)
        for idx in range(self.size):
            if (idx % 0x10) == 0x0:
                ret += "%04x: "%idx
            ret += "%02x "%self.data[idx]
            if (idx % 0x10) == 0xf:
                ret+= "\n"
        if ret[-1] != "\n": ret += "\n"
        return ret

class Syscall:
    def __init__(self, sysnum, args):
        self.sysnum = sysnum
        self.args = args
        self.argc = len(args)
        self.ret_val = None
        self.in_mems = []
        self.out_mems = []
        self.cov = []

    def add_inmem(self, mem: Mem):
        self.in_mems.append(mem)

    def add_outmem(self, mem: Mem):
        self.out_mems.append(mem)

    def set_ret_val(self, val: int):
        self.ret_val = val

    def set_cov(self, cov):
        self.cov = set(cov)

    def str(self, funcs = None):
        ret  = BAR
        ret += f"syscall_{self.sysnum}("
        ret += ", ".join(map(lambda x: "0x%x"%x, self.args))
        ret += f") = {self.ret_val}\n"
        ret += "InMems:\n"
        for m in self.in_mems: ret += str(m)
        ret += "OutMems:\n"
        for m in self.out_mems: ret += str(m)
        ret += "Func Coverage:\n"
        if funcs:
            for cov in self.cov: ret += funcs[cov] + " "
        else:
            for cov in self.cov: ret += "%x "%cov
        ret += "\n"
        return ret

    def __str__(self): return self.str()

class Trace:
    def __init__(self, syscalls):
        self.syscalls = syscalls


    def str(self, funcs = None):
        ret = ""
        for s in self.syscalls: ret += s.str(funcs)
        return ret

    def __str__(self): return self.str()

class InvalidTraceError(Exception):
    pass

def read_trace(f, fmt, size):
    data = f.read(size)
    if len(data) != size: raise InvalidTraceError
    return struct.unpack(fmt, data)

def load_syscall (f):
    sysnum = read_trace(f, "<Q", 8)[0]
    if len(SYS_ARGC) > sysnum: argc = SYS_ARGC[sysnum]
    else: argc = 6
    args = read_trace(f, "<" + "Q"*argc, 8*argc)
    return Syscall(sysnum, args)

def load_mem (f):
    addr = read_trace(f, "<Q", 8)[0]
    size = read_trace(f, "<I", 4)[0]
    data = f.read(size)
    if len(data) != size: raise InvalidTraceError
    return Mem(addr, data)

def load_trace(trace_path):
    syscalls = []
    cur = None
    try:
        with open(trace_path, "rb") as f:
            while True:
                cmd = f.read(1)
                if cmd == SYSCALL:
                    cur = load_syscall(f)
                    syscalls.append(cur)
                elif cmd == INMEM:
                    mem = load_mem (f)
                    cur.add_inmem(mem)
                elif cmd == OUTMEM:
                    mem = load_mem (f)
                    cur.add_outmem(mem)
                elif cmd == SYSRET:
                    ret_val = read_trace(f, "<Q", 8)[0]
                    cur.set_ret_val(ret_val)
                    cov_cnt = read_trace(f, "<Q", 8)[0]
                    cov = read_trace(f, "<"+ "Q"*cov_cnt, 8*cov_cnt)
                    cur.set_cov(cov)
                elif cmd == b"": break
                else: raise InvalidTraceError
    except: return None
    return Trace(syscalls)
