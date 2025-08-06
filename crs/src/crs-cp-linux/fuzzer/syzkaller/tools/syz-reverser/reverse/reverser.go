package reverse

import (
	"encoding/binary"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/google/syzkaller/prog"
	"github.com/google/syzkaller/tools/syz-reverser/syzlang"
	"github.com/google/syzkaller/tools/syz-reverser/testlang"
	"github.com/google/syzkaller/tools/syz-reverser/trace"
	"github.com/google/uuid"
)

type HarnessType int

const (
	HarnessTypeUnknown = iota
	HarnessTypeBase
	HarnessTypeCommand
)

type Reverser struct {
	config     *ReverserConfig
	Target     *prog.Target
	randSrc    rand.Source
	tracer     *trace.SkyTracer
	decompiler *syzlang.Decompiler
	// TODO: Decide to leave Reverser stateful or not
	harnessType HarnessType
	desc        *syzlang.Description
	iter        int
}

type ReverserConfig struct {
	TargetOS   string
	TargetArch string

	SyzkallerDir string
	WorkDir      string
	OutputPath   string

	HarnessID   string
	HarnessPath string
}

func (cfg ReverserConfig) New(tracerCfg *trace.SkyTracerConfig) (*Reverser, error) {
	target, err := prog.GetTarget(cfg.TargetOS, cfg.TargetArch)
	if err != nil {
		return nil, err
	}
	tracer, err := tracerCfg.New(cfg.HarnessPath)
	if err != nil {
		return nil, err
	}
	decompiler := &syzlang.Decompiler{ID: cfg.HarnessID}
	randSeed := time.Now().UnixNano()
	fmt.Printf("The random seed is %d.\n", randSeed)
	rev := Reverser{
		config:     &cfg,
		Target:     target,
		randSrc:    rand.NewSource(randSeed),
		tracer:     tracer,
		decompiler: decompiler,
	}
	return &rev, nil
}

func (rev *Reverser) GetByteOrder() binary.ByteOrder {
	if rev.Target.LittleEndian {
		return binary.LittleEndian
	} else {
		return binary.BigEndian
	}
}

func (rev *Reverser) getInputName() string {
	return testlang.MakeUniqueName(rev.config.HarnessID, testlang.InputName)
}

func (rev *Reverser) getCommandName() string {
	return testlang.MakeUniqueName(rev.config.HarnessID, testlang.CommandName)
}

func (rev *Reverser) getCommandCountName() string {
	return testlang.MakeUniqueName(rev.config.HarnessID, testlang.CommandCountName)
}

func (rev *Reverser) getCallName(inputName string) string {
	return syzlang.MakeAstCallName(TestLangCallName, inputName)
}

func (rev *Reverser) makeUniqueName() string {
	id := uuid.NewString()
	id = strings.Replace(id, "-", "_", -1)
	return testlang.MakeUniqueName(rev.config.HarnessID, id)
}
