import heapq
from .units import Unit, MobileUnit, Structure
from typing import List, Union, Optional, Tuple
class Map:
    def __init__(self):
        self.width = 28
        self.height = 28
        self.grid: List = [[None for _ in range(self.width)] for _ in range(self.height)]

    def is_in_arena(self, x: int, y: int) -> bool:
        """
        Check if a given position is within the arena boundaries.
        """
        return abs(x - 13.5) + abs(y - 13.5) <= 13.5

    def place_unit(self, unit: Unit, x: int, y: int):
        """
        Place a unit on the map at the given position.
        """
        assert self.is_in_arena(x, y) # Redundant check
        unit.position = (x, y)
        if isinstance(unit, MobileUnit):
            # Mobile units can be stacked, so we'll store them in a list
            if self.map.grid[y][x] is None or not isinstance(self.map.grid[y][x], list):
                self.map.grid[y][x] = []
            self.map.grid[y][x].append(unit)
        else:
            # Structures cannot be stacked
            self.map.grid[y][x] = unit

class Pathfinder:
    """
    Pathing class that implements the A* algorithm to find the shortest path between two points on the map.

    See "Patching" section (https://terminal.c1games.com/rules#AdvancedInfo) for more information.
    """
    def __init__(self, game_map: Map):
        self.game_map = game_map

    def find_path(self, unit: MobileUnit, start: Tuple[int, int], target_edge: str) -> Optional[List[Tuple[int, int]]]:
        """
        Find the shortest path for a unit to reach a target edge.
        """
        destination = self.find_destination(start, target_edge)
        path = self.a_star(start, destination)
        return self.apply_movement_preferences(path, unit.last_move)

    def find_destination(self, start, target_edge):
        ""
        x, y = start
        possible_destinations = []

        if target_edge == 'top-left':
            for i in range(14):
                if self.game_map.is_in_arena(i, i) and self.is_reachable(start, (i, i)):
                    possible_destinations.append((i, i))
        elif target_edge == 'top-right':
            for i in range(14, 28):
                if self.game_map.is_in_arena(i, 27-i) and self.is_reachable(start, (i, 27-i)):
                    possible_destinations.append((i, 27-i))
        elif target_edge == 'bottom-left':
            for i in range(14):
                if self.game_map.is_in_arena(i, 27-i) and self.is_reachable(start, (i, 27-i)):
                    possible_destinations.append((i, 27-i))
        elif target_edge == 'bottom-right':
            for i in range(14, 28):
                if self.game_map.is_in_arena(i, i) and self.is_reachable(start, (i, i)):
                    possible_destinations.append((i, i))
        else:
            raise ValueError(f"Invalid target edge: {target_edge}")

        if not possible_destinations:
            return None

        # Return the destination that's deepest into enemy territory
        if target_edge.startswith('top'):
            return min(possible_destinations, key=lambda pos: pos[1])
        else:  # bottom edges
            return max(possible_destinations, key=lambda pos: pos[1])

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