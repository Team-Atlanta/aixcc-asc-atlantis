package com.aixcc.jenkins.harnesses.three;

import hudson.ProxyConfiguration;
import hudson.security.AccessDeniedException3;
import jenkins.model.Jenkins;

import org.kohsuke.stapler.*;
import org.mockito.Mockito;
import org.springframework.security.core.Authentication;

import java.io.FileInputStream;
import java.util.Collections;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;

import static org.mockito.Mockito.*;

import aixcc.util.StaplerReplacer;

public class JenkinsThree {

    public static void fuzzerTestOneInput(byte[] data) throws Exception {
        String whole = new String(data);
        String[] parts = whole.split("\0");
        if (parts.length == 5) {
            Authentication a = Mockito.mock(Authentication.class);
            when(a.getName()).thenReturn("mock");
            Jenkins j = Mockito.mock(Jenkins.class);
            doThrow(new AccessDeniedException3(a, Jenkins.ADMINISTER))
                .when(j)
                .checkPermission(Jenkins.ADMINISTER);
            StaplerReplacer replacer = new StaplerReplacer();
            replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));
            HttpServletRequest innerReq = Mockito.mock(HttpServletRequest.class);
            when(innerReq.getParameter(parts[0])).thenReturn(parts[1]);
            when(innerReq.getParameter(parts[2])).thenReturn(parts[3]);
            RequestImpl req = new RequestImpl(replacer.stapler, innerReq, Collections.emptyList(), null);
            ResponseImpl rsp = Mockito.mock(ResponseImpl.class);
            try {
                new ProxyConfiguration.DescriptorImpl2(j).doValidateProxy(parts[4], req, rsp);
            } catch (AccessDeniedException3 e) {}
        }
    }
}