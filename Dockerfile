ARG K_VERSION
FROM runtimeverificationinc/kframework-k:ubuntu-jammy-${K_VERSION}

ARG PYTHON_VERSION=3.10

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

ARG USER_ID=1004
ARG GROUP_ID=1004
RUN    groupadd -g ${GROUP_ID} user \
    && useradd -m -u ${USER_ID} -s /bin/bash -g user user

ADD . kontrol
RUN chown -R user:user /home/user

USER user
ENV PATH=/home/user/.foundry/bin:${PATH}
RUN    curl -L https://foundry.paradigm.xyz | bash \
    && foundryup
ENV PATH=/home/user/.local/bin:${PATH}
RUN    pip install --user ./kontrol \
    && rm -rf kontrol        \
    && CXX=clang++-14 kevm-dist --verbose build -j4

WORKDIR /home/user
