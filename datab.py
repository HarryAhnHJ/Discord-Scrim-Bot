import match
from collections import deque
import discord


'''
A player queue for those who are in queue but have not found team with corresponding empty role
'''
waitlist_players = []


'''
Temporary database for all players in the server
'''
all_players=list([match.Player()])


'''
List of active matches - if a player if in any of these matches, they cannot queue
'''
# in_game_matches = list([match.Match()])

'''
List of active playerids
'''
in_game_players = list([str])


'''
List of playerids that have accepted incoming found match
'''
accepted_players = list([str])