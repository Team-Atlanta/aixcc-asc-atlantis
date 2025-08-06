

package com.aixcc.jenkins.harnesses.fourteen;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import java.nio.ByteBuffer;
import java.io.ByteArrayInputStream;
import java.io.DataInputStream;

public class JenkinsFourteen_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        ByteBuffer buffer = ByteBuffer.allocate(20480);

        // Number of requests (0-9)
        buffer.put((byte) (provider.consumeByte() % 10));

        for (int i = 0; i < 10; i++) {
            // Method (0 or 1)
            buffer.put((byte) (provider.consumeByte() % 2));

            // Number of parameters (0-9)
            buffer.put((byte) (provider.consumeByte() % 10));

            for (int j = 0; j < 10; j++) {
                String paramName = provider.consumeString(100);
                String paramValue = provider.consumeString(100);
                buffer.putShort((short) paramName.length());
                buffer.put(paramName.getBytes());
                buffer.putShort((short) paramValue.length());
                buffer.put(paramValue.getBytes());
            }

            // Set content type
            buffer.put((byte) (provider.consumeBoolean() ? 1 : 0));
            if (buffer.get(buffer.position() - 1) == 1) {
                String contentType = provider.consumeString(50);
                buffer.putShort((short) contentType.length());
                buffer.put(contentType.getBytes());
            }

            // Request body
            buffer.put((byte) (provider.consumeBoolean() ? 1 : 0));
            if (buffer.get(buffer.position() - 1) == 1) {
                int bodyLength = provider.consumeInt(0, 1000);
                buffer.putShort((short) bodyLength);
                buffer.put(provider.consumeBytes(bodyLength));
            }
        }

        byte[] data = new byte[buffer.position()];
        buffer.flip();
        buffer.get(data);

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
        
        JenkinsFourteen.fuzzerTestOneInput(data);
    }
}
