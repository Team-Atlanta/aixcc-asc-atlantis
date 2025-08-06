"""
FUZZING CONSTANTS
"""

JAZZER = "/classpath/jazzer_asc/jazzer"

INSTRUMENTATION_LIST = [
    "jenkins.**",
    "hudson.**",
    "org.jenkinsci.**",
    "com.cloudbees.**",
    "io.jenkins.**",
    "io.jenkins.blueocean.**",
    "io.jenkins.plugins.**",
    "io.jenkins.jenkinsfile",
]

# Execution timeout per fuzzing iteration (seconds)
EXECUTION_TIMEOUT = 5

# Focused fuzzing time (seconds)
FOCUSED_FUZZING_TOTAL_TIME = 300

"""
INTROSPECTOR CONSTANTS
"""

# Use X status lines of libfuzzer log used for check fuzzing is stuck or not
LIBFUZZER_LOG_STATUS_MAX_LINES = 50

# Number of rounds to check if the coverage and ft are not increasing
COV_FT_NOT_INCREASING_ROUNDS = 15

# Introspection timeout (seconds) 
INTROSPECTION_TIMEOUT = 180

"""
STATIC ANALYSIS CONSTANTS
"""
STATIC_ANALYZER_WEB_URL = "0.0.0.0"
STATIC_ANALYZER_WEB_PORT = 9505
