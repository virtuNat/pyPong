#!/usr/bin/env python
import os

from time import time
from math import copysign, hypot
from operator import add, sub, mul

import asyncio as aio
import pygame as pg

def load_image (name, alpha=None, colorkey=None):
    """Load an image file into memory."""
    try:
        image = pg.image.load(os.path.join('textures', name))
    except pg.error:
        print('Image loading failed: ')
        raise
    if alpha is None:
        image = image.convert()
        if colorkey is not None:
            image.set_colorkey(colorkey)
        return image
    return image.convert_alpha()


class ClipDrawGroup(pg.sprite.Group):

    def draw(self, surf):
        for sprite in self.sprites():
            surf.blit(sprite.image, sprite.rect, sprite.clip)


class Ball(pg.sprite.Sprite):
    """Ball"""

    def __init__(self, atlas, bounds):
        super().__init__()
        self.radius = 6
        self.bounds = bounds

        self.image = atlas
        self.clip = pg.Rect(70, 0, 12, 12)
        self.rect = pg.Rect(0, 0, 12, 12)
        self.rect.center = self.bounds.center

        self.pos = list(self.bounds.center)
        self.spe = 5
        self.vel = [-1, 0]

    def collide_paddle(self, paddle):
        dx = self.pos[0] - paddle.pos[0]
        dy = self.pos[1] - paddle.pos[1]
        dist = hypot(dx, dy)
        if dist > self.radius + paddle.radius:
            return
        nx = dx / dist
        ny = dy / dist
        rx = self.vel[0]
        ry = self.vel[1] - paddle.vel
        norm = rx * nx + ry * ny
        if norm > 0:
            return
        tngt = ry * nx - rx * ny
        vx = tngt * -ny - norm * nx
        vy = paddle.vel + tngt * nx - norm * ny
        vm = hypot(vx, vy)
        self.vel = [vx / vm, vy / vm]
        self.spe += 1
        if self.spe > 12:
            self.spe = 12
        if paddle.side:
            self.clip.top = 4 * self.radius
        else:
            self.clip.top = 2 * self.radius

    def update(self):
        self.pos = list(map(lambda p, v: p + self.spe * v, self.pos, self.vel))
        if self.pos[1] < 5 + self.radius:
            self.vel[1] = abs(self.vel[1])
        elif self.pos[1] > 295 - self.radius:
            self.vel[1] = -abs(self.vel[1])
        if self.pos[0] < 0 - self.radius or self.pos[0] > 600 + self.radius:
            self.pos = list(self.bounds.center)
            self.vel = [copysign(1, self.vel[0]), 0]
            self.spe = 5
            self.clip.top = 0
        self.rect.center = self.pos

    def draw(self, surf):
        surf.blit(self.image, self.rect)


class Paddle(pg.sprite.Sprite):
    def __init__(self, atlas, scrsize, side=0):
        super().__init__()
        self.radius = 35
        self.side = side

        self.image = atlas
        self.rect = pg.Rect(0, 0, 35, 70)
        self.clip = pg.Rect(self.radius * (1 - side), 0, 35, 70)

        self.pos = [side * scrsize[0], scrsize[1] / 2]
        if side:
            self.rect.midright = self.pos
        else:
            self.rect.midleft = self.pos
        self.vel = 0
        # self.acc = 0

    def set_movedir(self, movedir):
        if self.vel * movedir > 0:
            self.vel = 0
        else:
            self.vel = movedir * 6

    def set_stopdir(self, stopdir):
        if self.vel * stopdir > 0:
            self.vel = 0

    def update(self):
        self.pos[1] += self.vel
        if self.pos[1] < 5 + self.radius:
            self.pos[1] = 5 + self.radius
            self.vel = 0
            # self.acc = 0
        elif self.pos[1] > 295 - self.radius:
            self.pos[1] = 295 - self.radius
            self.vel = 0
            # self.acc = 0
        self.rect.centery = self.pos[1]

    def draw(self, surf):
        surf.blit(self.image, self.rect)


class Wall(pg.sprite.Sprite):
    def __init__(self, scrsize, side=0):
        super().__init__()
        size = (scrsize[0], 5)
        pos = (0, side * (scrsize[1] - 5))

        self.image = pg.Surface(size)
        self.image.fill(0xA0A0A0)
        self.rect = pg.Rect(pos, size)


class GameStateHandler(object):
    def __init__(self, window):
        self.window = window
        self.rect = self.window.get_rect()
        self.atlas = load_image('atlas.png', colorkey=0xFF00FF)

        self.ball = Ball(self.atlas, self.rect)
        self.pad1 = Paddle(self.atlas, self.rect.size, 0)
        self.pad2 = Paddle(self.atlas, self.rect.size, 1)

        self.actors = ClipDrawGroup(
            self.ball, self.pad1, self.pad2
            )
        self.bgwall = pg.sprite.Group(
            Wall(self.rect.size, 0), Wall(self.rect.size, 1)
            )

    async def draw_frame(self):
        self.window.fill((0, 0, 0))
        self.actors.draw(self.window)
        self.bgwall.draw(self.window)
        pg.display.flip()

    async def run(self, fps):
        frate = 0.9375 / fps
        ptime = time()
        frame = aio.ensure_future(self.draw_frame())
        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_w:
                        self.pad1.set_movedir(-1)
                    elif event.key == pg.K_s:
                        self.pad1.set_movedir(+1)
                    elif event.key == pg.K_UP:
                        self.pad2.set_movedir(-1)
                    elif event.key == pg.K_DOWN:
                        self.pad2.set_movedir(+1)
                elif event.type == pg.KEYUP:
                    if event.key == pg.K_w:
                        self.pad1.set_stopdir(-1)
                    elif event.key == pg.K_s:
                        self.pad1.set_stopdir(+1)
                    elif event.key == pg.K_UP:
                        self.pad2.set_stopdir(-1)
                    elif event.key == pg.K_DOWN:
                        self.pad2.set_stopdir(+1)
            self.actors.update()
            if self.ball.pos[0] < 300:
                self.ball.collide_paddle(self.pad1)
            else:
                self.ball.collide_paddle(self.pad2)
            if frame.done():
                frame = aio.ensure_future(self.draw_frame())
            await aio.sleep(frate - (time() - ptime)%frate)
            ptime = time()


def main():
    pg.init()
    pg.display.set_caption('pyPong')
    window = pg.display.set_mode((600, 300), pg.DOUBLEBUF)
    game_state = GameStateHandler(window)

    aloop = aio.get_event_loop()
    try:
        aloop.run_until_complete(game_state.run(60))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        raise RuntimeError('(╯°□°)╯︵ ┻━┻') from exc
    finally:
        aloop.close()
        pg.quit()

if __name__ == '__main__':
    main()
