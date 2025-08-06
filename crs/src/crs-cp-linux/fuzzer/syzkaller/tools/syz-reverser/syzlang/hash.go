package syzlang

import (
	"encoding/binary"
	"fmt"
	"hash"
	"hash/fnv"
	"sort"

	"github.com/google/syzkaller/pkg/ast"
)

// pkg/ast/ast.go
type HashAstType uint64

const (
	HashAstTypeStruct = iota
	HashAstTypeStrFlags
	HashAstTypeBinaryExpression
	HashAstTypeType
	HashAstTypeField
)

func HashStr(str string) uint64 {
	h := fnv.New64a()
	h.Write([]byte(str))
	return h.Sum64()
}

func (desc *Description) HashAstTypeForStruct(s *ast.Struct) uint64 {
	if s == nil {
		return 0
	}
	h := fnv.New64a()
	writeNumToHash(h, HashAstTypeStruct)
	if !s.IsUnion {
		writeNumToHash(h, 0)
		writeNumToHash(h, uint64(len(s.Fields)))
		for _, field := range s.Fields {
			writeNumToHash(h, desc.HashAstTypeForField(field))
		}
	} else {
		writeNumToHash(h, 1)
		fieldHashMap := map[uint64]bool{}
		for _, field := range s.Fields {
			fieldHashMap[desc.HashAstTypeForField(field)] = true
		}
		fieldHashes := []uint64{}
		for fieldHash := range fieldHashMap {
			fieldHashes = append(fieldHashes, fieldHash)
		}
		sort.Slice(fieldHashes, func(i, j int) bool {
			return fieldHashes[i] < fieldHashes[j]
		})
		writeNumToHash(h, uint64(len(fieldHashes)))
		for _, fieldHash := range fieldHashes {
			writeNumToHash(h, fieldHash)
		}
	}
	writeNumToHash(h, uint64(len(s.Attrs)))
	for _, attr := range s.Attrs {
		writeNumToHash(h, desc.HashAstTypeForType(attr))
	}
	return h.Sum64()
}

func (desc *Description) HashAstTypeForStrFlags(s *ast.StrFlags) uint64 {
	if s == nil {
		return 0
	}
	h := fnv.New64a()
	writeNumToHash(h, HashAstTypeStrFlags)
	strHashMap := map[uint64]bool{}
	for _, val := range s.Values {
		strHashMap[HashStr(val.Value)] = true
	}
	strHashes := []uint64{}
	for strHash := range strHashMap {
		strHashes = append(strHashes, strHash)
	}
	sort.Slice(strHashes, func(i, j int) bool {
		return strHashes[i] < strHashes[j]
	})
	writeNumToHash(h, uint64(len(strHashes)))
	for _, strHash := range strHashes {
		writeNumToHash(h, strHash)
	}
	return h.Sum64()
}

func (desc *Description) HashAstTypeForBinExpr(expr *ast.BinaryExpression) uint64 {
	if expr == nil {
		return 0
	}
	h := fnv.New64a()
	writeNumToHash(h, HashAstTypeBinaryExpression)
	writeNumToHash(h, uint64(expr.Operator))
	writeNumToHash(h, desc.HashAstTypeForType(expr.Left))
	writeNumToHash(h, desc.HashAstTypeForType(expr.Right))
	return h.Sum64()
}

func (desc *Description) HashAstTypeForType(t *ast.Type) uint64 {
	if t == nil {
		return 0
	}
	h := fnv.New64a()
	writeNumToHash(h, HashAstTypeType)
	// Only one of Value, Ident, String, Expression is filled.
	// from ast.fmtEndType()
	switch {
	case t.Ident != "":
		writeNumToHash(h, 0)
		switch node := desc.FindNode(t.Ident).(type) {
		case nil:
		case *ast.Struct:
			writeNumToHash(h, desc.HashAstTypeForStruct(node))
		case *ast.StrFlags:
			writeNumToHash(h, desc.HashAstTypeForStrFlags(node))
		default:
			fmt.Printf("Failed to handle %s (%T)\n", t.Ident, node)
			panic("TODO")
		}
	case t.HasString:
		writeNumToHash(h, 1)
		writeNumToHash(h, HashStr(t.String))
	case t.Expression != nil:
		writeNumToHash(h, 2)
		writeNumToHash(h, desc.HashAstTypeForBinExpr(t.Expression))
	default:
		writeNumToHash(h, 3)
		writeNumToHash(h, t.Value)
	}
	writeNumToHash(h, uint64(len(t.Colon)))
	for _, colon := range t.Colon {
		writeNumToHash(h, desc.HashAstTypeForType(colon))
	}
	writeNumToHash(h, uint64(len(t.Args)))
	for _, arg := range t.Args {
		writeNumToHash(h, desc.HashAstTypeForType(arg))
	}
	return h.Sum64()
}

func (desc *Description) HashAstTypeForField(field *ast.Field) uint64 {
	if field == nil {
		return 0
	}
	h := fnv.New64a()
	writeNumToHash(h, HashAstTypeField)
	writeNumToHash(h, desc.HashAstTypeForType(field.Type))
	writeNumToHash(h, uint64(len(field.Attrs)))
	for _, attr := range field.Attrs {
		writeNumToHash(h, desc.HashAstTypeForType(attr))
	}
	return h.Sum64()
}

func writeNumToHash(h hash.Hash64, num uint64) {
	buf := make([]byte, 8)
	binary.LittleEndian.PutUint64(buf, num)
	h.Write(buf)
}
