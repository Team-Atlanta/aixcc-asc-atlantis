package syzlang

import (
	"fmt"
	"os"
	"strings"
	"unsafe"

	"github.com/google/syzkaller/pkg/ast"
	"github.com/google/syzkaller/prog"
	"github.com/google/uuid"
)

func SaveToFile(desc *ast.Description, path string) error {
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()
	ast.FormatWriter(file, desc)
	return nil
}

func PointerizeType(t prog.Type) uintptr {
	var ptr unsafe.Pointer
	switch t := t.(type) {
	case *prog.ResourceType:
		ptr = unsafe.Pointer(t)
	case *prog.ConstType:
		ptr = unsafe.Pointer(t)
	case *prog.IntType:
		ptr = unsafe.Pointer(t)
	case *prog.FlagsType:
		ptr = unsafe.Pointer(t)
	case *prog.LenType:
		ptr = unsafe.Pointer(t)
	case *prog.ProcType:
		ptr = unsafe.Pointer(t)
	case *prog.CsumType:
		ptr = unsafe.Pointer(t)
	case *prog.VmaType:
		ptr = unsafe.Pointer(t)
	case *prog.BufferType:
		ptr = unsafe.Pointer(t)
	case *prog.ArrayType:
		ptr = unsafe.Pointer(t)
	case *prog.PtrType:
		ptr = unsafe.Pointer(t)
	case *prog.StructType:
		ptr = unsafe.Pointer(t)
	case *prog.UnionType:
		ptr = unsafe.Pointer(t)
	default:
		panic("TODO")
	}
	return uintptr(ptr)
}

func MakeUniqueName(prefix string) string {
	id := uuid.NewString()
	id = strings.Replace(id, "-", "_", -1)
	id = fmt.Sprintf("%s_%s", prefix, id)
	return id
}
