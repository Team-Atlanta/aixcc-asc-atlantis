public class BlobGenerator {
    public static void fuzzerTestOneInput(byte[] data) {
        try {
            java.io.FileOutputStream fos = new java.io.FileOutputStream("blob");
            fos.write(data);
            fos.close();
        } catch (java.io.IOException e) {
        }
    }
}
