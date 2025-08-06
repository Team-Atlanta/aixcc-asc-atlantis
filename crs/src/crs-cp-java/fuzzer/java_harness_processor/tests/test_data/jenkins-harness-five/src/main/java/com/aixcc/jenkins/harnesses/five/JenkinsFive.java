package com.aixcc.jenkins.harnesses.five;
import org.kohsuke.stapler.*;
import org.mockito.Mockito;
import static org.mockito.Mockito.*;

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.FileInputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;

import io.jenkins.plugins.toyplugin.UserNameAction;
import aixcc.util.StaplerReplacer;

public class JenkinsFive {

    public static void fuzzerTestOneInput(byte[] data) throws Throwable {
        String whole = new String(data);
        String[] parts = whole.split("\0");
        if (parts.length != 4) {
            return;
        }

        StaplerReplacer replacer = new StaplerReplacer();
        replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));
        HttpServletRequest inner_req = Mockito.mock(HttpServletRequest.class);
        RequestImpl req = new RequestImpl(replacer.stapler, inner_req, Collections.emptyList(), null);
        HttpServletResponse inner_rsp = Mockito.mock(HttpServletResponse.class);
        ResponseImpl rsp = new ResponseImpl(replacer.stapler, inner_rsp);
        StringWriter sw = new StringWriter();
        PrintWriter pw = new PrintWriter(sw);
        replacer.setCurrentRequest(req);
        replacer.setCurrentResponse(rsp);
        when(inner_req.getParameter(parts[0])).thenReturn(parts[1]);
        when(inner_req.getParameter(parts[2])).thenReturn(parts[3]);
        when(inner_rsp.getWriter()).thenReturn(pw);
        new UserNameAction().doGetName(req, rsp);
    }
}