# Kontrol

Fast Installation
-----------------

-   `bash <(curl https://kframework.org/install)`: install [kup package manager].
-   `kup install kontrol`: install Kontrol.
-   `kup list kontrol`: list available Kontrol versions.

**NOTE**: The first run will take longer to fetch all the libraries and compile sources. (30m to 1h)

### Build from source

#### K Framework

You need to install the [K Framework] on your system, see the instructions there.
The fastest way is via the [kup package manager], with which you can do to get the correct version of K:

```sh
kup install k.openssl.procps --version v$(cat deps/k_release)
```

#### Poetry dependencies

First you need to set up all the dependencies of the virtual environment using Poetry with the prerequisites `python 3.8.*`, `pip >= 20.0.2`, `poetry >= 1.3.2`:
```sh
poetry install
```

#### Build using the virtual environment

In order to build `kontrol`, you need to build these specific targets:
```sh
poetry run kevm-dist --verbose build -j`nproc` plugin haskell foundryx
```

To change the default compiler:
```sh
CXX=clang++-14 poetry run kevm-dist --verbose build -j`nproc` plugin haskell foundryx
```

On Apple Silicon:
```sh
APPLE_SILICON=true poetry run kevm-dist --verbose build -j`nproc` plugin haskell foundryx
```

Targets can be cleaned with:
```sh
poetry run kevm-dist clean
```

For more information, refer to `kevm-dist --help`.


## For developers

Use `make` to run common tasks (see the [Makefile](Makefile) for a complete list of available targets).

* `make build`: Build wheel
* `make check`: Check code style
* `make format`: Format code
* `make test-unit`: Run unit tests

To update the expected output of the tests, use the `--update-expected-output` flag:
```sh
make cov-integration TEST_ARGS="--numprocesses=8 --update-expected-output"
```

For interactive use, spawn a shell with `poetry shell` (after `poetry install`), then run an interpreter.
