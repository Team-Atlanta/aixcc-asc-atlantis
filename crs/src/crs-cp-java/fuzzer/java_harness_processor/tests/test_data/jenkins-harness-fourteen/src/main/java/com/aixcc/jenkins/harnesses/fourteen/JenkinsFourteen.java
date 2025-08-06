package com.aixcc.jenkins.harnesses.fourteen;

import java.util.List;
import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
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

public class JenkinsFourteen {

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

    public static void fuzzerTestOneInput(byte[] data) throws Throwable {
        DataInputStream stream = new DataInputStream(new ByteArrayInputStream(data));
        fuzzer(stream);
    }

	public static void fuzzer(DataInputStream data) throws Throwable {
        // First is number of requests, maximum of 10.
        int numRequests = data.readByte() % 10;

        for (int i = 0; i < numRequests; i++) {
            // Pick method next.
            int method = data.readByte() % 2;

            HttpServletRequest innerReq = Mockito.mock(HttpServletRequest.class);

            // Fuzz with a random number of parameters up to 10.
            int numParams = data.readByte() % 10;
            for (int j = 0; j < numParams; j++) {
                String paramName = data.readUTF();
                String value = data.readUTF();
                when(innerReq.getParameter(paramName)).thenReturn(value);
            }

            // Fuzz with a random number of headers up to 10.
            boolean setContentType = data.readBoolean();
            if (setContentType) {
                String contentType = data.readUTF();
                when(innerReq.getContentType()).thenReturn(contentType);
            }

            // Maybe fuzz with a random body of the request.
            if (data.readBoolean()) {
                int bodyLength = data.readUnsignedShort();
                byte[] body = new byte[bodyLength];
                data.readFully(body);

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

        private final InputStream sourceStream;
    
        /**
         * Create a DelegatingServletInputStream for the given source stream.
         * @param sourceStream the source stream (never <code>null</code>)
         */
        public DelegatingServletInputStream(InputStream sourceStream) {
            this.sourceStream = sourceStream;
        }
    
        /**
         * Return the underlying source stream (never <code>null</code>).
         */
        public final InputStream getSourceStream() {
            return this.sourceStream;
        }
    
        public int read() throws IOException {
            return this.sourceStream.read();
        }
    
        public void close() throws IOException {
            super.close();
            this.sourceStream.close();
        }

        public boolean isFinished() {
            try {
                return this.sourceStream.available() == 0;
            } catch (IOException e) {
                return true;
            }
        }

        public boolean isReady() {
            return true;
        }

        public void setReadListener(ReadListener readListener) {
            throw new UnsupportedOperationException();
        }
    }
}
