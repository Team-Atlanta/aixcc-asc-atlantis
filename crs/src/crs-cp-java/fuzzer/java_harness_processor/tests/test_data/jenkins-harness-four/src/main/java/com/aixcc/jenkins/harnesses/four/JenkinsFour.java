package com.aixcc.jenkins.harnesses.four;

import hudson.model.FreeStyleBuild;

import io.jenkins.plugins.coverage.CoverageProcessor;

import org.mockito.Mockito;
import static org.mockito.Mockito.*;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;

public class JenkinsFour {

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
