{
  description = "Kontrol";

  inputs = {
    rv-nix-tools.url = "github:runtimeverification/rv-nix-tools/854d4f05ea78547d46e807b414faad64cea10ae4";
    nixpkgs.follows = "rv-nix-tools/nixpkgs";

    kevm.url = "github:runtimeverification/evm-semantics/v1.0.854";
    kevm.inputs.nixpkgs.follows = "nixpkgs";

    k-framework.follows = "kevm/k-framework";
    flake-utils.follows = "kevm/flake-utils";
    foundry = {
      url =
        "github:shazow/foundry.nix?rev=221d7506a99f285ec6aee26245c55bbef8a407f1"; # Use the same version as CI
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
    solc = {
      url = "github:hellwolf/solc.nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
    uv2nix.url = "github:pyproject-nix/uv2nix/680e2f8e637bc79b84268949d2f2b2f5e5f1d81c";
    # stale nixpkgs is missing the alias `lib.match` -> `builtins.match`
    # therefore point uv2nix to a patched nixpkgs, which introduces this alias
    # this is a temporary solution until nixpkgs us up-to-date again
    uv2nix.inputs.nixpkgs.url = "github:runtimeverification/nixpkgs/libmatch";
    # inputs.nixpkgs.follows = "nixpkgs";
    pyproject-build-systems.url = "github:pyproject-nix/build-system-pkgs/7dba6dbc73120e15b558754c26024f6c93015dd7";
    pyproject-build-systems = {
      inputs.nixpkgs.follows = "uv2nix/nixpkgs";
      inputs.uv2nix.follows = "uv2nix";
      inputs.pyproject-nix.follows = "uv2nix/pyproject-nix";
    };
    pyproject-nix.follows = "uv2nix/pyproject-nix";
  };
  outputs = {
      self,
      k-framework,
      nixpkgs,
      flake-utils,
      kevm,
      rv-nix-tools,
      foundry,
      solc,
      pyproject-nix,
      pyproject-build-systems,
      uv2nix,
      ... }:
  let
    pythonVer = "310";
  in flake-utils.lib.eachDefaultSystem (system:
    let
      # due to the nixpkgs that we use in this flake being outdated, uv is also heavily outdated
      # we can just use the binary release of uv provided by uv2nix
      uvOverlay = final: prev: {
        uv = uv2nix.packages.${final.system}.uv-bin;
      };
      kontrolOverlay = final: prev:
      let
        kontrol-pyk = final.callPackage ./nix/kontrol-pyk {
          inherit pyproject-nix pyproject-build-systems uv2nix;
          python = final."python${pythonVer}";
        };
        kontrol = final.callPackage ./nix/kontrol {
          inherit kontrol-pyk;
          rev = self.rev or null;
        };
      in {
        inherit kontrol;
      };
      solcMkDefaultOverlay = final: prev: {
        solcMkDefault = solc.mkDefault;
      };
      pkgs = import nixpkgs {
        inherit system;
        overlays = [
          (final: prev: { llvm-backend-release = false; })
          k-framework.overlay
          foundry.overlay
          # Matching the version of Foundry with CI
          (final: prev: {
            foundry-bin = prev.foundry-bin.overrideAttrs (_: let
              sources = {
                "x86_64-linux" = {
                  url = "https://github.com/foundry-rs/foundry/releases/download/rc-1/foundry_rc-1_linux_amd64.tar.gz";
                  sha256 = "0kxfi64rl04r18jk60ji72fkvcaps0adrk3cjp9facyr7jcdx8gy";
                };
                "aarch64-linux" = {
                  url = "https://github.com/foundry-rs/foundry/releases/download/rc-1/foundry_rc-1_linux_arm64.tar.gz";
                  sha256 = "0dgbzmfzan8nfb2dfmb8960hdc6wi3x7jx3si5r9h94j6cn9sysk";
                };
                "x86_64-darwin" = {
                  url = "https://github.com/foundry-rs/foundry/releases/download/rc-1/foundry_rc-1_darwin_amd64.tar.gz";
                  sha256 = "0wx8fsghpdap5f16pkn8fsc3dbxfzxi03wjylp9bjw0knjs3f33g";
                };
                "aarch64-darwin" = {
                  url = "https://github.com/foundry-rs/foundry/releases/download/rc-1/foundry_rc-1_darwin_arm64.tar.gz";
                  sha256 = "1zq726d3vqnlp5bn5ijzia8xbw804g6kwxws02ddf390s5mr7946";
                };
              };
            in {
              src = final.fetchzip {
                inherit (sources.${final.stdenv.hostPlatform.system}) url sha256;
                stripRoot = false;
              };
            });
          })
          solc.overlay
          solcMkDefaultOverlay
          kevm.overlays.default
          uvOverlay
          kontrolOverlay
        ];
      };
      python = pkgs."python${pythonVer}";
    in {
      devShells.default =
      let
        kevmShell = kevm.devShell.${system};
      in pkgs.mkShell {
        buildInputs = (kevmShell.buildInputs or [ ]) ++ [
          pkgs.foundry-bin
          (solc.mkDefault pkgs pkgs.solc_0_8_13)
          python
          pkgs.uv
        ];
        env = (kevmShell.env or { }) // {
          # prevent uv from managing Python downloads and force use of specific 
          UV_PYTHON_DOWNLOADS = "never";
          UV_PYTHON = python.interpreter;
        };
        shellHook = (kevmShell.shellHook or "") + ''
          unset PYTHONPATH
        '';
      };
      packages = rec {
        kontrol = pkgs.kontrol;
        uv = pkgs.uv;
        default = kontrol;
      };
    }) // {
      overlays.default = final: prev: {
        inherit (self.packages.${final.system}) kontrol;
      };
    };
}
