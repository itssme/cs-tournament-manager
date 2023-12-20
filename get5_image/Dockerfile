###############################################
#        cs2-get5-docker Dockerfile          #
###############################################
##  Docker image containing cs2 with Get5   ##
##      plugin for setting up matches        ##
###############################################
#    github.com/theo-brown/cs2-get5docker    #
###############################################

FROM debian:bullseye-slim

###############
# CREATE USER #
###############
RUN useradd -m user

################
# INSTALL cs2 #
################
# Copy install script
# Install prerequisites
#   ca-certificates: required to trust downloads from the internet, including running cs2
#   wget: used to download steam and plugins
#   lib32stdc++6: required for source plugins
#   unzip: required to unzip get5
#   rsync: required to merge get5 directories
# Create directories
# Install SteamCMD
# Install cs2
# Install plugins
# Clean up
ENV HOME_DIR=/home/user \
    cs2_DIR=/home/user/cs2-server

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
       "mkdir $cs2_DIR \
       && bash $HOME_DIR/server-update.sh"

# starting from GET5 v0.13, the veto system uses in game chat instead of a handy menu...
ENV METAMOD_URL=https://mms.alliedmods.net/mmsdrop/1.12/mmsource-1.12.0-git1167-linux.tar.gz \
    SOURCEMOD_URL=https://sm.alliedmods.net/smdrop/1.12/sourcemod-1.12.0-git7017-linux.tar.gz \
    STEAMWORKS_URL=https://github.com/KyleSanderson/SteamWorks/releases/download/1.2.3c/package-lin.tgz \
    GET5_URL=https://github.com/splewis/get5/releases/download/v0.12.1/get5-v0.12.1.tar.gz

RUN su user -c  \
       "wget -q -O - $METAMOD_URL | tar -xz -C $cs2_DIR/cs2 \
       && wget -q -O - $SOURCEMOD_URL | tar -xz -C $cs2_DIR/cs2 \
       && wget -q -O get5.tar.gz $GET5_URL \
       && tar -xzf get5.tar.gz \
       && rsync -aq addons/ $cs2_DIR/cs2/addons \
       && rsync -aq cfg/ $cs2_DIR/cs2/cfg \
       && rm -rf addons cfg get5.zip"

# steamworks:
RUN su user -c \
      "wget -q -O steamworks.tar.gz $STEAMWORKS_URL \
      && mkdir steamworks \
      && tar -xzf steamworks.tar.gz -C steamworks \
      && rsync -aq steamworks/package/addons/ $cs2_DIR/cs2/addons"

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
COPY --chown=user cfg/* $cs2_DIR/cs2/cfg/

# FORCE MANUAL UPDATE IN CONTAINER, simply increment the number on the echo command, this is not very clever or a good solution but, well... it works
RUN su user -c "bash $HOME_DIR/server-update.sh" && echo "1"

RUN echo '"STEAM_0:0:64160074" "99:z"' >> $cs2_DIR/cs2/addons/sourcemod/configs/admins_simple.ini \
    && echo '"STEAM_0:1:124584389" "99:z"' >> $cs2_DIR/cs2/addons/sourcemod/configs/admins_simple.ini

############
# RUN cs2 #
############
ENV UPDATE_ON_LAUNCH=0
USER user
CMD ["bash", "server-launch.sh"]
