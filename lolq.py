from discord import app_commands
from discord.ext import commands
import discord
import os
from dotenv import load_dotenv
from pathlib import Path
import random
import json
import asyncio
import traceback
import logging
import datab
import match
import datetime
import time
import riotapi

'''
Bot
'''
intents = discord.Intents.all()
intents.messages = True
bot = commands.Bot(command_prefix="/",intents=intents)

@bot.event
async def on_ready():
    bot.qchannel = await bot.fetch_channel(datab.qchannel)
    bot.echannel = await bot.fetch_channel(datab.echannel)
    bot.my_guild = await bot.fetch_guild(datab.guild)
    bot.index = 1 #indicating match number, 1 means first match of the day
    bot.lobbies = []
    bot.timeout_float = 60.0
    '''
    Qstatus shows the active queue's status
    -1 = queue has not started
    0 = queue just started (no one queued yet) 
    1 = some people queued
    2 = match found
    3 = players accepting
    4 = some players decline/didn't respond, back to queue
    5 = everyone accepted, game starting? (not necessary)
    '''
    bot.qstatus = -1
    with open('players.json','r') as f:
        try:
            datab.all_players_dict = json.load(f)
        except:
            pass
    
    if len(datab.all_players_dict) != 0:
        for playerdict in datab.all_players_dict:
            player = match.Player()
            player.setplayerid(playerdict.get("id"))
            player.setplayerign(playerdict.get("ign"))
            player.setplayerrank(playerdict.get("rank"))
            player.setplayerelo(playerdict.get("elo"))
            datab.all_players.append(player)
    print(datab.all_players)
    print("bot ready.")
    

@bot.command(name="sync")
async def sync(ctx):
    print("sync command")
    if ctx.message.author.id == datab.my_id:
        bot.tree.clear_commands(guild=bot.my_guild)
        bot.tree.copy_global_to(guild=bot.my_guild)
        await bot.tree.sync(guild=None)
        
        await ctx.send('Command tree synced.',delete_after=5.0)
        # await bot.process_commands(ctx.message)
    else:
        await ctx.send('You must be the owner to use this command!')
    await ctx.message.delete()

@bot.tree.command(name="helpmepls")
async def help(inter:discord.Interaction):
    helpui = discord.Embed(title=f"__**Welcome to BCS Inhouses Testing!**__",color=0x03f8fc,
                               description="Use these commands. More commands coming, TBA")
    helpui.add_field(name="/signup [ign] [tagline]",value=f'Register to be able to queue for inhouses. Input your MAIN ACCOUNT IGN',inline=False)
    helpui.add_field(name="/start",value=f'Start the queue. Just need one player to use this command',inline=False)
    helpui.add_field(name="/queue [role]",value=f'Role is one of : Top, Jng, Mid, Bot, Sup',inline=False)
    helpui.add_field(name="/unqueue",value=f'Unqueue from queue.',inline=False)
    helpui.add_field(name="/accept",value=f'Accept a match found',inline=False)
    helpui.add_field(name="/decline",value=f'Decline a match found',inline=False)
    helpui.add_field(name="/win",value=f'Declare winning team after the match',inline=False)
    await inter.response.send_message(embed=helpui)

'''
Runs when !start command is made AND 
When previous lobby starts its game and new lobby needs to be formed
Creates a new match 
'''
@bot.tree.command(name="start")
async def start(inter: discord.Interaction):
    if bot.qstatus >= 0:
        await inter.response.send_message(content='Queue is already active',ephemeral=True,delete_after=3)
        return
    bot.lobbies.append(match.Match())
    bot.active_lobby = bot.lobbies[(bot.index-1)]
    bot.active_lobby.setmatchname(bot.index)
    bot.qstatus = 0
    await bot.qchannel.send('Queue is starting!!!')
    await inter.response.send_message("Done",ephemeral=True,delete_after=1)

    if len(datab.waitlist_players) == 0:
        await update_queue_ui(inter)
    else:
        num_players = bot.active_lobby.cntemptyspots() # number of players that can be queued
        await queue_from_waitlist(inter)
        await update_queue_ui(inter)

'''
Registers player to be able to queue. 
Either to be reset every day or permanently stored unless they leave the server, or banned
'''
@bot.tree.command(name="signup")
async def sign_up(inter: discord.Interaction,lolign: str,tagline:str):
    playerid = str(inter.user.id)
    playerign = str(lolign).lower().replace(" ","") 
    #elo is a fixed # at start

    ss = riotapi.SauderStats()
    print(playerign + tagline)
    try:
        rankinfo_list = ss.get_summoner_data(playerign,tagline)
    except:
        await inter.response.send_message(f'Error retrieving information from RiotAPI. Please contact an admin.',ephemeral=True)
        logging.exception("message")
        return
    
    if len(rankinfo_list) == 0:
        await inter.response.send_message(f'You are not ranked. Matchmaking may be unbalanced.')
        playerrank = "UNRANKED"
    else:
        playerign = rankinfo_list[0] 
        playerrank = rankinfo_list[1] + " " + rankinfo_list[2]

    newplayer = match.Player()
    newplayer.setplayerid(playerid)
    newplayer.setplayerrank(playerrank)
    newplayer.setplayerign(playerign)

    datab.all_players.append(newplayer)

    player_dict = {"id" : playerid,
                   "ign": playerign,
                   "rank": playerrank,
                   "elo" : newplayer.getplayerelo()} #elo is inhouse elo, NOT soloq
    
    datab.all_players_dict.append(player_dict)
    save_new_players()

    await inter.response.send_message(f'You have successfully signed up:\nIGN: {playerign}\nRank: {playerrank}',
                                      ephemeral=True,delete_after=30)


'''
sub-function: given player id, find player info. If player is not signed up, return False
'''
def findplayer(id:str,players: list[match.Player()]):
    for player in players:
        if player.getplayerid() == id:
            return player
        else:
            continue
    return False


'''
Update & Send the currently active lobby as an discord embed
Sends signal to check if lobby is full. If full, start match
'''
async def update_queue_ui(inter: discord.Interaction):
    al = bot.active_lobby
    al.ui = discord.Embed(title=f"__**Lobby {al.getname()}:**__",color=0x03f8fc,
                               description="Type '!queue [role]' to queue into the game!")
    al.ui.add_field(name="**Top**",value=f'{al.blue.top.getplayerign()}\n {al.red.top.getplayerign()}',inline=False)
    al.ui.add_field(name="**Jng**",value=f'{al.blue.jng.getplayerign()}\n {al.red.jng.getplayerign()}',inline=False)
    al.ui.add_field(name="**Mid**",value=f'{al.blue.mid.getplayerign()}\n {al.red.mid.getplayerign()}',inline=False)
    al.ui.add_field(name="**Bot**",value=f'{al.blue.bot.getplayerign()}\n {al.red.bot.getplayerign()}',inline=False)
    al.ui.add_field(name="**Sup**",value=f'{al.blue.sup.getplayerign()}\n {al.red.sup.getplayerign()}',inline=False)

    al.matchfound_ui = discord.Embed(title=f"__**Lobby {al.getname()}: MATCH FOUND**__",color=0x03f8fc,
                               description="Type '!accept' to accept the match!")
    numplayers_waiting = len(al.getfullrosters()) - len(datab.accepted_players)
    al.matchfound_ui.add_field(name=f'**Number of players we are waiting for:',
                               value = f'{str(numplayers_waiting)}',
                               inline=True)
    if bot.qstatus == -1:
        await bot.qchannel.send(f'ERROR: Contact an admin.')
    if bot.qstatus == 0: #initial queue start
        al.ui_msg = await bot.qchannel.send(embed=al.ui)
        bot.qstatus = 1
    elif bot.qstatus == 1: #someone queued
        await al.ui_msg.edit(embed=al.ui)
        if al.ismatchfull():
            await bot.qchannel.send(f"Full lobby! Game starting soon...")
            await full_match_found(inter)
    elif bot.qstatus == 2: #match found
        al.matchfound_ui_msg = await bot.qchannel.send(embed=al.matchfound_ui)
        await wait_for_response(inter)
    elif bot.qstatus == 3: #some players accepted queue
        await al.matchfound_ui_msg.edit(embed=al.matchfound_ui)
        if len(datab.accepted_players) + len(datab.declined_players) == 10:
            await bot.qchannel.send("All responses recorded.")
        if numplayers_waiting == 0:
            auto_matchmake(inter)
            bot.qstatus = 5 #game start
            await start_game(inter)
            save_new_players() #periodically save new players to the database (json)
    elif bot.qstatus == 4: #someone declined, going back to queue
        al.ui_msg = await bot.qchannel.send(embed=al.ui)
        await queue_from_waitlist(inter)
        if al.ismatchfull():
            await bot.qchannel.send(f"Full lobby! Game starting soon...")
            await full_match_found(inter)


'''
Save new players to json
'''
def save_new_players():
    with open("players.json", "w") as f:
        json.dump(datab.all_players_dict,f,indent=2)


'''
Called when a match is accepted by all 10 players
Swaps players between teams to balance out players based on rank/in-house elo
Stops when the teams are closest to balanced
This function should not do anything if some players are unranked AND have not played before
'''
def auto_matchmake(inter: discord.Interaction):
    # red_mmr = bot.active_lobby.getred().getteammmr()
    # blue_mmr = bot.active_lobby.getblue().getteammmr()

    # original_rank_diff = abs(blue_mmr - red_mmr)
    # if original_rank_diff < 10:
    #     return

    # redteam = bot.active_lobby.getred()
    # blueteam = bot.active_lobby.getblue()
    # for role in ["top","jng","mid","bot","sup"]:
    #     blueplayermmr = blueteam.getattr(role).getmmr()
    #     redplayermmr = redteam.getattr(role).getmmr()
    #     if 
    return
        

'''
Shows final player Embed UI
Randomly selects one player to create lobby and invite the 9 other players
Tournament Code if available(?)
'''
async def start_game(inter: discord.Interaction):
    al = bot.active_lobby
    al.startmatch_ui = discord.Embed(title=f"__**Lobby {al.getname()}:**__",color=0x03f8fc,
                                     description="Match Accepted! Enjoy the game!")
    al.startmatch_ui.add_field(name=f'**Blue Team**',
                               value=f'Top:  {al.blue.top.getplayerign()}\nJng:   {al.blue.jng.getplayerign()}\nMid:  {al.blue.mid.getplayerign()}\nBot:  {al.blue.bot.getplayerign()}\nSup:  {al.blue.sup.getplayerign()}',
                               inline=True)
    al.startmatch_ui.add_field(name=f'**Red Team**',
                               value=f'Top:  {al.red.top.getplayerign()}\nJng:   {al.red.jng.getplayerign()}\nMid:  {al.red.mid.getplayerign()}\nBot:  {al.red.bot.getplayerign()}\nSup:  {al.red.sup.getplayerign()}',
                               inline=True)
    al.startmatch_ui.add_field(name=f'Blue Team Multi',
                               value=f"[link](www.op.gg/{al.blue.top.getplayerign()})",
                               inline=False)
    al.startmatch_ui.add_field(name=f'Red Team Multi',
                               value=f"[link](www.op.gg)",
                               inline=True)

    al.startmatch_ui_msg = await bot.qchannel.send(embed=al.startmatch_ui)

    all_players = bot.active_lobby.getfullrosters()
    
    #adds players to indicate they are now in active game
    datab.in_game_players = datab.in_game_players + all_players

    random_player = random.choice(all_players)
    playerid_make_lobby = random_player.getplayerid()

    await bot.qchannel.send(f'<@{str(playerid_make_lobby)}> You are responsible this game for creating the lobby and inviting the other players.')
    bot.index += 1 # /start will now create and point to next queue
    bot.qstatus = -1
    await bot.qchannel.send(f"Type '/start' to start a new queue!")


'''
Starts the match. Pings all players in the match. 
If at least one player does not accept (react?) within x seconds, match returns to lobby (queue). 
The player(s) who did not accept will be removed and disallowed to queue again for y minutes. 
'''
async def full_match_found(inter: discord.Interaction):
    all_players_id = bot.active_lobby.getfullrostersids()
    ping_players = ""

    for playerid in all_players_id:
        ping_player = "<@" + str(playerid) + ">"
        ping_players = ping_players + " " + ping_player

    await bot.qchannel.send(f'''Match Found!\n{ping_players}\nType '/accept' to accept the queue, '/decline' to decline.
                   Note that declining too many times or not responding will time you out of queueing.''')
    bot.qstatus = 2
    await update_queue_ui(inter)


'''
Waits for either queue timer to run out OR for all players to respond with 'accept' or 'decline.
If accept, go to /accept command func
If decline, go to /decline command func
If no response, go to /decline command func (90s timer)
'''
async def wait_for_response(inter:discord.Interaction):
    # for player in bot.active_lobby.getfullrosters():
    #     def check(inter,command):
    #         return inter.user.id == player.getplayerid() and command.name == "accept"
    #     try:
    #         command = await bot.wait_for('command_completion',timeout=10.0,check=check) 
    #     except asyncio.TimeoutError:
    #         bot.active_lobby.remove_player_from_match(player.getplayerid())

    # await bot.qchannel.send(f'Some players have failed to respond in time. Replacing them with players from the waitlist...')
    # bot.qstatus = 0 #override qstatus = 1 from add_player_to_queue
    # await queue_from_waitlist(inter)
    # await update_queue_ui(inter)
    no_response = False
    def check(msg):
        return msg.content == "All responses recorded." and msg.channel == bot.qchannel and msg.author.id == datab.bot_id
    try:
        msg = await bot.wait_for('message',timeout=bot.timeout_float,check=check) 
    except asyncio.TimeoutError:
        for player in bot.active_lobby.getfullrosters():
            if player.getplayerid() not in datab.accepted_players:
                print('should not be here if no accepts')
                bot.active_lobby.remove_player_from_match(player.getplayerid())
        await bot.qchannel.send(f'Some players have failed to respond in time. Replacing them with players from the waitlist...')
        datab.accepted_players.clear()
        bot.qstatus = 4
        await update_queue_ui(inter)
    else:
        print('Success!')
        

'''
Accepts the match found (player in lobby only)
Update ui 
'''
@bot.tree.command(name="accept")
async def accept_match(inter: discord.Interaction):
    playerid = str(inter.user.id)
    if (bot.qstatus != 2) and (bot.qstatus != 3): #not in 'match found!' mode
        await inter.response.send_message(f'Match not found yet',ephemeral=True,delete_after=5)
        return

    if findplayer(playerid,bot.active_lobby.getfullrosters()) == False:
        await inter.response.send_message(f'You are not part of the current queued match!!',ephemeral=True,delete_after=5)
        return
    datab.accepted_players.append(playerid)
    await inter.response.send_message('You have accepted the match.', ephemeral=True,delete_after=3)
    bot.qstatus = 3
    print('Total number of players responded: ' + str(len(datab.accepted_players) + len(datab.declined_players)))
    await update_queue_ui(inter)


'''
Player who was pinged by bot that match was found, can decline with this command
'''
@bot.tree.command(name="decline")
async def decline_match(inter: discord.Interaction):
    playerid = str(inter.user.id)

    if (bot.qstatus != 2) and (bot.qstatus != 3): #not in 'match found!' mode
        await inter.response.send_message(f'Match not found yet',ephemeral=True,delete_after=5)
        return

    if findplayer(playerid,bot.active_lobby.getfullrosters()) == False: #not in queue
        await inter.response.send_message(f'You are not part of the current queued match!!',ephemeral=True,delete_after=5)
        return
    
    await inter.response.send_message(f'You have declined queue. Penalties may apply.',ephemeral=True)
    datab.declined_players.append(playerid)
    print('Total number of players responded: ' + str(len(datab.accepted_players) + len(datab.declined_players)))
    # apply_penalty(inter)

    # await bot.qchannel.send(f'Checking waitlist...')
    # if await queue_from_waitlist(inter) == False:
    #     await bot.qchannel.send(f'A player has declined the match. Going back to queue...')
    #     datab.accepted_players.clear()
    # bot.qstatus = 0 #override qstatus = 1 from add_player_to_queue
    # await update_queue_ui(inter)
    

'''
Called if there is at least one person in the waitlist. 
Queues players from waitlist into currently active queue
Queue should either be empty (start), or close to full (someone declined)
'''
async def queue_from_waitlist(inter:discord.Interaction):
    if len(datab.waitlist_players) == 0:
        return False
    
    n = len(datab.waitlist_players) #every time a player gets queued, subtract 1. Queue until it reaches 0
    temp_waitlist = []
    for playerlist in datab.waitlist_players: #each element is a list that contains [player,role]
        if n == 0:
            return
        print(datab.waitlist_players)
        player = playerlist[0] # is player object NOT player id
        role = playerlist[1]
        if await add_player_to_queue(inter,player.getplayerid(),role,1) == False:
            temp_waitlist.append(playerlist)
            n = n - 1
        else:
            continue
    datab.waitlist_players = temp_waitlist

'''
For players to put themselves in queue
Players are only able to queue into 1 role at a time (for now)
Game will start if there are 2 people in each of the 5 roles.
'''
@bot.tree.command(name="queue")
async def queue_role(inter: discord.Interaction, msgrole: str):
    team_blue = bot.active_lobby.getblue()
    team_red = bot.active_lobby.getred()
    teams = [team_blue,team_red]
    #match queue not started
    if bot.active_lobby.getname() == "":
        await inter.response.send_message('Error: Queue has not started yet.',ephemeral=True,delete_after=5)
        return
    #player has not signed up yet
    if findplayer(str(inter.user.id),datab.all_players) == False:
        await inter.response.send_message("You are not signed up. Please sign up using '!signup [rank]'\nE.g. !signup Emerald 2 or !signup Masters",
                                          ephemeral=True,
                                          delete_after=30)
        return
    
    #TEST ADMIN FUNCTION FOR QUEUEING ALL
    if msgrole.lower() == 'all':
        # print('im here')
        if str(inter.user.id) != str(datab.my_id):
            await inter.response.send_message(f'YOU DO NOT HAVE PERMISSION TO USE THIS FUNCTION. GTFO', ephemeral=True,delete_after=5)
            return
        else:
            admin = findplayer(str(inter.user.id),datab.all_players)
            for team in teams:
                team.setplayerasrole(admin,'top')
                team.setplayerasrole(admin,'jng')
                team.setplayerasrole(admin,'mid')
                team.setplayerasrole(admin,'bot')
                team.setplayerasrole(admin,'sup')
            await inter.response.send_message('Test queue all successful',ephemeral=True,delete_after=3)
            bot.qstatus = 1
            await update_queue_ui(inter)
        return
    #proper role input not found
    if is_proper_role(msgrole) == False:
        await inter.response.send_message('ERROR: Invalid role',ephemeral=True,delete_after=5)
        return
    #player is already in an active game. To officially end the game, use !win to declare winner
    if findplayer(str(inter.user.id),datab.in_game_players) != False:
        await inter.response.send_message("You are already in an active match! If your game ended, use !win to declare the winner.", 
                                          ephemeral=True,
                                          delete_after=10)
    '''
    if player already in queue, send error
    '''
    # for team in teams:
    #     for player in team.getteamplayers():
    #         if player.getplayerid() != "":
    #             if str(inter.message.author.id) == player.getplayerid():
    #                 await bot.qchannel.send(f'You are already in queue!')
    #                 return
    #             else:
    #                 continue
    '''
    if none of the above, try to find a spot
    '''
    await add_player_to_queue(inter,str(inter.user.id),msgrole,0)
    await update_queue_ui(inter)


'''
sub-function:
Adds player to queue or waitlist if queue is full
If stat = 0, it means they are queueing directly 
If stat = 1, it means they are queueing from waitlist
'''
async def add_player_to_queue(inter:discord.Interaction, userid:str,role:str,stat:int):
    team_blue = bot.active_lobby.getblue()
    team_red = bot.active_lobby.getred()
    teams = [team_blue,team_red]

    curr_player = None
    found_team = False
    for team in teams:
        if found_team == False:
            if not team.isfilled(role.lower()):
                curr_player = findplayer(userid,datab.all_players)
                team.setplayerasrole(curr_player,role)
                found_team = True
                if stat == 0:
                    await inter.response.send_message(f'Successfully added to queue', ephemeral=True)
    if found_team == False:
        curr_player = findplayer(userid,datab.all_players)
        datab.waitlist_players.append([curr_player,role])
        if stat == 0:
            await inter.response.send_message(f'Current queue has no availble spots for {role.lower()}. You have been added to the waitlist.',
                                              ephemeral=True)
        bot.qstatus = 1
        return False
    bot.qstatus = 1
    

'''
sub-function: Checks if the input string from Discord user is a proper role name
'''
def is_proper_role(msgrole:str):
    if ((msgrole.lower() != "top") and 
        (msgrole.lower() != "jng") and 
        (msgrole.lower() != "mid") and
        (msgrole.lower() != "bot") and
        (msgrole.lower() != "sup")):
        return False
    else:
        return True
    

'''
Unqueue user if they are in queue
'''
@bot.tree.command(name="unqueue")
async def unqueue(inter: discord.Interaction):
    dq_player_id = str(inter.user.id) 

    if (bot.qstatus != 1) and (bot.qstatus != 0):
        await inter.response.send_message(f'You cannot leave queue when match is already found. Use /decline instead.',ephemeral=True)
        return
        
    if findplayer(dq_player_id,bot.active_lobby.getfullrosters()) == False:
        print(f'Not currency in main lobby.. Could be waitlisted?')
    else:
        bot.active_lobby.remove_player_from_match(dq_player_id)
        await inter.response.send_message(f'You have been removed from queue.',ephemeral=True,delete_after=5)
        await update_queue_ui(inter)
        return
    
    if findplayer(dq_player_id, datab.waitlist_players) == False:
        await inter.response.send_message(f'You are not in queue.',ephemeral=True,delete_after=5)
        return
    else:
        datab.waitlist_players.remove_player_from_match(dq_player_id)
        await inter.response.send_message(f'You have been removed from the waitlist.',ephemeral=True,delete_after=5)
        await update_queue_ui(inter)
    

'''
View status of user/player 
In queue, in game, in waitlist, etc.
'''
@bot.tree.command(name="status")
async def view_status(inter: discord.Interaction):
    if findplayer(str(inter.user.id),datab.in_game_players):
        await inter.response.send_message(f'You are currently in an in-house game.',
                                          ephemeral=True)
    elif findplayer(str(inter.user.id),datab.accepted_players):
        await inter.response.send_message(f'You have accepted an incoming match and you are waiting for the game to start. Please wait for the other players to accept!',
                                          ephemeral=True)
    elif findplayer(str(inter.user.id),datab.waitlist_players):
        await inter.response.send_message(f"You are in the waitlist. You can wait for the next queue or type '/unqueue' to leave.",
                                          ephemeral=True)
    elif findplayer(str(inter.user.id),datab.all_players):
        await inter.response.send_message(f"You are not in queue. Type '/queue [role]' to play!",
                                          ephemeral=True)
    else:
        await inter.response.send_message(f"You have not signed up for in-houses. Type '/signup [ign] [rank]' so you can join queue!",
                                          ephemeral=True)


'''
Set winning team
'''
@bot.tree.command(name="win")
async def winning_team(inter: discord.Interaction, match_number: str, won_team: str):
    if (won_team.lower() != 'red') and (won_team.lower() != 'blue'):
        inter.response.send_message("Incorrect Input. Team should either be 'red' or 'blue'.",ephemeral=True,delete_after=5)
        return
    else:
        subject_match = bot.lobbies[int(match_number)-1]
        if inter.user.id in subject_match.getfullrostersids():
            subject_match.setwinningteam(won_team)
            for player in subject_match.getfullrosters():
                datab.in_game_players.remove(player)
            bot.qchannel.send(f'Match {match_number} is now complete, with {won_team.lower()} team winning the game. All players in the match can now queue.')
        else:
            await inter.response.send_message("You were not in match {match_number}.",epemeral=True)


@bot.event
async def on_error(event, *args, **kwargs):
    embed = discord.Embed(title=':x: Event Error', colour=0xe74c3c) #Red
    embed.add_field(name='Event', value=event)
    embed.description = '```py\n%s\n```' % traceback.format_exc()
    embed.timestamp = datetime.datetime.utcnow()
    await bot.echannel.send(embed=embed)


load_dotenv(Path("E:\Coding\DSB\.env"))
token = os.getenv("bcsbot_token")
bot.run(token)
