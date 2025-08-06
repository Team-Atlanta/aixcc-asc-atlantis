

package com.aixcc.jenkins.harnesses.seven;

import hudson.ProxyConfiguration;
import io.jenkins.plugins.toyplugin.UserRemoteConfig;
import jenkins.model.Jenkins;

import org.kohsuke.stapler.*;
import org.mockito.Mockito;

import java.io.FileInputStream;
import java.util.Collections;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;

import static org.mockito.Mockito.*;

import aixcc.util.StaplerReplacer;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import java.nio.ByteBuffer;

public class JenkinsSeven_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        String data;
        
        int stringLength = provider.consumeInt(0, 20480);
        ByteBuffer buffer = ByteBuffer.allocate(stringLength);
        for (int i = 0; i < stringLength; i++) {
            buffer.put(provider.consumeByte());
        }
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
        
        JenkinsSeven.fuzzerTestOneInput(data);
    }
}
