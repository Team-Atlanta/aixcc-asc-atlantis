package com.code_intelligence.jazzer.mutation.fieldsemantic;

import com.google.protobuf.Message.Builder;

public class Mask implements FieldSemantic {

	public static final String type = "mask";

	// fieldId -> the fullName of the field in a message proto 
	private String fieldId;

	// construction function
	public Mask(String id) {
		fieldId = id;
	}

	public boolean shouldMask() {
		return true;
	}

	public <T extends Builder> void fillPreMutationValueInPlace(T reference) {
		// mask does not change the field value before mutation
		// so do nothing
	}

	public <T extends Builder> void fillPostMutationValueInPlace(T reference) {
		// mask does not change the field value after mutation
		// so do nothing
	}
}
