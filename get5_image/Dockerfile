###############################################
#        csgo-get5-docker Dockerfile          #
###############################################
##  Docker image containing CSGO with Get5   ##
##      plugin for setting up matches        ##
###############################################
#    github.com/theo-brown/csgo-get5docker    #
###############################################

FROM debian:bullseye-slim

###############
# CREATE USER #
###############
RUN useradd -m user

################
# INSTALL CSGO #
################
# Copy install script
# Install prerequisites
#   ca-certificates: required to trust downloads from the internet, including running csgo
#   wget: used to download steam and plugins
#   lib32stdc++6: required for source plugins
#   unzip: required to unzip get5
#   rsync: required to merge get5 directories
# Create directories
# Install SteamCMD
# Install CSGO
# Install plugins
# Clean up
ENV HOME_DIR=/home/user \
    CSGO_DIR=/home/user/csgo-server \
    METAMOD_URL=https://mms.alliedmods.net/mmsdrop/1.12/mmsource-1.12.0-git1164-linux.tar.gz \
    SOURCEMOD_URL=https://sm.alliedmods.net/smdrop/1.12/sourcemod-1.12.0-git6936-linux.tar.gz \
    GET5_URL=https://github.com/splewis/get5/releases/download/v0.11.0/get5-v0.11.0.tar.gz

WORKDIR $HOME_DIR

COPY --chown=user --chmod=755 server-scripts/server-update.sh $HOME_DIR/

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    dpkg --add-architecture i386 && \
    apt-add-repository non-free && \
    apt-get update

RUN echo steam steam/question select "I AGREE" | debconf-set-selections && \
    echo steam steam/license note '' | debconf-set-selections &&  \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y install steamcmd

RUN ln -sf /usr/games/steamcmd /usr/bin/steamcmd

RUN apt-get -qq update \
    && apt-get -qq install -y --no-install-recommends --no-install-suggests \
        ca-certificates \
        wget \
        lib32stdc++6 \
        unzip \
        rsync \
    && su user -c  \
       "mkdir $CSGO_DIR \
       && bash $HOME_DIR/server-update.sh"

RUN su user -c  \
       "wget -q -O - $METAMOD_URL | tar -xz -C $CSGO_DIR/csgo \
       && wget -q -O - $SOURCEMOD_URL | tar -xz -C $CSGO_DIR/csgo \
       && wget -q -O get5.tar.gz $GET5_URL \
       && tar -xzf get5.tar.gz \
       && rsync -aq addons/ $CSGO_DIR/csgo/addons \
       && rsync -aq cfg/ $CSGO_DIR/csgo/cfg \
       && rm -rf addons cfg get5.zip"

RUN apt install gdb -y

RUN apt-get -qq purge -y unzip rsync wget \
    && apt-get -qq autoremove -y \
    && apt-get -qq clean \
    && rm -rf /var/lib/apt/lists/*

######################
# COPY LAUNCH SCRIPT #
######################
COPY --chown=user --chmod=755 server-scripts/server-launch.sh $HOME_DIR/

################
# COPY CONFIGS #
################
COPY --chown=user cfg/* $CSGO_DIR/csgo/cfg/

# FORCE MANUAL UPDATE IN CONTAINER, simply increment the number on the echo command, this is not very clever or a good solution but, well... it works
RUN su user -c "bash $HOME_DIR/server-update.sh" && echo "2"

############
# RUN CSGO #
############
ENV UPDATE_ON_LAUNCH=0
USER user
CMD ["bash", "server-launch.sh"]