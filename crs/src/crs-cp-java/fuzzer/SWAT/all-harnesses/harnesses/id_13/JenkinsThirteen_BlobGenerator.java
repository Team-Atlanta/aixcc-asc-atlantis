

package com.aixcc.jenkins.harnesses.thirteen;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import hudson.ProxyConfiguration;
import io.jenkins.plugins.toyplugin.UserRemoteConfig;
import jenkins.model.Jenkins;
import org.kohsuke.stapler.*;
import org.mockito.Mockito;
import java.io.FileInputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.ByteBuffer;
import java.util.Collections;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import static org.mockito.Mockito.*;
import aixcc.util.StaplerReplacer;

public class JenkinsThirteen_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        ByteBuffer bb = ByteBuffer.allocate(20480);
        
        int commandCount = provider.consumeInt(0, 10);
        bb.putInt(commandCount);
        
        for (int i = 0; i < commandCount; i++) {
            int command = provider.consumeInt(0, 1);
            bb.putInt(command);
            
            if (command == 0) {
                bb.putInt(provider.consumeInt(0, Integer.MAX_VALUE)); // cmd
                bb.putInt(provider.consumeInt(0, Integer.MAX_VALUE)); // value
                bb.putInt(provider.consumeInt(0, Integer.MAX_VALUE)); // checksum
            }
        }
        
        byte[] data = new byte[bb.position()];
        bb.flip();
        bb.get(data);
        
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
        
        JenkinsThirteen.fuzzerTestOneInput(data);
    }
}
