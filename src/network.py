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
        if name in packet.keys():
            if type(packet[name]) != kwargs[name]:
                raise IncompletePacketWarning(f"Invalid type for {name} Packet: {packet}, expected: {kwargs}")
        else:
            raise IncompletePacketWarning("Missing attribute")


name_to_packet = {}
packet_to_name = {}


def register(packet, name):
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

        # if type(self.name) != str or type(self.secret) != str:
        #    raise InvalidPacketError(
        #        f"Bad argument types: name<{type(self.name)}> should be str, secret<{type(self.secret)}> should be str")

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

        # if type(self.accepted) != bool or type(self.reason) != str:
        #    raise InvalidPacketError("Bad types for HandshakeRespond")

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

        # if type(self.border) != int or type(self.max_turn) != float:
        #    raise InvalidPacketError("Bad types for HandshakeGameInfo")

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

        # if type(self.angle) != float or type(self.sprinting) != bool:
        #    raise InvalidPacketError("Bad types for C2SUpdateInput")

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

class NetSegment:

    def __init__(self, ishead=None, radius=None, angle=None, pos=None, col=None, idx=None):
        self.ishead = ishead
        self.radius = radius
        self.angle = angle
        self.pos = pos
        self.col = col
        self.idx = idx

    def save(self):
        return {
            "ishead": self.ishead,
            "radius": self.radius,
            "angle": self.angle,
            "pos": self.pos,
            "col": self.col,
            "idx": self.idx
        }

    def load(self, packet: dict):
        self.ishead = packet.get("ishead", False)
        self.radius = packet.get("radius", 10)
        self.angle = float(packet.get("angle", 0.0))
        self.pos = tuple(packet.get("pos", (0, 0)))
        self.col = tuple(packet.get("col", (255, 0, 255)))
        self.idx = packet.get("idx", 0)

        packet["angle"] = float(packet["angle"])
        packet["pos"] = tuple(packet["pos"])
        packet["col"] = tuple(packet["col"])

        verify_packet(packet, ishead=bool, radius=int, angle=float, pos=tuple, col=tuple, idx=int)

        return self


class S2CModifySnake(Packet):
    C2S = False
    S2C = True

    def __init__(self, uuid="ERROR", isown=False, name="Player", alive=True, mousedown=False, head=None, segments=None):
        super().__init__()
        if segments is None:
            segments = []
        self.uuid = uuid
        self.isown = isown
        self.name = name
        self.alive = alive
        self.mousedown = mousedown
        self.head = head
        self.segments = segments

        # if type(self.uuid) != str:
        #    raise InvalidPacketError("Bad types for S2CRemoveSegment")

    def save(self):
        serialized_head = self.head.save()
        serialized_segments = []
        for seg in self.segments:
            serialized_segments.append(seg.save())
        return {
            "uuid": self.uuid,
            "isown": self.isown,
            "name": self.name,
            "alive": self.alive,
            "mousedown": self.mousedown,
            "head": serialized_head,
            "segments": serialized_segments
        }

    def load(self, packet: dict):
        self.uuid = str(packet.get("uuid", "ERROR"))
        self.isown = packet.get("isown", False)
        self.name = packet.get("name", "Player")
        self.alive = packet.get("alive", True)
        self.mousedown = packet.get("mousedown", False)
        head_dat = packet.get("head", None)
        self.head = NetSegment()
        self.head.load(head_dat)
        serialized_segments = packet.get("segments", [])
        self.segments = []
        packet["uuid"] = self.uuid
        packet["head"] = self.head
        for seg_dat in serialized_segments:
            seg = NetSegment()
            seg.load(seg_dat)
            self.segments.append(seg)

        verify_packet(packet, uuid=str, isown=bool, name=str, alive=bool, mousedown=bool, head=NetSegment, segments=list)

        return self


class S2CRemoveSnake(Packet):
    C2S = False
    S2C = True

    def __init__(self, uuid="ERROR"):
        super().__init__()
        self.uuid = uuid

        # if type(self.uuid) != str:
        #    raise InvalidPacketError("Bad types for S2CRemoveSegment")

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

        packet["uuid"] = str(packet["uuid"])
        packet["pos"] = tuple(packet["pos"])
        packet["col"] = tuple(packet["col"])

        verify_packet(packet, uuid=str, pos=tuple, col=tuple, radius=int, energy=int)

        return self


class S2CRemoveFood(Packet):
    C2S = False
    S2C = True

    def __init__(self, uuid="ERROR"):
        super().__init__()
        self.uuid = uuid

        # if type(self.uuid) != str:
        #    raise InvalidPacketError("Bad types for S2CRemoveFood")

    def save(self):
        return {"uuid": self.uuid}

    def load(self, packet: dict):
        self.uuid = packet.get("uuid", "ERROR")

        packet["uuid"] = str(packet["uuid"])

        verify_packet(packet, uuid=str)

        return self


class S2CKill(Packet):
    C2S = False
    S2C = True

    def __init__(self, msg="You died."):
        super().__init__()
        self.msg = msg

        # if type(self.msg) != str:
        #    raise InvalidPacketError("Bad types for S2CKill")

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
register(S2CRemoveSnake, "s2c_removesnake")
register(S2CAddFood, "s2c_addfood")
register(S2CModifySnake, "s2c_modifysnake")


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
