import random
import time
import typing

from pygase import GameState, Backend
import math


def gen_uuid():
    chars = "qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890"
    out = ""
    for _ in range(20):
        out += random.choice(chars)
    return out


def rand_color():
    return random.randint(10, 245), random.randint(10, 245), random.randint(10, 245)


def create_segment(radius: float, angle: float, pos: typing.Tuple[int, int], col: typing.Tuple[int, int, int],
                   uuid: str):
    """Angle is in radians"""
    return {"radius": radius, "angle": angle, "pos": pos, "col": col, "uuid": uuid}


def create_body(head_pos: typing.Tuple[int, int], head_radius: float, head_angle: float, length: int):
    def add_seg_pos(prev_pos, prev_angle, prev_radius):
        extra = 0
        last_seg_rev_angle = prev_angle + extra + math.pi
        behind_dist = (prev_radius / 2) * 2
        nx = prev_pos[0]
        ny = prev_pos[1]
        nx += math.cos(last_seg_rev_angle) * behind_dist
        ny += math.sin(last_seg_rev_angle) * behind_dist
        return tuple((nx, ny))  # , last_seg_rev_angle - math.pi

    segments = []
    for i in range(length):
        if i == 0:
            segments.append(create_segment(15, 0, add_seg_pos(head_pos, head_angle, head_radius),
                                           rand_color(), gen_uuid()))
        else:
            segments.append(create_segment(15, 0,
                                           add_seg_pos(segments[i - 1]["pos"],
                                                       segments[i - 1]["angle"],
                                                       segments[i - 1]["radius"]),
                                           rand_color(), gen_uuid()))
    return segments


initial_game_state = GameState(
    snakes={},  # player_id: Snake
    gameinfo={"border": 1200, "max_turn": math.pi / 90, "time": 0}
)

prev_time = time.perf_counter()


def time_step(game_state, super_dt):
    global prev_time
    now = time.perf_counter()
    dt = now - prev_time
    prev_time = now
    out = {"snakes": {}, "gameinfo": game_state.gameinfo}
    for player_id, snake in game_state.snakes.items():
        # out["snakes"][player_id] = snake
        pos = snake["head"]["pos"]

        speed = 3  # pixels per second
        vx = math.cos(snake["head"]["angle"]) * speed# * dt
        vy = math.sin(snake["head"]["angle"]) * speed# * dt
        new_pos = (pos[0] + vx, pos[1] - vy)
        # print(f"dt: {dt}, vel: ({vx}, {vy}), new_pos: {new_pos}")

        # out["snakes"][player_id]["head"]["pos"] = new_pos
        return {"snakes": {player_id: {"head": {"pos": new_pos}}},
                "gameinfo": {"time": game_state.gameinfo["time"] + dt}}
    out["gameinfo"]["time"] += dt
    # time.sleep(0.00005)
    # print(out)
    return out


# "UPDATE_INPUT" event handler
def on_update_input(player_id, angle: float, sprinting: bool, **kwargs):
    return {"snakes": {player_id: {"sprinting": sprinting, "head": {"angle": angle}}}}


backend = Backend(initial_game_state, time_step, event_handlers={"UPDATE_INPUT": on_update_input})


# "JOIN" event handler
def on_join(player_name, game_state, client_address, **kwargs):
    print(f"{player_name} joined.")
    player_id = len(game_state.snakes)
    backend.server.dispatch_event("PLAYER_CREATED", player_id, target_client=client_address)
    spawn_radius = min(game_state.gameinfo["border"] - 50, int(game_state.gameinfo["border"] * 0.8))
    spawn_angle = math.radians(random.randint(0, 360))
    spawn_distance = random.randint(0, spawn_radius)
    spawn_pos = (int(math.cos(spawn_angle) * spawn_distance), int(math.sin(spawn_angle) * spawn_distance))
    ret = {"snakes": {
        player_id: {
            "name": player_name,
            "uuid": gen_uuid(),
            "alive": True,
            "sprinting": False,
            "head": create_segment(20, 0, spawn_pos, rand_color(), gen_uuid()),
            "segments": create_body(spawn_pos, 20, 0, 10)
        }
    }}
    print(f"Joining with: {ret}")
    return ret


# "INIT_DATA" event handler
def on_init_data(player_id, game_state, client_address, **kwargs):
    print(f"Init data for client {player_id}")
    if player_id in game_state.snakes:
        print(f"Sending snake: {game_state.snakes[player_id]}")
    else:
        print("Player doesn't have a snake yet. Why?")
    backend.server.dispatch_event("START", target_client=client_address)
    return {"snakes": game_state.snakes, "gameinfo": game_state.gameinfo}


backend.game_state_machine.register_event_handler("JOIN", on_join)
backend.game_state_machine.register_event_handler("INIT_DATA", on_init_data)

if __name__ == "__main__":
    print("Starting server...")
    backend.run(hostname="localhost", port=9999)
