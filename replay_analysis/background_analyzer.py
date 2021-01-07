import time
from .replay_analyzer import create_encodings_for_canonical_replays

ANALYSIS_TO_KEEP = 30


def analyze_files_in_background(file_manager, replay_analyzer):
    time.sleep(15)
    analyzed_replays = list(file_manager.get_analyzed_replays())
    analyzed_replay_set = set([replay.stem for replay in analyzed_replays])

    for replay in file_manager.get_replays_reverse_chronological(size=10):
        if replay.stem not in analyzed_replays:
            analysis = replay_analyzer.get_analysis_for_file(replay)
            file_manager.persist_analysis(replay.stem, analysis)

    if len(analyzed_replays) > ANALYSIS_TO_KEEP:
        analyzed_replays = sorted(analyzed_replays, key=lambda f: f.stat().st_ctime, reverse=True)
        while len(analyzed_replays) > ANALYSIS_TO_KEEP:
            analyzed_replays[0].unlink()
            analyzed_replays = analyzed_replays[1:]


def create_encodings_in_background(file_manager):
    time.sleep(60)
    canonical_replay_names = set([replay.name for replay in file_manager.get_canonical_replays()])
    encoded_replays = None
    try:
        encoded_replays = file_manager.load_encodings_from_file()
    except FileNotFoundError:
        encoded_replays = create_encodings_for_canonical_replays(file_manager)

    encoded_replay_names = set([replay.path.name for replay in encoded_replays])

    if encoded_replay_names != canonical_replay_names:
        create_encodings_for_canonical_replays(file_manager)

