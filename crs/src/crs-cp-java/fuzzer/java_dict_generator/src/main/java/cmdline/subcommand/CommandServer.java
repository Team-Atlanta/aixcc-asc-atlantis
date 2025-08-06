package cmdline.subcommand;

import java.util.List;

import com.beust.jcommander.Parameter;
import branchana.BranchRanker;
import dictgen.DictGen;
import py4j.GatewayServer;

import setup.SootSetup;

public class CommandServer {

        @Parameter(names = {"-h", "--help"}, description = "Help/Usage", help = true)
        private boolean help;

        public boolean isHelp() {
                return help;
        }

        public static class ServeMenu {
                private static boolean sootInited = false;

                public static boolean isSootInited() {
                        return sootInited;
                }

                public static boolean setupSoot(String classPath, List<String> processDirs) {
                        System.out.println("Setup soot...");
                        if (sootInited) {
                                System.out.println("Soot already initialized");
                                return true;
                        }

                        try {
                                SootSetup.setup(classPath, processDirs, true);
                                sootInited = true;
                                return true;
                        } catch (Exception e) {
                                e.printStackTrace();
                                return false;
                        }
                }

                public static boolean genDictFocused(String targetClass, String targetMethod,
                                String outputDict) {
                        if (!sootInited) {
                                System.out.println("Soot not initialized");
                                return false;
                        }

                        int originalMaxCgDepth = DictGen.MAX_CG_DEPTH;
                        try {
                                DictGen.MAX_CG_DEPTH = 0;

                                System.out.println("Generate focused fuzz dict for " + targetClass + "."
                                                + targetMethod + " to " + outputDict + " ...");
                                DictGen.generate(targetClass, targetMethod, outputDict);

                                DictGen.MAX_CG_DEPTH = originalMaxCgDepth;
                                return true;
                        } catch (Exception e) {
                                DictGen.MAX_CG_DEPTH = originalMaxCgDepth;

                                e.printStackTrace();
                                return false;
                        }
                }

                public static boolean genDict(String targetClass, String targetMethod,
                                String outputDict) {
                        if (!sootInited) {
                                System.out.println("Soot not initialized");
                                return false;
                        }

                        try {
                                System.out.println("Generate fuzz dict for " + targetClass + "."
                                                + targetMethod + " to " + outputDict + " ...");
                                DictGen.generate(targetClass, targetMethod, outputDict);
                                return true;
                        } catch (Exception e) {
                                e.printStackTrace();
                                return false;
                        }
                }

                public static boolean rankBranch(String stuckBranchFile, String rankedBranchFile) {
                        if (!sootInited) {
                                System.out.println("Soot not initialized");
                                return false;
                        }

                        try {
                                System.out.println("Rank branches for " + stuckBranchFile + " ...");
                                BranchRanker.analyze(stuckBranchFile, rankedBranchFile);
                                return true;
                        } catch (Exception e) {
                                e.printStackTrace();
                                return false;
                        }
                }

                // NOTE: stuck branch analysis is not included here, it is supposed to be used in
                // command line mode since it analyzes on instrumented code, which is different from
                // the above analysis
        }

        public static void main(String[] args) {
                // runPy4jServers
                System.out.println("Starting gateway sever...");
                GatewayServer gatewayServer = new GatewayServer(new ServeMenu());
                gatewayServer.start();
        }

        public static void process() {
                main(new String[] {});
        }
}
