{
  description = "challenge-project";

  inputs =
    {
      nixpkgs.url = "github:nixos/nixpkgs/nixos-24.05";
      rust-overlay.url = "github:oxalica/rust-overlay";
      # old-python-nixpkgs.url = "github:nixos/nixpkgs/2030abed5863fc11eccac0735f27a0828376c84e";
    };

  outputs = { self, nixpkgs, rust-overlay, ... }@inputs:
    let
      system = "x86_64-linux";
      overlays = [ (import rust-overlay) ];
      # pkgs = nixpkgs.legacyPackages.${system};
      pkgs = import nixpkgs { inherit system overlays; };
    in
    {
      devShells.x86_64-linux.default =
        # pkgs.mkShell.override { stdenv = pkgs.clangStdenv; }
        pkgs.mkShell
          {
            nativeBuildInputs = with pkgs; [
              # inputs.old-python-nixpkgs.legacyPackages.${system}.python36
              # python311
              # python311Full
              # python311Packages.pip
              # python311Packages.virtualenv
              z3
              zlib
              libxml2
              libffi
              fd
              # ripgrep
              # git
              # pkg-config
              # rustup
              rust-bin.nightly."2024-06-18".default
              ninja
              cmake
              bashInteractive
              # clang
              # libclang
              # libcxx
              # llvm
              lit
              aflplusplus
              # patchelf
              # nix-ld
              # { programs.nix-ld.dev.enable = true; }
              # llvmPackages_18.stdenv
              llvmPackages_18.libcxxClang
              llvmPackages_18.clangUseLLVM
              llvmPackages_18.clang
              llvmPackages_18.llvm
              llvmPackages_18.libcxx
              llvmPackages_18.bintools
            ];
            LIBCLANG_PATH = pkgs.lib.makeLibraryPath [ pkgs.libclang.lib ];
            hardeningDisable = [ "all" ];  
            shellHook = ''
                export CLANG_DIR="${pkgs.clang}/bin";
            '';
                # export PYTHON_LIB="${pkgs.python311}/lib";
                # export PKG_CONFIG_PATH="/usr/lib/x86_64-linux-gnu/pkgconfig";
          };
    };
}
