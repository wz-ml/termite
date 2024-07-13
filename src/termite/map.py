import heapq
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
        return abs(x - 13.5) + abs(y - 13.5) <= 14

    def place_unit(self, unit: 'Unit', x: int, y: int):
        """
        Place a unit on the map at the given position.
        """
        assert self.is_in_arena(x, y) # Redundant check
        if isinstance(unit, MobileUnit):
            # Mobile units can be stacked, so we'll store them in a list
            if self.grid[y][x] is None or not isinstance(self.map.grid[y][x], list):
                self.grid[y][x] = []
            self.grid[y][x].append(unit)
        else:
            # Structures cannot be stacked
            self.grid[y][x] = unit

    def clear(self):
        """
        Clear the map of all mobile units.
        """
        for y in range(self.height):
            for x in range(self.width):
                if isinstance(self.grid[y][x], list):
                    self.grid[y][x] = None
        return self
class Pathfinder:
    """
    Pathing class that implements the A* algorithm to find the shortest path between two points on the map.

    See "Patching" section (https://terminal.c1games.com/rules#AdvancedInfo) for more information.

    A lot of code is ported from the Terminal python-algo starter kit.
    """
    def __init__(self, game_map: Map):
        self.game_map = game_map
        self.HORIZONTAL = 1
        self.VERTICAL = 2

    def find_path(self, unit: 'MobileUnit', start: Tuple[int, int], target_edge: str) -> List[Tuple[int, int]]:
        print(target_edge)
        end_points = self._get_end_points(target_edge)
        print(end_points)
        ideal_endpoint = self._idealness_search(start, end_points)
        print(ideal_endpoint)
        self._validate(ideal_endpoint, end_points)
        return self._get_path(start, end_points)

    def _get_end_points(self, target_edge: str) -> List[Tuple[int, int]]:
        """
        Returns the most ideal targets to reach based on the target edge.
        """
        end_points = []
        if target_edge == 'top-left':
            end_points = [(x, x + 14) for x in range(0, 14) if self.game_map.is_in_arena(x, x)]
        elif target_edge == 'top-right':
            end_points = [(x, 41-x) for x in range(14, 28) if self.game_map.is_in_arena(x, 27-x)]
        elif target_edge == 'bottom-left':
            end_points = [(x, 13-x) for x in range(0, 14) if self.game_map.is_in_arena(x, 27-x)]
        elif target_edge == 'bottom-right':
            end_points = [(x, x-14) for x in range(14, 28) if self.game_map.is_in_arena(x, x)]
        return end_points

    def _idealness_search(self, start: Tuple[int, int], end_points: List[Tuple[int, int]]) -> Tuple[int, int]:
        """
        Implements a BFS to find the most ideal reachable point.

        :param start: The starting point of the search.
        :param end_points: The target points to reach.
        :return: The most ideal point to reach.
        """
        queue = [start]
        visited = set([start])
        best_idealness = self._get_idealness(start, end_points)
        most_ideal = start

        while queue:
            current = queue.pop(0)
            for neighbor in self._get_neighbors(current):
                if neighbor not in visited and self.game_map.is_in_arena(*neighbor) and not self._is_blocked(neighbor):
                    visited.add(neighbor)
                    queue.append(neighbor)
                    current_idealness = self._get_idealness(neighbor, end_points)
                    if current_idealness > best_idealness:
                        best_idealness = current_idealness
                        most_ideal = neighbor

        return most_ideal

    def _get_neighbors(self, location: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Get the neighbors of a given location.
        """
        x, y = location
        return [(x, y + 1), (x, y - 1), (x + 1, y), (x - 1, y)]

    def _get_idealness(self, location: Tuple[int, int], end_points: List[Tuple[int, int]]) -> int:
        """
        Calculates the idealness of a location based on its distance from the target edge 
        and how deep it's in the enemy territory.
        """
        if location in end_points:
            return float('inf')
        
        direction = self._get_direction_from_endpoints(end_points)
        x, y = location
        idealness = 0
        
        if direction[1] == 1:
            idealness += 28 * y
        else:
            idealness += 28 * (27 - y)
        
        if direction[0] == 1:
            idealness += x
        else:
            idealness += (27 - x)
        
        return idealness

    def _get_direction_from_endpoints(self, end_points: List[Tuple[int, int]]) -> Tuple[int, int]:
        """
        Get the direction of the target edge based on the end points.

        param end_points: A set of endpoints on the target edge of the map.
        :return: A direction [x,y] representing the edge. For example, [1,1] for the top right and [-1, 1] for the top left
        """
        point = end_points[0]
        x, y = point
        direction = [1, 1]
        if x < 14:
            direction[0] = -1
        if y < 14:
            direction[1] = -1
        return tuple(direction)

    def _validate(self, ideal_tile: Tuple[int, int], end_points: List[Tuple[int, int]]):
        """
        Scan with BFS from the ideal point to calculate pathlengths from all reachable points.
        """
        queue = [ideal_tile] if ideal_tile not in end_points else end_points.copy()
        visited = set(queue)
        pathlengths = {pos: 0 for pos in queue}

        while queue:
            current = queue.pop(0)
            for neighbor in self._get_neighbors(current):
                if neighbor not in visited and self.game_map.is_in_arena(*neighbor) and not self._is_blocked(neighbor):
                    visited.add(neighbor)
                    queue.append(neighbor)
                    pathlengths[neighbor] = pathlengths[current] + 1

        self.pathlengths = pathlengths

    def _get_path(self, start: Tuple[int, int], end_points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Once all nodes are validated, and a target is found, the unit can path to its target.

        Don't call this function directly, unless it's necessary for your decision-making.
        Use choose_next_move instead.
        """
        path = [start]
        current = start
        move_direction = 0

        while current not in end_points and self.pathlengths.get(current, float('inf')) > 0:
            next_move = self._choose_next_move(current, move_direction, end_points)
            if current[0] == next_move[0]:
                move_direction = self.VERTICAL
            else:
                move_direction = self.HORIZONTAL
            path.append(next_move)
            current = next_move

        return path

    def _choose_next_move(self, current: Tuple[int, int], previous_move_direction: int, end_points: List[Tuple[int, int]]) -> Tuple[int, int]:
        """
        Implements movement preferences as detailed in "Patching."

        Yields the distinctive zigzag movement pattern.        

        :param current: The current position of the unit.
        :param previous_move_direction: The direction of the previous move.
        :param end_points: The target points to reach.
        :return: The next position to move to.
        """
        neighbors = self._get_neighbors(current)
        valid_neighbors = [n for n in neighbors if self.game_map.is_in_arena(*n) and not self._is_blocked(n)]
        
        ideal_neighbor = min(valid_neighbors, key=lambda n: (self.pathlengths.get(n, float('inf')), 
                                                             not self._better_direction(current, n, current, previous_move_direction, end_points)))
        return ideal_neighbor

    def _better_direction(self, prev_tile: Tuple[int, int], new_tile: Tuple[int, int], prev_best: Tuple[int, int], 
                          previous_move_direction: int, end_points: List[Tuple[int, int]]) -> bool:
        """
        Returns if the new tile is a better direction than the previous best tile.

        Favors alternating horizontal and vertical movements.
        """
        if previous_move_direction == self.HORIZONTAL and new_tile[0] != prev_best[0]:
            return prev_tile[1] != new_tile[1]
        if previous_move_direction == self.VERTICAL and new_tile[1] != prev_best[1]:
            return prev_tile[0] != new_tile[0]
        if previous_move_direction == 0:
            return prev_tile[1] != new_tile[1]
        
        direction = self._get_direction_from_endpoints(end_points)
        if new_tile[1] == prev_best[1]:  # If they both moved horizontal...
            return (direction[0] == 1 and new_tile[0] > prev_best[0]) or (direction[0] == -1 and new_tile[0] < prev_best[0])
        if new_tile[0] == prev_best[0]:  # If they both moved vertical...
            return (direction[1] == 1 and new_tile[1] > prev_best[1]) or (direction[1] == -1 and new_tile[1] < prev_best[1])
        return True

    def _is_blocked(self, position: Tuple[int, int]) -> bool:
        x, y = position
        return isinstance(self.game_map.grid[y][x], Structure)

# Prevent circular import
from .units import Unit, MobileUnit, Structure