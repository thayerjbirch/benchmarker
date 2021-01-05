import collections
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from replay_analysis.sc2_replay.SC2Replay import PlayerReplayData, Sc2Replay
from replay_analysis.sc2_replay.build import Build
import graph_maker.timeseries_graph as timeseries_graph

INT_MAX = 99999999999
CanonicalReplay = collections.namedtuple('CanonicalReplay', 'path player encoding')


def build_header(replay_name, players, canonical_replay_name, canonical_players):
    player_list = list(players.keys())
    canonical_player_list = list(canonical_players.keys())
    while len(player_list) < 2:
        player_list.append("")
    while len(canonical_player_list) < 2:
        canonical_player_list.append("")
    return html.Div(
        [
            html.H3("{}: {} vs {}".format(replay_name, player_list[0], player_list[1])),
            html.H6("Closest canonical replay: {}; {} vs {}".format(
                canonical_replay_name, canonical_player_list[0], canonical_player_list[1])),
        ],
    )


class ReplayAnalyzer:
    def __init__(self, player_names, canonical_dir):
        self.player_names = player_names
        files = canonical_dir.glob("*SC2Replay")
        self.canonical_replays = []
        for file in files:
            replay = Sc2Replay(str(file))
            for player in replay.players:
                build = Build(replay.players[player])
                self.canonical_replays.append(CanonicalReplay(file, player, build.get_build_encoding()))
            pass
        if not self.canonical_replays:
            print("No canonical replays found, exiting.")
            exit(1)

    def find_nearest_neighbor(self, build_encoding):
        min_build_distance = INT_MAX
        canonical_entry = None
        for canonical_replay in self.canonical_replays:
            _, _, encoding = canonical_replay
            build_distance = Build.encoding_distance(build_encoding, encoding)
            if build_distance < min_build_distance:
                min_build_distance = build_distance
                canonical_entry = canonical_replay
        return canonical_entry[0], canonical_entry[1]

    def build_tabbed_layout(self, player_key, player_data, canonical_data):
        return dcc.Tabs([
            dcc.Tab(label="Supply", children=[
                dcc.Graph(
                    figure=timeseries_graph.create_plotly_timeseries_graph(
                        [(player_key, player_data.get_supply_timeline()),
                         ("Target",
                          canonical_data.get_supply_timeline())],
                        title="Supply")
                )
            ]),
            dcc.Tab(label="Workers", children=[
                dcc.Graph(
                    figure=timeseries_graph.create_plotly_timeseries_graph(
                        [(player_key, player_data.get_unit_timeline("worker")),
                         ("Target",
                          canonical_data.get_unit_timeline("worker"))],
                        title="Workers")
                )
            ])
        ])

    def get_analysis_for_file(self, path):
        replay = Sc2Replay(str(path))
        player_key = ""
        for player in replay.players:
            if player in self.player_names:
                player_key = player_key = player

        if not player_key:
            print("Replay does not contain data from configured player(s).")
            return None

        player_data = replay.players[player_key]
        canonical_path, canonical_player = self.find_nearest_neighbor(Build(player_data).get_build_encoding())
        canonical_replay = Sc2Replay(str(canonical_path))
        canonical_data = canonical_replay.players[canonical_player]

        return html.Div(
            [
                build_header(path.name, replay.players, canonical_path.name, canonical_replay.players),
                self.build_tabbed_layout(player_key, player_data, canonical_data)
            ],
        )
