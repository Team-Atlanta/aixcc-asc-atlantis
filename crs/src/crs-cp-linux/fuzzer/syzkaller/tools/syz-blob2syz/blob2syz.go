// Copyright 2018 syzkaller project authors. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

package main

import (
	"bufio"
	"crypto/sha1"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/google/syzkaller/pkg/log"
	"github.com/google/syzkaller/pkg/mgrconfig"
	"github.com/google/syzkaller/prog"
	_ "github.com/google/syzkaller/sys"
	"github.com/google/syzkaller/sys/targets"

	"github.com/google/syzkaller/tools/syz-blob2syz/parser"
)

var (
	flagDatablob    = flag.String("datablob", "", "datablob file")
	flagDatablobDir = flag.String("blob-dir", "", "directory containing all datablobs")
	flagSyzlang     = flag.String("syzlang", "", "syzlang file containing pseudo syscalls")
	flagSyzConfig   = flag.String("syz-conf", "", "syzkaller path to pass results to Syzkaller")
	flagHarness     = flag.String("harness", "", "harness name (for testing)")
	flagType        = flag.String("type", "", "harness type")
)

const (
	goos = targets.Linux // Target OS
	arch = targets.AMD64 // Target architecture
)

func main() {
	flag.Parse()
	target := initializeTarget(goos, arch)
	blobs := loadDatablobs(*flagDatablobDir, *flagDatablob)
	syzMap := getSyzMap(*flagSyzlang, *flagHarness, target)
	progs := []*prog.Prog{}
	for _, blob := range blobs {
		prog, err := parseDatablob(target, blob, syzMap, *flagType)
		if err != nil {
			fmt.Printf("Error: %v", err)
		} else {
			progs = append(progs, prog)
			fmt.Printf("%v", string(prog.Serialize()))
		}
	}
	if cfgPath := *flagSyzConfig; len(cfgPath) != 0 {
		saveResultsToSyzkaller(progs, cfgPath)
	}
}

func initializeTarget(os, arch string) *prog.Target {
	target, err := prog.GetTarget(os, arch)
	if err != nil {
		log.Fatalf("failed to load target: %s", err)
	}
	target.ConstMap = make(map[string]uint64)
	for _, c := range target.Consts {
		target.ConstMap[c.Name] = c.Value
	}
	return target
}

func loadDatablobs(blobdir, blobfile string) [][]byte {
	if len(blobdir) != 0 && len(blobfile) != 0 {
		log.Fatalf("both --blob-dir and --datablob are given")
	}

	names := []string{}
	if len(blobdir) != 0 {
		blobfiles, err := os.ReadDir(blobdir)
		if err != nil {
			log.Fatal(err)
		}

		for _, e := range blobfiles {
			names = append(names, filepath.Join(blobdir, e.Name()))
		}
	} else {
		names = append(names, blobfile)
	}

	blobs := [][]byte{}
	for _, name := range names {
		blobs = append(blobs, loadDatablob(name))
	}
	return blobs
}

func loadDatablob(filename string) []byte {
	file, err := os.Open(filename)
	if err != nil {
		log.Fatalf("Cannot read datablob file: %v", filename)
		return nil
	}
	defer file.Close()

	// Get the file size
	stat, err := file.Stat()
	if err != nil {
		log.Fatalf("Cannot read the size of the datablob file: %v", filename)
		return nil
	}

	bs := make([]byte, stat.Size())
	_, err = bufio.NewReader(file).Read(bs)
	if err != nil && err != io.EOF {
		log.Fatalf("Failed to read the datablob file: %v", filename)
		return nil
	}
	return bs
}

func getSyzMap(syzlang, harness string, target *prog.Target) map[uint64]string {
	if len(harness) != 0 {
		return getSyzmapTester(harness)
	} else {
		return getSyzmap(syzlang, target)
	}
}

func parseDatablob(target *prog.Target, blob []byte, syzMap map[uint64]string, typ string) (*prog.Prog, error) {
	p, err := parser.ParseDatablob(target, blob, syzMap, typ)
	if err == nil {
		return p, nil
	}
	return parser.ParseFallback(target, blob, syzMap, typ)
}

func saveResultsToSyzkaller(progs []*prog.Prog, syzConf string) {
	cfg, err := mgrconfig.LoadFile(syzConf)
	if err != nil {
		log.Fatalf("Cannot load the Syzkaller config: %v, %v", syzConf, err)
	}
	syzDB0 := "syz-db"
	var syzDB string
	if path, err := exec.LookPath(syzDB0); err != nil {
		log.Errorf("%v does not exist. Cannot store outputs into corpus.db", syzDB)
		return
	} else {
		syzDB = path
	}

	workdir := cfg.Workdir
	corpusPath := cfg.PollingCorpus
	if _, err := os.Stat(corpusPath); os.IsNotExist(err) {
		mergeProgsToCorpus(progs, syzDB, workdir, corpusPath)
	} else {
		createCorpus(progs, syzDB, workdir, corpusPath)
	}
}

func mergeProgsToCorpus(progs []*prog.Prog, syzDB, workdir, corpusPath string) {
	dir, files := saveProgsToTmpdir(workdir, progs)
	defer os.RemoveAll(dir)
	args := append([]string{"merge", corpusPath}, files...)
	runSyzDB(syzDB, args)
}

func createCorpus(progs []*prog.Prog, syzDB, workdir, corpusPath string) {
	dir, _ := saveProgsToTmpdir(workdir, progs)
	defer os.RemoveAll(dir)
	args := []string{"pack", dir, corpusPath}
	runSyzDB(syzDB, args)
}

func hash(b []byte) string {
	h := sha1.New()
	h.Write(b)
	return fmt.Sprintf("%x", h.Sum(nil))
}

func saveProgsToTmpdir(workdir string, progs []*prog.Prog) (string, []string) {
	dname, err := os.MkdirTemp(workdir, "corpus")
	if err != nil {
		log.Errorf("Cannot create a tmpdir.")
	}

	fpaths := []string{}
	for _, prog := range progs {
		b := prog.Serialize()
		fname := hash(b)
		path := filepath.Join(dname, fname)
		err := os.WriteFile(path, b, 0666)
		if err != nil {
			log.Errorf("err: %v Failed to write prog: %v", err, string(b))
		}
		fpaths = append(fpaths, path)
	}
	return dname, fpaths
}

func runSyzDB(syzDB string, args []string) {
	log.Logf(1, "%v %v", syzDB, args)
	cmd := exec.Command(syzDB, args...)
	if err := cmd.Run(); err != nil {
		log.Fatalf("Failed to run syz-db %v", err)
	}
}
