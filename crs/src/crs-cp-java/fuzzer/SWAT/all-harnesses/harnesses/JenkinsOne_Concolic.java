
package com.aixcc.jenkins.harnesses.one;

import org.team_atlanta.*;
import io.jenkins.plugins.toyplugin.UserRemoteConfig;
import org.kohsuke.stapler.*;
import org.mockito.Mockito;

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;

import static org.mockito.Mockito.*;

import aixcc.util.StaplerReplacer;

public class JenkinsOne_Concolic {

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

    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception {
        int numParts = provider.consumeInt(3, 30);
        StringBuilder wholeBuilder = new StringBuilder();

        for (int i = 0; i < numParts; i++) {
            wholeBuilder.append(provider.consumeString(10));
            if (i < numParts - 1) {
                wholeBuilder.append(":");
            }
        }

        String whole = wholeBuilder.toString();
        String[] parts = whole.split(":");
        System.out.println("parts.length: " + parts.length);
        if (parts.length < 3 && parts.length % 3 != 0)
            return;

        HttpServletRequest inner_request = Mockito.mock(HttpServletRequest.class);
        RequestImpl request = Mockito.mock(RequestImpl.class);
        for (int i = 0; i < parts.length; i += 3) {
            when(inner_request.getParameter("cmd")).thenReturn(parts[i]);
            when(inner_request.getParameter("value")).thenReturn(parts[i + 1]);
            when(inner_request.getParameter("checksum")).thenReturn(parts[i + 2]);
            request = new RequestImpl(replacer.stapler, inner_request, Collections.emptyList(), null);
            replacer.setCurrentRequest(request);
            urc.modCounter(request, response);
        }

        urc.incCounter();
    }

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        fuzzerInitialize();
        fuzzerTestOneInput(provider);
    }
}
