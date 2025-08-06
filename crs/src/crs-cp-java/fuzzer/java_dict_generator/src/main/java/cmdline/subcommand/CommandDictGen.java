package cmdline.subcommand;

import com.beust.jcommander.Parameter;
import dictgen.DictGen;
import setup.SootSetup;
import java.util.List;

public class CommandDictGen {

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

	@Parameter(names = {"-c", "--target-classes"},
			description = "class that entry function belongs to", required = false)
	private List<String> targetClasses;

	@Parameter(names = {"-m", "--target-methods"},
			description = "entry function that the dict extracts from",
			required = false)
	private List<String> targetMethods;

	@Parameter(names = {"-o", "--output-dicts"}, description = "filenames of the output dicts",
			required = false)
	private List<String> outputDicts;

	public boolean isHelp() {
		return help;
	}

	public void runCmdMode() {
		System.out.println("Setup soot...");
		SootSetup.setup(classPath, processDirs, true);

		for (int i = 0; i < targetClasses.size(); i++) {
			String targetClass = targetClasses.get(i);
			String targetMethod = targetMethods.get(i);
			String outputDict = outputDicts.get(i);

			System.out.println("[" + i + "] Generating dict for " + targetClass + "."
					+ targetMethod + " to " + outputDict + " ...");

			DictGen.generate(targetClass, targetMethod, outputDict);
		}
	}

	public void process() {
		System.out.println("classPath: " + classPath);
		System.out.println("processDirs: " + processDirs);
		System.out.println("targetClasses: " + targetClasses);
		System.out.println("targetMethods: " + targetMethods);
		System.out.println("outputDicts: " + outputDicts);

		// check the length of the lists
		if (targetClasses.size() != targetMethods.size()
				|| targetClasses.size() != outputDicts.size()) {
			System.err.println(
					"ERROR: the length of target_classes, target_methods, and output_dict should be the same");
			System.exit(1);
		}

		System.out.println("Running in command line mode");
		runCmdMode();

	}

}
