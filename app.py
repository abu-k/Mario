"""
Simple 2d world where the player can interact with the items in the world.
"""

from game.util import get_collision_direction

__author__ = "Youcef Mesbah 42349343"
__date__ = "18 October 2019"
__version__ = "1.1.0"
__copyright__ = "The University of Queensland, 2019"

import math
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import Tuple, List
import sys
import pymunk
import os

from game.block import Block, MysteryBlock
from game.entity import Entity
from game.item import DroppedItem, Coin
from game.mob import Mob, CloudMob, Fireball
from game.view import GameView, ViewRenderer
from game.world import World
from level import load_world, WorldBuilder
from player import Player

BLOCK_SIZE = 2 ** 4
MAX_WINDOW_SIZE = (1080, math.inf)
JUMP_SIZE = 10

GOAL_SIZES = {
    "flag": (0.2, 9),
    "tunnel": (2, 2)
}
TIMING = {
    "invincibility" : 10000,
    "switch": 1000
}

BLOCKS = {
    '#': 'brick',
    '%': 'brick_base',
    '?': 'mystery_empty',
    '$': 'mystery_coin',
    '^': 'cube',
    'b': 'bounce_block',
    'I': 'flag',
    '=': 'tunnel',
    'S': 'switch'
}

ITEMS = {
    'C': 'coin',
    '*': 'star'
}

MOBS = {
    '&': "cloud",
    '@': "mushroom"
}


def create_block(world: World, block_id: str, x: int, y: int, *args):
    """Create a new block instance and add it to the world based on the block_id.

    Parameters:
        world (World): The world where the block should be added to.
        block_id (str): The block identifier of the block to create.
        x (int): The x coordinate of the block.
        y (int): The y coordinate of the block.
    """
    block_id = BLOCKS[block_id]
    if block_id == "mystery_empty":
        block = MysteryBlock()
    elif block_id == "mystery_coin":
        block = MysteryBlock(drop="coin", drop_range=(3, 6))
    elif block_id == "tunnel":
        block = Tunnel()
    elif block_id == "flag":
        block = Flag()
    elif block_id == "switch":
        block = Switch()
    else:
        block = Block(block_id)

    world.add_block(block, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_item(world: World, item_id: str, x: int, y: int, *args):
    """Create a new item instance and add it to the world based on the item_id.

    Parameters:
        world (World): The world where the item should be added to.
        item_id (str): The item identifier of the item to create.
        x (int): The x coordinate of the item.
        y (int): The y coordinate of the item.
    """
    item_id = ITEMS[item_id]
    if item_id == "coin":
        item = Coin()
    elif item_id == "star":
        item = Star()
    else:
        item = DroppedItem(item_id)

    world.add_item(item, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_mob(world: World, mob_id: str, x: int, y: int, *args):
    """Create a new mob instance and add it to the world based on the mob_id.

    Parameters:
        world (World): The world where the mob should be added to.
        mob_id (str): The mob identifier of the mob to create.
        x (int): The x coordinate of the mob.
        y (int): The y coordinate of the mob.
    """
    mob_id = MOBS[mob_id]
    if mob_id == "cloud":
        mob = CloudMob()
    elif mob_id == "fireball":
        mob = Fireball()
    elif mob_id == "mushroom":
        mob = Mushroom()
    else:
        mob = Mob(mob_id, size=(1, 1))

    world.add_mob(mob, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_unknown(world: World, entity_id: str, x: int, y: int, *args):
    """Create an unknown entity."""
    world.add_thing(Entity(), x * BLOCK_SIZE, y * BLOCK_SIZE,
                    size=(BLOCK_SIZE, BLOCK_SIZE))


BLOCK_IMAGES = {
    "brick": "brick",
    "brick_base": "brick_base",
    "cube": "cube",
    "bounce_block": "bounce_block",
    "tunnel": "tunnel",
    "flag": "flag",
    "switch": "switch",
    "switch_pressed": "switch_pressed"
}

ITEM_IMAGES = {
    "coin": "coin_item",
    "star": "star"
}

MOB_IMAGES = {
    "cloud": "floaty",
    "fireball": "fireball_down",
    "mushroom": "mushroom"
}


class MarioViewRenderer(ViewRenderer):
    """A customised view renderer for a game of mario."""

    @ViewRenderer.draw.register(Player)
    def _draw_player(self, instance: Player, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:

        if shape.body.velocity.x >= 0:

            image = self.load_image(instance.get_name() + "_right")
        else:
            image = self.load_image(instance.get_name() + "_left")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="player")]

    @ViewRenderer.draw.register(MysteryBlock)
    def _draw_mystery_block(self, instance: MysteryBlock, shape: pymunk.Shape,
                            view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_active():
            image = self.load_image("coin")
        else:
            image = self.load_image("coin_used")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]

    # @ViewRenderer.draw.register(Switch)
    # def _draw_switch(self, instance: Switch, shape: pymunk.Shape,
    #                         view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
    #     if instance.is_active():
    #         image = self.load_image("switch")
    #     else:
    #         image = self.load_image("switch_pressed")
    #
    #     return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
    #                               image=image, tags="block")]


class MarioApp:
    """High-level app class for Mario, a 2d platformer"""

    _world: World

    def __init__(self, master: tk.Tk):
        """Construct a new game of a MarioApp game.

        Parameters:
            master (tk.Tk): tkinter root widget
        """
        self._master = master
        self.load_config()

        self.invincibility = False
        self._on_tunnel = False

        world_builder = WorldBuilder(BLOCK_SIZE, gravity=(0, self.global_gravity), fallback=create_unknown)
        world_builder.register_builders(BLOCKS.keys(), create_block)
        world_builder.register_builders(ITEMS.keys(), create_item)
        world_builder.register_builders(MOBS.keys(), create_mob)
        self._builder = world_builder

        self._player = Player(max_health=self.health, name=self.character)
        self.reset_world(self.current_level)

        self._renderer = MarioViewRenderer(BLOCK_IMAGES, ITEM_IMAGES, MOB_IMAGES)

        size = tuple(map(min, zip(MAX_WINDOW_SIZE, self._world.get_pixel_size())))
        self._view = GameView(self._master, size, self._renderer)
        self._view.pack()
        self.bind()

        # Wait for window to update before continuing
        self._master.update_idletasks()
        self.step()

        menubar = tk.Menu(self._master)
        self._master.config(menu=menubar)
        file_menu = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=file_menu)  # tell menubar what its menu is
        file_menu.add_command(label="Load Level", command=self.menu_load_level)
        file_menu.add_command(label="Reset Level", command=self.menu_reset_level)
        file_menu.add_command(label="Exit", command=self.menu_exit)
        self.create_status_bar()
        self.highscore()


    def load_config(self):
        """
        Inputs config data from config file
        """
        self.config_filename = input("What is the filename of the configuration file?")
        try:
            with open(self.config_filename) as f:
                content = f.readlines()
            self.config = {}
            for line in content:
                line = line.strip("\n")
                if line.startswith("=="):
                    current_line = line
                    self.config[current_line] = []
                else:
                    self.config[current_line].append(line)

            for config_data in self.config.keys():
                if config_data == "==World==":
                    # Gets world data
                    for world_data in self.config["==World=="]:
                        if world_data.startswith("gravity"):
                            self.global_gravity = int(world_data.split(":")[-1].strip(" "))
                        if world_data.startswith("start"):
                            self.current_level = world_data.split(":")[-1].strip(" ")
                if config_data == "==Player==":
                    # Gets player data
                    for player_data in self.config["==Player=="]:
                        if player_data.startswith("character"):
                            self.character = player_data.split(":")[-1].strip(" ")
                        if player_data.startswith("x"):
                            self.x_start = int(player_data.split(":")[-1].strip(" "))
                        if player_data.startswith("y"):
                            self.y_start = int(player_data.split(":")[-1].strip(" "))
                        if player_data.startswith("mass"):
                            self.mass = int(player_data.split(":")[-1].strip(" "))
                        if player_data.startswith("health"):
                            self.health = int(player_data.split(":")[-1].strip(" "))
                        if player_data.startswith("max_velocity"):
                            self.max_velocity = int(player_data.split(":")[-1].strip(" "))
        except:
            # Closes the program if wrong config
            message = messagebox.showinfo("Information", "Config file invalid")
            if message == "ok":
                self._master.destroy()
                sys.exit()

    def get_character(self):
        """
        Returns character player chose
        :return: (Str) of character player chose in config file
        """
        return self.character

    def goto_next_level(self, type: str):
        """
        Goes to next level after colliding with flag or ducking on tunnel
        :param type: (Str) type of goal, flag or tunnel
        """
        self.highscore()
        for i in self.config["==" + self.current_level + "=="]:
            if i.startswith(type):
                self.reset_world(i.split(":")[-1].strip(" "))

    def create_status_bar(self):
        """
        Creates status bar
        """
        self.health_score_frame = tk.Frame(self._master, width=MAX_WINDOW_SIZE[0])
        self.health_score_frame.pack(expand=1, fill=tk.BOTH)

        pixels_health = self.get_health_bar_size()
        health_colour = self.get_colour_health()

        self.health_bar = tk.Canvas(self.health_score_frame, height=15, bg=health_colour, width=pixels_health)
        self.health_bar.pack(side=tk.TOP, anchor=tk.W)

        score_text = self.get_score_text()

        self.score_label = tk.Label(self._master, text=score_text)
        self.score_label.pack(expand=True)

    def update_status_bar(self):
        """
        Updates status bar after change
        """
        self.health_bar.config(bg=self.get_colour_health(), width=self.get_health_bar_size())
        self.score_label.config(text=self.get_score_text())

    def set_invincibility(self):
        """
        set invincibility
        """
        self.invincibility = True
        self.update_status_bar()
        self._master.after(TIMING["invincibility"], self.remove_invincibility)

    def remove_invincibility(self):
        """
        After set time, remove invincibility
        """
        self.invincibility = False
        self.update_status_bar()

    def _set_on_tunnel(self, is_on: bool):
        """
        Sets if player is on tunnel
        :param is_on: (bool) true if player is on tunnel
        :return: (bool) true if player is on tunnel
        """
        self._on_tunnel = is_on

    def get_score_text(self):
        """
        Returns string of what to display for score
        :return: (str) of what to display for score in status bar
        """
        return "Score: " + str(self._player.get_score())

    def get_colour_health(self):
        """
        Healthbar colour
        yellow if invincible
        red if < 25%
        yellow if < 50 and >= 25%
        green if > 50%
        :return: (str) colour of healthbar
        """
        health_percentage = 100 * self._player.get_health() / self._player.get_max_health()
        if self.invincibility:
            return "yellow"
        elif health_percentage >= 50:
            return "green"
        elif 50 > health_percentage >= 25:
            return "orange"
        elif health_percentage < 25:
            return "red"

    def get_health_bar_size(self):
        """
        total width for the health bar
        used to find percentage of the health bar for the health
        :return: (float) of what the total width for the health bar is
        """
        return MAX_WINDOW_SIZE[0] * self._player.get_health() / self._player.get_max_health()

    def menu_load_level(self):
        """
        Player loads specific level from file
        """
        self._master.filename = filedialog.askopenfilename()
        # Choose a file
        self.current_level = self._master.filename.split("/")[-1]
        self._player.change_health(self.health)
        # Resets health
        self._player.change_score(-self._player.get_score())
        # Resets score
        self.update_status_bar()
        # Updates status bar to reflect changes
        self.reset_world(self.current_level)

    def menu_reset_level(self):
        """
        Resets the current level, health to max and score to 0
        """
        self._player.change_health(self.health)
        self._player.change_score(-self._player.get_score())
        self.update_status_bar()
        self.reset_world(self.current_level)

    def menu_exit(self):
        """
        Exits the game
        """
        self._master.destroy()

    def death(self):
        """
        When player dies, they are given an option to restart the level, or to quit
        """
        MsgBox = tk.messagebox.askquestion("Dead!", "You have died. Would you like to restart the level?",
                                           icon='warning')
        if MsgBox == 'yes':
            self.menu_reset_level()
        else:
            self.menu_exit()

    def highscore(self):
        """
        Handles the highscore list
        NOT COMPLETE
        """
        pass
        # player_name = simpledialog.askstring('High Score', 'What is your name?')
        # print(self.current_level)
        # print(self._player.get_score())
        # if not os.path.exists("highscore.txt"):
        #     highscore_file = open("highscore.txt", "w+")
        #     highscore_file.write("== ==High Scores== ==\n")
        #     highscore_file.write("   =="+self.current_level+"==   \n")
        #     highscore_file.write(player_name+ " | "+ str(self._player.get_score())+"\n")
        #     highscore_file.close()
        #
        # else:
        #     highscore_data = {}
        #     with open("highscore.txt", "r+") as file:
        #         highscore_file = file.readlines()
        #     for line in highscore_file:
        #         line = line.strip("\n")
        #         if line.startswith("="):
        #             pass
        #         elif line == "\n" or line == "":
        #             pass
        #         elif line.startswith("-"):
        #             current_level = line.lstrip("-")
        #             highscore_data[current_level] = []
        #         else:
        #             highscore_data[current_level].append((int(line.split(" | ")[1]),line.split(" | ")[0]))
        #     highscore_data[self.current_level].append((self._player.get_score(),player_name))
        #     for i in highscore_data.keys():
        #         scores = highscore_data[i]
        #         scores.sort()
        #         print(scores)
        #     print(highscore_data)

    def game_end(self):
        """
        Lets the player know the game has ended
        """
        message = messagebox.showinfo("Information", "Congratulations, you have completed the game!")
        if message == "ok":
            self._master.destroy()

    def reset_world(self, new_level):
        """
        Resets level, or moves to new level
        :param new_level: (str) of filename for level moving to
        """
        if new_level == "END":
            # If str is END, end the game
            self.game_end()
        else:
            self._world = load_world(self._builder, new_level)
            self._world.add_player(self._player, self.x_start, self.y_start, self.mass)
            self._builder.clear()
            self._setup_collision_handlers()

    def unpress_switch(self, block, x, y, pressed_switch, positions):
        """
        After 10 seconds of the TIMIGS["switch"] is pressed, this function is called
        :param block: the original switch
        :param x: x coordinate of the swithc
        :param y: y coordinate of the swithc
        :param pressed_switch: the pressed switch object
        :param positions: list of all positions of bricks to be replaces
        """
        block._switch = False
        for i in positions:
            self._world.add_block(Block("brick"), i[0], i[1])
            # Add all the blocks that were removed
        self._world.remove_block(pressed_switch)
        # Remove pressed switch
        self._world.add_block(block ,x ,y )
        #

    def bind(self):
        """Bind all the keyboard events to their event handlers."""
        self._view.bind_all("<w>", self._jump)
        self._view.bind_all("<Up>", self._jump)
        self._view.bind_all("<space>", self._jump)
        self._view.bind_all("<s>", self._duck)
        self._view.bind_all("<Down>", self._duck)
        self._view.bind_all("<Right>", lambda e: self._move(1, 0))
        self._view.bind_all("<d>", lambda e: self._move(1, self._player.get_velocity()[1]))
        self._view.bind_all("<Left>", lambda e: self._move(-1, 0))
        self._view.bind_all("<a>", lambda e: self._move(-1, self._player.get_velocity()[1]))

    def redraw(self):
        """Redraw all the entities in the game canvas."""
        self._view.delete(tk.ALL)

        self._view.draw_entities(self._world.get_all_things())

    def scroll(self):
        """Scroll the view along with the player in the center unless
        they are near the left or right boundaries
        """
        x_position = self._player.get_position()[0]
        half_screen = self._master.winfo_width() / 2
        world_size = self._world.get_pixel_size()[0] - half_screen

        # Left side
        if x_position <= half_screen:
            self._view.set_offset((0, 0))

        # Between left and right sides
        elif half_screen <= x_position <= world_size:
            self._view.set_offset((half_screen - x_position, 0))

        # Right side
        elif x_position >= world_size:
            self._view.set_offset((half_screen - world_size, 0))

    def step(self):
        """Step the world physics and redraw the canvas."""
        data = (self._world, self._player)
        self._world.step(data)

        self.scroll()
        self.redraw()

        self._master.after(10, self.step)

    def _move(self, dx, dy):
        """
        Moves the player to the side.
        """
        if dx > self.max_velocity:
            # Limit player velocity to max_velocity set in confif file
            dx = self.max_velocity
        self._player.set_velocity((dx * BLOCK_SIZE * 5, self._player.get_velocity()[1]))

    def _jump(self, e):
        """
        First check that player is not already jumping, but is on a block.
        If not jumping, jump
        """
        if not self._player.is_jumping():
            self._player.set_velocity((self._player.get_velocity()[0], -BLOCK_SIZE * JUMP_SIZE))

    def _duck(self, e):
        """
        Handles when player ducks. If player on tunnel, move to bonus level, then set that
        player is no longer on tunnel
        """
        if self._on_tunnel:
            self.goto_next_level("tunnel")
            self._set_on_tunnel(False)

    def _setup_collision_handlers(self):
        """
        Setup handlers for collisions
        """
        self._world.add_collision_handler("player", "item", on_begin=self._handle_player_collide_item)
        self._world.add_collision_handler("player", "block", on_begin=self._handle_player_collide_block,
                                          on_separate=self._handle_player_separate_block)
        self._world.add_collision_handler("player", "mob", on_begin=self._handle_player_collide_mob)
        self._world.add_collision_handler("mob", "block", on_begin=self._handle_mob_collide_block)
        self._world.add_collision_handler("mob", "mob", on_begin=self._handle_mob_collide_mob)
        self._world.add_collision_handler("mob", "item", on_begin=self._handle_mob_collide_item)

    def _handle_mob_collide_block(self, mob: Mob, block: Block, data,
                                  arbiter: pymunk.Arbiter) -> bool:
        """
        Handles when a mob collides with a block
        :param mob: The mob that collided
        :param block: The block the mob collided with
        :return: (bool): True if mob can collide with block
        """
        if mob.get_id() == "fireball":
            if block.get_id() == "brick":
                # If fireball collides with brick, remove both
                self._world.remove_block(block)
            self._world.remove_mob(mob)
        elif mob.get_id() == "mushroom":
            # If mushroom collides with the side of a brick, turn around
            if get_collision_direction(block, mob) == "R" or get_collision_direction(block, mob) == "L":
                mob.set_tempo(-mob.get_tempo())
        elif block.get_id() == "switch_pressed":
            # Mob doesn't collide with pressed switch
            return False
        return True

    def _handle_mob_collide_item(self, mob: Mob, block: Block, data,
                                 arbiter: pymunk.Arbiter) -> bool:
        """
        Handles if a mob collides with an item
        :param mob: the mob that collided with item
        :param block: the item
        :return: Always returns False
        """
        return False

    def _handle_mob_collide_mob(self, mob1: Mob, mob2: Mob, data,
                                arbiter: pymunk.Arbiter) -> bool:
        """
        Handles when a mob collides with a mob
        :param mob1: One of the mobs that collided
        :param mob2: The other mob
        :return: (bool): always returns false
        """
        if mob1.get_id() == "fireball" or mob2.get_id() == "fireball":
            # If fireball hits another mob, remove both
            self._world.remove_mob(mob1)
            self._world.remove_mob(mob2)
        if mob1.get_id() == "mushroom" and mob2.get_id() == "mushroom":
            # If mushrooms collide, both change direction
            mob1.set_tempo(-mob1.get_tempo())
            mob2.set_tempo(-mob2.get_tempo())
        return False

    def _handle_player_collide_item(self, player: Player, dropped_item: DroppedItem,
                                    data, arbiter: pymunk.Arbiter) -> bool:
        """Callback to handle collision between the player and a (dropped) item. If the player has sufficient space in
        their to pick up the item, the item will be removed from the game world.

        Parameters:
            player (Player): The player that was involved in the collision
            dropped_item (DroppedItem): The (dropped) item that the player collided with
            data (dict): data that was added with this collision handler (see data parameter in
                         World.add_collision_handler)
            arbiter (pymunk.Arbiter): Data about a collision
                                      (see http://www.pymunk.org/en/latest/pymunk.html#pymunk.Arbiter)
                                      NOTE: you probably won't need this
        Return:
             bool: False (always ignore this type of collision)
                   (more generally, collision callbacks return True iff the collision should be considered valid; i.e.
                   returning False makes the world ignore the collision)
        """
        if dropped_item.get_id() == "star":
            # If player picks a star, make player invincible
            # See set_invincibility()
            self.set_invincibility()
        dropped_item.collect(self._player)
        self._world.remove_item(dropped_item)
        # Remove the item
        self.update_status_bar()
        # Update status to reflect new points
        return False

    def _handle_player_collide_block(self, player: Player, block: Block, data,
                                     arbiter: pymunk.Arbiter) -> bool:
        """
        Handles when the player collides with a block
        :param player: The player
        :param block: The block the player collided with
        :return: (bool): returns true if player can collide with block
        """

        if get_collision_direction(block, player) == "B":
            # Set player jumping to false if landed on top of block
            # so player can jump
            self._player.set_jumping(False)

        block.on_hit(arbiter, (self._world, player))

        if block.get_id() == "bounce_block":
            # Player jumps when collides with bounce block
            self._jump(None)
        if block.get_id() == "tunnel" and get_collision_direction(block, player) == "B":
            # If player ducks while on tunnel, move to next bonus level. See _duck()
            self._set_on_tunnel(True)

        elif block.get_id() == "flag":
            # If player collides with flag, move to next level.
            # If collides with top of flag, full health
            if get_collision_direction(block, player) == "B":
                self.goto_next_level("goal")
                player.change_health(player.get_max_health() - player.get_health())
            else:
                self.goto_next_level("goal")
        elif block.get_id() == "switch_pressed":
            # If switch is pressed, no colliding with it
            return False
        elif block.get_id() == "switch":
            if not block._switch:
                # If block is not switched
                if get_collision_direction(block, player) == "B":
                    # If landed on top of switch:
                    # Remove all blocks in a range of 10 BLOCK_SIZE from the switch
                    self._switch = True
                    x, y = block.get_position()[0], block.get_position()[1] # x and y coordinates of the switch
                    remove = self._world.get_things_in_range(x, y, BLOCK_SIZE * 10)
                    # remove is a list of all the things in the range
                    positions = []
                    for i in remove:
                        # Filtering only for bricks
                        if i == player:
                            pass
                        elif i.get_id() == "brick":
                            positions.append(i.get_position())
                            # Store coordinates for all the bricks
                            self._world.remove_block(i)
                            # Remove bricks
                    block._switch = True
                    self._world.remove_block(block)
                    # remove switch to be replace with pressed switch
                    pressed_switch = Switch_Pressed()
                    self._world.add_block(pressed_switch,x ,y)
                    # Add the pressed switch blick
                    self._master.after(TIMING["switch"], self.unpress_switch, block, x, y, pressed_switch, positions)
                    # After 10 sec, replace pressed switch with original and replace bricks
                    # See unpress_switch()
            else:
                return False

        return True

    def _handle_player_collide_mob(self, player: Player, mob: Mob, data,
                                   arbiter: pymunk.Arbiter) -> bool:
        """
        Handle for when the player collides with a mob
        :param player: the player
        :param mob: the mob the player collided with
        :return: (bool): True if player can connect with mob
        """
        if self.invincibility:
            # if player is currently invincible, destroy mobs without loosing health
            self._world.remove_mob(mob)
        else:
            # i.e. player is not invincible
            if mob.get_id() == "mushroom":
                # If mob is mushroom,
                # When the mob collides with the side of a player, the player should lose 1 health
                # point and be slightly repelled away from the mob
                if get_collision_direction(mob, player) == "R":
                    # Hit right side of mob
                    player.change_health(-1)
                    player.set_velocity((-100, player.get_velocity()[1]))
                elif get_collision_direction(mob, player) == "L":
                    # Hit right side of mob
                    player.change_health(-1)
                    player.set_velocity((100, player.get_velocity()[1]))
                elif get_collision_direction(mob, player) == "B":
                    # If player hits top of mushroom, mushroom dies, and player bounces
                    player.set_velocity((player.get_velocity()[0], -BLOCK_SIZE * 7))
                    player.set_jumping(True)
                    self._world.remove_mob(mob)
            else:
                mob.on_hit(arbiter, (self._world, player))
        # Update status bar to reflect change in health
        self.update_status_bar()
        if player.is_dead():
            self.death()
        return True

    def _handle_player_separate_block(self, player: Player, block: Block, data,
                                      arbiter: pymunk.Arbiter) -> bool:
        """
        Handle for when the player leaves a block
        :param player: The player
        :param block: The block the player seperated from
        :return: (bool): True if player disconnected from block
        """
        # If player leaves block, disallow jump until lands on another block
        self._player.set_jumping(True)
        # Player is no longer on tunnel. No moving to bonus level
        if block.get_id() == "tunnel":
            self._set_on_tunnel(False)
        return True


class BounceBlock(Block):
    """Class of BounceBlock, child of Block"""
    _id = "bounce"


class Flag(Block):
    """Class of Flag, child of Block"""
    _id = "flag"
    _cell_size = GOAL_SIZES["flag"]


class Tunnel(Block):
    """Class of Tunnel, child of Block"""
    _id = "tunnel"
    _cell_size = GOAL_SIZES["tunnel"]


class Switch(Block):
    """Class of Switch, child of Block"""
    _id = "switch"
    _switch = False
    _activated = False

    def is_active(self):
        """
        Returns:
        (bool): returns if the switch is pressed
        """
        return self._activated


class Switch_Pressed(Block):
    """Class of The pressed Switch block, child of Block"""
    _id = "switch_pressed"
    _switch = False
    _activated = False

    def is_active(self):
        """
        Returns:
        (bool): returns if the switch is pressed
        """
        return self._activated


class Mushroom(Mob):
    """Class for the Mushroom Mob"""
    _id = "mushroom"

    def __init__(self):
        super().__init__(self._id, size=(20, 20), weight=300, tempo=15)


class Star(DroppedItem):
    """A star item that can be picked up to increment the players score.
    """
    _id = "star"

    def __init__(self, value: int = 10):
        """Construct a coin with a score value of value.

        Parameters:
            value (int): The value of the coin
        """
        super().__init__()
        self._value = value
        self.invincibility = False


def main():
    root = tk.Tk()
    app = MarioApp(root)
    root.title("Mario Game")
    app.redraw()
    root.mainloop()


main()
