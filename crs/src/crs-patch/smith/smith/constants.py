from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
DATA_DIR = ROOT / 'data'

MAX_SAMPLES = 10
TEST_TIMEOUT = 60 * 30

# OPENAI specific
MAX_RETRY_COUNT_FOR_RATE_LIMIT_ERROR = 3

# Language servers
LSP_TIMEOUT = 10
CLANGD_PATH = Path('/usr/bin/clangd-17')
JDTLS_PATH = ROOT / 'opt/eclipse.jdt.ls/bin/jdtls'
