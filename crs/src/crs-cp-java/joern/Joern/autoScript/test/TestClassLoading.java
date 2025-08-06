public class TestClassLoading {
    public static void main(String[] args) {
        String classpath = System.getProperty("java.class.path");
        System.out.println("Classpath: " + classpath);
        try {
            Class.forName("io.jenkins.plugins.UtilPlug.UtilMain");
            System.out.println("Class loaded successfully");
        } catch (ClassFormatError e) {
            System.out.println("ClassFormatError: " + e.getMessage());
        } catch (ClassNotFoundException e) {
            System.out.println("ClassNotFoundException: " + e.getMessage());
        }
    }
}
