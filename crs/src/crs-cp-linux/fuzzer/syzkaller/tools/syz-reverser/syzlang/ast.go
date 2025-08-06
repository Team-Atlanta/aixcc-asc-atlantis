package syzlang

import (
	"fmt"

	"github.com/google/syzkaller/pkg/ast"
)

func GetAstName(node ast.Node) string {
	_, _, name := node.Info()
	return name
}

func MakeAstIdent(name string) *ast.Ident {
	return &ast.Ident{Name: name}
}

func MakeAstComment(text string) *ast.Comment {
	return &ast.Comment{Text: text}
}

func MakeAstCall(callName, inputName string) *ast.Call {
	bufName, lenName := "buf", "len"
	name := MakeAstCallName(callName, inputName)
	return &ast.Call{
		Name:     MakeAstIdent(name),
		CallName: callName,
		Args: []*ast.Field{
			{
				Name: MakeAstIdent(bufName),
				Type: &ast.Type{
					Ident: "ptr",
					Args: []*ast.Type{
						{Ident: "in"},
						{Ident: inputName},
					},
				},
			},
			{
				Name: MakeAstIdent(lenName),
				Type: &ast.Type{
					Ident: "bytesize",
					Args: []*ast.Type{
						{Ident: bufName},
					},
				},
			},
		},
	}
}

func MakeAstCallName(callName, inputName string) string {
	// TODO: Add unique ID to name so that it can be unique from other testlang
	return fmt.Sprintf("%s$%s", callName, inputName)
}

func MakeAstUnion(name string, fields []*ast.Field, comments []*ast.Comment, size *uint64) *ast.Struct {
	attrs := []*ast.Type{}
	var attr *ast.Type
	if size == nil {
		attr = &ast.Type{Ident: "varlen"}
	} else {
		attr = &ast.Type{
			Ident: "size",
			Args:  []*ast.Type{{Value: *size}},
		}
	}
	attrs = append(attrs, attr)
	return makeAstStruct(name, fields, attrs, comments, true)
}

func MakeAstStruct(name string, fields []*ast.Field, comments []*ast.Comment, size *uint64) *ast.Struct {
	attrs := []*ast.Type{{Ident: "packed"}}
	if size != nil {
		attr := ast.Type{
			Ident: "size",
			Args:  []*ast.Type{{Value: *size}},
		}
		attrs = append(attrs, &attr)
	}
	return makeAstStruct(name, fields, attrs, comments, false)
}

func makeAstStruct(name string, fields []*ast.Field, attrs []*ast.Type, comments []*ast.Comment, isUnion bool) *ast.Struct {
	s := ast.Struct{
		Name:     MakeAstIdent(name),
		Fields:   fields,
		Attrs:    attrs,
		Comments: comments,
		IsUnion:  isUnion,
	}
	return &s
}

func MakeAstStrFlags(name string, values []string) *ast.StrFlags {
	strs := []*ast.String{}
	for _, val := range values {
		str := MakeAstString(val)
		strs = append(strs, str)
	}
	return &ast.StrFlags{
		Name:   MakeAstIdent(name),
		Values: strs,
	}
}

func MakeAstString(value string) *ast.String {
	return &ast.String{Value: value}
}

func MakeAstType(args []*ast.Type, value *uint64, ident, str *string, expr *ast.BinaryExpression) *ast.Type {
	t := ast.Type{
		Args: args,
	}
	if value != nil {
		t.Value = *value
		return &t
	}
	if ident != nil {
		t.Ident = *ident
		return &t
	}
	if str != nil {
		t.String = *str
		t.HasString = true
		return &t
	}
	if expr != nil {
		t.Expression = expr
		return &t
	}
	return nil
}

func MakeAstArrayType(size *uint64) *ast.Type {
	typeID := "array"
	elemTypeID := "int8"
	args := []*ast.Type{MakeAstType(nil, nil, &elemTypeID, nil, nil)}
	if size != nil {
		sizeT := MakeAstType(nil, size, nil, nil, nil)
		args = append(args, sizeT)
	}
	return MakeAstType(args, nil, &typeID, nil, nil)
}

func MakeAstField(name string, typ *ast.Type, comments []*ast.Comment) *ast.Field {
	f := ast.Field{
		Name:     MakeAstIdent(name),
		Type:     typ,
		Comments: comments,
	}
	return &f
}
