

package com.aixcc.jenkins.harnesses.ten;

import static org.mockito.Mockito.*;

import aixcc.util.StaplerReplacer;
import io.jenkins.plugins.toyplugin.StateMonitor;
import org.mockito.Mockito;
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
import io.jenkins.plugins.toyplugin.SecretMessage;
import jenkins.model.Jenkins;
import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import java.nio.ByteBuffer;

public class JenkinsTen_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        String data;
        
        ByteBuffer buffer = ByteBuffer.allocate(20480);
        
        for (int i = 0; i < 8; i++) {
            String part = provider.consumeString(100);
            buffer.put(part.getBytes());
            if (i < 7) {
                buffer.put((byte) 0);
            }
        }
        
        data = new String(buffer.array(), 0, buffer.position());
        
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
        
        JenkinsTen.fuzzerTestOneInput(data);
    }
}
