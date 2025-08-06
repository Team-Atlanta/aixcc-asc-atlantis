package cmdline;

import com.beust.jcommander.JCommander;
import com.beust.jcommander.ParameterException;
import cmdline.subcommand.CommandDictGen;
import cmdline.subcommand.CommandServer;
import cmdline.subcommand.CommandStuckBranchAna;
import cmdline.subcommand.CommandBranchRanker;

public class Main {

    public static void main(String[] args) {
        CommandMain cmdMain = new CommandMain();
        CommandDictGen cmdDictGen = new CommandDictGen();
        CommandBranchRanker cmdBrRank = new CommandBranchRanker();
        CommandStuckBranchAna cmdsStkBrAna = new CommandStuckBranchAna();
        CommandServer cmdServer = new CommandServer();

        JCommander commander = JCommander.newBuilder().programName("java-static-analyzer")
                .addObject(cmdMain).addCommand("dict-gen", cmdDictGen, "dict")
                .addCommand("branch-rank", cmdBrRank, "rank")
                .addCommand("stuck-branch", cmdsStkBrAna, "stuck")
                .addCommand("server", cmdServer, "srv").build();

        try {
            commander.parse(args);

            if ((args.length == 0) || cmdMain.isHelp()) {
                commander.usage();
                System.exit(0);
            }

        } catch (ParameterException ex) {
            System.err.println("ERROR: " + ex.getMessage());
            commander.usage();
            System.exit(1);

        }

        switch (commander.getParsedCommand()) {
            case "dict-gen":
                System.out.println("dict generation");

                cmdDictGen.process();
                break;

            case "branch-rank":
                System.out.println("rank branches");

                cmdBrRank.process();
                break;

            case "stuck-branch":
                System.out.println("stuck branches");

                cmdsStkBrAna.process();
                break;

            case "server":
                System.out.println("server mode");

                cmdServer.process();
                break;

            default:
                break;
        }

    }
}
