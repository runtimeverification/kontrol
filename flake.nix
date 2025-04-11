{
  description = "Kontrol";

  inputs = {
    kevm.url = "github:runtimeverification/evm-semantics/v1.0.814";
    nixpkgs.follows = "kevm/nixpkgs";
    k-framework.follows = "kevm/k-framework";
    flake-utils.follows = "kevm/flake-utils";
    rv-utils.follows = "kevm/rv-utils";
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
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "uv2nix/nixpkgs";
      # inputs.uv2nix.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "uv2nix/nixpkgs";
      # inputs.uv2nix.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      # stale nixpkgs is missing the alias `lib.match` -> `builtins.match`
      # therefore point uv2nix to a patched nixpkgs, which introduces this alias
      # this is a temporary solution until nixpkgs us up-to-date again
      inputs.nixpkgs.url = "github:juliankuners/nixpkgs/e9a77bb24d408d3898f6a11fb065d350d6bc71f1";
      # inputs.uv2nix.follows = "nixpkgs";
    };
    fenix = {
      url = "github:nix-community/fenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
  outputs = {
      self,
      k-framework,
      nixpkgs,
      flake-utils,
      kevm,
      rv-utils,
      foundry,
      solc,
      pyproject-nix,
      pyproject-build-systems,
      uv2nix,
      fenix,
      ... }:
  let
    pythonVer = "310";
  in flake-utils.lib.eachDefaultSystem (system:
    let
      fenixRustToolchain = fenix.packages.${system}.minimal.toolchain;
      # due to the nixpkgs that we use in this flake being outdated, uv is also heavily outdated
      # also provide more recent rust compiler with fenix
      uvOverlay = final: prev: {
        uv = final.callPackage ./nix/uv { inherit fenixRustToolchain; };
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
        default = kontrol;
      };
    }) // {
      overlays.default = final: prev: {
        inherit (self.packages.${final.system}) kontrol;
      };
    };
}
