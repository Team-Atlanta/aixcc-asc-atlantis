package com.aixcc.jenkins.harnesses.seven;

import hudson.ProxyConfiguration;
import io.jenkins.plugins.toyplugin.UserRemoteConfig;
import jenkins.model.Jenkins;

import org.kohsuke.stapler.*;
import org.mockito.Mockito;

import java.io.FileInputStream;
import java.util.Collections;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;

import static org.mockito.Mockito.*;

import aixcc.util.StaplerReplacer;

public class JenkinsSeven {

    public static void fuzzerTestOneInput(byte[] data) throws Exception {

        String value = new String(data);
        new UserRemoteConfig().doCheckUrl(value);
    }
}