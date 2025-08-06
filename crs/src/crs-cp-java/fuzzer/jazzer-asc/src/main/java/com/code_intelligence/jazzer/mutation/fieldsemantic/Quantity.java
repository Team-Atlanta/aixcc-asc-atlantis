package com.code_intelligence.jazzer.mutation.fieldsemantic;

import com.google.protobuf.Message.Builder;
import com.google.protobuf.Descriptors.FieldDescriptor;
import com.google.protobuf.Descriptors.FieldDescriptor.JavaType;
import com.google.protobuf.ByteString;

import com.code_intelligence.jazzer.mutation.fieldsemantic.FieldSemantic;

import static com.code_intelligence.jazzer.mutation.fieldsemantic.Utils.getPresentFieldOrNull;
import static com.code_intelligence.jazzer.mutation.fieldsemantic.Utils.findFieldByFullName;

import java.util.Arrays;
import java.util.List;
import java.util.Map;


// length of, size of, count of, etc.
public class Quantity implements FieldSemantic {

  public static final String type = "quantity";

  private String quantityFieldId;
  private String quantityType;
  private String sourceFieldId;

  // TODO: support 'sizeof' when we meet that kind of case
  //       this is a bit tricky since we need to know the exact length of its raw bytes in input instead of the type deserialization length
  private List<String> quantityTypes = Arrays.asList("countof");

  // construction function
  public Quantity(String _quantityFieldId, String _quantityType, String _sourceFieldId) {
    quantityFieldId = _quantityFieldId;
    quantityType = _quantityType;
    sourceFieldId = _sourceFieldId;

    if (!quantityTypes.contains(quantityType)) {
      throw new IllegalArgumentException("quantity type " + quantityType + " is not supported");
    }
  }

  public <T extends Builder> void fillPreMutationValueInPlace(T reference) {
    // unlike encode, field with quantity semantics does not need to change the
    // field value before mutation
    // so do nothing
  }

  private int countOf(FieldDescriptor sourceField, Object sourceValue) {
    if (sourceField.isMapField()) {
      return ((Map<?, ?>) sourceValue).size();
    } else if (sourceField.isRepeated()) {
      return ((List<?>) sourceValue).size();
    } else if (sourceField.getJavaType() == JavaType.BYTE_STRING) {
      return ((ByteString) sourceValue).size();
    } else if (sourceField.getJavaType() == JavaType.STRING) {
      return ((String) sourceValue).length();
    } else {
      throw new IllegalArgumentException("field " + sourceField.getFullName() + " is not a repeated field");
    }
  }

  public static final byte[] intToByteArray(int value, boolean bigEndian, int arrayLength) {
    byte[] results = new byte[arrayLength];
    for (int i = 0; i < arrayLength; i++) {
      if (bigEndian) {
        results[i] = (byte)(value >>> (arrayLength - i - 1) * 8);
      } else {
        results[i] = (byte)(value >>> i * 8);
      }
    }
    return results;
  }

  private <T extends Builder> void setQuantityValue(T reference, FieldDescriptor quantityField, int value) {
    if (quantityField.getJavaType() == JavaType.INT) {
      reference.setField(quantityField, (Integer) value);
    } else if (quantityField.getJavaType() == JavaType.LONG) {
      reference.setField(quantityField, (Long) (long) value);
    } else if (quantityField.getJavaType() == JavaType.FLOAT) {
      reference.setField(quantityField, (Float) (float) value);
    } else if (quantityField.getJavaType() == JavaType.DOUBLE) {
      reference.setField(quantityField, (Double) (double) value);
    } else if (quantityField.getJavaType() == JavaType.BYTE_STRING) {
      // set as hex value 
      // TODO: little endian, big endian? length of the byte array?
      //reference.setField(quantityField, ByteString.copyFrom(intToByteArray(value, true, ?)));
      throw new IllegalArgumentException("field " + quantityField.getFullName() + ": ByteString as quantity field is not supported yet");
    } else if (quantityField.getJavaType() == JavaType.STRING) {
      // set as string
      reference.setField(quantityField, String.valueOf(value));
    } else {
      throw new IllegalArgumentException("field " + quantityField.getFullName() + " cannot be quantity field");
    }
  }

  public <T extends Builder> void fillPostMutationValueInPlace(T reference) {
    // get the value of the quantity field
    FieldDescriptor quantityField = findFieldByFullName(reference, quantityFieldId);
    Object qfValue = getPresentFieldOrNull(reference, quantityField);
    if (qfValue == null) {
      throw new IllegalArgumentException("field " + quantityFieldId + " is not present in the message");
    }

    // get the value of the source field
    FieldDescriptor sourceField = findFieldByFullName(reference, sourceFieldId);
    Object sfValue = getPresentFieldOrNull(reference, sourceField);
    if (sfValue == null) {
      // it can be null if the source field is removed by mutation, we set quantity as 0 in this case
      setQuantityValue(reference, quantityField, 0);
    }

    // calculate value from the source field & set to the quantity field
    switch (quantityType) {
      case "countof":
        setQuantityValue(reference, quantityField, countOf(sourceField, sfValue));
        break;
    
      default:
        throw new IllegalArgumentException("quantity type " + quantityType + " is not supported");
    }
  }

  public boolean shouldMask() {
    // mark a field as quantity indicates that you want to keep the semantics
    // instead of testing the quantity relation
    return true;
  }

}
