

package com.aixcc.jenkins.harnesses.twelve;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
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

public class JenkinsTwelve_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        String data;
        
        int stringLength = provider.consumeInt(0, 20480);
        data = provider.consumeString(stringLength);
            
        LocalBlobGenerator.fuzzerTestOneInput(data.getBytes());
    }
}


class LocalBlobGenerator {
    public static void fuzzerTestOneInput(byte[] data) throws Exception, Throwable 
    {
        String filename = System.getenv("POV_FILENAME");
        if (null == filename) 
            filename = "/work/tmp_blob";
            
        java.io.FileOutputStream fos = new java.io.FileOutputStream(filename);
        fos.write(data);
        fos.close();
        
        JenkinsTwelve.fuzzerTestOneInput(data);
    }
}
