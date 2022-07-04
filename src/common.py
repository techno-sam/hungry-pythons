import math

import pygase
import typing


class Serializable:
    def load(self, data: list) -> None:
        """Load object with data received from GameState"""
        pass

    def save(self) -> list:
        """Load object with data received from GameState"""
        return []

    @staticmethod
    def blank():
        return Serializable()


degrees = typing.NewType("degrees", float)


class Segment(Serializable):
    def __init__(self, radius: float, angle: degrees,
                 pos: typing.Tuple[int, int], col: typing.Tuple[int, int, int],
                 uuid: str):
        self.radius = radius
        self.angle = angle
        self.pos = pos
        self.col = col
        self.uuid = uuid

    def load(self, data: list) -> None:
        super().load(data)
        self.radius = data.pop(0)
        self.angle = data.pop(0)
        self.pos = data.pop(0)
        self.col = data.pop(0)
        self.uuid = data.pop(0)

    def save(self) -> list:
        my_data = [self.radius, self.angle, self.pos, self.col]
        return super().save() + my_data

    @staticmethod
    def blank():
        return Segment(0, 0, (0, 0), (0, 0, 0), "")


class Snake(Serializable):
    def __init__(self, uuid: str, name: str, alive: bool, head: Segment, segments: typing.List[Segment]):
        self.uuid = uuid
        self.name = name
        self.alive = alive
        self.head = head
        self.segments = segments

    def load(self, data: list) -> None:
        super().load(data)
        self.uuid = data.pop(0)
        self.name = data.pop(0)
        self.alive = data.pop(0)

        head_data = data.pop(0)
        if self.head is None:
            self.head = Segment.blank()
        self.head.load(head_data)

        segment_data = data.pop(0)
        for i in range(len(segment_data)):
            if i >= len(self.segments):
                self.segments.append(Segment.blank())
            self.segments[0].load(segment_data[i])

    def save(self) -> list:
        segment_data = []
        for segment in self.segments:
            segment_data.append(segment.save())
        my_data = [self.uuid, self.name, self.alive, self.head.save(), segment_data]
        return super().save() + my_data

    @staticmethod
    def blank():
        return Snake("", "uninitialized", True, Segment.blank(), [])


class GameInfo(Serializable):
    def __init__(self, border: int, max_turn: float):
        """
        max_turn is in radians
        border is a radius
        """
        self.border = border
        self.max_turn = max_turn

    def load(self, data: list) -> None:
        super().load(data)
        self.border = data.pop(0)
        self.max_turn = data.pop(0)

    def save(self) -> list:
        my_data = [self.border, self.max_turn]
        return super().save() + my_data

    @staticmethod
    def blank():
        return GameInfo(1200, math.pi/90)


