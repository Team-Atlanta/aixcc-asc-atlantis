package main

import (
	"flag"
	"fmt"
	"os"

	_ "github.com/google/syzkaller/sys/linux/gen"
	"github.com/google/syzkaller/sys/targets"

	"github.com/google/syzkaller/tools/syz-reverser/reverse"
	"github.com/google/syzkaller/tools/syz-reverser/testlang"
	"github.com/google/syzkaller/tools/syz-reverser/trace"
)

var (
	syzkallerDir    = flag.String("syzkaller", "", "Path to the syzkaller dir")
	tracerPath      = flag.String("tracer", "", "Path to skytracer.py")
	tracerKernelDir = flag.String("kernel", "", "Path to the kernel dir for SkyTracer")
	traceTimeout    = flag.Uint("trace_timeout", 60, "Timeout for each trace generation in seconds")
	workDir         = flag.String("work", "", "Path to the work dir")
	harnessID       = flag.String("harness_id", "", "ID of the harness")
	harnessPath     = flag.String("harness", "", "Path to the harness file")
	testlangPath    = flag.String("testlang", "", "Path to the testlang file")
	outputPath      = flag.String("output", "", "Path to the output file")
)

// TODO: DO NOT limit
const (
	TargetOS        = targets.Linux
	TargetArch      = targets.AMD64
	FallbackDescFmt = `
syz_harness_type1$%s_fallback(buf ptr[in, %s_fallback], len bytesize[buf])

%s_fallback {
        field_0 array[int8]
} [packed]
 `
)

func main() {
	// TODO: Check unset flags
	flag.Parse()

	defer func() {
		if r := recover(); r != nil {
			fmt.Println("Recovered from", r)
			useFallbackDescription(*harnessID, *outputPath)
		}
	}()

	tracerCfg := trace.SkyTracerConfig{
		TracerPath: *tracerPath,
		KernelDir:  *tracerKernelDir,
		WorkDir:    *workDir,
		Timeout:    *traceTimeout,
	}
	revCfg := reverse.ReverserConfig{
		TargetOS:     TargetOS,
		TargetArch:   TargetArch,
		SyzkallerDir: *syzkallerDir,
		WorkDir:      *workDir,
		OutputPath:   *outputPath,
		HarnessID:    *harnessID,
		HarnessPath:  *harnessPath,
	}
	rev, err := revCfg.New(&tracerCfg)
	if err != nil {
		panic(err)
	}

	testLang := testlang.ParseFile(testlangPath)
	fmt.Println(testLang)
	if err = rev.Transpile(testLang); err != nil {
		rev.UseDefaultDescription()
	}
	if err := rev.SaveTo(*outputPath); err != nil {
		panic(err)
	}

	trace.InitSyzlangMap(rev.Target)

	rev.Reverse()
}

func useFallbackDescription(harnessID, path string) {
	fmt.Println("Saving fallback description")
	file, err := os.Create(path)
	if err != nil {
		panic(err)
	}
	fallbackDesc := fmt.Sprintf(FallbackDescFmt, harnessID, harnessID, harnessID)
	fmt.Println(fallbackDesc)
	file.Write([]byte(fallbackDesc))
	file.Close()
	os.Exit(7)
}
