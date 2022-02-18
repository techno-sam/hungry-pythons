#!/usr/bin/python3

import pygame
import sys
import os
import math
import queue
import time
import random
import threading
import netstring
import network
import json
import socket
import colorsys
from colorama import Fore, Style
import argparse

"""
NOTES:
Reimplement snake length display
"""


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    default = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    base_path = getattr(sys, '_MEIPASS', default)
    # print(base_path)
    return os.path.join(base_path, relative_path)


'''thread use:
t = threading.Thread(target=function_for_thread_to_execute)
t.start() # thread ends when target returns
'''

"""
print("Options:\n\t--debug - enable debug mode")
print("\t--render_simple - enable simple rendering")
print("\t--port <PORT> - set port (default 60000)")
print("\t--host <IP> - set host (default localhost)")
print("\t--view_dist <DISTANCE> - set view radius (default 400)")
print("\t--secret <STRING> - set a secret to send to the server (not required, can provide advantages)")
"""

parser = argparse.ArgumentParser()

parser.add_argument("-d", "--debug", action="store_true", help="enable debug mode")
parser.add_argument("-r", "--render_simple", action="store_true", help="enable simple rendering")
parser.add_argument("-p", "--port", type=int, help="set port (default 60000)", default=60000)
parser.add_argument("-i", "--host", type=str, help="set host (default localhost)", default="localhost")
parser.add_argument("-v", "--view_dist", type=int, help="set view radius (default 400)", default=400,
                    metavar="DISTANCE")
parser.add_argument("-s", "--secret", type=str, help="set a secret to send to server (probably don't worry about it)",
                    default="")

args = parser.parse_args()


# (debug=False, render_simple=False, port=60000, host='localhost', view_dist=400, secret='')

# parsed_args = {'debug': None, 'port': None, 'host': None, 'view_dist': None, 'render_simple': None, 'secret': None}


def gen_uuid():
    return hash((random.random(), time.time()))


def debug(fun):  # do debug(lambda:<WHAT WAS ALREADY THERE>)
    do_debug = False
    if args.debug:
        do_debug = True
    if do_debug:
        return fun()


# open("config_pythonio.txt","w").write("hello")
# print("sys.argv: ",sys.argv)

# Exception classes
class HandshakeError(Exception):
    pass


# End Exception classes

# Network constants
HOST = args.host
PORT = args.port
SECRET = args.secret

# set up thread for generating segment images.
color_precision = 3

segImQueue = queue.Queue()


def segImGen():
    # print('\n\n\n',os.popen('file '+resource_path("segment.png")).read(),'\n\n\n')
    img = pygame.image.load(resource_path("assets/segment.png"))
    img = pygame.transform.scale(img, (30, 30))
    global color_precision
    dec_digs = color_precision
    iterations = 10 ** dec_digs
    for i in range(iterations):
        seg_img = img.copy()
        seg_hue = i / iterations
        for x in range(seg_img.get_width()):
            for y in range(seg_img.get_height()):
                # mult = (seg_img.get_at((x,y))[0]/255)
                # sc = seg_color
                # col = (round(sc[0]*mult),round(sc[1]*mult),round(sc[2]*mult))
                rgb = seg_img.get_at((x, y))[:3]
                hsv = colorsys.rgb_to_hsv(*rgb)
                col = colorsys.hsv_to_rgb(seg_hue, hsv[1], hsv[2])
                col = (int(col[0]), int(col[1]), int(col[2]), seg_img.get_at((x, y))[3])
                seg_img.set_at((x, y), col)
        segImQueue.put([[seg_hue, 15], seg_img.copy()])
        # print(f"segImQueue.put([[{seg_hue},15],seg_img])")
    # print("Done generating...")


segImThread = threading.Thread(target=segImGen)
if not args.render_simple:
    segImThread.start()  # thread ends when target returns

# End Network constants

# Handshake
name = input("Username: ")
# secret = None
print(f"Contacting server {HOST}:{PORT}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))
print("Connected")


def send_packet(packet: network.Packet):
    text_packet = json.dumps(network.save_packet(packet))
    #print(f"Sending packet:\n{text_packet}")
    netstring.socksend(sock, text_packet)


send_packet(network.HandshakeInit(name=name, secret=args.secret))
print("Sent handshake...")

_, msg = netstring.sockget(sock)
print(msg)
loaded = network.load_packet(json.loads(msg))
if type(loaded) != network.HandshakeRespond:
    sock.close()
    sys.exit()

print("Handshake Received...")

if not loaded.accepted:
    print(f"Server refused a connection.\nReason: {loaded.reason if loaded.reason != '' else 'None given.'}")
    sock.close()
    sys.exit()

send_packet(network.HandshakeRequestGameInfo())
print("Requested info")

_, msg = netstring.sockget(sock)
loaded = network.load_packet(json.loads(msg))
if type(loaded) != network.HandshakeGameInfo:
    sock.close()
    sys.exit()

print("Received info")

BORDER_DISTANCE = loaded.border

MAX_TURN = loaded.max_turn

send_packet(network.HandshakeStartGame())

print("Joined server...")
# End Handshake

# Ok, blocking is fine for handshakes, but you've got to not block
# waiting for a main message, especially since you don't know when it's coming.

pygame.init()

screen = pygame.display.set_mode([1100, 900])


# screen = pygame.Surface((7000,7000))

# background = pygame.image.load("/home/USER/bin/images/background_lines_7000x7000.png")

# background = pygame.transform.scale(background,(200,200))
# background = pygame.transform.scale(background,(7000,7000))

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


images = {}

seg_images = {}

head_images = {}

head_rot = 0
head_img = pygame.image.load(resource_path("assets/head.png"))
seg_img = pygame.image.load(resource_path("assets/segment.png"))
seg_color = (240, 10, 128)
# seg_hue = colorsys.rgb_to_hsv(*seg_color)[0]
seg_hue = 268 / 360
head_hue = seg_hue

'''
for x in range(seg_img.get_width()):
    for y in range(seg_img.get_height()):
        #mult = (seg_img.get_at((x,y))[0]/255)
        #sc = seg_color
        #col = (round(sc[0]*mult),round(sc[1]*mult),round(sc[2]*mult))
        rgb = seg_img.get_at((x,y))[:3]
        hsv = colorsys.rgb_to_hsv(*rgb)
        col = colorsys.hsv_to_rgb(seg_hue,hsv[1],hsv[2])
        col = (int(col[0]),int(col[1]),int(col[2]),seg_img.get_at((x,y))[3])
        seg_img.set_at((x,y),col)
#seg_img.set_colorkey((0,0,0))

for x in range(head_img.get_width()):
    for y in range(head_img.get_height()):
        #mult = (seg_img.get_at((x,y))[0]/255)
        #sc = seg_color
        #col = (round(sc[0]*mult),round(sc[1]*mult),round(sc[2]*mult))
        rgb = head_img.get_at((x,y))[:3]
        hsv = colorsys.rgb_to_hsv(*rgb)
        col = colorsys.hsv_to_rgb(head_hue,hsv[1],hsv[2])
        col = (int(col[0]),int(col[1]),int(col[2]),head_img.get_at((x,y))[3])
        head_img.set_at((x,y),col)'''

# print(head_hue,seg_hue)
# print(head_img.get_at((0,0)))
# head_img.set_colorkey((0,0,0,255))

base_head = pygame.image.load(resource_path("assets/head.png"))
base_seg = pygame.image.load(resource_path("assets/segment.png"))


class Segment(pygame.sprite.Sprite):
    def __init__(self, pos, uuid, color=(0, 125, 255), radius=15, is_head=False, is_self=False, angle=0, idx=0):
        pygame.sprite.Sprite.__init__(self)
        self.pos = tuple(pos)
        self.color = tuple(color)
        self.radius = radius
        self.is_head = is_head
        self.is_self = is_self
        self.uuid = uuid
        global seg_images, head_images, base_head, base_seg, color_precision, args
        '''try:
            self.image = images[(self.color,radius)]
        except:
            self.image = pygame.Surface([self.radius*2,self.radius*2])
            pygame.draw.ellipse(self.image,self.color,self.image.get_rect())
            self.image.set_colorkey((0,0,0))
            #print(f"type(color): {type(color)} is_head: {is_head}")
            images[(self.color,radius)] = self.image'''
        if self.is_head or True:
            self.image = pygame.Surface((self.radius * 2, self.radius * 2))
            self.image.fill((255, 255, 0))
            # self.image = pygame.transform.rotate(pygame.transform.scale(head_img,(self.radius*2,self.radius*2)),-head_rot)
        self.rect = self.image.get_rect()
        self.angle = angle
        self.idx = idx
        self.goal_angle = 0

        self.rect.x = self.pos[0] - self.rect.width / 2
        self.rect.y = self.pos[1] - self.rect.height / 2

        # self.head_img = base_head.copy()#pygame.image.load("/home/USER/bin/python_io/head.png")
        if self.is_head:
            head_img = base_head.copy()
            # print("YAY!")
            # time.sleep(1)
        self.seg_img = base_seg.copy()  # pygame.image.load("/home/USER/bin/python_io/segment.png")
        # seg_color = (240,10,128)
        self.seg_hue = round(colorsys.rgb_to_hsv(*self.color)[0], color_precision)
        self.head_hue = self.seg_hue
        if args.render_simple:
            self.seg_hue = 268 / 360
            self.head_hue = 268 / 360
            if not self.is_self:
                self.seg_hue = 5 / 360
                self.head_hue = 5 / 360
        if not self.is_head:
            try:
                # print("found matching segment!")
                self.seg_img = seg_images[(self.seg_hue, self.radius)]
            except KeyError:
                for x in range(self.seg_img.get_width()):
                    for y in range(self.seg_img.get_height()):
                        # mult = (seg_img.get_at((x,y))[0]/255)
                        # sc = seg_color
                        # col = (round(sc[0]*mult),round(sc[1]*mult),round(sc[2]*mult))
                        rgb = self.seg_img.get_at((x, y))[:3]
                        hsv = colorsys.rgb_to_hsv(*rgb)
                        col = colorsys.hsv_to_rgb(self.seg_hue, hsv[1], hsv[2])
                        col = (int(col[0]), int(col[1]), int(col[2]), self.seg_img.get_at((x, y))[3])
                        self.seg_img.set_at((x, y), col)
                # seg_img.set_colorkey((0,0,0))
                seg_images[(self.seg_hue, self.radius)] = self.seg_img
        if self.is_head:
            # print("heads are cool!")
            try:
                # self.head_hue = 0.5
                self.head_img = head_images[(self.head_hue, self.radius)].copy()
                # self.image = self.head_img
            except KeyError:
                # print("original head!")
                # self.head_hue = 0.5
                # print("1")
                # self.head_img = base_head.copy()
                temp_img = head_img.copy()  # pygame.Surface((head_img.get_width(),head_img.get_height()))
                for x in range(head_img.get_width()):
                    for y in range(head_img.get_height()):
                        # mult = (seg_img.get_at((x,y))[0]/255)
                        # sc = seg_color
                        # col = (round(sc[0]*mult),round(sc[1]*mult),round(sc[2]*mult))
                        rgb = head_img.get_at((x, y))[:3]
                        hsv = colorsys.rgb_to_hsv(*rgb)
                        # print(f"head_hue:{self.head_hue}")
                        col = colorsys.hsv_to_rgb(self.head_hue, hsv[1], hsv[2])
                        col = (int(col[0]), int(col[1]), int(col[2]), head_img.get_at((x, y))[3])
                        # self.head_img.set_at((x,y),col)
                        temp_img.set_at((x, y), col)
                        if rgb != (0, 0, 0) or col[:3] != (0, 0, 0):
                            pass  # print(f"Color was {rgb}, Color is: {col[:3]}, Pos ({x},{y})")
                # print("ONE!")
                head_images[(self.head_hue, self.radius)] = temp_img.copy()  # self.head_img.copy()
                self.head_img = temp_img.copy()
                # self.image = temp_img.copy()
                # print("TWO!")
        if self.is_head:
            self.image = pygame.transform.rotate(
                pygame.transform.scale(self.head_img, (self.radius * 2, self.radius * 2)), -head_rot)
        else:
            self.image = pygame.transform.rotate(
                pygame.transform.scale(self.seg_img, (self.radius * 2, self.radius * 2)), -math.degrees(self.angle))

    def update(self):
        if self.is_head:
            self.image = pygame.transform.rotate(
                pygame.transform.scale(self.head_img, (self.radius * 2, self.radius * 2)), -head_rot)
        else:
            self.image = pygame.transform.rotate(
                pygame.transform.scale(self.seg_img, (self.radius * 2, self.radius * 2)), -math.degrees(self.angle))
        self.rect.x = self.pos[0] - self.rect.width / 2
        self.rect.y = self.pos[1] - self.rect.height / 2


class Food(pygame.sprite.Sprite):
    # energy:
    #  1 for normal food
    # 10 for dead snake matter
    def __init__(self, pos, uuid, color=(0, 125, 255), radius=15, energy=1):
        pygame.sprite.Sprite.__init__(self)
        self.pos = tuple(pos)
        self.uuid = uuid
        self.color = tuple(color)
        self.radius = radius
        self.energy = energy
        global images
        try:
            self.image = images[(self.color, radius)]
        except KeyError:
            self.image = pygame.Surface([self.radius * 2, self.radius * 2])
            pygame.draw.ellipse(self.image, self.color, self.image.get_rect())
            self.image.set_colorkey((0, 0, 0))
            images[(self.color, radius)] = self.image
        self.rect = self.image.get_rect()

    def update(self):
        self.rect.x = self.pos[0] - self.rect.width / 2
        self.rect.y = self.pos[1] - self.rect.height / 2


# head = Segment((100,100),is_head=True,color=(200,14,150),radius=20)
# g = pygame.sprite.Group(head)

class ExtraData:
    def __init__(self):
        self.alive = True
        self.death_msg = ""


head_mutex = threading.Lock()
segs_mutex = threading.Lock()
foods_mutex = threading.Lock()
extra_data_mutex = threading.Lock()

extra_data = ExtraData()
head = Segment((0, 0), gen_uuid(), is_head=True, color=(0, 255, 0), radius=20)
segs = {}  # uuid:Segment
foods = {}  # uuid:Food


def network_thread():
    global head, head_mutex, segs_mutex, sock, foods_mutex, extra_data_mutex, extra_data, segs, foods
    while True:
        _, msg = netstring.sockget(sock)
        loaded = network.load_packet(json.loads(msg))
        if type(loaded) == network.S2CKill:
            with extra_data_mutex:
                print("We are killed")
                extra_data.alive = False
                extra_data.death_msg = loaded.msg
        elif type(loaded) == network.S2CRemoveFood:
            with foods_mutex:
                try:
                    del foods[loaded.uuid]
                except KeyError:
                    print(f"Failed to delete food with uuid {loaded.uuid}")
        elif type(loaded) == network.S2CRemoveSegment:
            with segs_mutex:
                del segs[loaded.uuid]
        elif type(loaded) == network.S2CAddFood:
            new_food = Food(loaded.pos, loaded.uuid, color=loaded.col, radius=loaded.radius, energy=loaded.energy)
            with foods_mutex:
                foods[loaded.uuid] = new_food
        elif type(loaded) == network.S2CModifySegment:
            if loaded.ishead and loaded.isown:
                with head_mutex:
                    head = Segment(loaded.pos, loaded.uuid, color=loaded.col, radius=loaded.radius,
                                   is_head=loaded.ishead, is_self=loaded.isown, angle=loaded.angle)
            else:
                with segs_mutex:
                    segs[loaded.uuid] = Segment(loaded.pos, loaded.uuid, color=loaded.col, radius=loaded.radius,
                                                is_head=loaded.ishead, is_self=loaded.isown, angle=loaded.angle,
                                                idx=loaded.idx)


networkThread = threading.Thread(target=network_thread)


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

def blit_centered(screen, source, dest, origin):
    center = (screen.get_width() / 2, screen.get_height() / 2)
    screen.blit(source, (round((center[0] - origin[0]) + dest[0]), round((center[1] - origin[1]) + dest[1])))
    # pygame.draw.circle(screen, (255,255,0), dest, 10)


def circle_centered(screen, color, pos, radius, origin):
    surf = pygame.Surface((radius * 2, radius * 2))
    surf.set_colorkey((0, 0, 0))
    if color == (0, 0, 0):
        surf.set_colorkey((255, 255, 255))
        surf.fill((255, 255, 255))
    pygame.draw.circle(surf, color, pos, radius)
    blit_centered(screen, surf, pos, origin)


cramping = 4

# for x in range(10):
#    add_seg(add_seg_pos(),color=(random.randint(10,245),random.randint(0,255),random.randint(0,255)))
mousedown = False
# sprint_mult = 1.75
###inputThread.start()
networkThread.start()
kg = True
first_run = True
while kg:
    # segImQueue.put([[seg_hue,15],seg_img])
    if not first_run:
        for i in range(2):
            if not segImQueue.empty():
                tmp = segImQueue.get()
                seg_images[tuple(tmp[0])] = tmp[1].copy()
                percent = round(tmp[0][0] * 100, 2)
                print(f"{percent}% done.    \r", end="")
                # print(f"seg_images[{tuple(tmp[0])}] = tmp[1].copy()")
    first_run = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # global shouldGetInput
            kg = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mousedown = True
        if event.type == pygame.MOUSEBUTTONUP:
            mousedown = False
    # mp = None
    mp = pygame.mouse.get_pos()
    # handle sprinting
    sprinting = mousedown and (len(segs) > 10)

    # Send Main Communications
    # global head_rot
    # temp_rot = head.goal_angle
    temp_rot = get_dif_angles(head.angle, head.goal_angle)
    # MAX_TURN = math.pi/90
    if temp_rot > MAX_TURN:
        temp_rot = MAX_TURN
    if temp_rot < MAX_TURN:
        temp_rot = -MAX_TURN
    head_rot = math.degrees(temp_rot + head.angle)  # head.goal_angle)
    # print(f"head_rot: {head_rot}, goal_angle: {math.degrees(head.goal_angle)}, angle: {math.degrees(head.angle)}")
    if head is not None:
        packet = network.C2SUpdateInput(angle=float(head.goal_angle), sprinting=sprinting)
    else:
        packet = network.C2SUpdateInput(angle=float(0), sprinting=sprinting)
    # print("sending: ",pickle.loads(send_bytes))
    send_packet(packet)


    # End Send Main Communications

    def text(screen, draw_string, pos, size=48, color=(255, 255, 255), auto=False, Font="Times"):
        font = pygame.font.Font(resource_path('assets/FreeSerif.ttf'), size)
        text = font.render(draw_string, True, color)
        text_rect = text.get_rect()
        text_rect.centerx = pos[0]  # was text_rect.centerx = pos[0]
        text_rect.y = pos[1]
        screen.blit(text, text_rect)
        # print("gutil.text() run...")
        if auto:
            pygame.display.update()


    # Process Incoming Communications
    with extra_data_mutex:
        if not extra_data.alive:
            print("Yeah, we should show we are dead")
            text(screen, extra_data.death_msg,
                 (round(screen.get_width() / 2), round(screen.get_height() / 2)))
            print(extra_data.death_msg)
            pygame.display.update()
            kg = False
            break

    # End Process Incoming Communications

    # mp = ((screen.get_width()//2)-mp[0],(screen.get_height()//2)-mp[1])
    # print(mp)

    screen.fill((255, 0, 0))
    # temp_surf = pygame.Surface((BORDER_DISTANCE*2,BORDER_DISTANCE*2))
    temp_x = 0
    temp_y = 0
    center = (screen.get_width() / 2, screen.get_height() / 2)
    dest = (0, 0)
    origin = (head.rect.x, head.rect.y)
    temp_pos = (round((center[0] - origin[0]) + dest[0]), round((center[1] - origin[1]) + dest[1]))
    pygame.draw.circle(screen, (0, 0, 0), temp_pos, BORDER_DISTANCE)
    # blit_centered(screen, temp_surf, (0,0), (head.rect.x,head.rect.y))

    # handle head
    with head_mutex:
        head.goal_angle = math.atan2(mp[1] - screen.get_height() / 2, mp[0] - screen.get_width() / 2)
        center_x = head.rect.x
        center_y = head.rect.y
    # draw food
    with foods_mutex:
        for food_uuid in foods:
            food = foods[food_uuid]
            # print("updating a food: ",food)
            food.update()
            blit_centered(screen, food.image, (food.rect.x, food.rect.y), (center_x, center_y))

    max_enemy_idx = -1
    max_own_idx = -1
    own_segs = {}  # idx:Segment[]
    enemy_segs = {}  # idx:Segment[]
    # update segments
    with segs_mutex:
        for seg_uuid in segs:
            seg = segs[seg_uuid]
            seg.update()

            # Compute order for rendering
            if seg.is_self:
                try:
                    _ = own_segs[seg.idx]
                except KeyError:
                    own_segs[seg.idx] = []
                own_segs[seg.idx].append(seg)
                if seg.idx > max_own_idx:
                    max_own_idx = seg.idx
            else:
                try:
                    _ = enemy_segs[seg.idx]
                except KeyError:
                    enemy_segs[seg.idx] = []
                enemy_segs[seg.idx].append(seg)
                if seg.idx > max_enemy_idx:
                    max_enemy_idx = seg.idx

    # render snake
    #temp_segs = segs.copy()
    #temp_segs.reverse()
    #for seg in temp_segs:
    #    blit_centered(screen, seg.image, (seg.rect.x, seg.rect.y), (center_x, center_y))
    for i in range(max_enemy_idx, 0, -1):
        try:
            for seg in enemy_segs[i]:
                blit_centered(screen, seg.image, (seg.rect.x, seg.rect.y), (center_x, center_y))
        except KeyError:
            pass
    for i in range(max_own_idx, 0, -1):
        try:
            for seg in own_segs[i]:
                blit_centered(screen, seg.image, (seg.rect.x, seg.rect.y), (center_x, center_y))
        except KeyError:
            pass
    with head_mutex:
        blit_centered(screen, head.image, (head.rect.x, head.rect.y), (center_x, center_y))
    del own_segs, enemy_segs

    # pygame.draw.circle(screen, (255,255,0), mp, 10)
    # end render
    # g.draw(screen)
    '''if len(segs)>0:
        last_seg = segs[len(segs)-1]
        last_seg_rev_angle = last_seg.angle+math.pi
        behind_dist = last_seg.radius/2
        nx = last_seg.pos[0]
        ny = last_seg.pos[1]
        nx += math.cos(last_seg_rev_angle)*behind_dist
        ny += math.sin(last_seg_rev_angle)*behind_dist
        pygame.draw.circle(screen,(255,255,255),(round(nx),round(ny)),15)'''
    # pygame.draw.circle(screen,(255,255,255),(0,0),30)
    # real_screen.fill((255,0,0))
    # real_screen.blit(screen,(-(head.pos[0]-real_screen.get_width()//2),-(head.pos[1]-real_screen.get_height()//2)))
    pygame.display.update()

send_packet(network.C2SQuit())

for x in range(5):
    print("Disconnecting in: ", 5 - x, end="\r")
    time.sleep(1)
sock.close()
sock.detach()
sock.__exit__()
print("Disconnected" + " " * 8)

pygame.quit()
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
"""

"""
Goodbye (only Client => Server is needed, or only Server => Client, there is nno reply):
  Client => Server:
    {'mode':2} #mode:2 is all that is needed to declare leaving
  Server => Client:
    {'mode':2} #optionally, {'killer':str(name_of_killer)} can also be added (if the border is the killer, 'the Border of Life and Death' will be the name)
"""
