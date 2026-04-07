{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs";
    nixpkgs24.url = "github:nixos/nixpkgs/24.11";
    nixpkgs22.url = "github:nixos/nixpkgs/22.11";
    nixpkgsUnstable.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flakeUtils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, nixpkgs24, nixpkgs22, nixpkgsUnstable, flakeUtils }:
    flakeUtils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pkgs24 = nixpkgs24.legacyPackages.${system};
        pkgs22 = nixpkgs22.legacyPackages.${system};
        pkgsUnstable = nixpkgsUnstable.legacyPackages.${system};
      in {
        packages = flakeUtils.lib.flattenTree {
          python314 = pkgs.python314;
          python313 = pkgs.python313;
          python312 = pkgs.python312;
          python311 = pkgs.python311;
          python310 = pkgs24.python310;
          python39 = pkgs24.python39;
          python38 = pkgs22.python38;
          go-task = pkgsUnstable.go-task;
        };
        devShell = pkgs.mkShell {
          buildInputs = with self.packages.${system}; [
            python314
            python313
            python312
            python311
            python310
            python39
            python38
            go-task
          ];
          shellHook = ''
            [[ ! -d .venv ]] && \
              echo "Creating virtualenv ..." && \
              ${pkgs24.python310}/bin/python -m \
                venv --copies --upgrade-deps .venv > /dev/null
            source .venv/bin/activate
          '';
        };
      }
    );
}
