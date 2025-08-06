#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import atexit
import shutil
import json
import yaml

class SyzRunner:
  def __init__(self, config_file, http=None, nokvm=False, debug=False, verbose=False):
    with open(config_file, 'r') as f:
      self.config = self._check_conf(yaml.safe_load(f))
    self.root_dir = os.path.abspath(os.path.dirname(__file__)+'/../../../')
    self.syzkaller_path = self.root_dir + '/fuzzer/syzkaller'

    self.linux = self.config['linux']
    self.harness_path = self.config['harness']
    self.harness = self.config.get('harness_id', os.path.basename(self.harness_path))
    self.verifier = self.config.get('verifier', os.path.join(self.root_dir, 'verifier/verifier.py'))

    self.img = self.config['img']
    self.syscall = self.config['syscall']
    self.filter = self.config.get('filter', {})
    self.filter_deny = self.config.get('filter_deny', [])
    self.syzlang = self.config.get('syzlang', [])
    # Number of VM instances
    self.vm_count = self.config.get('vm_count', 1)
    # Number of cores for each VM instance
    self.core = self.config.get('core', 2)
    # Number of parallel fuzzing processes in each VM instance
    self.procs = self.config.get('procs', 4)

    # Sanitizers, use values only for now
    self.sanitizers = self.config.get('sanitizers', {})
    self.sanitizers = list(self.sanitizers.values())

    # Generate dirs for testing
    if 'workdir' in self.config:
      self.workdir = self.config['workdir']
    else:
      self.workdir = self.syzkaller_path + '/workdir-harness/' + self.harness
    os.makedirs(self.workdir, exist_ok=True)
    self.syzkaller_linux = self.syzkaller_path + '/workdir-linux'

    atexit.register(self._exit)

    self.http = http
    self.debug = debug
    self.verbose = verbose
    self.syz_config = ''
    self.is_type1 = any("syz_harness_type1" in c for c in self.syscall)
    self.nokvm = nokvm

    self.polling_corpus = self.config.get('polling_corpus', '')

  def _check_conf(self, config):
    for c in ['linux', 'harness', 'img', 'syscall']:
      if c not in config:
        print(f"Error: missing {c} in config file")
        print(config)
        sys.exit(-1)
    return config

  def _exit(self):
    print('*' * 30)
    print('Runner Config:')
    print(self.config)
    print('Syzkaller config:')
    print(self.syz_config)
    print('*' * 30)

  def _run(self, cmd, timeout=None, cwd=None, shell=False):
    print(f"Running: {cmd}")
    return subprocess.run(cmd, timeout=timeout, cwd=cwd, shell=shell)

  def prepare_syzkaller_linux(self, force=False):
    print(f"Copying linux source to {self.syzkaller_linux} for syzkaller make extract")
    if force and os.path.exists(self.syzkaller_linux):
      shutil.rmtree(self.syzkaller_linux)
      shutil.copytree(self.linux, self.syzkaller_linux)
    elif not os.path.exists(self.syzkaller_linux):
      shutil.copytree(self.linux, self.syzkaller_linux) 
    else:
      print("Using existing linux source")

  def copy_syzlang_files(self):
    sys_linux_dir = os.path.join(self.syzkaller_path, 'sys', 'linux')
    for syzlang_file in self.syzlang:
      if os.path.exists(syzlang_file):
        print(f"Copying {syzlang_file} to {sys_linux_dir}")
        shutil.copy(syzlang_file, sys_linux_dir)
      else:
        print(f"{syzlang_file} does not exist")

  def clear_syzlang_files(self):
    sys_linux_dir = os.path.join(self.syzkaller_path, 'sys', 'linux')
    if os.path.exists(sys_linux_dir):
      for syzlang_file in self.syzlang:
        target_file = os.path.join(sys_linux_dir, os.path.basename(syzlang_file))
        if os.path.exists(target_file):
          print(f"Deleting {target_file}")
          os.remove(target_file)
        else:
          print(f"{target_file} does not exist")

  def _run_syzkaller_make(self, cmd, description):
    print(f"Build syzkaller: {description}")
    ret = self._run(cmd)
    if ret.returncode != 0:
      print(f'****{description} failed! Unable to proceed!!!!')
      sys.exit(-1)

  def build_syzkaller(self, do_extract=False):
    self.copy_syzlang_files()
    if self.is_type1:
      print("Limit syscalls for type1 harness")
      os.environ['RECOMMENDED_CALLS'] = '1'
      os.environ['MAX_CALLS'] = '1'
    #make extract
    if do_extract:
      command = ['make', '-C', self.syzkaller_path, 'extract', 'TARGETOS=linux', f'SOURCEDIR={self.syzkaller_linux}']
      self._run_syzkaller_make(command, 'make extract')
    #make generate
    command = ['make', '-C', self.syzkaller_path, 'generate']
    self._run_syzkaller_make(command, 'make generate')
    #make
    command = ['make', '-C', self.syzkaller_path]
    self._run_syzkaller_make(command, 'make')
    #copy bins
    shutil.copytree(self.syzkaller_path+'/bin', self.workdir+'/bin', dirs_exist_ok=True)

  def _create_syzkaller_config_file(self):
    config_base = {
      "target": "linux/amd64",
      "http": self.http,
      "workdir": os.path.join(self.workdir, "work"),
      "kernel_obj": self.linux,
      "kernel_src": self.linux,
      "init_files": [self.harness_path],
      "init_cmds": [f"mv {os.path.basename(self.harness_path)} /tmp/harness; chmod +x /tmp/harness; ls -al /tmp/harness"],
      "image": self.img,
      "syzkaller": self.workdir,
      "procs": self.procs,
      "enable_syscalls": self.syscall,
      "type": "qemu",
      "vm": {
        "count": self.vm_count,
        "kernel": os.path.join(self.linux, "arch/x86/boot/bzImage"),
        "cmdline": "net.ifnames=0 nokaslr",
        "cpu": self.core,
        "mem": 2048
      },
      "harness_executor": "default",
      "harness_id": self.harness,
      "verifier": self.verifier,
      "sanitizers": self.sanitizers,
      "polling_corpus": self.polling_corpus,
    }
    if self.img != "9p":
      config_base["sshkey"] = self.img+".id_rsa"
    if not self.http:
      config_base["http"] = "0.0.0.0:56741" # just dummy value, not used actually
    if self.filter:
      config_base["cover_filter"] = self.filter
    if self.filter_deny:
      config_base["cover_filter_deny"] = {
        "files": self.filter_deny
      }
    if self.nokvm:
      config_base["vm"]["qemu_args"] = "-cpu max" # max emulator w/o kvm

    self.syz_config = json.dumps(config_base, indent=2)
    print("Syzkaller config:")
    print(self.config)

    target_config_path = f'{self.workdir}/config.cfg'
    with open(target_config_path, 'w') as f:
      f.write(self.syz_config)

    return target_config_path

  def _run_syzmanager(self, config_file_path):
    command = [f'{self.workdir}/bin/syz-manager', f'-config={config_file_path}']
    if self.http:
      command += ['--http']
    if self.debug:
      command += ['--debug']
    if self.verbose:
      command += ['-vv', self.verbose]
    self._run(command)

  def run_syzkaller(self):
    config_file_path = self._create_syzkaller_config_file()
    self._run_syzmanager(config_file_path)

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser = argparse.ArgumentParser(description="Load YAML config for running a tool")
  parser.add_argument('config', help='YAML configuration file path')
  parser.add_argument("--build",
                      help="build syzkaller", action="store_true",
                      default=False)
  parser.add_argument("--clear",
                      help="clear syzlang files", action="store_true",
                      default=False)

  # Below options are for debugging, may not be used in competition
  parser.add_argument("--extract",
                      help="run make extract", action="store_true",
                      default=False)
  parser.add_argument("--force",
                      help="force copy linux source, use if linux src is updated", action="store_true",
                      default=False)
  parser.add_argument("--debug", help="run syzkaller with --debug", action="store_true", default=False)
  parser.add_argument("--verbose", nargs='?', const="9", default=None,
                      help="run syzkaller as verbose")
  parser.add_argument('--http', nargs='?', const="0.0.0.0:56741", default=None,
                      help='Bind syzkaller HTTP server to a specific address (default: 0.0.0.0:56741)')
  parser.add_argument("--nokvm",
                      help="run qemu without kvm", action="store_true",
                      default=False)
  args = parser.parse_args()

  runner = SyzRunner(args.config, args.http, args.nokvm, args.debug, args.verbose)
  if args.clear:
    runner.clear_syzlang_files()
  elif args.build:
    if args.extract:
      runner.prepare_syzkaller_linux(args.force)
    runner.build_syzkaller(args.extract)
    runner.clear_syzlang_files()
  else:
    runner.run_syzkaller()
