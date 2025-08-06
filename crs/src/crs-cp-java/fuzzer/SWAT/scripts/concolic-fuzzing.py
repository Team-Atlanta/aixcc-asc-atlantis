#!/usr/bin/env python3

import argparse
import base64
import glob
import hashlib
import json
import logging
import os
from pathlib import Path
import pickle
import shutil
import signal
import struct
import subprocess
import sys
import time
import traceback

import threading
from threading import Thread, Lock

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

threading.stack_size(0x4000000)
INIT_VALUE = b"x"
RUNNING_SCRIPT = 'swat-runner.sh'

CONCOLIC_TIMEOUT = '120'
STOP_CONCOLIC = False

#MAX_LOG_SIZE = 300 * 1048576

def setup_logger(name, log_file, level=logging.INFO, useConsoleHandler=True):
    formatter = logging.Formatter("[%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

    fileHandler = logging.FileHandler(log_file)
    fileHandler.setFormatter(formatter)
    logger = logging.getLogger(name)
    if useConsoleHandler:
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(formatter)
        logger.addHandler(consoleHandler)
    logger.setLevel(level)
    logger.addHandler(fileHandler)

    return logger

class CorpusQueue(FileSystemEventHandler):
    def __init__(self, concolic_runner):
        # dict is for checking existing files
        self.dict = {}
        # list is the queue
        self.list = []
        # mutex for the queue
        self.mutex = Lock()

        # options['mode'] = 'fuzzing' or 'concolic'
        self.options = {}

        # concolic runner instance
        self.concolic_runner = concolic_runner

    # returns the length of the queue
    def __len__(self):
        with self.mutex:
            return len(self.list)

    # set options as a dict { 'mode' : 'fuzzing' } or { 'mode' : 'concolic' }
    def set_options(self, options):
        self.options = options

    # check if the file exist in the dict
    def check_exists(self, filepath):
        r = False
        with self.mutex:
            if filepath in self.dict:
                r = True
            else:
                r = False
        return r

    # add to the queue
    def add_to_queue(self, filepath):
        # acquire the lock
        with self.mutex:
            # if the file is already existing in the queue, we have a trouble
            if filepath in self.dict:
                # later, suppress this with return by ignoring adding
                return
            self.dict[filepath] = 0
            self.list.append(filepath)

    # pop one from the queue
    def pop_from_queue(self):
        r = None
        # acquire the lock
        with self.mutex:
            # return None if the queue is empty
            if len(self.list) == 0:
                r = None
            else:
                # return the first item, remove it, and remove that entry from the dict
                if self.options == 'fuzzing':   # pop from the last for hybrid
                    r = self.list.pop(-1)
                else:
                    r = self.list.pop(0)
                del self.dict[r]

        # return None or element
        return r

    # FileSystemEventhandler override
    def on_created(self, event):
        # get the new file path
        new_file_path = event.src_path
        # check queue if it is for concolic or not
        is_concolic = self.options['mode'] == 'concolic'

        # if concolic
        if is_concolic:
            if self.check_exists(new_file_path):
                return
            else:
                self.add_to_queue(new_file_path)
        else:
            if self.check_exists(new_file_path):
                return
            else:
                # ignore concolic-generated corpus here
                if '-concolic' in new_file_path:
                    return

                # get filename
                p = Path(new_file_path)
                corpus_raw_filename = os.path.basename(str(p))
                harness_class_name = os.path.basename(p.parents[1])

                # add the imported path name
                import_path = self.concolic_runner.imported_corpus_storage_path
                import_filename = f'{import_path}/{corpus_raw_filename}-{harness_class_name}'
                try:
                    shutil.copy(new_file_path, import_filename)
                except:
                    return

                # add to the queue
                self.add_to_queue((import_filename, new_file_path))
                #self.add_to_queue(import_filename)


class ConcolicRunner(object):
    def __init__(self):
        self.executed_values = {}
        self.generated_files = {}
        self.fuzzing_corpus_queue = CorpusQueue(self)
        self.fuzzing_corpus_queue.set_options({'mode' : 'fuzzing'})
        self.concolic_corpus_queue = CorpusQueue(self)
        self.concolic_corpus_queue.set_options({'mode' : 'concolic'})
        self.observer_started = False
        self.mutex = Lock()
        self.save_mutex = Lock()

    # save state for re-execution
    def save_state(self):
        with self.save_mutex:
            d = {}
            d['executed_values'] = self.executed_values
            d['generated_files'] = self.generated_files
            d['fuzzing_corpus_queue_dict'] = self.fuzzing_corpus_queue.dict
            d['fuzzing_corpus_queue_list'] = self.fuzzing_corpus_queue.list
            d['concolic_corpus_queue_dict'] = self.concolic_corpus_queue.dict
            d['concolic_corpus_queue_list'] = self.concolic_corpus_queue.list

            pkl = pickle.dumps(d)
            with open(self.state_path, 'wb') as f:
                f.write(pkl)
                #self.logger.info(f"Saved state to {self.state_path}")

    # load state for re-execution
    def load_state(self):
        if os.path.exists(self.state_path):
            self.logger.info(f"Load prev states from {self.state_path}")
            with open(self.state_path, 'rb') as f:
                d = pickle.loads(f.read())
                self.executed_values = d['executed_values']
                self.generated_files = d['generated_files']
                self.fuzzing_corpus_queue.dict = d['fuzzing_corpus_queue_dict']
                self.fuzzing_corpus_queue.list = d['fuzzing_corpus_queue_list']
                self.concolic_corpus_queue.dict = d['concolic_corpus_queue_dict']
                self.concolic_corpus_queue.list = d['concolic_corpus_queue_list']

                self.logger.info(f'Loaded {len(self.concolic_corpus_queue.list)} concolic corpus queue')
                self.logger.info(f'Loaded {len(self.fuzzing_corpus_queue.list)} fuzzing corpus files')


    def retrieve_fuzzing_corpus_path_list(self):
        self.fuzzing_corpus_path_list = []

        for s in self.fuzzing_path_list:
            self.fuzzing_corpus_path_list += list(glob.glob(f'{s}/corpus_dir*'))

    def clear_classpath(self):
        to_be_returned = []

        all_classes = self.class_path.split(':')
        for classfile in all_classes:
            if not classfile.endswith('.jar'):
                to_be_returned.append(classfile)
                continue
            filename = os.path.basename(classfile)
            # find guava
            if filename.startswith('guava'):
                # get project name
                split1 = filename.split('-')
                if len(split1) == 1:
                    to_be_returned.append(classfile)
                    continue
                project_name = split1[0]
                version_string = split1[1]
                split2 = version_string.split('.')

                try:
                    version = int(split2[0])
                    if version > 27:
                        to_be_returned.append(classfile)
                    else:
                        # do not include lower version for SWAT
                        pass
                except:
                    to_be_returned.append(classfile)
            else:
                to_be_returned.append(classfile)
        #print(to_be_returned)
        print(f'all classes: {len(all_classes)}')
        print(f'ret: {len(to_be_returned)}')
        self.class_path = ':'.join(to_be_returned)

    #
    def set_logger(self):
        self.logger = setup_logger('concolic_logger',
                        self.log_filename)

    # set arguments
    def set_args(self, args):
        self.swat_path = args.swat
        self.harness_class = args.harness_class
        self.harness_directory = args.harness_directory
        self.class_path = args.class_path
        self.sym_var = args.sym_var

        self.log_path = args.logs
        if os.path.islink(self.log_path):
            self.log_path = os.readline(self.log_path)

        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)

        self.log_filename = f'{self.log_path}/concolic.log'
        self.set_logger()
        self.logger.info(f"SWAT PATH: {self.swat_path}")
        self.logger.info(f"Harness class: {self.harness_class}")
        #print(f"CLASSPATH: {self.class_path}")
        self.logger.info(f"SYM VAR: {self.sym_var}")
        self.logger.info(f"LOG PATH: {self.log_path}")

        self.logger.info(f"Fuzzer paths {args.fuzzing_paths}")
        b = base64.b64decode(args.fuzzing_paths)
        fuzzing_path_list = json.loads(str(b, 'utf-8'))
        self.logger.info(f'fuzzing path list: {fuzzing_path_list}')

        nolink_fuzzing_path_list = []
        for fuzz_path in fuzzing_path_list:
            if os.path.islink(fuzz_path):
                nolink_fuzzing_path_list.append(os.readlink(fuzz_path))
            else:
                nolink_fuzzing_path_list.append(fuzz_path)

        self.fuzzing_path_list = nolink_fuzzing_path_list
        self.logger.info(f'Fuzzing path list: {self.fuzzing_path_list}')
        self.retrieve_fuzzing_corpus_path_list()
        self.logger.info(f'Fuzzing corpus path list: {self.fuzzing_corpus_path_list}')

        self.concolic_corpus_path_head = args.concolic_corpus_path
        if os.path.islink(self.concolic_corpus_path_head):
            self.concolic_corpus_path_head = os.readlink(self.concolic_corpus_path_head)

        self.logger.info(self.concolic_corpus_path_head)

        self.concolic_corpus_storage_path = f'{self.concolic_corpus_path_head}/concolic-corpus'
        self.imported_corpus_storage_path = f'{self.concolic_corpus_path_head}/imported-corpus'
        self.exported_corpus_storage_path = f'{self.concolic_corpus_path_head}/exported-corpus'

        self.script_path = f'{self.concolic_corpus_path_head}/{RUNNING_SCRIPT}'
        self.state_path = f'{self.concolic_corpus_path_head}/state.pkl'

        self.logger.info(self.concolic_corpus_storage_path)
        self.logger.info(self.imported_corpus_storage_path)
        self.logger.info(self.exported_corpus_storage_path)
        self.logger.info(self.script_path)

        self.port = args.port
        self.config_path = f"{self.concolic_corpus_path_head}/swat.cfg"
        self.init_value_path = f"{self.concolic_corpus_path_head}/init.value"
        self.no_swat_output = args.no_swat_output

        self.logger.info(f'Harness directory {self.harness_directory}')

        dir_traversal = list(glob.glob(f'{self.harness_directory}/**', recursive=True))
        dir_traversal = [x[len(self.harness_directory):] for x in dir_traversal]
        self.logger.info(f'finding harness class : {dir_traversal}')


        class_file = [x for x in dir_traversal if x.endswith('.class')][0]
        if class_file[0] == '/':
            class_file = class_file[1:]

        self.logger.info(f'Harness class file: {class_file}')
        if '/' in class_file:
            package_name_slash = '/'.join(class_file.split('/')[:-1])
            package_name_dot = '.'.join(class_file.split('/')[:-1])
        else:
            package_name_slash = ''
            package_name_dot = ''
        self.logger.info(f'package_name_slash {repr(package_name_slash)}')
        self.logger.info(f'package_name_dot {repr(package_name_dot)}')
        self.harness_package_name_slash = package_name_slash
        self.harness_package_name_dot = package_name_dot

        self.logger.info(  f"Concolic setup {self.swat_path} {self.harness_class} {self.log_path} " +
                #f"{self.class_path} " +
                f"{self.sym_var} {self.fuzzing_path_list} {self.concolic_corpus_path_head} " +
                f"{self.script_path} " + f"{self.harness_package_name_slash}" +
                f"{self.harness_package_name_dot}" +
                "")

    def create_dirs(self):
        dirs =  [
                    self.concolic_corpus_path_head,
                    self.concolic_corpus_storage_path,
                    self.imported_corpus_storage_path,
                    self.exported_corpus_storage_path,
                ]
        self.logger.info(f"Creating dirs: {dirs}")
        for _dir in dirs:
            if not os.path.exists(_dir):
                #print(f'Creating {_dir}')
                os.makedirs(_dir)
                if os.path.exists(_dir):
                    self.logger.info(f'Directory {_dir} has been created')
                else:
                    self.logger.info(f'Directory {_dir} has NOT been created -- failed')

    def gen_swat_running_script(self):
        self.logger.info(f'SWAT running script is at {self.script_path}')
        self.instance_log_path = f'{self.concolic_corpus_path_head}/logs'
        if not os.path.exists(self.instance_log_path):
            os.makedirs(self.instance_log_path)
        if len(self.harness_package_name_dot) > 0:
            self.package_and_class_name = f'{self.harness_package_name_dot}.{self.harness_class}'
        else:
            self.package_and_class_name = self.harness_class

        script = f"""#!/bin/bash
rm -rf {self.instance_log_path}
mkdir {self.instance_log_path}
export PATH="/usr/lib/jvm/java-17-openjdk-amd64/bin:$PATH"
python3 {self.swat_path}/symbolic-explorer/SymbolicExplorer.py \\
 --mode active \\
 --agent {self.swat_path}/symbolic-executor/lib/symbolic-executor.jar \\
 --z3dir {self.swat_path}/libs/java-library-path \\
 --logdir {self.instance_log_path} \\
 --target {self.package_and_class_name} \\
 --classpath "{self.class_path}" \\
 --symbolicvars {self.sym_var} \\
 --config {self.config_path} \\
 --initvalue {self.init_value_path} \\
 --port {self.port} \\
 -o
        """

        if os.path.exists(self.script_path):
            os.unlink(self.script_path)
        with open(self.script_path, "wt") as f:
            f.write(script)
            os.chmod(self.script_path, 0o755)
        self.logger.info(f"swat-runner.sh written to {self.script_path}")


    def gen_func_signature_and_instrument_targets(self):

        # get function signature
        if len(self.harness_package_name_slash) > 0:
            self.func_signature = f'{self.harness_package_name_slash}/{self.harness_class}:fuzzerTestOneInput'
        else:
            self.func_signature = f'{self.harness_class}:fuzzerTestOneInput'

        instrument_targets = 'instrument_targets_here'
        print(f'SWAT PATH: {self.swat_path}')
        self.instrument_target_script_path = f'{self.swat_path}/scripts/get_instrument_target.py'

        self.instrument_targets = str(subprocess.check_output(['python3',
                                                                self.instrument_target_script_path,
																'-c', self.harness_class,
                                                                '-d', self.harness_directory,
															]),
														'utf-8')
        return (self.func_signature, self.instrument_targets)


    def gen_swat_config(self, function_signature, included_packages):
        if len(self.harness_package_name_slash) > 0:
            included_packages = f'{self.harness_package_name_slash}/{self.harness_class}:{included_packages}'
        else:
            included_packages = f'{self.harness_class}:{included_packages}'
        print('Generating swat config')
        cfg = f"""logging.debug=false
logging.classes=false
logging.invocation=false
logging.level=WARN
logging.formulaLength=1048576

instrumentation.transformer=PARAMETER
instrumentation.parameter.symbolicPattern={function_signature}
instrumentation.includePackages={included_packages}
instrumentation.prefix=""

solver.mode=HTTP
exitOnError=false
explorer.host=localhost
explorer.port={self.port}"""
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
        with open(self.config_path, "wt") as f:
            f.write(cfg)
        self.logger.info(f'Writing config file at {self.config_path}')

    def write_init_value(self, init_value=INIT_VALUE):
        with open(self.init_value_path, "wb") as f:
            f.write(init_value)
        self.logger.info(f"Executed: {repr(init_value)}\n\n")

    def write_log_inputs(self, inputs):
        for _input in inputs:
            self.logger.info(f"To be Executed: {repr(_input)}\n\n")

    def build(self):
        subprocess.run("make clean && make -j", shell=True)

    def run(self, filepath):
        with open(self.init_value_path, 'rb') as f:
            data = f.read()
            f.close()

        self.logger.info(f"Running SWAT for {filepath} with {data}")
        #input("Press ENTER to continue")
        cmd = ['/usr/bin/timeout']
        cmd += [f'{CONCOLIC_TIMEOUT}']
        cmd += [f'{self.script_path}']
        procs.clear()
        if self.no_swat_output:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)

        procs.append(proc)
        proc.wait()
        proc.communicate()
        """
        if self.no_swat_output:
            r = subprocess.run(f"timeout {CONCOLIC_TIMEOUT} {self.script_path}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            r = subprocess.run(f"timeout {CONCOLIC_TIMEOUT} {self.script_path}", shell=True)
        """

    def add_corpus_header(self, data):
        header = struct.pack('B', 1) + struct.pack('>I', len(data))
        #header = b''
        return (header + data)

    def strip_corpus_header(self, data):
        return data[5:]

    def get_solutions(self, original_path):
        try:
            with open(f'{self.instance_log_path}/generated_inputs.json', 'rt') as solution_file:
                loaded_data = json.loads(solution_file.read())
                for data in loaded_data:
                    raw_byte_data = eval(data['stream'])
                    self.logger.info(raw_byte_data)

                    byte_data_with_header = self.add_corpus_header(raw_byte_data)
                    #corpus_fn = f'{hashlib.sha1(byte_data_with_header).hexdigest()}-concolic'
                    corpus_fn = f'{hashlib.sha1(byte_data_with_header).hexdigest()}'
                    self.logger.info(f'{corpus_fn}: {raw_byte_data}')
                    self.logger.info(f'{data}')

                    if not (corpus_fn in self.generated_files):
                        self.generated_files[corpus_fn] = 1
                        full_path = f'{self.concolic_corpus_storage_path}/{corpus_fn}'
                        with self.mutex:
                            with open(full_path, 'wb') as corpus_file:
                                corpus_file.write(raw_byte_data)
                                corpus_file.close()
                                # put files to fuzzers here
                                for fuzzing_corpus_path in self.fuzzing_corpus_path_list:
                                    self.logger.info(fuzzing_corpus_path)
                                    fuzzing_corpus_filename = f'{fuzzing_corpus_path}/{corpus_fn}-concolic'
                                    with open(fuzzing_corpus_filename, 'wb') as fuzzing_corpus_file:
                                        fuzzing_corpus_file.write(byte_data_with_header)
                                    # copy this into exported file
                                    exported_filename = f'{self.exported_corpus_storage_path}/{corpus_fn}'
                                    shutil.copy(fuzzing_corpus_filename, exported_filename)
                                    self.logger.info(f'Corpus exported {fuzzing_corpus_filename}')
                                # log output
                                with open(self.init_value_path, 'rb') as init_value_file:
                                    init_data = init_value_file.read()
                                    self.logger.info(f"Solution {corpus_fn} from {original_path}: {init_data} to {raw_byte_data}\n")
                                    self.logger.info(f"Solution dict {data}")

                        self.concolic_corpus_queue.add_to_queue(full_path)

        except FileNotFoundError:
            pass


    def execute_newfile_watchdog(self):
        # create a file watchdog observer
        self.observer = Observer()
        for corpus_path in self.fuzzing_corpus_path_list:
            # add a handler for fuzzing corpus directory
            while not os.path.exists(corpus_path):
                self.logger.info(f'Waiting for registring a watchdog at {corpus_path}')
                time.sleep(1)
            self.observer.schedule(self.fuzzing_corpus_queue, corpus_path, recursive=False)
            self.logger.info(f'Registered a watchdog at {corpus_path}')

        # add a handler for concolic corpus storage directory
        #print(f'Registring a watchdog at {self.concolic_corpus_storage_path}')
        #self.observer.schedule(self.concolic_corpus_queue,
        #                        self.concolic_corpus_storage_path, recursive=False)

        # run observer thread
        self.observer.start()

        # mark observer has started
        time.sleep(0.1)
        self.observer_started = True

    def process_queue(self):
        #print(f"PQ PID: {os.getpid()}")
        is_concolic = False
        while True:
            concolic_runner.save_state()
            # STOP on SIGUSR1 signal
            if STOP_CONCOLIC:
                break
            # flip concolic flag; select concolic and jazzer corpora one by one
            is_concolic = not is_concolic

            if is_concolic:
                message = 'concolic'
            else:
                message = 'fuzzing'

            #input(f"\n\nPRESS ENTER to run {message}\n\n")

            popped = None
            data = None
            if is_concolic:
                queue = self.concolic_corpus_queue
                popped = queue.pop_from_queue()
                if not popped == None:
                    with open(popped, "rb") as f:
                        data = f.read()
                    self.logger.info(f"Concolic File {popped} Data read {data}")
                else:
                    pass
                    #print("Concolic popped is None")
            else:
                if True:
                    queue = self.fuzzing_corpus_queue
                    while True:
                        currently_popped = queue.pop_from_queue()
                        #print(f'currently_popped {currently_popped}')
                        if currently_popped == None:
                            #print(f'popped None')
                            popped = None
                            break
                        else:
                            if not os.path.exists(currently_popped[1]):
                                continue
                            popped = currently_popped[0]
                        try:
                            with open(popped, "rb") as f:
                                data = f.read()
                            self.logger.info(f"Fuzzing File {popped} Data read {data}")
                            break
                        except FileNotFoundError:
                            self.logger.info(f"File {popped} not found")

            # if nothing is in queue, sleep 0.01 second (not hogging the CPU cycles) and loop!
            if popped == None:
                time.sleep(0.01)
                continue

            self.logger.info(f"Running mode {message} for {popped}")
            if os.path.exists(self.init_value_path):
                os.unlink(self.init_value_path)

            with open(self.init_value_path, "wb") as f:
                if not is_concolic:
                    data = self.strip_corpus_header(data)
                f.write(data)

            try:
                # STOP on SIGUSR1 signal
                if STOP_CONCOLIC:
                    break
                self.run(popped)
                solutions = self.get_solutions(popped)
            except Exception as e:
                self.logger.info(repr(e))
                self.logger.info(traceback.format_exc())

        #for p in procs:
        #    print(f"{__file__} sending SIGKILL to child pid = {p.pid}")
        #    # kill timeout process
        #    try:
        #        os.kill(p.pid, signal.SIGKILL)
        #    except ProcessLookupError:
        #        # suppress error for already killed processes
        #        pass

        for p in procs:
            try:
                os.waitpid(p.pid, os.WUNTRACED)
            except ChildProcessError:
                pass

        os._exit(0)

    def execute_runner_thread(self):
        time.sleep(0.1)
        self.t = Thread(target=self.process_queue)
        self.t.start()

    def execute_threads(self):
        self.execute_newfile_watchdog()
        self.execute_runner_thread()
        self.wait()

    def generate_concolic_corpus(self, filename, data):
        concolic_fn = f"{self.concolic_corpus_storage_path}/{filename}"
        if os.path.exists(concolic_fn):
            os.unlink(concolic_fn)
        with self.mutex:
            with open(concolic_fn, "wb") as f:
                #f.write(self.add_corpus_header(data))
                f.write(data)
            self.concolic_corpus_queue.add_to_queue(concolic_fn)

    def wait(self):
        # wait until the observer thread starts
        while not self.observer_started:
            time.sleep(0.01)
        # add an initial concolic corpus
        self.generate_concolic_corpus('initial-concolic', b'\x00'*127)

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.observer.stop()
            #self.write_log_inputs()
            return


def parse_args():
    parser = argparse.ArgumentParser(description='Concolic Executor for Jazzer')
    parser.add_argument('-s', '--swat',
                        type=str, help='SWAT directory')
    parser.add_argument('-c', '--harness-class',
                        type=str, help='harness class')
    parser.add_argument('-l', '--logs',
                        type=str, help='log directory', default='logs')
    parser.add_argument('-p', '--class-path',
                        type=str, help='classpath for running SWAT')
    parser.add_argument('-v', '--sym-var',
                        type=str, help='symbolic variable', default='Ljava/lang/String')
    parser.add_argument('-f', '--fuzzing-paths',
                        type=str, help="fuzzing paths, corpus parent path per each fuzzer")
    parser.add_argument('-C', '--concolic-corpus-path',
                        type=str, help='concolic corpus path')
    parser.add_argument('-t', '--port',
                        type=str, help='http port')
    parser.add_argument('-z', '--prioritize-concolic',
                        help='run over concolic generate inputs', action='store_true', default=False)
    parser.add_argument('-n', '--no-swat-output',
                        help='suppress SWAT output', action='store_true', default=False)
    parser.add_argument('-H', '--harness-directory',
                        type=str, help="classpath for harness (location of com.aixcc...JenkinsTwo_Concolic.class..)")

    return parser.parse_args()


# Killing all via SIGUSR1
procs = []
concolic_runner = None

def sigusr1_handler(signum, stack):
    global STOP_CONCOLIC
    # Stop process_queue loop
    print(f"{__file__} received SIGUSR1 {len(procs)} {procs}")
    STOP_CONCOLIC = True
    concolic_runner.save_state()
    #for p in procs:
    #    print(f"{__file__} sending SIGKILL to child pid = {p.pid}")
    #    os.waitpid(p.pid, os.WUNTRACED)
    #    # kill timeout
    #    #try:
    #    #    os.kill(p.pid, signal.SIGKILL)
    #    #except ProcessLookupError:
    #    #    # suppress error for already killed processes
    #    #    pass

    #for p in procs:
    #    os.waitpid(p.pid, os.WUNTRACED)
    #os._exit(0)


def main():
    global concolic_runner
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    #instrument_targets = "jenkins/:hudson/Util/:org/jenkinsci/:com/cloudbees/:io/jenkins/:io/jenkins/blueocean/:io/jenkins.plugins/:io/jenkins/jenkinsfile:org/kohsuke/"
    args = parse_args()
    c = ConcolicRunner()
    concolic_runner = c
    c.set_args(args)
    c.clear_classpath()
    c.create_dirs()
    c.load_state()
    c.gen_swat_running_script()
    function_signature, instrument_targets = c.gen_func_signature_and_instrument_targets()
    c.gen_swat_config(function_signature, instrument_targets)
    #c.gen_swat_config(f'{c.harness_package_name_slash}/{c.harness_class}:fuzzerTestOneInput',
    #        f'{c.harness_package_name_slash}/:{instrument_targets}')
    c.execute_threads()

if __name__ == '__main__':
    main()
