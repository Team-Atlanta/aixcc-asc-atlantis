package com.aixcc.jenkins.harnesses.one;

import io.jenkins.plugins.toyplugin.UserRemoteConfig;

import org.kohsuke.stapler.*;
import org.mockito.Mockito;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import static org.mockito.Mockito.*;

import aixcc.util.StaplerReplacer;

public class JenkinsOne {

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

        String whole = new String(data);
        String[] parts = whole.split(":");
        System.out.println("parts.length: " + parts.length);
        if (parts.length < 3 && parts.length % 3 != 0)
            return;

        HttpServletRequest inner_request = Mockito.mock(HttpServletRequest.class);
        RequestImpl request = Mockito.mock(RequestImpl.class);
        for(int i = 0; i < parts.length; i += 3) {
            when(inner_request.getParameter("cmd")).thenReturn(parts[i]);
            when(inner_request.getParameter("value")).thenReturn(parts[i+1]);
            when(inner_request.getParameter("checksum")).thenReturn(parts[i+2]);
            request = new RequestImpl(replacer.stapler, inner_request, Collections.emptyList(), null);
            replacer.setCurrentRequest(request);
            urc.modCounter(request, response);
        }

        urc.incCounter();
    }
}
