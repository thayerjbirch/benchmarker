import copy
from collections import namedtuple
import html

UnitId = namedtuple('UnitId', ['tag_index', 'tag_recycle'])
Entity = namedtuple('Entity', ['unit_id', 'owning_player', 'type'])
BuildEntry = namedtuple('BuildEntry', ['time', 'supply', 'entity', 'is_unit'])


def standardize_name(name):
    return html.unescape(name.decode('utf8')).split("<sp/>")[-1]


class Snapshot:
    def __init__(self, parent, last_snapshot, game_loop):
        self.parent = parent
        self.last_snapshot = last_snapshot
        self.mineral_income = 0
        self.vespene_income = 0
        self.supply = None
        self.resources_lost = 0
        self.army_value = 0
        self.tech_value = 0
        self.economy_value = 0
        self.units = None
        self.in_production = None
        self.structures = None
        self.game_loop = game_loop

    def get_units(self):
        # If we don't have current state for this snapshot, go backwards in time
        # unit we find a snapshot that has the state at that time, then propagate
        # that state forward and apply the delta at this timestamp.
        if self.units is None:
            snapshot_stack = []
            snapshot = self
            while snapshot.units is None:
                snapshot_stack.append(snapshot)
                if snapshot.last_snapshot is not None:
                    snapshot = snapshot.last_snapshot
                else:  # if we hit time = 0, just fill an empty dictionary
                    snapshot.units = {}
            while snapshot_stack:
                snapshot = snapshot_stack.pop()
                if snapshot.last_snapshot:
                    snapshot.units = copy.deepcopy(snapshot.last_snapshot.units)
        return self.units

    def get_in_production(self):
        # If we don't have current state for this snapshot, go backwards in time
        # unit we find a snapshot that has the state at that time, then propagate
        # that state forward and apply the delta at this timestamp.
        if self.in_production is None:
            snapshot_stack = []
            snapshot = self
            while snapshot.in_production is None:
                snapshot_stack.append(snapshot)
                if snapshot.last_snapshot is not None:
                    snapshot = snapshot.last_snapshot
                else:  # if we hit time = 0, just fill an empty dictionary
                    snapshot.in_production = {}
            while snapshot_stack:
                snapshot = snapshot_stack.pop()
                if snapshot.last_snapshot:
                    snapshot.in_production = copy.deepcopy(snapshot.last_snapshot.in_production)
        return self.in_production

    def get_structures(self):
        if self.structures is None:
            snapshot_stack = []
            snapshot = self
            while snapshot.structures is None:
                snapshot_stack.append(snapshot)
                if snapshot.last_snapshot is not None:
                    snapshot = snapshot.last_snapshot
                else:  # if we hit time = 0, just fill an empty dictionary
                    snapshot.structures = {}
            while snapshot_stack:
                snapshot = snapshot_stack.pop()
                if snapshot.last_snapshot:
                    snapshot.structures = copy.deepcopy(snapshot.last_snapshot.structures)
        return self.structures

    def get_supply(self):
        if self.supply is None:
            snapshot_stack = []
            snapshot = self
            while snapshot.supply is None:
                snapshot_stack.append(snapshot)
                if snapshot.last_snapshot is not None:
                    snapshot = snapshot.last_snapshot
                else:  # if we hit time = 0, just fill with 0
                    snapshot.supply = 0
            while snapshot_stack:
                snapshot = snapshot_stack.pop()
                if snapshot.last_snapshot:
                    snapshot.supply = snapshot.last_snapshot.supply
        return self.supply

    def update_economy(self, event):
        stats = event['m_stats']
        self.mineral_income = stats.get('m_scoreValueMineralsCollectionRate', 0)
        self.vespene_income = stats.get('m_scoreValueVespeneCollectionRate', 0)
        self.supply = stats.get('m_scoreValueFoodUsed', 0) / 4096
        for stat, value in stats.items():
            if 'Lost' in stat:
                self.resources_lost += value
            elif 'UsedCurrentArmy' in stat:
                self.army_value += value
            elif 'UsedCurrentEconomy' in stat:
                self.economy_value += value
            elif 'UsedCurrentTech' in stat:
                self.tech_value += value

    def start_production(self, entity_name):
        in_production = self.get_in_production()
        in_production[entity_name] = in_production.get(entity_name, 0) + 1

    def finish_production(self, unit):
        in_production = self.get_in_production()
        if unit.type in in_production:
            in_production[unit.type] -= 1
        else:
            print(unit.type)
        if in_production[unit.type] == 0:
            del (in_production[unit.type])
        self.unit_born(unit)

    def unit_born(self, unit):
        if unit.type in self.parent.available_units:
            units = self.get_units()
            units[unit.type] = units.get(unit.type, 0) + 1
            self.parent.unit_id_to_type[unit.unit_id] = unit.type

    def unit_died(self, unit):
        units = self.get_units()
        if unit.type in units:
            units[unit.type] = units[unit.type] - 1
            if units[unit.type] == 0:
                del (units[unit.type])


class PlayerReplayData:
    def __init__(self, player_detail_dict, entity_dict, game_loops):
        self.timeseries = []
        self.build_events = []
        last_snapshot = None
        for x in range(game_loops):
            # replay is a set of deltas, we have to build state as we go
            snapshot = Snapshot(self, last_snapshot, x)
            self.timeseries.append(snapshot)
            last_snapshot = snapshot

        color = {
            'r': player_detail_dict['m_color']['m_r'],
            'g': player_detail_dict['m_color']['m_g'],
            'b': player_detail_dict['m_color']['m_b'],
            'a': player_detail_dict['m_color']['m_a'],
        }
        self.color = color
        self.teamId = player_detail_dict['m_teamId']
        self.observe = player_detail_dict['m_observe']
        self.control = player_detail_dict['m_control']
        self.race = player_detail_dict['m_race'].decode()
        self.handicap = player_detail_dict['m_handicap']
        self.name = standardize_name(player_detail_dict['m_name'])
        self.result = player_detail_dict['m_result']
        self.region = player_detail_dict['m_toon']['m_region']
        self.available_structures = entity_dict[self.race]["structures"]
        self.available_units = entity_dict[self.race]["army"] + entity_dict[self.race]["worker"]

        # used for looking up events that map to a specific unit
        self.unit_id_to_type = {}

    def update_economy(self, game_loop, snapshot):
        self.timeseries[game_loop].update_economy(snapshot)

    def start_production_at_time(self, game_loop, entity):
        self.timeseries[game_loop].start_production(entity.type)

        if game_loop > 0:
            if entity.type in self.available_structures:
                self.build_events.append(
                    BuildEntry(game_loop, self.timeseries[game_loop].get_supply(), entity.type, False))
            if entity.type in self.available_units:
                self.build_events.append(
                    BuildEntry(game_loop, self.timeseries[game_loop].get_supply(), entity.type, True))

    def finish_production_at_time(self, game_loop, unit):
        self.timeseries[game_loop].finish_production(unit)

    def unit_born_at_time(self, game_loop, unit):
        self.timeseries[game_loop].unit_born(unit)

    def unit_died_at_time(self, game_loop, unit):
        self.timeseries[game_loop].unit_died(unit)
        return

    def get_unit_timeline(self, unit_param: str):
        unit = unit_param
        if unit == 'worker':
            unit = {'Protoss': 'Probe', 'Terran': 'SCV', 'Zerg': 'Drone'}[self.race]
        return [snapshot.get_units().get(unit, 0) for snapshot in self.timeseries][10:]

    def get_supply_timeline(self):
        return [snapshot.get_supply() for snapshot in self.timeseries][10:]
