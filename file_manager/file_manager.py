import collections
import dash_html_components as dash_html
import html
import pickle
from pathlib import Path

ReplayAnalysisNav = collections.namedtuple('ReplayAnalysisNav', 'display_name path url')


class FileManager:
    def __init__(self, config):
        try:
            if str.startswith(config['working_directory'], "%HOME%"):
                self.working_dir = Path(config['working_directory'].replace("%HOME%", str(Path.home())))
            else:
                self.working_dir = Path(config['working_directory'])

            if str.startswith(config['replay_directory'], "%HOME%"):
                self.replay_dir = Path(config['replay_directory'].replace("%HOME%", str(Path.home())))
            else:
                self.replay_dir = Path(config['replay_directory'])

            self.analyzed_replay_dir = self.working_dir / "analyzed_replays"

            if str.startswith(config['canonical_replay_directory'], "%HOME%"):
                self.canonical_dir = Path(config['canonical_replay_directory'].replace("%HOME%", str(Path.home())))
            else:
                self.canonical_dir = Path(config['canonical_replay_directory'])
        except KeyError as e:
            print("Failed to read directory configurations with error:\n", e)

    def get_replays_navs(self, size=10):
        navs = []
        files = self.replay_dir.glob("*")
        for file in sorted(files, key=lambda f: f.stat().st_ctime, reverse=True)[:size]:
            navs.append(ReplayAnalysisNav(file.name, file, html.escape(file.name)))
        return navs

    def get_analyzed_replays(self):
        # Make the directory if it doesn't exist
        self.analyzed_replay_dir.mkdir(parents=True, exist_ok=True)
        return self.analyzed_replay_dir.glob("*.analysis")

    def get_replay_analysis(self, name):
        found_replays = list(self.analyzed_replay_dir.glob("*" + name + ".analysis"))

        if not found_replays:
            # ToDo: start analysis for the replay if possible
            raise ValueError("Replay not found")
        elif len(found_replays) > 1:
            raise ValueError("Replay name ambiguous")
        else:
            return found_replays[0]

    def get_canonical_replays(self):
        return list(self.canonical_dir.glob("*SC2Replay"))

    def persist_encodings(self, encodings):
        with open(self.working_dir / "persisted_canonical_encodings", 'wb') as file:
            pickle.dump(encodings, file)

    def load_encodings_from_file(self):
        with open(self.working_dir / "persisted_canonical_encodings", 'rb') as file:
            return pickle.load(file)

    def persist_analysis(self, name, analysis):
        with open(self.analyzed_replay_dir / (name + ".analysis"), 'wb') as file:
            pickle.dump(analysis, file)

    def load_analysis_from_url(self, url):
        analysis_name = html.unescape(url[1:].replace("%20", " ")).replace('.SC2Replay', '') + '.analysis'
        file_name = self.analyzed_replay_dir / analysis_name
        print(file_name)
        try:
            with open(file_name, 'rb') as file:
                analysis = pickle.load(file)
            return analysis
        except FileNotFoundError:
            return dash_html.Div([dash_html.P(
                "Unable to load replay analysis. We're probably just not done processing, "
                "refresh to try again in a minute or so.")])

    def get_replays_reverse_chronological(self, size=10):
        files = self.replay_dir.glob("*")
        return sorted(files, key=lambda f: f.stat().st_ctime, reverse=True)[:size]

    def get_replay_from_url(self, url):
        return self.replay_dir / html.unescape(url[1:].replace("%20", " "))
