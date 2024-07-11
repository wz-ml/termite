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