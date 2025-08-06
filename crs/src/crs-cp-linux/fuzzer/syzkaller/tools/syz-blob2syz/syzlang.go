package main

import (
	"bufio"
	"os"
	"regexp"
	"strconv"

	"github.com/google/syzkaller/pkg/log"
	"github.com/google/syzkaller/prog"
	"github.com/google/syzkaller/tools/syz-blob2syz/parser"
)

func getSyzmap(filename string, target *prog.Target) map[uint64]string {
	file, err := os.Open(filename)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	res := make(map[uint64]string)
	// XXX: the current version assumes that pseudo syscalls are given
	// in the increasing order starting from 0. Apprently this
	// assumptino does not hold for some of our benchmarks harnesses
	// (eg, NRFIN-00001).
	idx := uint64(0)
	s := bufio.NewScanner(file)
	for s.Scan() {
		line := s.Text()
		r := regexp.MustCompile(`syz_harness[a-zA-Z0-9$_]*\(`)
		if str := r.FindString(line); len(str) != 0 {
			res[idx] = str[:len(str)-1]
			idx += 1
		}
	}

	if err = s.Err(); err != nil {
		log.Fatalf("%v", err)
	}

	index := getIndex(filename)
	postProcessSyzmap(res, index, target)

	return res
}

func getIndex(filename string) map[string]uint64 {
	constFilename := filename + ".const"
	file, err := os.Open(constFilename)
	if err != nil {
		log.Errorf("Cannot open .const file (%v). Didn't make extract?", constFilename)
	}

	res := make(map[string]uint64)
	s := bufio.NewScanner(file)
	for s.Scan() {
		line := s.Text()
		r := regexp.MustCompile(`([a-zA-Z0-9$_]*)\s=\s([0-9]*)`)
		if matched := r.FindStringSubmatch(line); len(matched) > 2 {
			k, v := matched[1], matched[2]
			if k == "arches" {
				continue
			}
			ui, err := strconv.ParseUint(v, 10, 64)
			if err != nil {
				continue
			}
			res[k] = ui
		}
	}
	return res
}

func postProcessSyzmap(res map[uint64]string, index map[string]uint64, target *prog.Target) {
	for cmd, callName := range res {
		call, err := parser.FindSyscall(callName, target)
		if err != nil {
			panic(err)
		}
		prog.ForeachCallType(call, func(t prog.Type, ctx *prog.TypeCtx) {
			switch t0 := t.(type) {
			case *prog.ConstType:
				// XXX I wanted to check whether the const value comes
				// from a command (ie, cmd int32[...]) or not, but I
				// don't know how to do that. As a simple workaround,
				// check if any argument of the call contains the
				// const value.
				val := t0.Val
				for k := range index {
					v := index[k]
					if v == val {
						res[v] = callName
					}
				}
			}
		})
		_ = cmd
	}
}
