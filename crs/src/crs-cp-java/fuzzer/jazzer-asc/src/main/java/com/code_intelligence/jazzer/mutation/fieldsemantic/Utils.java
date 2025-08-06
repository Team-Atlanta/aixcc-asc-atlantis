package com.code_intelligence.jazzer.mutation.fieldsemantic;

import com.google.protobuf.Message.Builder;
import com.google.protobuf.Descriptors.FieldDescriptor;
import com.google.protobuf.Descriptors.FieldDescriptor.JavaType;

public class Utils {

  static <T extends Builder, U> U getPresentFieldOrNull(T builder, FieldDescriptor field) {
    if (builder.hasField(field)) {
      return (U) builder.getField(field);
    } else {
      return null;
    }
  }

  static <T extends Builder> FieldDescriptor findFieldByFullName(T builder, String fullName) {
    for (FieldDescriptor field : builder.getAllFields().keySet()) {
      if (field.getFullName().equals(fullName)) {
        return field;
      }
    }
    return null;
  }
}
