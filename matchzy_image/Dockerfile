###########################################################
# Dockerfile that builds a CS2 Gameserver
###########################################################

# BUILD STAGE

FROM cm2network/steamcmd:root as build_stage

ENV STEAMAPPID 730
ENV STEAMAPP cs2
ENV STEAMAPPDIR "${HOMEDIR}/${STEAMAPP}-dedicated"

RUN set -x \
	# Install, update & upgrade packages
	&& apt-get update \
	&& apt-get install -y --no-install-recommends --no-install-suggests \
		wget \
		ca-certificates \
		lib32z1 \
        simpleproxy \
        libicu-dev \
        unzip \
	&& mkdir -p "${STEAMAPPDIR}" \
	# Clean up
        && apt-get clean \
        && find /var/lib/apt/lists/ -type f -delete

# BASE

FROM build_stage AS bullseye-base

# Set permissions on STEAMAPPDIR
#   Permissions may need to be reset if persistent volume mounted
RUN set -x \
        && chown -R "${USER}:${USER}" "${STEAMAPPDIR}" \
        && chmod 0777 "${STEAMAPPDIR}"

# Switch to user
#USER ${USER}

WORKDIR ${HOMEDIR}

# Create App Dir
RUN mkdir -p "${STEAMAPPDIR}" || true

# Download Updates
RUN bash "${STEAMCMDDIR}/steamcmd.sh" +force_install_dir "${STEAMAPPDIR}" \
				+login anonymous \
				+app_update "${STEAMAPPID}" \
				+quit

#USER root

# Give ${USER} permission for cs2 game folder
#RUN chown -R "${USER}:${USER}" "${STEAMAPPDIR}"

#USER ${USER}

# TODO: remove .tar.gz files after installation

# Installation of metamod
ENV METAMOD_URL=https://mms.alliedmods.net/mmsdrop/2.0/mmsource-2.0.0-git1284-linux.tar.gz
RUN wget -q -O - $METAMOD_URL | tar -xz -C ${STEAMAPPDIR}/game/csgo

# Installation of matchzy (with cssharp)
ENV MATCHZY_URL=https://github.com/shobhit-pathak/MatchZy/releases/download/0.7.0/matchzy-0.7.0-with-cssharp.zip
RUN wget -O matchzy.zip $MATCHZY_URL && unzip matchzy.zip -d ${STEAMAPPDIR}/game/csgo && rm matchzy.zip

# DEBUG
#RUN ls ${STEAMAPPDIR}/game/csgo/addons -l && pwd ${STEAMAPPDIR}/game/csgo && quit 1

#USER root

#RUN chown -R "${USER}:${USER}" "${STEAMAPPDIR}/game/csgo/addons" && \
#    chmod 777 ${STEAMAPPDIR}/game/csgo/addons -R

# copy entry scripts and server config
COPY etc/entry.sh "${HOMEDIR}/entry.sh"
COPY etc/server.cfg "/etc/server.cfg"
COPY etc/pre.sh "/etc/pre.sh"
COPY etc/post.sh "/etc/post.sh"
COPY etc/acmrs.sh "/etc/acmrs.sh"

# set default env variables
ENV CS2_SERVERNAME="cs2 private server" \
    CS2_IP=0.0.0.0 \
    CS2_SERVER_HIBERNATE=0 \
    CS2_PORT=27015 \
    CS2_RCON_PORT="" \
    CS2_MAXPLAYERS=10 \
    CS2_RCONPW="pass" \
    CS2_PW="" \
    CS2_MAPGROUP="mg_active" \
    CS2_STARTMAP="cs_office" \
    CS2_GAMEALIAS="" \
    CS2_GAMETYPE=0 \
    CS2_GAMEMODE=1 \
    CS2_LAN=0 \
    TV_AUTORECORD=0 \
    TV_ENABLE=0 \
    TV_PORT=27020 \
    TV_PW="pass" \
    TV_RELAY_PW="pass" \
    TV_MAXRATE=0 \
    TV_DELAY=1 \
    SRCDS_TOKEN="" \
    CS2_CFG_URL="" \
    CS2_ADDITIONAL_ARGS=""

#RUN chown -R "${USER}:${USER}" "${HOMEDIR}/entry.sh"

# Switch to user
#USER ${USER}

CMD ["bash", "entry.sh"]
