#!/usr/bin/env python
import os

from time import time
from math import copysign, hypot, sqrt
from random import randint
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


class ClipDrawSprite(pg.sprite.Sprite):
    """Sprites that use a clip rectangle to designate its tile in an atlas."""

    def __init__(self):
        super().__init__()
        self.image = None
        self.rect = None
        self.clip = None

    def draw(self, surf):
        surf.blit(self.image, self.rect, self.clip)


class ClipDrawGroup(pg.sprite.Group):
    """Group that accomodates atlas based sprites."""

    def draw(self, surf):
        blitfunc = surf.blit
        for sprite in self.sprites():
            blitfunc(sprite.image, sprite.rect, sprite.clip)


class Ball(ClipDrawSprite):
    """You know, the thing that bounces and is the objective?"""

    def __init__(self, atlas, bounds):
        super().__init__()
        self.radius = 6
        self.bounds = bounds

        self.image = atlas
        self.rect = pg.Rect(0, 0, 12, 12)
        self.clip = pg.Rect(70, 0, 12, 12)
        self.rect.center = self.bounds.center

        self.pos = list(self.bounds.center)
        self.spe = 6
        self.vel = [-1 if randint(0, 1) else 1, 0]

    def collide_paddle(self, paddle):
        dx = self.pos[0] - paddle.pos[0]
        dy = self.pos[1] - paddle.pos[1]
        dist = hypot(dx, dy)
        rd = self.radius + paddle.radius
        # If the radii do not intersect, there is no collision.
        if dist > rd:
            return
        rx, ry = self.vel
        # Solve for the point to clip to.
        dif1 = -(dx*rx + dy*ry)
        dif2 = (rx*dy - ry*dx)
        disc = sqrt(rd*rd - dif2*dif2)
        para = dif1 - disc
        self.pos[0] += rx * para
        self.pos[1] += ry * para
        self.rect.center = self.pos
        # Check dot product of velocity to normal.
        nx = dx / dist
        ny = dy / dist
        norm = rx * nx + ry * ny
        # If dot product is positive, ball is moving away from paddle.
        if norm > 0:
            return
        # Solve for the tangent component.
        tngt = ry * nx - rx * ny
        # Flip the normal component and re-sum them into x-y basis.
        vx = tngt * -ny - norm * nx
        vy = tngt * nx - norm * ny
        # Normalize the result.
        vm = hypot(vx, vy)
        self.vel = [vx / vm, vy / vm]
        # Increase the speed of the ball.
        self.spe += 1
        if self.spe > 12:
            self.spe = 12
        # Change ball color based on which paddle hit it.
        if paddle.side:
            self.clip.y = 4 * self.radius
        else:
            self.clip.y = 2 * self.radius

    def update(self):
        # Update position based on velocity.
        self.pos[0] += self.spe * self.vel[0]
        self.pos[1] += self.spe * self.vel[1]
        # Calculate collision with boundary wall.
        if self.pos[1] < self.bounds.top + self.radius:
            dy = self.bounds.top + self.radius - self.pos[1]
            dx = dy * self.vel[0] / self.vel[1]
            self.pos = [self.pos[0] + dx, self.pos[1] + dy]
            self.vel[1] = abs(self.vel[1])
        elif self.pos[1] > self.bounds.bottom - self.radius:
            dy = self.bounds.bottom - self.radius - self.pos[1]
            dx = dy * self.vel[0] / self.vel[1]
            self.pos = [self.pos[0] + dx, self.pos[1] + dy]
            self.vel[1] = -abs(self.vel[1])
        # Reset if out of bounds.
        if (self.pos[0] < self.bounds.left - self.radius 
            or self.pos[0] > self.bounds.right + self.radius
            ):
            self.pos = list(self.bounds.center)
            self.vel = [copysign(1, self.vel[0]), 0]
            self.spe = 6
            self.clip.y = 0
        # Update display position.
        self.rect.center = self.pos


class Paddle(ClipDrawSprite):
    """Player-controlled collision boundaries. Ugh, vectors."""

    def __init__(self, atlas, bounds, side=0):
        super().__init__()
        self.radius = 35
        self.side = side
        self.bounds = bounds

        self.image = atlas
        self.rect = pg.Rect(0, 0, 35, 70)
        self.clip = pg.Rect(self.radius * (1 - side), 0, 35, 70)

        self.pos = [side * bounds.w, bounds.centery]
        if side:
            self.rect.midright = self.pos
        else:
            self.rect.midleft = self.pos
        self.vel = 0

        self.kickon = False
        self.kicktime = 0
        self.kickradius = 70

    def set_movedir(self, movedir):
        if self.vel * movedir > 0:
            self.vel = 0
        else:
            self.vel = movedir * 6

    def set_stopdir(self, stopdir):
        if self.vel * stopdir > 0:
            self.vel = 0

    def update(self):
        # Update position based on velocity.
        self.pos[1] += self.vel
        # Clip position to the boundary.
        if self.pos[1] < self.bounds.top + self.radius:
            self.pos[1] = self.bounds.top + self.radius
            self.vel = 0
        elif self.pos[1] > self.bounds.bottom - self.radius:
            self.pos[1] = self.bounds.bottom - self.radius
            self.vel = 0
        # Update display position.
        self.rect.centery = self.pos[1]


class Wall(pg.sprite.Sprite):
    def __init__(self, scrsize, side=0):
        super().__init__()
        size = (scrsize[0], 5)
        pos = (0, side * (scrsize[1] - 5))

        self.image = pg.Surface(size)
        self.image.fill(0xA0A0A0)
        self.rect = pg.Rect(pos, size)


class GameStateHandler(object):
    """Handles the game, self-explanatory."""

    def __init__(self, window):
        self.window = window
        self.rect = self.window.get_rect()
        self.bounds = pg.Rect(0, 5, self.rect.w, self.rect.h - 10)
        self.atlas = load_image('atlas.png', colorkey=0xFF00FF)

        self.ball = Ball(self.atlas, self.bounds)
        self.pad1 = Paddle(self.atlas, self.bounds, 0)
        self.pad2 = Paddle(self.atlas, self.bounds, 1)

        self.actors = ClipDrawGroup(
            self.ball, self.pad1, self.pad2
            )
        self.bgwall = pg.sprite.Group(
            Wall(self.rect.size, 0), Wall(self.rect.size, 1)
            )

    async def draw_frame(self):
        """Draw task."""
        self.window.fill((0, 0, 0))
        self.actors.draw(self.window)
        self.bgwall.draw(self.window)
        pg.display.flip()

    async def run(self, fps):
        """Main task, running the game logic and input queue."""
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
            if self.ball.pos[0] < self.bounds.centerx:
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
