
package com.aixcc.jenkins.harnesses.four;

import org.team_atlanta.*;
import hudson.model.FreeStyleBuild;
import io.jenkins.plugins.coverage.CoverageProcessor;
import org.mockito.Mockito;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Base64;

import static org.mockito.Mockito.when;

public class JenkinsFour_Concolic {

    public static void fuzzerTestOneInput(FuzzedDataProvider provider) throws Throwable {
        String reportName = provider.consumeString(20);
        String serializedObject = provider.consumeString(100);

        String whole = reportName + "\0" + serializedObject;
        String[] parts = whole.split("\0");
        if (parts.length != 2)
            return;

        byte[] target = Base64.getDecoder().decode(parts[1]);
        try (FileOutputStream fos = new FileOutputStream(reportName)) {
            fos.write(target);
        } catch (IOException e) {
            return;
        }

        FreeStyleBuild build = Mockito.mock(FreeStyleBuild.class);
        when(build.getRootDir()).thenReturn(new File("."));
        CoverageProcessor.recoverCoverageResult(build);
    }

    public static void main(String[] args) throws Throwable, Exception {
        BinaryArgumentLoader bal = new BinaryArgumentLoader(args[0]);
        FuzzedDataProvider provider = new FuzzedDataProvider(bal.readAsBytes());
        fuzzerTestOneInput(provider);
    }
}
