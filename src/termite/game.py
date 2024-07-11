from .map import Map, Pathfinder
from .units import MobileUnit, Structure, Support
from .units import Demolisher, Interceptor, Scout, Wall, Turret, Support
from colorama import init, Fore, Back, Style
import warnings

class Player:
    def __init__(self):
        self.health = 30
        self.structure_points = 40
        self.mobile_points = 5
        self.deployments = []

    def deploy(self, game_state):
        # This method should be overridden by AI or human player implementations
        # For now, we'll just return an empty list
        self.deployments = []
        return self.deployments
    
    def can_afford(self, unit):
        if isinstance(unit, MobileUnit):
            return self.mobile_points >= unit.cost
        elif isinstance(unit, Structure):
            return self.structure_points >= unit.cost
        return False

    def deduct_cost(self, unit):
        if isinstance(unit, MobileUnit):
            self.mobile_points -= unit.cost
        elif isinstance(unit, Structure):
            self.structure_points -= unit.cost

    def decay_mobile_points(self):
        self.mobile_points = round(self.mobile_points * 0.75, 1)

    def add_resources(self, turn_number):
        self.structure_points += 5
        self.mobile_points += 5 + (turn_number // 10)

    def remove_structure(self, structure):
        refund = round(0.75 * structure.cost * (structure.health / structure.max_health), 1)
        self.structure_points += refund
    
class TerminalGame:
    def __init__(self):
        self.map = Map()
        self.pathfinder = Pathfinder(self.map)
        self.player1 = Player()
        self.player2 = Player()
        self.current_turn = 0
        self.frame_count = 0
        self.units = []

    def play_turn(self):
        self.restore_phase()
        self.deploy_phase()
        self.action_phase()
        self.current_turn += 1

    def restore_phase(self):
        for player in (self.player1, self.player2):
            player.decay_mobile_points()
            player.add_resources(self.current_turn)
        # Add logic for resource generation from structures

    def deploy_phase(self):
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

    def is_valid_deployment(self, player, unit, position):
        # Check if the position is in the player's half of the arena
        # and if it's a valid position for the unit type
        # This is a simplified check and should be expanded based on game rules
        x, y = position
        is_player1 = player == self.player1
        is_in_player_half = y < 14 if is_player1 else y >= 14
        is_valid_position = self.map.is_in_arena(x, y) and self.map.grid[y][x] is None
        
        if isinstance(unit, MobileUnit):
            return is_valid_position and (x == 0 or x == 27)  # Mobile units on edges
        elif isinstance(unit, Structure):
            return is_valid_position and is_in_player_half
        
        return False

    def place_unit(self, player, unit, position):
        self.map.place_unit(unit, *position)
        unit.creation_time = self.frame_count
        unit.set_side('bottom' if player == self.player1 else 'top')
        self.units.append(unit)

    def action_phase(self):
        while self.units_active():
            self.process_frame()
            self.frame_count += 1

    def process_frame(self):
        self.apply_support_shields()
        self.move_units()
        self.reset_attack_status()
        self.resolve_attacks()
        self.remove_destroyed_units()

    def apply_support_shields(self):
        for support in [u for u in self.units if isinstance(u, Support)]:
            for unit in [u for u in self.units if isinstance(u, MobileUnit)]:
                if support.distance_to(unit) <= support.range:
                    support.apply_shield(unit)

    def reset_attack_status(self):
        for unit in self.units:
            if isinstance(unit, MobileUnit):
                unit.reset_attack_status()

    def resolve_attacks(self):
        for unit in sorted(self.units, key=lambda u: u.creation_time):
            if isinstance(unit, MobileUnit):
                unit.attack(self)

    def remove_destroyed_units(self):
        destroyed_units = [unit for unit in self.units if unit.health <= 0]
        for unit in destroyed_units:
            self.remove_unit(unit)

    def remove_unit(self, unit):
        self.units.remove(unit)
        x, y = unit.position
        self.map.grid[y][x] = None

    def move_units(self):
        for unit in list(self.units):  # Create a copy of the list to avoid modification during iteration
            if isinstance(unit, MobileUnit):
                unit.move(self)

    def remove_destroyed_units(self):
        # Remove units with health <= 0
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

    def handle_mobile_unit_destruction(self, unit):
        # Handle any special effects when a mobile unit is destroyed
        # For example, applying area damage for self-destructing units
        if unit.distance_moved >= 5:
            self.apply_self_destruct_damage(unit)

    def handle_structure_destruction(self, unit):
        # Handle any special effects when a structure is destroyed
        # For example, refunding some resources to the player
        player = self.get_unit_owner(unit)
        refund = round(0.75 * unit.cost * (unit.health / unit.max_health), 1)
        player.structure_points += refund

    def apply_self_destruct_damage(self, unit):
        # Apply area damage when a mobile unit self-destructs
        for target in self.units:
            if target.unit_type != unit.unit_type and unit.distance_to(target) <= 1.5:
                target.take_damage(unit.max_health)

    def get_unit_owner(self, unit):
        # Determine which player owns the unit
        return self.player1 if unit.side == 'bottom' else self.player2

    def units_active(self):
        # Check if there are any active mobile units on the map
        return any(isinstance(unit, MobileUnit) for unit in self.units)

    def is_game_over(self):
        if self.player1.health <= 0 or self.player2.health <= 0:
            return True
        if self.current_turn >= 100:
            return True
        return False

    def get_winner(self):
        if self.player1.health > self.player2.health:
            return "Player 1"
        elif self.player2.health > self.player1.health:
            return "Player 2"
        else:
            # Implement computation time comparison logic
            pass

    def get_game_state(self):
        # Return a representation of the current game state
        # This should include information that players need to make decisions
        return {
            'map': self.map.grid,
            'current_turn': self.current_turn,
            'player1_health': self.player1.health,
            'player2_health': self.player2.health,
            'player1_resources': {'mobile': self.player1.mobile_points, 'structure': self.player1.structure_points},
            'player2_resources': {'mobile': self.player2.mobile_points, 'structure': self.player2.structure_points},
            'units': self.units
        }
    
    def upgrade_structure(self, player, structure):
        if player.structure_points >= structure.upgrade_cost and not structure.is_upgraded:
            player.structure_points -= structure.upgrade_cost
            structure.upgrade()
            return True
        return False

    def get_unit_color(self, unit):
        health_percentage = unit.health / unit.max_health
        if health_percentage > 0.7:
            return Fore.GREEN
        elif health_percentage > 0.3:
            return Fore.YELLOW
        else:
            return Fore.RED

    def render(self):
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
        for y in range(self.map.height):
            row = ""
            for x in range(self.map.width):
                if not self.map.is_in_arena(x, y):
                    row += "  "
                elif self.map.grid[y][x] is None:
                    row += f"{Fore.WHITE}· {Style.RESET_ALL}"
                else:
                    unit = self.map.grid[y][x]
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