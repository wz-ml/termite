from .map import Pathfinder
from .game import TerminalGame

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
    def __init__(self, unit_type, cost, health, range, damage):
        self.unit_type = unit_type
        self.cost = cost
        self.health = health
        self.max_health = health
        self.range = range
        self.damage = damage
        self.position = None
        self.creation_time = None
        self.side = None

    def distance_to(self, other_unit):
        # Calculate Euclidean distance
        return ((self.position[0] - other_unit.position[0])**2 + 
                (self.position[1] - other_unit.position[1])**2)**0.5

    def progress_towards_side(self, other_unit):
        # Calculate how far the other unit is into this unit's side
        # This will depend on which side of the arena the unit is on
        if self.side == 'bottom':
            # For bottom player, progress is measured by how far up the unit has moved
            return 27 - other_unit.position[1]
        else:  # self.side == 'top'
            # For top player, progress is measured by how far down the unit has moved
            return other_unit.position[1]
        
    def distance_to_nearest_edge(self):
        # Calculate distance to the nearest edge of the arena
        x, y = self.position
        distances = [
            x,  # distance to left edge
            27 - x,  # distance to right edge
            y,  # distance to top edge
            27 - y  # distance to bottom edge
        ]
        return min(distances)
    
    def set_side(self, side):
        if side not in ['top', 'bottom']:
            raise ValueError("Side must be 'top' or 'bottom'")
        self.side = side

    def attack(self, target):
        if target and target.health > 0:
            target.take_damage(self.damage)

    def take_damage(self, damage):
        self.health = max(0, self.health - damage)

class MobileUnit(Unit):
    def __init__(self, unit_type, cost, health, range, damage, speed):
        super().__init__(unit_type, cost, health, range, damage)
        self.speed = speed
        self.shields = 0
        self.position = None  # To be set when deployed
        self.speed = speed
        self.frames_since_last_move = 0
        self.last_move = None
        self.path = []
        self.destination = None

    def add_shield(self, shield_amount):
        self.shields += shield_amount

    def move(self, game):
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
    
    def has_reached_enemy_edge(self, game):
        return (self.side == 'bottom' and self.position[1] == 0) or (self.side == 'top' and self.position[1] == 27)
    
    def attack(self, game_state):
        if self.has_attacked_this_frame:
            return  # Unit can only attack once per frame

        potential_targets = self.get_potential_targets(game_state)
        target = Targeting.select_target(self, potential_targets)

        if target:
            damage_dealt = self.deal_damage(target)
            self.has_attacked_this_frame = True
            return damage_dealt
        return 0

    def get_potential_targets(self, game_state):
        return [unit for unit in game_state.units 
                if unit.side != self.side 
                and self.distance_to(unit) <= self.range 
                and unit.health > 0]

    def deal_damage(self, target):
        damage = self.damage
        if isinstance(target, Structure) and self.unit_type == "Interceptor":
            return 0  # Interceptors cannot damage structures
        target.take_damage(damage)
        return damage

    def reset_attack_status(self):
        self.has_attacked_this_frame = False

    def self_destruct(self, game):
        if self.distance_moved >= 5:
            # Apply area damage
            for unit in game.units:
                if unit.side != self.side and self.distance_to(unit) <= 1.5:
                    unit.take_damage(self.max_health)

        # Remove the unit from the game
        game.remove_unit(self)

    def take_damage(self, damage):
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
    def __init__(self):
        super().__init__("Scout", cost=1, health=15, range=3.5, damage=2, speed=1)

class Demolisher(MobileUnit):
    def __init__(self):
        super().__init__("Demolisher", cost=3, health=5, range=4.5, damage=8, speed=2)

class Interceptor(MobileUnit):
    def __init__(self):
        super().__init__("Interceptor", cost=1, health=40, range=4.5, damage=20, speed=4)

    def deal_damage(self, target):
        if isinstance(target, Structure):
            return 0  # Interceptors cannot damage structures
        return super().deal_damage(target)

class Structure(Unit):
    def __init__(self, unit_type, cost, health, range, damage, upgrade_cost=None, upgrade_stats=None):
        super().__init__(unit_type, cost, health, range, damage)
        self.upgrade_cost = upgrade_cost if upgrade_cost else cost
        self.upgrade_stats = upgrade_stats
        self.position = None  # To be set when deployed
        self.is_upgraded = False

    def upgrade(self):
        if not self.is_upgraded:
            self.is_upgraded = True
            if self.upgrade_stats:
                for key, value in self.upgrade_stats.items():
                    setattr(self, key, value)
            health_percentage = self.health / self.max_health
            self.max_health = self.upgrade_stats.get('health', self.max_health)
            self.health = int(self.max_health * health_percentage)

class Wall(Structure):
    def __init__(self):
        super().__init__("Wall", cost=1, health=60, range=0, damage=0, 
                         upgrade_cost=1, upgrade_stats={'health': 120})

class Support(Structure):
    def __init__(self):
        super().__init__("Support", cost=4, health=30, range=3.5, damage=0,
                         upgrade_stats={'range': 7, 'base_shielding': 4})
        self.base_shielding = 3
        self.shielded_units = set()

    def apply_shield(self, mobile_unit):
        if mobile_unit not in self.shielded_units:
            shield_amount = self.base_shielding
            if self.is_upgraded:
                shield_amount = self.upgrade_stats['base_shielding']
            mobile_unit.add_shield(shield_amount)
            self.shielded_units.add(mobile_unit)

class Turret(Structure):
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