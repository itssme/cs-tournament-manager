echo "running server-launch.sh"

######################
# Set launch options #
######################
ARGS="-game cs2 -console -usercon +net_public_adr 0.0.0.0"

if [ -v SERVER_TOKEN ]
then
    ARGS="$ARGS +sv_setsteamaccount $SERVER_TOKEN"
fi
if [ -v PASSWORD ]
then
    ARGS="$ARGS +sv_password $PASSWORD"
fi
if [ -v RCON_PASSWORD ]
then
    ARGS="$ARGS +rcon_password $RCON_PASSWORD"
fi
if [ -v GOTV_PASSWORD ]
then
    ARGS="$ARGS +tv_password $GOTV_PASSWORD"
fi
if [ -v  PUBLIC_ADDRESS ]
then
    ARGS="$ARGS +net_public_adr $PUBLIC_ADDRESS"
fi
if [ -v IP ]
then
    ARGS="$ARGS -ip $IP"
else
    ARGS="$ARGS -ip 0.0.0.0"
fi
if [ -v PORT ]
then
    ARGS="$ARGS -port $PORT"
fi
if [ -v GOTV_PORT ]
then
    ARGS="$ARGS +tv_port $GOTV_PORT"
fi
if [ -v CLIENT_PORT ]
then
    ARGS="$ARGS +clientport $CLIENT_PORT"
fi
if [ -v TICKRATE ]
then
    ARGS="$ARGS -tickrate $TICKRATE"
else
    ARGS="$ARGS -tickrate 128"
fi
if [ -v MAXPLAYERS ]
then
    ARGS="$ARGS -maxplayers_override $MAXPLAYERS"
else
    ARGS="$ARGS -maxplayers_override 10"
fi
if [ -v GAMETYPE ]
then
    ARGS="$ARGS +game_type $GAMETYPE"
else
    ARGS="$ARGS +game_type 0"
fi
if [ -v GAMEMODE ]
then
    ARGS="$ARGS +game_mode $GAMEMODE"
else
    ARGS="$ARGS +game_mode 1"
fi
if [ -v MAPGROUP ]
then
    ARGS="$ARGS +mapgroup $MAPGROUP"
else
    ARGS="$ARGS +mapgroup mg_active"
fi
if [ -v MAP ]
then
    ARGS="$ARGS +map $MAP"
else
    ARGS="$ARGS +map cs_agecny"
fi
if [ -v HOST_WORKSHOP_COLLECTION ]
then
    ARGS="$ARGS +host_workshop_collection $HOST_WORKSHOP_COLLECTION"
fi
if [ -v WORKSHOP_START_MAP ]
then
    ARGS="$ARGS +workshop_start_map $WORKSHOP_START_MAP"
fi
if [ -v WORKSHOP_AUTHKEY ]
then
    ARGS="$ARGS -authkey $WORKSHOP_AUTHKEY"
fi
if [ -v AUTOEXEC ]
then
    ARGS="$ARGS +exec $AUTOEXEC"
fi
if [ $UPDATE_ON_LAUNCH -eq 1 ]
then
    ARGS="$ARGS -autoupdate"
fi
if [ -v CUSTOM_ARGS ]
then
    ARGS="$ARGS $CUSTOM_ARGS"
fi

if [ -v LOAD_BACKUP ]
then
    echo "Running backup of previous game, writing load command 'get5_loadmatch_url $LOAD_BACKUP' to $cs2_DIR/cs2/cfg/sourcemod/get5.cfg"
    echo "get5_loadbackup_url \"$LOAD_BACKUP\"" > $cs2_DIR/cs2/cfg/sourcemod/get5.cfg
else
  if [ -v MATCH_CONFIG ]
  then
      echo "Found match_config, writing load command to $cs2_DIR/cs2/cfg/sourcemod/get5.cfg"
      echo $MATCH_CONFIG > $cs2_DIR/cs2/match_config.json
      echo 'get5_autoload_config match_config.json' > $cs2_DIR/cs2/cfg/sourcemod/get5.cfg
      cat $cs2_DIR/cs2/match_config.json
      cat $cs2_DIR/cs2/cfg/sourcemod/get5.cfg
      echo "Done adding match_config to server"
  else
      echo "No match_config supplied, running server without loading a match"
      echo 'get5_check_auths 0' > $cs2_DIR/cs2/cfg/sourcemod/get5.cfg
    fi
fi

#################
# Launch server #
#################
cd $cs2_DIR
echo "./srcds_run $ARGS"
./srcds_run $ARGS
