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

ARG USER_ID=9876
ARG GROUP_ID=9876
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
RUN ls -l /home/user
USER user

ENV PATH=/home/user/.local/bin:${PATH}
RUN    pip install ./kontrol \
    && rm -rf kontrol        \
    && CXX=clang++-14 kevm-dist --verbose build -j4
