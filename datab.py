import match
from collections import deque
import discord
# import mysql.connector

my_id = 211524290103738369
bot_id = 1114637994327035986
admins = [str(my_id),str(bot_id)]
'''
self_test
'''
# guild = 808907371715362856
# qchannel = 1114666837209264229
# echannel = 1114762534654845020
# gchannel = 1116776884345258184

'''
alpha-test
'''
# guild = 1123086946885972060
# qchannel = 1188613397403680838
# echannel = 1124467640107282552


'''
main server
'''
guild = 936783882752262165
qchannel = 1192955594383032340
echannel = 1197846605869621288
gchannel = 1192953434618478642

'''
A player queue for those who are in queue but have not found team with corresponding empty role
'''
waitlist_players = []


'''
Temporary database for all players in the server
'''
all_players=list([])

all_players_dict = []


'''
List of active matches - if a player if in any of these matches, they cannot queue
'''
# in_game_matches = list([match.Match()])

'''
List of active playerids
'''
in_game_players = list([])


'''
List of playerids that have accepted & declined incoming found match
'''
accepted_players = list([])
declined_players = list([])

# mydb = mysql.connector.connect(
#     host="localhost",
#     user="soulblue",
#     password="mypw"
# )

rank_dict = {
    "UNRANKED" : 50,
    "PLATINUM IV" : 10,
    "PLATINUM III" : 11,
    "PLATINUM II" : 12,
    "PLATINUM I" : 15,
    "EMERALD IV" : 25,
    "EMERALD III" : 35,
    "EMERALD II" : 48,
    "EMERALD I" : 65,
    "DIAMOND IV" : 80,
    "DIAMOND III" : 100,
    "DIAMOND II" : 120,
    "DIAMOND I" : 150,
    "MASTER I" : 180,
    "GRANDMASTER I" : 280,
}