package trace

import (
	"encoding/binary"
	"os"
)

const (
	SYSCALL byte = 0
	INMEM   byte = 1
	OUTMEM  byte = 2
	SYSRET  byte = 3
)

func read32(f *os.File) uint32 {
	data := make([]byte, 4)
	n, err := f.Read(data)
	if n != 4 || err != nil {
		panic(err)
	}
	return binary.LittleEndian.Uint32(data)
}

func read64(f *os.File) uint64 {
	data := make([]byte, 8)
	n, err := f.Read(data)
	if n != 8 || err != nil {
		panic(err)
	}
	return binary.LittleEndian.Uint64(data)
}

func loadCov(f *os.File) Cov {
	cnt := int(read64(f))
	cov := make([]uint64, cnt)
	for i := 0; i < cnt; i++ {
		cov[i] = read64(f)
	}
	return Cov{cov}
}

func loadMem(f *os.File) Mem {
	addr := read64(f)
	size := read32(f)
	data := make([]byte, size)
	n, err := f.Read(data)
	if uint32(n) != size || err != nil {
		panic(err)
	}
	return Mem{addr, size, data}
}

func loadSyscall(f *os.File) Syscall {
	sysnum := read64(f)
	var argc int
	if sysnum < uint64(len(SYS_ARGC)) {
		argc = SYS_ARGC[sysnum]
	} else {
		argc = 6
	}
	args := make([]uint64, argc)
	for i := 0; i < argc; i++ {
		args[i] = read64(f)
	}
	return Syscall{sysnum: sysnum, args: args}
}

func Load(fname *string) *Trace {
	f, err := os.Open(*fname)
	if err != nil {
		panic(err)
	}

	var cur Syscall
	var syscalls []Syscall
	cmd := make([]byte, 1)

	for {
		n, _ := f.Read(cmd)
		if n != 1 {
			break
		}
		switch cmd[0] {
		case SYSCALL:
			cur = loadSyscall(f)
		case INMEM:
			mem := loadMem(f)
			cur.addInMem(mem)
		case OUTMEM:
			mem := loadMem(f)
			cur.addOutMem(mem)
		case SYSRET:
			retval := read64(f)
			cov := loadCov(f)
			cur.setRet(retval, cov)
			syscalls = append(syscalls, cur)
		default:
			panic("Invalid cmd")
		}
	}
	trace := Trace{syscalls}
	return &trace
}
