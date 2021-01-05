import collections
import html
import pathlib
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

            if str.startswith(config['canonical_replay_directory'], "%HOME%"):
                self.canonical_dir = Path(config['canonical_replay_directory'].replace("%HOME%", str(Path.home())))
            else:
                self.canonical_dir = Path(config['canonical_replay_directory'])
        except KeyError as e:
            print("Failed to read directory configurations with error:\n", e)

    def get_replays_reverse_chronological(self, size=10):
        navs = []
        files = self.replay_dir.glob("*")
        for file in sorted(files, key=lambda f: f.stat().st_ctime, reverse=True)[:size]:
            navs.append(ReplayAnalysisNav(file.name, file, html.escape(file.name)))
        return navs

    def get_replay_from_url(self, url):
        return self.replay_dir / html.unescape(url[1:].replace("%20", " "))
