{
  description = "Tetris game written in Python (pygame)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      forAllSystems = f: nixpkgs.lib.genAttrs systems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pyTetris = pkgs.python3Packages.buildPythonApplication {
            pname = "py-tetris";
            version = "1.0.0";
            src = self;
            format = "setuptools";
            dependencies = [ pkgs.python3Packages.pygame ];
            meta = {
              description = "Tetris game written in Python";
              mainProgram = "py-tetris";
            };
          };
        in
        f pkgs pyTetris
      );
    in
    {
      packages = forAllSystems (_: pyTetris: { default = pyTetris; });

      apps = forAllSystems (_: pyTetris: {
        default = {
          type = "app";
          program = "${pyTetris}/bin/py-tetris";
        };
      });

      devShells = forAllSystems (pkgs: _pyTetris: {
        default = pkgs.mkShell {
          packages = [
            pkgs.python3
            pkgs.python3Packages.pygame
            pkgs.python3Packages.pytest
          ];
          shellHook = ''
            echo "Run the game with: python3 tetris.py  (or: nix run .#)"
            echo "Run the tests with: python3 -m pytest tests -v"
          '';
        };
      });

      checks = forAllSystems (pkgs: _pyTetris: {
        default = pkgs.stdenv.mkDerivation {
          pname = "py-tetris-tests";
          version = "1.0.0";
          src = self;
          nativeBuildInputs = [
            (pkgs.python3.withPackages (ps: with ps; [ ps.pytest ps.pygame ]))
          ];
          dontConfigure = true;
          dontMake = true;
          dontBuild = true;
          doCheck = true;
          installPhase = "mkdir -p $out";
          checkPhase = ''
            runHook preCheck
            python -m pytest tests -v
            runHook postCheck
          '';
        };
        mypy = pkgs.stdenv.mkDerivation {
          pname = "py-tetris-mypy";
          version = "1.0.0";
          src = self;
          nativeBuildInputs = [
            (pkgs.python3.withPackages (ps: with ps; [ ps.mypy ps.pygame ]))
          ];
          dontConfigure = true;
          dontMake = true;
          dontBuild = true;
          doCheck = true;
          installPhase = "mkdir -p $out";
          checkPhase = ''
            runHook preCheck
            python -m mypy --strict tetris.py
            runHook postCheck
          '';
        };
      });
    };
}
