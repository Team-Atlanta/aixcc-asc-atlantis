from apps.infilling.app import app
from loop.framework.benchmark.hooks import use_runner

if __name__ == "__main__":
    (run,) = use_runner(app)
    run()
