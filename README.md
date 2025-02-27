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
poetry run kdist --verbose build -j2 evm-semantics.haskell kontrol.base
```

To change the default compiler:
```sh
CXX=clang++-14 poetry run kdist --verbose build -j2 evm-semantics.haskell kontrol.base
```

On Apple Silicon:
```sh
APPLE_SILICON=true poetry run kdist --verbose build -j2 evm-semantics.haskell kontrol.base
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

### Build Development Kontrol Image with Fixed Upstream Dependencies
--------------------------------
Relevant to this workflow [kontrol-push-fixed-deps.yml](.github/workflows/kontrol-push-fixed-deps.yml)
>This is relevant for internal development to publish development images of Kontrol with modified Kontrol changes and retain fixed upstream dependencies.
The use case for this workflow is intended to facilitate testing changes to Kontrol needed for use in testing CI or in other downstream workflows without needing to publish changes or PRs first.

The intent is to reduce the friction of needing custom builds and avoiding lengthy upstream changes and PRs.

### Build Kontrol with Kup and Specific Dependency Overrides
--------------------------------
Relevant to this workflow [kup-build-kontrol.yml](.github/workflows/kontrol-push-unfixed-deps.yml)
> This is relevant for internal development to publish development images of Kontrol for use in KaaS or a dockerized test environment.
Use the workflow [Kup Build Kontrol](.github/workflows/kup-build-kontrol.yml) to publish a custom version of Kontrol for use in CI and [KaaS](https://kaas.runtimeverification.com/).
[See KUP docs for more information](https://github.com/runtimeverification/kup/blob/master/src/kup/install-help.md#kup-install----override)

#### Using Kup 
-------------
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
> **Notice**: the 'follows' in the 'kup list' output. This shows the links to the important dependencies and which are affected when you set the overrides. 

Now run a build using kup and specific dependency overrides:    

`kup install kontrol --override kevm/k-framework/haskell-backend "hash/branch_name" --override kevm/k-framework/haskell-backend "hash"`  

> **Note**: It's important that you use the short-rev hash or the long for specific revisions of the dependencies to modify. 

#### Using the workflow to publish to ghcr.io/runtimeverification
--------------------------------

#### Running the workflow
- Go to repo [Kontrol Actions Page](https://github.com/runtimeverification/kontrol/actions) 
- Click on "Push Kontrol w/ Dependencies" from the left hand list 
- Click on "Run Workflow" on the top right corner of the list of workflow runs is an option "Run Workflow".
- Use the 'master' branch unless you're doing something special.
- Input the override hash strings for specific dependencies to override in kontrol. See below on how to find the hash for the dependency.
- Then click "Run Workflow" and a job will start.
- The workflow summary shows the name of the image that was built and pushed e.g. ghcr.io/runtimeverification/kontrol-custom:tag 

> **Note**: The tag will be a randomly generated string.

[The workflow](.github/workflows/kontrol-push-unfixed-deps.yml) takes multiple inputs to override the various components of kontrol. Those overrides are listed above in the example output of 'kup list kontrol --inputs' 

To set the desired revisions of the dependencies. Find the associated hash on the branch and commit made to be used for the dependnecy override. 
If an input is left blank, the workflow will workout the default hash to use based on kontrols latest release. 

Example to fetch the desired hash to insert a different dependency version into the kontrol build.
Substitude the k-framework revision used to build kontrol.
```
K_TAG=$(curl -s https://raw.githubusercontent.com/runtimeverification/kontrol/master/deps/k_release)
git ls-remote https://github.com/runtimeverification/k.git refs/tags/v${K_TAG} | awk '{print $1}'
```

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
