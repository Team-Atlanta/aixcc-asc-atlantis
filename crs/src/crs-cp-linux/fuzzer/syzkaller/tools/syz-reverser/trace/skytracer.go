package trace

import (
	"bufio"
	"fmt"
	"os/exec"
)

type SkyTracer struct {
	config *SkyTracerConfig
	cmd    *exec.Cmd
	writer *bufio.Writer
	reader *bufio.Reader
}

type SkyTracerConfig struct {
	TracerPath string
	KernelDir  string
	WorkDir    string
	Timeout    uint
}

func (cfg SkyTracerConfig) New(harnessPath string) (*SkyTracer, error) {
	cmd := exec.Command(
		cfg.TracerPath,
		cfg.KernelDir,
		harnessPath,
		"--workdir", cfg.WorkDir,
		"--no_load",
		"--monitor",
		"--timeout", fmt.Sprint(cfg.Timeout))
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, err
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, err
	}
	writer := bufio.NewWriter(stdin)
	reader := bufio.NewReader(stdout)
	fmt.Println(cmd)
	if err := cmd.Start(); err != nil {
		return nil, err
	}
	tracer := SkyTracer{
		config: &cfg,
		cmd:    cmd,
		writer: writer,
		reader: reader,
	}
	_, err = tracer.readLineUntil("SkyTracer is ready")
	if err != nil {
		return nil, err
	}
	return &tracer, nil
}

func (tracer *SkyTracer) readLine() (*string, error) {
	str, err := tracer.reader.ReadString('\n')
	if err != nil {
		return nil, err
	}
	str = str[:len(str)-1]
	return &str, nil
}

func (tracer *SkyTracer) readLineUntil(line string) (*string, error) {
	for {
		str, err := tracer.readLine()
		if err != nil {
			return nil, err
		}
		fmt.Println(*str)
		if *str == line {
			return str, nil
		}
	}
}

func (tracer *SkyTracer) writeLine(line string) (int, error) {
	fmt.Println(line)
	return tracer.writer.Write([]byte(line + "\n"))
}

func (tracer *SkyTracer) GenTrace(blobPath string) (*Trace, error) {
	_, err := tracer.readLineUntil("Enter the blob path:")
	if err != nil {
		return nil, err
	}
	_, err = tracer.writeLine(blobPath)
	if err != nil {
		return nil, err
	}
	err = tracer.writer.Flush()
	if err != nil {
		return nil, err
	}
	_, err = tracer.readLineUntil("Here is the trace path:")
	if err != nil {
		return nil, err
	}
	tracePath, err := tracer.readLine()
	if err != nil {
		return nil, err
	}
	fmt.Println(*tracePath)
	t := Load(tracePath)
	return t, nil
}
