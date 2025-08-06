

package com.aixcc.jenkins.harnesses.eight;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import java.nio.ByteBuffer;

import static org.mockito.Mockito.*;

import java.io.FileInputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import com.code_intelligence.jazzer.api.BugDetectors;
import io.jenkins.plugins.toyplugin.AuthAction;

import org.kohsuke.stapler.RequestImpl;
import org.kohsuke.stapler.ResponseImpl;
import org.kohsuke.stapler.WebApp;
import org.mockito.Mockito;

import aixcc.util.StaplerReplacer;

public class JenkinsEight_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        String data;
        
        ByteBuffer buffer = ByteBuffer.allocate(20480);
        
        String part1 = provider.consumeString(100);
        String part2 = provider.consumeString(100);
        String part3 = provider.consumeString(100);
        String part4 = provider.consumeString(100);
        
        buffer.put(part1.getBytes());
        buffer.put((byte) 0);
        buffer.put(part2.getBytes());
        buffer.put((byte) 0);
        buffer.put(part3.getBytes());
        buffer.put((byte) 0);
        buffer.put(part4.getBytes());
        
        data = new String(buffer.array());
        
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
        
        JenkinsEight.fuzzerTestOneInput(data);
    }
}
