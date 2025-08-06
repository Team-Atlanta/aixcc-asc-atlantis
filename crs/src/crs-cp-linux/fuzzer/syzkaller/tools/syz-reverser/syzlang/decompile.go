package syzlang

import (
	"fmt"
	"strings"

	"github.com/google/syzkaller/pkg/ast"
	"github.com/google/syzkaller/prog"
)

type Decompiler struct {
	ID string
}

// TODO: Inspect each type more
// DO NOT use prog.Type.Size()
func (decomp *Decompiler) DecompileType(typ prog.Type, size *uint64) (*ast.Type, []ast.Node) {
	if size == nil {
		switch typ.(type) {
		case *prog.ResourceType, *prog.ConstType, *prog.IntType,
			*prog.FlagsType, *prog.LenType:
			return nil, nil
		case *prog.BufferType, *prog.StructType:
		default:
			fmt.Printf("Failed to handle %T\n", typ)
			panic("TODO")
		}
	}
	switch typ.(type) {
	case *prog.BufferType:
	case *prog.PtrType:
		// TODO: Get from target
		if size != nil && *size != 8 {
			return nil, nil
		}
	default:
		// FIXME: DO NOT limit
		if size != nil && *size != 1 && *size != 2 && *size != 4 && *size != 8 {
			return nil, nil
		}
	}
	switch typ := typ.(type) {
	case *prog.ResourceType:
		astType := ast.Type{Ident: typ.Name()}
		return &astType, nil
	case *prog.ConstType:
		astType := ast.Type{
			Ident: intN(*size),
			Args: []*ast.Type{
				{Value: typ.Val},
			},
		}
		return &astType, nil
	case *prog.IntType:
		return decomp.decompileIntType(typ, *size), nil
	case *prog.FlagsType:
		astType := ast.Type{
			Ident: "flags",
			Args: []*ast.Type{
				{Ident: typ.Name()},
				{Ident: intN(*size)},
			},
		}
		return &astType, nil
	case *prog.LenType:
		return decomp.decompileLenType(typ, size)
	case *prog.BufferType:
		return decomp.decompileBufferType(typ, size)
	case *prog.PtrType:
		panic("TODO")
		// return &ast.Type{
		// 	Ident: "ptr",
		// 	Args: []*ast.Type{
		// 		{Ident: typ.ElemDir.String()},
		// 		// FIXME: Make size arg optional
		// 		decompileType(typ.Elem, 0),
		// 	},
		// }
	case *prog.StructType:
		return decomp.decompileStructType(typ), nil
	default:
		fmt.Printf("Failed to decompile %T\n", typ)
		return nil, nil
	}
}

// FIXME: Set max value based on t.TypeBitSize()
func (decomp *Decompiler) decompileIntType(t *prog.IntType, size uint64) *ast.Type {
	ret := ast.Type{Ident: intN(size)}
	switch t.Kind {
	case prog.IntPlain:
	case prog.IntRange:
		rangeArg := ast.Type{
			Value: t.RangeBegin,
			Colon: []*ast.Type{
				{Value: t.RangeEnd},
			},
		}
		ret.Args = append(ret.Args, &rangeArg)
		if t.Align != 0 {
			alignArg := ast.Type{Value: t.Align}
			ret.Args = append(ret.Args, &alignArg)
		}
	default:
		panic("TODO")
	}
	return &ret
}

func intN(n uint64) string {
	return fmt.Sprintf("int%d", 8*n)
}

func (decomp *Decompiler) decompileLenType(t *prog.LenType, size *uint64) (*ast.Type, []ast.Node) {
	if len(t.Path) != 1 {
		panic("TODO")
	}
	newNodes := []ast.Node{}
	ret := ast.Type{
		Ident: "len",
		Args: []*ast.Type{
			{Ident: t.Path[0]},
			{Ident: intN(*size)},
		},
	}
	astFields := []*ast.Field{}
	astLenField := MakeAstField("field_0", &ret, nil)
	astFields = append(astFields, astLenField)
	voidName := t.Path[0]
	astVoidType := &ast.Type{
		Ident: "array",
		Args:  []*ast.Type{{Ident: "void"}},
	}
	astVoidField := MakeAstField(voidName, astVoidType, nil)
	astFields = append(astFields, astVoidField)
	structName := MakeUniqueName(decomp.ID)
	structName = strings.ReplaceAll(structName, "-", "_")
	astStruct := MakeAstStruct(structName, astFields, nil, size)
	newNodes = append(newNodes, astStruct)
	astType := ast.Type{Ident: structName}
	return &astType, newNodes
}

// Be aware that prog.BufferType is not the buffer type built in syzlang.
// (i.e. type buffer[DIR] ptr[DIR, array[int8]])
func (decomp *Decompiler) decompileBufferType(t *prog.BufferType, size *uint64) (*ast.Type, []ast.Node) {
	switch t.Kind {
	case prog.BufferBlobRand:
		astType := &ast.Type{
			Ident: "array",
			Args:  []*ast.Type{{Ident: "int8"}},
		}
		if size != nil {
			astType.Args = append(astType.Args, &ast.Type{Value: *size})
		}
		return astType, nil
	case prog.BufferString:
		newNodes := []ast.Node{}
		astType := &ast.Type{Ident: "string"}
		if t.NoZ {
			astType.Ident += "noz"
		}
		if len(t.Values) > 0 {
			id := MakeUniqueName(decomp.ID)
			astStrFlags := ast.StrFlags{Name: MakeAstIdent(id)}
			for _, value := range t.Values {
				if !t.NoZ {
					value = value[:len(value)-1]
				}
				// TODO: Handle ast.String.Fmt
				str := ast.String{Value: value}
				astStrFlags.Values = append(astStrFlags.Values, &str)
			}
			newNodes = append(newNodes, &astStrFlags)
			arg := ast.Type{Ident: id}
			astType.Args = append(astType.Args, &arg)
		}
		if size != nil {
			astType.Args = append(astType.Args, &ast.Type{Value: *size})
		}
		return astType, newNodes
	case prog.BufferFilename:
		astType := &ast.Type{
			Ident: "string",
			Args:  []*ast.Type{{Ident: "filename"}},
		}
		if t.NoZ {
			astType.Ident += "noz"
		}
		return astType, nil
	case prog.BufferGlob:
		astType := ast.Type{
			Ident: "glob",
			Args: []*ast.Type{
				{
					HasString: true,
					String:    t.SubKind,
				},
			},
		}
		return &astType, nil
	default:
		fmt.Printf("Failed to handle buffer (kind: %d)\n", t.Kind)
		panic("TODO")
	}
}

func (decomp *Decompiler) decompileStructType(t *prog.StructType) *ast.Type {
	ret := ast.Type{Ident: t.Name()}
	return &ret
}
