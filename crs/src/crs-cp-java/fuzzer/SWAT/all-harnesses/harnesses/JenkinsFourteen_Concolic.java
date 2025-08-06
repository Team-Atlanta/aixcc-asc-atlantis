
package com.aixcc.jenkins.harnesses.fourteen;

import org.team_atlanta.*;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;
import javax.servlet.ReadListener;
import javax.servlet.ServletContext;
import javax.servlet.ServletInputStream;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import jenkins.model.Jenkins;
import hudson.PluginManager;
import org.kohsuke.stapler.*;

import aixcc.util.StaplerReplacer;

import org.mockito.Mockito;
import static org.mockito.Mockito.*;

public class JenkinsFourteen_Concolic {

    static PluginManager manager;
    static StaplerReplacer replacer;
    static ResponseImpl response;

    static {
        // Set which directories are allowed for file creation.
        System.setProperty("jazzer.fs_allowed_dirs", "/tmp/," + System.getProperty("java.io.tmpdir"));

        try {
            Jenkins j = Mockito.mock(Jenkins.class);
            manager = PluginManager.createDefault(j);

            replacer = new StaplerReplacer();
            replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));

            HttpServletResponse inner_response = Mockito.mock(HttpServletResponse.class);
            PrintWriter writer = new PrintWriter(new StringWriter());
            when(inner_response.getWriter()).thenReturn(writer);

            response = new ResponseImpl(replacer.stapler, inner_response);
            replacer.setCurrentResponse(response);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Throwable {
        // Number of requests, maximum of 10
        int numRequests = provider.consumeInt(0, 9);

        for (int i = 0; i < numRequests; i++) {
            // Pick method next
            int method = provider.consumeInt(0, 1);

            HttpServletRequest innerReq = Mockito.mock(HttpServletRequest.class);

            // Fuzz with a random number of parameters up to 10
            int numParams = provider.consumeInt(0, 9);
            for (int j = 0; j < numParams; j++) {
                String paramName = provider.consumeString(20);
                String value = provider.consumeString(50);
                when(innerReq.getParameter(paramName)).thenReturn(value);
            }

            // Fuzz with content type
            boolean setContentType = provider.consumeBoolean();
            if (setContentType) {
                String contentType = provider.consumeString(30);
                when(innerReq.getContentType()).thenReturn(contentType);
            }

            // Maybe fuzz with a random body of the request
            if (provider.consumeBoolean()) {
                int bodyLength = provider.consumeInt(0, 1000);
                byte[] body = provider.consumeBytes(bodyLength);

                ByteArrayInputStream byteStream = new ByteArrayInputStream(body);

                when(innerReq.getInputStream()).thenAnswer(input -> {
                    return new DelegatingServletInputStream(byteStream);
                });
                when(innerReq.getContentLength()).thenReturn(bodyLength);
            }

            RequestImpl req = new RequestImpl(replacer.stapler, innerReq, Collections.emptyList(), null);
            replacer.setCurrentRequest(req);

            if (method == 0) {
                HttpResponse res = manager.doCreateNewUpload(req);
            } else if (method == 1) {
                HttpResponse res = manager.doPerformUpload(req);
            }
        }
    }

    public static class DelegatingServletInputStream extends ServletInputStream {
        // ... (rest of the class remains unchanged)
    }

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        
        fuzzerTestOneInput(provider);
    }
}
