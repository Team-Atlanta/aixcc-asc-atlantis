package syzlang

import (
	"path/filepath"

	"github.com/google/syzkaller/pkg/ast"
	"github.com/google/syzkaller/pkg/compiler"
	"github.com/google/syzkaller/prog"
	"github.com/google/syzkaller/sys/targets"
)

func Compile(target *prog.Target, srcDir string, desc *ast.Description, errHdl ast.ErrorHandler) *compiler.Prog {
	errHdl = makeCompileErrorHandler(errHdl)
	osDir := filepath.Join(srcDir, "sys", target.OS)
	descs := ast.ParseGlob(filepath.Join(osDir, "*.txt"), errHdl)
	if descs == nil {
		return nil
	}
	descs.Nodes = append(descs.Nodes, desc.Nodes...)
	constFilePath := filepath.Join(osDir, "*.const")
	constFile := compiler.DeserializeConstFile(constFilePath, errHdl)
	if constFile == nil {
		return nil
	}
	consts := constFile.Arch(target.Arch)
	compileTarget := targets.List[target.OS][target.Arch]
	descProg := compiler.Compile(descs, consts, compileTarget, errHdl)
	if descProg == nil {
		return nil
	}
	prog.RestoreLinks(descProg.Syscalls, descProg.Resources, descProg.Types)
	return descProg
}

func makeCompileErrorHandler(errHdl ast.ErrorHandler) ast.ErrorHandler {
	return func(pos ast.Pos, msg string) {
		if pos.File != "" {
			return
		}
		ast.LoggingHandler(pos, msg)
		if errHdl != nil {
			errHdl(pos, msg)
		}
	}
}
