

package com.aixcc.jenkins.harnesses.nine;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import io.jenkins.plugins.toyplugin.Api;
import jenkins.model.Jenkins;
import aixcc.util.StaplerReplacer;
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
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.nio.ByteBuffer;

public class JenkinsNine_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        String data;
        
        String part1 = provider.consumeString(100);
        String part2 = provider.consumeString(100);
        String part3 = provider.consumeString(100);
        
        ByteBuffer buffer = ByteBuffer.allocate(20480);
        buffer.put(part1.getBytes());
        buffer.put((byte) 0);
        buffer.put(part2.getBytes());
        buffer.put((byte) 0);
        buffer.put(part3.getBytes());
        
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
        
        JenkinsNine.fuzzerTestOneInput(data);
    }
}
