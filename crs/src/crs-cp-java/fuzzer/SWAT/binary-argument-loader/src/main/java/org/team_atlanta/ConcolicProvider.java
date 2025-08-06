package org.team_atlanta;

import java.util.*;
import java.nio.*;

public class ConcolicProvider {
    public byte[] byte_stream;
    public int consume_index;

    // constructor
    public ConcolicProvider(byte[] stream) {
        this.byte_stream = stream;
    }

    // instrumentation purpose
    public void printStack() {
    }

    // get int
    public int getInt(int a) {
        if (consume_index >= byte_stream.length) {
            return -1;
        }
        ByteBuffer buf = ByteBuffer.wrap(Arrays.copyOfRange(byte_stream, consume_index, consume_index + 4));
        consume_index += 4;
        return buf.getInt();
    }

    // get string
    public String getString(int a) {

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
