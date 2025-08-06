
import org.team_atlanta.*;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Enumeration;
import java.util.List;

import jenkins.model.Jenkins;
import aixcc.util.StaplerReplacer;
import java.nio.ByteBuffer;
import java.util.*;

import io.jenkins.plugins.UtilPlug.UtilMain;
import org.kohsuke.stapler.WebApp;
import org.kohsuke.stapler.RequestImpl;
import org.kohsuke.stapler.ResponseImpl;
import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.mockito.Mockito;
import static org.mockito.Mockito.*;

public class JenkinsTwo_Concolic {

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        fuzzerTestOneInput(provider);
    }

    final int expected_data_length = Integer.BYTES + // picker
            Integer.BYTES + // count
            1 + // request header name minimum
            1 + // separator
            1 + // request header value minimum
            1 + // separator
            1; // command minimum

    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception {
        new JenkinsTwo_Concolic().fuzz(provider);
    }

    UtilMain nw;
    Jenkins mockJ;
    StaplerReplacer replacer;
    RequestImpl req;
    ResponseImpl resp;

    private void fuzz(FuzzedDataProvider provider) {
        int picker = provider.consumeInt(0, Integer.MAX_VALUE);
        int count = provider.consumeInt(0, 255);

        String headerName = provider.consumeString(10);
        String headerValue = provider.consumeString(10);
        String command = provider.consumeString(20);

        setup_utilmain();
        try {
            setup_replacer();
        } catch (Exception e) {
            return; // eat it
        }

        set_header(headerName, headerValue);

        for (int i = 0; i < count; i++) {
            try {
                switch (picker) {
                    case 13:
                        nw.doexecCommandUtils(command, req, resp);
                        break;
                    default:
                        throw new Exception("unsupported method picker");
                }
            } catch (Exception e) {
                continue; // eat it
            }
        }
    }

    private void setup_utilmain() {
        nw = new UtilMain();
        mockJ = Mockito.mock(Jenkins.class);
        when(mockJ.hasPermission(Jenkins.ADMINISTER)).thenReturn(false);

        nw.jenkin = mockJ;
    }

    private void setup_replacer() throws Exception {
        replacer = new StaplerReplacer();
        replacer.setWebApp(new WebApp(Mockito.mock(ServletContext.class)));
    }

    private void set_header(String name, String value) {
        List<String> header_names = new ArrayList<>();
        header_names.add(name);
        Enumeration<String> headerNamesEnumeration = Collections.enumeration(header_names);

        HttpServletRequest mockRequest = Mockito.mock(HttpServletRequest.class);
        when(mockRequest.getHeaderNames()).thenReturn(headerNamesEnumeration);
        when(mockRequest.getHeader(name)).thenReturn(value);
        when(mockRequest.getHeader("Referer")).thenReturn("http://localhost:8080/UtilPlug/execCommandUtils");

        req = new RequestImpl(replacer.stapler, mockRequest, Collections.emptyList(), null);

        HttpServletResponse mockResp = Mockito.mock(HttpServletResponse.class);
        resp = new ResponseImpl(replacer.stapler, mockResp);

        replacer.setCurrentRequest(req);
        replacer.setCurrentResponse(resp);
    }
}
