ARG Z3_VERSION
ARG K_VERSION
ARG LLVM_VERSION

FROM ghcr.io/foundry-rs/foundry:rc-1 AS foundry

ARG Z3_VERSION
FROM runtimeverificationinc/z3:ubuntu-jammy-${Z3_VERSION} AS z3

ARG K_VERSION
FROM runtimeverificationinc/kframework-k:ubuntu-jammy-${K_VERSION}

COPY --from=foundry /usr/local/bin/forge /usr/local/bin/forge
COPY --from=foundry /usr/local/bin/anvil /usr/local/bin/anvil
COPY --from=foundry /usr/local/bin/cast /usr/local/bin/cast

COPY --from=z3 /usr/bin/z3 /usr/bin/z3

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
            libsecp256k1-dev           \
            libssl-dev                 \
            libyaml-dev                \
            llvm-${LLVM_VERSION}-dev   \
            llvm-${LLVM_VERSION}-tools \
            maven                      \
            python3                    \
            python3-pip

ARG IMAGE_USER=user
ARG IMAGE_GROUP
ARG USER_ID
ARG GROUP_ID
RUN groupadd -g ${GROUP_ID} ${IMAGE_GROUP} && useradd -m -u ${USER_ID} -s /bin/sh -g ${IMAGE_GROUP} ${IMAGE_USER}

USER ${IMAGE_USER}:${IMAGE_GROUP}
RUN mkdir /home/${IMAGE_USER}/workspace
WORKDIR /home/${IMAGE_USER}/workspace

ENV PATH=/home/${IMAGE_USER}/.cargo/bin:/home/${IMAGE_USER}/.local/bin:/usr/local/bin/:${PATH}

ARG UV_VERSION
RUN curl -LsSf https://astral.sh/uv/$UV_VERSION/install.sh | sh && uv --version

RUN    cargo install svm-rs --version 0.3.0 --locked \
    && svm install 0.8.13                            \
    && solc --version
