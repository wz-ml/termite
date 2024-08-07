from .map import Map, Pathfinder
from .units import Unit, MobileUnit, Structure, Support
from .units import Demolisher, Interceptor, Scout, Wall, Turret, Support
from colorama import init, Fore, Back, Style
import warnings
from typing import List, Union, Optional, Container, Tuple

class Player:
    """
    A base class for all agents that play Terminal.
    """
    def __init__(self):
        self.health = 30
        self.structure_points = 40
        self.mobile_points = 5
        self.deployments = []

    def deploy(self, game_state: dict) -> List[Tuple[Union[MobileUnit, Structure], Tuple[int, int]]]:
        """
        This method should be overridden by AI or human player implementations.

        :param game_state: A dictionary containing the current game state.
        :return: A list of tuples containing the unit to deploy and the position to deploy it.

        By default, returns an empty list.
        """
        self.deployments = []
        return self.deployments
    
    def upgrade(self, game_state: dict) -> List[Tuple[int, int]]:
        """
        This method should be overridden by AI or human player implementations.

        Note: All upgrades are applied after all deployments.

        :param game_state: A dictionary containing the current game state.
        :return: A list of positions (x, y) where structures should be upgraded.

        By default, returns an empty list.
        """
        self.upgrades = []
        return self.upgrades

    def process_upgrades(self, game: 'TerminalGame') -> None:
        """
        Process the upgrades requested by the player.
        """
        upgrade_positions = self.upgrade(game.get_game_state())
        for pos in upgrade_positions:
            x, y = pos
            structure = game.map.grid[y][x]
            if isinstance(structure, Structure) and structure.side == self.side:
                if self.structure_points >= structure.upgrade_cost and not structure.is_upgraded:
                    self.structure_points -= structure.upgrade_cost
                    structure.upgrade()
                else:
                    warnings.warn(f"Cannot upgrade {structure.unit_type} at position {pos}. Insufficient points or already upgraded.")
            else:
                warnings.warn(f"Invalid upgrade position {pos}")

    def can_afford(self, unit: Union[MobileUnit, Structure]) -> bool:
        """
        Check if this player can afford to deploy a unit.
        """
        if isinstance(unit, MobileUnit):
            return self.mobile_points >= unit.cost
        elif isinstance(unit, Structure):
            return self.structure_points >= unit.cost
        return False

    def deduct_cost(self, unit: Unit):
        if isinstance(unit, MobileUnit):
            self.mobile_points -= unit.cost
        elif isinstance(unit, Structure):
            self.structure_points -= unit.cost

    def decay_mobile_points(self) -> None:
        """
        Decay mechanic where unspent mobile points are reduced by 25% each turn.
        """
        self.mobile_points = round(self.mobile_points * 0.75, 1)

    def add_resources(self, turn_number: int) -> None:
        """
        Grant resources to the player based on the current turn number.

        Happens once during the Restore Phase.
        """
        self.structure_points += 5
        self.mobile_points += 5 + (turn_number // 10)

    def remove_structure(self, structure: Structure) -> None:
        refund = round(0.75 * structure.cost * (structure.health / structure.max_health), 1)
        self.structure_points += refund
    
class TerminalGame:
    """
    The main game class that manages the game state and progression.

    The game loop is divided into three phases:
    - Restore Phase: Players gain resources and mobile points.
    - Deploy Phase: Players deploy units onto the map.
    - Action Phase: Units move and attack each other.

    The game ends after 100 turns or when a player's health reaches 0.
    """
    def __init__(self, player1: Optional[Player] = None, player2: Optional[Player] = None):
        """
        Initialize the game with two players.
        """
        self.map = Map()
        self.pathfinder = Pathfinder(self.map)
        if player1 is None: 
            self.player1: Player = Player()
        else:
            self.player1 = player1
        self.player1.side = 'bottom'

        if player2 is None:
            self.player2: Player = Player()
        else:
            self.player2 = player2
        self.player2.side = "top"

        self.current_turn = 0
        self.frame_count = 0
        self.units: List[Unit] = []

    def play_turn(self):
        """
        Primary method. Play a single turn of the game.
        """
        self.deploy_phase()
        self.action_phase()
        self.current_turn += 1
        self.restore_phase()

    def restore_phase(self):
        """
        Phase 1: All players gain resources and mobile points.
        """
        for player in (self.player1, self.player2):
            player.decay_mobile_points()
            player.add_resources(self.current_turn)
        # Add logic for resource generation from structures
        # Note from Will: There's this line in the rulebook: 
        # "Structures that generate resources will do so at this time.""
        # But I cannot for the life of me find which structures generate resources. Leaving this blank for now.

    def deploy_phase(self):
        """
        Phase 2: Players deploy units onto the map and upgrade structures.
        """
        for player in (self.player1, self.player2):
            player_deployments = player.deploy(self.get_game_state())
            
            for deployment in player_deployments:
                unit, position = deployment
                if self.is_valid_deployment(player, unit, position):
                    if player.can_afford(unit):
                        self.place_unit(player, unit, position)
                        player.deduct_cost(unit)
                    else:
                        print(f"Player cannot afford to deploy {unit.unit_type}")
                else:
                    print(f"Invalid deployment: {unit.unit_type} at {position}")
        self.upgrade_phase()
    
    def upgrade_phase(self):
        """
        Allow players to upgrade their structures. Happens at the end of the deploy phase.
        """
        for player in (self.player1, self.player2):
            player.process_upgrades(self)

    def is_valid_deployment(self, player: Player, unit: Unit, position: Tuple[int, int]) -> bool:
        """
        Check if the position is in the player's half of the arena and if it's a valid position for the unit type.
        """
        x, y = position
        is_player1 = player == self.player1
        
        # Check if the position is within the diamond-shaped arena
        if not self.map.is_in_arena(x, y):
            return False

        if isinstance(unit, MobileUnit):
            # Mobile units can be deployed on the edges of the diamond on the current player's side
            if is_player1:
                return y <= 13 and abs(x - 13.5) + abs(y - 13.5) == 14
            else:  # Player 2
                return y >= 14 and abs(x - 13.5) + abs(y - 13.5) == 14
        elif isinstance(unit, Structure):
            # Static units can be deployed on the player's half of the diamond
            # and cannot be deployed on top of existing structures
            if is_player1:
                valid_area = y <= 13 and abs(x - 13.5) + abs(y - 13.5) <= 14
            else:  # Player 2
                valid_area = y >= 14 and abs(x - 13.5) + abs(y - 13.5) <= 14
            
            return valid_area and self.map.grid[y][x] is None  # Ensure the cell is empty
        
        return False

    def place_unit(self, player: Player, unit: Unit, position: Tuple[int, int]):
        """
        Place a unit on the map at the specified position.
        """
        x, y = position        
        unit.creation_time = self.frame_count
        unit.position = (x, y)
        unit.set_side('bottom' if player == self.player1 else 'top')
        self.units.append(unit)
        self.map.place_unit(unit, x, y)

    def action_phase(self):
        """
        Phase 3: units move and attack each other.
        """
        while self.units_active():
            self.process_frame()
            self.frame_count += 1

    def process_frame(self):
        """
        Undergo a single frame of the action phase.
        """
        self.apply_support_shields()
        self.move_units()
        self.reset_attack_status()
        self.resolve_attacks()
        self.remove_destroyed_units()

    def apply_support_shields(self):
        """
        Step 1: All support units apply shields to nearby mobile units.
        """
        for support in [u for u in self.units if isinstance(u, Support)]:
            for unit in [u for u in self.units if isinstance(u, MobileUnit)]:
                if support.distance_to(unit) <= support.range:
                    support.apply_shield(unit) # apply_shield only applies the shield if the support has not already shielded.

    def move_units(self):
        """
        Step 2: All mobile units move towards their target.
        """
        for unit in list(self.units):  # Create a copy of the list to avoid modification during iteration
            if isinstance(unit, MobileUnit):
                unit.move(self)
        # Remove all mobile units from the map
        self.map.clear()
        # Add all new positions to the map
        for unit in self.units:
            if isinstance(unit, MobileUnit):
                x, y = unit.position
                self.map.place_unit(unit, x, y)
        
    def reset_attack_status(self):
        """
        Step 3: Reset the attack status of all mobile units.
        """
        for unit in self.units:
            if isinstance(unit, MobileUnit):
                unit.reset_attack_status()

    def resolve_attacks(self):
        """
        Step 4: All mobile units attack enemy units within range.
        """
        for unit in sorted(self.units, key=lambda u: u.creation_time):
            if isinstance(unit, MobileUnit):
                unit.attack(self)

    def remove_destroyed_units(self):
        """
        Step 5: Remove units that have been destroyed.

        This may seem like a strange way to handle unit destruction, but Terminal
        has the curious property that units can simultaneously destroy each other.
        """
        destroyed_units = [unit for unit in self.units if unit.health <= 0]
        for unit in destroyed_units:
            self.remove_unit(unit)

        # Handle any additional effects of unit destruction
        for unit in destroyed_units:
            if isinstance(unit, MobileUnit):
                # Mobile units might have additional destruction effects
                self.handle_mobile_unit_destruction(unit)
            elif isinstance(unit, Structure):
                # Structures might have additional destruction effects
                self.handle_structure_destruction(unit)

    def remove_unit(self, unit: Unit):
        self.units.remove(unit)
        x, y = unit.position
        self.map.grid[y][x] = None

    def handle_mobile_unit_destruction(self, unit: MobileUnit):
        """
        Handle any special effects when a mobile unit is destroyed.
        For example, applying area damage for self-destructing units.
        """
        if unit.distance_moved >= 5:
            self.apply_self_destruct_damage(unit)

    def handle_structure_destruction(self, unit: Structure):
        """
        Handle any special effects when a structure is destroyed.
        For example, refunding some resources to the player.
        """
        player = self.get_unit_owner(unit)
        refund = round(0.75 * unit.cost * (unit.health / unit.max_health), 1)
        player.structure_points += refund

    def apply_self_destruct_damage(self, unit: MobileUnit):
        """
        Apply area damage when a mobile unit self-destructs.
        """
        for target in self.units:
            if target.unit_type != unit.unit_type and unit.distance_to(target) <= 1.5:
                target.take_damage(unit.max_health)

    """
    --------------- Helper Methods ---------------
    """
    def get_unit_owner(self, unit: Union[Unit, str]) -> Player:
        """
        Determine which player owns a given unit.
        """
        if isinstance(unit, str):
            return self.player1 if unit == 'bottom' else self.player2
        return self.player1 if unit.side == 'bottom' else self.player2

    def units_active(self) -> bool:
        """
        Check if there are any active mobile units on the map
        """
        return any(isinstance(unit, MobileUnit) for unit in self.units)

    def is_game_over(self) -> bool:
        """
        Check if the game is over.
        """
        if self.player1.health <= 0 or self.player2.health <= 0:
            return True
        if self.current_turn >= 100:
            return True
        return False

    def get_winner(self) -> str:
        """
        Returns the winner of the game: either "Player 1", "Player 2", or "Draw".

        The game should be over before calling this method.
        """
        assert self.is_game_over()
        if self.player1.health > self.player2.health:
            return "Player 1"
        elif self.player2.health > self.player1.health:
            return "Player 2"
        else:
            # TODO: Implement computation time comparison logic -> if both players kill each other simultaneously
            # or have the same health after 100 turns, the player with the most remaining computation time wins.
            pass
            return "Draw"

    def get_game_state(self) -> dict:
        """
        Return a representation of the current game state.
        This should include all the information that players need to make decisions.

        Keys:
        - map: A 2D list representing the game map.
        - current_turn: The current turn number.
        - player1_health: Player 1's health.
        - player2_health: Player 2's health.
        - player1_resources: A dictionary of Player 1's resources. Keys: 'mobile', 'structure'.
        - player2_resources: A dictionary of Player 2's resources. Keys: 'mobile', 'structure'.
        """
        return {
            'map': self.map.grid,
            'current_turn': self.current_turn,
            'player1_health': self.player1.health,
            'player2_health': self.player2.health,
            'player1_resources': {'mobile': self.player1.mobile_points, 'structure': self.player1.structure_points},
            'player2_resources': {'mobile': self.player2.mobile_points, 'structure': self.player2.structure_points},
            'units': self.units
        }
    
    def upgrade_structure(self, player: Player, structure: Structure) -> bool:
        """
        Request to upgrade a structure.

        Returns True if the upgrade was successful, False otherwise.
        """
        if player.structure_points >= structure.upgrade_cost and not structure.is_upgraded:
            player.structure_points -= structure.upgrade_cost
            structure.upgrade()
            return True
        return False

    def get_unit_color(self, unit: Unit):
        """
        Helper function for rendering units with different colors based on health.
        """
        health_percentage = unit.health / unit.max_health
        if health_percentage > 0.7:
            return Fore.GREEN
        elif health_percentage > 0.3:
            return Fore.YELLOW
        else:
            return Fore.RED

    def render(self):
        """
        Render the game state as a prettified string to print.
        """

        output = []
        
        output.append(f"Turn: {self.current_turn}/100")
        output.append(f"Frame: {self.frame_count}")
        output.append("")

        # Player information
        p1_health = f"{Fore.RED}{'♥' * self.player1.health}{Style.RESET_ALL:<30}"
        p2_health = f"{Fore.RED}{'♥' * self.player2.health}{Style.RESET_ALL:>30}"
        output.append(f"Player 1: {p1_health}")
        output.append(f"Player 2: {p2_health}")
        output.append("")

        # Resources
        output.append(f"P1 Resources - Mobile: {Fore.CYAN}{self.player1.mobile_points:.1f}{Style.RESET_ALL}, Structure: {Fore.YELLOW}{self.player1.structure_points:.1f}{Style.RESET_ALL}")
        output.append(f"P2 Resources - Mobile: {Fore.CYAN}{self.player2.mobile_points:.1f}{Style.RESET_ALL}, Structure: {Fore.YELLOW}{self.player2.structure_points:.1f}{Style.RESET_ALL}")
        output.append("")

        # Game board
        for y in reversed(range(self.map.height)):
            row = ""
            for x in range(self.map.width):
                if not self.map.is_in_arena(x, y):
                    row += "  "
                elif self.map.grid[y][x] is None:
                    row += f"{Fore.WHITE}· {Style.RESET_ALL}"
                else:
                    units = self.map.grid[y][x]
                    if isinstance(units, list):
                        unit = units[0]
                    else:
                        unit = units
                    color = self.get_unit_color(unit)
                    if isinstance(unit, Scout):
                        row += f"{color}{'S' if unit.side == 'bottom' else 's'} {Style.RESET_ALL}"
                    elif isinstance(unit, Demolisher):
                        row += f"{color}{'D' if unit.side == 'bottom' else 'd'} {Style.RESET_ALL}"
                    elif isinstance(unit, Interceptor):
                        row += f"{color}{'I' if unit.side == 'bottom' else 'i'} {Style.RESET_ALL}"
                    elif isinstance(unit, Wall):
                        row += f"{color}{'W' if unit.side == 'bottom' else 'w'} {Style.RESET_ALL}"
                    elif isinstance(unit, Support):
                        row += f"{color}{'U' if unit.side == 'bottom' else 'u'} {Style.RESET_ALL}"
                    elif isinstance(unit, Turret):
                        row += f"{color}{'T' if unit.side == 'bottom' else 't'} {Style.RESET_ALL}"
            output.append(row)

        output.append("\nLegend:")
        output.append(f"{Fore.GREEN}Green{Style.RESET_ALL}: High Health, {Fore.YELLOW}Yellow{Style.RESET_ALL}: Medium Health, {Fore.RED}Red{Style.RESET_ALL}: Low Health")
        output.append("S/s: Scout, D/d: Demolisher, I/i: Interceptor")
        output.append("W/w: Wall, U/u: Support, T/t: Turret")
        output.append("Uppercase: Player 1, Lowercase: Player 2")

        return "\n".join(output)