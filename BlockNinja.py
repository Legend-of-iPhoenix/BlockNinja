# This is free and unencumbered software released into the public domain.
# 
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
# 
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# 
# For more information, please refer to <http://unlicense.org/>

from scene import *
from random import randint, random, gauss, choice
from time import time
import console
import re
import math

touch_radius = 30
max_blocks = 10
block_chance = 0.02
bomb_chance = 0.1
crit_chance = 0.05
bomb_texture = 'plf:Tile_Bomb'
blade_effect_size = (10, 10)
blade_effect_chance = 1
blade_effect_duration = 25
streak_ticks = 16
text_age_max = 50
crit_particle_boost = 2

game_length = 60  # seconds, unenforced maximum 599 (9 min 59 sec), but you will get errors thrown in your face


# picks a randome particle effect for the blade
def blade_effect_sprite():
  return choice([
    'plf:HudX', 'pzl:Particle' + str(randint(1, 2)),
    'spc:Star' + str(randint(1, 3))
  ])


# self-explanatory
def distance(p0, p1):
  return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)


crit_particle_boost -= 1  # important


# Class for my particle effects when you slice a block.
# Leaving the explanation up to the reader, because you might learn something and because I'm lazy
class Slice(Node):
  # recalculates particle positions (go figure)
  def calculate_particle_positions(self, node, duration):
    for i in range(len(self.particles)):
      self.positions[i] = (self.velocities[i][0] + self.positions[i][0],
                           self.velocities[i][1] + self.positions[i][1])
      self.particles[i].position = self.positions[i]
      self.velocities[i] = (self.velocities[i][0] * .99,
                            self.velocities[i][1] - .25)
      self.particles[i].rotation += self.rotational_velocities[i]

  # block is the block being destroyed, is_crit is 0 if the slice was not a critical hit, 1 otherwise
  def __init__(self, block, is_crit, *args, **kwargs):
    self.particles = []
    self.velocities = []
    self.positions = []
    self.rotational_velocities = []
    Node.__init__(self, *args, **kwargs)
    self.position = block.position
    for i in range(randint(3, 5)):
      sprite = SpriteNode(block.texture, scale=0.33, parent=self)
      sprite.position = (block.size.w * random() - (block.size.w / 2),
                         block.size.h * random() - (block.size.h / 2))
      self.positions.append(sprite.position)
      self.velocities.append([
        value * (1 + is_crit * crit_particle_boost)
        for value in (4 * random() - 2, 6 * random() - 2)
      ])
      self.rotational_velocities.append(random() - .5)
      sprite.rotation = 2 * math.pi * random()
      self.particles.append(sprite)
    self.run_action(
      Action.call(self.calculate_particle_positions, 1 +
                  is_crit * crit_particle_boost))
    self.run_action(
      Action.sequence(
        Action.wait(1 + is_crit * crit_particle_boost), Action.remove()))


# Main game scene
class Game(Scene):

  # draws the score in the top left corner
  def draw_score(self):
    score_string = str(self.score)
    for char in self.score_chars:
      char.remove_from_parent()
    self.score_chars = []
    for i in range(len(score_string)):
      self.score_chars.append(SpriteNode('spc:Score' + score_string[i]))
      self.score_chars[-1].position = (32 + i * 24, self.size[1] - 24)
      self.add_child(self.score_chars[-1])

  # draws remaining time
  def draw_time(self):
    t = game_length - int(time() - self.epoch)
    f = t
    if (t >= 0):
      for char in self.time_chars:
        char.remove_from_parent()
      self.time_chars = []
      if (t >= 60):
        for i in (
            18, 30
        ):  # 18 = top ball in colon dividing minutes and seconds, 30 = bottom
          self.time_chars.append(
            SpriteNode(
              'pzl:BallGray',
              position=(self.size[0] - 106, self.size[1] - i),
              size=(6, 6),
              alpha=.9))
        # minutes
        self.time_chars.append(
          SpriteNode(
            'spc:Score' + str(t // 60),
            position=(self.size[0] - 146, self.size[1] - 24),
            alpha=.9))

        t %= 60
      t = str(t)
      if (len(t) == 1):
        t = '0' + t  # pad start with 0
      for i in range(2):
        self.time_chars.append(
          SpriteNode(
            'spc:Score' + t[1 - i],
            position=(self.size[0] - i * 24 - 50, self.size[1] - 24),
            alpha=.9,
            color=("red" if f <= 20 and f % 2 else
                   "white")))  # this does red flashy thing at end
      for char in self.time_chars:
        self.add_child(char)
    return t  # so external things know when to stopc

  # returns a boolean that represents whether a point is in the scene
  def in_scene(self, position):
    return not (position[0] < 0 or position[1] < 0 or
                position[0] > self.size[0] or position[1] > self.size[1])

  # removes a block
  def remove_block(self, removal):
    self.positions.remove(removal[0])
    self.velocities.remove(removal[1])
    removal[2].remove_from_parent()
    self.blocks.remove(removal[2])
    self.rotational_velocities.remove(removal[3])

  # creates a block
  def createBlock(self):
    self.blocks.append(
      SpriteNode(
        'pzl:' + (['Blue', 'Gray', 'Green', 'Purple', 'Red', 'Yellow'
                  ][randint(0, 5)]) + str(randint(1, 8)),
        alpha=1))  # essentially picks a color then picks a shape
    self.positions.append((gauss(self.size[0] / 2, self.size[0] / 4),
                           self.size[1] / 8))
    self.blocks[-1].position = self.positions[-1]
    self.add_child(self.blocks[-1])
    self.velocities.append(
      ((self.size[0] / 2 - self.positions[-1][0]) / 20, ((
        (12 * math.sqrt(5 * self.size[1]) - 245) / 40)) * random() +
       5))  # the y velocity part lets us scale onto larger screens
    # it's quite a bit of "simple" math to get there
    self.rotational_velocities.append(random() / 5)

  # creates a bomb
  def createBomb(self):
    self.blocks.append(SpriteNode(
      bomb_texture, alpha=
      0.9))  # I am using alpha values to differentiate between bombs/blocks
    # bit of a hack, but hey, it works
    self.positions.append((gauss(self.size[0] / 2, self.size[0] / 4),
                           self.size[1] / 8))
    self.blocks[-1].position = self.positions[-1]
    self.add_child(self.blocks[-1])
    self.velocities.append(((self.size[0] / 2 - self.positions[-1][0]) / 20, (
      (12 * math.sqrt(5 * self.size[1]) - 245) / 40) * random() + 5))
    self.rotational_velocities.append(random() / 5)

  def setup(self):
    # print("============")
    # print(" Game Begin ")
    # print("============")
    self.epoch = time()  # time game starts
    self.score = 0  # score
    self.score_chars = []  # holds the sprites for the score
    self.time_chars = []  # holds sprites for clock
    self.blocks = []  # holds sprites for blocks
    self.velocities = []  # holds velocities of blocks
    self.positions = []  # holds list of block positions
    self.rotational_velocities = []  # list of rotational speeed
    self.current_touch_id = None  # prevents multiple touches from messing with things
    self.streak = 0  # holds the current streak
    self.ticks = 0  # holds countdown until streak ends; reset to streak_ticks when block is scored
    self.text = []  # holds a list of the strings needing to be draw
    self.text_age = [
    ]  # list of text ages, when a text's age is greater than text_age_max, it despawns
    self.text_pos = []  # list of text positions
    self.blade_particles = []  # list of blade particle sprites
    self.blade_particle_ages = []  # list of blade particle ages
    self.background_color = 'black'
    self.matches = []  # for highscores
    self.waiting = False  # for endgame, prevents crashes
    self.touchCircle = SpriteNode(
      'shp:Circle',
      alpha=.9,
      size=(touch_radius, touch_radius),
      position=self.size / 2,
      parent=self
    )  # shows the effective radius of the blade. Intended to be a debug feature, but the game is too hard for me anyways.

  # draw loop, automatically called
  def draw(self):
    t = self.draw_time()  # this is somewhat of a hack, but meh
    if (t < 0):  # if there is no time left
      for child in self.children:
        if (child.alpha <
            1):  # I'm using alpha to differentiate things because it is attached to the sprite, works nixely, and doesn't really affect anything
          child.remove_from_parent()
      for block in self.blocks:
        block.remove_from_parent()
        self.add_child(
          Slice(block, 1)
        )  # make all of the blocks currently on screen explode as if they were hit with a crit
      self.blocks = []  # prevents particle flood
      if (t <= -2 and self.matches == [] and not self.waiting):
        self.waiting = True  # basically says, only run this once
        name = ''  # highscore username
        with open('block_scores.dat', 'a+') as file:  # open highscores file
          while (len(name) > 8 or len(name) < 1):
            name = console.input_alert(
              'Name:',
              message='Must be between 1 and 8 characters',
              hide_cancel_button=True)  # input validation
          file.write('\n' + name + '\n' +
                     str(self.score))  # write name and highscore at end of file
          file.seek(0)  # go to beginning of file 
          self.matches = re.findall(
            r"^(.*)\n(\d+)", str(file.read()),
            re.MULTILINE)  # find all of the name/value pairs
          self.matches.sort(
            key=(lambda n: -int(n[1])
                ))  # sort such that biggest is first, this is a bit of a hack
      if (t <=
          ~crit_particle_boost):  # it takes 1 second plus whatever the crit velocity boost is, but we are in "overtime" so it's negative. This works out to be equal to the two's compliment, -1-x
        matches = self.matches  # you have endured so much, take a break from this crazy code
        for i in range(min(len(matches), 10)):
          text(
            '01' [i == 9] + str((i + 1) % 10) + ': ' + matches[i][0] + ' ' *
            (9 - len(matches[i][0])) +
            matches[i][1],  # lol you thought I was serious
            font_name='Menlo',
            font_size=16,
            x=self.size[0] / 2,
            y=self.size[1] / 2 + 18 * (4 - i))
    else:
      self.draw_score()
      stroke(255, 255, 255, 250)  # note the alpha value of not 100%
      stroke_weight(2)
      to_remove = [
      ]  # I remove after I iterate because it gets even more messy if I don't
      for i in range(len(self.blocks)):
        self.positions[i] = (self.velocities[i][0] + self.positions[i][0],
                             self.velocities[i][1] + self.positions[i][1])
        self.blocks[i].position = self.positions[i]
        self.velocities[i] = (self.velocities[i][0] * .99,
                              self.velocities[i][1] - .25)
        self.blocks[i].rotation += self.rotational_velocities[i]
        if (not self.in_scene(self.positions[i])):
          to_remove.append([
            self.positions[i], self.velocities[i], self.blocks[i],
            self.rotational_velocities[i]
          ])
      for removal in to_remove:
        self.remove_block(removal)
      if (random() < block_chance and len(self.blocks) < max_blocks):
        if (random() < bomb_chance):  # this might be the cleanest code in here
          self.createBomb()
        else:
          self.createBlock()
      to_remove = []
      # </cleanest code in here>
      for i in range(len(self.blade_particles)):
        self.blade_particle_ages[i] += 1
        if (self.blade_particle_ages[i] > blade_effect_duration):
          to_remove.append(
            [self.blade_particle_ages[i], self.blade_particles[i]])
        else:
          if (i < len(self.blade_particles) - 3):
            line(self.blade_particles[i].position[0],
                 self.blade_particles[i].position[1],
                 self.blade_particles[i + 1].position[0],
                 self.blade_particles[i + 1].position[1])
      for removal in to_remove:
        removal[1].remove_from_parent()
        self.blade_particle_ages.remove(removal[0])
        self.blade_particles.remove(removal[1])
      # For your reference, this it what it looks like without the to_repeat function. It's actually surprisingly neat. Unfortunately, there are several reasons why I cannot do this with the others.
      i = 0
      while (i < len(self.text)):
        if (self.text_age[i] < text_age_max):
          text(
            self.text[i],
            font_name='Futura',
            font_size=16,
            x=self.text_pos[i][0],
            y=self.text_pos[i][1])
          self.text_age[i] += 1
        else:
          del self.text[i]
          del self.text_pos[i]
          del self.text_age[i]
          i -= 1
        i += 1

  # only applies at the end
  def touch_began(self, touch):
    if (
        self.matches !=
      []):  # if our matches (highscores) array has been populated and we clicked,
      self.stop()  # just... stop.

  # This looks like a mess, but it really isn't.
  def touch_moved(self, touch):
    if (self.current_touch_id ==
        None):  # if we don't already have a finger/paw/tentacle/nose on the screen
      self.current_touch_id = touch.touch_id  # ensure that we can identify said finger/paw/tentacle/nose later.
    if (self.current_touch_id == touch.
        touch_id):  # if the touch event we are recieving matches up with the one we want,
      self.touchCircle.position = touch.location  # move the front of the blade thing
      if (self.ticks >= 1):  # if there is still time to increase the streak
        self.ticks -= 1  # shorten thst timr
      if (self.ticks == 0):  # if there is no more time
        if (self.streak >= 3):  # and we did more than 2 fruits
          # announce that we got a streak:
          self.text.append("Streak! +" + str(self.streak))
          self.text_pos.append((touch.location[0], touch.location[1] + 24))
          self.text_age.append(0)
          self.score += self.streak  # add to the score
        self.streak = 0  # reset score
      to_remove = []
      if (random() <
          blade_effect_chance):  # if we should place a blade particle
        self.blade_particles.append(
          SpriteNode(
            blade_effect_sprite(),
            position=touch.location,
            size=blade_effect_size,
            alpha=.9))
        self.blade_particle_ages.append(0)
        self.add_child(self.blade_particles[-1])
        # place a blade particle ^^
      for i in range(
          len(self.blocks)):  # iterate through all of the blocks on-screen
        if (distance(self.positions[i], touch.location) <=
            touch_radius):  # if there is a collidion
          to_remove.append([ # prepare to remove the block
            self.positions[i], self.velocities[i], self.blocks[i],
            self.rotational_velocities[i]
          ])
      for removal in to_remove:  # with each removal
        if (removal[2].alpha == .9):  # if the sprite's alpha is .9 (aka a bomb)
          self.score -= 10  # decrease score
          self.text.append("-10")  # display it, too.
          self.text_pos.append((touch.location[0], touch.location[1] + 24))
          self.text_age.append(0)
          if (self.score <
              0):  # ensure score is never less than zero, because we don't have a sprite for the negative sign
            self.score = -1
        else:
          if (random() <
              crit_chance):  # if it is not a bomb, give random chance for the collision to be a crit 
            self.text.append("Crit: +10")  # display it
            self.text_pos.append((touch.location[0], touch.location[1] + 24))
            self.text_age.append(0)
            self.score += 10  # do it
            self.add_child(
              Slice(removal[2],
                    1))  # givd the particles extra velocity (second argument)
          else:
            self.add_child(Slice(removal[2], 0))
        self.remove_block(removal)
        self.ticks = streak_ticks  # reset ticks cuz we hit something
        self.streak += 1  # increase streak
        self.score += 1  # increase score

  def touch_ended(self, touch):  # if a finger/paw/tentacle/nose lifted off:
    if (touch.touch_id ==
        self.current_touch_id):  # if it was the one we were tracking
      self.current_touch_id = None  # mark us as "open for business"
      # I like to imagine this is done somewhat reluctantly, as if our "Python" lost a good friend
      if (self.streak >= 3):  # if there was a streak, show it
        self.text.append("Streak! +" + str(self.streak))
        self.text_pos.append((touch.location[0], touch.location[1] + 24))
        self.text_age.append(0)
        self.score += self.streak  # do it
      self.streak = 0  # reset
      self.ticks = 0


run(Game(), LANDSCAPE)  # run the game

# I'm sorry

