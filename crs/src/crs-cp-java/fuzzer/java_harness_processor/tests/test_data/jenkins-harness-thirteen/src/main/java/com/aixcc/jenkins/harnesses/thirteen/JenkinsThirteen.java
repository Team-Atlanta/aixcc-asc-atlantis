package com.aixcc.jenkins.harnesses.thirteen;

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

public class JenkinsThirteen {

    static ResponseImpl response;
    static StaplerReplacer replacer;
    static UserRemoteConfig urc;

    public static void fuzzerInitialize() throws Throwable {

        replacer = new StaplerReplacer();
        replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));

        HttpServletResponse inner_response = Mockito.mock(HttpServletResponse.class);
        PrintWriter writer = new PrintWriter(new StringWriter());
        when(inner_response.getWriter()).thenReturn(writer);

        response = new ResponseImpl(replacer.stapler, inner_response);
        replacer.setCurrentResponse(response);

        urc = new UserRemoteConfig();
    }

    public static void fuzzerTestOneInput(byte[] data) throws Exception {
        byte[] bd = data;
        ByteBuffer bb = ByteBuffer.wrap(bd);

        int command_count = bb.getInt();
        HttpServletRequest inner_request = Mockito.mock(HttpServletRequest.class);
        RequestImpl request = Mockito.mock(RequestImpl.class);

        for(int i = 0; i < command_count; i++) {
            int command = bb.getInt();
            switch(command) {
                case 0:
                    String cmd = Integer.toString(bb.getInt());
                    when(inner_request.getParameter("cmd")).thenReturn(cmd);
                    String value = Integer.toString(bb.getInt());
                    when(inner_request.getParameter("value")).thenReturn(value);
                    String checksum = Integer.toString(bb.getInt());
                    when(inner_request.getParameter("checksum")).thenReturn(checksum);
                    request = new RequestImpl(replacer.stapler, inner_request, Collections.emptyList(), null);
                    replacer.setCurrentRequest(request);
                    System.out.println(cmd + " , " + value + ", " + checksum);
                    urc.modCounter(request, response);
                    break;
                case 1:
                    urc.incCounter();
                    break;
            }
        }
    }
}
