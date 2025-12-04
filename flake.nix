{
  description = "Kontrol";

  inputs = {
    rv-nix-tools.url = "github:runtimeverification/rv-nix-tools/854d4f05ea78547d46e807b414faad64cea10ae4";
    nixpkgs.follows = "rv-nix-tools/nixpkgs";

    kevm.url = "github:runtimeverification/evm-semantics/v1.0.881";
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
    uv2nix.url = "github:pyproject-nix/uv2nix/c8cf711802cb00b2e05d5c54d3486fce7bfc8f7c";
    # uv2nix requires a newer version of nixpkgs
    # therefore, we pin uv2nix specifically to a newer version of nixpkgs
    # until we replaced our stale version of nixpkgs with an upstream one as well
    # but also uv2nix requires us to call it with `callPackage`, so we add stuff
    # from the newer nixpkgs to our stale nixpkgs via an overlay
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
    uv2nix.inputs.nixpkgs.follows = "nixpkgs-unstable";
    # uv2nix.inputs.nixpkgs.follows = "nixpkgs";
    pyproject-build-systems.url = "github:pyproject-nix/build-system-pkgs/795a980d25301e5133eca37adae37283ec3c8e66";
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
      nixpkgs-unstable,
      ... }:
  let
    pythonVer = "310";
  in flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs-unstable = import nixpkgs-unstable {
        inherit system;
      };
      # for uv2nix, remove this once we updated to a newer version of nixpkgs
      staleNixpkgsOverlay = final: prev: {
        inherit (pkgs-unstable) replaceVars;
      };
      # due to the nixpkgs that we use in this flake being outdated, uv is also heavily outdated
      # we can just use the binary release of uv provided by uv2nix
      uvOverlay = final: prev: {
        uv = uv2nix.packages.${final.system}.uv-bin;
      };
      kontrolOverlay = final: prev:
      let
        kontrol-pyk-pyproject = final.callPackage ./nix/kontrol-pyk-pyproject {
          inherit uv2nix;
        };
        kontrol-pyk = final.callPackage ./nix/kontrol-pyk {
          inherit pyproject-nix pyproject-build-systems kontrol-pyk-pyproject;
          pyproject-overlays = [
            (k-framework.overlays.pyk-pyproject system)
            (kevm.overlays.pyk-pyproject system)
          ];
          python = final."python${pythonVer}";
        };
        kontrol = final.callPackage ./nix/kontrol {
          inherit kontrol-pyk;
          rev = self.rev or null;
        };
      in {
        inherit kontrol kontrol-pyk-pyproject;
      };
      solcMkDefaultOverlay = final: prev: {
        solcMkDefault = solc.mkDefault;
      };
      pkgs = import nixpkgs {
        inherit system;
        overlays = [
          staleNixpkgsOverlay
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
        kevmShell = kevm.devShells.${system}.default;
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
        inherit (pkgs) kontrol uv kontrol-pyk kontrol-pyk-pyproject;
        default = kontrol;
      };
    }) // {
      overlays = {
        default = final: prev: {
          inherit (self.packages.${final.system}) kontrol;
        };
        # this pyproject-nix overlay allows for overriding the python packages that are otherwise locked in `uv.lock`
        # by using this overlay in dependant nix flakes, you ensure that nix overrides also override the python package     
        pyk-pyproject = system: final: prev: {
          inherit (self.packages.${system}.kontrol-pyk-pyproject.lockFileOverlay final prev) kontrol-pyk;
        };
      };
    };
}
