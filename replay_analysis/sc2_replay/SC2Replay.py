import json

from collections import namedtuple
from mpyq import MPQArchive
from s2protocol.versions import build, list_all, latest
from replay_analysis.sc2reader import Sc2ReplayReader
from .PlayerReplayData import standardize_name
from .PlayerReplayData import Entity as Entity, UnitId
from .PlayerReplayData import PlayerReplayData as PlayerReplayData
from .PlayerReplayData import Snapshot as Snapshot
from .units import UNITS as UNITS

Map = namedtuple('Map', ['name', 'width', 'height'])
event_set = set()
a = True

UNIT_ID_TO_UNIT = {}


def event_to_uid(event):
    return (event['m_unitTagIndex'] << 18) | event['m_unitTagRecycle']


def handle_unit_started(replay, event):  # eventid == 1
    if event['m_controlPlayerId'] > 0:
        player_name = replay.playerIdToName[event['m_controlPlayerId']]
        unit_id = UnitId(event['m_unitTagIndex'], event['m_unitTagRecycle'])
        entity = Entity(unit_id,
                        player_name, event['m_unitTypeName'].decode())
        replay.players[player_name].start_production_at_time(event['_gameloop'], entity)
        UNIT_ID_TO_UNIT[unit_id] = entity
    return


def handle_unit_born(replay, event):  # eventid == 6
    if event['m_controlPlayerId'] > 0:
        player_name = replay.playerIdToName[event['m_controlPlayerId']]
        unit_id = UnitId(event['m_unitTagIndex'], event['m_unitTagRecycle'])
        entity = Entity(unit_id,
                        player_name, event['m_unitTypeName'].decode())
        replay.players[replay.playerIdToName[event['m_controlPlayerId']]]\
            .unit_born_at_time(event['_gameloop'], entity)
        UNIT_ID_TO_UNIT[unit_id] = entity
    return


def handle_unit_died(replay, event):  # eventid == 2
    # ignore KeyErrors, things like forcefields trigger this event and we're not
    # tracking them.
    try:
        unit = UNIT_ID_TO_UNIT[UnitId(event['m_unitTagIndex'], event['m_unitTagRecycle'])]
        replay.players[unit.owning_player].unit_died_at_time(event['_gameloop'], unit)
    except KeyError:
        pass
    return


def handle_unit_finished(replay, event):  # eventid == 7
    unit = UNIT_ID_TO_UNIT[UnitId(event['m_unitTagIndex'], event['m_unitTagRecycle'])]
    replay.players[unit.owning_player].finish_production_at_time(event['_gameloop'], unit)
    return


def handle_upgrade(replay, event):  # eventid == 5
    return


def handle_unit_changed(replay, event):  # eventid == 4
    return


def handle_unit_position(replay, event): # eventid == 8
    return


def handle_other(replay, event):
    return


EVENT_HANDLERS = {
        "NNet.Replay.Tracker.SUnitInitEvent": handle_unit_started,
        "NNet.Replay.Tracker.SUnitDiedEvent": handle_unit_died,
        "NNet.Replay.Tracker.SUnitDoneEvent": handle_unit_finished,
        "NNet.Replay.Tracker.SUpgradeEvent": handle_upgrade,
        "NNet.Replay.Tracker.SUnitTypeChangeEvent": handle_unit_changed,
        "NNet.Replay.Tracker.SUnitPositionsEvent": handle_unit_position,
        # Generating units through ways other than buildings. Example: larva, broodlings, warp-in
        "NNet.Replay.Tracker.SUnitBornEvent": handle_unit_born,
}


class Sc2Replay:

    def __init__(self, replay_path):
        # Public member variables
        self.players = {}
        self.game_length = 0
        self.game_loops = 0
        self.race = None
        self.replay_path = replay_path

        # Private member variables
        self.parsed_details = {}
        self.parsed_economy_data = {}
        self.parsed_worker_data = {}
        self.parsed_army_data = {}
        self.parsed_structure_data = {}
        self.playerIdToUserId = {}
        self.playerIdToName = {}

        reader = Sc2ReplayReader(replay_path)
        replay_metadata = reader.get_replay_init_data()
        replay_header = reader.get_replay_header()
        replay_details = reader.get_replay_details()

        economy_events, unit_events = \
                self.parse_tracker_events(replay_details, reader.get_replay_tracker_events())

        self.parse_replay_details(reader, replay_header, replay_details, replay_metadata)

        for event in economy_events:
            player_name = self.playerIdToName[event['m_playerId']]
            self.players[player_name].update_economy(event['_gameloop'], event)

        for event in unit_events:
            EVENT_HANDLERS.get(event['_event'], handle_other)(self, event)

        for player in self.players:
            self.players[player].finalize_timeline()

    def parse_tracker_events(self, replay_details, tracker_events):
        last_registered_game_loop = tracker_events[-1]['_gameloop']
        self.game_loops = last_registered_game_loop + 1
        self.game_length = last_registered_game_loop / 24.0 # in seconds and corresponds with ggtracker

        economy_data = []
        unit_data = []
        for event in tracker_events:
            if event['_event'] == 'NNet.Replay.Tracker.SPlayerSetupEvent':
                player = replay_details['m_playerList'][event['m_playerId']-1]
                name = standardize_name(player['m_name'])

                self.playerIdToName[event['m_playerId']] = name
                self.playerIdToUserId[event['m_playerId']] = event['m_userId']
                self.race = player['m_race']

            elif event['_event'] == 'NNet.Replay.Tracker.SPlayerStatsEvent':
                economy_data.append(event)
            elif 0 < event['_eventid'] < 9:
                unit_data.append(event)

        return economy_data, unit_data

    def parse_replay_details(self, reader, replay_header, replay_details, replay_metadata):
        self.elapsedGameLoops = replay_header['m_elapsedGameLoops']
        self.game_version = reader.get_replay_protocol_version()
        self.map = Map(
                replay_details['m_title'],
                replay_metadata['m_syncLobbyState']['m_gameDescription']['m_mapSizeX'],
                replay_metadata['m_syncLobbyState']['m_gameDescription']['m_mapSizeY'])

        self.mapName = replay_details['m_title']
        # Black magic, found at https://github.com/karlgluck/heroes-of-the-storm-replay-parser
        self.gameStart = (replay_details['m_timeUTC'] / 10000000) - 11644473600
        self.isBlizzardMap = replay_details['m_isBlizzardMap']
        self.gameSpeed = replay_details['m_gameSpeed']
        parsed_player_list = []
        for e in replay_details['m_playerList']:
            self.players[standardize_name(e['m_name'])] = (PlayerReplayData(e, UNITS, self.game_loops))


def first_char_to_lower(s):  s[:1].lower() + s[1:] if s else ''
