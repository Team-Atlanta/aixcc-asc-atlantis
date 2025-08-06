package reverse

import (
	"fmt"
	"os"
	"strings"

	"github.com/google/syzkaller/pkg/ast"
	"github.com/google/syzkaller/pkg/compiler"
	"github.com/google/syzkaller/tools/syz-reverser/syzlang"
	"github.com/google/syzkaller/tools/syz-reverser/testlang"
)

const (
	TestLangCallName = "syz_harness"
)

func (rev *Reverser) Transpile(testLang *testlang.TestLang) error {
	desc := testLang.ToSyzLang(rev.config.HarnessID)
	if desc == nil {
		return fmt.Errorf("failed to transpile testlang into syzlang")
	}
	rev.desc = desc
	rev.harnessType = HarnessTypeBase
	if rev.hasCommands(desc) {
		rev.harnessType = HarnessTypeCommand
	}
	pseudoSyscall := syzlang.MakeAstCall(TestLangCallName, rev.getInputName())
	desc.AddNode(pseudoSyscall)
	rev.unflattenCommands(desc)
	if !rev.recoverDesc(desc) {
		return fmt.Errorf("failed to compile transpiled syzlang")
	}
	return nil
}

func (rev *Reverser) recoverDesc(desc *syzlang.Description) bool {
	errMsgs := []string{}
	errHdl := func(pos ast.Pos, msg string) {
		errMsgs = append(errMsgs, msg)
	}
	connectUnusedStructs := func(msg string) {
		prefixs := []string{"unused struct ", "unused union "}
		for _, prefix := range prefixs {
			if !strings.HasPrefix(msg, prefix) {
				continue
			}
			name := strings.TrimPrefix(msg, prefix)
			for _, node := range desc.NodeMap {
				if node, ok := node.(*ast.Struct); ok {
					for _, field := range node.Fields {
						if field.Name.Name != name {
							continue
						}
						used := false
						if field.Type.Ident == name {
							used = true
						}
						for _, typeArg := range field.Type.Args {
							if typeArg.Ident == name {
								used = true
							}
						}
						if used {
							fmt.Printf("%s is used\n", name)
							break
						}
						fmt.Printf("%s is unused\n", name)
						desc.RemoveTree(field.Type.Ident)
						for _, typeArg := range field.Type.Args {
							desc.RemoveTree(typeArg.Ident)
						}
						switch field.Type.Ident {
						case "array":
							typeArgs := field.Type.Args
							field.Type.Args = []*ast.Type{{Ident: name}}
							for _, typeArg := range typeArgs {
								if typeArg.Value > 0 {
									field.Type.Args = append(field.Type.Args, typeArg)
								}
							}
						default:
							field.Type.Ident = name
						}
					}
				}
			}
		}
	}
	for i := 0; i < 10; i++ {
		errMsgs = []string{}
		if rev.Compile(desc, errHdl) != nil {
			fmt.Println("Succeed to recover!")
			rev.desc = desc
			return true
		}
		for _, msg := range errMsgs {
			connectUnusedStructs(msg)
		}
	}
	removeUnused := func(msg string) {
		prefix := "unused "
		if !strings.HasPrefix(msg, prefix) {
			return
		}
		tokens := strings.Split(msg, " ")
		name := tokens[len(tokens)-1]
		desc.RemoveTree(name)
	}
	errMsgs = []string{}
	if rev.Compile(desc, errHdl) != nil {
		fmt.Println("Succeed to recover!")
		rev.desc = desc
		return true
	}
	for _, msg := range errMsgs {
		removeUnused(msg)
	}
	if rev.Compile(desc, nil) != nil {
		fmt.Println("Succeed to recover!")
		rev.desc = desc
		return true
	}
	return false
}

func (rev *Reverser) UseDefaultDescription() {
	desc := syzlang.NewDescription(rev.config.HarnessID)
	// syz_harness$()
	pseudoSyscall := syzlang.MakeAstCall(TestLangCallName, rev.getInputName())
	desc.AddNode(pseudoSyscall)
	// INPUT
	inputFields := []*ast.Field{}
	switch rev.harnessType {
	case HarnessTypeBase:
		astType := syzlang.MakeAstArrayType(nil)
		astField := syzlang.MakeAstField("field_0", astType, nil)
		inputFields = append(inputFields, astField)
	case HarnessTypeCommand:
		// COMMAND_CNT
		var pLenBaseType *string
		if rev.desc != nil {
			if input := rev.desc.FindNode(rev.getInputName()); input != nil {
				if input, ok := input.(*ast.Struct); ok {
					if len(input.Fields) > 0 &&
						input.Fields[0].Name.Name == rev.getCommandCountName() {
						field := input.Fields[0]
						if field.Type.Ident == "len" {
							for _, typeArg := range field.Type.Args {
								if strings.HasPrefix(typeArg.Ident, "int") {
									pLenBaseType = &typeArg.Ident
								}
							}
						}
					}
				}
			}
		}
		if pLenBaseType == nil {
			lenBaseType := "int8"
			pLenBaseType = &lenBaseType
		}
		astType := &ast.Type{
			Ident: "len",
			Args: []*ast.Type{
				{Ident: rev.getCommandName()},
				{Ident: *pLenBaseType},
			},
		}
		astField := syzlang.MakeAstField(rev.getCommandCountName(), astType, nil)
		inputFields = append(inputFields, astField)
		// COMMAND
		astType = &ast.Type{
			Ident: "array",
			Args:  []*ast.Type{{Ident: rev.getCommandName()}},
		}
		astField = syzlang.MakeAstField(rev.getCommandName(), astType, nil)
		inputFields = append(inputFields, astField)
		// This doesn't support splitting per each command
		cmdsName := syzlang.MakeUniqueName(rev.config.HarnessID)
		cmdsAstType := syzlang.MakeAstArrayType(nil)
		cmdsAstField := syzlang.MakeAstField("field_0", cmdsAstType, nil)
		cmdsAstFields := []*ast.Field{cmdsAstField}
		cmdsStruct := syzlang.MakeAstStruct(cmdsName, cmdsAstFields, nil, nil)
		desc.AddNode(cmdsStruct)
		cmdAstType := &ast.Type{Ident: cmdsName}
		cmdAstField := syzlang.MakeAstField(cmdsName, cmdAstType, nil)
		cmdAstFields := []*ast.Field{cmdAstField}
		cmdAstUnion := syzlang.MakeAstUnion(rev.getCommandName(), cmdAstFields, nil, nil)
		desc.AddNode(cmdAstUnion)
	default:
		fmt.Printf("Faield to handle %+v\n", rev.harnessType)
		panic("TODO")
	}
	input := syzlang.MakeAstStruct(rev.getInputName(), inputFields, nil, nil)
	desc.AddNode(input)
	rev.desc = desc
}

func (rev *Reverser) unflattenCommands(desc *syzlang.Description) {
	if rev.harnessType != HarnessTypeCommand {
		return
	}
	if cmds := desc.FindNode(rev.getCommandName()); cmds != nil {
		if cmds, ok := cmds.(*ast.Struct); ok {
			if !isFlattenedCommand(cmds) {
				return
			}
			desc.RenameNode(cmds.Name.Name, desc.MakeUniqueName())
			fields := []*ast.Field{
				{
					Name: syzlang.MakeAstIdent(cmds.Name.Name),
					Type: &ast.Type{Ident: cmds.Name.Name},
				},
			}
			cmds := syzlang.MakeAstStruct(rev.getCommandName(), fields, nil, nil)
			desc.AddNode(cmds)
		}
	}
}

func isFlattenedCommand(cmds *ast.Struct) bool {
	for _, cmd := range cmds.Fields {
		if cmd.Name.Name != cmd.Type.Ident || len(cmd.Type.Args) != 0 {
			return true
		}
	}
	return false
}

func (rev *Reverser) limitToSingleCommand(desc *syzlang.Description) *syzlang.Description {
	if rev.harnessType != HarnessTypeCommand {
		return desc
	}
	newDesc := syzlang.NewDescription(desc.ID)
	for _, node := range desc.NodeMap {
		if syzlang.GetAstName(node) != rev.getInputName() {
			// DO NOT clone node
			newDesc.AddNode(node)
			continue
		}
		node, ok := node.Clone().(*ast.Struct)
		if !ok {
			panic("TODO")
		}
		for _, field := range node.Fields {
			switch field.Name.Name {
			case rev.getCommandName():
				field.Type.Args = append(field.Type.Args, &ast.Type{Value: 1})
			case rev.getCommandCountName():
				field.Type.Ident = field.Type.Args[len(field.Type.Args)-1].Ident
				field.Type.Args = []*ast.Type{{Value: 1}}
			}
		}
		newDesc.AddNode(node)
	}
	return newDesc
}

func (rev *Reverser) Compile(desc *syzlang.Description, errHdl ast.ErrorHandler) *compiler.Prog {
	return syzlang.Compile(rev.Target, rev.config.SyzkallerDir, desc.Finalize(), errHdl)
}

func (rev *Reverser) SaveTo(path string) error {
	desc := rev.desc.Clone()
	if rev.harnessType == HarnessTypeCommand {
		rev.splitIntoCommands(desc)
	}
	rev.annotateCallType(desc)
	astDesc := desc.Finalize()
	ast.FormatWriter(os.Stdout, astDesc)
	if rev.Compile(desc, nil) == nil {
		return fmt.Errorf("failed to compile")
	}
	fmt.Printf("Saving to %s ...\n", path)
	return syzlang.SaveToFile(astDesc, path)
}

func (rev *Reverser) hasCommands(desc *syzlang.Description) bool {
	hasCmd, hasCmdCnt := false, false
	if input := desc.FindNode(rev.getInputName()); input != nil {
		if input, ok := input.(*ast.Struct); ok && !input.IsUnion {
			for _, field := range input.Fields {
				switch field.Name.Name {
				case rev.getCommandName():
					if field.Type.Ident == "array" {
						hasCmd = true
					}
				case rev.getCommandCountName():
					if field.Type.Ident == "len" {
						hasCmdCnt = true
					}
				}
			}
		}
	}
	return hasCmd && hasCmdCnt
}

func (rev *Reverser) splitIntoCommands(desc *syzlang.Description) {
	if cmds := desc.FindNode(rev.getCommandName()); cmds != nil {
		if cmds, ok := cmds.(*ast.Struct); ok {
			for _, cmd := range cmds.Fields {
				call := syzlang.MakeAstCall(TestLangCallName, cmd.Name.Name)
				desc.AddNode(call)
			}
		}
	}
	namesToRemove := []string{
		rev.getCallName(rev.getInputName()),
		rev.getInputName(),
		rev.getCommandName(),
	}
	for _, name := range namesToRemove {
		desc.RemoveNode(name)
	}
}

func (rev *Reverser) annotateCallType(desc *syzlang.Description) {
	for _, node := range desc.GetCalls() {
		newName := fmt.Sprintf("%s_type%d", TestLangCallName, rev.harnessType)
		newName = strings.Replace(node.Name.Name, TestLangCallName, newName, 1)
		node.CallName = newName
		desc.RenameNode(node.Name.Name, newName)
	}
}
