package com.code_intelligence.jazzer.mutation.fieldsemantic;

import com.google.protobuf.Message.Builder;

import java.util.Arrays;
import java.util.List;

import com.code_intelligence.jazzer.mutation.fieldsemantic.FieldSemantic;

// CRC, sha1, md5, etc.
public class Checksum implements FieldSemantic {
	
  public static final String type = "checksum";

  private List<String> quantityTypes = Arrays.asList("crc", "sha1", "md5");
  public Checksum() {
  }

  public <T extends Builder> void fillPreMutationValueInPlace(T reference) {
  }

	public <T extends Builder> void fillPostMutationValueInPlace(T reference) {
  }

	public boolean shouldMask() {
    // mutation on checksum field is meaningless
    return true;
  }

}
