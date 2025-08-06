package com.aixcc.jenkins.harnesses.eight;

import static org.mockito.Mockito.*;

import java.io.FileInputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import com.code_intelligence.jazzer.api.BugDetectors;
import io.jenkins.plugins.toyplugin.AuthAction;

import org.kohsuke.stapler.RequestImpl;
import org.kohsuke.stapler.ResponseImpl;
import org.kohsuke.stapler.WebApp;
import org.mockito.Mockito;

import aixcc.util.StaplerReplacer;

public class JenkinsEight {

  public static void fuzzerTestOneInput(byte[] data) throws Exception {
    BugDetectors.allowNetworkConnections();

    String whole = new String(data);
    String[] parts = whole.split("\0");
    if (parts.length != 4)
      return;

    AuthAction action = new AuthAction();

    StaplerReplacer replacer = new StaplerReplacer();
    replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));

    HttpServletRequest inner_request = Mockito.mock(HttpServletRequest.class);
    when(inner_request.getParameter(parts[0])).thenReturn(parts[1]);
    when(inner_request.getParameter(parts[2])).thenReturn(parts[3]);
    RequestImpl request = new RequestImpl(replacer.stapler, inner_request, Collections.emptyList(), null);

    HttpServletResponse inner_response = Mockito.mock(HttpServletResponse.class);
    StringWriter stringWriter = new StringWriter();
    PrintWriter printWriter = new PrintWriter(stringWriter);
    when(inner_response.getWriter()).thenReturn(printWriter);
    ResponseImpl response = new ResponseImpl(replacer.stapler, inner_response);

    replacer.setCurrentRequest(request);
    replacer.setCurrentResponse(response);
    action.authenticateAsAdmin(request, response);
  }
}