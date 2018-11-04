#!/usr/bin/env python
from time import time
from math import hypot, cos, sin
from operator import add, sub, mul
import asyncio as aio
import pygame as pg

class Ball(pg.sprite.Sprite):
    def __init__(self, radius=6):
        super().__init__()
        self.radius = radius
        size = (2 * radius,) * 2
        pos = (300 - radius, 150 - radius)

        self.image = pg.Surface(size)
        self.image.fill(0xC8C8C8)

        self.rect = pg.Rect(pos, size)
        self.pos = list(self.rect.center)
        self.spe = 5
        self.vel = [-1, 0]

    def collide_paddle(self, paddle):
        dx = self.pos[0] - paddle.side * 600
        dy = self.pos[1] - paddle.pos
        dist = hypot(dx, dy)
        if dist > self.radius + paddle.radius:
            return
        nx = dx / dist
        ny = dy / dist
        rx, ry = self.vel
        norm = rx * nx + ry * ny
        if norm > 0:
            return
        tngt = ry * nx - rx * ny
        vx = tngt * -ny - norm * nx
        vy = tngt * nx - norm * ny
        vm = hypot(vx, vy)
        self.vel = [vx / vm, vy / vm]
        self.spe += 1
        if self.spe > 12:
            self.spe = 12

    def update(self):
        self.pos = list(map(lambda p, v: p + self.spe * v, self.pos, self.vel))
        if self.pos[1] < 5 + self.radius:
            self.vel[1] = abs(self.vel[1])
        elif self.pos[1] > 295 - self.radius:
            self.vel[1] = -abs(self.vel[1])
        if self.pos[0] < 0 - self.radius or self.pos[0] > 600 + self.radius:
            self.pos = [300 - self.radius, 150 - self.radius]
            self.vel = [self.vel[0] / abs(self.vel[0]), 0]
            self.spe = 5
        self.rect.center = self.pos

    def draw(self, surf):
        surf.blit(self.image, self.rect)


class Paddle(pg.sprite.Sprite):
    def __init__(self, side=0, radius=35):
        super().__init__()
        self.side = side
        self.radius = radius

        scrsize = pg.display.get_surface().get_size()
        size = (radius, 2 * radius)
        pos = (side * (scrsize[0] - radius), 150 - radius)

        self.image = pg.Surface(size)
        self.image.fill(
            0x0000FF if side else 0xFF0000
            )
        self.rect = pg.Rect(pos, size)

        self.pos = scrsize[1] / 2
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
        self.pos += self.vel
        if self.pos < 5 + self.radius:
            self.pos = 5 + self.radius
            self.vel = 0
            # self.acc = 0
        elif self.pos > 295 - self.radius:
            self.pos = 295 - self.radius
            self.vel = 0
            # self.acc = 0
        self.rect.centery = self.pos

    def draw(self, surf):
        surf.blit(self.image, self.rect)


class Wall(pg.sprite.Sprite):
    def __init__(self, side=0):
        super().__init__()
        scrsize = pg.display.get_surface().get_size()
        size = (scrsize[0], 5)
        pos = (0, side * (scrsize[1] - 5))

        self.image = pg.Surface(size)
        self.image.fill(0xA0A0A0)
        self.rect = pg.Rect(pos, size)


class GameStateHandler(object):
    def __init__(self, window):
        self.window = window

        self.ball = Ball()
        self.pad1 = Paddle(0)
        self.pad2 = Paddle(1)

        self.actors = pg.sprite.Group(
            self.ball, self.pad1, self.pad2
            )
        self.bgwall = pg.sprite.Group(
            Wall(0), Wall(1)
            )

    async def draw_frame(self):
        self.window.fill((0, 0, 0))
        self.actors.draw(self.window)
        self.bgwall.draw(self.window)
        pg.display.flip()

    async def run(self):
        frate = 0.9375/60
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
        aloop.run_until_complete(game_state.run())
    except KeyboardInterrupt:
        pass
    except Exception:
        raise
    finally:
        aloop.close()
        pg.quit()

if __name__ == '__main__':
    main()
