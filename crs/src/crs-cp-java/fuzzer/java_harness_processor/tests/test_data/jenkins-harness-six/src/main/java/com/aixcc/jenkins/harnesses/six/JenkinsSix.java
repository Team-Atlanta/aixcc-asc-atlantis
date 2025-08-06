package com.aixcc.jenkins.harnesses.six;
import aixcc.util.StaplerReplacer;
import io.jenkins.plugins.toyplugin.StateMonitor;
import org.mockito.Mockito;
import static org.mockito.Mockito.*;
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

public class JenkinsSix {
    public static void fuzzerTestOneInput(byte[] data) throws Throwable {
        String whole = new String(data);
        String[] parts = whole.split("\0");
        if (parts.length != 4)
            return;

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
        when(inner_rsp.getWriter()).thenReturn(pw);
        when(inner_req.getParameter(parts[0])).thenReturn(parts[1]);
        when(inner_req.getParameter(parts[2])).thenReturn(parts[3]);
        new StateMonitor().doCheck(req, rsp);
    }

}
