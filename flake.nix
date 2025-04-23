{
  description = "Kontrol";

  inputs = {
    kevm.url = "github:runtimeverification/evm-semantics/v1.0.814";
    nixpkgs.follows = "kevm/nixpkgs";
    k-framework.follows = "kevm/k-framework";
    flake-utils.follows = "kevm/flake-utils";
    rv-utils.follows = "kevm/rv-utils";
    poetry2nix.follows = "kevm/poetry2nix";
    foundry = {
      url =
        "github:shazow/foundry.nix?rev=221d7506a99f285ec6aee26245c55bbef8a407f1"; # Use the same version as CI
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
    solc = {
      url = "github:goodlyrottenapple/solc.nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
  };
  outputs = { self, k-framework, nixpkgs, flake-utils, poetry2nix, kevm
    , rv-utils, foundry, solc, ... }@inputs:
    let
      nixLibs = pkgs:
        with pkgs;
        "-I${openssl.dev}/include -L${openssl.out}/lib -I${secp256k1}/include -L${secp256k1}/lib";
      overlay = final: prev:
        let
          poetry2nix =
            inputs.poetry2nix.lib.mkPoetry2Nix { pkgs = prev; };

          kontrol-pyk = { solc_version ? null }:
            (poetry2nix.mkPoetryApplication {
              python = prev.python310;
              projectDir = ./.;

              postPatch = ''
                ${prev.lib.strings.optionalString (solc_version != null) ''
                  substituteInPlace ./src/kontrol/foundry.py \
                    --replace "'forge', 'build'," "'forge', 'build', '--no-auto-detect',"
                ''}
                substituteInPlace ./pyproject.toml \
                  --replace ', subdirectory = "kevm-pyk"' ""
              '';

              overrides = poetry2nix.overrides.withDefaults
                (finalPython: prevPython: {
                  pyk = prev.pyk-python310;
                  kevm-pyk = prev.kevm-pyk;
                });
              groups = [ ];
              # We remove `"dev"` from `checkGroups`, so that poetry2nix does not try to resolve dev dependencies.
              checkGroups = [ ];
            });

          kontrol = { solc_version ? null }:
            prev.stdenv.mkDerivation {
              pname = "kontrol";
              version = self.rev or "dirty";
              buildInputs = with prev; [
                autoconf
                automake
                cmake
                git
                clang
                prev.kevm-pyk
                (kontrol-pyk { inherit solc_version; })
                k-framework.packages.${prev.system}.k
                boost
                libtool
                mpfr
                openssl.dev
                gmp
                pkg-config
                secp256k1
              ];
              nativeBuildInputs = [ prev.makeWrapper ];

              src = ./.;

              dontUseCmakeConfigure = true;

              enableParallelBuilding = true;

              buildPhase = ''
                XDG_CACHE_HOME=$(pwd) NIX_LIBS="${nixLibs prev}" ${
                  prev.lib.optionalString
                  (prev.stdenv.isAarch64 && prev.stdenv.isDarwin)
                  "APPLE_SILICON=true"
                } kdist -v build kontrol.base
              '';

              installPhase = ''
                mkdir -p $out
                cp -r ./kdist-*/* $out/
                ln -s ${prev.kevm}/evm-semantics $out/evm-semantics
                mkdir -p $out/bin
                ln -s ${prev.kevm}/bin/kevm $out/bin/kevm
                makeWrapper ${
                  (kontrol-pyk { inherit solc_version; })
                }/bin/kontrol $out/bin/kontrol --prefix PATH : ${
                  prev.lib.makeBinPath
                  ([ prev.which k-framework.packages.${prev.system}.k ]
                    ++ prev.lib.optionals (solc_version != null) [
                      final.foundry-bin
                      (solc.mkDefault final solc_version)
                    ])
                } --set NIX_LIBS "${nixLibs prev}" --set KDIST_DIR $out
              '';

              passthru = if solc_version == null then {
                # list all supported solc versions here
                solc_0_8_13 = kontrol { solc_version = final.solc_0_8_13; };
                solc_0_8_15 = kontrol { solc_version = final.solc_0_8_15; };
                solc_0_8_22 = kontrol { solc_version = final.solc_0_8_22; };
              } else
                { };
            };
        in { inherit kontrol; };
    in flake-utils.lib.eachSystem [
      "x86_64-linux"
      "x86_64-darwin"
      "aarch64-linux"
      "aarch64-darwin"
    ] (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [
            (final: prev: { llvm-backend-release = false; })
            k-framework.overlay
            k-framework.overlays.pyk
            foundry.overlay
            # Matching the version of Foundry with CI
            (final: prev: {
              foundry-bin =
                let
                  inherit (final.stdenv.hostPlatform) system;

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

                  src = final.fetchzip {
                    inherit (sources.${system}) url sha256;
                    stripRoot = false;
                  };
                in
                  final.stdenv.mkDerivation {
                    name = "foundry-bin";
                    src = src;
                    installPhase = ''
                      mkdir -p $out/bin
                      cp forge cast anvil chisel $out/bin/
                    '';
                  };
            })
            solc.overlay
            kevm.overlays.default
            overlay
          ];
        };
      in {
        devShell = kevm.devShell.${system}.overrideAttrs (old: {
          buildInputs = old.buildInputs
            ++ [ pkgs.foundry-bin (solc.mkDefault pkgs pkgs.solc_0_8_13) ];
        });
        packages = {
          kontrol = pkgs.kontrol { };
          default = pkgs.kontrol { };
        };
      }) // {
        overlays.default = overlay;
      };
}
