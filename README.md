# Kontrol
Kontrol combines [KEVM](https://github.com/runtimeverification/evm-semantics) and [Foundry](https://book.getfoundry.sh/) to grant developers the ability to perform formal verification without learning a new language or tool. This is especially useful for those who are not verification engineers. Additionally, developers can leverage Foundry test suites they have already developed and use symbolic execution to increase the level of confidence.

## Documentation & Support
Documentation for Kontrol can be found in [Kontrol book](https://docs.runtimeverification.com/kontrol).

Join our [Kontrol Telegram Group](https://t.me/rv_kontrol) or [Discord server](https://discord.com/invite/CurfmXNtbN) if you have any questions or require support.

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
kup install k.openssl.secp256k1 --version v$(cat deps/k_release)
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

### Build Kontrol with Kup and Specific Dependency Override
> This is relevant for internal development to publish development images of kontrol for use in kaas or a dockerized test environment.
Use the workflow [Kup Build Kontrol](.github/workflows/kup-build-kontrol.yml) to publish a custom version of Kontrol for use in CI and [KaaS](https://kaas.runtimeverification.com/).
[See KUP docs for more information](https://github.com/runtimeverification/kup/blob/master/src/kup/install-help.md#kup-install----override) 

#### Using Kup 
Relevant dependency options are shown below and can be listed using `kup list kontrol --inputs`  
For example: 
```
Inputs:
├── k-framework - follows kevm/k-framework
├── kevm - github:runtimeverification/evm-semantics (6c2526b)
│   ├── blockchain-k-plugin - github:runtimeverification/blockchain-k-plugin (c9264b2)
│   │   ├── k-framework - github:runtimeverification/k (5d1ccd5)
│   │   │   ├── haskell-backend - github:runtimeverification/haskell-backend (d933d5c)
│   │   │   │   └── rv-utils - follows kevm/blockchain-k-plugin/k-framework/llvm-backend/rv-utils
│   │   │   ├── llvm-backend - github:runtimeverification/llvm-backend (37b1dd9)
│   │   │   │   ├── immer-src - github:runtimeverification/immer (4b0914f)
│   │   │   │   └── rv-utils - github:runtimeverification/rv-nix-tools (a650588)
│   │   │   └── rv-utils - follows kevm/blockchain-k-plugin/k-framework/llvm-backend/rv-utils
│   │   └── rv-utils - follows kevm/blockchain-k-plugin/k-framework/rv-utils
│   ├── haskell-backend - follows kevm/k-framework/haskell-backend
│   ├── k-framework - github:runtimeverification/k (81bcc24)
│   │   ├── haskell-backend - github:runtimeverification/haskell-backend (786c780)
│   │   │   └── rv-utils - follows kevm/k-framework/llvm-backend/rv-utils
│   │   ├── llvm-backend - github:runtimeverification/llvm-backend (d5eab4b)
│   │   │   ├── immer-src - github:runtimeverification/immer (4b0914f)
│   │   │   └── rv-utils - github:runtimeverification/rv-nix-tools (a650588)
│   │   └── rv-utils - follows kevm/k-framework/llvm-backend/rv-utils
│   └── rv-utils - follows kevm/k-framework/rv-utils
└── rv-utils - follows kevm/rv-utils
```
Now run a build using kup and specific dependency overrides:    

`kup install kontrol --override kevm/haskell-backend "hash/branch name" --override kevm/k-framework/haskell-backend "hash/branch name"`

#### Using the workflow and publish to ghcr.io/runtimeverification
The workflow takes a single input and ONLY a single override to fill in the paramater '--override' which is a string following the path from the above dep tree to be passed to kup install. Explained in more detail above.

Running the workflow by providing the override desired for the build. 

Example using the workflow to publish a ghcr.io/runtimeverification/kontrol-custom:tag image using kup `override` with a custom version of haskell-backend

The string to input to the workflow input job Under Actions > "Push Kontrol w/ Dependencies" on the top right corner of the list of workflow runs is an option "Run Workflow".
Select this option and input the override string as `kevm/k-framework/haskell-backend "hash/branch name"`
Then click "Run Workflow" and a job will start. The image when finished will be published to ghcr.io/runtimeverification/kontrol-custom:tag  

The tag will be a randomly generated string. See the workflow summary for the full name of the image to use in KaaS or pull down locally with `docker pull ghcr.io/runtimeverification/kontrol-custom:tag`


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
