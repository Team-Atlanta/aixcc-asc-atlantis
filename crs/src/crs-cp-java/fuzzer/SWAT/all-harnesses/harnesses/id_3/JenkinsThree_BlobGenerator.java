

package com.aixcc.jenkins.harnesses.three;

import hudson.ProxyConfiguration;
import hudson.security.AccessDeniedException3;
import jenkins.model.Jenkins;

import org.kohsuke.stapler.*;
import org.mockito.Mockito;
import org.springframework.security.core.Authentication;

import java.io.FileInputStream;
import java.util.Collections;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;

import static org.mockito.Mockito.*;

import aixcc.util.StaplerReplacer;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import java.nio.ByteBuffer;

public class JenkinsThree_BlobGenerator {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception, Throwable {
        String data;
        
        ByteBuffer buffer = ByteBuffer.allocate(20480);
        
        String part1 = provider.consumeString(100);
        String part2 = provider.consumeString(100);
        String part3 = provider.consumeString(100);
        String part4 = provider.consumeString(100);
        String part5 = provider.consumeString(100);
        
        data = part1 + "\0" + part2 + "\0" + part3 + "\0" + part4 + "\0" + part5;
        
        buffer.put(data.getBytes());
        byte[] byteArray = buffer.array();
        
        LocalBlobGenerator.fuzzerTestOneInput(byteArray);
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
        
        JenkinsThree.fuzzerTestOneInput(data);
    }
}
