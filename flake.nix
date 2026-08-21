{
  description = "Tetris game written in Python (pygame)";

  inputs = {
    # stable: fewer surprise rebuilds; flake.lock pins the exact revision
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
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
            # nixpkgs' "pygame" is pygame-ce (dist "pygame-ce") on unstable
            # but upstream pygame (dist "pygame") on 26.05, so the wheel's
            # Requires-Dist name check can never pass on both; the real
            # dependency is provided by nix, so skip the redundant check
            dontCheckRuntimeDeps = true;
            # the test suite runs in checks.default, not during the build
            doInstallCheck = false;
            postInstall = ''
              install -Dm644 $src/py-tetris.desktop \
                $out/share/applications/py-tetris.desktop
              install -Dm644 $src/icons/py-tetris-128.png \
                $out/share/icons/hicolor/128x128/apps/py-tetris.png
              install -Dm644 $src/icons/py-tetris-512.png \
                $out/share/icons/hicolor/512x512/apps/py-tetris.png
            '';
            meta = {
              description = "Tetris game written in Python";
              mainProgram = "py-tetris";
              desktopName = "py-tetris.desktop";
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
