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
    bot.gchannel = await bot.fetch_channel(datab.gchannel)
    bot.my_guild = await bot.fetch_guild(datab.guild)
    bot.bcs_logo = "https://cdn.discordapp.com/attachments/1134645264179810355/1135607814648254586/BCS_Transparent_low_det.png?ex=65b7d031&is=65a55b31&hm=3cd2ecb5ff40fa498db46c3eaaa7586dfeb16054bce6d275f41c025792962ad1&"
    bot.index = 1 #indicating match number, 1 means first match of the day
    bot.lobbies = []
    bot.timeout_float = 60.0

    bot.elopergame = 30
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
    start = time.time()
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
    # print(datab.all_players)
    end = time.time()
    print(f'Loading player data from json took {end-start} seconds')
    print("bot ready.")
    

@bot.command(name="sync")
async def sync(ctx):
    print("sync command")
    if str(ctx.message.author.id) == str(datab.my_id):
        bot.tree.clear_commands(guild=bot.my_guild)
        bot.tree.copy_global_to(guild=bot.my_guild)
        await bot.tree.sync(guild=None)
        
        await ctx.send('Command tree synced.',delete_after=5.0)
        # await bot.process_commands(ctx.message)
    else:
        await ctx.send('You must be the owner to use this command!')
        

@bot.tree.command(name="helpmepls")
async def help(inter:discord.Interaction):
    helpui = discord.Embed(title=f"__**Welcome to BCS Inhouses Testing!**__",
                           color=0x03f8fc,
                           description="Press [tab] after each command word.\nExample: /signup (tab) [input ign] (tab) [tag, WITHOUT #]")
    helpui.add_field(name="/signup [ign] [tagline]",value=f"Register to be able to queue for inhouses. Input your MAIN ACCOUNT IGN\nTag line should be without '#'",
                     inline=False)
    helpui.add_field(name="/start",value=f'Start the queue. Just need one player to use this command',inline=False)
    helpui.add_field(name="/queue [role]",value=f'Role is one of : top, jg, mid, bot, sup',inline=False)
    helpui.add_field(name="/unqueue",value=f'Unqueue from queue.',inline=False)
    helpui.add_field(name="/accept",value=f'Accept a match found',inline=False)
    helpui.add_field(name="/decline",value=f'Decline a match found',inline=False)
    helpui.add_field(name="/win",value=f'Declare winning team after the match. One player from the winning team should use this.',inline=False)
    helpui.add_field(name="/status",value=f"Gives your status in the in-house queue")
    helpui.add_field(name="/leaderboard",value=f"Leaderboard",inline=False)
    await inter.response.send_message(embed=helpui)


'''
Runs when !start command is made AND 
When previous lobby starts its game and new lobby needs to be formed
Creates a new match 
'''
@bot.tree.command(name="start")
async def start(inter: discord.Interaction):
    print(f"current channel is {inter.channel}")
    if bot.qstatus >= 0:
        await inter.response.send_message(content='Queue is already active',ephemeral=True,delete_after=3)
        return
    bot.qstatus = 0
    bot.lobbies.append(match.Match())

    print(f'number of matches today: {len(bot.lobbies)}')
    print(f'current index: {bot.index}')
    bot.active_lobby = bot.lobbies[bot.index-1]
    bot.active_lobby.setmatchname(bot.index)

    await bot.qchannel.send('Queue is starting!!!')
    await inter.response.send_message("Done",ephemeral=True,delete_after=1)
    
    await update_queue_ui(inter)
    # if len(datab.waitlist_players) == 0:
    #     await update_queue_ui(inter)
    # else:
    #     num_players = bot.active_lobby.cntemptyspots() # number of players that can be queued
    #     await queue_from_waitlist(inter)
        
        
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
    
    responded=False

    if rankinfo_list == False:
        await inter.response.send_message(f'IGN not found, please contact an admin if this is an error',ephemeral=True)
        return
    
    '''
    Riot API uses the original Riot IGN even if players name changed. So this is to use the most current IGN. 
    '''
    playerign = playerign + "#" + tagline

    if len(rankinfo_list) == 0:
        
        playerrank = "UNRANKED"
        await inter.response.send_message(f'You have successfully signed up:\nIGN: {playerign}\nRank: {playerrank}\nYou are not ranked. Matchmaking may be unbalanced.',
                                          ephemeral=True)
        responded=True
    else:
        # playerign = rankinfo_list[0]
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
    save_player_data()

    if responded == False:
        await inter.response.send_message(f'You have successfully signed up:\nIGN: {playerign}\nRank: {playerrank}',
                                          ephemeral=True,delete_after=30)
    


'''
sub-function: given player id, find player info. If player is not signed up, return False
'''
def findplayer(id:str,players):
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
                               description="Type '/queue [role]' to queue into the game!")
    al.ui.add_field(name="**Top**",value=f'{al.blue.top.getplayerign()}\n {al.red.top.getplayerign()}',inline=False)
    al.ui.add_field(name="**Jungle**",value=f'{al.blue.jg.getplayerign()}\n {al.red.jg.getplayerign()}',inline=False)
    al.ui.add_field(name="**Mid**",value=f'{al.blue.mid.getplayerign()}\n {al.red.mid.getplayerign()}',inline=True)
    al.ui.add_field(name="        ",value="      ",inline=True)
    al.ui.add_field(name="<a:pepenoting:995163777265827950> **Waitlist_Queue**",
                value=show_waitlist(),
                inline=True)
    al.ui.add_field(name="**Bottom**",value=f'{al.blue.bot.getplayerign()}\n {al.red.bot.getplayerign()}',inline=False)
    al.ui.add_field(name="**Support**",value=f'{al.blue.sup.getplayerign()}\n {al.red.sup.getplayerign()}',inline=False)
    al.ui.set_thumbnail(url=bot.bcs_logo)
    # al.ui.set_image(url="https://cdn.discordapp.com/attachments/1163467557337055272/1164747095354396733/SoulBlue.png?ex=65bc4ec3&is=65a9d9c3&hm=7644b904cca36f695e8c362e5dec6576355a1a07d212d10f2f2cbbf7dec82d4c&")


    al.matchfound_ui = discord.Embed(title=f"__**Lobby {al.getname()}: MATCH FOUND**__",color=0x03f8fc,
                               description="Type '/accept' to accept the match!")
    numplayers_waiting = len(al.getfullrosters()) - len(datab.accepted_players)
    al.matchfound_ui.add_field(name=f'**Number of players we are waiting for:',
                               value = f'{str(numplayers_waiting)}',
                               inline=True)
    if bot.qstatus == -1:
        await bot.qchannel.send(f'ERROR: Contact an admin.')

    if bot.qstatus == 0: #initial queue start
        al.ui_msg = await bot.qchannel.send(embed=al.ui)
        print("should be here at the start of EVERY LOBBY")
        bot.qstatus = 1
        if len(datab.waitlist_players) != 0:
            await queue_from_waitlist(inter)

    elif bot.qstatus == 1: #someone queued
        await al.ui_msg.edit(embed=al.ui)
        if al.ismatchfull():
            await bot.qchannel.send(f"Full lobby! Game starting soon...")
            await full_match_found(inter)

    elif bot.qstatus == 2: #match found
        al.matchfound_ui_msg = await bot.qchannel.send(embed=al.matchfound_ui)
        await al.ui_msg.edit(embed=al.ui)
        bot.qstatus = 3
        await wait_for_response(inter)

    elif bot.qstatus == 3: #waiting for players to accept or decline
        await al.ui_msg.edit(embed=al.ui)
        await al.matchfound_ui_msg.edit(embed=al.matchfound_ui)
        if len(datab.accepted_players) + len(datab.declined_players) == 10:
            await bot.qchannel.send("All responses recorded.")
        if numplayers_waiting == 0:
            await auto_matchmake(inter)
            bot.qstatus = 5 #game start
            print("starting game...")
            await start_game(inter)
            save_player_data() #periodically save new players to the database (json)

    elif bot.qstatus == 4: #someone declined, going back to queue
        al.ui_msg = await bot.qchannel.send(embed=al.ui)
        print("Should be here after someone declines. Check if there are duplicate embed errors.")
        bot.qstatus = 1
        if len(datab.waitlist_players) != 0:
            await queue_from_waitlist(inter)


'''
Show waitlist in queue ui
'''
def show_waitlist():
    if len(datab.waitlist_players) == 0: #each element is [player,role]
        return ""
    else:
        output_str = ""
        n = 3
        for playerlist in datab.waitlist_players:
            if n == 0:
                break
            else:
                player_str = f"{playerlist[0].getplayerign()} ({playerlist[1].upper()})"
                output_str += player_str + "\n"
                n = n - 1
        if n > 0:
            return output_str
        else:
            return output_str + f"\nand {len(datab.waitlist_players)-3} more..."


'''
2. Dump all_players_dict data to players.json (save_player_dict)
'''
def save_player_data():
    save_player_dict()
    start = time.time()
    with open("players.json", "w") as f:
        json.dump(datab.all_players_dict,f,indent=2)
    end = time.time()
    print(f'Dumping player data to json took {end-start} seconds')
'''
1. Store player attributes in all_players_dict
'''
def save_player_dict():
    start = time.time()
    print(datab.all_players)
    for player in datab.all_players:
        for player_dict in datab.all_players_dict:
            if player.getplayerid() == player_dict["id"]:
                player_dict["elo"] = player.getplayerelo()
    end = time.time()
    print(f'Saving player data to dictionary took {end-start} seconds')


'''
Called when a match is accepted by all 10 players
Swaps players between teams to balance out players based on rank/in-house elo
Stops when the teams are closest to balanced
This function should not do anything if some players are unranked AND have not played before
'''
async def auto_matchmake(inter: discord.Interaction):
    for role in ["top","jg","mid","bot","sup"]:
        redteam = bot.active_lobby.getred()
        blueteam = bot.active_lobby.getblue()
        red_mmr = redteam.getteammmr()
        blue_mmr = blueteam.getteammmr()

        team_rank_diff = abs(blue_mmr - red_mmr)
        if team_rank_diff < 10:
            continue
        blueplayermmr = getattr(blueteam,role).getmmr()
        redplayermmr = getattr(redteam,role).getmmr()
        if blue_mmr > red_mmr:
            if blueplayermmr >= redplayermmr:
                bot.active_lobby.swapplayers(role)
            else:
                continue
        else:
            if blueplayermmr <= redplayermmr:
                bot.active_lobby.swapplayers(role)
            else:
                continue
        print(f"Blue Team MMR is {blueteam.getteammmr()}")
        print(f"Red Team MMR is {redteam.getteammmr()}")
    await bot.qchannel.send(f"Teams have been formed based on rank and in-house elo.")
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
                               value=f'Top:  {al.blue.top.getplayerign()}\nJg:   {al.blue.jg.getplayerign()}\nMid:  {al.blue.mid.getplayerign()}\nBot:  {al.blue.bot.getplayerign()}\nSup:  {al.blue.sup.getplayerign()}',
                               inline=True)
    al.startmatch_ui.add_field(name=f'**Red Team**',
                               value=f'Top:  {al.red.top.getplayerign()}\nJg:   {al.red.jg.getplayerign()}\nMid:  {al.red.mid.getplayerign()}\nBot:  {al.red.bot.getplayerign()}\nSup:  {al.red.sup.getplayerign()}',
                               inline=True)
    al.startmatch_ui.add_field(name=f'Blue Team Multi',
                               value=f'[Link]({al.blue.getteammulti()})',
                               inline=False)
    al.startmatch_ui.add_field(name=f'Red Team Multi',
                               value=f'[Link]({al.red.getteammulti()})',
                               inline=True)
    al.startmatch_ui.add_field(name=f'Create Draft Link Here',
                               value=f'[Link]({create_draft()})',
                               inline=False)
    al.startmatch_ui.set_thumbnail(url=bot.bcs_logo)

    al.startmatch_ui_msg = await bot.qchannel.send(embed=al.startmatch_ui)

    all_players = bot.active_lobby.getfullrosters()
    
    #adds players to indicate they are now in active game
    datab.in_game_players = datab.in_game_players + all_players

    random_player = random.choice(all_players)
    playerid_make_lobby = random_player.getplayerid()

    all_players_9 = all_players.copy()
    all_players.remove(random_player)
    print(all_players)
    print(all_players_9)

    random_player2 = random.choice(all_players_9)
    playerid_make_draft = random_player2.getplayerid()

    await bot.qchannel.send(f'''<@{str(playerid_make_lobby)}> You are responsible this game for creating the lobby and inviting the other players.\nPassword: 123\nGame Type: Blind Pick\nAllow Spectators: All\n''')
    await bot.qchannel.send(f'''<@{str(playerid_make_draft)}> You are responsible for making draft with the link above. Send the generated links once everyone is in lobby.''')
    bot.index += 1 # /start will now create and point to next queue
    bot.qstatus = -1
    datab.accepted_players = []
    await bot.qchannel.send(f"Type '/start' to start a new queue!")

def create_draft():
    url = "https://draftlol.dawe.gg"
    return url


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
    no_response = False
    def check(msg):
        return msg.content == "All responses recorded." and msg.channel == bot.qchannel and str(msg.author.id) == str(datab.bot_id)
    try:
        msg = await bot.wait_for('message',timeout=bot.timeout_float,check=check) 
    except asyncio.TimeoutError:
        for player in bot.active_lobby.getfullrosters():
            if player.getplayerid() not in datab.accepted_players:
                print(player.getplayerign() + ' has not accepted. Removing player...')
                # await apply_penalty(inter,player)
                print(player.getplayerid())
                bot.active_lobby.remove_player_from_match(player.getplayerid())
        print('after removing, players in current lobby are ' + str(bot.active_lobby.getfullrostersnames()))
        await bot.qchannel.send(f'Some players have failed to respond in time. Replacing them with players from the waitlist...')
        datab.accepted_players.clear()
        bot.qstatus = 4
        await update_queue_ui(inter)
    else:
        print('Success!')
    

'''
Applies penalty counter to players with bad behaviour
i.e. Declining match too many times, toxicity, other players reporting the player
'''
async def apply_penalty(inter:discord.Interaction,player: match.Player):
    return


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
    
    if (playerid in datab.accepted_players) and (playerid not in datab.admins):
            await inter.response.send_message(f'You have already accepted the match!',ephemeral=True,delete_after=5)
            return
    else:
        datab.accepted_players.append(playerid)
        await inter.response.send_message('You have accepted the match.', ephemeral=True,delete_after=3)
    # bot.qstatus = 3
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
        await inter.response.send_message(f'You are not part of the currently queued match!!',ephemeral=True,delete_after=5)
        return
    
    await inter.response.send_message(f'You have declined queue. Penalties may apply.',ephemeral=True)
    datab.declined_players.append(playerid)
    print('Total number of players responded: ' + str(len(datab.accepted_players) + len(datab.declined_players)))
    

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
    temp_waitlist = []
    print(datab.waitlist_players)
    for playerlist in datab.waitlist_players: #each element is a list that contains [player,role]
        player = playerlist[0] # is player object NOT player id
        role = playerlist[1]
        if await add_player_to_queue(inter,player.getplayerid(),role,1) == False:
            temp_waitlist.append(playerlist)
        else:
            continue
    datab.waitlist_players = temp_waitlist
    print(f'waitlist after players added to queue: {datab.waitlist_players}')
    print('current lobby: ' + str(bot.active_lobby.getfullrostersnames()))
    await update_queue_ui(inter)

'''
For players to put themselves in queue
Players are only able to queue into 1 role at a time (for now)
Game will start if there are 2 people in each of the 5 roles.
'''
@bot.tree.command(name="queue")
async def queue_role(inter: discord.Interaction, msgrole: str):
    try:
        team_blue = bot.active_lobby.getblue()
        team_red = bot.active_lobby.getred()
        teams = [team_blue,team_red]
    except:
        await inter.response.send_message('Error: Queue has not started yet.',ephemeral=True,delete_after=5)
        return
    #match queue not started

    if bot.active_lobby.getname() == "" or bot.qstatus == -1:
        await inter.response.send_message('Error: Queue has not started yet.',ephemeral=True,delete_after=5)
        return

    #player has not signed up yet
    if findplayer(str(inter.user.id),datab.all_players) == False:
        await inter.response.send_message("You are not signed up. Please sign up using '/signup [rank]'\nE.g. !signup Emerald 2 or !signup Masters",
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
                team.setplayerasrole(admin,'jg')
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
    
    '''
    Player is already in an active game. 
    To officially end the game, use !win to declare winner
    '''
    # if findplayer(str(inter.user.id),datab.in_game_players) != False:
    #     await inter.response.send_message("You are already in an active match! If your game ended, use !win to declare the winner.", 
    #                                       ephemeral=True,
    #                                       delete_after=10)
    #     return
    '''
    if player already in queue, send error
    '''
    # for team in teams:
    #     for player in team.getteamplayers():
    #         if player.getplayerid() != "":
    #             if str(inter.user.id) == player.getplayerid():
    #                 await inter.response.send_message(f'You are already in queue!',ephemeral=True)
    #                 return
    #             else:
    #                 continue
    '''
    if none of the above, try to find a spot
    '''
    await add_player_to_queue(inter,str(inter.user.id),msgrole.lower(),0)
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
                    await inter.response.send_message(f'Successfully added to queue', ephemeral=True,delete_after=10)
                else:
                    print(curr_player.getplayerign() + ' has been added to ' + role)
                bot.qstatus = 1
    if found_team == False:
        curr_player = findplayer(userid,datab.all_players)
        if stat == 0:
            datab.waitlist_players.append([curr_player,role])
            await inter.response.send_message(f'Current queue has no availble spots for {role.lower()}. You have been added to the waitlist.',
                                              ephemeral=True,delete_after=10)
        else:
            print('failed to find empty spot. should return false.')
        if not bot.active_lobby.ismatchfull():
            bot.qstatus = 1
        return False
    bot.qstatus = 1
    

'''
sub-function: Checks if the input string from Discord user is a proper role name
'''
def is_proper_role(msgrole:str):
    if ((msgrole.lower() != "top") and 
        (msgrole.lower() != "jg") and 
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

    '''
    first, look in waitlist. Players in waitlist should be able to unqueue at any time
    '''
    waitlist_playerids = []
    #waitlist_player is a list of list[player,role]
    for playerlist in datab.waitlist_players:
        waitlist_playerids.append(playerlist[0])

    if findplayer(dq_player_id, waitlist_playerids) != False:
        datab.waitlist_players.remove_player_from_match(dq_player_id)
        await inter.response.send_message(f'You have been removed from the waitlist.',ephemeral=True,delete_after=5)
        await update_queue_ui(inter)
        return
        
    '''
    If not in waitlist, then look in lobby. Check if they are in lobby first, then check status of the queue.
    '''
    if findplayer(dq_player_id,bot.active_lobby.getfullrosters()) == False:
        await inter.response.send_message(f'Looks like you are not in queue.',ephemeral=True)
    else:
        if (bot.qstatus != 1) and (bot.qstatus != 0):
            await inter.response.send_message(f'You cannot leave queue when match is already found. Use /decline instead.',ephemeral=True)
            return
        bot.active_lobby.remove_player_from_match(dq_player_id)
        await inter.response.send_message(f'You have been removed from queue.',ephemeral=True,delete_after=5)
        await update_queue_ui(inter)
        return


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
        await inter.response.send_message("Incorrect Input. Team should either be 'red' or 'blue'.",ephemeral=True,delete_after=5)
        return
    else:
        await inter.response.send_message(f"Submitting Winner of Match {match_number}...",ephemeral=True,delete_after=5)
        subject_match = bot.lobbies[int(match_number)-1]

        if subject_match.getwteam() != "":
            await inter.response.send_message(f"Match results already submitted.",ephemeral=True,delete_after=10)
            return

        print(subject_match.getfullrostersnames())
        print(str(inter.user.id)==subject_match.getfullrostersids()[0])
        print(subject_match.getfullrostersids()[0]==inter.user.id)

        if str(inter.user.id) in subject_match.getfullrostersids():
            subject_match.setwinningteam(won_team)
            for player in subject_match.getfullrosters():
                print(player.getplayerelo())
                if player in getattr(subject_match,won_team).getteamplayers():
                    player.setplayerelo(player.getplayerelo()+bot.elopergame)
                    print(f"{player.getplayerign()}'s current elo is {player.getplayerelo()}")
                else:
                    player.setplayerelo(player.getplayerelo()-bot.elopergame)
                    print(f"{player.getplayerign()}'s current elo is {player.getplayerelo()}")
                datab.in_game_players.remove(player)
            await bot.qchannel.send(f'Match {match_number} is now complete, with {won_team.lower()} team winning the game.\nAll players in the match can now queue.')
        else:
            await inter.response.send_message(f"You were not in match {match_number}.",ephemeral=True)
    save_player_data()
 

'''
Leaderboard?
'''
@bot.tree.command(name="leaderboard")
async def leaderboard(inter:discord.Interaction):
    players_by_elo = sorted(datab.all_players,key=lambda x: x.getplayerelo(),reverse=True)
    embed = discord.Embed(title='BCS In-House Leaderboard', colour=0x03f8fc) #BCS blue
    embed.add_field(name='', value=f':first_place: {players_by_elo[0].getplayerign()}, {players_by_elo[0].getplayerelo()} pts',inline=False)
    embed.add_field(name='', value=f':second_place: {players_by_elo[1].getplayerign()}, {players_by_elo[1].getplayerelo()} pts',inline=False)
    embed.add_field(name='', value=f':third_place: {players_by_elo[2].getplayerign()}, {players_by_elo[2].getplayerelo()} pts',inline=False)
    embed.timestamp = datetime.datetime.now()
    await inter.response.send_message(f"Sending leaderboard to general...",ephemeral=True)
    await bot.gchannel.send(embed=embed)
    return


@bot.tree.error
async def on_error(inter: discord.Interaction,error):
    embed = discord.Embed(title=':x: Event Error', colour=0xe74c3c) #Red
    embed.add_field(name='Event', value=error)
    embed.description = '```py\n%s\n```' % traceback.format_exc()
    embed.timestamp = datetime.datetime.now()
    await bot.echannel.send(embed=embed)


@bot.event
async def on_message(message):
    if message.channel.id != bot.qchannel.id:
        print("not in queue channel")
        return
    else:
        await bot.process_commands(message)
        if str(message.author.id) not in datab.admins:
            await asyncio.sleep(5)
            await message.delete()  
    

load_dotenv(Path("E:\Coding\DSB\.env"))
token = os.getenv("bcsbot_token")
bot.run(token)
