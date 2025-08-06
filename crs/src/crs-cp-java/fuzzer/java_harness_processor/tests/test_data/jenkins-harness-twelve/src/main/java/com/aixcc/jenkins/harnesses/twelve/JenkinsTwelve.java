package com.aixcc.jenkins.harnesses.twelve;

import io.jenkins.plugins.toyplugin.Script;
import jenkins.model.Jenkins;
import aixcc.util.StaplerReplacer;
import hudson.model.Job;
import hudson.model.Queue;
import io.jenkins.plugins.toyplugin.StateMonitor;
import org.mockito.Mockito;
import static org.mockito.Mockito.*;
import org.kohsuke.stapler.*;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;

import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import javax.script.ScriptException;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import groovy.lang.GroovyClassLoader;
import groovy.lang.GroovyShell;


public class JenkinsTwelve {
    public static void fuzzerTestOneInput(byte[] data) throws Exception {

        String value = new String(data);
        Jenkins mockJ = Mockito.mock(Jenkins.class);
        when(mockJ.hasPermission(Job.CONFIGURE)).thenReturn(true);
        try {
            new Script(mockJ).doCheckScriptCompile(value);
        } catch (ScriptException e) {}
    }
}