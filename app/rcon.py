from srcds.rcon import RconConnection


class RCON(RconConnection):
    def __init__(self, server, port=27015, password="", single_packet_mode=False):
        super().__init__(server, port=port, password=password, single_packet_mode=single_packet_mode)

    def __enter__(self):
        return self

    def __exit__(self):
        self._sock.close()
