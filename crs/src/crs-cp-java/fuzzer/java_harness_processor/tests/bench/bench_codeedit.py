import os
import re
import argparse

from bench_init import *

from harness.llm import ChatBot
from harness.common.project import Project
from harness.utils.logger import Log
from harness.utils.builder import CPBuilder
from harness.java_static.code_editor import LLMJavaCodeEditor
from harness.generator import LLMConcolicHarnessGenerator
from harness.common.harness import Harness


argparse = argparse.ArgumentParser()
argparse.add_argument("-n", "--num", type=int, default=3)
args = argparse.parse_args()

num_of_exec = args.num


test_code = '''package com.aixcc.jenkins.harnesses.nine;

import io.jenkins.plugins.toyplugin.Api;
import jenkins.model.Jenkins;
import aixcc.util.StaplerReplacer;
import hudson.model.Queue;
import io.jenkins.plugins.toyplugin.StateMonitor;
import org.mockito.Mockito;

class JenkinsNine_AAAA {
    public static void fuzzerTestOneInput(byte[] data) throws Exception {

        String whole = new String(data);
        String[] parts = whole.split(":");
        JenkinsNine.fuzzerTestOneInput(data);
    }
}
public class JenkinsNine {
    public static void fuzzerTestOneInput(byte[] data) throws Exception {

        String whole = new String(data);
        String[] parts = whole.split(":");
    }
}'''

expected_code = '''import io.jenkins.plugins.toyplugin.Api;
import jenkins.model.Jenkins;
import aixcc.util.StaplerReplacer;
import hudson.model.Queue;
import io.jenkins.plugins.toyplugin.StateMonitor;
import org.mockito.Mockito;

class JenkinsNine_AAAA {
    public static void fuzzerTestOneInput(byte[] data) throws Exception {

        String whole = new String(data);
        String[] parts = whole.split(":");
        JenkinsNine_MyTest.fuzzerTestOneInput(data);
    }
}
public class JenkinsNine_MyTest {
    public static void fuzzerTestOneInput(byte[] data) throws Exception {

        String whole = new String(data);
        String[] parts = whole.split(":");
    }
}'''

class LLMJavaCodeEditorTest(TestBench):
    def setUp(self):
        pass
    
    def batch(self):
        editor = LLMJavaCodeEditor(test_code)
        editor.change_class_name("JenkinsNine", "JenkinsNine_MyTest")
        editor.change_package("")
        code = editor.get_code().strip()
        
        if code != expected_code:
            print("Assert ----------- Generated code")
            print(code)
            return False
        return True


if __name__ == "__main__":
    test = LLMJavaCodeEditorTest()
    test.name = "LLMJavaCodeEditorTest"
    
    res = test.bench(n=num_of_exec)
    print("success rate: ", res.count(True), "/", num_of_exec)