{
  lib,
  callPackage,
  nix-gitignore,
  stdenvNoCC,

  uv2nix,
  solc_version ? null,
}:
let
  # patches cannot yet be applied to uv workspaces, so we use a derivation containing the src instead
  src = stdenvNoCC.mkDerivation {
    name = "kontrol-pyk-src";
    src = callPackage ../kontrol-source { };

    dontConfigure = true;
    dontBuild = true;

    postPatch = ''
      ${lib.strings.optionalString (solc_version != null) ''
        substituteInPlace ./src/kontrol/foundry.py \
          --replace "'forge', 'build'," "'forge', 'build', '--no-auto-detect',"
      ''}
    '';

    installPhase = ''
      mkdir -p $out
      cp -r . $out/
    '';
  };

  # load a uv workspace from a workspace root
  workspace = uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = "${src}";
  };

  # create overlay
  lockFileOverlay = workspace.mkPyprojectOverlay {
    # prefer "wheel" over "sdist" due to maintance overhead
    # there is no bundled set of overlays for "sdist" in uv2nix, in contrast to poetry2nix
    sourcePreference = "wheel";
  };
in {
  inherit lockFileOverlay workspace;
}
