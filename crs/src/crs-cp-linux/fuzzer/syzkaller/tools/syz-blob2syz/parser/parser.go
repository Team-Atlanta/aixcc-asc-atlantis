package parser

import (
	"fmt"

	"github.com/google/syzkaller/pkg/log"
	"github.com/google/syzkaller/prog"
)

func ParseDatablob(target *prog.Target, blob []byte, syzMap map[uint64]string, typ string) (p *prog.Prog, err error) {
	ctx := &context{
		target: target,
		syzMap: syzMap,
		blob:   blob,
	}
	log.Logf(4, "Size: %d, %v", len(blob), blob)
	if typ == "type2" {
		return ctx.parseDatablobType2()
	} else if typ == "type1" {
		return ctx.parseDatablobType1()
	} else {
		// try type1 first, and if it fails, try type2
		if p, err := ctx.parseDatablobType2(); err == nil {
			return p, nil
		} else {
			return ctx.parseDatablobType1()
		}
	}
}

func (ctx *context) parseDatablobType2() (p *prog.Prog, err error) {
	ctx.blob0 = append([]byte{}, ctx.blob...)
	ctx.builder = prog.MakeProgGen(ctx.target)
	defer func() {
		ctx.blob = ctx.blob0
		// XXX Using recover is so ugly
		if e := recover(); e != nil {
			if ctx.exhausted {
				p, err = ctx.builder.Finalize()
				if err != nil {
					p, err = nil, fmt.Errorf("Failed to parse type 1: %v", e)
					return
				}
				if len(p.Calls) == 0 {
					err = fmt.Errorf("Exhausted before making a single call")
				}
			} else {
				p, err = nil, fmt.Errorf("Failed to parse type 1: %v", e)
			}
		}
	}()
	count := ctx.parseInt(4)
	ctx.count = count
	ctx.parseCommand = true
	return ctx.__parseDatablob()
}

func (ctx *context) parseDatablobType1() (p *prog.Prog, err error) {
	ctx.blob0 = append([]byte{}, ctx.blob...)
	ctx.builder = prog.MakeProgGen(ctx.target)
	defer func() {
		ctx.blob = ctx.blob0
		// XXX Using recover is so ugly
		if e := recover(); e != nil {
			if ctx.exhausted {
				p, err = ctx.builder.Finalize()
				if err != nil {
					p, err = nil, fmt.Errorf("Failed to parse type 2: %v", e)
					return
				}
				if len(p.Calls) == 0 {
					err = fmt.Errorf("Exhausted before making a single call")
				}
			} else {
				p, err = nil, fmt.Errorf("Failed to parse type 2: %v", e)
			}
		}
	}()
	ctx.count = 1
	ctx.parseCommand = false
	return ctx.__parseDatablob()
}

func (ctx *context) __parseDatablob() (p *prog.Prog, err error) {
	for i := 0; i < int(ctx.count); i++ {
		l := 10
		if len(ctx.blob) < l {
			l = len(ctx.blob)
		}
		log.Logf(4, "%v", ctx.blob[:l])
		ctx.reinit()
		var cmd uint64
		if ctx.parseCommand {
			log.Logf(1, "Parsing %d-th command", i)
			cmd = ctx.__parseInt(4, false)
		} else {
			cmd = 0
		}
		log.Logf(1, "Command: %v", cmd)
		name, err := lookupMap(ctx.syzMap, cmd)
		if err != nil {
			return nil, err
		}
		scall, err := FindSyscall(name, ctx.target)
		if err != nil {
			return nil, err
		}
		call := prog.MakeCall(scall, nil)
		call.Args = ctx.genArgs(call)
		ctx.builder.Append(call)
		log.Logf(1, "Consumed: %d", ctx.consumed)
	}
	return ctx.builder.Finalize()
}

func ParseFallback(target *prog.Target, blob []byte, syzMap map[uint64]string, typ string) (p *prog.Prog, err error) {
	ctx := &context{
		builder: prog.MakeProgGen(target),
		target:  target,
		syzMap:  syzMap,
		blob:    blob,
	}
	const (
		dummyArgName  = "data"
		dummyArgDepth = 2
	)
	ctx.__recordLength(dummyArgName, uint64(len(blob)), dummyArgDepth)
	var name string
	if typ == "type1" {
		name = "syz_harness_type1$dummy"
	} else {
		name = "syz_harness_type2$dummy"
	}
	scall, err := FindSyscall(name, target)
	if err != nil {
		return nil, err
	}
	call := prog.MakeCall(scall, nil)
	call.Args = ctx.genArgs(call)
	ctx.builder.Append(call)
	return ctx.builder.Finalize()
}

func FindSyscall(name string, target *prog.Target) (*prog.Syscall, error) {
	if scall, ok := target.SyscallMap[name]; ok {
		return scall, nil
	} else {
		return nil, fmt.Errorf("Cannot find a syscall: %v", name)
	}
}

func lookupMap(syzMap map[uint64]string, cmd uint64) (string, error) {
	if callName, ok := syzMap[cmd]; ok {
		return callName, nil
	} else {
		return "", fmt.Errorf("Cannot find the callname for the command %v", cmd)
	}
}
