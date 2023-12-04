import match
from collections import deque
import discord

# in_lobby = deque([match.Match()])


# in_game = deque([match.Match()])

'''
A player queue for those who are in queue but have not found team with corresponding empty role
'''
waitlist_players = deque([match.Player()])

# username_dict = {}

# userrank_dict = {}

'''
Temporary database for all players in the server
'''
all_players=list([match.Player()])

