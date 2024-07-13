from termite.game import TerminalGame, Player
from termite.units import Scout, Demolisher, Interceptor, Turret, Support, Wall
import pickle as pkl
import pytest

class EvalPlayer(Player):
    def deploy(self, game_state, deploy_str: str):
        deployed_units = []
        for unit_str in deploy_str.split(','):
            unit_type, x, y = unit_str.split()
            unit = self.create_unit(unit_type)
            if unit:
                deployed_units.append((unit, (int(x), int(y))))
        return deployed_units
    def create_unit(self, unit_type):
        if unit_type == "scout" and self.mobile_points >= 1:
            return Scout()
        elif unit_type == "demolisher" and self.mobile_points >= 3:
            return Demolisher()
        elif unit_type == "interceptor" and self.mobile_points >= 1:
            return Interceptor()
        elif unit_type == "wall" and self.structure_points >= 1:
            return Wall()
        elif unit_type == "support" and self.structure_points >= 4:
            return Support()
        elif unit_type == "turret" and self.structure_points >= 2:
            return Turret()
        else:
            return None
        
@pytest.fixture
def evalgame():
    return TerminalGame(EvalPlayer(), EvalPlayer())

def get_new_evalgame():
    return TerminalGame(EvalPlayer(), EvalPlayer())

def test_one_scout(evalgame):
    with open("init_state.pkl", "rb") as f:
        init_state = pkl.load(f)
    assert evalgame.get_game_state() == init_state

    # dep = ["scout 5 8", "scout 11 12"]
    # for idx, player in enumerate((evalgame.player1, evalgame.player2)):
    #     player_deployments = player.deploy(None, dep[idx])
        
    #     for deployment in player_deployments:
    #         unit, position = deployment
    #         if evalgame.is_valid_deployment(player, unit, position):
    #             if player.can_afford(unit):
    #                 evalgame.place_unit(player, unit, position)
    #                 player.deduct_cost(unit)
    #             else:
    #                 print(f"Player cannot afford to deploy {unit.unit_type}")
    #         else:
    #             print(f"Invalid deployment: {unit.unit_type} at {position}")
    # evalgame.upgrade_phase()

    # with open("dep_1_scout_1.pkl", "rb") as f:
    #     s = pkl.load(f)
    # assert evalgame.get_game_state() == s

    evalgame = get_new_evalgame()
    evalgame.player1.mobile_points = 1
    units = evalgame.player1.deploy(None, "scout 0 0")
    assert len(units) == 1
    assert isinstance(units[0][0], Scout)
    assert units[0][1] == (0, 0)