package main

import (
	"bytes"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func printSeperator() {
	for i := 0; i < 40; i++ {
		fmt.Print("*")
	}
	fmt.Println()
}

func runCommand(cmd *exec.Cmd, desc string) {
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	printSeperator()
	fmt.Printf("Command: %s\n", cmd.String())
	err := cmd.Run()

	if err != nil {
		fmt.Printf("Error running command: %s \n", err)
		fmt.Print(stderr.String())
		fmt.Printf("skytracer failed at stage: %s \n", desc)
		fmt.Println("Exiting...")
		printSeperator()
		os.Exit(-1)
	}

	fmt.Println("Command Output:")
	fmt.Println(stdout.String())
	printSeperator()
}

var TRACER_INSTRUMENT string = `
static void skytracer_init(int argc, char **argv, char **envp) {
asm("mov $0xf000, %rax; syscall");
}

static void skytracer_fini(void) {
asm("mov $0xf001, %rax; syscall");
}

__attribute__((section(".init_array"), used)) static typeof(skytracer_init) *init_p = skytracer_init;
__attribute__((section(".fini_array"), used)) static typeof(skytracer_fini) *fini_p = skytracer_fini;
`

func createPatchedTestHarness(testHarness, patchedTestHarness string) string {
	source, err := os.ReadFile(testHarness)
	if err != nil {
		fmt.Println("Error reading test harness src:", err)
		os.Exit(-1)
	}

	newSource := string(source) + TRACER_INSTRUMENT

	err = os.WriteFile(patchedTestHarness, []byte(newSource), 0644)
	if err != nil {
		fmt.Println("Error creating patched test harness:", err)
		os.Exit(-1)
	}

	cmd := exec.Command("gcc", patchedTestHarness, "-static", "-o", patchedTestHarness[:len(patchedTestHarness)-2])
	runCommand(cmd, "Build test harness")

	fmt.Printf("Patched test harness src created at : %s \n", patchedTestHarness)

	return patchedTestHarness[:len(patchedTestHarness)-2]
}

func createSymtabs(vmlinux string) string {
	vmlinuxSymtabs := fmt.Sprintf("%s.symtabs", vmlinux)

	vmlinuxFileInfo, err := os.Stat(vmlinux)
	if err != nil {
		fmt.Printf("vmlinux file does not exist: %s\n", err)
		os.Exit(-1)
	}

	symtabsFileInfo, err := os.Stat(vmlinuxSymtabs)
	if err == nil {
		vmlinuxTime := vmlinuxFileInfo.ModTime()
		symtabsTime := symtabsFileInfo.ModTime()
		if vmlinuxTime.Before(symtabsTime) {
			fmt.Println("No need to create new symtabs file")
			return vmlinuxSymtabs
		}
	}

	f, err := os.Create(vmlinuxSymtabs)
	if err != nil {
		fmt.Println("Error creating symtabs file:", err)
		os.Exit(-1)
	}
	defer f.Close()

	cmd := exec.Command("objdump", "-t", vmlinux)
	output, err := cmd.Output()
	if err != nil {
		fmt.Println("Error running objdump:", err)
		os.Exit(-1)
	}

	lines := strings.Split(string(output), "\n")
	lines = lines[1 : len(lines)-1]
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if !strings.Contains(line, ".text") {
			continue
		}
		tokens := strings.Fields(line)
		if len(tokens) < 2 {
			continue
		}
		addr := tokens[0]
		name := tokens[len(tokens)-1]
		fmt.Fprintf(f, "%s, %s\n", name, addr)
	}
	return vmlinuxSymtabs
}

func runVirtme(linuxKernel, qemuBin, workdir, vmlinuxSymtabs, traceOutputPath, patchedHarness, testBlob string) {
	testBlobFilename := filepath.Base(testBlob)

	cmd := exec.Command("cp", testBlob, workdir+testBlobFilename)
	runCommand(cmd, "Copy blob to workdir")

	script := workdir + "trace.sh"
	file, err := os.Create(script)
	if err != nil {
		fmt.Println("Error creating script file:", err)
		os.Exit(-1)
	}

	fmt.Fprintln(file, "#!/bin/bash")
	fmt.Fprintln(file, patchedHarness+" "+workdir+testBlobFilename)
	file.Close()

	cmd = exec.Command("chmod", "755", script)
	runCommand(cmd, "Chmod script file to execute")

	cmdAndArgs := []string{"virtme-run", "--memory", "2G", "--mods=auto", "--kopt", "panic=-1"}
	cmdAndArgs = append(cmdAndArgs, "--kopt", "nokaslr")
	cmdAndArgs = append(cmdAndArgs, "--kimg", linuxKernel)
	cmdAndArgs = append(cmdAndArgs, "--qemu-bin", qemuBin)
	cmdAndArgs = append(cmdAndArgs, "--rwdir", workdir+"="+workdir)
	cmdAndArgs = append(cmdAndArgs, "--disable-kvm")
	cmdAndArgs = append(cmdAndArgs, "--script-sh", script)
	cmd = exec.Command(cmdAndArgs[0], cmdAndArgs[1:]...)
	cmd.Env = append(os.Environ(), "SYMTABS="+vmlinuxSymtabs, "SKYTRACE_OUT="+traceOutputPath)
	runCommand(cmd, "virtme-run with script")
}

func main() {
	var (
		testHarnessName = flag.String("harness", "", "test harness src file name")
		testBlobName    = flag.String("blob", "", "test blob name")
	)

	flag.Parse()
	flag.VisitAll(func(f *flag.Flag) {
		if f.DefValue == f.Value.String() {
			fmt.Printf("Error: Flag %s is required.\n", f.Name)
			os.Exit(-1)
		}
	})

	testHarnessPrefix := "/cp-linux/src/test_harnesses/"
	testHarness := testHarnessPrefix + *testHarnessName

	testBlobPrefix := "/cp-linux/exemplar_only/blobs/"
	testBlob := testBlobPrefix + *testBlobName

	traceDir := "/tracer/"
	trace := traceDir + *testHarnessName + ".trace"
	patchedHarnessSrc := traceDir + "trace_" + *testHarnessName

	kernelPrefix := "/src-no-kasan/"
	vmlinux := kernelPrefix + "vmlinux"

	err := os.MkdirAll(traceDir, os.ModePerm)
	if err != nil {
		fmt.Println("Error creating trace work directory:", err)
		os.Exit(-1)
	}

	patchedHarness := createPatchedTestHarness(testHarness, patchedHarnessSrc)
	vmlinuxSymtabs := createSymtabs(vmlinux)
	linuxKernel := kernelPrefix + "arch/x86/boot/bzImage"
	qemuBin := "/fuzzer/SkyTracer/out/qemu-system-x86_64"
	runVirtme(linuxKernel, qemuBin, traceDir, vmlinuxSymtabs, trace, patchedHarness, testBlob)
}
