

package com.aixcc.jenkins.harnesses.one;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import io.jenkins.plugins.toyplugin.UserRemoteConfig;
import org.kohsuke.stapler.*;
import org.mockito.Mockito;
import java.nio.ByteBuffer;

public class JenkinsOne_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        String data;
        
        ByteBuffer buffer = ByteBuffer.allocate(20480);
        int numParts = provider.consumeInt(1, 10);  // Consume a random number of parts (1-10)
        
        for (int i = 0; i < numParts; i++) {
            String cmd = provider.consumeString(10);
            String value = provider.consumeString(10);
            String checksum = provider.consumeString(10);
            
            buffer.put(cmd.getBytes());
            buffer.put(":".getBytes());
            buffer.put(value.getBytes());
            buffer.put(":".getBytes());
            buffer.put(checksum.getBytes());
            
            if (i < numParts - 1) {
                buffer.put(":".getBytes());
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
        
        JenkinsOne.fuzzerTestOneInput(data);
    }
}
