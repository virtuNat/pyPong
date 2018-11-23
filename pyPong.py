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

    def __init__(self, image=None, rect=None, clip=None):
        super().__init__()
        self.image = image
        if image is not None and rect is None:
            self.rect = self.image.get_rect()
        else:
            self.rect = rect
        if self.rect is not None and clip is None:
            self.clip = self.rect.copy()
            self.clip.topleft = (0, 0)
        else:
            self.clip = clip

    def draw(self, surf):
        surf.blit(self.image, self.rect, self.clip)


class ClipDrawGroup(pg.sprite.OrderedUpdates):
    """Group that accomodates atlas based sprites."""

    def draw(self, surf):
        blitfunc = surf.blit
        for sprite in self.sprites():
            blitfunc(sprite.image, sprite.rect, sprite.clip)


class Ball(ClipDrawSprite):
    """You know, the thing that bounces and is the objective?"""

    def __init__(self, atlas, bounds):
        super().__init__(
            atlas,
            pg.Rect(0, 0, 12, 12),
            pg.Rect(70, 0, 12, 12),
            )
        self.radius = 6
        self.bounds = bounds
        self.rect.center = self.bounds.center

        self.minspe = 1.75
        self.maxspe = 6.25

        self.pos = list(self.bounds.center)
        self.spe = self.minspe
        self.vel = [-1 if randint(0, 1) else 1, 0]

    def collide_paddle(self, paddle):
        dx = self.pos[0] - paddle.pos[0]
        dy = self.pos[1] - paddle.pos[1]
        dist = hypot(dx, dy)
        if paddle.kickon and dist <= self.radius + paddle.kickradius:
            self.vel = [dx / dist, dy / dist]
            self.register_hit(paddle, 0.5)
            paddle.reset_kick()
            return
        rd = self.radius + paddle.radius
        # If the radii do not intersect, there is no collision.
        if dist > rd:
            return
        rx, ry = self.vel
        # Check dot product of velocity to normal.
        nx = dx / dist
        ny = dy / dist
        # Both n and r are unit vectors, the dot product is just cos(w)
        norm = rx * nx + ry * ny
        # Solve for the point to clip to.
        dif1 = -(dx*rx + dy*ry)
        dif2 = (rx*dy - ry*dx)
        disc = sqrt(rd*rd - dif2*dif2)
        # If dot product is positive, ball is moving away from paddle.
        if norm >= 0:
            # Clip to the closer side of the paddle.
            p1 = dif1 + disc
            p2 = dif1 - disc
            para = p1 if abs(p1) < abs(p2) else p2
            self.pos[0] += rx * para
            self.pos[1] += ry * para
            self.rect.center = self.pos
            return
        # Clip to the side of the paddle that forces a backtrack.
        para = dif1 - disc
        self.pos[0] += rx * para
        self.pos[1] += ry * para
        self.rect.center = self.pos
        # Solve for the tangent component, sin(w)
        tngt = ry * nx - rx * ny
        # Flip the normal component and re-sum them into x-y basis.
        self.vel = [
            tngt * -ny - norm * nx,
            tngt * nx - norm * ny,
            ]
        self.register_hit(paddle, 0.125)

    def register_hit(self, paddle, acc):
        # Increase the speed of the ball.
        self.spe += acc
        if self.spe > self.maxspe:
            self.spe = self.maxspe
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
            self.spe = self.minspe
            self.clip.y = 0
        # Update display position.
        self.rect.center = self.pos


class BallTrail(ClipDrawSprite):

    def __init__(self, atlas, ball):
        super().__init__(atlas, ball.rect.copy(), ball.clip.copy())
        self.image.set_alpha(0x3F)

    def update(self, ball):
        self.rect.topleft = ball.rect.topleft
        self.clip.topleft = ball.clip.topleft


class BallGroup(ClipDrawGroup):

    def __init__(self, atlas, bounds, size):
        self.ball = Ball(atlas, bounds)
        self.size = size
        atlas2 = atlas.copy()
        super().__init__(
            *(BallTrail(atlas2, self.ball) for _ in range(size - 1)),
            self.ball,
            )

    def __len__(self):
        return self.size

    def update(self):
        sprites = self.sprites()
        for sp1, sp2 in zip(sprites[:-1], sprites[1:]):
            sp1.update(sp2)
        self.ball.update()


class Paddle(ClipDrawSprite):
    """Player-controlled collision boundaries. Ugh, vectors."""

    def __init__(self, atlas, bounds, side=0):
        self.radius = 35
        self.side = side
        self.bounds = bounds

        super().__init__(
            atlas,
            pg.Rect(0, 0, 35, 70),
            pg.Rect(self.radius * (1 - side), 0, 35, 70),
            )

        self.pos = [side * bounds.w, bounds.centery]
        if side:
            self.rect.midright = self.pos
        else:
            self.rect.midleft = self.pos
        self.dir = 0
        self.vel = 0
        self.spe = 10

        self.kickradius = 90
        self.kicksprite = KickSprite(atlas, bounds, self)
        self.reset_kick()

    def set_movedir(self, movedir):
        if self.vel * movedir > 0:
            self.dir = 0
        else:
            self.dir = movedir

    def set_stopdir(self, stopdir):
        if self.vel * stopdir > 0:
            self.dir = 0

    def set_kick(self):
        if self.kickreset == 0:
            self.kickon = True
            self.kicksprite.set_kick()

    def reset_kick(self):
        self.kickon = False
        self.kickreset = 75
        self.kicktime = 0
        self.clip.top = 2 * self.radius

    def update(self):
        if self.kickon:
            if self.kicktime <= 10:
                self.kicktime += 1
            else:
                self.reset_kick()
        else:
            if self.kickreset > 0:
                self.kickreset -= 1
            else:
                self.clip.top = 0
        # Update position based on velocity.
        self.vel = self.dir * self.spe
        self.pos[1] += self.vel
        # Clip position to the boundary.
        if self.pos[1] < self.bounds.top + self.radius:
            self.pos[1] = self.bounds.top + self.radius
            self.dir = 0
        elif self.pos[1] > self.bounds.bottom - self.radius:
            self.pos[1] = self.bounds.bottom - self.radius
            self.dir = 0
        # Update display position.
        self.rect.centery = self.pos[1]


class KickSprite(ClipDrawSprite):

    def __init__(self, atlas, bounds, paddle):
        super().__init__(
            atlas.subsurface(
                (82 + paddle.kickradius*(1 - paddle.side), 0),
                (paddle.kickradius, 2*paddle.kickradius),
                ),
            None, None
            )
        self.bounds = bounds
        self.paddle = paddle
        self.rectbase = self.rect.copy()
        self.timer = 0
        if paddle.side:
            self.rectbase.midright = paddle.pos
        else:
            self.rectbase.midleft = paddle.pos

    def set_kick(self):
        self.image.set_alpha(200)
        self.timer = 10

    def update(self):
        if self.timer > 0:
            self.image.set_alpha(25 * self.timer)
            self.timer -= 1
        else:
            self.image.set_alpha(0)
        pos = self.paddle.rect.centery
        self.rectbase.centery = pos
        self.rect = self.rectbase.clip(self.bounds)
        self.clip.height = self.rect.height
        if pos < self.bounds.centery:
            self.clip.bottom = self.rectbase.height
        else:
            self.clip.top = 0            


class GameStateHandler(object):
    """Handles the game, self-explanatory."""

    def __init__(self, window):
        self.window = window
        self.rect = self.window.get_rect()
        self.bounds = pg.Rect(0, 205, self.rect.w, 390)
        self.atlas = load_image('atlas.png', colorkey=0xFF00FF)
        self.field = load_image('field.png')

        self.balls = BallGroup(self.atlas, self.bounds, 25)
        self.ball = self.balls.ball
        self.pad1 = Paddle(self.atlas, self.bounds, 0)
        self.pad2 = Paddle(self.atlas, self.bounds, 1)

        self.actors = ClipDrawGroup(
            self.pad1, self.pad2,
            self.pad1.kicksprite, self.pad2.kicksprite,
            )

    async def draw_frame(self):
        """Draw task."""
        self.window.fill((127, 0, 127))
        self.window.blit(self.field, (0, 200))
        self.actors.draw(self.window)
        self.balls.draw(self.window)
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
                    elif event.key == pg.K_d:
                        self.pad1.set_kick()
                    elif event.key == pg.K_UP:
                        self.pad2.set_movedir(-1)
                    elif event.key == pg.K_DOWN:
                        self.pad2.set_movedir(+1)
                    elif event.key == pg.K_LEFT:
                        self.pad2.set_kick()
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
            for _ in range(4):
                self.balls.update()
                if self.ball.pos[0] < self.bounds.width * 0.25:
                    self.ball.collide_paddle(self.pad1)
                elif self.ball.pos[0] > self.bounds.width * 0.75:
                    self.ball.collide_paddle(self.pad2)
            if frame.done():
                frame = aio.ensure_future(self.draw_frame())
            await aio.sleep(frate - (time() - ptime)%frate)
            ptime = time()


def main():
    pg.init()
    pg.display.set_caption('pyPong')
    window = pg.display.set_mode((800, 600), pg.DOUBLEBUF)
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
