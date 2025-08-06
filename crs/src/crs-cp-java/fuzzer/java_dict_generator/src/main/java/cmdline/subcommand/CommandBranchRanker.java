package cmdline.subcommand;

import java.util.List;

import com.beust.jcommander.Parameter;
import branchana.BranchRanker;
import setup.SootSetup;

public class CommandBranchRanker {

	@Parameter(names = {"-h", "--help"}, description = "Help/Usage", help = true)
	private boolean help;

	@Parameter(names = {"-C", "--classpath"},
			description = "classpath arguments of soot, the jar dependencies for analyzing the target harness",
			required = true)
	private String classPath;

	@Parameter(names = {"-D", "--processdirs"},
			description = "processdir argument of soot, directories of the target harnesses",
			required = true)
	private List<String> processDirs;

	@Parameter(names = {"-i", "--stuck-branch-file"},
			description = "input file of the stuck branches", required = true)
	private String stuckBranchFile;

	@Parameter(names = {"-o", "--ranked-branch-file"},
			description = "output file of the ranked branches", required = true)
	private String rankedBranchFile;

	public boolean isHelp() {
		return help;
	}

	public void runCmdMode() {
		System.out.println("Setup soot...");
		SootSetup.setup(classPath, processDirs, true);

		System.out.println("Ranking the branches from " + stuckBranchFile + " to "
				+ rankedBranchFile);

		BranchRanker.analyze(stuckBranchFile, rankedBranchFile);
	}

	public void process() {
		System.out.println("classPath: " + classPath);
		System.out.println("processDirs: " + processDirs);
		System.out.println("stuckBranchFile: " + stuckBranchFile);

		System.out.println("Running in command line mode");
		runCmdMode();

	}

}
