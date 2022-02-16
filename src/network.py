import math


class Packet:
    C2S = False
    S2C = False

    def __init__(self):
        pass

    def save(self):
        return {}

    def load(self, packet: dict):
        return self


class InvalidPacketError(KeyError):
    pass


class IncompletePacketWarning(RuntimeWarning):
    pass


def verify_packet(packet, **kwargs):
    for name in kwargs:
        if hasattr(packet, name):
            if type(packet[name]) != kwargs[name]:
                raise IncompletePacketWarning("Invalid type")
        else:
            raise IncompletePacketWarning("Missing attribute")


name_to_packet = {}
packet_to_name = {}


def register(name, packet):
    name_to_packet[name] = packet
    packet_to_name[packet] = name


###############
#  Handshake  #
###############

class HandshakeInit(Packet):
    C2S = True
    S2C = False

    def __init__(self, name="Player", secret=""):
        super().__init__()
        self.name = name
        self.secret = secret

        if type(self.name) != str or type(self.secret) != str:
            raise InvalidPacketError(
                f"Bad argument types: name<{type(self.name)}> should be str, secret<{type(self.secret)}> should be str")

    def save(self):
        return {"name": self.name, "secret": self.secret}

    def load(self, packet: dict):
        self.name = packet.get("name", "Player")
        self.secret = packet.get("secret", "")

        verify_packet(packet, name=str)

        return self


class HandshakeRespond(Packet):
    C2S = False
    S2C = True

    def __init__(self, accepted=False, reason=""):
        super().__init__()
        self.accepted = accepted
        self.reason = reason

        if type(self.accepted) != bool or type(self.reason) != str:
            raise InvalidPacketError("Bad types for HandshakeRespond")

    def save(self):
        return {"accepted": self.accepted, "reason": self.reason}

    def load(self, packet: dict):
        self.accepted = packet.get("accepted", False)
        self.reason = packet.get("reason", "")

        verify_packet(packet, accepted=bool)

        return self


class HandshakeRequestGameInfo(Packet):
    C2S = True
    S2C = False

    def __init__(self):
        super().__init__()

    def save(self):
        return {}

    def load(self, packet: dict):
        return self


class HandshakeGameInfo(Packet):
    C2S = False
    S2C = True

    def __init__(self, border=1200, max_turn=math.pi / 90):
        super().__init__()
        self.border = border
        self.max_turn = max_turn

        if type(self.border) != int or type(self.max_turn) != float:
            raise InvalidPacketError("Bad types for HandshakeGameInfo")

    def save(self):
        return {"border": self.border, "max_turn": self.max_turn}

    def load(self, packet: dict):
        self.border = packet.get("border", 1200)
        self.max_turn = packet.get("max_turn", math.pi / 90)

        verify_packet(packet, border=int, max_turn=float)

        return self


class HandshakeStartGame(Packet):
    C2S = True
    S2C = False

    def __init__(self):
        super().__init__()

    def save(self):
        return {}

    def load(self, packet: dict):
        return self


#######################
#  Client ==> Server  #
#######################

class C2SUpdateInput(Packet):
    C2S = True
    S2C = False

    def __init__(self, angle: float = 0.5, sprinting: bool = None):
        super().__init__()
        self.angle = angle
        self.sprinting = sprinting

        if type(self.angle) != float or type(self.sprinting) != bool:
            raise InvalidPacketError("Bad types for C2SUpdateInput")

    def save(self):
        return {"angle": self.angle, "sprinting": self.sprinting}

    def load(self, packet: dict):
        self.angle = packet.get("angle", 0.0)
        self.sprinting = packet.get("sprinting", False)

        verify_packet(packet, angle=float, sprinting=bool)

        return self


class C2SQuit(Packet):
    C2S = True
    S2C = False

    def __init__(self):
        super().__init__()

    def save(self):
        return {}

    def load(self, packet: dict):
        return self


class C2SResend(Packet):
    C2S = True
    S2C = False

    def __init__(self):
        super().__init__()

    def save(self):
        return {}

    def load(self, packet: dict):
        return self


#######################
#  Server ==> Client  #
#######################

class S2CModifySegment(Packet):
    C2S = False
    S2C = True

    def __init__(self, uuid="ERROR", ishead=None, isown=None, radius=None, angle=None, pos=None, col=None):
        super().__init__()
        self.uuid = uuid
        self.ishead = ishead
        self.isown = isown
        self.radius = radius
        self.angle = angle
        self.pos = pos
        self.col = col

    def save(self):
        return {
            "uuid": self.uuid,
            "ishead": self.ishead,
            "isown": self.isown,
            "radius": self.radius,
            "angle": self.angle,
            "pos": self.pos,
            "col": self.col
        }

    def load(self, packet: dict):
        self.uuid = packet.get("uuid", "ERROR")
        self.ishead = packet.get("ishead", False)
        self.isown = packet.get("isown", False)
        self.radius = packet.get("radius", 10)
        self.angle = packet.get("angle", 0.0)
        self.pos = packet.get("pos", (0, 0))
        self.col = packet.get("col", (255, 0, 255))

        verify_packet(packet, uuid=str, ishead=bool, isown=bool, radius=int, angle=float, pos=tuple, col=tuple)

        return self


class S2CRemoveSegment(Packet):
    C2S = False
    S2C = True

    def __init__(self, uuid="ERROR"):
        super().__init__()
        self.uuid = uuid

        if type(self.uuid) != str:
            raise InvalidPacketError("Bad types for S2CRemoveSegment")

    def save(self):
        return {"uuid": self.uuid}

    def load(self, packet: dict):
        self.uuid = packet.get("uuid", "ERROR")

        verify_packet(packet, uuid=str)

        return self


class S2CAddFood(Packet):
    C2S = False
    S2C = True

    def __init__(self, uuid="ERROR", pos=None, col=None, radius=None, energy=None):
        super().__init__()
        self.uuid = uuid
        self.pos = pos
        self.col = col
        self.radius = radius
        self.energy = energy

    def save(self):
        return {"uuid": self.uuid, "pos": self.pos, "col": self.col, "radius": self.radius, "energy": self.energy}

    def load(self, packet: dict):
        self.uuid = packet.get("uuid", "ERROR")
        self.pos = packet.get("pos", (0, 0))
        self.col = packet.get("col", (255, 0, 255))
        self.radius = packet.get("radius", 10)
        self.energy = packet.get("energy", 1)

        verify_packet(packet, uuid=str, pos=tuple, col=tuple, radius=int, energy=int)

        return self


class S2CRemoveFood(Packet):
    C2S = False
    S2C = True

    def __init__(self, uuid="ERROR"):
        super().__init__()
        self.uuid = uuid

        if type(self.uuid) != str:
            raise InvalidPacketError("Bad types for S2CRemoveFood")

    def save(self):
        return {"uuid": self.uuid}

    def load(self, packet: dict):
        self.uuid = packet.get("uuid", "ERROR")

        verify_packet(packet, uuid=str)

        return self


class S2CKill(Packet):
    C2S = False
    S2C = True

    def __init__(self, msg="You died."):
        super().__init__()
        self.msg = msg

        if type(self.msg) != str:
            raise InvalidPacketError("Bad types for S2CKill")

    def save(self):
        return {"msg": self.msg}

    def load(self, packet: dict):
        self.msg = packet.get("msg", "You died.")

        return self


class S2CResending(Packet):
    C2S = False
    S2C = True

    def __init__(self):
        super().__init__()

    def save(self):
        return {}

    def load(self, packet: dict):
        return self


register(HandshakeInit, "h_init")
register(HandshakeRespond, "h_respond")
register(HandshakeGameInfo, "h_gameinfo")
register(HandshakeStartGame, "h_startgame")
register(HandshakeRequestGameInfo, "h_requestgameinfo")

register(C2SResend, "c2s_resend")
register(C2SQuit, "c2s_quit")
register(C2SUpdateInput, "c2s_updateinput")

register(S2CKill, "s2c_kill")
register(S2CResending, "s2c_resending")
register(S2CRemoveFood, "s2c_removefood")
register(S2CRemoveSegment, "s2c_removesegment")
register(S2CAddFood, "s2c_addfood")
register(S2CModifySegment, "s2c_modifyfood")


def load_packet(packet: dict):
    try:
        name = packet["name"]
        data = packet["data"]
        packet_class = name_to_packet[name]
        ret = packet_class()
        ret.load(data)
        return ret
    except KeyError:
        raise InvalidPacketError("Malformed packet received")


def save_packet(packet: Packet):
    try:
        name = packet_to_name[packet.__class__]
        data = packet.save()
        return {"name": name, "data": data}
    except KeyError:
        raise InvalidPacketError("Unknown packet")
