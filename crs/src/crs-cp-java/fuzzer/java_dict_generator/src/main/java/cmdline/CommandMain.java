package cmdline;

import com.beust.jcommander.Parameter;

public class CommandMain {

	@Parameter(names = {"-h", "--help"}, description = "Help/Usage", help = true)
	private boolean help;

	public boolean isHelp() {
		return help;
	}

}
