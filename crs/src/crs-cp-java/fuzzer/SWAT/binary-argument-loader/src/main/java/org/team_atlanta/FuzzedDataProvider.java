package org.team_atlanta;

import java.util.*;
import java.nio.*;

public class FuzzedDataProvider {
    public byte[] byte_stream;
    public int consume_index;

    // constructor
    public FuzzedDataProvider(byte[] stream) {
        this.byte_stream = stream;
    }

    // instrumentation purpose
    public void printStack() {
    }

    /*
        - consumeBoolean()
        - consumeInt(int min, int max)
        - consumeString(int size)
        - consumeByte()
        - consumeBytes(int size)
        // additional
        - consumeLong(long min, long max)
    */

    public boolean consumeBoolean() {
        if (consume_index >= byte_stream.length) {
            return false;
        }
        return byte_stream[consume_index++] != 0;
    }

    public byte consumeByte() {
        if (consume_index >= byte_stream.length) {
            return (byte)255;
        }
        return byte_stream[consume_index++];
    }

    public byte[] consumeBytes(int size) {
        // return byte[] with size
        byte[] ret = Arrays.copyOfRange(byte_stream, consume_index, consume_index + size);
        consume_index += size;
        return ret;
    }

    // get int
    public int consumeInt(int min, int max) {
        if (consume_index >= byte_stream.length) {
            return -1;
        }
        ByteBuffer buf = ByteBuffer.wrap(Arrays.copyOfRange(byte_stream, consume_index, consume_index + 4));
        consume_index += 4;
        return buf.getInt();
    }

    // get long
    public long consumeLong(long min, long max) {
        if (consume_index >= byte_stream.length) {
            return -1;
        }
        ByteBuffer buf = ByteBuffer.wrap(Arrays.copyOfRange(byte_stream, consume_index, consume_index + 8));
        consume_index += 8;
        return buf.getLong();
    }

    // get string
    public String consumeString(int size) {

        if (consume_index >= byte_stream.length) {
            return new String("");
        }

        int string_end_index = byte_stream.length;
        for (int i=consume_index; i < byte_stream.length; ++i) {
            if (byte_stream[i] == 0) {
                string_end_index = i;
                break;
            }
        }

        String stringToReturn = new String(Arrays.copyOfRange(byte_stream, consume_index, string_end_index));
        consume_index = string_end_index + 1;

        return stringToReturn;

    }

}
