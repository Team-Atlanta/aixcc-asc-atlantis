package cmdline.subcommand;

import com.beust.jcommander.Parameter;
import branchana.StuckBranchAnalyzer;
import setup.SootSetup;
import java.util.List;

public class CommandStuckBranchAna {

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

	@Parameter(names = {"-i", "--edgeID-file"}, description = "input file of the edge IDs",
			required = true)
	private String edgeIDFile;

	@Parameter(names = {"-o", "--stuck-branches-files"},
			description = "output file of the stuck branches", required = true)
	private String stuckBranchFile;

	public boolean isHelp() {
		return help;
	}

	public void runCmdMode() {
		System.out.println("Setup soot...");
		SootSetup.setup(classPath, processDirs, false);

		System.out.println("Analyzing the stuck branches from " + edgeIDFile + " to "
				+ stuckBranchFile);

		StuckBranchAnalyzer.analyze(edgeIDFile, stuckBranchFile);
	}

	public void process() {
		System.out.println("classPath: " + classPath);
		System.out.println("processDirs: " + processDirs);
		System.out.println("edgeIDFile: " + edgeIDFile);
		System.out.println("stuckBranchFile: " + stuckBranchFile);

		System.out.println("Running in command line mode");
		runCmdMode();

	}

}
