import pygame as pg
from settings import *

class KeyboardHandler:
    def __init__(self, app):
        self.app = app
        self.post = app.post

    def keydown_callback(self, e):
        if e.key == pg.K_RETURN:
            self.app.screen.cur_pos[1] += 1
            self.app.screen.cur_pos[0] = 0
            self.app.inter.input_line(self.app.screen.current_input)
            self.app.screen.current_input = ""

        elif e.key == pg.K_BACKSPACE:
            p = self.app.screen.cur_pos
            p[0]-=1
            self.app.screen.write(*p, ' ')
            self.app.screen.current_input = self.app.screen.current_input[:-2]
            if self.app.screen.cur_pos[0]>0:
                self.app.screen.cur_pos[0] -= 1
            else:
                self.app.screen.cur_pos[0] = 39
                self.app.screen.cur_pos[1] -= 1

        elif e.key == pg.K_UP and self.app.screen.cur_pos[1]>0:
            self.app.screen.cur_pos[1] -= 1
        elif e.key == pg.K_LEFT and self.app.screen.cur_pos[0]>0:
            self.app.screen.cur_pos[0] -= 1
        elif e.key == pg.K_DOWN and self.app.screen.cur_pos[1]<24:
            self.app.screen.cur_pos[1] += 1
        elif e.key == pg.K_RIGHT and self.app.screen.cur_pos[0]<39:
            self.app.screen.cur_pos[0] += 1

        elif e.key == pg.K_HOME:
            self.app.screen.cur_pos[0] = 0
        # elif e.key == pg.K_END:
        #     l = 40
        #     for i in range(40):
        #         if self.app.screen.screen[i, self.app.screen.cur_pos[1]] != 32:
        #             break
        #     self.app.screen.cur_pos[0] = l
        
        elif e.key == pg.K_PAUSE:
            self.post.ce = not self.post.ce

        elif e.key in [pg.K_LSHIFT, pg.K_RSHIFT, pg.K_CAPSLOCK, pg.K_LCTRL, pg.K_RCTRL, pg.K_LALT, pg.K_RALT, pg.K_KP_PLUS, pg.K_KP_MINUS]:
            pass

        else:
            self.app.screen.write(*self.app.screen.cur_pos, e.unicode)
            if self.app.screen.cur_pos[0]>39:
                self.app.screen.cur_pos[0] = 0
                self.app.screen.cur_pos[1] += 1