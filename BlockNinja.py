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

game_length = 60  # seconds, unenforced maximum 599 (9 min 59 sec), but you will get errors thrown in your face


def blade_effect_sprite():
  return choice(['plf:HudX', 'pzl:Particle' + str(randint(1, 2)), 'spc:Star' + str(randint(1, 3))])


def distance(p0, p1):
  return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)


class Slice(Node):

  def calculate_particle_positions(self, node, duration):
    for i in range(len(self.particles)):
      self.positions[i] = (self.velocities[i][0] + self.positions[i][0],
                           self.velocities[i][1] + self.positions[i][1])
      self.particles[i].position = self.positions[i]
      self.velocities[i] = (self.velocities[i][0] * .99,
                            self.velocities[i][1] - .25)
      self.particles[i].rotation += self.rotational_velocities[i]

  def __init__(self, block, *args, **kwargs):
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
      self.velocities.append((4 * random() - 2, 6 * random() - 2))
      self.rotational_velocities.append(random() - .5)
      sprite.rotation = 2 * math.pi * random()
      self.particles.append(sprite)
    self.run_action(Action.call(self.calculate_particle_positions, 1))
    self.run_action(Action.sequence(Action.wait(1), Action.remove()))


class Game(Scene):

  def draw_score(self):
    score_string = str(self.score)
    for char in self.score_chars:
      char.remove_from_parent()
    self.score_chars = []
    for i in range(len(score_string)):
      self.score_chars.append(SpriteNode('spc:Score' + score_string[i]))
      self.score_chars[-1].position = (32 + i * 24, self.size[1] - 24)
      self.add_child(self.score_chars[-1])

  def draw_time(self):
    t = game_length - int(time() - self.epoch)
    if (t >= 0):
      for char in self.time_chars:
        char.remove_from_parent()
      self.time_chars = []
      if (t >= 60):
        self.time_chars.append(
          SpriteNode(
            'pzl:BallGray',
            position=(self.size[0] - 106, self.size[1] - 18),
            size=(6, 6),
            alpha=.9))
        self.time_chars.append(
          SpriteNode(
            'pzl:BallGray',
            position=(self.size[0] - 106, self.size[1] - 30),
            size=(6, 6),
            alpha=.9))
        self.time_chars.append(
          SpriteNode(
            'spc:Score' + str(t // 60),
            position=(self.size[0] - 146, self.size[1] - 24),
            alpha=.9))

        t %= 60
      t = str(t)
      if (len(t) == 1):
        t = '0' + t
      for i in range(2):
        self.time_chars.append(
          SpriteNode(
            'spc:Score' + t[1 - i],
            position=(self.size[0] - i * 24 - 50, self.size[1] - 24),
            alpha=.9))
      for char in self.time_chars:
        self.add_child(char)
      return 0
    else:
      return t  # game over

  def in_scene(self, position):
    return not (position[0] < 0 or position[1] < 0 or
                position[0] > self.size[0] or position[1] > self.size[1])

  def remove_block(self, removal):
    self.positions.remove(removal[0])
    self.velocities.remove(removal[1])
    removal[2].remove_from_parent()
    self.blocks.remove(removal[2])
    self.rotational_velocities.remove(removal[3])

  def createFruit(self):
    self.blocks.append(
      SpriteNode(
        'pzl:' + (['Blue', 'Gray', 'Green', 'Purple', 'Red', 'Yellow'
                  ][randint(0, 5)]) + str(randint(1, 8)),
        alpha=1))
    self.positions.append((gauss(self.size[0] / 2, self.size[0] / 4),
                           self.size[1] / 8))
    self.blocks[-1].position = self.positions[-1]
    self.add_child(self.blocks[-1])
    self.velocities.append(((self.size[0] / 2 - self.positions[-1][0]) / 20, ((
      (12 * math.sqrt(5 * self.size[1]) - 245) / 40)) * random() + 5))
    self.rotational_velocities.append(random() / 5)

  def createBomb(self):
    self.blocks.append(SpriteNode(bomb_texture, alpha=0.9))
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
    self.epoch = time()
    self.score = 0
    self.score_chars = []
    self.time_chars = []
    self.blocks = []
    self.velocities = []
    self.positions = []
    self.rotational_velocities = []
    self.current_touch_id = None
    self.streak = 0
    self.ticks = 0
    self.text = []
    self.text_age = []
    self.text_pos = []
    self.blade_particles = []
    self.blade_particle_ages = []
    self.background_color = 'black'
    self.matches = []
    self.waiting = False
    [self.createFruit() for i in range(3)]
    self.touchCircle = SpriteNode('shp:Circle', alpha=.9)
    self.touchCircle.size = (touch_radius, touch_radius)
    self.touchCircle.position = self.size / 2
    self.add_child(self.touchCircle)

  def draw(self):
    t = self.draw_time()  # this is somewhat of a hack, but meh
    if (t < 0):
      for child in self.children:
        if (child.alpha <
            1):  # I'm using alpha to differentiate things because it is attached to the sprite, works nixely, and doesn't really affect anything
          child.remove_from_parent()
      for block in self.blocks:
        block.remove_from_parent()
        self.add_child(Slice(block))
      self.blocks = []
      if (t <= -2 and self.matches == [] and not self.waiting):
        self.waiting = True
        name = ''
        with open('block_scores.dat', 'a+') as file:
          while (len(name) > 8 or len(name) < 1):
            name = console.input_alert(
              'Name:',
              message='Must be between 1 and 8 characters',
              hide_cancel_button=True)
          file.write('\n' + name + '\n' + str(self.score))
          file.seek(0)
          self.matches = re.findall(r"^(.*)\n(\d+)",
                                    str(file.read()), re.MULTILINE)
          self.matches.sort(key=(lambda n: -int(n[1])))
      if (t <= -2):
        matches = self.matches
        for i in range(min(len(matches), 10)):
          text(
            '01' [i == 9] + str((i + 1) % 10) + ': ' + matches[i][0] + ' ' *
            (9 - len(matches[i][0])) + matches[i][1],
            font_name='Menlo',
            font_size=16,
            x=self.size[0] / 2,
            y=self.size[1] / 2 + 18 * (4 - i))
    else:
      self.draw_score()
      stroke(255, 255, 255, 250)
      stroke_weight(2)
      to_remove = []
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
        if (random() < bomb_chance):
          self.createBomb()
        else:
          self.createFruit()
      to_remove = []
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

  def touch_began(self, touch):
    if (self.matches != []):
      self.stop()

  def touch_moved(self, touch):
    if (self.current_touch_id == None):
      self.current_touch_id = touch.touch_id
    if (self.current_touch_id == touch.touch_id):
      self.touchCircle.position = touch.location
      if (self.ticks >= 1):
        self.ticks -= 1
      if (self.ticks == 0):
        if (self.streak >= 3):
          self.text.append("Streak! +" + str(self.streak))
          self.text_pos.append((touch.location[0], touch.location[1] + 24))
          self.text_age.append(0)
          self.score += self.streak
        self.streak = 0
      to_remove = []
      if (random() < blade_effect_chance):
        self.blade_particles.append(
          SpriteNode(
            blade_effect_sprite(),
            position=touch.location,
            size=blade_effect_size,
            alpha=.9))
        self.blade_particle_ages.append(0)
        self.add_child(self.blade_particles[-1])
      for i in range(len(self.blocks)):
        if (distance(self.positions[i], touch.location) <= touch_radius):
          to_remove.append([
            self.positions[i], self.velocities[i], self.blocks[i],
            self.rotational_velocities[i]
          ])
      for removal in to_remove:
        if (removal[2].alpha == .9):
          self.score -= 10
          self.text.append("-10")
          self.text_pos.append((touch.location[0], touch.location[1] + 24))
          self.text_age.append(0)
          if (self.score < 0):
            self.score = -1
        else:
          if (random() < crit_chance):
            self.text.append("Crit: +10")
            self.text_pos.append((touch.location[0], touch.location[1] + 24))
            self.text_age.append(0)
            self.score += 10
          self.add_child(Slice(removal[2]))
        self.remove_block(removal)
        self.ticks = streak_ticks
        self.streak += 1
        self.score += 1

  def touch_ended(self, touch):
    if (touch.touch_id == self.current_touch_id):
      self.current_touch_id = None
      if (self.streak >= 3):
        self.text.append("Streak! +" + str(self.streak))
        self.text_pos.append((touch.location[0], touch.location[1] + 24))
        self.text_age.append(0)
        self.score += self.streak
      self.streak = 0
      self.ticks = 0


run(Game(), LANDSCAPE)
