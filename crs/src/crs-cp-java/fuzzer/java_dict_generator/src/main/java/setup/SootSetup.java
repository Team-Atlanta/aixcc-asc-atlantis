package setup;

import java.util.List;
import java.util.ArrayList;

import soot.*;
import soot.options.Options;

public class SootSetup {

	/*
	 * NOTE: we should make this configurable for a general dict generator, but it is fine for
	 * semifinal cp
	 */
	final static String fuzzerEntryMethod = "fuzzerTestOneInput";

	public static List<SootMethod> entryPoints = null;

	public static void setup(String classPath, List<String> processDirs, boolean cgPass) {

		// Pattern pkgRegex = Pattern.compile(".*jenkins.*");

		G.reset();
		Options.v().set_prepend_classpath(true);
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_soot_classpath(classPath);
		Options.v().set_process_dir(processDirs);
		Options.v().set_whole_program(true);
		// Options.v().set_app(true);
		Options.v().setPhaseOption("cg.spark", "enabled:true");
		Options.v().setPhaseOption("cg.spark", "verbose:true");
		Options.v().setPhaseOption("cg.spark", "on-fly-cg:true");
		Options.v().set_src_prec(Options.src_prec_class);
		Options.v().set_ignore_resolving_levels(true);

		Scene.v().loadNecessaryClasses();

		// mark entry point
		List<SootMethod> entryPoints = new ArrayList<SootMethod>();
		for (SootClass sc : Scene.v().getClasses()) {
			for (SootMethod sm : sc.getMethods()) {
				if (sm.getName().equals(fuzzerEntryMethod)) {
					entryPoints.add(sm);
				}
			}
		}
		if (entryPoints.size() == 0)
			throw new RuntimeException(
					"No entry point found with method: " + fuzzerEntryMethod);

		// print entry points
		for (SootMethod sm : entryPoints) {
			System.out.println("Entry point: " + sm.getDeclaringClass().getName() + "."
					+ sm.getName());
		}

		Scene.v().setEntryPoints(entryPoints);

		// PackManager.v().runPacks();
		PackManager.v().getPack("wjpp").apply();
		PackManager.v().getPack("wjtp").remove("wjtp.lfp");
		PackManager.v().getPack("wjtp").remove("wjtp.ajc");
		if (cgPass) {
			PackManager.v().getPack("cg").apply();
		}
		PackManager.v().getPack("wjtp").apply();
	}
}
