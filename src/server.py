#!/usr/bin/python3

import os

import sys
sys.path.append(os.path.abspath(sys.argv[0]))


import math

import time

import random

import threading

import netstring

import json as pickle

import socketserver

'''thread use:
t = threading.Thread(target=function_for_thread_to_execute)
t.start() # thread ends when target returns
'''

print("Options:\n\t--debug - enable debug mode")
print("\t--moving_food - make food move")
print("\t--port <PORT> - set port (default 60000)")
print("\t--host <IP> - set host (default localhost unless with certain computer names)")
print("\t--max_clients <NUMBER> - set the maximum number of clients (default 50)")
print("\t--timeout <SECONDS> - set timeout (how often we need to hear from a client) (default 5)")
print("\t--border <RADIUS> - set border radius (beyond border, all snakes die) (default 1,200)")
print("\t--start <NUMBER> - set spawn length (default 10)")
print("\t--chance_formula <FORMULA> - create a custom formula to determine chance that a piece of food adds to length of snake. <SL> will be replaced with the length of the snake.")

global parsed_args
parsed_args = {'debug':None,'port':None,'host':None,'max_clients':None,'timeout':None,'border':None,'moving_food':None,'start':None,'chance_formula':None}

args = sys.argv.copy()
args.pop(0)
flag_args = ['debug','moving_food']
input_args = ['port','host','max_clients','timeout','border','start','chance_formula']
while len(args)>0:
    arg = args.pop(0)
    '''if arg=="--debug":
        parsed_args['debug']=True
    elif arg=="--port":
        parsed_args['port']=args.pop(0)
    elif arg=="--host":
        parsed_args['host']=args.pop(0)'''
    for opt in flag_args:
        if arg=="--"+opt:
            parsed_args[opt]=True
    for opt in input_args:
        if arg=="--"+opt:
            parsed_args[opt]=args.pop(0)
#print("parsed_args: ",parsed_args)

def debug(fun): #do debug(lambda:<WHAT WAS ALREADY THERE>)
    do_debug=False
    if parsed_args['debug']==True:
        do_debug = True
    if do_debug:
        return fun()

# Start of network setup
HOST, PORT = "localhost", 60000
#HOST = "localhost" # only for testing purposes
try:
    computer_name = os.popen("uname -n").read().replace('\n','')
    if computer_name == 'example_name':#replace with name of computer you want to set default for
        HOST = "192.168.0.5"#replace with ip address of computer
except:
    pass#don't have command uname?
if parsed_args['port'] != None:
    PORT = int(parsed_args['port'])
if parsed_args['host'] != None:
    HOST = parsed_args['host']
print(f"Serving on {HOST}:{PORT}")


global active_connections
active_connections = [] #list of ips that we are in active communication with

global dead_handling_connections
dead_handling_connections = [] #list of ips that are dead, but we still need to tell them they are dead

global MAX_CONNECTIONS
MAX_CONNECTIONS = 50

if parsed_args['max_clients']!=None:
    MAX_CONNECTIONS = int(parsed_args['max_clients'])

global TIMEOUT_TIME
TIMEOUT_TIME = 5 #we have to hear from a client every TIMEOUT_TIME seconds, or they are killed

if parsed_args['timeout']!=None:
    TIMEOUT_TIME = float(parsed_args['timeout'])

global DO_THREADS
DO_THREADS = True

global BORDER_DISTANCE
BORDER_DISTANCE = 1200#10000 #beyond this point, all snakes die

if parsed_args['border']!=None:
    BORDER_DISTANCE = int(round(float(parsed_args['border'])))

global START_LENGTH
START_LENGTH = 10

if parsed_args['start']!=None:
    START_LENGTH = int(round(float(parsed_args['start'])))

global CHANCE_FORMULA
CHANCE_FORMULA = "1"
if parsed_args['chance_formula']!=None:
    temp = parsed_args['chance_formula']
    try:
        pars = temp.replace("<SL>","3")
        eval(pars)
        CHANCE_FORMULA = temp
    except:
        pass

global LOAD_DISTANCE
LOAD_DISTANCE = 800 #how far from snakes is food handeled.

def timeout_thread():
    debug(lambda:print("timeout_thread start"))
    global snakes, TIMEOUT_TIME
    while DO_THREADS:
        for sn in snakes:
            if time.time() >= sn['last_message'] + TIMEOUT_TIME:
                #this snake is timed out, kill it.
                for ded in sn['segs']:
                    foods.append(Food((ded.rect.x,ded.rect.y), color=ded.color, radius=random.randint(13,15), energy=DEAD_MASS))
                kill(sn, "Timeout")
                debug(lambda:print(f"Timed out: ip: {sn['ip']}, uuid: {sn['uuid']}, name: {sn['name']}"))
            elif False:
                print(f"{sn['name']} last talked {time.time()-sn['last_message']} seconds ago.")

        time.sleep(1)
    debug(lambda:print("timeout_thread stop"))

timeoutThread = threading.Thread(target=timeout_thread)

def get_connection_cookie(ip):
    """
    Returns a connection cookie, which is used to verify ongoing connections, even if the client changes port, this also allows multiple instances per ip
    """
    return hash((ip, time.time()))

class MyTcpServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, address, request_handler_class):
        self.address = address
        self.request_handler_class = request_handler_class
        super().__init__(self.address, self.request_handler_class)

def clean(text): #function to 'clean' text (aka, try to filter out curse words, remove special characters, etc...)
    return text #don't feel like actually doing anything yet.

class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        global active_connections, snakes, foods, dead_handling_connections, BORDER_DISTANCE, START_LENGTH
        #self.client_address is the (ip, port) of client
        error,msg = netstring.sockget(self.request)
        error_meanings = {1:"Real Error",2:"Timeout",3:"End of File"}
        if error!=0:
            print("SOCKET ERROR: ",error_meanings[error])
        else:
            #handle the message...
            unpickled = pickle.loads(msg)
            if not 'mode' in unpickled.keys():
                """what the heck? what kind of communication is this supposed to be?"""
            elif unpickled['mode']==0: #handshake
                if len(active_connections)>=MAX_CONNECTIONS:
                    netstring.socksend(self.request, pickle.dumps({'mode':0,'accepted':False,'reason':'Server is full'}))
                else:
                    debug(lambda:print("got connection with table: ",unpickled))
                    cookie = get_connection_cookie(self.client_address[0])
                    active_connections.append((self.client_address[0],cookie))
                    netstring.socksend(self.request, pickle.dumps({'mode':0,'accepted':True,'cookie':cookie,'border_distance':BORDER_DISTANCE,'max_turn':(math.pi/90)}))
                    debug(lambda:print("replied with: ",{'mode':0,'accepted':True,'cookie':cookie}))
                    #ok, now we have to actually setup a snake for this client
                    spawn_radius = BORDER_DISTANCE - 75
                    spawn_pos = (random.randint(-spawn_radius,spawn_radius),random.randint(-spawn_radius,spawn_radius))
                    while dist(spawn_pos[0],spawn_pos[1],0,0)>spawn_radius:
                        spawn_pos = (random.randint(-spawn_radius,spawn_radius),random.randint(-spawn_radius,spawn_radius))
                    temp_snake = {}#             pos, should be randomly generated in future.
                    temp_snake['head'] = Segment(spawn_pos, cookie, color=(random.randint(10,245),random.randint(10,245),random.randint(10,245)), radius=20, is_head=True)
                    temp_snake['segs'] = []
                    
                    def add_seg_pos(head,segs):
                        if len(segs)>0:
                            last_seg = segs[len(segs)-1]
                        else:
                            last_seg = head
                        last_seg_rev_angle = last_seg.angle+math.pi
                        behind_dist = (last_seg.radius/2)#*2
                        nx = last_seg.pos[0]
                        ny = last_seg.pos[1]
                        nx += math.cos(last_seg_rev_angle)*behind_dist
                        ny += math.sin(last_seg_rev_angle)*behind_dist
                        return (nx,ny)
                    
                    for x in range(START_LENGTH): #change 10 to whatever start length you want
                        temp_snake['segs'].append(Segment(add_seg_pos(temp_snake['head'],temp_snake['segs']),cookie,color=(random.randint(10,245),random.randint(10,245),random.randint(10,245))))
                    temp_snake['mousedown'] = False
                    temp_snake['angle'] = 0
                    temp_snake['uuid'] = cookie
                    temp_snake['name'] = 'Player'
                    temp_snake['ip'] = self.client_address[0]
                    temp_snake['last_message'] = time.time()
                    if 'name' in unpickled.keys():
                        temp_snake['name'] = clean(unpickled['name'])
                    snakes.append(temp_snake)
                    del temp_snake
            elif unpickled['mode']==1: #main communications
                if 'cookie' in unpickled.keys(): #if we don't even have a cookie, no communication. WE NEED TREATS TO FUNCTION!
                    if (self.client_address[0],unpickled['cookie']) in active_connections:
                        #print("mode:1, got message: ",unpickled)
                        if not ('angle' in unpickled.keys()):
                            unpickled['angle'] = 0
                        if not ('sprinting' in unpickled.keys()):
                            unpickled['sprinting'] = False
                        for sn in snakes:
                            if sn['uuid']==unpickled['cookie']:
                                sn['mousedown'] = unpickled['sprinting']
                                sn['angle'] = unpickled['angle']
                                #update_snake(sn)###Performance upgrades
                                #print(time.time()-sn['last_message'])
                                sn['last_message'] = time.time()
            elif unpickled['mode']==2: #goodbye
                if 'cookie' in unpickled.keys(): #if we don't even have a cookie, no communication. WE NEED TREATS TO FUNCTION!
                    if (self.client_address[0],unpickled['cookie']) in active_connections:
                        debug(lambda:print("quit: ",unpickled))
                        # remove this client from list of snakes
                        new_snakes = []
                        for sn in snakes:
                            if sn['uuid']!=unpickled['cookie']:
                                new_snakes.append(sn)
                            else: #add mass of snake being removed
                                for ded in sn['segs']:
                                    foods.append(Food((ded.rect.x,ded.rect.y), color=ded.color, radius=random.randint(13,15), energy=DEAD_MASS))
                        snakes = new_snakes.copy()
                        del new_snakes

                        # remove this client from active_connections
                        new_active_connections = []
                        for ac in active_connections:
                            if ac!=(self.client_address[0],unpickled['cookie']):
                                new_active_connections.append(ac)
                        active_connections = new_active_connections.copy()
                        del new_active_connections
                        netstring.socksend(self.request,pickle.dumps({'mode':2}))
            #print("active_connections: ",active_connections)
            if 'mode' in unpickled.keys(): #just send all that stuff from the queue
                if 'cookie' in unpickled.keys(): #if we don't even have a cookie, no communication. WE NEED TREATS TO FUNCTION!
                    if ((self.client_address[0],unpickled['cookie']) in active_connections) or ((self.client_address[0],unpickled['cookie']) in dead_handling_connections):
                        #print("queue: ",out_message_queue)
                        queued_message = get_from_out_queue(self.client_address[0],unpickled['cookie'])
                        while queued_message:
                            if queued_message['mode']==2:
                                debug(lambda:print("sending: ",queued_message))
                                # remove this client from dead_handling_connections
                                temp = []
                                for dhc in dead_handling_connections:
                                    if dhc!=(self.client_address[0],unpickled['cookie']):
                                        temp.append(dhc)
                                dead_handling_connections = temp.copy()
                                del temp
                            #print("sending message from queue: ",queued_message)
                            try:
                                netstring.socksend(self.request,pickle.dumps(queued_message))
                            except TypeError:
                                print(f"Failed to send a queued message {queued_message}, to client: {self.client_address[0]}, cookie: {unpickled['cookie']}")
                            queued_message = get_from_out_queue(self.client_address[0],unpickled['cookie'])
                
        msg = b''
# End of network setup


import pygame

pygame.init()

######screen = pygame.display.set_mode([1100,900])
#screen = pygame.Surface((7000,7000))

#background = pygame.image.load("/home/USER/bin/images/background_lines_7000x7000.png")

#background = pygame.transform.scale(background,(200,200))
#background = pygame.transform.scale(background,(7000,7000))

def get_uuid(username, ip, secret=None):
    return hash((username, ip, secret))

class Segment(pygame.sprite.Sprite):
    def __init__(self, pos, snake_uuid, color=(0,125,255), radius=15, is_head=False):
        pygame.sprite.Sprite.__init__(self)
        self.pos = pos
        self.color = color
        self.radius = radius
        self.is_head = is_head
        self.image = pygame.Surface([self.radius*2,self.radius*2])
        pygame.draw.ellipse(self.image,self.color,self.image.get_rect())
        self.image.set_colorkey((0,0,0))
        self.rect = self.image.get_rect()
        self.target_pos = pos
        self.max_turn = math.pi/90#math.pi/90
        self.angle = 0
        self.spd_mlt = 6.75#2
        self.speed = 0.5*self.spd_mlt
        self.normal_speed = 0.5*self.spd_mlt
        if not self.is_head:
            self.normal_speed = self.spd_mlt*0.7#1.5*self.spd_mlt
        self.obey_max_turn = self.is_head
        if not self.is_head:
            self.max_turn = math.pi/6
        self.goal_angle = 0
        self.snake_uuid = snake_uuid
        
        self.rect.x = self.pos[0] - self.rect.width/2
        self.rect.y = self.pos[1] - self.rect.height/2
    def update(self,dtime):
        #circle_centered(screen, color, pos, 50, (0,0))
        if not self.is_head:
            self.goal_angle = math.atan2(self.target_pos[1]-self.pos[1],self.target_pos[0]-self.pos[0])

        def get_dif_angles(source,target):
            source = math.degrees(source)
            target = math.degrees(target)
            def mod(a,n):
                return a - int(a/n) * n
            r = mod(target-source,360)
            if r>180:
                r=r-360
            if -r>180:
                r = -(-r-360)
            return math.radians(r)


        max_turn = self.max_turn##*dtime*40
        
        change = get_dif_angles(self.angle,self.goal_angle)#self.goal_angle-self.angle
        #print(f"{round(change%360)}",end="\r")
        if self.obey_max_turn:
            if change>max_turn:
                change = max_turn
            if change<-self.max_turn:
                change = -max_turn
        self.angle += change

        self.pos = list(self.pos)

        temp_speed = self.speed##*dtime*40
        
        self.pos[0] += math.cos(self.angle)*temp_speed
        self.pos[1] += math.sin(self.angle)*temp_speed

        self.pos = tuple(self.pos)
        
        self.rect.x = self.pos[0] - self.rect.width/2
        self.rect.y = self.pos[1] - self.rect.height/2

class Food(pygame.sprite.Sprite):
    #energy:
    #  1 for normal food
    # 10 for dead snake matter
    def __init__(self, pos, color=(0,125,255), radius=15, energy=1):
        pygame.sprite.Sprite.__init__(self)
        self.pos = pos
        self.color = color
        self.radius = radius
        self.energy = energy
        self.image = pygame.Surface([self.radius*2,self.radius*2])
        pygame.draw.ellipse(self.image,self.color,self.image.get_rect())
        self.image.set_colorkey((0,0,0))
        self.rect = self.image.get_rect()
    def update(self):
        global snakes,foods,LOAD_DISTANCE,parsed_args
        
        self.rect.x = self.pos[0] - self.rect.width/2
        self.rect.y = self.pos[1] - self.rect.height/2

        out_of_range = True

        for sn in snakes:
            head = sn['head']
            distance = dist(self.pos[0],self.pos[1],head.pos[0],head.pos[1])
            if distance<=LOAD_DISTANCE:
                out_of_range = False
                break
                
        if out_of_range:
            #print("deleting...")
            foods.pop(foods.index(self))
        else:
            if self.energy>1:
                if random.randint(0,100000)==0:
                    self.energy -= 1
        if random.randint(0,20)==0 and parsed_args['moving_food']==True:
            self.pos = list(self.pos)
            rnge = 5
            self.pos[0] += random.randint(-rnge,rnge)
            self.pos[1] += random.randint(-rnge,rnge)
            self.pos = tuple(self.pos)

#head = Segment((100,100),is_head=True,color=(200,14,150),radius=20)
#g = pygame.sprite.Group(head)
snakes = []
foods = []
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

#pygame.mouse.set_pos([100,102])




#def screen_pos_to_game_pos(sp,scr):
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
cramping = 2.3#3#4
"""
for x in range(10):
    add_seg(add_seg_pos(),color=(random.randint(10,245),random.randint(0,255),random.randint(0,255)))
mousedown = False"""
sprint_mult = 1.75

out_message_queue = {} #outgoing message queue

def add_to_out_queue(ip,cookie,msg,do_debug=False):
    if do_debug:
        debug(lambda:print(f"added_to_out_queue: ip: {ip}, cookie: {cookie}, msg: {msg}"))
    if not ((ip,cookie) in out_message_queue.keys()):
        out_message_queue[(ip,cookie)] = []
    out_message_queue[(ip,cookie)].append(msg)
def get_from_out_queue(ip,cookie):
    if ((ip,cookie) in out_message_queue.keys()):
        if len(out_message_queue[(ip,cookie)])>0:
            return out_message_queue[(ip,cookie)].pop(0)

def kill(snake,killer_name):
    global snakes, active_connections, dead_handling_connections
    new_snakes = []
    for s in snakes:
        if s['uuid']!=snake['uuid']:
            new_snakes.append(s)
    snakes = new_snakes.copy()
    del new_snakes
    add_to_out_queue(snake['ip'],snake['uuid'],{'mode':2,'killer':killer_name},True)
    # remove this client from active_connections
    debug(lambda:print(f"killing ip: {snake['ip']}, uuid: {snake['uuid']}, killer: {killer_name}, name: {snake['name']}"))
    new_active_connections = []
    for ac in active_connections:
        if ac!=(snake['ip'],snake['uuid']):
            new_active_connections.append(ac)
        else:
            dead_handling_connections.append(ac)
    active_connections = new_active_connections.copy()
    del new_active_connections


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
def update_snake(snake,dtime_override=None):
    global snakes,foods
    head = snake['head']
    segs = snake['segs']
    mousedown = snake['mousedown']
    angle = snake['angle']
    uuid = snake['uuid']
    def add_seg_pos():
        if len(segs)>0:
            last_seg = segs[len(segs)-1]
        else:
            last_seg = head
        second_last_seg = segs[len(segs)-2]
        positive = True
        if last_seg.angle-second_last_seg.angle<0:
            positive = False
        extra = math.pi/70#((last_seg.angle-second_last_seg.angle)*-1.8)
        if not positive:
            extra = -abs(extra)
        last_seg_rev_angle = last_seg.angle+extra+math.pi
        behind_dist = (last_seg.radius/2)*2
        nx = last_seg.pos[0]
        ny = last_seg.pos[1]
        nx += math.cos(last_seg_rev_angle)*behind_dist
        ny += math.sin(last_seg_rev_angle)*behind_dist
        return (nx,ny),last_seg_rev_angle-math.pi

    def add_seg(pos,uuid,color=(0,125,255),radius=15,angle=0):
        newseg = Segment(pos,uuid,color=color,radius=radius)
        newseg.angle = angle
        #g.add(newseg)
        segs.append(newseg)
    def remove_seg():
        if len(segs)>0:
            seg = segs.pop()
            seg.kill()

    #let's start by seeing if this snake is ded
    for enemy in snakes:
        if enemy['uuid']!=snake['uuid']:
            for seg in enemy['segs']:
                if collision_circle(seg.rect.x, seg.rect.y, seg.radius, head.rect.x, head.rect.y, head.radius):
                    kill(snake,enemy['name'])
                    #add mass
                    for ded in segs:
                        foods.append(Food((ded.rect.x,ded.rect.y), color=ded.color, radius=random.randint(13,15), energy=DEAD_MASS))
                    return None
    if dist(head.pos[0],head.pos[1],0,0)>BORDER_DISTANCE:
        kill(snake,'the Border of Life and Death')
        return None
    
    #screen.fill((0,0,0))
    #mp = None
    #mp = pygame.mouse.get_pos()
    #handle sprinting
    sprinting = mousedown and (len(segs)>10)
    if sprinting and random.randint(0,275)==0:
        last_seg = segs[len(segs)-1]
        foods.append(Food((last_seg.rect.x,last_seg.rect.y), color=last_seg.color, radius=random.randint(5,8), energy=1))
        if len(segs)>0:
            seg = segs.pop()
            seg.kill()
            del seg
    
    #mp = ((screen.get_width()//2)-mp[0],(screen.get_height()//2)-mp[1])
    #print(mp)
    #handle head
    #head.target_pos = mp
    head.goal_angle = angle#math.atan2(mp[1]-screen.get_height()/2,mp[0]-screen.get_width()/2)
    head.speed = head.normal_speed
    if sprinting:
        head.speed = head.normal_speed * sprint_mult
    #if collision_circle(mp[0],mp[1],2,head.pos[0],head.pos[1],head.radius):
    #    head.speed = 0
    #handle segments
    for i in range(len(segs)):
        if i == 0:
            segs[i].target_pos = head.pos
            segs[i].speed = segs[i].normal_speed
            if sprinting:
                segs[i].speed = segs[i].normal_speed * sprint_mult
            #                                                 segs[i].radius/cramping
            if collision_circle(segs[i].pos[0],segs[i].pos[1],segs[i].radius/cramping,head.pos[0],head.pos[1],head.radius/cramping):
                segs[i].speed = 0
        else:
            segs[i].target_pos = segs[i-1].pos
            segs[i].speed = segs[i].normal_speed
            if sprinting:
                segs[i].speed = segs[i].normal_speed * sprint_mult
            if collision_circle(segs[i].pos[0],segs[i].pos[1],segs[i].radius/cramping,segs[i-1].pos[0],segs[i-1].pos[1],segs[i-1].radius/cramping):
                segs[i].speed = 0
        
        #print(s.pos)
    #add some food
    foods_in_range = 0
    for f in foods:
        if dist(f.pos[0],f.pos[1],head.pos[0],head.pos[1])<(LOAD_DISTANCE*(7/8)):
            foods_in_range += 1
    should_add_food = (foods_in_range<round((1000/1440000)*((LOAD_DISTANCE*(7/8))**2)))
    while should_add_food:
        foods_in_range = 0
        for f in foods:
            if dist(f.pos[0],f.pos[1],head.pos[0],head.pos[1])<(LOAD_DISTANCE*(7/8)):
                foods_in_range += 1
        should_add_food = (foods_in_range<round((1000/1440000)*((LOAD_DISTANCE*(7/8))**2)))
        if True:#should_add_food and random.randint(0,200)==0:
            for i in range(random.randint(0,3)):
                rnge = LOAD_DISTANCE*(7/8)#1200
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
    #deal with food
    #eat food
    new_foods = []
    search_rad = 15
    for food in foods:
        if collision_circle(food.pos[0], food.pos[1], food.radius, head.pos[0], head.pos[1], head.radius):
            #print(f"collision_circle({food.rect.x}, {food.rect.y}, {food.radius}, {head.rect.x}, {head.rect.y}, {head.radius})")
            #raise Exception("just need to end")
            #quit()
            if food.energy>0:
                for x in range(food.energy):
                    chance = int(CHANCE_FORMULA.replace("<SL>",str(len(segs))))
                    if random.randint(1,chance)==1:
                        info = add_seg_pos()
                        pos_to_add = info[0]
                        add_seg(pos_to_add,uuid,color=food.color,angle=info[1])
            else:
                for x in range(-food.energy):
                    remove_seg()
        else:
            new_foods.append(food)
    foods = new_foods.copy()
    """#draw food
    for food in foods:
        food.update()
        blit_centered(screen, food.image, (food.rect.x,food.rect.y), (head.rect.x,head.rect.y))"""
    #update snake
    dtime = time.time()-snake['last_message']
    if dtime_override!=None:
        dtime = dtime_override
    #print(f"head angle: {head.angle}, goal_angle: {head.goal_angle}, speed: {head.speed}")
    #print(f"pre head data: {head.pos}")
    head.update(dtime)
    #print(f"post head data: {head.pos}")
    #quit()
    send_distance = 775
    cx, cy = head.pos[0],head.pos[1]
    for seg in segs:
        seg.update(dtime)
    seg_mess = []
    for seg in segs:
        seg_mess.append([seg.pos,seg.color,seg.radius, seg.angle])
    message = {'mode':1,'head':[head.pos, head.color, head.radius, head.angle], 'segs':seg_mess, 'enemy_segs':[], 'food':[]}
    for s in snakes:
        if s['uuid']!=snake['uuid']:
            enemy_seg = s['head']
            if dist(enemy_seg.pos[0],enemy_seg.pos[1],cx,cy)<=send_distance:
                    message['enemy_segs'].append([enemy_seg.pos,enemy_seg.color,enemy_seg.radius,enemy_seg.angle,True])
            for enemy_seg in s['segs']:
                if dist(enemy_seg.pos[0],enemy_seg.pos[1],cx,cy)<=send_distance:
                    message['enemy_segs'].append([enemy_seg.pos,enemy_seg.color,enemy_seg.radius,enemy_seg.angle])
    for f in foods:
        f.update()
    for f in foods:
        if dist(f.pos[0],f.pos[1],cx,cy)<=send_distance:
            message['food'].append([f.pos,f.color,f.radius,f.energy])
    add_to_out_queue(snake['ip'],snake['uuid'],message)

if __name__ == "__main__":
    #global HOST, PORT

    # Create the server, binding to localhost on port 9999
    with MyTcpServer((HOST, PORT), MyTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        #server.serve_forever()
        timeoutThread.start()
        kg = True
        while kg:
            try:
                #print(dtime)
                for sn in snakes:
                    update_snake(sn,1/40)
                server.handle_request()
            except KeyboardInterrupt:
                kg = False
            #print("decoded: ", decoded)
            #if decoded=='shutdown':
            #    kg = False
        #print("hello")
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
