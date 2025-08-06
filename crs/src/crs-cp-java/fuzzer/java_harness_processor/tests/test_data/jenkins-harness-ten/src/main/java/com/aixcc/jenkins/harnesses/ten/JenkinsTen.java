package com.aixcc.jenkins.harnesses.ten;

import static org.mockito.Mockito.*;

import aixcc.util.StaplerReplacer;
import io.jenkins.plugins.toyplugin.StateMonitor;
import org.mockito.Mockito;
import org.kohsuke.stapler.*;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import io.jenkins.plugins.toyplugin.SecretMessage;
import jenkins.model.Jenkins;

public class JenkinsTen {

    static SecretMessage action;
    static StaplerReplacer replacer;
    static ResponseImpl response;

    public static void fuzzerInitialize() throws Throwable {
        Jenkins j = Mockito.mock(Jenkins.class);
        when(j.hasPermission(Jenkins.ADMINISTER)).thenReturn(false);

        action = new SecretMessage();
        action.setJenkins(j);

        replacer = new StaplerReplacer();
        replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));

        HttpServletResponse inner_response = Mockito.mock(HttpServletResponse.class);
        PrintWriter writer = new PrintWriter(new StringWriter());
        when(inner_response.getWriter()).thenReturn(writer);

        response = new ResponseImpl(replacer.stapler, inner_response);
        replacer.setCurrentResponse(response);
    }

    public static void fuzzerTestOneInput(byte[] data) throws Throwable {

        String whole = new String(data);
        String[] parts = whole.split("\0");
        if (parts.length != 8)
            return;

        HttpServletRequest inner_request = Mockito.mock(HttpServletRequest.class);
        when(inner_request.getParameter(parts[0])).thenReturn(parts[1]);
        when(inner_request.getParameter(parts[2])).thenReturn(parts[3]);
        when(inner_request.getParameter(parts[4])).thenReturn(parts[5]);
        when(inner_request.getParameter(parts[6])).thenReturn(parts[7]);
        RequestImpl request = new RequestImpl(replacer.stapler, inner_request, Collections.emptyList(), null);
        replacer.setCurrentRequest(request);
        action.doPerform(request, response);
    }

}
