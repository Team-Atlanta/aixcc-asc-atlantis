
package com.aixcc.jenkins.harnesses.nine;

import org.team_atlanta.*;
import io.jenkins.plugins.toyplugin.Api;
import jenkins.model.Jenkins;
import aixcc.util.StaplerReplacer;
import hudson.model.Queue;
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

public class JenkinsNine_Concolic {

    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception {
        String part1 = provider.consumeString(20);
        String part2 = provider.consumeString(20);
        String part3 = provider.consumeString(20);

        String whole = part1 + "\0" + part2 + "\0" + part3;
        String[] parts = whole.split("\0");
        System.out.println(parts.length);
        if (parts.length != 3)
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

        String xpath = parts[2];
        String wrapper = null;
        String tree = null;

        Jenkins mockJ = Mockito.mock(Jenkins.class);
        new Api(mockJ).doXml(req, rsp, xpath, wrapper, tree, 0);
    }

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        
        fuzzerTestOneInput(provider);
    }
}
