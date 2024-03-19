ARG Z3_VERSION
ARG K_VERSION
ARG BASE_DISTRO
ARG LLVM_VERSION

FROM ghcr.io/foundry-rs/foundry:nightly-7545c7a2857a873fa1909ec4174032c4e4702116 as FOUNDRY

ARG Z3_VERSION
FROM runtimeverificationinc/z3:ubuntu-jammy-${Z3_VERSION} as Z3

ARG K_VERSION
FROM runtimeverificationinc/kframework-k:ubuntu-jammy-${K_VERSION}

COPY --from=FOUNDRY /usr/local/bin/forge /usr/local/bin/forge
COPY --from=FOUNDRY /usr/local/bin/anvil /usr/local/bin/anvil
COPY --from=FOUNDRY /usr/local/bin/cast /usr/local/bin/cast

COPY --from=Z3 /usr/bin/z3 /usr/bin/z3

ARG LLVM_VERSION

RUN    apt-get update                  \
    && apt-get upgrade --yes           \
    && apt-get install --yes           \
            cargo                      \
            clang-${LLVM_VERSION}      \
            cmake                      \
            curl                       \
            debhelper                  \

            libboost-test-dev          \
            libcrypto++-dev            \
            libprocps-dev              \
            libsecp256k1-dev           \
            libssl-dev                 \
            libyaml-dev                \
            llvm-${LLVM_VERSION}-dev   \
            llvm-${LLVM_VERSION}-tools \
            maven                      \
            python3                    \
            python3-pip

ARG USER=user
ARG GROUP
ARG USER_ID
ARG GROUP_ID
RUN groupadd -g ${GROUP_ID} ${GROUP} && useradd -m -u ${USER_ID} -s /bin/sh -g ${GROUP} ${USER}

USER ${USER}:${GROUP}
RUN mkdir /home/${USER}/workspace
WORKDIR /home/${USER}/workspace

ENV PATH=/home/${USER}/.cargo/bin:/home/${USER}/.local/bin:/usr/local/bin/:${PATH}

RUN    curl -sSL https://install.python-poetry.org | python3 - \
    && poetry --version

RUN    cargo install svm-rs --version 0.3.0 --locked \
    && svm install 0.8.13                            \
    && solc --version
