import math
import typing

import pygame
import time
from pygase import Client


def blit_centered(surf: pygame.Surface, source: pygame.Surface,
                  dst: typing.Tuple[int, int], origin_pos: typing.Tuple[int, int]):
    middle = (surf.get_width() / 2, surf.get_height() / 2)
    surf.blit(source, (round((middle[0] - origin_pos[0]) + dst[0]), round((middle[1] - origin_pos[1]) + dst[1])))
    # pygame.draw.circle(screen, (255,255,0), dest, 10)


def circle_centered(surf: pygame.Surface, col: typing.Tuple[int, int, int], center_pos: typing.Tuple[int, int],
                    radius: float, origin_pos: typing.Tuple[int, int]):
    tmp_surf = pygame.Surface((radius * 2, radius * 2))
    tmp_surf.set_colorkey((0, 0, 0))
    if col == (0, 0, 0):
        tmp_surf.set_colorkey((255, 255, 255))
        tmp_surf.fill((255, 255, 255))
    pygame.draw.circle(tmp_surf, col, (int(radius), int(radius)), radius)
    blit_centered(surf, tmp_surf, (center_pos[0] - int(radius), center_pos[1] - int(radius)), origin_pos)


def waiting_indicator():
    pieces = list("-/-\\|/")
    num_pieces = len(pieces)
    index = int(time.time() * 2.5) % num_pieces
    print("\r" + pieces[index], end="")


class SnakeClient(Client):
    def __init__(self):
        super().__init__()
        self.player_id = None
        self.started = False
        self.register_event_handler("PLAYER_CREATED", self.on_player_created)
        self.register_event_handler("START", self.start)

    def on_player_created(self, player_id: int):  # noqa
        self.player_id = player_id
        self.dispatch_event("INIT_DATA", self.player_id)

    def start(self):
        self.started = True


client = SnakeClient()

if __name__ == "__main__":
    client.connect_in_thread(hostname="localhost", port=9999)
    client.dispatch_event("JOIN", input("Player name: "))
    while client.player_id is None:
        pass
    print()
    print(client.player_id)
    while not client.started:
        waiting_indicator()
        time.sleep(0.5)
    print()
    with client.access_game_state() as game_state:
        print(f"Game started with snake {game_state.snakes[client.player_id]}")

    keys_pressed = set()
    mousedown = False
    move_refresh = False
    clock = pygame.time.Clock()
    pygame.init()

    screen_width = 640
    screen_height = 420
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.DOUBLEBUF)

    kg = True
    start_time = None
    while kg:
        dt = clock.tick(50)
        screen.fill((255, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                kg = False
            if event.type == pygame.KEYDOWN:
                keys_pressed.add(event.key)
            if event.type == pygame.KEYUP:
                keys_pressed.remove(event.key)
            if event.type == pygame.MOUSEBUTTONDOWN:
                mousedown = True
                move_refresh = True
            if event.type == pygame.MOUSEBUTTONUP:
                mousedown = False
                move_refresh = True
            if event.type == pygame.MOUSEMOTION:
                move_refresh = True

        with client.access_game_state() as game_state:
            if start_time is None:
                start_time = time.time() - game_state.gameinfo['time']
            server_time = game_state.gameinfo['time']
            client_time = time.time()-start_time
            pygame.display.set_caption(f"Server_Time: {round(server_time, 2)}, Client_Time: {round(client_time, 2)}, Diff: {round(server_time-client_time, 4)}", "")
            if move_refresh:
                mp = pygame.mouse.get_pos()
                angle = math.atan2(mp[1] - screen.get_height() / 2, mp[0] - screen.get_width() / 2)
                client.dispatch_event(
                    event_type="UPDATE_INPUT",
                    player_id=client.player_id,
                    angle=angle,
                    sprinting=mousedown
                )
            # print(game_state.snakes)
            my_x, my_y = [int(coord) for coord in game_state.snakes[client.player_id]["head"]["pos"]]
            ##########
            # BORDER #
            ##########
            center = (screen.get_width() / 2, screen.get_height() / 2)
            dest = (0, 0)
            origin = (my_x, my_y)
            temp_pos = (round((center[0] - origin[0]) + dest[0]), round((center[1] - origin[1]) + dest[1]))
            pygame.draw.circle(screen, (0, 0, 0), temp_pos, game_state.gameinfo["border"])

            ##########
            # Snakes #
            ##########
            for player_id, snake in game_state.snakes.items():
                if player_id == client.player_id:
                    color = (50, 255, 50)
                else:
                    color = (50, 50, 255)
                circle_centered(screen, snake["head"]["col"], (my_x, my_y), snake["head"]["radius"], origin)
                for seg in snake["segments"]:
                    x, y = [int(coord) for coord in seg["pos"]]
                    circle_centered(screen, seg["col"], (x, y), seg["radius"], origin)
            pygame.display.flip()

    pygame.quit()
    client.disconnect(shutdown_server=True)
