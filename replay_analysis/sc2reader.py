import sys

# Imports from Blizzard
import mpyq
from s2protocol.versions import build, list_all, latest
from s2protocol.decoders import *

# This Class reads a given replay file and extracts Event data and Replay details
# which are returned as standard Python dictionaries or a list of dictionaries (events)
class Sc2ReplayReader:
    def __init__(self, replay_path):
        self.__archive = mpyq.MPQArchive(replay_path)

        # Read the protocol header, this can be read with any protocol
        contents = self.__archive.header['user_data_header']['content']
        self.__header = latest().decode_replay_header(contents)

        # The header's baseBuild determines which protocol to use
        self.__base_build = self.__header['m_version']['m_baseBuild']
        try:
            self.__protocol = build(self.__base_build)
        except:
            print('Unsupported base build: ' + str(self.__base_build))
            sys.exit(1)

    def get_replay_protocol_version(self):
        return self.__base_build

    def get_replay_header(self):
        return self.__header

    def get_replay_init_data(self):
        try:
            return self.__replay_init_data
        except AttributeError:
            self.__replay_init_data = self.__protocol.decode_replay_initdata(self.__archive.read_file('replay.initData'))
            return self.__replay_init_data

    def get_replay_attributes_events(self):
        try:
            return self.__replay_attribute_events
        except AttributeError:
            self.__replay_attribute_events = self.__protocol.decode_replay_attributes_events(self.__archive.read_file('replay.attributes.events'))
            return self.__replay_attribute_events

    def get_replay_details(self):
        try:
            return self.__replay_details
        except AttributeError:
            self.__replay_details = self.__protocol.decode_replay_details(self.__archive.read_file('replay.details'))
            return self.__replay_details

    # Return a list of Message Events which contains Messages and Pings to other players
    def get_replay_message_events(self):
        try:
            return self.__replay_message_events
        except AttributeError:
            generator = self.__protocol.decode_replay_message_events(self.__archive.read_file('replay.message.events'))
            self.__replay_message_events = []
            self.__fill_event_list(self.__replay_message_events, generator)
            return self.__replay_message_events

    # Return a list of Game Events which contains Human actions and certain triggered events
    def get_replay_game_events(self):
        try:
            return self.__replay_game_events
        except AttributeError:
            generator = self.__protocol.decode_replay_game_events(self.__archive.read_file('replay.game.events'))
            self.__replay_game_events = []
            self.__fill_event_list(self.__replay_game_events, generator)
            return self.__replay_game_events

    # Return a list of Tracker Events which contains Game state information
    def get_replay_tracker_events(self):
        try:
            return self.__replay_tracker_events
        except AttributeError:
            generator = self.__protocol.decode_replay_tracker_events(self.__archive.read_file('replay.tracker.events'))
            self.__replay_tracker_events = []
            self.__fill_event_list(self.__replay_tracker_events, generator)
            return self.__replay_tracker_events

    # Note: list is mutable, so this is passed by reference which saves us the overhead of copying lists.
    def __fill_event_list(self, list_ref, event_generator):
        del list_ref[:] # clear all elements in the list and do the same to all other references of this list.
        for event in event_generator:
            list_ref.append(event)
