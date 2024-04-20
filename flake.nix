{
  description = "Kontrol";

  inputs = {
    kevm.url = "github:runtimeverification/evm-semantics/v1.0.532";
    nixpkgs.follows = "kevm/nixpkgs";
    nixpkgs-pyk.follows = "kevm/nixpkgs-pyk";
    k-framework.follows = "kevm/k-framework";
    flake-utils.follows = "kevm/flake-utils";
    rv-utils.follows = "kevm/rv-utils";
    pyk.follows = "kevm/pyk";
    poetry2nix.follows = "kevm/poetry2nix";
    foundry = {
      url =
        "github:shazow/foundry.nix/monthly"; # Use monthly branch for permanent releases
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
    solc = {
      url = "github:hellwolf/solc.nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
  };
  outputs = { self, k-framework, nixpkgs, flake-utils, poetry2nix, kevm
    , rv-utils, pyk, foundry, solc, ... }@inputs:
    let
      nixLibs = pkgs:
        with pkgs;
        "-I${procps}/include -L${procps}/lib -I${openssl.dev}/include -L${openssl.out}/lib -I${secp256k1}/include -L${secp256k1}/lib";
      overlay = final: prev:
        let
          nixpkgs-pyk = import inputs.nixpkgs-pyk {
            system = prev.system;
            overlays = [ pyk.overlay ];
          };
          poetry2nix =
            inputs.poetry2nix.lib.mkPoetry2Nix { pkgs = nixpkgs-pyk; };

          kontrol-pyk = { solc_version ? null }:
            (poetry2nix.mkPoetryApplication {
              python = nixpkgs-pyk.python310;
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
                  pyk = nixpkgs-pyk.pyk-python310;
                  kevm-pyk = prev.kevm-pyk;
                  xdg-base-dirs = prevPython.xdg-base-dirs.overridePythonAttrs
                    (old: {
                      propagatedBuildInputs = (old.propagatedBuildInputs or [ ])
                        ++ [ finalPython.poetry ];
                    });
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
                # This is somewhat hacky but it's only a build time dependency.
                # We basically override kevm-pyk to add kontrol as a runtime dependency
                # so that kdist finds the foundry target.
                (prev.kevm-pyk.overridePythonAttrs (old: {
                  propagatedBuildInputs = (old.propagatedBuildInputs or [ ])
                    ++ [
                      ((kontrol-pyk { inherit solc_version; }).overrideAttrs
                        (oldAttrs: { propagatedBuildInputs = [ ]; }))
                    ];
                }))
                k-framework.packages.${prev.system}.k
                libtool
                openssl.dev
                gmp
                pkg-config
                procps
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
                } kdist build kontrol.foundry
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
            foundry.overlay
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
