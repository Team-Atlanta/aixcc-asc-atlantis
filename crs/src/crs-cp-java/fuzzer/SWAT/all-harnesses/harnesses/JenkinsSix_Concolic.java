
package com.aixcc.jenkins.harnesses.six;

import org.team_atlanta.*;
import aixcc.util.StaplerReplacer;
import io.jenkins.plugins.toyplugin.StateMonitor;
import org.mockito.Mockito;
import static org.mockito.Mockito.*;
import org.kohsuke.stapler.*;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class JenkinsSix_Concolic {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Throwable {
        String part1 = provider.consumeString(10);
        String part2 = provider.consumeString(20);
        String part3 = provider.consumeString(10);
        String part4 = provider.consumeString(20);

        String whole = part1 + "\0" + part2 + "\0" + part3 + "\0" + part4;
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

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        
        fuzzerTestOneInput(provider);
    }
}
