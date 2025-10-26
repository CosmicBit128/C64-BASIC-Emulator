from settings import *


class Screen:
    def __init__(self, app):
        self.app = app
        self.screen = np.full((40, 25), 32, dtype=np.uint8)
        self.cur_pos = [0, 6]
        self.current_input = ""

        self.write(4, 1, '**** COMMODORE 64 BASIC V2 ****', False)
        self.write(1, 3, '64K RAM SYSTEM  38911 BASIC BYTES FREE', False)
        self.write(0, 5, 'READY.', False)

    def write(self, x, y, text, move_cursor=True):
        for i, char in enumerate(text):
            char = char.upper()
            c=ord(char)
            c = c-64 if c>64 and c<91 else c
            if char == '\n': # New line
                y += 1
                self.cur_pos[1] += 1
                self.cur_pos[0] = 0
                continue
            if c==147: # Clear Screen
                self.screen = np.full((40, 25), 32, dtype=np.uint8)
                self.cur_pos = [0, -1]
                continue
            if x+i > 39:
                y += 1
                self.cur_pos[1] += 1
                self.cur_pos[0] = 0
            else:
                if move_cursor: self.cur_pos[0] += 1
            if y>24:
                self.scroll()
                y -= 1
            if self.cur_pos[1]>24:
                self.scroll()
            self.screen[x+i,y] = c
            if move_cursor: self.current_input += char
    
    def scroll(self):
        # Scroll screen
        self.screen = np.roll(self.screen, -1, 1)
        self.screen[:, -1] = 32
        self.cur_pos[1] -= 1