from moderngl import TRIANGLE_STRIP
from settings import *
import pygame as pg


class PostProcess:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx
        self.c = 0
        self.ce = True
        self.palettes = {
            'apple': [
                '#101010',#624ecd',
                '#22AA22'#a792ff'
            ],
            'c64': [
                '#624ecd',
                '#a792ff'
            ]
        }
        self.color = self.palettes['c64']

        # Font
        self.font = pg.transform.scale_by(pg.image.load('res/tileset.png'), SCALING)
        pixels = pg.PixelArray(self.font)
        pixels.replace(pg.Color('#ffffff'), pg.Color(self.color[0]))  # Replace white with blue
        pixels.replace(pg.Color('#000000'), pg.Color(self.color[1]))  # Replace white with blue
        del pixels

        # Post-Processing Render Passes
        self.passes = {
            'crt': []
        }

        # Framebuffer
        self.fbo_texture = self.ctx.texture((int(WIN_RES.x), int(WIN_RES.y)), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.fbo_texture])

        self.quad_vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0
        ], dtype='f4')

        self.quad_buffer = self.ctx.buffer(self.quad_vertices.tobytes())

        for post in self.passes.keys():
            prog = self.get_program(post)
            uniforms = self.get_uniforms(post)
            vao = self.ctx.simple_vertex_array(prog, self.quad_buffer, 'Position')

            self.passes[post] = [prog, uniforms, self.quad_buffer, vao]

        self.set_uniforms_on_init()

    def update(self):
        surf = pg.Surface(WIN_RES)
        surf.fill(self.color[1])
        surf.fill(self.color[0], (32*SCALING, 36*SCALING, 320*SCALING, 200*SCALING))
        # 15 -> 8 | 600 -> 320 | 720 -> 384
        # 16 -> 8 | 400 -> 200 | 544 -> 272
        # Draw Screen
        for y in range(25):
            for x in range(40):
                char = int(self.app.screen.screen[x, y])
                cx, cy = (char%16, char//16)
                if [x, y]==self.app.screen.cur_pos and self.app.time%.5<.25:
                    cy += 8
                surf.blit(
                    self.font.subsurface(SCALING*cx*8, SCALING*cy*8, SCALING*8, SCALING*8),
                    ((32 + x*8)*SCALING, (36 + y*8)*SCALING)
                )
        self.screen_texture, w, h = self.app.create_mgl_texture_from_surface(surf)
    
    def render(self):
        # CRT pass
        crt_pass = self.passes['crt']
        prog, uniforms, _, vao = crt_pass

        # Bind FBO texture to sampler
        self.ctx.screen.use()
        self.ctx.clear(color=BG_COLOR)
        self.screen_texture.use(location=0)
        self.fbo_texture.use(location=1)

        # Set uniforms
        for k, v in uniforms['update'].items():
            prog[k].value = eval(v)

        vao.render(TRIANGLE_STRIP)
        self.fbo.clear(color=BG_COLOR)
        self.ctx.copy_framebuffer(self.fbo, self.ctx.screen)

    def out_callback(self, text):
        self.app.screen.write(*self.app.screen.cur_pos, f"{text}\n")

    def set_uniforms_on_init(self):
        for shader in self.passes.keys():
            for k, v in self.passes[shader][1]['init'].items():
                self.passes[shader][0][k].value = eval(v)

    def get_uniforms(self, name):
        with open(f'shaders/{name}.json', 'r') as f:
            data = json.load(f)
        for k, v in data['update'].items():
            if isinstance(data['update'][k], (list, tuple)):
                data['update'][k] = [float(i) for i in v]
        return data
    
    def get_program(self, shader_name):
        with open(f'shaders/screen.vert') as file:
            vertex_shader = file.read()
        with open(f'shaders/{shader_name}.frag') as file:
            fragment_shader = file.read()

        program = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        return program