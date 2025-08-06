package trace

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"hash/fnv"
	"math"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/google/syzkaller/prog"
	"github.com/google/syzkaller/tools/syz-reverser/syzlang"
)

const MaxErrNo = 4095

var SyzlangMap = make(map[uint64][]*prog.Syscall) //syscall number -> Syzlang syscalls

// No syscall to generate these resources in /sys/linux/
var whiteResources = map[string]bool{
	"time_sec":  true,
	"time_nsec": true,
	"time_usec": true,
}

func InitSyzlangMap(target *prog.Target) {
	for _, syscall := range target.Syscalls {
		num := syscall.NR
		SyzlangMap[num] = append(SyzlangMap[num], syscall)
	}
}

// TODO: Embed in MatchCtx
type CaptureSource struct {
	InTraceIdx int
	Syscall    *prog.Syscall
	ArgIdx     int
	InArgPath  uint64
	Type       prog.Type
}

type Match struct {
	SysNum uint64
	Args   []bool
}

// TODO: Memo scope for each field
type MatchCtx struct {
	inTraceIdx  int
	syscall     *Syscall
	progSyscall *prog.Syscall
	fixedArgs   []bool
	argIdx      int
	inArgPath   uint64
	isStrict    bool
	dir         *prog.Dir
	resources   map[uint64]map[string]map[string]bool
	captures    map[CaptureSource][]byte
	depth       int
}

func (ctx *MatchCtx) addPath(edge uint64) {
	uint64Size := 8
	buf := make([]byte, uint64Size*2)
	binary.LittleEndian.PutUint64(buf[uint64Size*0:], ctx.inArgPath)
	binary.LittleEndian.PutUint64(buf[uint64Size*1:], edge)
	h := fnv.New64a()
	h.Write(buf)
	ctx.inArgPath = h.Sum64()
}

func (ctx *MatchCtx) capture(t prog.Type, mem []byte) {
	ctx.log("Capturing %+v (len: %d) ...", mem, len(mem))
	// fmt.Scanln()
	src := CaptureSource{
		InTraceIdx: ctx.inTraceIdx,
		Syscall:    ctx.progSyscall,
		ArgIdx:     ctx.argIdx,
		InArgPath:  ctx.inArgPath,
		Type:       t,
	}
	ctx.captures[src] = mem
}

// TODO: Use log or syzkaller log
func (ctx *MatchCtx) log(format string, args ...interface{}) {
	indent := strings.Repeat("\t", ctx.depth)
	format = indent + format + "\n"
	fmt.Printf(format, args...)
}

func (trace0 Trace) MatchWith(trace1 *Trace) ([][]*prog.Syscall, map[CaptureSource][]byte) {
	matches := []*Match{}
	var maxIters int
	if len(trace0.syscalls) < len(trace1.syscalls) {
		maxIters = len(trace0.syscalls)
	} else {
		maxIters = len(trace1.syscalls)
	}
	for i := 0; i < maxIters; i++ {
		syscall0, syscall1 := trace0.syscalls[i], trace1.syscalls[i]
		if syscall0.sysnum != syscall1.sysnum {
			break
		}
		var match *Match
		syscalls, ok := SyzlangMap[syscall0.sysnum]
		if !ok {
			break
		}
		var syscall *prog.Syscall
		for _, s := range syscalls {
			if s.Name != s.CallName || strings.HasPrefix(s.CallName, "syz_") {
				continue
			}
			syscall = s
			fmt.Println(syscall.CallName)
			break
		}
		match = &Match{SysNum: syscall0.sysnum}
		// Comparing syscall.Args might be just enough to work thanks to KASLR.
		for i := range syscall0.args {
			fmt.Printf("%x <-> %x\n", syscall0.args[i], syscall1.args[i])
			matched := false
			if syscall == nil {
				matched = syscall0.args[i] == syscall1.args[i]
			} else {
				if !(i < len(syscall.Args)) {
					continue
				}
				arg := syscall.Args[i]
				fmt.Printf("[%d] %T\n", i, arg.Type)
				switch typ := arg.Type.(type) {
				case *prog.PtrType:
					if typ.ElemDir == prog.DirIn || typ.ElemDir == prog.DirInOut {
						mem0 := syscall0.readMem(typ.ElemDir, syscall0.args[i])
						mem1 := syscall1.readMem(typ.ElemDir, syscall1.args[i])
						if mem0 != nil && mem1 != nil {
							matched = bytes.Equal(mem0, mem1)
						}
					}
				default:
					matched = syscall0.args[i] == syscall1.args[i]
				}
			}
			match.Args = append(match.Args, matched)
		}
		fmt.Printf("%+v\n", match.Args)
		matches = append(matches, match)
	}
	return trace0.Match(matches)
}

// FIXME: Handle field.Varlen()
// TODO: Introduce log level
func (trace Trace) Match(matches []*Match) ([][]*prog.Syscall, map[CaptureSource][]byte) {
	// Init with stdin, stdout and stderr
	resources := map[uint64]map[string]map[string]bool{
		0: {
			"fd_tty": {
				"fd":     true,
				"fd_tty": true,
			},
		},
		1: {
			"fd_tty": {
				"fd":     true,
				"fd_tty": true,
			},
		},
		2: {
			"fd_tty": {
				"fd":     true,
				"fd_tty": true,
			},
		},
	}
	ctx := MatchCtx{resources: resources}
	ret := [][]*prog.Syscall{}
	retCaptures := map[CaptureSource][]byte{}
	for i, syscall := range trace.syscalls {
		ctx.inTraceIdx = i
		fmt.Printf("%+v\n", syscall)
		ctx.syscall = &syscall
		if !(i < len(matches)) {
			break
		}
		if syscall.sysnum != matches[i].SysNum {
			panic("TODO")
		}
		ctx.fixedArgs = matches[i].Args
		fmt.Printf("strict match: %+v\n", ctx.fixedArgs)
		cands, captures := ctx.match()
		for src, mem := range captures {
			retCaptures[src] = mem
		}
		ret = append(ret, cands)
		// fmt.Scanln()
	}
	return ret, retCaptures
}

func (ctx *MatchCtx) match() ([]*prog.Syscall, map[CaptureSource][]byte) {
	syscall := ctx.syscall
	ret := []*prog.Syscall{}
	captures := map[CaptureSource][]byte{}
	cands := SyzlangMap[syscall.sysnum]
	for i, cand := range cands {
		if strings.HasPrefix(cand.CallName, "syz_") {
			continue
		}
		matched := true
		ctx.log("[%d] %+v", i, cand)
		ctx.progSyscall = cand
		ctx.captures = map[CaptureSource][]byte{}
		ctx.depth++
		// DO NOT depend on syscall.args, which is from the trace
		for i_field, field := range cand.Args {
			if !(i_field < len(syscall.args)) {
				ctx.log("[%d] Ignoring untraced args ...", i_field)
				continue
			}
			ctx.log("[%d] %+v %+v = %+v", i_field, field.Name, field, syscall.args[i_field])
			if !(!field.HasDirection && field.Direction == prog.DirIn) {
				panic("TODO")
			}
			if field.Condition != nil {
				panic("TODO")
			}
			ctx.argIdx = i_field
			ctx.inArgPath = 0
			ctx.isStrict = ctx.fixedArgs[i_field]
			if !ctx.matchNum(field.Type, syscall.args[i_field]) && ctx.isStrict {
				matched = false
				break
			}
		}
		ctx.depth--
		ctx.log("matched: %+v", matched)
		if matched {
			ret = append(ret, cand)
			for src, mem := range ctx.captures {
				captures[src] = mem
			}
		}
	}
	for _, cand := range ret {
		ctx.log(BAR)
		ctx.log("%+v", cand)
		ctx.matchRet(cand.Ret, syscall.args)
	}
	return ret, captures
}

// TODO: Recover
// TODO: Integrate into matchMem()
// TODO: Consider opt
// Refer to (*Type).generate in prog/rand.go
// Refer to prog.foreachTypeImpl()
func (ctx *MatchCtx) matchNum(t prog.Type, num uint64) bool {
	origInArgPath := ctx.inArgPath
	defer func() { ctx.inArgPath = origInArgPath }()
	ctx.addPath(uint64(syzlang.PointerizeType(t)))
	ctx.depth++
	defer func() { ctx.depth-- }()
	if ctx.dir != nil {
		ctx.log("Direction: %s", *ctx.dir)
	}
	if !ctx.isStrict && !isPtr(t) && (ctx.dir == nil || *ctx.dir != prog.DirOut) {
		mem := new(bytes.Buffer)
		switch t.Size() {
		case 1:
			binary.Write(mem, binary.LittleEndian, uint8(num))
		case 2:
			binary.Write(mem, binary.LittleEndian, uint16(num))
		case 4:
			binary.Write(mem, binary.LittleEndian, uint32(num))
		case 8:
			binary.Write(mem, binary.LittleEndian, uint64(num))
		}
		ctx.capture(t, mem.Bytes())
	}
	switch t := t.(type) {
	case *prog.ResourceType:
		return ctx.matchResource(t, num)
	case *prog.ConstType:
		return ctx.matchConst(t, num)
	case *prog.IntType:
		return ctx.matchInt(t, num)
	case *prog.FlagsType:
		return ctx.matchFlags(t, num)
	case *prog.LenType:
		ctx.log("Ignoring len%v for now ...", t.Path)
		return true
	case *prog.ProcType:
		return true
	case *prog.VmaType:
		return ctx.matchVma(t, num)
	case *prog.PtrType:
		return ctx.matchPtr(t, num)
	default:
		ctx.log("Failed to handle %T", t)
		panic("TODO")
	}
}

func (ctx *MatchCtx) matchMem(t prog.Type, mem []byte) bool {
	origInArgPath := ctx.inArgPath
	defer func() { ctx.inArgPath = origInArgPath }()
	ctx.addPath(uint64(syzlang.PointerizeType(t)))
	ctx.depth++
	defer func() { ctx.depth-- }()
	if ctx.dir != nil {
		ctx.log("Direction: %s", *ctx.dir)
	}
	ctx.log("Matching %T with %+v", t, mem)
	if !ctx.isStrict && !isPtr(t) && (ctx.dir == nil || *ctx.dir != prog.DirOut) {
		ctx.capture(t, mem)
	}
	switch t := t.(type) {
	case *prog.BufferType:
		return ctx.matchBuffer(t, mem)
	case *prog.ArrayType:
		return ctx.matchArray(t, mem)
	case *prog.StructType:
		return ctx.matchStruct(t, mem)
	case *prog.UnionType:
		return ctx.matchUnion(t, mem)
	default:
		if t.Varlen() {
			panic("TODO")
		}
		if uint64(len(mem)) < t.Size() {
			ctx.log("Mem is too short (%d < %d)", len(mem), t.Size())
			return false
		}
		var num uint64
		switch t.Size() {
		case 1:
			num = uint64(mem[0])
		case 2:
			// FIXME: Get endian from target
			num = uint64(binary.LittleEndian.Uint16(mem))
		case 4:
			num = uint64(binary.LittleEndian.Uint32(mem))
		case 8:
			num = binary.LittleEndian.Uint64(mem)
		}
		return ctx.matchNum(t, num)
	}
}

func isSameVal(arg, val uint64) bool {
	return arg == val ||
		arg <= uint64(math.MaxUint32) && int64(int32(arg)) == int64(val)
}

func isPtr(t prog.Type) bool {
	switch t.(type) {
	case *prog.VmaType, *prog.PtrType:
		return true
	default:
		return false
	}
}

func (ctx *MatchCtx) matchResource(t *prog.ResourceType, arg uint64) bool {
	ctx.log("resource %s", t.Desc.Name)
	if ctx.dir == nil || *ctx.dir != prog.DirOut {
		return ctx.matchResourceIn(t, arg)
	} else {
		return ctx.matchResourceOut(t, arg)
	}
}

func (ctx *MatchCtx) matchResourceIn(t *prog.ResourceType, arg uint64) bool {
	matched := false
	// FIXME: Return early and put special values behind as fallback
	for _, val := range t.SpecialValues() {
		if isSameVal(arg, val) {
			matched = true
			break
		}
	}
	if resources, ok := ctx.resources[arg]; ok {
		ctx.log("%+v", resources)
		for name, kinds := range resources {
			if _, ok := kinds[t.Desc.Name]; !ok {
				continue
			}
			matched = true
			if ctx.progSyscall.Name == "close" {
				delete(resources, name)
			}
		}
	}
	// FIXME: Replace with target.AuxResources
	_, ok := whiteResources[t.Desc.Name]
	matched = matched || ok
	return matched
}

func (ctx *MatchCtx) matchResourceOut(t *prog.ResourceType, arg uint64) bool {
	if _, ok := ctx.resources[arg]; !ok {
		ctx.resources[arg] = make(map[string]map[string]bool)
	}
	if _, ok := ctx.resources[arg][t.Desc.Name]; !ok {
		ctx.resources[arg][t.Desc.Name] = make(map[string]bool)
	}
	for _, kind := range t.Desc.Kind {
		ctx.resources[arg][t.Desc.Name][kind] = true
	}
	return true
}

func (ctx *MatchCtx) matchConst(t *prog.ConstType, arg uint64) bool {
	ctx.log("const[%+v]", t.Val)
	return isSameVal(arg, t.Val)
}

func (ctx *MatchCtx) matchInt(t *prog.IntType, arg uint64) bool {
	switch t.Kind {
	case prog.IntPlain:
		ctx.log("int%d", t.TypeBitSize())
		if !(t.RangeBegin == 0 && t.RangeEnd == 0 && t.Align == 0) {
			panic("TODO")
		}
		return arg < (1 << t.TypeBitSize())
	case prog.IntRange:
		// FIXME: Handle big endian
		// TODO: Handle strict description (e.g. sock_port)
		ctx.log("int%d[%d:%d, %d]", t.TypeBitSize(), t.RangeBegin, t.RangeEnd, t.Align)
		ctx.log("Ignoring range and endian for now...")
		if t.Align != 0 {
			panic("TODO")
		}
		return true
		//return t.RangeBegin <= arg && arg <= t.RangeEnd
	default:
		panic("TODO")
	}
}

func (ctx *MatchCtx) matchFlags(t *prog.FlagsType, arg uint64) bool {
	ctx.log("flags(mask? %+v)%+v", t.BitMask, t.Vals)
	if t.BitMask {
		mask := uint64(0)
		for _, bit := range t.Vals {
			mask |= bit
		}
		return arg|mask == mask
	} else {
		for _, val := range t.Vals {
			if arg == val {
				return true
			}
		}
		return false
	}
}

func (ctx *MatchCtx) matchVma(t *prog.VmaType, arg uint64) bool {
	attr := ""
	if t.RangeBegin != 0 || t.RangeEnd != 0 {
		attr = fmt.Sprintf("[%d-%d]", t.RangeBegin, t.RangeEnd)
	}
	ctx.log("%s%s", t, attr)
	if arg == 0 {
		return true
	}
	// TODO: Handle prog.VmaType.{RangeBegin, RangeEnd}
	return true
}

func (ctx *MatchCtx) matchBuffer(t *prog.BufferType, mem []byte) bool {
	switch t.Kind {
	case prog.BufferBlobRand:
		return true
	case prog.BufferBlobRange:
		return ctx.matchBufferBlobRange(t, mem)
	case prog.BufferString:
		return ctx.matchBufferString(t, mem)
	case prog.BufferFilename:
		return ctx.matchBufferFilename(t, mem)
	case prog.BufferText:
		return ctx.matchBufferText(t, mem)
	case prog.BufferGlob:
		return ctx.matchBufferGlob(t, mem)
	default:
		ctx.log("Failed to handle buffer[%d]", t.Kind)
		panic("TODO")
	}
}

func (ctx *MatchCtx) matchBufferBlobRange(t *prog.BufferType, mem []byte) bool {
	if t.Kind != prog.BufferBlobRange {
		return false
	}
	memSize := uint64(len(mem))
	return t.RangeBegin <= memSize && memSize <= t.RangeEnd
}

func (ctx *MatchCtx) matchBufferString(t *prog.BufferType, mem []byte) bool {
	if t.Kind != prog.BufferString {
		return false
	}
	typeName := "string"
	if t.NoZ {
		typeName += "noz"
	}
	if len(t.Values) > 0 {
		typeName += fmt.Sprintf("%+v", t.Values)
	}
	ctx.log("%s", typeName)
	if len(t.Values) == 0 {
		if t.NoZ {
			return true
		}
		for i := range mem {
			if mem[len(mem)-1-i] == 0 {
				return true
			}
		}
	}
	for _, str := range t.Values {
		if len(mem) < len(str) {
			continue
		}
		if bytes.Equal(mem[:len(str)], []byte(str)) {
			return true
		}
	}
	return false
}

func (ctx *MatchCtx) matchBufferFilename(t *prog.BufferType, mem []byte) bool {
	if t.Kind != prog.BufferFilename {
		return false
	}
	typeName := "string"
	if t.NoZ {
		typeName += "noz"
	}
	typeName += "[filename]"
	if len(t.Values) > 0 {
		typeName += fmt.Sprintf("%+v", t.Values)
	}
	ctx.log("%s", typeName)
	if len(t.Values) > 0 || len(t.SubKind) > 0 {
		panic("TODO")
	}
	if t.NoZ {
		return true
	}
	for i := range mem {
		if mem[len(mem)-1-i] == 0 {
			return true
		}
	}
	return false
}

// prog.BufferText is not a simple text but a binary code.
func (ctx *MatchCtx) matchBufferText(t *prog.BufferType, mem []byte) bool {
	if t.Kind != prog.BufferText {
		return false
	}
	ctx.log("text[%+v]", t.Text)
	if len(mem) == 0 {
		return true
	}
	panic("TODO")
}

func (ctx *MatchCtx) matchBufferGlob(t *prog.BufferType, mem []byte) bool {
	if t.Kind != prog.BufferGlob {
		return false
	}
	ctx.log("glob[%+v]", t.SubKind)
	i_null := bytes.Index(mem, []byte("\x00"))
	if i_null == -1 {
		return false
	}
	// FIXME: Consider non-UTF-8
	path := string(mem[:i_null])
	for _, str := range t.Values {
		if path == strings.TrimRight(str, "\x00") {
			return true
		}
	}
	if filepath.IsLocal(path) {
		return false
	}
	path = filepath.Clean(path)
	matched := true
	// Refer to host.getGlobsInfo()
	glob_pats := strings.Split(t.SubKind, ":")
	for _, pat := range glob_pats {
		ctx.log(pat)
		exclude := strings.HasPrefix(pat, "-")
		if exclude {
			pat = pat[1:]
		}
		if strings.Contains(pat, "***") ||
			strings.Contains(pat, ".") ||
			strings.Contains(pat, "^") ||
			strings.Contains(pat, "[") ||
			strings.Contains(pat, "]") {
			continue
		}
		pat = strings.ReplaceAll(pat, "**", ".\x00")
		pat = strings.ReplaceAll(pat, "*", "[^/]\x00")
		pat = strings.ReplaceAll(pat, "\x00", "*")
		pat = strings.ReplaceAll(pat, "?", ".")
		ctx.log(pat)
		patMatched, err := regexp.Match(pat, []byte(path))
		if err != nil {
			ctx.log(err.Error())
			continue
		}
		if patMatched != !exclude {
			matched = false
			break
		}
	}
	return matched
}

func (ctx *MatchCtx) matchArray(t *prog.ArrayType, mem []byte) bool {
	matched := true
	ctx.log(BAR)
	ctx.log("%+v", t)
	if t.Elem.Varlen() {
		return true
	}
	memLen := uint64(len(mem))
	// TODO: Ignore?
	if t.Kind == prog.ArrayRangeLen {
		if !(t.RangeBegin*t.Elem.Size() <= memLen &&
			memLen <= t.RangeEnd*t.Elem.Size()) {
			return false
		}
	}
	origInArgPath := ctx.inArgPath
	defer func() { ctx.inArgPath = origInArgPath }()
	ctx.depth++
	defer func() { ctx.depth-- }()
	elemOff := uint64(0)
	for elemOff+t.Elem.Size() <= memLen {
		ctx.inArgPath = origInArgPath
		ctx.addPath(elemOff / t.Elem.Size())
		if !ctx.matchMem(t.Elem, mem[elemOff:elemOff+t.Elem.Size()]) {
			matched = false
			if ctx.isStrict {
				break
			}
		}
		elemOff += t.Elem.Size()
	}
	return matched
}

// TODO: Handle "opt" attribute
func (ctx *MatchCtx) matchPtr(t *prog.PtrType, arg uint64) bool {
	syscall := ctx.syscall
	ctx.log("%+v = 0x%x", t, arg)
	if arg == 0 {
		return true
	}
	mem := syscall.readMem(t.ElemDir, arg)
	if mem == nil {
		return false
	}
	ctx.log("%+v", mem)
	ctx.log("%+v", string(mem))
	origDir := ctx.dir
	defer func() { ctx.dir = origDir }()
	ctx.dir = &t.ElemDir
	return ctx.matchMem(t.Elem, mem)
}

func (ctx *MatchCtx) matchStruct(t *prog.StructType, mem []byte) bool {
	matched := true
	ctx.log("%s struct%+v", t.Name(), t.Fields)
	if !t.Varlen() && uint64(len(mem)) < t.Size() {
		ctx.log("Mem is too short (%d < %d)", len(mem), t.Size())
		return false
	}
	fieldOff := uint64(0)
	origInArgPath := ctx.inArgPath
	defer func() { ctx.inArgPath = origInArgPath }()
	origDir := ctx.dir
	defer func() { ctx.dir = origDir }()
	ctx.depth++
	defer func() { ctx.depth-- }()
	for i, field := range t.Fields {
		ctx.inArgPath = origInArgPath
		ctx.addPath(uint64(i))
		size := uint64(0)
		if !field.Varlen() {
			size = field.Size()
		}
		ctx.log("[%d] %s %+v (%T) (size: %d, align: %d)", i, field.Name, field, field.Type, size, field.Alignment())
		if !field.Varlen() && uint64(len(mem)) < fieldOff+field.Size() {
			return false
		}
		high := uint64(len(mem))
		if !field.Varlen() {
			high = fieldOff + field.Size()
		}
		fieldMem := mem[fieldOff:high]
		if field.HasDirection {
			ctx.dir = &field.Direction
		}
		if !ctx.matchMem(field.Type, fieldMem) {
			matched = false
			if ctx.isStrict {
				break
			}
		}
		if !field.Varlen() {
			fieldOff += field.Size()
		} else {
			break
		}
	}
	return matched
}

func (ctx *MatchCtx) matchUnion(t *prog.UnionType, mem []byte) bool {
	matched := false
	ctx.log("%s union%+v", t.Name(), t.Fields)
	origInArgPath := ctx.inArgPath
	defer func() { ctx.inArgPath = origInArgPath }()
	origDir := ctx.dir
	defer func() { ctx.dir = origDir }()
	ctx.depth++
	defer func() { ctx.depth-- }()
	for i, field := range t.Fields {
		ctx.inArgPath = origInArgPath
		ctx.addPath(uint64(i))
		ctx.log("%+v: %+v (%T)", field.Name, field, field.Type)
		if field.HasDirection {
			ctx.dir = &field.Direction
		}
		if ctx.matchMem(field.Type, mem) {
			matched = true
			if ctx.isStrict {
				break
			}
		}
	}
	return matched
}

func (ctx *MatchCtx) matchRet(t prog.Type, args []uint64) {
	if t == nil {
		return
	}
	syscall := ctx.syscall
	ctx.log("ret = %d", int64(syscall.retval))
	if int64(syscall.retval) < 0 &&
		int64(syscall.retval) >= -1*MaxErrNo {
		return
	}
	switch t := t.(type) {
	case *prog.ResourceType:
		ctx.log("ret: resource %s", t.Desc.Name)
		ctx.log("%+v", t.Desc.Kind)
		ctx.matchResourceOut(t, syscall.retval)
		switch ctx.progSyscall.Name {
		case "dup", "dup2":
			var oldFd, newFd uint64
			switch ctx.progSyscall.Name {
			case "dup":
				oldFd = args[0]
				newFd = syscall.retval
			case "dup2":
				oldFd = args[0]
				newFd = args[1]
			}
			ctx.log("dup: %d -> %d", oldFd, newFd)
			if resources, ok := ctx.resources[oldFd]; ok {
				for name, kinds := range resources {
					if _, ok := kinds["fd"]; !ok {
						continue
					}
					// TODO: Separate kinds based on its base class
					ctx.resources[newFd][name] = kinds
				}
			}
		}
	default:
		ctx.log("Failed to handle ret %T", t)
		panic("TODO")
	}
	ctx.log("%+v", ctx.resources)
}

func (syscall *Syscall) readMem(dir prog.Dir, addr uint64) []byte {
	mems := []Mem{}
	fmt.Println(BAR)
	fmt.Printf("inMems: %+v\n", syscall.inMems)
	fmt.Printf("outMems: %+v\n", syscall.outMems)
	fmt.Println(BAR)
	if dir == prog.DirIn || dir == prog.DirInOut {
		mems = append(mems, syscall.inMems...)
	}
	if dir == prog.DirOut || dir == prog.DirInOut {
		mems = append(mems, syscall.outMems...)
	}
	unifiedMem := map[uint64]byte{}
	for _, mem := range mems {
		for i, b := range mem.data {
			addr := mem.addr + uint64(i)
			if oldB, ok := unifiedMem[addr]; ok && b != oldB && dir != prog.DirInOut {
				panic("TODO")
			}
			unifiedMem[addr] = b
		}
	}
	ret := []byte{}
	for {
		b, ok := unifiedMem[addr]
		if !ok {
			break
		}
		ret = append(ret, b)
		addr++
	}
	if len(ret) == 0 {
		return nil
	}
	return ret
}
