package reverse

import (
	"fmt"
	"sort"
	"strings"

	"github.com/google/syzkaller/pkg/ast"
	"github.com/google/syzkaller/prog"
	"github.com/google/syzkaller/tools/syz-reverser/syzlang"
	"github.com/google/syzkaller/tools/syz-reverser/testlang"
	"github.com/google/syzkaller/tools/syz-reverser/trace"
)

func (rev *Reverser) Reverse() {
	// FIXME: Break on certain condition
	for !rev.isDone() {
		descBak := rev.desc.Clone()
		desc := rev.limitToSingleCommand(rev.desc)
		rev.reverseOnce(desc)
		rev.iter++
		if err := rev.SaveTo(rev.config.OutputPath); err != nil {
			fmt.Println(err)
			rev.desc = descBak
		}
	}
}

func (rev *Reverser) isDone() bool {
	switch rev.harnessType {
	case HarnessTypeBase:
		if input, ok := rev.desc.FindNode(rev.getInputName()).(*ast.Struct); ok {
			if !rev.isStructDone(input) {
				return false
			}
		}
	case HarnessTypeCommand:
		if cmds, ok := rev.desc.FindNode(rev.getCommandName()).(*ast.Struct); ok {
			for _, cmd := range cmds.Fields {
				if cmd, ok := rev.desc.FindNode(cmd.Name.Name).(*ast.Struct); ok {
					if !rev.isStructDone(cmd) {
						return false
					}
				}
			}
		}
	}
	return true
}

func (rev *Reverser) isStructDone(astStruct *ast.Struct) bool {
	for _, field := range astStruct.Fields {
		done := false
		for _, comment := range field.Comments {
			if comment.Text == testlang.DoneComment {
				done = true
				break
			}
		}
		if !done {
			fmt.Printf("%s.%s is not done ...\n", astStruct.Name.Name, field.Name.Name)
			return false
		}
	}
	return true
}

// FIXME: DO NOT use redundant description
func (rev *Reverser) addNode(desc *syzlang.Description, node ast.Node) {
	desc.AddNode(node)
	if desc != rev.desc {
		rev.desc.AddNode(node)
	}
}

func (rev *Reverser) removeNode(desc *syzlang.Description, node ast.Node) {
	nodeName := syzlang.GetAstName(node)
	desc.RemoveNode(nodeName)
	if desc != rev.desc {
		rev.desc.RemoveNode(nodeName)
	}
}

func (rev *Reverser) removeType(desc *syzlang.Description, t *ast.Type) {
	desc.RemoveType(t)
	if desc != rev.desc {
		rev.desc.RemoveType(t)
	}
}

func (rev *Reverser) reverseOnce(desc *syzlang.Description) {
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("Recovered from", r)
		}
	}()
	astCallNode := desc.FindNode(rev.getCallName(rev.getInputName()))
	if astCallNode == nil {
		return
	}
	astCall, ok := astCallNode.(*ast.Call)
	if !ok {
		return
	}
	descProg := rev.Compile(desc, nil)
	if descProg == nil {
		return
	}
	blobArgs := []prog.Arg{}
	// TODO: Remove already completed struct so that it is generated no more
	blobArg := rev.GenSampleBlobArg(descProg)
	if blobArg == nil {
		return
	}
	blobArgs = append(blobArgs, blobArg)
	blobArgs = append(blobArgs, rev.mutateBlobArg(blobArg))
	blobs := [][]byte{}
	traces := []*trace.Trace{}
	for _, blobArg := range blobArgs {
		blob := rev.GenBlob(blobArg)
		fmt.Println(len(blob))
		fmt.Println(blob)
		blobs = append(blobs, blob)
		blobPath, err := rev.SaveBlob(blob)
		if err != nil {
			fmt.Println(err)
			return
		}
		t, err := rev.tracer.GenTrace(*blobPath)
		if err != nil {
			fmt.Println(err)
			return
		}
		traces = append(traces, t)
	}
	captures := make([]map[trace.CaptureSource][]byte, 2)
	// FIXME: Compare only once
	for i := 0; i < 2; i++ {
		_, captures[i] = traces[i].MatchWith(traces[1-i])
	}
	// FIXME: Remove
	typeInfs := map[commonSubstr][]trace.CaptureSource{}
	for src := range captures[0] {
		if _, ok := captures[1][src]; ok {
			fmt.Println("=============================")
			fmt.Printf("%+v %s\n", src, src.Syscall.Name)
			// Find LCS between blob and its capture
			lcsSeen := make(map[commonSubstr]uint)
			for i := 0; i < 2; i++ {
				mem := captures[i][src]
				fmt.Printf("Finding LCS between blobs[%d] and %+v\n", i, mem)
				// TODO: Find mem[::-1] too
				// FIXME: De-duplicate LCSes after trim
				for _, lcs := range getLongestCommonSubstr(blobs[i], mem) {
					fmt.Printf("Found LCS: %+v\n", lcs)
					lcs = trimCommonLCS(lcs, blobs[0], blobs[1])
					if lcs.s1.len() == 0 || lcs.s2.beg != 0 {
						fmt.Printf("Ignoring LCS %+v\n", lcs)
						continue
					}
					lcsSeen[lcs] |= 1 << i
				}
			}
			// Infer type for common LCS
			for lcs, bitmap := range lcsSeen {
				if bitmap != 0b11 {
					continue
				}
				fmt.Printf("Found common LCS %+v\n", lcs)
				typeInfs[lcs] = append(typeInfs[lcs], src)
			}
		}
	}
	lcses := []commonSubstr{}
	for lcs := range typeInfs {
		lcses = append(lcses, lcs)
	}
	sort.Slice(lcses, func(i, j int) bool {
		return lcses[i].s1.len() > lcses[j].s1.len()
	})
	inferMap := map[*ast.Field]map[*ast.Type]*uint64{}
	for _, lcs := range lcses {
		beg, end := uint64(lcs.s1.beg), uint64(lcs.s1.end)
		mem := blobs[0][beg:end]
		fmt.Printf("Trying to infer mem %+v at blobs[0][%d:%d] ...\n", mem, beg, end)
		typeMap := map[prog.Type]map[string]bool{}
		for _, src := range typeInfs[lcs] {
			comment := fmt.Sprintf("from %dth arg of %s", src.ArgIdx, src.Syscall.Name)
			if _, ok := typeMap[src.Type]; !ok {
				typeMap[src.Type] = map[string]bool{}
			}
			typeMap[src.Type][comment] = true
		}
		rev.inferType(&prog.ArgCtx{}, beg, end, blobArg, astCall.Args[0], typeMap, desc, false, inferMap)
	}
	newlyInferred := false
	for astField, astTypes := range inferMap {
		origType := astField.Clone().(*ast.Field).Type
		var origAstUnion *ast.Struct
		if astUnion, ok := desc.FindNode(origType.Ident).(*ast.Struct); ok && astUnion.IsUnion {
			origAstUnion = astUnion
			randomFieldIdxs := []int{}
			for i, astField := range astUnion.Fields {
				isRandom := false
				for _, astComment := range astField.Comments {
					if astComment.Text == testlang.RandomComment {
						isRandom = true
						break
					}
				}
				if isRandom {
					randomFieldIdxs = append(randomFieldIdxs, i)
				}
			}
			// TODO: Restore ignored random fields on save
			for _, i := range randomFieldIdxs {
				astUnion.Fields[i] = astUnion.Fields[len(astUnion.Fields)-1]
				astUnion.Fields = astUnion.Fields[:len(astUnion.Fields)-1]
			}
		}
		astTypeMap := map[*ast.Type]map[string]bool{origType: nil}
		var pSize *uint64
		for astType, size := range astTypes {
			astTypeMap[astType] = nil
			// All size should be the same
			pSize = size
		}
		astUnion := rev.unionAstTypes(desc, astTypeMap, pSize)
		if !newlyInferred &&
			desc.HashAstTypeForStruct(astUnion) != desc.HashAstTypeForStruct(origAstUnion) {
			newlyInferred = true
		}
		newAstType := syzlang.MakeAstType(nil, nil, &astUnion.Name.Name, nil, nil)
		astField.Type = newAstType
		marked := false
		for _, astComment := range astField.Comments {
			if astComment.Text == testlang.DoneComment {
				marked = true
			}
		}
		if !marked {
			fmt.Printf("%s is done!\n", astField.Name.Name)
			testlang.MarkFieldDone(astField)
		}
	}
	if !newlyInferred {
		if err := rev.RemoveBlob(); err != nil {
			fmt.Println(err)
		}
	}
}

func trimCommonLCS(lcs commonSubstr, s1, s2 []byte) commonSubstr {
	beg, end := lcs.s1.beg, lcs.s1.end
	// Trim beginning
	for beg < end && s1[beg] == s2[beg] {
		beg++
	}
	if lcs.s1.beg != beg {
		fmt.Printf("Trimmed common LCS %+v at [%d:%d]\n", s1[lcs.s1.beg:beg], lcs.s1.beg, beg)
		lcs.s2.beg += beg - lcs.s1.beg
		lcs.s1.beg = beg
	}
	// Trim end
	for beg < end && s1[end-1] == s2[end-1] {
		end--
	}
	if lcs.s1.end != end {
		fmt.Printf("Trimmed common LCS %+v at [%d:%d]\n", s1[end:lcs.s1.end], end, lcs.s1.end)
		lcs.s2.end += end - lcs.s1.end
		lcs.s1.end = end
	}
	return lcs
}

// FIXME: If we modify AST, it won't be coherent with prog.Arg anymore.
// This is based on prog.ForeachSubArg().
func (rev *Reverser) inferType(ctx *prog.ArgCtx, memBeg, memEnd uint64, arg prog.Arg, astNode ast.Node, typeMap map[prog.Type]map[string]bool, desc *syzlang.Description, isParentUnionVarLen bool, inferMap map[*ast.Field]map[*ast.Type]*uint64) *ast.Type {
	fmt.Println(strings.Repeat("=", 100))
	fmt.Printf("node: %s (%T) %+v\n", syzlang.GetAstName(astNode), astNode, astNode)
	fmt.Printf("arg: (%T) (%T) (size: %d) (offset: %d) %+v\n", arg, arg.Type(), arg.Size(), ctx.Offset, arg)
	fmt.Printf("ctx: %+v\n", ctx)
	ctx0 := *ctx
	defer func() { *ctx = ctx0 }()
	if ctx.Stop {
		return nil
	}
	switch a := arg.(type) {
	case *prog.DataArg:
		argBeg, argEnd := ctx.Offset, ctx.Offset+arg.Size()
		if !(argBeg == memBeg && memEnd <= argEnd) {
			return nil
		}
		fmt.Printf("Matched with blob[%d:%d]\n", memBeg, memEnd)
		isVarLen := isParentUnionVarLen || a.Type().Varlen()
		newType := rev.insertType(desc, isVarLen, typeMap, ctx.Offset, ctx.Offset+arg.Size(), memBeg, memEnd)
		return newType
	case *prog.GroupArg:
		overlayField := 0
		if typ, ok := a.Type().(*prog.StructType); ok {
			ctx.Parent = &a.Inner
			ctx.Fields = typ.Fields
			overlayField = typ.OverlayField
		}
		var totalSize uint64
		for i, arg1 := range a.Inner {
			if i == overlayField {
				ctx.Offset = ctx0.Offset
			}
			fieldAstNode := matchGroupArg(a, desc, astNode, i)
			if fieldAstNode == nil {
				continue
			}
			newAstType := rev.inferType(ctx, memBeg, memEnd, arg1, fieldAstNode, typeMap, desc, false, inferMap)
			if newAstType != nil {
				var astField *ast.Field
				var fieldArg prog.Arg
				switch astNode := astNode.(type) {
				case *ast.Struct:
					astField = astNode.Fields[i]
					fieldArg = arg1
				// array[]
				case *ast.Field:
					astField = astNode
					fieldArg = a
				default:
					fmt.Printf("Failed to handle %T\n", astNode)
					panic("TODO")
				}
				if astField != nil && fieldArg != nil {
					var pSize *uint64
					if !fieldArg.Type().Varlen() {
						size := fieldArg.Type().Size()
						pSize = &size
					}
					if _, ok := inferMap[astField]; !ok {
						inferMap[astField] = map[*ast.Type]*uint64{}
					}
					inferMap[astField][newAstType] = pSize
				}
			}
			size := arg1.Size()
			ctx.Offset += size
			if totalSize < ctx.Offset {
				totalSize = ctx.Offset - ctx0.Offset
			}
		}
		if true {
			claimedSize := a.Size()
			varlen := a.Type().Varlen()
			if varlen && totalSize > claimedSize || !varlen && totalSize != claimedSize {
				panic(fmt.Sprintf("bad group arg size %v, should be <= %v for %#v type %#v",
					totalSize, claimedSize, a, a.Type().Name()))
			}
		}
	case *prog.PointerArg:
		if a.Res != nil {
			ctx.Base = a
			ctx.Offset = 0
			astNode := matchPointerArg(a, desc, astNode)
			return rev.inferType(ctx, memBeg, memEnd, a.Res, astNode, typeMap, desc, false, inferMap)
		}
	case *prog.UnionArg:
		// TODO: Use result value of inferType()
		astNode := matchUnionArg(a, desc, astNode)
		return rev.inferType(ctx, memBeg, memEnd, a.Option, astNode, typeMap, desc, a.Type().Varlen(), inferMap)
	}
	return nil
}

// [beg:end)
func (rev *Reverser) insertType(desc *syzlang.Description, isVarLen bool, typeMap map[prog.Type]map[string]bool, boundBeg, boundEnd, insertBeg, insertEnd uint64) *ast.Type {
	astFields := []*ast.Field{}
	if insertBeg-boundBeg > 0 {
		size := insertBeg - boundBeg
		astArrayType := syzlang.MakeAstArrayType(&size)
		fieldName := fmt.Sprintf("field_%d", len(astFields))
		astField := syzlang.MakeAstField(fieldName, astArrayType, nil)
		astFields = append(astFields, astField)
	}
	var pSize *uint64
	if !isVarLen {
		size := insertEnd - insertBeg
		pSize = &size
	}
	astUnion := rev.unionTypes(desc, typeMap, pSize)
	if astUnion == nil {
		return nil
	}
	newAstType := syzlang.MakeAstType(nil, nil, &astUnion.Name.Name, nil, nil)
	fieldName := fmt.Sprintf("field_%d", len(astFields))
	astField := syzlang.MakeAstField(fieldName, newAstType, nil)
	astFields = append(astFields, astField)
	if boundEnd-insertEnd > 0 {
		var astArrayType *ast.Type
		if isVarLen {
			astArrayType = syzlang.MakeAstArrayType(nil)
		} else {
			size := boundEnd - insertEnd
			astArrayType = syzlang.MakeAstArrayType(&size)
		}
		fieldName := fmt.Sprintf("field_%d", len(astFields))
		astField := syzlang.MakeAstField(fieldName, astArrayType, nil)
		astFields = append(astFields, astField)
	}
	if len(astFields) > 1 {
		structName := rev.makeUniqueName()
		var pSize *uint64
		if !isVarLen {
			size := boundEnd - boundBeg
			pSize = &size
		}
		astStruct := syzlang.MakeAstStruct(structName, astFields, nil, pSize)
		rev.addNode(desc, astStruct)
		newAstType = syzlang.MakeAstType(nil, nil, &astStruct.Name.Name, nil, nil)
	}
	return newAstType
}

func (rev *Reverser) unionTypes(desc *syzlang.Description, typeMap map[prog.Type]map[string]bool, size *uint64) *ast.Struct {
	astTypeMap := map[*ast.Type]map[string]bool{}
	for typ, comments := range typeMap {
		if size != nil {
			if typ.Varlen() {
				fmt.Printf("Ignoring variable length-ed %T ...\n", typ)
				continue
			}
			minTypeSize := syzlang.GetMinSizeOf(typ)
			if *size < minTypeSize {
				fmt.Printf("Ignoring unfit type %T (%d) into %d ...\n", typ, minTypeSize, *size)
				continue
			}
		}
		astType, newNodes := rev.decompiler.DecompileType(typ, size)
		if astType == nil {
			continue
		}
		astTypeMap[astType] = comments
		for _, node := range newNodes {
			rev.addNode(desc, node)
		}
	}
	astUnion := rev.unionAstTypes(desc, astTypeMap, size)
	return astUnion
}

func (rev *Reverser) unionAstTypes(desc *syzlang.Description, typeMap map[*ast.Type]map[string]bool, size *uint64) *ast.Struct {
	typeHashMap := map[uint64][]*ast.Type{}
	astFields := []*ast.Field{}
	addField := func(astType *ast.Type, astComments []*ast.Comment) {
		typeHash := desc.HashAstTypeForType(astType)
		if _, ok := typeHashMap[typeHash]; ok {
			fmt.Println("Removing duplicated nodes")
			rev.removeType(desc, astType)
			return
		}
		typeHashMap[typeHash] = append(typeHashMap[typeHash], astType)
		fieldName := fmt.Sprintf("field_%d", len(astFields))
		astField := syzlang.MakeAstField(fieldName, astType, astComments)
		astFields = append(astFields, astField)
	}
	for astType, comments := range typeMap {
		astComments := []*ast.Comment{}
		for comment := range comments {
			astComment := syzlang.MakeAstComment(comment)
			astComments = append(astComments, astComment)
		}
		astNode := desc.FindNode(astType.Ident)
		if astUnion, ok := astNode.(*ast.Struct); ok && astUnion.IsUnion {
			fmt.Printf("Removing existing union %s\n", astUnion.Name.Name)
			rev.removeNode(desc, astUnion)
			for _, field := range astUnion.Fields {
				addField(field.Type, field.Comments)
			}
		} else {
			addField(astType, astComments)
		}
	}
	if len(astFields) == 0 {
		return nil
	}
	unionName := rev.makeUniqueName()
	astUnion := syzlang.MakeAstUnion(unionName, astFields, nil, size)
	rev.addNode(desc, astUnion)
	return astUnion
}

func matchPointerArg(arg *prog.PointerArg, desc *syzlang.Description, astNode ast.Node) ast.Node {
	switch astNode := astNode.(type) {
	case *ast.Field:
		if astNode.Type.Ident == "ptr" {
			for _, arg := range astNode.Type.Args {
				if astNode := desc.FindNode(arg.Ident); astNode != nil {
					return astNode
				}
			}
		}
	default:
		fmt.Printf("Failed to handle %T\n", astNode)
		panic("TODO")
	}
	return nil
}

func matchGroupArg(arg *prog.GroupArg, desc *syzlang.Description, astNode ast.Node, idx int) ast.Node {
	switch astNode := astNode.(type) {
	// prog.StructType
	case *ast.Struct:
		if !astNode.IsUnion {
			return astNode.Fields[idx]
		}
	// prog.ArrayType
	case *ast.Field:
		switch astNode.Type.Ident {
		case "array":
			for _, arg := range astNode.Type.Args {
				if arg.Ident == "void" {
					return nil
				}
				if astNode := desc.FindNode(arg.Ident); astNode != nil {
					return astNode
				}
			}
			panic("TODO")
		default:
			if astNode := desc.FindNode(astNode.Type.Ident); astNode != nil {
				return matchGroupArg(arg, desc, astNode, idx)
			}
			fmt.Printf("Failed to handle %s\n", astNode.Type.Ident)
			panic("TODO")
		}
	default:
		fmt.Printf("Failed to handle %T\n", astNode)
		panic("TODO")
	}
	return nil
}

func matchUnionArg(arg *prog.UnionArg, desc *syzlang.Description, astNode ast.Node) ast.Node {
	switch astNode := astNode.(type) {
	case *ast.Struct:
		if astNode.IsUnion {
			astField := astNode.Fields[arg.Index]
			if astNode := desc.FindNode(astField.Name.Name); astNode != nil {
				return astNode
			}
			return astField
		}
	case *ast.Field:
		astStruct := desc.FindNode(arg.Type().Name())
		return matchUnionArg(arg, desc, astStruct)
	default:
		fmt.Printf("Failed to handle %T\n", astNode)
		panic("TODO")
	}
	return nil
}
