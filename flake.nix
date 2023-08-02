{
  description = "kontrol - Foundry integration for KEVM";
  inputs = {
    nixpkgs.url = "nixpkgs/nixos-22.05";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };
  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    let
      allOverlays = [
        poetry2nix.overlay
        (final: prev: {
          kontrol = prev.poetry2nix.mkPoetryApplication {
            python = prev.python310;
            projectDir = ./.;
            groups = [];
            # We remove `dev` from `checkGroups`, so that poetry2nix does not try to resolve dev dependencies.
            checkGroups = [];
           };
        })
      ];
    in flake-utils.lib.eachSystem [
      "x86_64-linux"
      "x86_64-darwin"
      "aarch64-linux"
      "aarch64-darwin"
    ] (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = allOverlays;
        };
      in {
        packages = rec {
          inherit (pkgs) kontrol;
          default = kontrol;
        };
      }) // {
        overlay = nixpkgs.lib.composeManyExtensions allOverlays;
      };
}
