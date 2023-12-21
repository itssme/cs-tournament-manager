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
	&& mkdir -p "${STEAMAPPDIR}" \
	# Clean up
        && apt-get clean \
        && find /var/lib/apt/lists/ -type f -delete

# BASE

FROM build_stage AS bullseye-base

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
    TV_DELAY=0 \
    SRCDS_TOKEN="" \
    CS2_CFG_URL="" \
    CS2_ADDITIONAL_ARGS=""

# Set permissions on STEAMAPPDIR
#   Permissions may need to be reset if persistent volume mounted
RUN set -x \
        && chown -R "${USER}:${USER}" "${STEAMAPPDIR}" \
        && chmod 0777 "${STEAMAPPDIR}"

# Switch to user
USER ${USER}

WORKDIR ${HOMEDIR}

# Create App Dir
RUN mkdir -p "${STEAMAPPDIR}" || true

# Download Updates
RUN bash "${STEAMCMDDIR}/steamcmd.sh" +force_install_dir "${STEAMAPPDIR}" \
				+login anonymous \
				+app_update "${STEAMAPPID}" \
				+quit

USER root

COPY etc/entry.sh "${HOMEDIR}/entry.sh"
COPY etc/server.cfg "/etc/server.cfg"
COPY etc/pre.sh "/etc/pre.sh"
COPY etc/post.sh "/etc/post.sh"

# Add entry script
RUN chmod +x "${HOMEDIR}/entry.sh" \
	&& chown -R "${USER}:${USER}" "${HOMEDIR}/entry.sh" "${STEAMAPPDIR}"

# Switch to user
USER ${USER}

CMD ["bash", "entry.sh"]
