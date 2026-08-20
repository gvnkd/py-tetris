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
            pyproject = true;
            build-system = [ pkgs.python3Packages.setuptools ];
            dependencies = [ pkgs.python3Packages.pygame ];
            # the test suite runs in checks.default, not during the build
            doInstallCheck = false;
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
            pkgs.python3Packages.mypy
          ];
          shellHook = ''
            export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
            echo "Run the game with: python3 -m py_tetris  (or: nix run .#)"
            echo "Run the tests with: python3 -m pytest tests -v"
            echo "Type-check with:   python3 -m mypy"
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
            PYTHONPATH=src python -m pytest tests -v
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
            python -m mypy --strict src/py_tetris
            runHook postCheck
          '';
        };
      });
    };
}
