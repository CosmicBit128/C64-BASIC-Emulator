from pygame import OPENGL, DOUBLEBUF, FULLSCREEN, RESIZABLE
import numpy as np
import math
import json
import glm

# resolution
SCALING = 2
WIN_RES = glm.vec2(384*SCALING, 272*SCALING)
WIN_CENTER = int(WIN_RES.x//2), int(WIN_RES.y//2)
FULLSCREEN = False
FLAGS = (OPENGL | DOUBLEBUF | RESIZABLE) if not FULLSCREEN else (OPENGL | DOUBLEBUF | FULLSCREEN)

# camera
ASPECT_RATIO = WIN_RES.x / WIN_RES.y
FOV_DEG = 70
V_FOV = glm.radians(FOV_DEG)  # vertical FOV
H_FOV = 2 * math.atan(math.tan(V_FOV * 0.5) * ASPECT_RATIO)  # horizontal FOV
NEAR = 0.1
FAR = 2000.0
PITCH_MAX = glm.radians(89)
PI = 3.14159

# player
PLAYER_SPEED = 0.3
PLAYER_ROT_SPEED = 0.003
PLAYER_POS = glm.vec3(18.0, 4.0, 0.0)
YAW=180
PITCH=-10
ROLL=0
MOUSE_SENSITIVITY = 0.006

# colors
BG_COLOR = glm.vec3(0.0, 0.0, 0.0)
