import org.team_atlanta.*;
import io.jenkins.plugins.toyplugin.Script;
import jenkins.model.Jenkins;
import hudson.model.Job;
import org.mockito.Mockito;
import static org.mockito.Mockito.*;

import javax.script.ScriptException;

public class JenkinsTwelve_Concolic {
    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Exception {
        String value = provider.consumeString(100); // Consume a string of up to 100 characters

        Jenkins mockJ = Mockito.mock(Jenkins.class);
        when(mockJ.hasPermission(Job.CONFIGURE)).thenReturn(true);
        try {
            new Script(mockJ).doCheckScriptCompile(value);
        } catch (ScriptException e) {}
    }

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        fuzzerTestOneInput(provider);
    }
}
