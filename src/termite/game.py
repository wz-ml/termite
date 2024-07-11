import heapq

class Map:
    def __init__(self):
        self.width = 28
        self.height = 28
        self.grid = [[None for _ in range(self.width)] for _ in range(self.height)]

    def is_in_arena(self, x, y):
        return abs(x - 13.5) + abs(y - 13.5) <= 13.5

    def place_unit(self, unit, x, y):
        if self.is_in_arena(x, y):
            self.grid[y][x] = unit
            unit.position = (x, y)

class Pathfinder:
    def __init__(self, game_map):
        self.game_map = game_map

    def find_path(self, unit, start, target_edge):
        destination = self.find_destination(start, target_edge)
        path = self.a_star(start, destination)
        return self.apply_movement_preferences(path, unit.last_move)

    def find_destination(self, start, target_edge):
        # Find the deepest reachable point on the target edge
        x, y = start
        if target_edge == 'top':
            return max((x, 0) for x in range(28) if self.game_map.is_in_arena(x, 0) and self.is_reachable(start, (x, 0)))
        elif target_edge == 'bottom':
            return max((x, 27) for x in range(28) if self.game_map.is_in_arena(x, 27) and self.is_reachable(start, (x, 27)))
        elif target_edge == 'left':
            return max((0, y) for y in range(28) if self.game_map.is_in_arena(0, y) and self.is_reachable(start, (0, y)))
        elif target_edge == 'right':
            return max((27, y) for y in range(28) if self.game_map.is_in_arena(27, y) and self.is_reachable(start, (27, y)))

    def a_star(self, start, goal):
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan distance

        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + 1

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None  # No path found

    def apply_movement_preferences(self, path, last_move):
        if not path or len(path) < 2:
            return path

        preferred_path = [path[0]]
        for i in range(1, len(path)):
            current = path[i-1]
            next_pos = path[i]
            move = (next_pos[0] - current[0], next_pos[1] - current[1])

            if move == last_move:
                # Try to find an alternative move
                alternatives = [n for n in self.get_neighbors(current) if n != next_pos and n in path]
                if alternatives:
                    next_pos = min(alternatives, key=lambda x: path.index(x))

            preferred_path.append(next_pos)
            last_move = (next_pos[0] - current[0], next_pos[1] - current[1])

        return preferred_path

    def is_blocked(self, position):
        x, y = position
        return self.game_map.grid[y][x] is not None and isinstance(self.game_map.grid[y][x], Structure)

    def get_neighbors(self, position):
        x, y = position
        neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        return [pos for pos in neighbors if self.game_map.is_in_arena(*pos) and not self.is_blocked(pos)]

    def is_reachable(self, start, end):
        return self.a_star(start, end) is not None

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
        self.units = [u for u in self.units if u.health > 0]

    def move_units(self):
        for unit in self.get_all_mobile_units():
            unit.move(self.pathfinder)

    def remove_destroyed_units(self):
        # Remove units with health <= 0
        destroyed_units = [unit for unit in self.units if unit.health <= 0]
        for unit in destroyed_units:
            self.units.remove(unit)
            x, y = unit.position
            self.map.grid[y][x] = None  # Clear the unit from the map

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
        if unit.has_moved_at_least_5_spaces:  # You'll need to track this in the MobileUnit class
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

    @property
    def has_moved_at_least_5_spaces(self):
        return self.distance_moved >= 5
    
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