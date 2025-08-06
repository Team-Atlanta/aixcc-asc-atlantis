//! A libfuzzer-like fuzzer with llmp-multithreading support and restarts
//! The example harness is built for libpng.
use core::time::Duration;
use std::{env, net::SocketAddr, path::PathBuf};

use clap::{self, Parser};
use libafl::observers::cmp::CmpObserver;
use libafl::{
    corpus::{Corpus, InMemoryCorpus, InMemoryOnDiskCorpus, OnDiskCorpus},
    events::{launcher::Launcher, setup_restarting_mgr_std, EventConfig, EventRestarter},
    executors::{inprocess::InProcessExecutor, ExitKind, ShadowExecutor},
    feedback_and, feedback_and_fast, feedback_or, feedback_or_fast,
    feedbacks::{CrashFeedback, MaxMapFeedback, NewHashFeedback, TimeFeedback, TimeoutFeedback},
    fuzzer::{Fuzzer, StdFuzzer},
    generators::RandBytesGenerator,
    inputs::{BytesInput, HasTargetBytes},
    monitors::{MultiMonitor, OnDiskTOMLMonitor},
    mutators::{
        scheduled::{havoc_mutations, tokens_mutations, StdScheduledMutator},
        token_mutations::I2SRandReplace,
        token_mutations::Tokens,
        StdMOptMutator,
    },
    observers::{BacktraceObserver, CanTrack, HitcountsMapObserver, StdMapObserver, TimeObserver},
    schedulers::{
        powersched::PowerSchedule, IndexesLenTimeMinimizerScheduler, QueueScheduler,
        StdWeightedScheduler,
    },
    stages::{
        calibrate::CalibrationStage, power::StdPowerMutationalStage, ShadowTracingStage,
        StdMutationalStage,
    },
    state::{HasCorpus, StdState},
    Error, HasMetadata,
};
use libafl_bolts::{
    core_affinity::{CoreId, Cores},
    rands::StdRand,
    shmem::{ShMemProvider, StdShMemProvider},
    tuples::{tuple_list, Merge},
    AsSlice,
};
use libafl_targets::{
    libfuzzer_initialize, libfuzzer_test_one_input, std_edges_map_observer, CmpLogObserver,
};
use mimalloc::MiMalloc;

#[global_allocator]
static GLOBAL: MiMalloc = MiMalloc;

/// Parse a millis string to a [`Duration`]. Used for arg parsing.
fn timeout_from_millis_str(time: &str) -> Result<Duration, Error> {
    Ok(Duration::from_millis(time.parse()?))
}

/// The commandline args this fuzzer accepts
#[derive(Debug, Parser)]
#[command(
    name = "LibAFL for libfuzzer harness",
    about = "A libfuzzer-like fuzzer with llmp-multithreading support and a launcher",
    author = "CRS-User"
)]
struct Opt {
    #[arg(
        short,
        long,
        value_parser = Cores::from_cmdline,
        help = "Spawn a client in each of the provided cores. Broker runs in the 0th core. 'all' to select all available cores. 'none' to run a client without binding to any core. eg: '1,2-4,6' selects the cores 1,2,3,4,6.",
        name = "CORES",
        default_value = "all"
    )]
    cores: Cores,

    #[arg(
        short = 'p',
        long,
        help = "Choose the broker TCP port, default is 1337",
        name = "PORT",
        default_value = "1337"
    )]
    broker_port: u16,

    #[arg(short = 'a', long, help = "Specify a remote broker", name = "REMOTE")]
    remote_broker_addr: Option<SocketAddr>,

    #[arg(
        short,
        long,
        help = "Set an initial corpus directory",
        name = "INPUT",
        default_value = "./corpus"
    )]
    input: Vec<PathBuf>,

    #[arg(
        short,
        long,
        help = "Set the output directory, default is ./out",
        name = "OUTPUT",
        default_value = "./crashes"
    )]
    output: PathBuf,

    #[arg(
        value_parser = timeout_from_millis_str,
        short,
        long,
        help = "Set the exeucution timeout in milliseconds, default is 10000",
        name = "TIMEOUT",
        default_value = "30000"
    )]
    timeout: Duration,

    #[arg(
        short = 'x',
        long,
        help = "Feed the fuzzer with an user-specified list of tokens (often called \"dictionary\"",
        name = "TOKENS",
        default_value = "./libafl_fuzzing.dict"
    )]
    tokens: PathBuf,
}

#[no_mangle]
pub extern "C" fn cleanup() {
    // println!("[-] exit: Rust cleanup code running...");
    // Trigger an abort or any other logic you need
    std::process::abort();
}

#[no_mangle]
pub extern "C" fn register_cleanup() {
    extern "C" {
        fn atexit(func: extern "C" fn()) -> i32;
    }

    unsafe {
        atexit(cleanup);
    }
}

/// The main fn, `no_mangle` as it is a C main
#[cfg(not(test))]
#[no_mangle]
pub extern "C" fn libafl_main() {
    let opt = Opt::parse();

    let broker_port = opt.broker_port;
    let cores = opt.cores;

    register_cleanup();

    println!(
        "Workdir: {:?}",
        env::current_dir().unwrap().to_string_lossy().to_string()
    );
    fuzz(
        &opt.input,
        opt.output,
        &opt.tokens,
        broker_port,
        cores,
        opt.timeout,
    )
    .expect("An error occurred while fuzzing");
}

/// The actual fuzzer
#[cfg(not(test))]
fn fuzz(
    corpus_dirs: &[PathBuf],
    objective_dir: PathBuf,
    token_dict: &PathBuf,
    broker_port: u16,
    cores: Cores,
    timeout: Duration,
) -> Result<(), Error> {
    use std::backtrace;

    use libafl::events::restarting;

    let monitor = OnDiskTOMLMonitor::new(
        "./fuzzer_stats.toml",
        MultiMonitor::new(|s| println!("{s}")),
    );

    let shmem_provider = StdShMemProvider::new().expect("Failed to init shared memory");

    println!("Broker port: {}", broker_port);

    let mut run_client = |state: Option<_>, mut restarting_mgr, _core_id| {
        // Create an observation channel using the coverage map
        let edges_observer = unsafe { std_edges_map_observer("edges").track_indices() };

        // Create an observation channel to keep track of the execution time
        let time_observer = TimeObserver::new("time");
        let map_feedback = MaxMapFeedback::new(&edges_observer);
        let cmplog_observer = CmpLogObserver::new("cmplog", true);
        let calibration = CalibrationStage::new(&map_feedback);
        let backtrace_observer = BacktraceObserver::owned(
            "BacktraceObserver",
            libafl::observers::HarnessType::InProcess,
        );

        // Feedback to rate the interestingness of an input
        // This one is composed by two Feedbacks in OR
        let mut feedback = feedback_or!(
            // New maximization map feedback linked to the edges observer and the feedback state
            map_feedback,
            // Time feedback, this one does not need a feedback state
            TimeFeedback::new(&time_observer)
        );

        // A feedback to choose if an input is a solution or not
        let mut objective = feedback_or_fast!(
            feedback_and_fast!(
                CrashFeedback::new(),
                NewHashFeedback::new(&backtrace_observer)
            ),
            TimeoutFeedback::new()
        );

        // If not restarting, create a State from scratch
        let mut state = state.unwrap_or_else(|| {
            StdState::new(
                // RNG
                StdRand::new(),
                // Corpus that will be evolved, we keep it in memory for performance
                // we store the corpus in the `queue` directory for patching team as well
                // InMemoryCorpus::new(),
                InMemoryOnDiskCorpus::new("queue")
                    .expect("failed to create in-memory corpus queue"),
                // Corpus in which we store solutions (crashes in this example),
                // on disk so the user can get them after stopping the fuzzer
                OnDiskCorpus::new(&objective_dir).unwrap(),
                // States of the feedbacks.
                // The feedbacks can report the data that should persist in the State.
                &mut feedback,
                // Same for objective feedbacks
                &mut objective,
            )
            .unwrap()
        });

        println!("We're a client, let's fuzz :)");

        if state.metadata_map().get::<Tokens>().is_none() {
            if let Ok(tokens) = Tokens::from_file(&token_dict) {
                state.add_metadata(tokens);
            }
        }

        // A minimization+queue policy to get testcasess from the corpus
        let scheduler = IndexesLenTimeMinimizerScheduler::new(
            &edges_observer,
            StdWeightedScheduler::with_schedule(
                &mut state,
                &edges_observer,
                Some(PowerSchedule::EXPLORE),
            ),
        );

        // A fuzzer with feedbacks and a corpus scheduler
        let mut fuzzer = StdFuzzer::new(scheduler, feedback, objective);

        // The wrapped harness function, calling out to the LLVM-style harness
        let mut harness = |input: &BytesInput| {
            let target = input.target_bytes();
            let buf = target.as_slice();
            libfuzzer_test_one_input(buf);
            ExitKind::Ok
        };

        // Create the executor for an in-process function with one observer for edge coverage and one for the execution time
        let mut executor = ShadowExecutor::new(
            InProcessExecutor::batched_timeout(
                &mut harness,
                tuple_list!(edges_observer, time_observer, backtrace_observer),
                &mut fuzzer,
                &mut state,
                &mut restarting_mgr,
                timeout,
            )?,
            tuple_list!(cmplog_observer),
        );

        // The actual target run starts here.
        // Call LLVMFUzzerInitialize() if present.
        let args: Vec<String> = env::args().collect();
        if libfuzzer_initialize(&args) == -1 {
            println!("Warning: LLVMFuzzerInitialize failed with -1");
        }

        // In case the corpus is empty (on first run), reset
        if state.must_load_initial_inputs() {
            if corpus_dirs.is_empty() || corpus_dirs[0].read_dir()?.next().is_none() {
                let mut generator = RandBytesGenerator::new(32);
                // Generate 8 initial inputs
                state
                    .generate_initial_inputs(
                        &mut fuzzer,
                        &mut executor,
                        &mut generator,
                        &mut restarting_mgr,
                        8,
                    )
                    .expect("Failed to generate the initial corpus");
                println!(
                    "We imported {} inputs from the generator.",
                    state.corpus().count()
                );
            } else {
                println!("Loading from {:?}", &corpus_dirs);
                state
                    .load_initial_inputs(
                        &mut fuzzer,
                        &mut executor,
                        &mut restarting_mgr,
                        corpus_dirs,
                    )
                    .unwrap_or_else(|_| {
                        panic!("Failed to load initial corpus at {:?}", &corpus_dirs)
                    });
                println!("We imported {} inputs from disk.", state.corpus().count());
            }
        }

        // Setup a tracing stage in which we log comparisons
        let tracing = ShadowTracingStage::new(&mut executor);

        // Setup a randomic Input2State stage
        let i2s =
            StdMutationalStage::new(StdScheduledMutator::new(tuple_list!(I2SRandReplace::new())));

        // Setup a basic mutator with a mutational stage
        let mutator = StdMOptMutator::new(
            &mut state,
            havoc_mutations().merge(tokens_mutations()),
            7,
            5,
        )?;
        let power = StdPowerMutationalStage::new(mutator);

        // The order of the stages matter!
        let mut stages = tuple_list!(calibration, tracing, i2s, power);
        // let mut stages = tuple_list!(calibration, power);

        fuzzer.fuzz_loop(&mut stages, &mut executor, &mut state, &mut restarting_mgr)?;

        Ok(())
    };

    print!("Starting launcher.. \n");

    match Launcher::builder()
        .shmem_provider(shmem_provider)
        .configuration(EventConfig::from_name("default"))
        .monitor(monitor)
        .run_client(&mut run_client)
        .cores(&cores)
        .broker_port(broker_port)
        .remote_broker_addr(None)
        .stdout_file(Some("/dev/null"))
        .build()
        .launch()
    {
        Ok(()) => Ok(()),
        Err(Error::ShuttingDown) => Err(Error::ShuttingDown),
        Err(err) => panic!("Failed to run launcher: {err:?}"),
    }
}
