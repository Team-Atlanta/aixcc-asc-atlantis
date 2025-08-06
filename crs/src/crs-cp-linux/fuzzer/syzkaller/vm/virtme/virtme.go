package virtme

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/google/syzkaller/pkg/config"
	"github.com/google/syzkaller/pkg/log"
	"github.com/google/syzkaller/pkg/osutil"
	"github.com/google/syzkaller/pkg/report"
	"github.com/google/syzkaller/sys/targets"
	"github.com/google/syzkaller/vm/vmimpl"
)

func init() {
	var _ vmimpl.Infoer = (*instance)(nil)
	vmimpl.Register("virtme", ctor, true)
}

type Config struct {
	Count    int    `json:"count"`
	Kernel   string `json:"kernel"`
	Initrd   string `json:"initrd"`
	Cmdline  string `json:"cmdline"`
	CPU      int    `json:"cpu"`
	Mem      int    `json:"mem"`
	NetDev   string `json:"network_device"`
	Snapshot bool   `json:"snapshot"`
}

type Pool struct {
	env        *vmimpl.Env
	cfg        *Config
	target     *targets.Target
	archConfig *archConfig
	version    string
}

type instance struct {
	index       int
	cfg         *Config
	target      *targets.Target
	archConfig  *archConfig
	version     string
	args        []string
	image       string
	debug       bool
	os          string
	workdir     string
	sshkey      string
	sshuser     string
	timeouts    targets.Timeouts
	port        int
	monport     int
	forwardPort int
	mon         net.Conn
	monEnc      *json.Encoder
	monDec      *json.Decoder
	rpipe       io.ReadCloser
	wpipe       io.WriteCloser
	virtme      *exec.Cmd
	merger      *vmimpl.OutputMerger
	files       map[string]string
	diagnose    chan bool
}

type archConfig struct {
	NetDev  string
	CmdLine []string
}

var archConfigs = map[string]*archConfig{
	"linux/amd64": {
		NetDev: "e1000",
		CmdLine: []string{
			"root=/dev/sda",
			"console=ttyS0",
		},
	},
	// Add more configurations for other architectures if needed
}

func ctor(env *vmimpl.Env) (vmimpl.Pool, error) {
	archConfig := archConfigs[env.OS+"/"+env.Arch]
	cfg := &Config{
		Count:    1,
		CPU:      1,
		Mem:      1024,
		NetDev:   archConfig.NetDev,
		Snapshot: true,
	}
	if err := config.LoadData(env.Config, cfg); err != nil {
		return nil, fmt.Errorf("failed to parse virtme vm config: %w", err)
	}
	if cfg.Count < 1 || cfg.Count > 128 {
		return nil, fmt.Errorf("invalid config param count: %v, want [1, 128]", cfg.Count)
	}
	if env.Debug && cfg.Count > 1 {
		log.Logf(0, "limiting number of VMs from %v to 1 in debug mode", cfg.Count)
		cfg.Count = 1
	}
	if !osutil.IsExist(cfg.Kernel) {
		return nil, fmt.Errorf("kernel file '%v' does not exist", cfg.Kernel)
	}
	if cfg.CPU <= 0 || cfg.CPU > 1024 {
		return nil, fmt.Errorf("bad virtme cpu: %v, want [1-1024]", cfg.CPU)
	}
	if cfg.Mem < 128 || cfg.Mem > 1048576 {
		return nil, fmt.Errorf("bad virtme mem: %v, want [128-1048576]", cfg.Mem)
	}
	cfg.Kernel = osutil.Abs(cfg.Kernel)
	cfg.Initrd = osutil.Abs(cfg.Initrd)

	output, err := osutil.RunCmd(time.Minute, "", "virtme-ng", "--version")
	if err != nil {
		return nil, err
	}
	version := string(bytes.Split(output, []byte{'\n'})[0])

	pool := &Pool{
		env:        env,
		cfg:        cfg,
		version:    version,
		target:     targets.Get(env.OS, env.Arch),
		archConfig: archConfig,
	}
	return pool, nil
}

func (pool *Pool) Count() int {
	return pool.cfg.Count
}

func (pool *Pool) Create(workdir string, index int) (vmimpl.Instance, error) {
	sshkey := pool.env.SSHKey
	sshuser := pool.env.SSHUser
	sshkey = filepath.Join(workdir, "key")
	sshuser = "root"
	if _, err := osutil.RunCmd(10*time.Minute, "", "ssh-keygen", "-t", "rsa", "-b", "2048",
		"-N", "", "-C", "", "-f", sshkey); err != nil {
		return nil, err
	}
	initFile := filepath.Join(workdir, "init.sh")
	if err := osutil.WriteExecFile(initFile, []byte(strings.Replace(initScript, "{{KEY}}", sshkey, -1))); err != nil {
		return nil, fmt.Errorf("failed to create init file: %w", err)
	}
	for i := 0; ; i++ {
		inst, err := pool.ctor(workdir, sshkey, sshuser, index)
		if err == nil {
			return inst, nil
		}
		if i < 1000 && strings.Contains(err.Error(), "could not set up host forwarding rule") {
			continue
		}
		if i < 1000 && strings.Contains(err.Error(), "Device or resource busy") {
			continue
		}
		return nil, err
	}
}

func (pool *Pool) ctor(workdir, sshkey, sshuser string, index int) (vmimpl.Instance, error) {
	inst := &instance{
		index:      index,
		cfg:        pool.cfg,
		target:     pool.target,
		archConfig: pool.archConfig,
		version:    pool.version,
		image:      pool.env.Image,
		debug:      pool.env.Debug,
		os:         pool.env.OS,
		timeouts:   pool.env.Timeouts,
		workdir:    workdir,
		sshkey:     sshkey,
		sshuser:    sshuser,
		diagnose:   make(chan bool, 1),
	}
	if st, err := os.Stat(inst.image); err == nil && st.Size() == 0 {
		inst.image = ""
	}
	closeInst := inst
	defer func() {
		if closeInst != nil {
			closeInst.Close()
		}
	}()

	var err error
	inst.rpipe, inst.wpipe, err = osutil.LongPipe()
	if err != nil {
		return nil, err
	}

	if err := inst.boot(); err != nil {
		return nil, err
	}

	closeInst = nil
	return inst, nil
}

func (inst *instance) Close() {
	if inst.virtme != nil {
		inst.virtme.Process.Kill()
		inst.virtme.Wait()
	}
	if inst.merger != nil {
		inst.merger.Wait()
	}
	if inst.rpipe != nil {
		inst.rpipe.Close()
	}
	if inst.wpipe != nil {
		inst.wpipe.Close()
	}
	if inst.mon != nil {
		inst.mon.Close()
	}
}

func (inst *instance) boot() error {
	inst.port = vmimpl.UnusedTCPPort()
	instanceName := fmt.Sprintf("VM-%v", inst.index)
	args := []string{
		"--verbose", "--show-boot-console",
		"--mods=auto",
		"--kimg", inst.cfg.Kernel,
		"--memory", strconv.Itoa(inst.cfg.Mem),
		"--cpus", strconv.Itoa(inst.cfg.CPU),
		"--name", instanceName,
		"--show-command",
		"--kopt", strings.Join(inst.archConfig.CmdLine, " ") + " " + inst.cfg.Cmdline,
		"--script-sh", filepath.Join(inst.workdir, "init.sh"),
		"--qemu-opts",
	}
	forwardedPort := vmimpl.UnusedTCPPort()
	pprofExt := fmt.Sprintf(",hostfwd=tcp::%v-:%v", forwardedPort, vmimpl.PprofPort)
	log.Logf(3, "instance %s's pprof is available at 127.0.0.1:%v", instanceName, forwardedPort)
	args = append(args,
		"-device", inst.cfg.NetDev+",netdev=net0",
		"-netdev", fmt.Sprintf("user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:%v-:22%s", inst.port, pprofExt),
	)

	if inst.cfg.Initrd != "" {
		args = append(args, "--initrd", inst.cfg.Initrd)
	}
	if inst.image != "" {
		args = append(args, "--disk", fmt.Sprintf("image=%s", inst.image))
		if inst.cfg.Snapshot {
			args = append(args, "--snaps")
		}
	}
	if inst.debug {
		log.Logf(0, "running command: virtme-run %#v", args)
	}
	inst.args = args
	virtme := osutil.Command("virtme-run", args...)
	virtme.Stdout = inst.wpipe
	virtme.Stderr = inst.wpipe
	if err := virtme.Start(); err != nil {
		return fmt.Errorf("failed to start virtme-run %+v: %w", args, err)
	}
	inst.wpipe.Close()
	inst.wpipe = nil
	inst.virtme = virtme

	var tee io.Writer
	if inst.debug {
		tee = os.Stdout
	}
	inst.merger = vmimpl.NewOutputMerger(tee)
	inst.merger.Add("virtme", inst.rpipe)
	inst.rpipe = nil

	var bootOutput []byte
	bootOutputStop := make(chan bool)
	go func() {
		for {
			select {
			case out := <-inst.merger.Output:
				bootOutput = append(bootOutput, out...)
			case <-bootOutputStop:
				close(bootOutputStop)
				return
			}
		}
	}()
	if err := vmimpl.WaitForSSH(inst.debug, 10*time.Minute*inst.timeouts.Scale, "localhost",
		inst.sshkey, inst.sshuser, inst.os, inst.port, inst.merger.Err); err != nil {
		bootOutputStop <- true
		<-bootOutputStop
		return vmimpl.MakeBootError(err, bootOutput)
	}
	bootOutputStop <- true
	return nil
}

func (inst *instance) Forward(port int) (string, error) {
	if port == 0 {
		return "", fmt.Errorf("vm/virtme: forward port is zero")
	}
	if !inst.target.HostFuzzer {
		if inst.forwardPort != 0 {
			return "", fmt.Errorf("vm/virtme: forward port already set")
		}
		inst.forwardPort = port
	}
	return fmt.Sprintf("localhost:%v", port), nil
}

func (inst *instance) targetDir() string {
	return "/tmp/"
}

func (inst *instance) Copy(hostSrc string) (string, error) {
	base := filepath.Base(hostSrc)
	vmDst := filepath.Join(inst.targetDir(), base)
	if inst.target.HostFuzzer {
		if base == "syz-fuzzer" || base == "syz-execprog" {
			return hostSrc, nil
		}
		if inst.files == nil {
			inst.files = make(map[string]string)
		}
		inst.files[vmDst] = hostSrc
	}

	args := append(vmimpl.SCPArgs(inst.debug, inst.sshkey, inst.port),
		hostSrc, inst.sshuser+"@localhost:"+vmDst)
	if inst.debug {
		log.Logf(0, "running command: scp %#v", args)
	}
	_, err := osutil.RunCmd(10*time.Minute*inst.timeouts.Scale, "", "scp", args...)
	if err != nil {
		return "", err
	}
	return vmDst, nil
}

func (inst *instance) Run(timeout time.Duration, stop <-chan bool, command string) (
	<-chan []byte, <-chan error, error) {
	rpipe, wpipe, err := osutil.LongPipe()
	if err != nil {
		return nil, nil, err
	}
	inst.merger.Add("ssh", rpipe)

	sshArgs := vmimpl.SSHArgsForward(inst.debug, inst.sshkey, inst.port, inst.forwardPort)
	args := strings.Split(command, " ")
	if bin := filepath.Base(args[0]); inst.target.HostFuzzer &&
		(bin == "syz-fuzzer" || bin == "syz-execprog") {
		for i, arg := range args {
			if strings.HasPrefix(arg, "-executor=") {
				args[i] = "-executor=" + "/usr/bin/ssh " + strings.Join(sshArgs, " ") +
					" " + inst.sshuser + "@localhost " + arg[len("-executor="):]
			}
			if host := inst.files[arg]; host != "" {
				args[i] = host
			}
		}
	} else {
		args = []string{"ssh"}
		args = append(args, sshArgs...)
		args = append(args, inst.sshuser+"@localhost", "cd "+inst.targetDir()+" && "+command)
	}
	if inst.debug {
		log.Logf(0, "running command: %#v", args)
	}
	cmd := osutil.Command(args[0], args[1:]...)
	cmd.Dir = inst.workdir
	cmd.Stdout = wpipe
	cmd.Stderr = wpipe
	if err := cmd.Start(); err != nil {
		wpipe.Close()
		return nil, nil, err
	}
	wpipe.Close()
	errc := make(chan error, 1)
	signal := func(err error) {
		select {
		case errc <- err:
		default:
		}
	}

	go func() {
	retry:
		select {
		case <-time.After(timeout):
			signal(vmimpl.ErrTimeout)
		case <-stop:
			signal(vmimpl.ErrTimeout)
		case <-inst.diagnose:
			cmd.Process.Kill()
			goto retry
		case err := <-inst.merger.Err:
			cmd.Process.Kill()
			if cmdErr := cmd.Wait(); cmdErr == nil {
				err = nil
			}
			signal(err)
			return
		}
		cmd.Process.Kill()
		cmd.Wait()
	}()
	return inst.merger.Output, errc, nil
}

func (inst *instance) Info() ([]byte, error) {
	info := fmt.Sprintf("%v\nvirtme-run %q\n", inst.version, inst.args)
	return []byte(info), nil
}

func (inst *instance) Diagnose(rep *report.Report) ([]byte, bool) {
	if inst.target.OS == targets.Linux {
		if output, wait, handled := vmimpl.DiagnoseLinux(rep, inst.ssh); handled {
			return output, wait
		}
	}
	return nil, false
}

func (inst *instance) ssh(args ...string) ([]byte, error) {
	return osutil.RunCmd(time.Minute*inst.timeouts.Scale, "", "ssh", inst.sshArgs(args...)...)
}

func (inst *instance) sshArgs(args ...string) []string {
	sshArgs := append(vmimpl.SSHArgs(inst.debug, inst.sshkey, inst.port), inst.sshuser+"@localhost")
	return append(sshArgs, args...)
}

// nolint: lll
const initScript = `#! /bin/bash
set -eux

NET_IFACE=$(ifconfig -a | grep -o '^[^ ]*:' | sed 's/://g' | grep -v lo | head -n 1)

ifconfig $NET_IFACE up
udhcpc -i $NET_IFACE

mount -t tmpfs none /tmp
mount -t tmpfs none /var
mount -t tmpfs none /run
mount -t tmpfs none /etc
mount -t tmpfs none /root

echo "root::0:0:root:/root:/bin/bash" > /etc/passwd
mkdir -p /root/.ssh
chmod 0700 /root/.ssh
cp {{KEY}}.pub /root/.ssh/authorized_keys
chmod 0600 /root/.ssh/authorized_keys
chmod 700 /root

mkdir -p /run/sshd/
chmod 700 /run/sshd
groupadd -g 33 sshd
useradd -u 33 -g 33 -c sshd -d / sshd

# SSH configuration
mkdir -p /etc/ssh
cat > /etc/ssh/sshd_config <<EOF
Port 22
Protocol 2
PermitRootLogin yes
PasswordAuthentication no
ChallengeResponseAuthentication no
AuthorizedKeysFile /root/.ssh/authorized_keys
HostKey {{KEY}}
IgnoreUserKnownHosts yes
AllowUsers root
LogLevel INFO
TCPKeepAlive yes
PubkeyAuthentication yes
EOF

/usr/sbin/sshd -e -D
/sbin/halt -f
`
