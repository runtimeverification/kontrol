ARG Z3_VERSION
ARG K_VERSION
FROM runtimeverificationinc/z3:ubuntu-jammy-${Z3_VERSION} as Z3

ARG K_VERSION
FROM runtimeverificationinc/kframework-k:ubuntu-jammy-${K_VERSION}

ARG PYTHON_VERSION=3.10

# Upgrade z3 to match the version Kontrol was built with not minimum version used in K.
COPY --from=Z3 /usr/bin/z3 /usr/bin/z3

RUN    apt-get -y update             \
    && apt-get -y install            \
         autoconf                    \
         cmake                       \
         curl                        \
         graphviz                    \
         libprocps-dev               \
         libsecp256k1-dev            \
         libssl-dev                  \
         libtool                     \
         python${PYTHON_VERSION}     \
         python${PYTHON_VERSION}-dev \
    && apt-get -y clean

ARG USER_ID=1010
ARG GROUP_ID=1010
RUN    groupadd -g ${GROUP_ID} user \
    && useradd -m -u ${USER_ID} -s /bin/bash -g user user

USER user
WORKDIR /home/user

ENV PATH=/home/user/.foundry/bin:${PATH}
RUN    curl -L https://foundry.paradigm.xyz | bash \
    && foundryup

ADD . kontrol
USER root
RUN chown -R user:user kontrol
USER user

ENV PATH=/home/user/.local/bin:${PATH}
RUN    pip install ./kontrol \
    && rm -rf kontrol        \
    && CXX=clang++-14 kevm-dist --verbose build -j4
