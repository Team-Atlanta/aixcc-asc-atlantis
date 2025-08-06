package com.code_intelligence.jazzer.mutation.fieldsemantic;

import com.google.protobuf.Message.Builder;

/*
 * Common interface for field semantics.
 */
public interface FieldSemantic {

	public <T extends Builder> void fillPreMutationValueInPlace(T reference);

	public <T extends Builder> void fillPostMutationValueInPlace(T reference);

	public boolean shouldMask();

}
