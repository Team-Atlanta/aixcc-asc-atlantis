package syzlang

import (
	"fmt"

	"github.com/google/syzkaller/pkg/ast"
)

type Description struct {
	ID      string
	NodeMap map[string]ast.Node
}

func NewDescription(id string) *Description {
	return &Description{
		ID:      id,
		NodeMap: make(map[string]ast.Node),
	}
}

func (desc *Description) Finalize() *ast.Description {
	astDesc := &ast.Description{}
	for name, node := range desc.NodeMap {
		if name != GetAstName(node) {
			fmt.Println(name)
			fmt.Println(GetAstName(node))
			panic("TODO")
		}
		astDesc.Nodes = append(astDesc.Nodes, node.Clone())
		astDesc.Nodes = append(astDesc.Nodes, &ast.NewLine{})
	}
	return astDesc
}

func (desc *Description) MakeUniqueName() string {
	return MakeUniqueName(desc.ID)
}

func (desc *Description) AddNode(node ast.Node) {
	name := GetAstName(node)
	if name == "" {
		return
	}
	// TODO: Let nodes have unique names
	if _, ok := desc.NodeMap[name]; ok {
		panic("TODO")
	}
	desc.NodeMap[name] = node
}

func (desc *Description) FindNode(name string) ast.Node {
	return desc.NodeMap[name]
}

func (desc *Description) GetCalls() []*ast.Call {
	nodes := []*ast.Call{}
	for _, node := range desc.NodeMap {
		if node, ok := node.(*ast.Call); ok {
			nodes = append(nodes, node)
		}
	}
	return nodes
}

func (desc *Description) RemoveNode(name string) {
	delete(desc.NodeMap, name)
}

func (desc *Description) RemoveTree(name string) {
	root := desc.FindNode(name)
	if root == nil {
		return
	}
	desc.RemoveNode(name)
	if root, ok := root.(*ast.Struct); ok {
		for _, field := range root.Fields {
			desc.RemoveType(field.Type)
		}
	}
}

func (desc *Description) RemoveType(t *ast.Type) {
	desc.RemoveTree(t.Ident)
	for _, arg := range t.Args {
		desc.RemoveTree(arg.Ident)
	}
}

func (desc *Description) Clone() *Description {
	newDesc := NewDescription(desc.ID)
	for _, node := range desc.NodeMap {
		newDesc.AddNode(node.Clone())
	}
	return newDesc
}

func (desc Description) RenameNode(oldName, newName string) {
	node, ok := desc.NodeMap[oldName]
	if !ok {
		return
	}
	switch node := node.(type) {
	case *ast.Define:
		node.Name.Name = newName
	case *ast.Resource:
		node.Name.Name = newName
	case *ast.Call:
		node.Name.Name = newName
	case *ast.Struct:
		node.Name.Name = newName
	case *ast.IntFlags:
		node.Name.Name = newName
	case *ast.StrFlags:
		node.Name.Name = newName
	case *ast.TypeDef:
		node.Name.Name = newName
	default:
		panic("TODO")
	}
	delete(desc.NodeMap, oldName)
	desc.NodeMap[newName] = node
}
