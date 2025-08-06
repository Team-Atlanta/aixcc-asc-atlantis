import static org.mockito.Mockito.*;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Collections;

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.team_atlanta.*;
import io.jenkins.plugins.toyplugin.AuthAction;

import org.kohsuke.stapler.RequestImpl;
import org.kohsuke.stapler.ResponseImpl;
import org.kohsuke.stapler.WebApp;
import org.mockito.Mockito;

import aixcc.util.StaplerReplacer;

public class JenkinsEight_Concolic {

  public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception {
    String part1 = provider.consumeString(10);
    String part2 = provider.consumeString(20);
    String part3 = provider.consumeString(10);
    String part4 = provider.consumeString(20);

    AuthAction action = new AuthAction();

    StaplerReplacer replacer = new StaplerReplacer();
    replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));

    HttpServletRequest inner_request = Mockito.mock(HttpServletRequest.class);
    when(inner_request.getParameter(part1)).thenReturn(part2);
    when(inner_request.getParameter(part3)).thenReturn(part4);
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

  public static void main(String[] args) throws Throwable, Exception {
    BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
    FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
    fuzzerTestOneInput(provider);
  }
}
