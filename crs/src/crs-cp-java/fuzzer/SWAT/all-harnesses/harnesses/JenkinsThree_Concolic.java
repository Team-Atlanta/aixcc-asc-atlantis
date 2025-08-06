
package com.aixcc.jenkins.harnesses.three;

import hudson.ProxyConfiguration;
import hudson.security.AccessDeniedException3;
import jenkins.model.Jenkins;
import org.kohsuke.stapler.*;
import org.mockito.Mockito;
import org.springframework.security.core.Authentication;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import static org.mockito.Mockito.*;
import aixcc.util.StaplerReplacer;
import org.team_atlanta.*;

import java.util.Collections;

public class JenkinsThree_Concolic {

    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception {
        String part1 = provider.consumeString(10);
        String part2 = provider.consumeString(10);
        String part3 = provider.consumeString(10);
        String part4 = provider.consumeString(10);
        String part5 = provider.consumeString(10);

        Authentication a = Mockito.mock(Authentication.class);
        when(a.getName()).thenReturn("mock");
        Jenkins j = Mockito.mock(Jenkins.class);
        doThrow(new AccessDeniedException3(a, Jenkins.ADMINISTER))
            .when(j)
            .checkPermission(Jenkins.ADMINISTER);
        StaplerReplacer replacer = new StaplerReplacer();
        replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));
        HttpServletRequest innerReq = Mockito.mock(HttpServletRequest.class);
        when(innerReq.getParameter(part1)).thenReturn(part2);
        when(innerReq.getParameter(part3)).thenReturn(part4);
        RequestImpl req = new RequestImpl(replacer.stapler, innerReq, Collections.emptyList(), null);
        ResponseImpl rsp = Mockito.mock(ResponseImpl.class);
        try {
            new ProxyConfiguration.DescriptorImpl2(j).doValidateProxy(part5, req, rsp);
        } catch (AccessDeniedException3 e) {}
    }

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        
        fuzzerTestOneInput(provider);
    }
}
