import hudson.model.FreeStyleBuild;

import io.jenkins.plugins.coverage.CoverageProcessor;

import org.mockito.Mockito;
import static org.mockito.Mockito.*;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;

import org.team_atlanta.*;

public class JenkinsFourConcolic {

    public static void main(String[] args) throws Throwable {
        try {
		BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        byte[] data = bal.readAsBytes();
		String arg = new String(data);
        new JenkinsFourConcolic().fuzz_concolic(arg);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void fuzz_concolic(String whole) throws Throwable {

        String[] parts = whole.split("\0");
        if (parts.length != 2)
            return;

        String reportName = parts[0];
        String serializedObject = parts[1];
        byte[] target = java.util.Base64.getDecoder().decode(serializedObject);
        try (FileOutputStream fos = new FileOutputStream(reportName)) {
            fos.write(target);
        } catch (IOException e) {
            return;
        }

        FreeStyleBuild build = Mockito.mock(FreeStyleBuild.class);
        when(build.getRootDir()).thenReturn(new File("."));
        CoverageProcessor.recoverCoverageResult(build);

    }


    public static void fuzzerTestOneInput(byte[] data) throws Throwable {

        String whole = new String(data);
        String[] parts = whole.split("\0");
        if (parts.length != 2)
            return;

        String reportName = parts[0];
        String serializedObject = parts[1];
        byte[] target = java.util.Base64.getDecoder().decode(serializedObject);
        try (FileOutputStream fos = new FileOutputStream(reportName)) {
            fos.write(target);
        } catch (IOException e) {
            return;
        }

        FreeStyleBuild build = Mockito.mock(FreeStyleBuild.class);
        when(build.getRootDir()).thenReturn(new File("."));
        CoverageProcessor.recoverCoverageResult(build);

    }

}
