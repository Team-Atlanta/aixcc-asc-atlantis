package branchana;

import java.util.Map;
import java.util.Set;
import java.util.List;

public class IntrospectionData {

	public static class SanitizerInfo {
		public String sanitizerName;
		public String fullClassname;
		public String methodName;
		public String[] args;

		public SanitizerInfo(String sanitizerName, String fullClassname, String methodName,
				String[] args) {
			this.sanitizerName = sanitizerName;
			this.fullClassname = fullClassname;
			this.methodName = methodName;
			this.args = args;
		}
	}

	public static class JsonData {
		public Set<Integer> allEdgeIds;
		public Map<String, List<SanitizerInfo>> seed2SanitizerInfos;
		public Map<String, List<Integer>> seed2EdgeIds;
	}

}
