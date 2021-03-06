FROM nvidia/cuda:9.0-cudnn7-devel-centos7

WORKDIR /root

RUN yum -y update \
    && yum -y install curl bzip2 \
    && curl -sSL https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -bfp /usr/local/ \
    && rm -rf /tmp/miniconda.sh \
    && conda install -y python=3 \
    && conda update conda \
    && conda clean --all --yes \
    && rpm -e --nodeps curl bzip2 \
    && yum clean all

RUN yum -y install epel-release
RUN yum -y install git make which gcc gcc-c++ libcurl-devel unzip zip jq curl

COPY battler.env.yml /root
RUN conda env create -f battler.env.yml

# Need to install pytorch after intel-openmp for pytorch to use omp
RUN bash -c 'source activate metagrok && conda install -y pytorch=1.0.1 cudatoolkit=9.0 -c pytorch'

RUN mkdir -p /root/scripts
COPY scripts/predef /root/scripts
COPY config.json /root

# Install vmtouch
COPY scripts/install-vmtouch.sh /root/scripts
RUN sh scripts/install-vmtouch.sh && rm scripts/install-vmtouch.sh

# Install htop
COPY scripts/install-htop.sh /root/scripts
RUN sh scripts/install-htop.sh && rm scripts/install-htop.sh

# Install nvm
COPY scripts/install-nvm.sh /root/scripts
RUN sh scripts/install-nvm.sh && rm scripts/install-nvm.sh

# Install Pokemon Showdown
COPY scripts/install-showdown.sh /root/scripts
RUN sh scripts/install-showdown.sh --no-client && rm scripts/install-showdown.sh

# Install everything else
COPY scripts /root/scripts
RUN sh scripts/install-more-conda-packages.sh

RUN echo 'set -o vi' >> /root/.bashrc
RUN echo 'source activate metagrok' >> /root/.bashrc