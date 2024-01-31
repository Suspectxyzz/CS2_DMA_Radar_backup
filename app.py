import memprocfs
import struct
import time
import pygame
import pygame_gui
import json
import math
import numpy as np
import os
import re
import threading

########## ADJUST SIZES HERE ##########

triangle_length = 13
circle_size = 7 # 8 too big
hp_font_size = 18
rot_angle = 0

#######################################

maps_with_split = ['de_nuke','de_vertigo']
dwEntityList = 0x17CE6A0
dwLocalPlayerPawn = 0x16D4F48
m_iHealth = 0x32C
m_vOldOrigin = 0x1224
m_iTeamNum = 0x3BF
m_angEyeAngles = 0x1518
mapNameVal = 0x1CC200
m_iCompTeammateColor = 0x738
m_bIsDefusing = 0x13B0
global players

#######################################

entitys = []
zoom_scale = 2

def world_to_minimap(x, y, pos_x, pos_y, scale, map_image, screen, zoom_scale, rotation_angle):
    image_x = int((x - pos_x) * screen.get_width() / (map_image.get_width() * scale * zoom_scale))
    image_y = int((y - pos_y) * screen.get_height() / (map_image.get_height() * scale * zoom_scale))
    center_x, center_y = screen.get_width() // 2, screen.get_height() // 2
    image_x, image_y = rotate_point((center_x, center_y), (image_x, image_y), rotation_angle)
    return int(image_x), int(image_y)

def rotate_point(center, point, angle):
    angle_rad = math.radians(angle)
    temp_point = point[0] - center[0], center[1] - point[1]
    temp_point = (temp_point[0]*math.cos(angle_rad)-temp_point[1]*math.sin(angle_rad), temp_point[0]*math.sin(angle_rad)+temp_point[1]*math.cos(angle_rad))
    temp_point = temp_point[0] + center[0], center[1] - temp_point[1]
    return temp_point

def getmapdata(mapname):
    with open(f'maps/{mapname}/meta.json', 'r') as f:
        data = json.load(f)
    scale = data['scale']
    x = data['offset']['x']
    y = data['offset']['y']
    return scale,x,y

def getlowermapdata(mapname):
    with open(f'maps/{mapname}/meta.json', 'r') as f:
        data = json.load(f)
    lowerx = data['splits']['offset']['x']
    lowery = data['splits']['offset']['y']
    z = data['splits']['zRange']['z']
    return lowerx,lowery,z

def readmapfrommem():
    mapNameAddress_dll = cs2.module('matchmaking.dll')
    mapNameAddressbase = mapNameAddress_dll.base
    mapNameAddress = struct.unpack("<Q", cs2.memory.read(mapNameAddressbase + mapNameVal, 8, memprocfs.FLAG_NOCACHE))[0]
    mapName = struct.unpack("<32s", cs2.memory.read(mapNameAddress+0x4, 32, memprocfs.FLAG_NOCACHE))[0].decode('utf-8', 'ignore')
    return str(mapName)

def rotate_image(image, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect().center)
    return rotated_image, new_rect

def getentitys():
    while True:
        players = []
        for entityId in range(1,2048):
            EntityENTRY = struct.unpack("<Q", cs2.memory.read((entList + 0x8 * (entityId >> 9) + 0x10), 8, memprocfs.FLAG_NOCACHE))[0]
            try:
                entity = struct.unpack("<Q", cs2.memory.read(EntityENTRY + 120 * (entityId & 0x1FF), 8, memprocfs.FLAG_NOCACHE))[0]
                entityHp = struct.unpack("<I", cs2.memory.read(entity + m_iHealth, 4, memprocfs.FLAG_NOCACHE))[0]
                team = struct.unpack("<I", cs2.memory.read(entity + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
                if int(team) == 1 or int(team) == 2 or int(team) == 3:
                    if entityHp<=100 and entityHp>0:
                        p = player1(entity)
                        players.append(p)
                        print('added 1')
                else:
                    pass
            except:
                pass
        print(players)
        time.sleep(10)

class player1:
    def __init__(self, entity_id):
        self.entity_id = entity_id
        self.pX = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin +0x4, 4, memprocfs.FLAG_NOCACHE))[0]
        self.pY = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin, 4, memprocfs.FLAG_NOCACHE))[0]
        self.pZ = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin +0x8, 4, memprocfs.FLAG_NOCACHE))[0]
        self.Hp = struct.unpack("<I", cs2.memory.read(entity_id + m_iHealth, 4, memprocfs.FLAG_NOCACHE))[0]
        self.team = struct.unpack("<I", cs2.memory.read(entity_id + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
        self.EyeAngles = struct.unpack("<fff", cs2.memory.read(entity_id +(m_angEyeAngles +0x4) , 12, memprocfs.FLAG_NOCACHE))
        self.EyeAngles = math.radians(self.EyeAngles[0]+rot_angle)

    def draw(self, screen):
        if mapname in maps_with_split:
            if self.pZ<lowerz:
                transformed_x, transformed_y = world_to_minimap(self.pX, self.pY, lowerx, lowery, scale, map_image, screen, zoom_scale, rot_angle)
            else:
                transformed_x, transformed_y = world_to_minimap(self.pX, self.pY, x, y, scale, map_image, screen, zoom_scale, rot_angle)
        else:
            transformed_x, transformed_y = world_to_minimap(self.pX, self.pY, x, y, scale, map_image, screen, zoom_scale, rot_angle)
        triangle_top_x = transformed_x + math.sin(self.EyeAngles) * triangle_length
        triangle_top_y = transformed_y + math.cos(self.EyeAngles) * triangle_length
        triangle_left_x = transformed_x + math.sin(self.EyeAngles + math.pi / 3) * triangle_length / 2
        triangle_left_y = transformed_y + math.cos(self.EyeAngles + math.pi / 3) * triangle_length / 2
        triangle_right_x = transformed_x + math.sin(self.EyeAngles - math.pi / 3) * triangle_length / 2
        triangle_right_y = transformed_y + math.cos(self.EyeAngles - math.pi / 3) * triangle_length / 2
        if self.Hp > 0 and self.team == 2:
            pygame.draw.polygon(screen, triangle_color, [(triangle_top_x, triangle_top_y), (triangle_left_x, triangle_left_y), (triangle_right_x, triangle_right_y)])
            pygame.draw.circle(screen, (255, 0, 0), (transformed_x, transformed_y), circle_size)
        if self.Hp > 0 and self.team == 3:
            pygame.draw.polygon(screen, triangle_color, [(triangle_top_x, triangle_top_y), (triangle_left_x, triangle_left_y), (triangle_right_x, triangle_right_y)])
            pygame.draw.circle(screen, (0, 0, 255), (transformed_x, transformed_y), circle_size)
        if self.Hp>30:
            text_surface = font.render(f'  {self.Hp}', True, (0, 255, 0))
            text_surface.set_alpha(255)
        if self.Hp<=30:  
            text_surface = font.render(f'  {self.Hp}', True, (255, 0, 0))
            text_surface.set_alpha(255)
        if self.Hp==0:
            text_surface = font.render(f'  {self.Hp}', True, (255, 0, 0))
            text_surface.set_alpha(0)
        screen.blit(text_surface, (transformed_x, transformed_y))

vmm = memprocfs.Vmm(['-device', 'fpga', '-disable-python', '-disable-symbols', '-disable-symbolserver', '-disable-yara', '-disable-yara-builtin', '-debug-pte-quality-threshold', '64'])
cs2 = vmm.process('cs2.exe')
client = cs2.module('client.dll')
client_base = client.base
print(f"[+] Finded client base")

entList = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
print(f"[+] Entered entitylist")

player = struct.unpack("<Q", cs2.memory.read(client_base + dwLocalPlayerPawn, 8, memprocfs.FLAG_NOCACHE))[0]

mapname = readmapfrommem()

map_folders = [f for f in os.listdir('maps') if os.path.isdir(os.path.join('maps', f))]

for folder in map_folders:
    if folder in mapname:
        mapname = folder
        break

if mapname == 'empty':
    print(f"[-] You are not connected to map")
    exit()
if os.path.exists(f'maps/{mapname}'):
    pass
else:
    print(f'[-] Please, import this map first ({mapname})')
    exit()
print(f"[+] Found map {mapname}")
if mapname in maps_with_split:
    lowerx,lowery,lowerz = getlowermapdata(mapname)
scale,x,y = getmapdata(mapname)
pygame.init()

manager = pygame_gui.UIManager((600, 600))
clock = pygame.time.Clock()
screen_width, screen_height = 600, 600
screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
pygame.display.set_caption("CS2 Radar")
map_image = pygame.image.load(f'maps/{mapname}/radar.png')
font = pygame.font.Font(None, hp_font_size)
rot_plus_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((50, 50), (120, 30)), text='ANGLE+90', manager=manager)

while True:
    thread1 = threading.Thread(target=getentitys)
    thread1.start()
    running = True
    while running:
        try:
            if 1==1:
                players[0]
            #except:
                #print('Entity list is clear. Retrying in 5 sec)')
                #time.sleep(5)
                #continue
        except:
            print('[-] Error data reading. Some entity leave or map closed. Closing program')
            exit()

        time_delta = clock.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            manager.process_events(event)
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == rot_plus_button:
                        rot_angle += 90
        manager.update(time_delta)

        screen.fill((0, 0, 0))

        triangle_color = (255, 255, 255)

        rotated_map_image, map_rect = rotate_image(pygame.transform.scale(map_image, screen.get_size()), rot_angle)
        rot_plus_button.set_position([50, 50])
        screen.blit(rotated_map_image, map_rect.topleft)
        manager.draw_ui(screen)
        for p in players:
            p.draw(screen)

        pygame.display.flip()
pygame.quit()

