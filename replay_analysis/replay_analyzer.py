import collections
import dash_html_components as html
import dash_core_components as dcc
import graph_maker.timeseries_graph as timeseries_graph
import re
from replay_analysis.sc2_replay.SC2Replay import PlayerReplayData, Sc2Replay
from replay_analysis.sc2_replay.build import Build
from .sc2_replay.units import UNITS

INT_MAX = 99999999999
CanonicalReplay = collections.namedtuple('CanonicalReplay', 'path player encoding')
UnitDisplayPair = collections.namedtuple('UnitDisplayPair', 'unit_tag unit_display_name')

UNIT_DISPLAY_PAIRS_BY_RACE = {
    race: [UnitDisplayPair(unit, re.sub(r"(\w)([A-Z])", r"\1 \2", unit)) for
           unit in
           UNITS[race]['army']] for race
    in
    UNITS.keys()}
UNIT_DISPLAY_PAIRS_BY_RACE["Protoss"] = [UnitDisplayPair("Probe", "Worker")] + UNIT_DISPLAY_PAIRS_BY_RACE["Protoss"]
UNIT_DISPLAY_PAIRS_BY_RACE["Terran"] = [UnitDisplayPair("SCV", "Worker")] + UNIT_DISPLAY_PAIRS_BY_RACE["Terran"]
UNIT_DISPLAY_PAIRS_BY_RACE["Zerg"] = [UnitDisplayPair("Drone", "Worker")] + UNIT_DISPLAY_PAIRS_BY_RACE["Zerg"]


def build_header(replay_name, players, canonical_replay_name, canonical_players):
    player_list = list(players.keys())
    canonical_player_list = list(canonical_players.keys())
    while len(player_list) < 2:
        player_list.append("")
    if len(player_list) > 2:
        player_list = ["Team", "Team"]
    while len(canonical_player_list) < 2:
        canonical_player_list.append("")
    return html.Div(
        [
            html.H3("{}: {} vs {}".format(replay_name, player_list[0], player_list[1])),
            html.H6("Closest canonical replay: {}; {} vs {}".format(
                canonical_replay_name, canonical_player_list[0], canonical_player_list[1])),
        ],
    )


def build_general_tab(player_key, player_data, canonical_data):
    return dcc.Tab(label="General", children=[
        dcc.Tab(label="Supply", children=[
            dcc.Dropdown(id='general-dropdown',
                         options=[{'label': 'Supply', 'value': 'Supply'},
                                  {'label': 'Army Value', 'value': 'ArmyValue'},
                                  {'label': 'Resources Lost', 'value': 'ResourcesLost'},
                                  {'label': 'Income', 'value': 'Income'},
                                  {'label': 'Mineral Income', 'value': 'MineralIncome'},
                                  {'label': 'Vespene Income', 'value': 'VespeneIncome'},
                                  ],
                         value='Supply'),
            dcc.Graph(
                figure=timeseries_graph.create_plotly_timeseries_graph(
                    [(player_key, player_data.get_supply_timeline()),
                     ("Target",
                      canonical_data.get_supply_timeline())],
                    title="Supply"),
                id="Supply"
            ),
            dcc.Graph(
                figure=timeseries_graph.create_plotly_timeseries_graph(
                    [(player_key, player_data.get_generic_timeline('army_value')),
                     ("Target",
                      canonical_data.get_generic_timeline('army_value'))],
                    title="Army Value"),
                id="ArmyValue"
            ),
            dcc.Graph(
                figure=timeseries_graph.create_plotly_timeseries_graph(
                    [(player_key, player_data.get_generic_timeline('resources_lost')),
                     ("Target",
                      canonical_data.get_generic_timeline('resources_lost'))],
                    title="Resources Lost"),
                id="ResourcesLost"),
            dcc.Graph(
                figure=timeseries_graph.create_plotly_timeseries_graph(
                    [(player_key, player_data.get_income_timeline()),
                     ("Target",
                      canonical_data.get_income_timeline())],
                    title="Income"),
                id="Income"
            ),
            dcc.Graph(
                figure=timeseries_graph.create_plotly_timeseries_graph(
                    [(player_key, player_data.get_income_timeline("MINERAL")),
                     ("Target",
                      canonical_data.get_income_timeline("MINERAL"))],
                    title="Mineral Income"),
                id="MineralIncome"
            ),
            dcc.Graph(
                figure=timeseries_graph.create_plotly_timeseries_graph(
                    [(player_key, player_data.get_income_timeline("VESPENE")),
                     ("Target",
                      canonical_data.get_income_timeline("VESPENE"))],
                    title="Vespene Gas Income"),
                id="VespeneIncome"
            )
        ])
    ])


def build_units_tab(player_key, player_data, canonical_data):
    unit_pairs = UNIT_DISPLAY_PAIRS_BY_RACE[player_data.race]
    dropdown_options = []
    graphs = []
    for unit_pair in unit_pairs:
        dropdown_options.append({'label': unit_pair.unit_display_name, 'value': unit_pair.unit_tag})
        graphs.append(dcc.Graph(
            figure=timeseries_graph.create_plotly_timeseries_graph(
                [(player_key, player_data.get_unit_timeline(unit_pair.unit_tag)),
                 ("Target", canonical_data.get_unit_timeline(unit_pair.unit_tag))], title=unit_pair.unit_display_name),
            id=unit_pair.unit_tag))
    return dcc.Tab(label="Units", children=[dcc.Dropdown(id='{}-units-dropdown'.format(player_data.race),
                                                         options=dropdown_options,
                                                         value={'Protoss': 'Probe', 'Terran': 'SCV',
                                                                'Zerg': 'Drone'}[player_data.race])] + graphs)


def build_tabbed_layout(player_key, player_data, canonical_data):
    return dcc.Tabs([
        build_general_tab(player_key, player_data, canonical_data),
        build_units_tab(player_key, player_data, canonical_data),
    ])


def create_encodings_for_canonical_replays(file_manager):
    canonical_replays = []
    for file in file_manager.get_canonical_replays():
        replay = Sc2Replay(str(file))
        for player in replay.players:
            build = Build(replay.players[player])
            canonical_replays.append(CanonicalReplay(file, player, build.get_build_encoding()))
    file_manager.persist_encodings(canonical_replays)
    return canonical_replays


def get_canonical_replays(file_manager):
    try:
        return file_manager.load_encodings_from_file()
    except FileNotFoundError:
        return create_encodings_for_canonical_replays(file_manager)


class ReplayAnalyzer:
    def __init__(self, player_names, file_manager):
        self.player_names = player_names
        self.file_manager = file_manager

    def find_nearest_neighbor(self, build_encoding):
        min_build_distance = INT_MAX
        canonical_entry = None
        for canonical_replay in get_canonical_replays(self.file_manager):
            _, _, encoding = canonical_replay
            build_distance = Build.encoding_distance(build_encoding, encoding)
            if build_distance < min_build_distance:
                min_build_distance = build_distance
                canonical_entry = canonical_replay
        return canonical_entry[0], canonical_entry[1]

    def get_analysis_for_file(self, path):
        replay = Sc2Replay(str(path))
        player_key = ""
        for player in replay.players:
            if player in self.player_names:
                player_key = player

        if not player_key:
            print("Replay does not contain data from configured player(s).")
            return None

        player_data = replay.players[player_key]
        canonical_path, canonical_player = self.find_nearest_neighbor(Build(player_data).get_build_encoding())
        canonical_replay = Sc2Replay(str(canonical_path))
        canonical_data = canonical_replay.players[canonical_player]

        return html.Div(
            [
                build_header(path.stem, replay.players, canonical_path.stem, canonical_replay.players),
                build_tabbed_layout(player_key, player_data, canonical_data)
            ],
        )
