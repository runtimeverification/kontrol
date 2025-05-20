{
  lib,
  stdenv,
  runCommand,
  makeWrapper,
  callPackage,

  autoconf,
  automake,
  cmake,
  git,
  clang,
  k,
  boost,
  libtool,
  mpfr,
  openssl,
  gmp,
  pkg-config,
  secp256k1,
  kevm,
  which,
  foundry-bin,
  solcMkDefault,
  solc_0_8_13,
  solc_0_8_15,
  solc_0_8_22,

  kontrol-pyk,
  solc_version ? null,
  rev ? null
} @ args:
let
  kontrol-pyk-solc = kontrol-pyk.override { inherit solc_version; };
  nixLibs = "-I${openssl.dev}/include -L${openssl.out}/lib -I${secp256k1}/include -L${secp256k1}/lib";
in
stdenv.mkDerivation {
  pname = "kontrol";
  version = if (rev != null) then rev else "dirty";
  buildInputs = [
    autoconf
    automake
    cmake
    git
    clang
    kontrol-pyk-solc
    k
    boost
    libtool
    mpfr
    openssl.dev
    gmp
    pkg-config
    secp256k1
  ];
  nativeBuildInputs = [ makeWrapper ];

  src = callPackage ../kontrol-source { };

  dontUseCmakeConfigure = true;

  enableParallelBuilding = true;

  buildPhase = ''
    XDG_CACHE_HOME=$(pwd) NIX_LIBS="${nixLibs}" ${
      lib.optionalString
      (stdenv.isAarch64 && stdenv.isDarwin)
      "APPLE_SILICON=true"
    } kontrol-kdist -v build kontrol.base
  '';

  installPhase = ''
    mkdir -p $out
    cp -r ./kdist-*/* $out/
    ln -s ${kevm}/evm-semantics $out/evm-semantics
    mkdir -p $out/bin
    ln -s ${kevm}/bin/kevm $out/bin/kevm
    makeWrapper ${kontrol-pyk-solc}/bin/kontrol $out/bin/kontrol --prefix PATH : ${
      lib.makeBinPath
      ([ which k ] ++ lib.optionals (solc_version != null) [
        foundry-bin
        (solcMkDefault { inherit runCommand lib; } solc_version)
      ])
    } --set NIX_LIBS "${nixLibs}" --set KDIST_DIR $out
  '';

  passthru = if solc_version == null then {
    # list all supported solc versions here
    solc_0_8_13 = callPackage ./default.nix (args // { solc_version = solc_0_8_13; });
    solc_0_8_15 = callPackage ./default.nix (args // { solc_version = solc_0_8_15; });
    solc_0_8_22 = callPackage ./default.nix (args // { solc_version = solc_0_8_22; });
  } else { };
}