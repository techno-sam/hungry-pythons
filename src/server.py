#!/usr/bin/python3

import os
import sys
import math
import time
import random
import threading
import json
import socketserver
import argparse
from colorama import Fore, Style
import pygame
import select
import queue

sys.path.append(os.path.abspath(sys.argv[0]))

import netstring
import network
import profiler

'''thread use:
t = threading.Thread(target=function_for_thread_to_execute)
t.start() # thread ends when target returns
'''

secrets = {}

try:
    jsonfile = os.path.dirname(os.path.abspath(sys.argv[0])) + "/secrets.json"
    data = open(jsonfile).read()
    secrets = json.loads(data)
except FileNotFoundError:
    pass

parser = argparse.ArgumentParser()  # description="")

parser.add_argument("-d", "--debug", action="store_true", help="enable debug mode")
parser.add_argument("-m", "--moving_food", action="store_true", help="make food move")
parser.add_argument("-p", "--port", type=int, help="set port (default 60000)", default=60000)
parser.add_argument("-i", "--host", type=str, help="set host (default localhost)", default="localhost")
parser.add_argument("-c", "--max_clients", type=int, help="set the maximum number of clients (default 50)", default=50)
parser.add_argument("-t", "--timeout", type=int,
                    help="after <timeout> seconds, a client is disconnected if not heard from in the meantime (default 5)",
                    default=5, metavar="SECONDS")
parser.add_argument("-b", "--border", type=int, help="set border radius, beyond it all snakes die (default 1,200)",
                    default=1200, metavar="RADIUS")
parser.add_argument("-s", "--start", type=int, help="start length for snakes (default 10)", default=10,
                    metavar="LENGTH")
parser.add_argument("--speed", type=float, help="set speed multiplier (default 5)", default=5)

args = parser.parse_args()


# (moving_food=False, port=60000, host='localhost', max_clients=50, timeout=5, border=1200, start=10, speed=5)


def debug(fun):  # do debug(lambda:<WHAT WAS ALREADY THERE>)
    do_debug = False
    if args.debug:
        do_debug = True
    if do_debug:
        return fun()


# Start of network setup
HOST, PORT = args.host, args.port
# HOST = "localhost" # only for testing purposes
try:
    computer_name = os.popen("uname -n").read().replace('\n', '')
    if computer_name == 'example_name':  # replace with name of computer you want to set default for
        HOST = "192.168.0.5"  # replace with ip address of computer
except Exception:
    pass  # don't have command uname?

print(f"Serving on {HOST}:{PORT}")

MAX_CONNECTIONS = args.max_clients
TIMEOUT_TIME = args.timeout  # we have to hear from a client every TIMEOUT_TIME seconds, or they are killed
SPEED = args.speed  # we have to hear from a client every TIMEOUT_TIME seconds, or they are killed
BORDER_DISTANCE = args.border  # 10000 #beyond this point, all snakes die
START_LENGTH = args.start
LOAD_DISTANCE = 800  # how far from snakes is food handled.
CHANCE_FORMULA = "1"


class Snake:
    def __init__(self, uuid):
        self.head = None
        self.segments = []
        self.name = "Player"
        self.secret = ""
        self.alive = True
        self.mousedown = False
        self.mouseangle = 0
        self.uuid = uuid
        self.last_update = time.time()
        self.last_message = time.time()
        self.disconnect_time = -1

    def send_update_msg(self):
        head = network.NetSegment(ishead=True, radius=self.head.radius, angle=self.head.angle, pos=self.head.pos, col=self.head.color, idx=0)
        segments = []
        idx = 0
        for seg in self.segments:
            idx += 1
            segments.append(network.NetSegment(ishead=False, radius=seg.radius, angle=seg.angle, pos=seg.pos, col=seg.color, idx=idx))
        send_update(network.S2CModifySnake(uuid=self.uuid, isown=True, name=self.name, alive=self.alive, mousedown=self.mousedown, head=head, segments=segments), uuid=self.uuid)
        send_update(network.S2CModifySnake(uuid=self.uuid, isown=False, name=self.name, alive=self.alive, mousedown=self.mousedown, head=head, segments=segments), blacklist_uuid=self.uuid)


def gen_uuid():
    return hash((random.random(), time.time()))


snakes = {}  # id:Snake()
snakes_lock = threading.Lock()

updates = {}  # uuid:Queue#{timestamp:Packet}
#updates_lock = threading.Lock()


class MyTcpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, address, request_handler_class):
        self.address = address
        self.request_handler_class = request_handler_class
        super().__init__(self.address, self.request_handler_class)


def clean(text):  # function to 'clean' text (aka, try to filter out curse words, remove special characters, etc...)
    return text  # don't feel like actually doing anything yet.


class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        print("Handle called")

        def send_packet(packet: network.Packet):
            netstring.socksend(self.request, json.dumps(network.save_packet(packet)))

        _, msg = netstring.sockget(self.request)
        print(msg)
        loaded = network.load_packet(json.loads(msg))
        if type(loaded) != network.HandshakeInit:
            print(f"Invalid handshake start with type of {type(loaded)}")
            self.request.close()
            return
        uuid = gen_uuid()

        def add_seg_pos(head, segs):
            if len(segs) > 0:
                last_seg = segs[len(segs) - 1]
            else:
                last_seg = head
            '''second_last_seg = segs[len(segs) - 2]
            positive = True
            if last_seg.angle - second_last_seg.angle < 0:
                positive = False
            extra = math.pi / 70  # ((last_seg.angle-second_last_seg.angle)*-1.8)
            if not positive:
                extra = -abs(extra)'''
            extra = 0
            last_seg_rev_angle = last_seg.angle + extra + math.pi
            behind_dist = (last_seg.radius / 2) * 2
            nx = last_seg.pos[0]
            ny = last_seg.pos[1]
            nx += math.cos(last_seg_rev_angle) * behind_dist
            ny += math.sin(last_seg_rev_angle) * behind_dist
            return tuple((nx, ny))  # , last_seg_rev_angle - math.pi

        name, secret = loaded.name, loaded.secret
        accepted = False
        print("Waiting for lock")
        with snakes_lock:
            print("Got it")
            num_snakes = len(snakes)
            if num_snakes < args.max_clients:
                accepted = True
                snake = Snake(uuid)
                snakes[uuid] = snake
                print("Accepted client!")

                spawn_radius = BORDER_DISTANCE - (75*2)
                spawn_pos = (random.randint(-spawn_radius, spawn_radius), random.randint(-spawn_radius, spawn_radius))
                while dist(spawn_pos[0], spawn_pos[1], 0, 0) > spawn_radius:
                    spawn_pos = (random.randint(-spawn_radius, spawn_radius),
                                 random.randint(-spawn_radius, spawn_radius))

                snake.head = Segment(spawn_pos, uuid, gen_uuid(), snake,
                                     color=(random.randint(10, 245), random.randint(10, 245), random.randint(10, 245)),
                                     radius=20, is_head=True)
                for x in range(START_LENGTH):
                    seg_uuid = gen_uuid()
                    snake.segments.append(Segment(add_seg_pos(snake.head, snake.segments), uuid, seg_uuid, snake,
                                                  color=(random.randint(10, 245), random.randint(10, 245),
                                                         random.randint(10, 245)), radius=15, is_head=False))
                snake.send_update_msg()
                # del snake
                print(f"Spawned {START_LENGTH} segments")

        send_packet(network.HandshakeRespond(accepted=accepted, reason="Server is full" if not accepted else ""))

        print("Waiting for game info request")

        _, msg = netstring.sockget(self.request)
        loaded = network.load_packet(json.loads(msg))
        if type(loaded) != network.HandshakeRequestGameInfo:
            self.request.close()
            return
        print("Sending game info")
        send_packet(network.HandshakeGameInfo(border=args.border, max_turn=math.pi / 90))

        _, msg = netstring.sockget(self.request)
        loaded = network.load_packet(json.loads(msg))
        if type(loaded) != network.HandshakeStartGame:
            self.request.close()
            return

        with snakes_lock:
            snakes[uuid].last_message = time.time()

        # request_mutex = threading.Lock()

        # stop_input_flag = threading.Event()

        print("DEBUG POINT")

        '''def client_input_fun(sock):
            while not stop_input_flag.is_set():
                print("Searching for input")
                input_got = False
                with request_mutex:
                    print("Mutex achieved")
                    print(sock)
                    print(sock.fileno())
                    print(f"Time: {time.time()}")
                    read, _, _ = select.select([sock], [], [], 0)  # poll
                    if len(read) == 1:
                        input_got = True
                        _, message = netstring.sockget(sock)
                if input_got:
                    print(f"Got message: {message}")
                    loaded_packet = network.load_packet(json.loads(message))
                    if type(loaded_packet) == network.C2SQuit:
                        kill(uuid, "Quit")
                    elif type(loaded_packet) == network.C2SUpdateInput:
                        with snakes_lock:
                            sn = snakes[uuid]
                            sn.mousedown = loaded_packet.sprinting
                            sn.mouseangle = loaded_packet.angle
                            del sn
                    time.sleep(0.5)
                else:
                    time.sleep(2)

        client_input_thread = threading.Thread(target=client_input_fun, args=(self.request,))'''

        playing = True
        # client_input_thread.start()
        while playing:
            # Get client input
            # print(self.request)
            # print(self.request.fileno())
            # print(f"Time: {time.time()}")
            # print("Polling for input")
            read, _, _ = select.select([self.request], [], [], 0)  # poll
            if len(read) == 1:
                _, message = netstring.sockget(self.request)
                # print(f"Got message: {message}")
                try:
                    loaded_packet = network.load_packet(json.loads(message))
                    if type(loaded_packet) == network.C2SQuit:
                        kill(uuid, "Quit")
                        with snakes_lock:
                            snakes[uuid].disconnect_time = 0
                    elif type(loaded_packet) == network.C2SUpdateInput:
                        with snakes_lock:
                            sn = snakes[uuid]
                            sn.mousedown = loaded_packet.sprinting
                            sn.mouseangle = loaded_packet.angle
                            sn.last_message = time.time()
                            # del sn
                except json.decoder.JSONDecodeError:
                    pass
                    # print(f"Got erroring message {message}")

            # Send all updates
            # print("Waiting to send")
            if True:  # with updates_lock:
                # print("Ready to send")
                my_updates = updates[uuid]
                while not my_updates.empty():
                    # if type(my_updates[timestamp]) != network.S2CAddFood:
                    #    print(f"{Fore.RED}Sending packet: {my_updates[timestamp]}{Style.RESET_ALL}")
                    send_packet(my_updates.get())
                    # if type(my_updates[timestamp]) != network.S2CAddFood:
                    #    print(f"{Fore.RED}Done sending packet: {my_updates[timestamp]}{Style.RESET_ALL}")
                # updates[uuid] = {}

            # CLOSE request if DED
            with snakes_lock:
                snake = snakes[uuid]
                if not snake.alive:
                    #print("OOPS")
                    if snake.disconnect_time == -1:
                        snake.disconnect_time = time.time()+3
                        print(f"Will disconnect {uuid} in 3 seconds")
                    elif time.time() >= snake.disconnect_time:
                        print(f"Disconnected {uuid}")
                        print("Sending updates")
                        my_updates = updates[uuid]
                        while not my_updates.empty():
                            # if type(my_updates[timestamp]) != network.S2CAddFood:
                            #    print(f"{Fore.RED}Sending packet: {my_updates[timestamp]}{Style.RESET_ALL}")
                            send_packet(my_updates.get())
                        print("Updates sent")
                        self.request.close()
                        print("Closed connection")
                        playing = False
                        # stop_input_flag.set()
                        del updates[uuid]
                        del snakes[uuid]
                    else:
                        # print(f"Disconnecting {uuid} in {snake.disconnect_time-time.time(): .2f} seconds")
                        pass
                    #print("DONE OOPSING")
                    #raise Exception("KILLED A SNAKE BAAAAAADDDDDDD")
            # print(f"{Fore.GREEN}network sleeping{Style.RESET_ALL}")
            ####time.sleep(1)
        print("BYYYYEEEEEEEEEEE")


print("hello")
# End of network setup


pygame.init()


######screen = pygame.display.set_mode([1100,900])
# screen = pygame.Surface((7000,7000))

# background = pygame.image.load("/home/USER/bin/images/background_lines_7000x7000.png")

# background = pygame.transform.scale(background,(200,200))
# background = pygame.transform.scale(background,(7000,7000))


class Segment(pygame.sprite.Sprite):
    def __init__(self, pos, snake_uuid, uuid, parent_snake, color=(0, 125, 255), radius=15, is_head=False):
        pygame.sprite.Sprite.__init__(self)
        self.pos = pos
        self.color = color
        self.radius = radius
        self.is_head = is_head
        self.image = pygame.Surface([self.radius * 2, self.radius * 2])
        pygame.draw.ellipse(self.image, self.color, self.image.get_rect())
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.target_pos = pos
        self.max_turn = math.pi / 90  # math.pi/90
        self.angle = 0
        self.spd_mlt = SPEED  # 6.75#2
        self.speed = 0.5 * self.spd_mlt
        self.normal_speed = 0.5 * self.spd_mlt
        if not self.is_head:
            self.normal_speed = self.spd_mlt * 0.7  # 1.5*self.spd_mlt
        self.obey_max_turn = self.is_head
        if not self.is_head:
            self.max_turn = math.pi / 6
        self.goal_angle = 0
        self.snake_uuid = snake_uuid
        self.uuid = uuid
        self.parent_snake = parent_snake

        self.rect.x = self.pos[0] - self.rect.width / 2
        self.rect.y = self.pos[1] - self.rect.height / 2
        self.cache_hash = None
        # self.send_update_msg()

    def gen_cache_hash(self):
        return hash((self.uuid, self.is_head, self.radius, self.angle, self.pos, self.color))

    def send_update_msg(self):
        new_cache_hash = self.gen_cache_hash()
        if self.cache_hash != new_cache_hash:
            '''idx = 0
            if not self.is_head:
                for seg in self.parent_snake.segments:
                    idx += 1
                    if seg.uuid == self.uuid:
                        break
            packet = network.S2CModifySegment(uuid=self.uuid, ishead=self.is_head, isown=False, radius=self.radius,
                                              angle=self.angle, pos=self.pos, col=self.color, idx=idx)
            send_update(packet, blacklist_uuid=self.snake_uuid)
            ownerpacket = network.S2CModifySegment(uuid=self.uuid, ishead=self.is_head, isown=True, radius=self.radius,
                                                   angle=self.angle, pos=self.pos, col=self.color, idx=idx)
            send_update(ownerpacket, uuid=self.snake_uuid)'''
            self.parent_snake.send_update_msg()
            self.cache_hash = new_cache_hash

    def update(self, dtime):
        # circle_centered(screen, color, pos, 50, (0,0))
        if not self.is_head:
            self.goal_angle = math.atan2(self.target_pos[1] - self.pos[1], self.target_pos[0] - self.pos[0])

        def get_dif_angles(source, target):
            source = math.degrees(source)
            target = math.degrees(target)

            def mod(a, n):
                return a - int(a / n) * n

            r = mod(target - source, 360)
            if r > 180:
                r = r - 360
            if -r > 180:
                r = -(-r - 360)
            return math.radians(r)

        max_turn = self.max_turn  ##*dtime*40

        change = get_dif_angles(self.angle, self.goal_angle)  # self.goal_angle-self.angle
        # print(f"{round(change%360)}",end="\r")
        if self.obey_max_turn:
            if change > max_turn:
                change = max_turn
            if change < -self.max_turn:
                change = -max_turn
        self.angle += change

        self.pos = list(self.pos)

        temp_speed = self.speed  ##*dtime*40

        self.pos[0] += math.cos(self.angle) * temp_speed
        self.pos[1] += math.sin(self.angle) * temp_speed

        self.pos = tuple(self.pos)

        self.rect.x = self.pos[0] - self.rect.width / 2
        self.rect.y = self.pos[1] - self.rect.height / 2
        # self.send_update_msg()


class Food(pygame.sprite.Sprite):
    # energy:
    #  1 for normal food
    # 10 for dead snake matter
    def __init__(self, pos, uuid, color=(0, 125, 255), radius=15, energy=1):
        pygame.sprite.Sprite.__init__(self)
        self.pos = pos
        self.uuid = uuid
        self.color = color
        self.radius = radius
        self.energy = energy
        self.image = pygame.Surface([self.radius * 2, self.radius * 2])
        pygame.draw.ellipse(self.image, self.color, self.image.get_rect())
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.cache_hash = None
        self.send_update_msg()

    def gen_cache_hash(self):
        return hash((self.uuid, self.pos, self.color, self.radius, self.energy))

    def send_update_msg(self):
        new_cache_hash = self.gen_cache_hash()
        if self.cache_hash != new_cache_hash:
            send_update(
                network.S2CAddFood(uuid=self.uuid, pos=self.pos, col=self.color, radius=self.radius,
                                   energy=self.energy))
            self.cache_hash = new_cache_hash

    def update(self):
        global snakes, foods, LOAD_DISTANCE

        self.rect.x = self.pos[0] - self.rect.width / 2
        self.rect.y = self.pos[1] - self.rect.height / 2

        out_of_range = True

        with snakes_lock:
            for uuid in snakes:
                snake = snakes[uuid]
                head = snake.head
                distance = dist(self.pos[0], self.pos[1], head.pos[0], head.pos[1])
                if distance <= LOAD_DISTANCE:
                    out_of_range = False
                    break

        if out_of_range:
            # print("deleting...")
            send_update(network.S2CRemoveFood(self.uuid))
            #print(f"{Fore.CYAN}requesting self deletion{Style.RESET_ALL}")
            #del foods[self.uuid]
            return True
        else:
            if self.energy > 1:
                if random.randint(0, 100000) == 0:
                    self.energy -= 1
                    self.send_update_msg()
        if random.randint(0, 20) == 0 and args.moving_food:
            self.pos = list(self.pos)
            rnge = 5
            self.pos[0] += random.randint(-rnge, rnge)
            self.pos[1] += random.randint(-rnge, rnge)
            self.pos = tuple(self.pos)
            self.send_update_msg()


# head = Segment((100,100),is_head=True,color=(200,14,150),radius=20)
# g = pygame.sprite.Group(head)
foods = {}  # uuid:Food


def dist(x1, y1, x2, y2):
    # Pythagorean Theorem: a^2 + b^2 = c^2
    a = x1 - x2
    b = y1 - y2
    c = math.sqrt(math.pow(a, 2) + math.pow(b, 2))
    return c


def collision_circle(x1, y1, r1, x2, y2, r2):
    # find the distance between seg1 and seg2 and tell if they collide
    d = dist(x1, y1, x2, y2)

    if d <= r1 + r2:
        return True


# pygame.mouse.set_pos([100,102])


# def screen_pos_to_game_pos(sp,scr):
#    '''sp - screen pos -> game_pos
#       scr - screen to use'''
#    return ((sp[0]-scr.get_width()//2),(sp[1]-scr.get_height()//2))
"""
def blit_centered(screen, source, dest, origin):
    center = (screen.get_width()/2,screen.get_height()/2)
    screen.blit(source, (round((center[0]-origin[0])+dest[0]), round((center[1]-origin[1])+dest[1])))
    #pygame.draw.circle(screen, (255,255,0), dest, 10)

def circle_centered(screen, color, pos, radius, origin):
    surf = pygame.Surface((radius*2,radius*2))
    surf.set_colorkey((0,0,0))
    if color == (0,0,0):
        surf.set_colorkey((255,255,255))
        surf.fill((255,255,255))
    pygame.draw.circle(surf, color, pos, radius)
    blit_centered(screen, surf, pos, origin)
"""
cramping = 2.3  # 3#4
"""
for x in range(10):
    add_seg(add_seg_pos(),color=(random.randint(10,245),random.randint(0,255),random.randint(0,255)))
mousedown = False"""
sprint_mult = 1.75


def send_update(packet, uuid=None, blacklist_uuid=None):
    # print("Waiting for update lock")
    if True:  # with updates_lock:
        # print("Received update lock")
        if uuid is None:
            for uuid in updates:
                if uuid != blacklist_uuid:
                    if uuid not in updates:
                        updates[uuid] = queue.Queue()
                    updates[uuid].put(packet)
        else:
            if uuid not in updates:
                updates[uuid] = queue.Queue()
            updates[uuid].put(packet)


def gen_killed_msg(killer):
    return random.choice([
        "You stubbed your nose on " + killer + ".",
        "You didn't see " + killer + " ahead of you.",
        "You bumped into " + killer + ".",
        "You thought " + killer + " was a ghost."
    ])


def gen_border_death_msg():
    return random.choice([
        "You ran into the border."
    ])


def kill(uuid, msg, already_locked=False):
    global snakes
    #print(f"Killing snake {uuid} with msg: {msg}")
    #print("Waiting for lock to kill")
    if not already_locked:
        snakes_lock.acquire()
    send_kill = False
    if snakes[uuid].alive:
        # Needs to be locked
        #print("Kill lock received")
        snakes[uuid].alive = False
        snakes[uuid].segments = []
        #print("Kill sending update")
        snakes[uuid].send_update_msg()
        #print("Kill sent update")
        send_kill = True
    if not already_locked:
        snakes_lock.release()
    # No locks needed
    if send_kill:
        print("Done updating snake, sending S2CKill")
        send_update(network.S2CKill(msg=msg))
        print("S2CKill sent")
    # remove this client from active_connections
    # debug(lambda: print(
    #    f"killing ip: {snake['ip']}, uuid: {snake['uuid']}, killer: {killer_name}, name: {snake['name']}"))


DEAD_MASS = 3
'''iters = round((1000/1440000)*(BORDER_DISTANCE**2))
for x in range(iters):
    if True:#len(foods)<500 and random.randint(0,200)==0:
        for i in range(random.randint(1,3)):
            rnge = BORDER_DISTANCE#1200
            x = 0 + random.randint(-rnge,rnge)
            y = 0 + random.randint(-rnge,rnge)
            if abs(x-0)<40:
                x += random.choice([-40,40])
            if abs(y-0)<40:
                y += random.choice([-40,40])
            red = random.randint(10,245)
            green = random.randint(10,245)
            blue = random.randint(10,245)
            if dist(x,y,0,0)<BORDER_DISTANCE:
                if random.randint(0,100)!=0:
                    foods.append(Food((x,y), color=(red,green,blue), radius=random.randint(5,8), energy=1))
                else:
                    foods.append(Food((x,y), color=(red,green,blue), radius=random.randint(13,15), energy=DEAD_MASS))'''

print("Defining update snake")


def update_snake(uuid, dtime_override=None):
    global snakes, foods
    with snakes_lock:
        # print("Lock achieved")
        snake = snakes[uuid]
        head = snake.head
        segs = snake.segments
        mousedown = snake.mousedown
        angle = snake.mouseangle
        uuid = snake.uuid

        def add_seg_pos():
            if len(segs) > 0:
                last_seg = segs[len(segs) - 1]
            else:
                last_seg = head
            second_last_seg = segs[len(segs) - 2]
            positive = True
            if last_seg.angle - second_last_seg.angle < 0:
                positive = False
            extra = math.pi / 70  # ((last_seg.angle-second_last_seg.angle)*-1.8)
            if not positive:
                extra = -abs(extra)
            last_seg_rev_angle = last_seg.angle + extra + math.pi
            behind_dist = (last_seg.radius / 2) * 2
            nx = last_seg.pos[0]
            ny = last_seg.pos[1]
            nx += math.cos(last_seg_rev_angle) * behind_dist
            ny += math.sin(last_seg_rev_angle) * behind_dist
            return (nx, ny), last_seg_rev_angle - math.pi

        def add_seg(pos, snake_uuid, color=(0, 125, 255), radius=15, angle=0):
            # print("Creating segment")
            newseg = Segment(pos, snake_uuid, gen_uuid(), snake, color=color, radius=radius)
            newseg.angle = angle
            # g.add(newseg)
            segs.append(newseg)

        def remove_seg():
            if len(segs) > 0:
                seg = segs.pop()
                seg.kill()
                #send_update(network.S2CRemoveSegment(uuid=seg.uuid))
                snake.send_update_msg()

        # print("Checkpoint 1")
        # let's start by seeing if this snake is ded
        for enemy_uuid in snakes:
            if enemy_uuid != uuid:
                enemy = snakes[enemy_uuid]
                for seg in enemy.segments:
                    if collision_circle(seg.rect.x, seg.rect.y, seg.radius, head.rect.x, head.rect.y, head.radius):
                        print(f"{Fore.RED}Killing snake from bumping into snake{Style.RESET_ALL}")
                        kill(uuid, gen_killed_msg(enemy.name), True)
                        # add mass
                        for ded in segs:
                            tmp_uuid = gen_uuid()
                            print(f"{Fore.BLUE}Adding food from dead snake{Style.RESET_ALL}")
                            foods[tmp_uuid] = Food((ded.rect.x, ded.rect.y),
                                                   tmp_uuid,
                                                   color=ded.color,
                                                   radius=random.randint(13, 15),
                                                   energy=DEAD_MASS)
                        return None
        if dist(head.pos[0], head.pos[1], 0, 0) > BORDER_DISTANCE:
            ####print(f"{Fore.RED}Snake killed OOF{Style.RESET_ALL}")
            kill(snake.uuid, gen_border_death_msg(), True)
            return None
        # print("Checkpoint 2")
        # screen.fill((0,0,0))
        # mp = None
        # mp = pygame.mouse.get_pos()
        # handle sprinting
        sprinting = mousedown and (len(segs) > 10)
        if sprinting and random.randint(0, 275) == 0:
            last_seg = segs[len(segs) - 1]
            tmp_uuid = gen_uuid()
            foods[tmp_uuid] = Food((last_seg.rect.x, last_seg.rect.y), uuid, color=last_seg.color,
                                   radius=random.randint(5, 8), energy=1)
            remove_seg()

        # mp = ((screen.get_width()//2)-mp[0],(screen.get_height()//2)-mp[1])
        # print(mp)
        # handle head
        # head.target_pos = mp
        head.goal_angle = angle  # math.atan2(mp[1]-screen.get_height()/2,mp[0]-screen.get_width()/2)
        head.speed = head.normal_speed
        if sprinting:
            head.speed = head.normal_speed * sprint_mult
        # if collision_circle(mp[0],mp[1],2,head.pos[0],head.pos[1],head.radius):
        #    head.speed = 0
        # print("Checkpoint 3")
        # handle segments
        for i in range(len(segs)):
            if i == 0:
                segs[i].target_pos = head.pos
                segs[i].speed = segs[i].normal_speed
                if sprinting:
                    segs[i].speed = segs[i].normal_speed * sprint_mult
                #                                                 segs[i].radius/cramping
                if collision_circle(segs[i].pos[0], segs[i].pos[1], segs[i].radius / cramping, head.pos[0], head.pos[1],
                                    head.radius / cramping):
                    segs[i].speed = 0
            else:
                segs[i].target_pos = segs[i - 1].pos
                segs[i].speed = segs[i].normal_speed
                if sprinting:
                    segs[i].speed = segs[i].normal_speed * sprint_mult
                if collision_circle(segs[i].pos[0], segs[i].pos[1], segs[i].radius / cramping, segs[i - 1].pos[0],
                                    segs[i - 1].pos[1], segs[i - 1].radius / cramping):
                    segs[i].speed = 0

            # print(s.pos)
        # print('Checkpoint 3.5')
        # add some food
        foods_in_range = 0
        for f_uuid in foods:
            f = foods[f_uuid]
            if dist(f.pos[0], f.pos[1], head.pos[0], head.pos[1]) < (LOAD_DISTANCE * (7 / 8)):
                foods_in_range += 1
        should_add_food = (foods_in_range < round((1000 / 1440000) * ((LOAD_DISTANCE * (7 / 8)) ** 2)))
        while should_add_food:
            foods_in_range = 0
            for f_uuid in foods:
                f = foods[f_uuid]
                if dist(f.pos[0], f.pos[1], head.pos[0], head.pos[1]) < (LOAD_DISTANCE * (7 / 8)):
                    foods_in_range += 1
            should_add_food = (foods_in_range < round((1000 / 1440000) * ((LOAD_DISTANCE * (7 / 8)) ** 2)))
            # print(
            #    f"Foods_in_range: {foods_in_range}, Total needed: {round((1000 / 1440000) * ((LOAD_DISTANCE * (7 / 8)) ** 2))}")
            if True:  # should_add_food and random.randint(0,200)==0:
                for i in range(random.randint(0, 3)):
                    rnge = round(LOAD_DISTANCE * (7 / 8))  # 1200
                    x = head.rect.x + random.randint(-rnge, rnge)
                    y = head.rect.y + random.randint(-rnge, rnge)
                    if abs(x - head.rect.x) < 40:
                        x += random.choice([-40, 40])
                    if abs(y - head.rect.y) < 40:
                        y += random.choice([-40, 40])
                    red = random.randint(10, 245)
                    green = random.randint(10, 245)
                    blue = random.randint(10, 245)
                    if dist(x, y, 0, 0) < BORDER_DISTANCE:
                        if random.randint(0, 100) != 0:
                            tmp_uuid = gen_uuid()
                            foods[tmp_uuid] = Food((x, y), tmp_uuid, color=(red, green, blue),
                                                   radius=random.randint(5, 8), energy=1)
                        else:
                            tmp_uuid = gen_uuid()
                            foods[tmp_uuid] = Food((x, y), tmp_uuid, color=(red, green, blue),
                                                   radius=random.randint(13, 15), energy=DEAD_MASS)
        # print("Checkpoint 4")
        """
        if len(foods)<2000 and random.randint(0,200)==0:
            for i in range(random.randint(0,3)):
                rnge = BORDER_DISTANCE#1200
                x = head.rect.x + random.randint(-rnge,rnge)
                y = head.rect.y + random.randint(-rnge,rnge)
                if abs(x-head.rect.x)<40:
                    x += random.choice([-40,40])
                if abs(y-head.rect.y)<40:
                    y += random.choice([-40,40])
                red = random.randint(10,245)
                green = random.randint(10,245)
                blue = random.randint(10,245)
                if dist(x,y,0,0)<BORDER_DISTANCE:
                    if random.randint(0,100)!=0:
                        foods.append(Food((x,y), color=(red,green,blue), radius=random.randint(5,8), energy=1))
                    else:
                        foods.append(Food((x,y), color=(red,green,blue), radius=random.randint(13,15), energy=DEAD_MASS))
        """
        # deal with food
        # eat food
        search_rad = 15
        foods_to_remove = []
        for food_uuid in foods:
            # print(f"trying to eat food with uuid {food_uuid}")
            food = foods[food_uuid]
            if collision_circle(food.pos[0], food.pos[1], food.radius, head.pos[0], head.pos[1], head.radius):
                # print(f"{Fore.MAGENTA}colliding with food{Style.RESET_ALL}")
                # print(f"collision_circle({food.rect.x}, {food.rect.y}, {food.radius}, {head.rect.x}, {head.rect.y}, {head.radius})")
                # raise Exception("just need to end")
                # quit()
                if food.energy > 0:
                    for x in range(food.energy):
                        chance = round(eval(CHANCE_FORMULA.replace("SL", str(len(segs)))))
                        if chance < 1:
                            chance = 1
                        if random.randint(1, chance) == 1:
                            info = add_seg_pos()
                            pos_to_add = info[0]
                            # print(f"Yummy, adding segment")
                            add_seg(pos_to_add, uuid, color=food.color, angle=info[1])
                            # print(f"Yummy, added segment")
                else:
                    for x in range(-food.energy):
                        remove_seg()

                foods_to_remove.append(food_uuid)
                send_update(network.S2CRemoveFood(food_uuid))
            # print(f"Done trying food with uuid {food_uuid}")
        for food_uuid in foods_to_remove:
            # print(f"{Fore.YELLOW}Deleting food with uuid {food_uuid}{Style.RESET_ALL}")
            del foods[food_uuid]
        # print("checkpoint 5")
        """#draw food
        for food in foods:
            food.update()
            blit_centered(screen, food.image, (food.rect.x,food.rect.y), (head.rect.x,head.rect.y))"""
        # update snake
        dtime = time.time() - snake.last_update
        if dtime_override != None:
            dtime = dtime_override
        # print(f"head angle: {head.angle}, goal_angle: {head.goal_angle}, speed: {head.speed}")
        # print(f"pre head data: {head.pos}")
        head.update(dtime)
        # print("Checkpoint 5.1")
        # print(f"post head data: {head.pos}")
        # quit()
        send_distance = 775
        cx, cy = head.pos[0], head.pos[1]
        for seg in segs:
            # seg = segs[seg_uuid]
            seg.update(dtime)
        # print("CHeckpoint 6")
        '''seg_mess = []
        for seg in segs:
            seg_mess.append([seg.pos, seg.color, seg.radius, seg.angle])
        message = {'mode': 1, 'head': [head.pos, head.color, head.radius, head.angle], 'segs': seg_mess,
                   'enemy_segs': [],
                   'food': []}
        for s in snakes:
            if s['uuid'] != snake['uuid']:
                enemy_seg = s['head']
                if dist(enemy_seg.pos[0], enemy_seg.pos[1], cx, cy) <= send_distance:
                    message['enemy_segs'].append(
                        [enemy_seg.pos, enemy_seg.color, enemy_seg.radius, enemy_seg.angle, True])
                for enemy_seg in s['segs']:
                    if dist(enemy_seg.pos[0], enemy_seg.pos[1], cx, cy) <= send_distance:
                        message['enemy_segs'].append(
                            [enemy_seg.pos, enemy_seg.color, enemy_seg.radius, enemy_seg.angle])
        for f in foods:
            f.update()
        for f in foods:
            if dist(f.pos[0], f.pos[1], cx, cy) <= send_distance:
                message['food'].append([f.pos, f.color, f.radius, f.energy])
        send_update(snake['ip'], snake['uuid'], message)'''
        snake.last_update = time.time()
        snake.send_update_msg()
        # print("Lock should release soon")
    # print("Lock released")


def run_server(instance):
    print(instance)
    print("Started server", instance)
    print("More done")
    print("Yet more stuff")
    print("Awesome")
    while True:
        # print("C")
        try:
            instance.handle_request()
        except ValueError:
            pass  # print("OOOOOOOOOOOOOOOOOOOOOOOOPPPPPPSSSSSSSSSSSSSSSSSSS")
        # print("Pausing...")
        time.sleep(5)
        # print("Done pausing...")
        # print("D")
    print("Ended server")


if __name__ == "__main__":
    # global HOST, PORT

    # Create the server, binding to localhost on port 9999
    with MyTcpServer((HOST, PORT), MyTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        # server.serve_forever()
        # timeoutThread.start()
        serverThread = threading.Thread(target=run_server, args=(server,))
        serverThread.start()
        print("A")
        # server.serve_forever()
        print("B")
        print("LKJLKJL")
        time.sleep(5)
        print("END SLEEPING")
        last_time = time.time()
        kg = True
        while kg:
            # print("TRYING to do stuff")
            try:
                # print(dtime)
                # print(f"Number of snakes: {len(snakes)}\nNumber of foods: {len(foods)}")
                for sn_uuid in snakes:
                    # print(f"Updating snake uuid {sn_uuid}")
                    update_snake(sn_uuid, 1 / 40)
                    # print(f"Done updating snake uuid {sn_uuid}")
                fuuid_to_remove = []
                for f_uuid in foods:
                    #print(f"Updating food uuid {f_uuid}")
                    if foods[f_uuid].update():
                        fuuid_to_remove.append(f_uuid)
                    #print(f"Done updating food uuid {f_uuid}")
                    #print("More data")
                    #print("Does this get run?")
                    #print("OK..........")
                    #print("Weird stuff happening")#'''
                for f_uuid in fuuid_to_remove:
                    del foods[f_uuid]
                del fuuid_to_remove
                # print("Outside of for loop...")
                # print(f"After Number of snakes: {len(snakes)}\nAfter Number of foods: {len(foods)}")
            except KeyboardInterrupt:
                kg = False
            now = time.time()
            diff = now - last_time
            if diff < (1 / 20):
                time.sleep((1 / 20) - diff)
            last_time = time.time()
            # print("Loop done, ready for next")
            # print("decoded: ", decoded)
            # if decoded=='shutdown':
            #    kg = False
        # print("hello")
        print("Bye bye")
        server.shutdown()
        DO_THREADS = False
        pygame.quit()

"""
Mainloop design:
Receive messages, put in buffer.
Loop through messages,
    if handshake, respond
    elif main communication and already shook hands, update certain snake with update_snake()
    elif goodbye, remove from shook_hands table
    else, send death message with ('killer':'Invalid communication')
Loop through shook_hands table,
    if no message from that snake, add time to timeout table
    if timed out, send death message ('killer':'Timeout'), and remove snake from shook_hands table
"""

"""
Client/Server Communication Protocol follows.
If a client doesn't hear from a server for 5 seconds, it sends a goodbye message, and disconnects
If a server doesn't hear from a client for 5 seconds, it sends a death message (with 'killer':'Timeout') and disconnects
"""

"""
Handshake:
  Client => Server:
    {'mode':0,'name':string (name player wants to be known as)} # optionally, a client can also add {'secret':str(a special authentication secret for developers, etc)}
  Server => Client:
    {'mode':0, 'accepted':boolean} # if accepted, server will next send the first Server => Client message in the Main Communication Protocol, otherwise, server will ignore client for a few minutes
"""

"""
Main Communication Protocol:
  Client => Server:
    {'mode':1,'angle':float (radians), 'sprinting':boolean}
  Server => Client:
    Section of message containing player info
    {'mode':1,'head':[tuple (position of player's head), color, size], 'segs':[ [position_of_segment, color, size], [position_of_segment2, color2, size2], etc..]}
    Section of message containing enemy info (is appended on to player info section) (use player_info_msg.update(enemy_info_msg))
    {'enemy_segs':[ [position_of_segment, color, size], [position_of_segment2, color2, size2], etc..]}
    Section of message containing food info (use format of enemy info section, except with 'food' key instead of 'enemy_segs' key
"""

"""
Goodbye (only Client => Server is needed, or only Server => Client, there is nno reply):
  Client => Server:
    {'mode':2} #mode:2 is all that is needed to declare leaving
  Server => Client:
    {'mode':2} #optionally, {'killer':str(name_of_killer)} can also be added (if the border is the killer, 'the Border of Life and Death' will be the name)
"""
