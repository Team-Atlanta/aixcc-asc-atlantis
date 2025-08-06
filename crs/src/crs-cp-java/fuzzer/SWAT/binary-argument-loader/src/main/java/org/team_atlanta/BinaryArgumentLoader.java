package org.team_atlanta;

import java.util.*;
import java.io.*;
import java.nio.*;
import java.nio.file.Files;
import java.nio.file.Path;

public class BinaryArgumentLoader {
	public String filename = null;
	public BinaryArgumentLoader(String filename) {
		this.filename = filename;
	}
	public byte[] readAsBytes() {
		try {
			Path path = Path.of(this.filename);
			byte[] bytes = Files.readAllBytes(path);
			System.out.println("=== ARGUMENT INPUT START ===\n");
			for (int i=0; i<bytes.length; ++i) {
				System.out.printf("%02d", bytes[i]);
			      	if (i % 16 == 15) {
					System.out.printf("\n");
				}
				else {
					System.out.printf(" ");
				}
			}
			System.out.println("=== ARGUMENT INPUT  END  ===\n");
			return bytes;

		} catch (Exception e) {
			System.out.println("Exception: " + e.getMessage());
			e.printStackTrace();
			System.exit(-1);
		}
		return null;
	}
}


