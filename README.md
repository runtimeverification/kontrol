# Kontrol

## Documentation
Documentation for Kontrol can be found here: [https://docs.runtimeverification.com/kontrol](https://docs.runtimeverification.com/kontrol).

## Fast Installation

-   `bash <(curl https://kframework.org/install)`: install [kup package manager].
-   `kup install kontrol`: install Kontrol.
-   `kup list kontrol`: list available Kontrol versions.

**NOTE**: The first run will take longer to fetch all the libraries and compile sources. (30m to 1h)

## Build from source

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
poetry run kdist --verbose build -j2 evm-semantics.haskell kontrol.foundry
```

To change the default compiler:
```sh
CXX=clang++-14 poetry run kdist --verbose build -j2 evm-semantics.haskell kontrol.foundry
```

On Apple Silicon:
```sh
APPLE_SILICON=true poetry run kdist --verbose build -j2 evm-semantics.haskell kontrol.foundry
```

Targets can be cleaned with:
```sh
poetry run kdist clean
```

For more information, refer to `kdist --help`.


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

## Resources

-   [KEVM](https://github.com/runtimeverification/evm-semantics): Formal model of EVM in K Framework.
-   [EVM Yellowpaper](https://github.com/ethereum/yellowpaper): Original specification of EVM.

For more information about the [K Framework], refer to these sources:

-   [The K Tutorial](https://github.com/runtimeverification/k/tree/master/k-distribution/k-tutorial)
-   [Semantics-Based Program Verifiers for All Languages](https://fsl.cs.illinois.edu/publications/stefanescu-park-yuwen-li-rosu-2016-oopsla)
-   [Reachability Logic Resources](http://fsl.cs.illinois.edu/index.php/Reachability_Logic_in_K)
-   [Matching Logic Resources](http://www.matching-logic.org/)
-   [Logical Frameworks](https://dl.acm.org/doi/10.5555/208683.208700): Discussion of logical frameworks.

[K Framework]: <https://kframework.org>
[kup package manager]: <https://github.com/runtimeverification/kup>
