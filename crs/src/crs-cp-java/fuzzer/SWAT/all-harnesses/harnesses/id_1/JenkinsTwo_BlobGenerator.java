

package com.aixcc.jenkins.harnesses.two;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import java.nio.ByteBuffer;
import java.util.Arrays;

public class JenkinsTwo_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        ByteBuffer buf = ByteBuffer.allocate(20480);

        // Add picker (Integer)
        buf.putInt(provider.consumeInt(0, Integer.MAX_VALUE));

        // Add count (Integer)
        int count = provider.consumeInt(0, 255);
        buf.putInt(count);

        // Add request header name
        String headerName = provider.consumeString(10);
        buf.put(headerName.getBytes());
        buf.put((byte) 0);

        // Add request header value
        String headerValue = provider.consumeString(10);
        buf.put(headerValue.getBytes());
        buf.put((byte) 0);

        // Add command
        String command = provider.consumeString(20);
        buf.put(command.getBytes());
        buf.put((byte) 0);

        // Convert ByteBuffer to byte array
        byte[] data = Arrays.copyOf(buf.array(), buf.position());

        LocalBlobGenerator.fuzzerTestOneInput(data);
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
        
        JenkinsTwo.fuzzerTestOneInput(data);
    }
}
