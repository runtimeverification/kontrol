{
  description = "Kontrol";

  inputs = {
    kevm.url = "github:runtimeverification/evm-semantics/v1.0.323";
    nixpkgs.follows = "kevm/nixpkgs";
    k-framework.follows = "kevm/k-framework";
    k-framework.inputs.nixpkgs.follows = "nixpkgs";
    flake-utils.follows = "kevm/flake-utils";
    rv-utils.url = "github:runtimeverification/rv-nix-tools";
    pyk.follows = "kevm/pyk";
    pyk.inputs.flake-utils.follows = "k-framework/flake-utils";
    pyk.inputs.nixpkgs.follows = "k-framework/nixpkgs";
    poetry2nix.follows = "kevm/poetry2nix";
    foundry.url =
      "github:shazow/foundry.nix/monthly"; # Use monthly branch for permanent releases
    solc = {
      url = "github:hellwolf/solc.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
  outputs = { self, k-framework, nixpkgs, flake-utils, poetry2nix, kevm
    , rv-utils, pyk, foundry, solc }:
    let
      nixLibs = pkgs:
        with pkgs;
        "-I${procps}/include -L${procps}/lib -I${openssl.dev}/include -L${openssl.out}/lib";
      overlay = final: prev:
        let
          kontrol-pyk = { solc_version ? null }:
            (prev.poetry2nix.mkPoetryApplication {
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

              overrides = prev.poetry2nix.overrides.withDefaults
                (finalPython: prevPython: {
                  pyk = prev.pyk-python310;
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
                (kevm-pyk.overridePythonAttrs (old: {
                  propagatedBuildInputs = (old.propagatedBuildInputs or [ ])
                    ++ [ (kontrol-pyk { inherit solc_version; }) ];
                }))
                k-framework.packages.${prev.system}.k
                libtool
                openssl.dev
                gmp
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
                } kevm-dist build -j4 foundryx
              '';

              installPhase =
                let kevm = prev.kevm k-framework.packages.${prev.system}.k;
                in ''
                  mkdir -p $out
                  cp -r ./kdist-*/* $out/
                  ln -s ${kevm}/haskell $out/haskell
                  ln -s ${kevm}/haskell-standalone $out/haskell-standalone
                  ln -s ${kevm}/llvm $out/llvm
                  ln -s ${kevm}/plugin $out/plugin
                  mkdir -p $out/bin
                  makeWrapper ${
                    (kontrol-pyk { inherit solc_version; })
                  }/bin/kontrol $out/bin/kontrol --prefix PATH : ${
                    prev.lib.makeBinPath
                    ([ prev.which k-framework.packages.${prev.system}.k ]
                      ++ prev.lib.optionals (solc_version != null) [
                        final.foundry-bin
                        (solc.mkDefault final solc_version)
                      ])
                  } --set NIX_LIBS "${nixLibs prev}" --set KEVM_DIST_DIR $out
                '';

              passthru = if solc_version == null then {
                # list all supported solc versions here
                solc_0_8_13 = kontrol { solc_version = final.solc_0_8_13; };
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
            poetry2nix.overlay
            pyk.overlay
            foundry.overlay
            solc.overlay
            kevm.overlays.default
            overlay
          ];
        };
      in {
        packages = {
          kontrol = pkgs.kontrol { };
          default = pkgs.kontrol { };
        };
      }) // {
        overlays.default = overlay;
      };
}
