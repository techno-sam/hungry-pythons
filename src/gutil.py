#!/usr/bin/python3

#IMPORTANT NOTE:
#this CANNOT be run. It will FAIL!!!
#it is ONLY for IMPORTING PURPOSES!!!
#ONLY TO BE USED WITH PYGAME!!!
#currently, you MUST have your PYGAME DISPLAY called: screen

#functions and variables:
"""
text(draw_string, pos, size=48, color=(255,255,255))
question(qtext, show_text=True, color=(255, 255, 255), background=(0,0,0))
"""

#function definitions:
import pygame
import time
pygame.init()
def text(screen, draw_string, pos, size=48, color=(255,255,255), auto=False, Font="Times"):
    print(f"Loading font {Font}")
    font = pygame.font.SysFont(Font, size)
    text = font.render(draw_string, True, color)
    text_rect = text.get_rect()
    text_rect.x = pos[0] #was text_rect.centerx = pos[0]
    text_rect.y = pos[1]
    screen.blit(text, text_rect)
    #print("gutil.text() run...")
    if auto:
        pygame.display.update()
def type_text(screen, textt, pos, size=48, color=(255,255,255), delay=0.35):
      for i in range(len(textt)):
            screen.fill((0,0,0))
            try:
                  text(screen, textt[:i+1], pos, size, color)
            except:
                  text(screen, textt, pos, size, color)
            pygame.display.update()
            time.sleep(delay)


global p,i,size
p = i = size = 0
def d():
      global p,i,size
      try:
            p = list(p)
            p[1] = pos[1] + ((size + 10)*i) + endy + 10
            p = tuple(p)
      except:
            jksfljghsdfghsdljh = "" #print("Error running d()")

def smart_type(screen, textt, pos, size=48, color=(255,255,255), delay=0.35, Font="Times", bg=(0,0,0)):
      #global p,i,size
      lines = textt.split("\n")
      already_done = []
      endy = 0
      for i in range(len(lines)):
            screen.fill(bg)
            """for i3 in range(len(already_done)):
                  te = already_done[i3]
                  x = pos[0] + ((size + 10)*i3)
                  y = pos[1]
                  gutil.text(screen, te, (x, y), size, color)"""
            tex = lines[i]
            p = list(pos)
            p[1] = pos[1] + ((size + 10)*i)
            for i2 in range(len(tex)):
                  screen.fill(bg)
                  ##p = list(p)
                  for i3 in range(len(already_done)):
                        te = already_done[i3]
                        y = pos[1] + ((size + 10)*i3)
                        x = pos[0]
                        text(screen, te, (x, y), size, color, Font=Font)
                        endy = y
                        d()
                        #pygame.display.update()
                        #print("1")
                        '''p[1] += endy
                        p[1] += 10
                        p = tuple(p)'''
                  ##p[1] = pos[1] + ((size + 10)*i) + endy + 10
                  #p[1] += 10
                  ##p = tuple(p)
                  d()
                  
                  try:
                        text(screen, tex[:i2+1], p, size, color, True, Font=Font)
                        #print(tex[:i2+1])
                  except:
                        text(screen, tex, p, size, color, True, Font=Font)
                  pygame.display.update()

                  #print(time.ctime(time.time()))
                  l = len(tex)
                  if True: #not tex[l-1] == " ":
                        time.sleep(delay)
            already_done.append(tex)
            #endx = p[0]

def question(screen, qtext, show_text=True, color=(255, 255, 255), background=(0,0,0)):
    retu = False
    keepGoing = True
    BLACK = background
    WHITE = color
    button_list = [pygame.K_a, pygame.K_b, pygame.K_c, pygame.K_d, pygame.K_e, pygame.K_f, pygame.K_g, pygame.K_h, pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l, pygame.K_m, pygame.K_n, pygame.K_o, pygame.K_p, pygame.K_q, pygame.K_r, pygame.K_s, pygame.K_t, pygame.K_u, pygame.K_v, pygame.K_w, pygame.K_x, pygame.K_y, pygame.K_z, pygame.K_COMMA, pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_PERIOD, pygame.K_AT]

    letter_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", ",", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "@"]
    text_list = []


    while keepGoing:
        rounds = -1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    retu = True
                for button in button_list:
                    rounds += 1
                    if event.key == button:
                        try:
                            text_list += letter_list[rounds]
                        except Exception:
                            a = "hello"
        screen.fill(BLACK)
        #display question
        font = pygame.font.SysFont("Times", 24)
        text = font.render(qtext, True, WHITE)
        text_rect = text.get_rect()
        #text_rect.centerx = screen.get_rect().centerx
        text_rect.x = 0
        text_rect.y = 0
        screen.blit(text, text_rect)
        #display typed text
        draw_string = ""
        for letter in text_list:
            draw_string += letter
        font = pygame.font.SysFont("Times", 24)
        text = font.render(draw_string, True, WHITE)
        text_rect = text.get_rect()
        text_rect.centerx = screen.get_rect().centerx
        text_rect.y = 40
        if show_text:
            screen.blit(text, text_rect)
        if retu:
            keepGoing = False
            return draw_string
        pygame.display.update()


def safe_question(screen, qtext, show_text=True, color=(255, 255, 255), background=(0,0,0)):
    retu = False
    keepGoing = True
    BLACK = background
    WHITE = color
    button_list = [pygame.K_a, pygame.K_b, pygame.K_c, pygame.K_d, pygame.K_e, pygame.K_f, pygame.K_g, pygame.K_h, pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l, pygame.K_m, pygame.K_n, pygame.K_o, pygame.K_p, pygame.K_q, pygame.K_r, pygame.K_s, pygame.K_t, pygame.K_u, pygame.K_v, pygame.K_w, pygame.K_x, pygame.K_y, pygame.K_z, pygame.K_COMMA, pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_PERIOD, pygame.K_AT]

    letter_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", ",", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "@"]
    text_list = []


    while keepGoing:
        rounds = -1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                #pygame.quit()
                print("NO CLOSING WINDOW!!!")
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    retu = True
                for button in button_list:
                    rounds += 1
                    if event.key == button:
                        try:
                            text_list += letter_list[rounds]
                        except Exception:
                            a = "hello"
        screen.fill(BLACK)
        #display question
        font = pygame.font.SysFont("Times", 24)
        text = font.render(qtext, True, WHITE)
        text_rect = text.get_rect()
        text_rect.centerx = screen.get_rect().centerx
        text_rect.y = 10
        screen.blit(text, text_rect)
        #display typed text
        draw_string = ""
        for letter in text_list:
            draw_string += letter
        font = pygame.font.SysFont("Times", 24)
        text = font.render(draw_string, True, WHITE)
        text_rect = text.get_rect()
        text_rect.centerx = screen.get_rect().centerx
        text_rect.y = 40
        if show_text:
            screen.blit(text, text_rect)
        if retu:
            keepGoing = False
            return draw_string
        pygame.display.update()
#end of module
