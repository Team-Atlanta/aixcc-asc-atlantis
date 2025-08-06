package trace

import (
	"fmt"
	"strings"
)

var BAR = strings.Repeat("=", 30)
var SYS_ARGC = []int{3, 3, 3, 1, 2, 2, 2, 3, 3, 6, 3, 2, 1, 4, 4, 1, 3, 4, 4,
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
	1, 5, 6, 4, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
	6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
	6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
	6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 4, 2, 6, 4, 3, 5, 2, 5, 3, 3, 2,
	2, 3, 4, 3, 4, 5, 6, 5, 4, 3, 4, 2, 1, 2, 5, 4, 4, 4, 3, 4, 6, 4, 4, 4, 4, 4,
	3, 3}

type Mem struct {
	addr uint64
	size uint32
	data []byte
}

type Cov struct {
	funcs []uint64
}

type Syscall struct {
	sysnum  uint64
	args    []uint64
	retval  uint64
	inMems  []Mem
	outMems []Mem
	cov     Cov
}

type Trace struct {
	syscalls []Syscall
}

/*
  Methods for Syscall
*/

func (syscall *Syscall) addInMem(m Mem) {
	syscall.inMems = append(syscall.inMems, m)
}

func (syscall *Syscall) addOutMem(m Mem) {
	syscall.outMems = append(syscall.outMems, m)
}

func (syscall *Syscall) setRet(retval uint64, cov Cov) {
	syscall.retval = retval
	syscall.cov = cov
}

/*
  String methods
*/

func strJoin[T any](arr []T, f func(T) string, sep string) string {
	var ret []string
	for _, item := range arr {
		ret = append(ret, f(item))
	}
	return strings.Join(ret, sep)
}

func (trace Trace) String() string {
	return strJoin(trace.syscalls, func(x Syscall) string { return x.String() }, "\n")
}

func (syscall Syscall) String() string {
	ret := BAR + "\n"
	ret += fmt.Sprintf("syscall_0x%x(", syscall.sysnum)
	ret += strJoin(syscall.args, func(x uint64) string { return fmt.Sprintf("0x%x", x) }, ", ")
	ret += fmt.Sprintf(") = 0x%x\n", syscall.retval)
	ret += "InMems:\n"
	for _, m := range syscall.inMems {
		ret += m.String()
	}
	ret += "OutMems:\n"
	for _, m := range syscall.outMems {
		ret += m.String()
	}
	ret += "Cov:\n"
	ret += syscall.cov.String()
	return ret
}

func (mem Mem) String() string {
	ret := fmt.Sprintf("Addr: 0x%x, size: 0x%x\n", mem.addr, mem.size)
	for i, x := range mem.data {
		if (i % 0x10) == 0x0 {
			ret += fmt.Sprintf("%04x: ", i)
		}
		ret += fmt.Sprintf("%02x ", x)
		if (i % 0x10) == 0xf {
			ret += "\n"
		}
	}
	if len(ret) > 0 && ret[len(ret)-1] != 0x0a {
		ret += "\n"
	}
	return ret
}

func (cov Cov) String() string {
	ret := ""
	for i, addr := range cov.funcs {
		ret += fmt.Sprintf("%x ", addr)
		if (i % 0x8) == 0x7 {
			ret += "\n"
		}
	}
	if len(ret) > 0 && ret[len(ret)-1] != 0x0a {
		ret += "\n"
	}
	return ret
}
