use std::env;
use std::path::{Path, PathBuf};
use std::fs;
use std::process::Command;

use libafl_cc::{ClangWrapper, CompilerWrapper, ToolWrapper};
use pathsearch::find_executable_in_path;
use which::which;

/// The max version of `LLVM` we're looking for
#[cfg(not(target_vendor = "apple"))]
const LLVM_VERSION_MAX: u32 = 33;

/// The min version of `LLVM` we're looking for
#[cfg(not(target_vendor = "apple"))]
const LLVM_VERSION_MIN: u32 = 6;

/// Get the extension for a shared object
fn dll_extension<'a>() -> &'a str {
    "so"
}

fn find_llvm_version() -> Option<i32> {
    let llvm_env_version = env::var("LLVM_VERSION");
    let output = if let Ok(version) = llvm_env_version {
        version
    } else {
        exec_llvm_config(&["--version"])
    };
    if let Some(major) = output.split('.').collect::<Vec<&str>>().first() {
        if let Ok(res) = major.parse::<i32>() {
            return Some(res);
        }
    }
    None
}

fn find_llvm_config() -> Result<String, String> {
    if let Ok(var) = env::var("LLVM_CONFIG") {
        return Ok(var);
    }

    for version in (LLVM_VERSION_MIN..=LLVM_VERSION_MAX).rev() {
        let llvm_config_name: String = format!("llvm-config-{version}");
        if which(&llvm_config_name).is_ok() {
            return Ok(llvm_config_name);
        }
    }

    if which("llvm-config").is_ok() {
        return Ok("llvm-config".to_owned());
    }

    Err("could not find llvm-config".to_owned())
}

fn exec_llvm_config(args: &[&str]) -> String {
    let llvm_config = find_llvm_config().expect("Unexpected error");
    match Command::new(llvm_config).args(args).output() {
        Ok(output) => String::from_utf8(output.stdout)
            .expect("Unexpected llvm-config output")
            .trim()
            .to_string(),
        Err(e) => panic!("Could not execute llvm-config: {e}"),
    }
}

pub fn main() {
    let mut args: Vec<String> = env::args().collect();
    let original_args = args.clone();

    let mut i = 0;
    while i < args.len() {
        if args[i] == "-I" && i + 1 < args.len() && (args[i + 1] == "/usr/lib/LibFuzzingEngine.a" || args[i + 1] == "/usr/lib/libFuzzingEngine.a") {
            args.remove(i); // Remove "-I"
            args.remove(i); // Remove the next element (LibFuzzingEngine.a or libFuzzingEngine.a)
        } else {
            i += 1;
        }
    }

    // remove libfuzzingengine from the blocklist
    let blocklist = ["/usr/lib/LibFuzzingEngine.a", "/usr/lib/libFuzzingEngine.a"];
    for item in &blocklist {
        args.retain(|x| x != item);
    } 

    let mut is_harness = false;
    let keywords = env::var("CP_HARNESS").unwrap_or("pov_harness".to_string());

    for word in keywords.split(":") {
        for arg in args.iter() {
            if arg.contains(&word) {
                is_harness = true;
                break;
            }
        }
    }

    // Check if any of the symbols are in args
    let has_wrap_symbol = args.iter().any(|arg| arg.contains("-Wl,--wrap="));
    let has_c = args.iter().any(|arg| arg.ends_with("-c"));
    let has_o = args.iter().any(|arg| arg.ends_with("-o"));
    let original_linked_libfuzzer = original_args
        .iter()
        .any(|arg| arg.contains("/usr/lib/libFuzzingEngine.a"));

    if args.len() > 1 {
        let mut dir = env::current_exe().unwrap();
        let wrapper_name = dir.file_name().unwrap().to_str().unwrap();

        let is_cpp = match wrapper_name[wrapper_name.len()-2..].to_lowercase().as_str() {
            "cc" => false,
            "++" | "pp" | "xx" => true,
            _ => panic!("Could not figure out if c or c++ wrapper was called. Expected {dir:?} to end with c or cxx"),
        };

        dir.pop();

        // just assume this is already in skytool, and we already renamed the 32-bit lib
        let skynet_lib = if args.iter().any(|arg| arg == "-m32") {
            "skynet_libfuzzer_32"
        }
        else {
            "skynet_libfuzzer"
        };
        
        let extract_wrap_symbol = |a: &String| {
            let idx = a.find("--wrap=").unwrap();
            let wrapstrlen = "--wrap=".len();
            a[idx + wrapstrlen..].to_string()
        };

        let wrap_symbols = args
            .iter()
            .filter(|a| a.contains("--wrap="))
            .map(extract_wrap_symbol)
            .collect::<Vec<_>>();

        if !wrap_symbols.is_empty() {
            let libskynet = dir.join(&format!("lib{}.a", skynet_lib));
            let libskynet_mod = dir.join(&format!("lib{}_modified.a", skynet_lib));
            let mut objcopy_cmd = Command::new("objcopy");
            let _objcopy_cmd = wrap_symbols
                .iter()
                .fold(&mut objcopy_cmd, |acc, sym| {
                    acc.arg("--redefine-sym").arg(format!("{sym}=__real_{sym}"))
                })
                .arg(libskynet.as_os_str())
                .arg(libskynet_mod.as_os_str())
                .output()
                .expect(&format!("Failed to do objcopy"));
        } else {
            fs::copy(
                dir.join(&format!("lib{}.a", skynet_lib)),
                dir.join(&format!("lib{}_modified.a", skynet_lib)),
            )
            .expect("Failed to copy lib.a");
        }

        let llvm_bindir = exec_llvm_config(&["--bindir"]);
        let bindir_path = Path::new(&llvm_bindir);

        // NOTE Andrew: commenting alternative impl.
        //      The bindir method works only if we're not in nix env (which is fine with current workflow)

        // Search for clang on path. Couldn't get sh -c 'command -v clang' working, using external crate
        // let cc_path = if let Some(exe) = find_executable_in_path("clang") {
        //     exe.display().to_string()
        // } 
        // else {
        //     "/usr/local/bin/clang".to_string()
        // };
        // let cxx_path = if let Some(exe) = find_executable_in_path("clang++") {
        //     exe.display().to_string()
        // } 
        // else {
        //     "/usr/local/bin/clang++".to_string()
        // };
        // cc.wrapped_cc(cc_path);
        // cc.wrapped_cxx(cxx_path);

        let mut clang = bindir_path.join("clang");
        let mut clangcpp = bindir_path.join("clang++");
        let cxxflags = exec_llvm_config(&["--cxxflags"]);
        let mut cxxflags: Vec<String> = cxxflags.split_whitespace().map(String::from).collect();

        if !clang.exists() {
            clang = PathBuf::from("/usr/local/bin/clang".to_string());
        }

        if !clangcpp.exists() {
            clangcpp = PathBuf::from("/usr/local/bin/clang++".to_string());
        }


        let mut cc = ClangWrapper::new();
        cc.wrapped_cc(clang.clone().to_str().unwrap().to_string());
        cc.wrapped_cxx(clangcpp.clone().to_str().unwrap().to_string());

        cc.cpp(is_cpp)
            // silence the compiler wrapper output, needed for some configure scripts.
            .silence(true)
            .parse_args(&args)
            .expect("Failed to parse the command line")
            .add_arg("-fsanitize-coverage=trace-pc-guard,trace-cmp");

        let should_link = is_harness || original_linked_libfuzzer || (!has_c || has_o);
        // let should_link = is_harness || original_linked_libfuzzer;
        if should_link {
            cc.link_staticlib(&dir, &format!("{}_modified", skynet_lib));
        }

        if let Some(code) = cc.run().expect("Failed to run the wrapped compiler") {
            std::process::exit(code);
        }
    } else {
        panic!("LibAFL CC: No Arguments given");
    }
}
