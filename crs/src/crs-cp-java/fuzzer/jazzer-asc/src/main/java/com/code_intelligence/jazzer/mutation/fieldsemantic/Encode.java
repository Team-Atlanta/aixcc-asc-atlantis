package com.code_intelligence.jazzer.mutation.fieldsemantic;

import java.util.List;
import java.util.Arrays;
import java.util.Base64;

import com.google.protobuf.ByteString;
import com.google.protobuf.Message.Builder;
import com.google.protobuf.Descriptors.FieldDescriptor;
import com.google.protobuf.Descriptors.FieldDescriptor.JavaType;

import com.code_intelligence.jazzer.mutation.fieldsemantic.FieldSemantic;

import static com.code_intelligence.jazzer.mutation.fieldsemantic.Utils.getPresentFieldOrNull;
import static com.code_intelligence.jazzer.mutation.fieldsemantic.Utils.findFieldByFullName;

// base 64, etc.
public class Encode implements FieldSemantic {

  public static final String type = "encode";

  private String fieldId;
  private String encodingType;
  private List<String> encodingTypes = Arrays.asList("base64");

  public Encode(String id, String eType) {
    fieldId = id;
    encodingType = eType;

    if (!encodingTypes.contains(encodingType)) {
      // TODO: support more encoding types
      throw new IllegalArgumentException("encoding type " + encodingType + " is not supported");
    }
  }

  public boolean shouldMask() {
    // self encode requires not mask the field
    return false;
  }

  public <T extends Builder> void fillPreMutationValueInPlace(T reference) {
    // decode the field using the given algo before mutation

    FieldDescriptor field = findFieldByFullName(reference, fieldId);
    // System.out.println("id: " + fieldId);
    // System.out.println("field: " + field);
    Object curValue = getPresentFieldOrNull(reference, field);

    if (curValue == null) {
      throw new IllegalArgumentException("field " + fieldId + " is not present in the message");
    }

    if (field.getJavaType() == JavaType.STRING) {
      if (encodingType.equals("base64")) {
        reference.setField(field, new String(Base64.getDecoder().decode(((String) curValue).getBytes())));
      }

    } else if (field.getJavaType() == JavaType.BYTE_STRING) {
      if (encodingType.equals("base64")) {
        reference.setField(field,
            ByteString.copyFrom(Base64.getDecoder().decode(((ByteString) curValue).toByteArray())));
      }

    } else {
      // TODO: support more data types
      throw new IllegalArgumentException("encode semantic does not support field with type " + field.getFullName());

    }
  }

  public <T extends Builder> void fillPostMutationValueInPlace(T reference) {
    // encode the field using the given algo after mutation

    FieldDescriptor field = findFieldByFullName(reference, fieldId);
    // System.out.println("id: " + fieldId);
    // System.out.println("field: " + field);
    Object curValue = getPresentFieldOrNull(reference, field);

    if (curValue == null) {
      throw new IllegalArgumentException("field " + fieldId + " is not present in the message");
    }

    if (field.getJavaType() == JavaType.STRING) {
      if (encodingType.equals("base64")) {
        reference.setField(field, Base64.getEncoder().encodeToString(((String) curValue).getBytes()));
      }

    } else if (field.getJavaType() == JavaType.BYTE_STRING) {
      if (encodingType.equals("base64")) {
        reference.setField(field,
            ByteString.copyFrom(Base64.getEncoder().encodeToString(((ByteString) curValue).toByteArray()).getBytes()));
      }

    } else {
      // TODO: support more data types
      throw new IllegalArgumentException("encode semantic does not support field with type " + field.getFullName());

    }
  }
}