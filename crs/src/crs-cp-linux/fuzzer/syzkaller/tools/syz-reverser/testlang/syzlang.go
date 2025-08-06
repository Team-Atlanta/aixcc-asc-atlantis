package testlang

import (
	"fmt"

	"github.com/google/syzkaller/pkg/ast"
	"github.com/google/syzkaller/tools/syz-reverser/syzlang"
)

const DoneComment = "Done"
const RandomComment = "Random"

func (testLang *TestLang) ToSyzLang(id string) *syzlang.Description {
	desc := syzlang.NewDescription(id)
	for _, record := range testLang.records {
		recordDesc := record.toSyzLang(id)
		for _, node := range recordDesc.Finalize().Nodes {
			desc.AddNode(node)
		}
	}
	return desc
}

func (record *Record) toSyzLang(id string) *syzlang.Description {
	desc := syzlang.NewDescription(id)
	name := MakeUniqueName(id, record.name)
	s := ast.Struct{
		Name:    syzlang.MakeAstIdent(name),
		IsUnion: record.isUnion,
	}
	if s.IsUnion {
		s.Attrs = append(s.Attrs, &ast.Type{Ident: "varlen"})
	} else {
		s.Attrs = append(s.Attrs, &ast.Type{Ident: "packed"})
	}
	nameCnts := map[string]int{}
	lenDeps := map[string]string{}
	for _, field := range record.fields {
		// TODO: Init Field.Comments with original testLang
		var f *ast.Field
		var namedSize *NamedSize
		switch field := field.(type) {
		case NormalField:
			var newNodes []ast.Node
			f, namedSize, newNodes = field.toSyzLang(id)
			for _, node := range newNodes {
				desc.AddNode(node)
			}
		case ArrayField:
			f, namedSize = field.toSyzLang(id)
		case RefField:
			f = field.toSyzLang(id)
		default:
			fmt.Printf("Failed to handle %+v\n", field)
			panic("TODO")
		}
		nameCnts[f.Name.Name]++
		if nameCnts[f.Name.Name] > 1 {
			// If there were `len` for this duplicated name, it's already wrong.
			f.Name.Name = fmt.Sprintf("%s_%d", f.Name.Name, nameCnts[f.Name.Name])
		}
		if namedSize != nil {
			if _, ok := lenDeps[namedSize.name]; ok {
				panic("TODO")
			}
			lenDeps[namedSize.name] = f.Name.Name
		}
		s.Fields = append(s.Fields, f)
	}
	for _, field := range s.Fields {
		if arrayName, ok := lenDeps[field.Name.Name]; ok {
			delete(lenDeps, field.Name.Name)
			var size *uint64
			if node := desc.FindNode(field.Type.Ident); node != nil {
				if syzlang.GetAstName(node) != field.Type.Ident {
					continue
				}
				if astStruct, ok := node.(*ast.Struct); ok {
					for _, attr := range astStruct.Attrs {
						if attr.Ident != "size" {
							continue
						}
						size = &attr.Args[0].Value
						desc.RemoveNode(field.Type.Ident)
						for _, field := range astStruct.Fields {
							desc.RemoveNode(field.Type.Ident)
							for _, typeArg := range field.Type.Args {
								desc.RemoveNode(typeArg.Ident)
							}
						}
					}
				}
			}
			if size == nil {
				panic("TODO")
			}
			ident := fmt.Sprintf("int%d", 8*(*size))
			field.Type.Ident = "len"
			field.Type.Args = []*ast.Type{
				{Ident: arrayName},
				{Ident: ident},
			}
			MarkFieldDone(field)
		}
	}
	if len(lenDeps) > 0 {
		for lenName, arrayName := range lenDeps {
			fmt.Printf("Length dependency is not resolved: %s[%s]\n", arrayName, lenName)
		}
		panic("TODO")
	}
	desc.AddNode(&s)
	return desc
}

func (field *NormalField) toSyzLang(id string) (f *ast.Field, namedSize *NamedSize, newNodes []ast.Node) {
	name := MakeUniqueName(id, field.name)
	var pSize *uint64
	if field.size != nil {
		switch s := (*field.size).(type) {
		case FixedSize:
			size := uint64(s.size)
			pSize = &size
		case NamedSize:
			namedSize = &NamedSize{MakeUniqueName(id, s.name)}
		default:
			fmt.Printf("Failed to handle %T\n", s)
			panic("TODO")
		}
	}
	if field.value != nil {
		// TODO: Serialize into byte string
		if pSize == nil ||
			(*pSize != 1 && *pSize != 2 && *pSize != 4 && *pSize != 8) {
			panic("TODO")
		}
		// TODO: Add certain range
		astType := &ast.Type{
			Ident: fmt.Sprintf("int%d", 8*(*pSize)),
			Args:  []*ast.Type{{Value: *field.value}},
		}
		f = syzlang.MakeAstField(name, astType, nil)
		MarkFieldDone(f)
		return
	}
	astFields := []*ast.Field{}
	addField := func(t *ast.Type, isRandom bool) {
		fieldName := fmt.Sprintf("field_%d", len(astFields))
		astField := syzlang.MakeAstField(fieldName, t, nil)
		if isRandom {
			MarkFieldRandom(astField)
		}
		astFields = append(astFields, astField)
	}
	var baseType *ast.Type
	if field.fieldType != nil {
		if *field.fieldType == "string" {
			if pSize == nil {
				baseType = &ast.Type{Ident: "string"}
				addField(baseType, true)
			}
		} else {
			panic("TODO")
		}
	}
	if baseType == nil {
		baseType = &ast.Type{
			Ident: "array",
			Args:  []*ast.Type{{Ident: "int8"}},
		}
		if pSize != nil {
			baseType.Args = append(baseType.Args, &ast.Type{Value: *pSize})
		}
		addField(baseType, true)
		if pSize == nil {
			baseType = &ast.Type{Ident: "string"}
			addField(baseType, true)
		}
	}
	// If size is 1, it's already full by NULL character.
	if pSize == nil || *pSize >= 2 {
		name := syzlang.MakeUniqueName(id)
		values := []string{}
		for i := 0; i < 8; i++ {
			name := field.name
			if pSize != nil {
				name = name[:*pSize-1-1]
			}
			val := fmt.Sprintf("%d%s", i, name)
			values = append(values, val)
		}
		astStrFlags := syzlang.MakeAstStrFlags(name, values)
		newNodes = append(newNodes, astStrFlags)
		astType := &ast.Type{
			Ident: "string",
			Args:  []*ast.Type{{Ident: name}},
		}
		addField(astType, false)
	}
	unionName := syzlang.MakeUniqueName(id)
	astUnion := syzlang.MakeAstUnion(unionName, astFields, nil, pSize)
	newNodes = append(newNodes, astUnion)
	astType := &ast.Type{Ident: unionName}
	f = syzlang.MakeAstField(name, astType, nil)
	return
}

func (field *ArrayField) toSyzLang(id string) (f *ast.Field, namedSize *NamedSize) {
	name := MakeUniqueName(id, field.itemType)
	f = &ast.Field{
		Name: syzlang.MakeAstIdent(name),
		Type: &ast.Type{
			Ident: "array",
			Args:  []*ast.Type{{Ident: name}},
		},
	}
	if field.cnt != nil {
		switch s := (*field.cnt).(type) {
		case FixedSize:
			size := uint64(s.size)
			f.Type.Args = append(f.Type.Args, &ast.Type{Value: size})
		case NamedSize:
			namedSize = &NamedSize{MakeUniqueName(id, s.name)}
		default:
			fmt.Printf("Failed to handle %T\n", s)
			panic("TODO")
		}
	}
	MarkFieldDone(f)
	return
}

func (field *RefField) toSyzLang(id string) *ast.Field {
	name := MakeUniqueName(id, field.name)
	astField := &ast.Field{
		Name: syzlang.MakeAstIdent(name),
		Type: &ast.Type{Ident: name},
	}
	MarkFieldDone(astField)
	return astField
}

func MakeUniqueName(id, name string) string {
	return fmt.Sprintf("%s_%s", id, name)
}

func MarkFieldDone(astField *ast.Field) {
	markField(astField, DoneComment)
}

func MarkFieldRandom(astField *ast.Field) {
	markField(astField, RandomComment)
}

func markField(astField *ast.Field, comment string) {
	for _, astComment := range astField.Comments {
		if astComment.Text == comment {
			return
		}
	}
	astComment := syzlang.MakeAstComment(comment)
	astField.Comments = append(astField.Comments, astComment)
}
