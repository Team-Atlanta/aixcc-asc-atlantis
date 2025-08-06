package reverse

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"os"
	"path/filepath"

	"github.com/google/syzkaller/pkg/compiler"
	"github.com/google/syzkaller/prog"
)

// This assumes `syz_harness$INPUT(blob ptr[in, *], ...)`.
func (rev *Reverser) GenSampleBlobArg(descProg *compiler.Prog) prog.Arg {
	for _, syscall := range descProg.Syscalls {
		if syscall.Name != rev.getCallName(rev.getInputName()) {
			continue
		}
		for {
			sampleSyscall := rev.genSampleSyscall(syscall)
			if len(sampleSyscall.Args) == 0 {
				continue
			}
			blobArg := sampleSyscall.Args[0]
			failed := false
			firstDataArgBytes := map[byte]bool{}
			prog.ForeachSubArg(blobArg, func(arg prog.Arg, ctx *prog.ArgCtx) {
				if arg, ok := arg.(*prog.DataArg); ok {
					if len(arg.Data()) == 0 {
						return
					}
					b := arg.Data()[0]
					if _, ok := firstDataArgBytes[b]; ok {
						failed = true
						ctx.Stop = true
						return
					}
					firstDataArgBytes[b] = true
				}
			})
			if failed {
				fmt.Println("Regenerating blob ...")
				continue
			}
			return blobArg
		}
	}
	return nil
}

func (rev *Reverser) mutateBlobArg(arg prog.Arg) prog.Arg {
	switch arg := arg.(type) {
	case *prog.DataArg:
		newData := []byte{}
		for _, b := range arg.Data() {
			newData = append(newData, ^b)
		}
		return prog.MakeDataArg(arg.Type(), arg.Dir(), newData)
	case *prog.GroupArg:
		newInner := []prog.Arg{}
		for _, innerArg := range arg.Inner {
			newInner = append(newInner, rev.mutateBlobArg(innerArg))
		}
		return prog.MakeGroupArg(arg.Type(), arg.Dir(), newInner)
	case *prog.PointerArg:
		if arg.Res == nil {
			return arg
		}
		newArg := rev.mutateBlobArg(arg.Res)
		return prog.MakePointerArg(arg.Type(), arg.Dir(), arg.Address, newArg)
	case *prog.UnionArg:
		newOption := rev.mutateBlobArg(arg.Option)
		return prog.MakeUnionArg(arg.Type(), arg.Dir(), newOption, arg.Index)
	}
	return arg
}

func (rev *Reverser) genSampleSyscall(syscall *prog.Syscall) *prog.Call {
	sampleProg := rev.Target.GenSampleProg(syscall, rev.randSrc)
	if len(sampleProg.Calls) != 1 {
		panic("TODO")
	}
	return sampleProg.Calls[0]
}

func (rev *Reverser) GenBlob(blobArg prog.Arg) []byte {
	byteOrder := rev.GetByteOrder()
	blob := new(bytes.Buffer)
	prog.ForeachSubArg(blobArg, func(arg prog.Arg, ctx *prog.ArgCtx) {
		// TODO: Assert ctx.Offset
		switch arg := arg.(type) {
		case *prog.ConstArg:
			switch arg.Size() {
			case 1:
				binary.Write(blob, byteOrder, uint8(arg.Val))
			case 2:
				binary.Write(blob, byteOrder, uint16(arg.Val))
			case 4:
				binary.Write(blob, byteOrder, uint32(arg.Val))
			case 8:
				binary.Write(blob, byteOrder, uint64(arg.Val))
			}
		case *prog.DataArg:
			blob.Write(arg.Data())
		}
	})
	return blob.Bytes()
}

func (rev *Reverser) SaveBlob(blob []byte) (*string, error) {
	seedDir := filepath.Join(rev.config.WorkDir, "seeds")
	err := os.Mkdir(seedDir, 0750)
	if err != nil && !os.IsExist(err) {
		return nil, err
	}
	blobName := fmt.Sprintf("%d.bin", rev.iter)
	blobPath := filepath.Join(seedDir, blobName)
	blobFile, err := os.Create(blobPath)
	if err != nil {
		return nil, err
	}
	defer blobFile.Close()
	_, err = blobFile.Write(blob)
	if err != nil {
		return nil, err
	}
	return &blobPath, nil
}

func (rev *Reverser) RemoveBlob() error {
	seedDir := filepath.Join(rev.config.WorkDir, "seeds")
	blobName := fmt.Sprintf("%d.bin", rev.iter)
	blobPath := filepath.Join(seedDir, blobName)
	return os.Remove(blobPath)
}
