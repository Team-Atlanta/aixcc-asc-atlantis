package parser

import (
	"encoding/binary"
	"fmt"
	"reflect"
	"strconv"

	"github.com/google/syzkaller/pkg/log"
	"github.com/google/syzkaller/prog"
)

type context struct {
	builder      *prog.Builder
	target       *prog.Target
	syzMap       map[uint64]string
	count        uint64
	resources    []*prog.ResultArg
	blob         []byte
	blob0        []byte
	parseCommand bool
	exhausted    bool
	consumed     int
	// Cache for the currently-building call
	call        *prog.Call
	lengths     [MaxDepth]map[string]uint64
	depth       int
	lenFromBlob bool
}

// Max depth of nested arguments
const MaxDepth = 16

func (ctx *context) reinit() {
	ctx.call = nil
	for i := 0; i < MaxDepth; i++ {
		ctx.lengths[i] = nil
	}
	ctx.depth = 0
}

func (ctx *context) __parseInt(size int, remove bool) uint64 {
	if len(ctx.blob) < size {
		ctx.exhausted = true
		panic("blob is exhausted")
	}
	var val uint64
	switch size {
	case 1:
		val = uint64(ctx.blob[0])
	case 2:
		val = uint64(binary.LittleEndian.Uint16(ctx.blob[:size]))
	case 4:
		val = uint64(binary.LittleEndian.Uint32(ctx.blob[:size]))
	case 8:
		val = binary.LittleEndian.Uint64(ctx.blob[:size])
	}
	if remove {
		ctx.consumed += size
		ctx.blob = ctx.blob[size:]
	}
	log.Logf(3, "Parsing int: %v (size: %v)", val, size)
	return val
}

func (ctx *context) parseInt(size int) uint64 {
	return ctx.__parseInt(size, true)
}

func (ctx *context) copyBlob(size uint64) []byte {
	if len(ctx.blob) < int(size) {
		ctx.exhausted = true
		panic("blob is exhausted")
	}
	res := make([]byte, size)
	copy(res, ctx.blob[:size])
	ctx.blob = ctx.blob[size:]
	ctx.consumed += int(size)
	log.Logf(3, "Parsing blob (size: %v): %v", size, res)
	return res
}

func (ctx *context) genArgs(call *prog.Call) []prog.Arg {
	ctx.lenFromBlob = true
	args := []prog.Arg{}
	for _, field := range call.Meta.Args {
		arg := ctx.genArg(field.Type, field.Name, field.Dir(prog.DirIn))
		args = append(args, arg)
		ctx.lenFromBlob = false
	}
	return args
}

func (ctx *context) genArg(typ prog.Type, name string, dir prog.Dir) prog.Arg {
	log.Logf(1, "name: %v, type: %v (%v)", name, typ, reflect.TypeOf(typ))
	ctx.depth++
	defer func() {
		ctx.depth--
	}()

	if dir == prog.DirOut {
		switch typ.(type) {
		case *prog.IntType, *prog.FlagsType, *prog.ConstType, *prog.ProcType, *prog.VmaType:
			return typ.DefaultArg(dir)
		case *prog.ResourceType:
			a := typ.DefaultArg(dir).(*prog.ResultArg)
			// XXX: is this compatible for all harnesses?
			ctx.resources = append(ctx.resources, a)
			return a
		}
	}

	switch t := typ.(type) {
	case *prog.IntType, *prog.ConstType, *prog.FlagsType, *prog.CsumType:
		return ctx.genConst(t, name)
	case *prog.LenType:
		return ctx.genLen(t)
	case *prog.ResourceType:
		return ctx.genResource(t, dir)
	case *prog.PtrType:
		return ctx.genPtr(t)
	case *prog.BufferType:
		return ctx.genBuffer(t, name)
	case *prog.StructType:
		return ctx.genStruct(t, dir)
	case *prog.ArrayType:
		return ctx.genArray(t, dir)
	case *prog.UnionType:
		return ctx.genUnion(t, dir, name)
	// case *prog.ProcType:
	// case *prog.VmaType:
	default:
		panic(fmt.Sprintf("unsupported type: %#v", t))
	}
}

func (ctx *context) genPtr(t *prog.PtrType) prog.Arg {
	elem := ctx.genArg(t.Elem, t.Elem.String(), t.ElemDir)
	return prog.MakePointerArg(t, t.ElemDir, ctx.builder.Allocate(elem.Size(), t.Alignment()), elem)
}

func (ctx *context) genStruct(t *prog.StructType, dir prog.Dir) prog.Arg {
	inner := []prog.Arg{}
	for _, f := range t.Fields {
		a0 := ctx.genArg(f.Type, f.Name, dir)
		inner = append(inner, a0)
	}
	return prog.MakeGroupArg(t, dir, inner)
}

func (ctx *context) genConst(t prog.Type, name string) prog.Arg {
	var base int
	var i int
	switch t.Format() {
	case prog.FormatNative:
		var val uint64
		if name == "comma" && t.Size() == 1 && ctx.blob[0] != ',' {
			// XXX: Need to test this more. I don't understand what
			// the doc says (the string flag part)
			val = ','
		} else {
			val = ctx.getUint64(int(t.Size()))
		}
		return prog.MakeConstArg(t, prog.DirIn, val)
	case prog.FormatStrHex:
		for i = 0; i < len(ctx.blob) && (('0' <= ctx.blob[i] && ctx.blob[i] <= '9') || ('a' <= ctx.blob[i] && ctx.blob[i] <= 'f')); i++ {
		}
		base = 16
	case prog.FormatStrDec:
		for i = 0; i < len(ctx.blob) && ('0' <= ctx.blob[i] && ctx.blob[i] <= '9'); i++ {
		}
		base = 10
	case prog.FormatStrOct:
		for i = 0; i < len(ctx.blob) && ('0' <= ctx.blob[i] && ctx.blob[i] <= '7'); i++ {
		}
		base = 8
	default:
		panic("not supported")
	}
	data := ctx.copyBlob(uint64(i))
	val, err := strconv.ParseUint(string(data), base, 64)
	if err != nil {
		panic(err)
	}
	return prog.MakeConstArg(t, prog.DirIn, val)
}

func (ctx *context) genLen(t *prog.LenType) prog.Arg {
	var val uint64
	if ctx.lenFromBlob {
		val := ctx.getUint64(int(t.Size()))
		for _, p := range t.Path {
			ctx.recordLength(p, val)
		}
	}
	return prog.MakeConstArg(t, prog.DirIn, val)
}

func (ctx *context) __recordLength(path string, val uint64, d int) {
	log.Logf(2, "Recording legnth %v of %v (depth: %v)", val, path, d)
	if ctx.lengths[d] == nil {
		ctx.lengths[d] = make(map[string]uint64)
	}
	ctx.lengths[d][path] = val
}

func (ctx *context) recordLength(path string, val uint64) {
	d := ctx.depth - 1
	ctx.__recordLength(path, val, d)
}

func (ctx *context) lookupLength(name string) (uint64, bool) {
	d := ctx.depth - 1
	log.Logf(2, "Looking up length for %v (depth: %v)", name, d)
	if ctx.lengths[d] == nil {
		return 0, false
	}
	if len, ok := ctx.lengths[d][name]; ok {
		log.Logf(2, "Returning legnth %v for %v", len, name)
		return len, true
	}
	return 0, false
}

func (ctx *context) genResource(t *prog.ResourceType, dir prog.Dir) prog.Arg {
	idx := ctx.getUint64(int(t.Size()))
	return prog.MakeResultArg(t, dir, ctx.resources[idx], 0)
}

func (ctx *context) genBuffer(t *prog.BufferType, name string) prog.Arg {
	switch k := t.Kind; k {
	case prog.BufferBlobRand, prog.BufferFilename, prog.BufferString, prog.BufferBlobRange:
		var (
			len uint64
			ok  bool
		)
		if !t.IsVarlen {
			len = t.Size()
		} else {
			len, ok = ctx.lookupLength(name)
			if !ok {
				len, ok = ctx.calculateLengthForNoZ(t)
			}
			if !ok {
				panic("XXX: failed to retrieve the length")
			}
		}
		data := ctx.copyBlob(len)
		if k == prog.BufferString && !checkBufferValue(t, data, t.Values) {
			panic(fmt.Sprintf("wrong: %v, %v", data, t.Values))
		}
		return prog.MakeDataArg(t, prog.DirIn, data)
	default:
		panic(fmt.Sprintf("not yet implemented: %v", k))
	}
}

func checkBufferValue(t *prog.BufferType, data []byte, values []string) bool {
	if t.IsVarlen {
		return true
	}
	s := string(data)
	for _, v := range values {
		if v == s {
			return true
		}
	}
	return false
}

func (ctx *context) calculateLengthForNoZ(t *prog.BufferType) (uint64, bool) {
	if t.NoZ {
		return 0, false
	}
	for i := 0; i < len(ctx.blob); i++ {
		if ctx.blob[i] == 0 {
			return uint64(i) + 1, true
		}
	}
	return 0, false
}

func (ctx *context) genArray(t *prog.ArrayType, dir prog.Dir) prog.Arg {
	// XXX: Assumption
	var len uint64
	if !t.Varlen() {
		len = t.RangeBegin
	} else {
		var ok bool
		len, ok = ctx.lookupLength(t.Name())
		if !ok {
			// XXX: Cannot infer the length of the array.
			len = 1
		}
	}
	var args []prog.Arg
	for i := 0; i < int(len); i++ {
		switch t := t.Elem.(type) {
		case *prog.StructType:
			arg := ctx.genArg(t, t.Name(), dir)
			args = append(args, arg)
		case *prog.IntType:
			arg := ctx.genArg(t, t.Name(), dir)
			args = append(args, arg)
		default:
			panic(fmt.Sprintf("unsupported: %v", t))
		}
	}
	return prog.MakeGroupArg(t, prog.DirIn, args)
}

func (ctx *context) genUnion(t *prog.UnionType, dir prog.Dir, name string) prog.Arg {
	for i, f := range t.Fields {
		blob := make([]byte, len(ctx.blob))
		copy(blob, ctx.blob)
		arg := ctx.tryGenUnion(t, dir, f, name, i)
		if arg != nil {
			log.Logf(3, "Generated union: %v", f.Name)
			return arg
		}
		ctx.blob = blob
	}
	if !t.Varlen() {
		f := t.Fields[0]
		opt := ctx.genArg(f.Type, f.Name, dir)
		return prog.MakeUnionArg(t, dir, opt, 0)
	}
	return t.DefaultArg(dir)
}

func (ctx *context) tryGenUnion(t *prog.UnionType, dir prog.Dir, f prog.Field, name string, index int) (a prog.Arg) {
	// XXX:
	defer func() {
		if err := recover(); err != nil {
			log.Logf(4, "%v: %v", f.Name, err)
			a = nil
			return
		}
	}()
	switch t0 := f.Type.(type) {
	case *prog.StructType:
		a := ctx.genArg(t0, f.Name, dir)
		return prog.MakeUnionArg(t, dir, a, index)
	case *prog.BufferType:
		len, ok := ctx.lookupLength(name)
		if ok {
			data := ctx.copyBlob(len)
			a := prog.MakeDataArg(t0, dir, data)
			return prog.MakeUnionArg(t, dir, a, index)
		}
	default:
		panic(fmt.Sprintf("unsupported underlying type, %v", reflect.TypeOf(t0)))
	}
	panic("failed gen union")
}

func (ctx *context) getUint64(byte int) uint64 {
	return ctx.parseInt(byte)
}
