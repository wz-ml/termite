from typing import List, Union, Optional, Container, Tuple

class Targeting:
    @staticmethod
    def select_target(attacker, potential_targets):
        if not potential_targets:
            return None

        # Step 1: Prioritize Mobile units over Structures
        mobile_targets = [t for t in potential_targets if isinstance(t, MobileUnit)]
        targets = mobile_targets if mobile_targets else potential_targets

        # Step 2: Choose the nearest target(s)
        min_distance = min(attacker.distance_to(t) for t in targets)
        targets = [t for t in targets if attacker.distance_to(t) == min_distance]

        # Step 3: Choose the target(s) with the lowest remaining health
        min_health = min(t.health for t in targets)
        targets = [t for t in targets if t.health == min_health]

        # Step 4: Choose the target(s) furthest into/towards the attacker's side
        max_progress = max(attacker.progress_towards_side(t) for t in targets)
        targets = [t for t in targets if attacker.progress_towards_side(t) == max_progress]

        # Step 5: Choose the target closest to an edge
        min_edge_distance = min(t.distance_to_nearest_edge() for t in targets)
        targets = [t for t in targets if t.distance_to_nearest_edge() == min_edge_distance]

        # If still multiple targets, choose the most recently created one
        return max(targets, key=lambda t: t.creation_time)
    
class Unit:
    """
    Defines the base class for all units in the game.
    """
    def __init__(self, unit_type: str, cost: int, health: float, range: float, damage: float):
        """
        Initialize a new unit with the given attributes.
        :param unit_type: The type of unit.
        :param cost: The cost to deploy the unit.
        :param health: The health of the unit.
        :param range: The maximum attack range of the unit, defined in Euclidian distance.
        :param damage: The damage dealt by the unit per tick.
        """
        self.unit_type: str = unit_type
        self.cost: int = cost
        self.health: float = health
        self.max_health: float = health
        self.range: float = range
        self.damage: float = damage
        self.position: float = None
        self.creation_time: Optional[int] = None
        self.side = None

    def set_side(self, side: str) -> None:
        """
        Set the side of the arena this unit is on. Used for pathfinding and targeting.
        """
        if side not in ['top', 'bottom']:
            raise ValueError("Side must be 'top' or 'bottom'")
        self.side = side

        if self.side == 'bottom':
            if self.position[0] <= 13:
                self.target_edge = 'top-left'
            else:
                self.target_edge = 'top-right'
        else:  # self.side == 'top'
            if self.position[0] <= 13:
                self.target_edge = 'bottom-left'
            else:
                self.target_edge = 'bottom-right'

    def distance_to(self, other_unit: 'Unit') -> float:
        """
        Calculate Euclidean distance to another unit.
        """
        return ((self.position[0] - other_unit.position[0])**2 + 
                (self.position[1] - other_unit.position[1])**2)**0.5

    def progress_towards_side(self, other_unit: 'Unit') -> float:
        """
        Calculate how far another unit is into this unit's side, depending on which side of the arena this unit is on.
        """
        if self.side == 'bottom':
            # For bottom player, progress is measured by how far up the unit has moved
            return 27 - other_unit.position[1]
        else:  # self.side == 'top'
            # For top player, progress is measured by how far down the unit has moved
            return other_unit.position[1]
        
    def distance_to_nearest_edge(self) -> float:
        """
        Calculate the distance from this unit to the nearest edge of the arena.
        """
        x, y = self.position
        distances = [
            x,  # distance to left edge
            27 - x,  # distance to right edge
            y,  # distance to top edge
            27 - y  # distance to bottom edge
        ]
        return min(distances)

    def attack(self, target: 'Unit') -> None:
        if target and target.health > 0:
            target.take_damage(self.damage)

    def take_damage(self, damage: float) -> None:
        self.health = max(0, self.health - damage)

class MobileUnit(Unit):
    """
    Defines the base class for mobile units in the game.
    """
    def __init__(self, unit_type: str, cost: float, health: float, range: float, damage: float, speed: int):
        """
        Initialization function.
        :param speed: The speed of the unit, defined as the number of ticks it takes to move one tile.
        """
        super().__init__(unit_type, cost, health, range, damage)
        self.speed = speed
        self.shields = 0
        self.position: Optional[Tuple[int, int]] = None  # To be set when deployed
        self.speed = speed
        self.frames_since_last_move = 0
        self.last_move = None
        self.path = []
        self.destination = None

    def add_shield(self, shield_amount: float) -> None:
        self.shields += shield_amount

    def move(self, game: 'TerminalGame') -> None:
        self.frames_since_last_move += 1
        if self.frames_since_last_move >= self.speed:
            if not self.path:
                self.path = game.pathfinder.find_path(self, self.position, self.target_edge)
            
            if self.path:
                next_pos = self.path.pop(0)
                self.last_move = (next_pos[0] - self.position[0], next_pos[1] - self.position[1])
                self.position = next_pos
                self.frames_since_last_move = 0
                self.distance_moved += 1

                if self.has_reached_enemy_edge(game):
                    self.reach_enemy_edge(game)
            else:
                self.self_destruct(game)
    
    def has_reached_enemy_edge(self, game: 'TerminalGame') -> bool:
        """
        Check if this unit has reached the enemy edge of the diamond-shaped arena.
        """
        x, y = self.position
        if self.side == 'bottom':
            # For units starting at the bottom, they reach the enemy edge when:
            # x + y == 27 (top-right edge) or x - y == 0 (top-left edge)
            return x + y == 27 or x == y
        else:  # self.side == 'top'
            # For units starting at the top, they reach the enemy edge when:
            # x + y == 27 (bottom-left edge) or y - x == 0 (bottom-right edge)
            return x + y == 27 or y == x
    
    def attack(self, game_state: 'TerminalGame') -> Union[float, None]:
        """
        Attack the closest enemy unit within range.

        Targeting priority:
        1. Mobile units over Structures
        2. Nearest target(s)
        3. Lowest remaining health
        4. Furthest into/towards the attacker's side
        5. Closest to an edge

        :return: The amount of damage dealt to the target. None if no target was attacked.
        """
        if self.has_attacked_this_frame:
            return  # Unit can only attack once per frame

        potential_targets = self.get_potential_targets(game_state)
        target = Targeting.select_target(self, potential_targets)

        if target:
            damage_dealt = self.deal_damage(target)
            self.has_attacked_this_frame = True
            return damage_dealt
        return 0

    def get_potential_targets(self, game_state: 'TerminalGame') -> List['Unit']:
        """
        Returns all valid targets in range of this unit.
        """
        return [unit for unit in game_state.units 
                if unit.side != self.side 
                and self.distance_to(unit) <= self.range 
                and unit.health > 0]

    def deal_damage(self, target: 'Unit') -> float:
        """
        Deal damage to a target unit.
        """
        damage = self.damage
        if isinstance(target, Structure) and self.unit_type == "Interceptor":
            return 0  # Interceptors cannot damage structures
        target.take_damage(damage)
        return damage

    def reset_attack_status(self) -> None:
        """
        All mobile units can attack once per frame. This resets the attack status.
        """
        self.has_attacked_this_frame = False

    def self_destruct(self, game) -> None:
        """
        Applies self-destruct damage to nearby enemy units and removes the unit from the game.

        In Terminal, a unit will self-destruct if its path to the opposite side is blocked.
        Self-destruct damage is only applied if the unit has moved at least 5 tiles.
        """
        if self.distance_moved >= 5:
            # Apply area damage
            for unit in game.units:
                if unit.side != self.side and self.distance_to(unit) <= 1.5:
                    unit.take_damage(self.max_health)

        # Remove the unit from the game
        game.remove_unit(self)

    def take_damage(self, damage: float) -> None:
        if self.shields > 0:
            if damage <= self.shields:
                self.shields -= damage
                return
            else:
                damage -= self.shields
                self.shields = 0
        
        self.health = max(0, self.health - damage)

# Create specific unit types
class Scout(MobileUnit):
    """
    The Scout is a fast, low-cost unit with low health and damage.

    Useful for taking advantage of openings in the enemy's defense.
    """
    def __init__(self):
        super().__init__("Scout", cost=1, health=15, range=3.5, damage=2, speed=1)

class Demolisher(MobileUnit):
    """
    The Demolisher is a slow, high-cost unit with high health and damage.

    Useful for breaking through enemy defenses and dealing heavy damage to structures.
    """
    def __init__(self):
        super().__init__("Demolisher", cost=3, health=5, range=4.5, damage=8, speed=2)

class Interceptor(MobileUnit):
    """
    The Interceptor is a slow, powerful, and cheap unit that demolishes enemy mobile attackers.

    Cannot damage structures.
    """
    def __init__(self):
        super().__init__("Interceptor", cost=1, health=40, range=4.5, damage=20, speed=4)

    def deal_damage(self, target):
        if isinstance(target, Structure):
            return 0  # Interceptors cannot damage structures
        return super().deal_damage(target)

class Structure(Unit):
    """
    Base class for all structure units in the game.

    Structure units are stationary units that provide support, defense, or attack capabilities.
    """
    def __init__(self, unit_type: str, cost: int, health: float, range: float, damage: float, 
                 upgrade_cost=None, upgrade_stats=None):
        """
        Initialization function.
        :param upgrade_cost: The cost to upgrade the unit.
        :param upgrade_stats: The stats to upgrade the unit by.
        """
        super().__init__(unit_type, cost, health, range, damage)
        self.upgrade_cost = upgrade_cost if upgrade_cost else cost
        self.upgrade_stats = upgrade_stats
        self.position = None  # To be set when deployed
        self.is_upgraded = False

    def upgrade(self):
        """
        Structures can be upgraded once to improve their stats.

        Damage taken persists through upgrades.
        """
        if not self.is_upgraded:
            self.is_upgraded = True
            if self.upgrade_stats:
                for key, value in self.upgrade_stats.items():
                    setattr(self, key, value)
            health_percentage = self.health / self.max_health
            self.max_health = self.upgrade_stats.get('health', self.max_health)
            self.health = int(self.max_health * health_percentage)

class Wall(Structure):
    """
    Simple defensive structure that provides a barrier against enemy units.
    """
    def __init__(self):
        super().__init__("Wall", cost=1, health=60, range=0, damage=0, 
                         upgrade_cost=1, upgrade_stats={'health': 120})

class Support(Structure):
    """
    Grants shielding to friendly units within range.

    Think of it like a Starcraft 2 shield battery!
    """
    def __init__(self):
        super().__init__("Support", cost=4, health=30, range=3.5, damage=0,
                         upgrade_stats={'range': 7, 'base_shielding': 4})
        self.base_shielding = 3
        self.shielded_units = set()

    def apply_shield(self, mobile_unit: MobileUnit):
        """
        Apply shield to a mobile unit if it hasn't been shielded by this support before.
        
        :param mobile_unit: The mobile unit to shield
        """
        if mobile_unit not in self.shielded_units:
            shield_amount = self.base_shielding
            if self.is_upgraded:
                shield_amount = self.upgrade_stats['base_shielding']
            mobile_unit.add_shield(shield_amount)
            self.shielded_units.add(mobile_unit)

class Turret(Structure):
    """
    High-health, high-damage, and high-cost defensive turret.
    """
    def __init__(self):
        super().__init__("Turret", cost=2, health=75, range=2.5, damage=5,
                         upgrade_cost=4, upgrade_stats={'damage': 15, 'range': 3.5})

    def attack(self, game_state):
        potential_targets = self.get_potential_targets(game_state)
        target = Targeting.select_target(self, potential_targets)
        if target:
            damage_dealt = self.deal_damage(target)
            return damage_dealt
        return 0

    def get_potential_targets(self, game_state):
        return [unit for unit in game_state.units 
                if isinstance(unit, MobileUnit) and unit.side != self.side 
                and self.distance_to(unit) <= self.range 
                and unit.health > 0]