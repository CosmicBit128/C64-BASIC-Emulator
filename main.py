import moderngl as mgl
import pygame as pg

from settings import *
from screen import Screen
from post import PostProcess
from keyboard import KeyboardHandler
from interpreter import BasicInterpreter


class Renderer:
    def __init__(self, win_res, framerate: float = 60.0):
        pg.init()

        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 4)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 0)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, 24)

        pg.display.set_mode(win_res, flags=FLAGS)
        pg.display.set_caption("Commodore 64 BASIC Interpreter")
        self.ctx = mgl.create_context()

        self.ctx.enable(mgl.DEPTH_TEST | mgl.CULL_FACE | mgl.BLEND)
        self.ctx.gc_mode = 'auto'

        self.fps = framerate

        # Time
        self.clock = pg.time.Clock()
        self.time = 0
        self.dt = 0

        # Setup modules
        self.on_init()

    def on_init(self):
        self.screen = Screen(self)
        self.post = PostProcess(self)
        self.inter = BasicInterpreter(self.post.out_callback)
        self.kb = KeyboardHandler(self)

    def update(self):
        self.dt = self.clock.tick(0)
        self.time = pg.time.get_ticks()*0.001
        self.post.update()

        keys = pg.key.get_pressed()
        if keys[pg.K_KP_PLUS]:
            self.post.c += 0.01
        if keys[pg.K_KP_MINUS]:
            self.post.c -= 0.01

    def render(self):
        self.post.render()
        pg.display.flip()

    def events(self):
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit(0)
            
            if e.type == pg.KEYDOWN:
                self.kb.keydown_callback(e)
            
    def run(self):
        while True:
            self.events()
            self.update()
            self.render()

    def create_mgl_texture_from_surface(self, surface):
        surf_data = pg.image.tobytes(surface, "RGBA", True)
        width, height = surface.get_size()
        texture = self.ctx.texture((width, height), 4, data=surf_data)
        texture.build_mipmaps()
        texture.filter = (mgl.LINEAR, mgl.LINEAR)
        texture.repeat_x = False
        texture.repeat_y = False
        return texture, width, height

if __name__ == '__main__':
    eng = Renderer(WIN_RES, 60.0)
    eng.run()
