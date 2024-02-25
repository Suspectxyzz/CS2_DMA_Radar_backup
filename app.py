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
from requests import get
import threading


with open(f'config.json', 'r') as f:
    settings = json.load(f)

triangle_length = settings['triangle_length']
circle_size = settings['circle_size']
hp_font_size = settings['hp_font_size']
rot_angle = settings['rot_angle']
cross_size = settings['cross_size']

#######################################

offsets = get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/generated/offsets.json').json()
clientdll = get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/generated/client.dll.json').json()

#######################################

maps_with_split = ['de_nuke','de_vertigo']
dwEntityList = offsets['client_dll']['data']['dwEntityList']['value']
dwLocalPlayerPawn = offsets['client_dll']['data']['dwLocalPlayerPawn']['value']
m_iPawnHealth = clientdll['CCSPlayerController']['data']['m_iPawnHealth']['value']
m_iPawnArmor = clientdll['CCSPlayerController']['data']['m_iPawnArmor']['value']
m_bPawnIsAlive = clientdll['CCSPlayerController']['data']['m_bPawnIsAlive']['value']
m_angEyeAngles = clientdll['C_CSPlayerPawnBase']['data']['m_angEyeAngles']['value']
m_iTeamNum = clientdll['C_BaseEntity']['data']['m_iTeamNum']['value']
m_hPlayerPawn = clientdll['CCSPlayerController']['data']['m_hPlayerPawn']['value']
m_vOldOrigin = clientdll['C_BasePlayerPawn']['data']['m_vOldOrigin']['value']
m_iIDEntIndex = clientdll['C_CSPlayerPawnBase']['data']['m_iIDEntIndex']['value']
m_iHealth = clientdll['C_BaseEntity']['data']['m_iHealth']['value']
mapNameVal = offsets['matchmaking_dll']['data']['dwGameTypes_mapName']['value']
m_bIsDefusing = clientdll['C_CSPlayerPawnBase']['data']['m_bIsDefusing']['value']
m_bPawnHasDefuser = clientdll['CCSPlayerController']['data']['m_bPawnHasDefuser']['value']
m_iCompTeammateColor = clientdll['CCSPlayerController']['data']['m_iCompTeammateColor']['value']
print('[+] offsets parsed')

#https://github.com/a2x/cs2-dumper/tree/main/generated

#######################################

zoom_scale = 2
map_folders = [f for f in os.listdir('maps') if os.path.isdir(os.path.join('maps', f))]
global_entity_list = []
def world_to_minimap(x, y, pos_x, pos_y, scale, map_image, screen, zoom_scale, rotation_angle):
    try:
        image_x = int((x - pos_x) * screen.get_width() / (map_image.get_width() * scale * zoom_scale))
        image_y = int((y - pos_y) * screen.get_height() / (map_image.get_height() * scale * zoom_scale))
        center_x, center_y = screen.get_width() // 2, screen.get_height() // 2
        image_x, image_y = rotate_point((center_x, center_y), (image_x, image_y), rotation_angle)
        return int(image_x), int(image_y)
    except:
        return 0,0

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
    mapNameAddress = struct.unpack("<Q", cs2.memory.read(mapNameAddressbase + mapNameVal, 8, memprocfs.FLAG_NOCACHE))[0]
    mapname = struct.unpack("<32s", cs2.memory.read(mapNameAddress+0x4, 32, memprocfs.FLAG_NOCACHE))[0].decode('utf-8', 'ignore')
    for folder in map_folders:
        if folder in mapname:
            mapname = folder
            break
    if mapname != 'empty':
        print(f"[+] Found map {mapname}")
    mapname = str(mapname)
    return mapname

def get_only_mapname():
    mapNameAddress = struct.unpack("<Q", cs2.memory.read(mapNameAddressbase + mapNameVal, 8, memprocfs.FLAG_NOCACHE))[0]
    mapname = struct.unpack("<32s", cs2.memory.read(mapNameAddress+0x4, 32, memprocfs.FLAG_NOCACHE))[0].decode('utf-8', 'ignore')
    mapname = str(mapname)
    return mapname

def pawnhandler():
    global global_entity_list
    global playerTeam
    while True:
        try:
            entityss = getentitypawns()
            if global_entity_list == entityss:
                pass
            else:
                global_entity_list = entityss
            
            player = struct.unpack("<Q", cs2.memory.read(client_base + dwLocalPlayerPawn, 8, memprocfs.FLAG_NOCACHE))[0]
            playerTeam = struct.unpack("<I", cs2.memory.read(player + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
        except:
            pass

        time.sleep(10)

def rotate_image(image, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect().center)
    return rotated_image, new_rect

def getentitypawns():
    entitys = []
    EntityList = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
    EntityList = struct.unpack("<Q", cs2.memory.read(EntityList + 0x10, 8, memprocfs.FLAG_NOCACHE))[0]
    for i in range(0,64):
        try:
            EntityAddress = struct.unpack("<Q", cs2.memory.read(EntityList + (i + 1) * 0x78, 8, memprocfs.FLAG_NOCACHE))[0]
            EntityPawnListEntry = struct.unpack("<Q", cs2.memory.read(client_base + dwEntityList, 8, memprocfs.FLAG_NOCACHE))[0]
            Pawn = struct.unpack("<Q", cs2.memory.read(EntityAddress + m_hPlayerPawn, 8, memprocfs.FLAG_NOCACHE))[0]
            EntityPawnListEntry = struct.unpack("<Q", cs2.memory.read(EntityPawnListEntry + 0x10 + 8 * ((Pawn & 0x7FFF) >> 9), 8, memprocfs.FLAG_NOCACHE))[0]
            Pawn = struct.unpack("<Q", cs2.memory.read(EntityPawnListEntry + 0x78 * (Pawn & 0x1FF), 8, memprocfs.FLAG_NOCACHE))[0]
            entitys.append((Pawn, EntityAddress))
        except:
            pass
    return(entitys)

class player1:
    def __init__(self, entity_id, EntityAddress):
        self.entity_id = entity_id
        self.EntityAddress = EntityAddress
        self.pX = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin +0x4, 4, memprocfs.FLAG_NOCACHE))[0]
        self.pY = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin, 4, memprocfs.FLAG_NOCACHE))[0]
        self.pZ = struct.unpack("<f", cs2.memory.read(entity_id + m_vOldOrigin +0x8, 4, memprocfs.FLAG_NOCACHE))[0]
        self.Hp = struct.unpack("<I", cs2.memory.read(entity_id + m_iHealth, 4, memprocfs.FLAG_NOCACHE))[0]
        self.team = struct.unpack("<I", cs2.memory.read(entity_id + m_iTeamNum, 4, memprocfs.FLAG_NOCACHE))[0]
        self.EyeAngles = struct.unpack("<fff", cs2.memory.read(entity_id +(m_angEyeAngles +0x4) , 12, memprocfs.FLAG_NOCACHE))
        self.EyeAngles = math.radians(self.EyeAngles[0]+rot_angle)
        self.isdefusing = struct.unpack("<I", cs2.memory.read(entity_id + m_bIsDefusing, 4, memprocfs.FLAG_NOCACHE))[0]
        self.hasdefuser = struct.unpack("?", cs2.memory.read(EntityAddress + m_bPawnHasDefuser, 1, memprocfs.FLAG_NOCACHE))[0]
        self.color = struct.unpack("<I", cs2.memory.read(EntityAddress + m_iCompTeammateColor, 4, memprocfs.FLAG_NOCACHE))[0]
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
        if self.Hp > 0 and self.team == playerTeam:
            if self.color == 0:
                pygame.draw.polygon(screen, triangle_color, [(triangle_top_x, triangle_top_y), (triangle_left_x, triangle_left_y), (triangle_right_x, triangle_right_y)])
                pygame.draw.circle(screen, (0, 0, 255), (transformed_x, transformed_y), circle_size)
            if self.color == 1:
                pygame.draw.polygon(screen, triangle_color, [(triangle_top_x, triangle_top_y), (triangle_left_x, triangle_left_y), (triangle_right_x, triangle_right_y)])
                pygame.draw.circle(screen, (0, 255, 0), (transformed_x, transformed_y), circle_size)
            if self.color == 2:
                pygame.draw.polygon(screen, triangle_color, [(triangle_top_x, triangle_top_y), (triangle_left_x, triangle_left_y), (triangle_right_x, triangle_right_y)])
                pygame.draw.circle(screen, (255, 255, 0), (transformed_x, transformed_y), circle_size)
            if self.color == 3:
                pygame.draw.polygon(screen, triangle_color, [(triangle_top_x, triangle_top_y), (triangle_left_x, triangle_left_y), (triangle_right_x, triangle_right_y)])
                pygame.draw.circle(screen, (255, 106, 2), (transformed_x, transformed_y), circle_size)
            if self.color == 4:
                pygame.draw.polygon(screen, triangle_color, [(triangle_top_x, triangle_top_y), (triangle_left_x, triangle_left_y), (triangle_right_x, triangle_right_y)])
                pygame.draw.circle(screen, (167, 107, 243), (transformed_x, transformed_y), circle_size)
        if self.Hp > 0 and self.team != playerTeam:
            pygame.draw.polygon(screen, triangle_color, [(triangle_top_x, triangle_top_y), (triangle_left_x, triangle_left_y), (triangle_right_x, triangle_right_y)])
            pygame.draw.circle(screen, (255, 0, 0), (transformed_x, transformed_y), circle_size)
        if self.isdefusing == 1:
            if self.hasdefuser:
                pygame.draw.line(screen, (255, 0, 0), (transformed_x - cross_size, transformed_y - cross_size), (transformed_x + cross_size, transformed_y + cross_size), 2)
                pygame.draw.line(screen, (255, 0, 0), (transformed_x + cross_size, transformed_y - cross_size), (transformed_x - cross_size, transformed_y + cross_size), 2)
            else:
                pygame.draw.line(screen, (0, 255, 0), (transformed_x - cross_size, transformed_y - cross_size), (transformed_x + cross_size, transformed_y + cross_size), 2)
                pygame.draw.line(screen, (0, 255, 0), (transformed_x + cross_size, transformed_y - cross_size), (transformed_x - cross_size, transformed_y + cross_size), 2)
        if self.Hp>30:
            text_surface = font.render(f'  {self.Hp}', True, (0, 255, 0))
            text_surface.set_alpha(255)
        if self.Hp<=30:  
            text_surface = font.render(f'  {self.Hp}', True, (255, 0, 0))
            text_surface.set_alpha(255)
        if self.Hp==0:
            text_surface = font.render(f'  {self.Hp}', True, (255, 0, 0))
            text_surface.set_alpha(0)
        if self.Hp>100:
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


mapNameAddress_dll = cs2.module('matchmaking.dll')
mapNameAddressbase = mapNameAddress_dll.base

pygame.init()
manager = pygame_gui.UIManager((600, 600))
clock = pygame.time.Clock()
screen_width, screen_height = 600, 600
screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
pygame.display.set_caption("CS2 Radar")
font = pygame.font.Font(None, hp_font_size)
rot_plus_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((50, 50), (120, 30)), text='ANGLE+90', manager=manager)

running = True
while running:
    t = threading.Thread(target=pawnhandler)
    t.start()
    mapname = readmapfrommem()
    if 'empty' in mapname:
        image = pygame.image.load(f'maps/empty/1.png')
        rotat_image = pygame.transform.rotate(image, 0)
        rect = rotat_image.get_rect(center = image.get_rect().center)
        screen.blit(image, rect.topleft)
        pygame.display.flip()
        time.sleep(8)
        continue
    if os.path.exists(f'maps/{mapname}'):
        pass
    else:
        print(f'[-] Please, import this map first ({mapname})')
        continue
    if mapname in maps_with_split:
        lowerx,lowery,lowerz = getlowermapdata(mapname)
    scale,x,y = getmapdata(mapname)
    map_image = pygame.image.load(f'maps/{mapname}/radar.png')
    while not 'empty' in get_only_mapname():
        try:
            players = []
            for Pawn, EntityAddress in global_entity_list:
                p = player1(Pawn,EntityAddress)
                players.append(p)
        except:
            pass

        time_delta = clock.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()
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
        try:
            for p in players:
                p.draw(screen)
        except:
            pass

        pygame.display.flip()
pygame.quit()
