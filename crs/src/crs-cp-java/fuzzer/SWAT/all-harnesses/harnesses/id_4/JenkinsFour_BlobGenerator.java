

package com.aixcc.jenkins.harnesses.four;

import hudson.model.FreeStyleBuild;
import io.jenkins.plugins.coverage.CoverageProcessor;
import org.mockito.Mockito;
import static org.mockito.Mockito.*;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import java.util.Base64;

public class JenkinsFour_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        String data;
        
        String reportName = provider.consumeString(100);
        String serializedObject = Base64.getEncoder().encodeToString(provider.consumeBytes(1000));
        
        ByteBuffer buffer = ByteBuffer.allocate(20480);
        buffer.put(reportName.getBytes());
        buffer.put((byte) 0);
        buffer.put(serializedObject.getBytes());
        
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
        
        JenkinsFour.fuzzerTestOneInput(data);
    }
}
