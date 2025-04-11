# copied from https://github.com/NixOS/nixpkgs/blob/b73fc9705bfca9ad9799bb7c8d9a1947cbd8662a/pkgs/by-name/uv/uv/package.nix
# in the stale nixpkgs from this flake, uv is too out-of-date for proper use
# though, we also need to update rustc and cargo to more recent version that we take from fenix
# this is a temporary solution until nixpkgs in our flake is up-to-date again
# slightly modified in order to make it build properly on stale nixpkgs

{
  lib,
  stdenv,
  rustPlatform,
  fetchFromGitHub,

  # buildInputs
  rust-jemalloc-sys,

  # nativeBuildInputs
  cmake,
  installShellFiles,
  pkg-config,

  buildPackages,
  python3Packages,
  nix-update-script,

  # use different rust distribution in nix
  makeRustPlatform,
  fenixRustToolchain,
}:

(makeRustPlatform {
  cargo = fenixRustToolchain;
  rustc = fenixRustToolchain;
}).buildRustPackage rec {
  pname = "uv";
  version = "0.6.13";

  src = fetchFromGitHub {
    owner = "astral-sh";
    repo = "uv";
    rev = version;
    hash = "sha256-vJvF8ioEtiriWh120WhMxkYSody04PuXA6EISjWWvYA=";
  };

  useFetchCargoVendor = true;
  cargoHash = "sha256-pwbqYe2zdQJQGoqrIwryBHmnS8spPgQ0qdpmxdT+9sk=";

  buildInputs = [
    # rust-jemalloc-sys
  ];

  nativeBuildInputs = [
    cmake
    installShellFiles
    pkg-config
  ];

  cargoLock = {
    lockFile = "${src}/Cargo.lock";
    outputHashes = {
      "async_zip-0.0.17" = "sha256-VfQg2ZY5F2cFoYQZrtf2DHj0lWgivZtFaFJKZ4oyYdo=";
      "pubgrub-0.3.0-alpha.1" = "sha256-FF10Ia2fvBIP/toxnjh/bqjHazFDChMd2qQzASGZLiM=";
      "tl-0.7.8" = "sha256-F06zVeSZA4adT6AzLzz1i9uxpI1b8P1h+05fFfjm3GQ=";
    };
  };

  dontUseCmakeConfigure = true;

  cargoBuildFlags = [
    "--package"
    "uv"
  ];

  # Tests require python3
  doCheck = false;

  postInstall = lib.optionalString (stdenv.hostPlatform.emulatorAvailable buildPackages) (
    let
      emulator = stdenv.hostPlatform.emulator buildPackages;
    in
    ''
      installShellCompletion --cmd uv \
        --bash <(${emulator} $out/bin/uv generate-shell-completion bash) \
        --fish <(${emulator} $out/bin/uv generate-shell-completion fish) \
        --zsh <(${emulator} $out/bin/uv generate-shell-completion zsh)
    ''
  );

  doInstallCheck = true;

  passthru = {
    tests.uv-python = python3Packages.uv;
    updateScript = nix-update-script { };
  };

  meta = {
    description = "Extremely fast Python package installer and resolver, written in Rust";
    homepage = "https://github.com/astral-sh/uv";
    changelog = "https://github.com/astral-sh/uv/blob/${version}/CHANGELOG.md";
    license = with lib.licenses; [
      asl20
      mit
    ];
    maintainers = with lib.maintainers; [ GaetanLepage ];
    mainProgram = "uv";
  };
}