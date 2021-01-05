
from enum import Enum
from datetime import timedelta
from .PlayerReplayData import PlayerReplayData
from .units import UNITS as units

Matchup = Enum('Matchup', 'PvP PvT PvZ TvT TvZ TvP ZvZ ZvT ZvP other')

MAX_LOOPS_TO_COLLAPSE = 160
EXPANSIONS = ["Nexus", "CommandCenter", "Hatchery"]


# Converts games loops to time in format MM:SS
def loops_to_timestring(t):
    return str(timedelta(seconds=int(t / 22.4)))[2:]


def levenshtein_distance(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


class Build:

    def __init__(self, player_data: PlayerReplayData, matchup: Matchup = Matchup.other):
        self.matchup = matchup
        self.player_data = player_data

        self._building_encoding_map = self.create_encoding()
        # Lazy evaluated string encoding of the build
        self._build_encoding = None

    def __str__(self):
        return '\n'.join(["{} -- {}".format(self.player_data.name, self.matchup.name), "Time     Supply    Build"] \
                + Build.condense_build(self.player_data.build_events))

    def create_encoding(self):
        structures = units[self.player_data.race]['structures']
        mapping = {}
        # assigning each structure to a lowercase character
        for i in range(len(structures)):
            mapping[structures[i]] = chr(i + 97)
        return mapping

    def get_build_encoding(self):
        if self._build_encoding is None:
            encoding_chars = []
            for event in self.player_data.build_events:
                if not event.is_unit: # We're only looking at structures
                    encoding_chars.append(self._building_encoding_map[event.entity])
            self._build_encoding = ''.join(encoding_chars)
        return self._build_encoding

    @staticmethod
    def condense_build(build_events):
        build_lines = []
        i = 0

        while i < len(build_events):
            start_time = build_events[i].time
            is_unit = build_events[i].is_unit
            j = i+1
            if build_events[i].entity not in EXPANSIONS: # keep expansions on their own entry
                while j < len(build_events) \
                        and build_events[j].time - start_time < MAX_LOOPS_TO_COLLAPSE \
                        and build_events[j].is_unit == is_unit \
                        and build_events[j].entity not in EXPANSIONS:
                    j += 1

            build_lines.append(Build.condense_lines(build_events[i:j]))
            i = j
        return build_lines

    @staticmethod
    def condense_lines(close_events):
        line_elements = []
        event_dict = {}
        # using the timestamp and supply of the first event
        time = close_events[0].time
        supply = close_events[0].supply

        for event in close_events:
            event_dict[event.entity] = event_dict.get(event.entity, 0) + 1

        for key in event_dict:
            if event_dict[key] > 1:
                line_elements.append("{} x{}".format(str(key), event_dict[key]))
            else:
                line_elements.append(str(key))

        return "{}    {:>6}    {}".format(loops_to_timestring(time), int(supply), ", ".join(line_elements))

    @staticmethod
    def distance(build1: 'Build', build2: 'Build'):
        return levenshtein_distance(build1.get_build_encoding(), build2.get_build_encoding())

    @staticmethod
    def encoding_distance(build1_encoding: 'str', build2_encoding: 'str'):
        return levenshtein_distance(build1_encoding, build2_encoding)
