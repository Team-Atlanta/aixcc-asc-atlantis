package syzlang

import (
	"fmt"

	"github.com/google/syzkaller/prog"
)

func GetMinSizeOf(t prog.Type) uint64 {
	return getMinSizeOf(t, 0)
}

func getMinSizeOf(t prog.Type, depth uint64) uint64 {
	depth++
	if depth == 1 {
		switch t.(type) {
		case
			*prog.ResourceType,
			*prog.ConstType,
			*prog.IntType,
			*prog.FlagsType,
			*prog.LenType,
			*prog.ProcType:
			// FIXME: Consider possible values for each type
			return 1
		}
	}
	if !t.Varlen() {
		return t.Size()
	}
	switch t := t.(type) {
	default:
		fmt.Printf("Failed to handle %T\n", t)
		panic("TODO")
	}
}
