from discord import app_commands
from discord.ext import commands
import discord
import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
from collections import deque
import random
import json
import asyncio
import traceback
import logging
import datab
import match
import riotapi

'''
Bot
'''
intents = discord.Intents.all()
intents.messages = True
bot = commands.Bot(command_prefix="/",intents=intents)

@bot.event
async def on_ready():
    bot.qchannel = bot.get_channel(datab.qchannel)
    bot.echannel = bot.get_channel(datab.echannel)
    bot.my_guild = await bot.fetch_guild(datab.guild)
    bot.index = 1 #indicating match number, 1 means first match of the day
    bot.lobbies = []
    print("bot ready.")
    

@bot.command(name="sync")
async def sync(ctx):
    print("sync command")
    if ctx.message.author.id == datab.my_id:
        bot.tree.clear_commands(guild=bot.my_guild)
        bot.tree.copy_global_to(guild=bot.my_guild)
        await bot.tree.sync(guild=bot.my_guild)
        await ctx.send('Command tree synced.') 
        # await bot.process_commands(ctx.message)
    else:
        await ctx.send('You must be the owner to use this command!')


'''
Runs when !start command is made AND 
When previous lobby starts its game and new lobby needs to be formed
Creates a new match 
'''
@bot.tree.command(name="start")
async def start(inter: discord.Interaction):
    bot.lobbies.append(match.Match())
    bot.active_lobby = bot.lobbies[(bot.index-1)]
    bot.active_lobby.setmatchname(bot.index)
    
    await inter.response.send_message(content='Queue started!',ephemeral=True)

    if len(datab.waitlist_players) == 0:
        await update_queue_ui(inter,0)
    else:
        await queue_from_waitlist(inter)
        await update_queue_ui(inter,0)

'''
Registers player to be able to queue. 
Either to be reset every day or permanently stored unless they leave the server, or banned
'''
@bot.tree.command(name="signup")
async def sign_up(inter: discord.Interaction,lolign: str, msgrank: str):
    # await channel.send('Adding you as a player...',ephemeral=True)
    playerid = str(inter.user.id)
    playerign = str(lolign).lower().replace(" ","") #author name is discord username, NOT server nickname
    playerrank = str(msgrank).lower().replace(" ","")

    newplayer = match.Player()
    newplayer.setplayerid(playerid)
    newplayer.setplayerign(playerign)
    newplayer.setplayerrank(playerrank)

    datab.all_players.append(newplayer)
    await inter.response.send_message(f'You have successfully signed up. Welcome!',ephemeral=True)
    # await bot.qchannel.send(f'A player has signed up.')


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
async def update_queue_ui(inter: discord.Interaction,stat:int):
    al = bot.active_lobby
    al.ui = discord.Embed(title=f"__**Lobby {al.getname()}:**__",color=0x03f8fc,
                               description="Type '!queue [role]' to queue into the game!")
    # al.ui.add_field(name=f'**Blue Team**',
    #                      value=f'Top:  {al.blue.top.name}\nJng:   {al.blue.jng.name}\nMid:  {al.blue.mid.name}\nBot:  {al.blue.bot.name}\nSup:  {al.blue.sup.name}',
    #                      inline=True)
    # al.ui.add_field(name=f'**Red Team**',
    #                      value=f'Top:  {al.red.top.name}\nJng:   {al.red.jng.name}\nMid:  {al.red.mid.name}\nBot:  {al.red.bot.name}\nSup:  {al.red.sup.name}',
    #                      inline=True)
    al.ui.add_field(name="Top",value=f'{al.blue.top.getplayerign()}\n {al.red.top.getplayerign()}',inline=True)
    al.ui.add_field(name="Jng",value=f'{al.blue.jng.getplayerign()}\n {al.red.jng.getplayerign()}',inline=True)
    al.ui.add_field(name="Mid",value=f'{al.blue.mid.getplayerign()}\n {al.red.mid.getplayerign()}',inline=True)
    al.ui.add_field(name="Bot",value=f'{al.blue.bot.getplayerign()}\n {al.red.bot.getplayerign()}',inline=True)
    al.ui.add_field(name="Sup",value=f'{al.blue.sup.getplayerign()}\n {al.red.sup.getplayerign()}',inline=True)

    al.matchfound_ui = discord.Embed(title=f"__**Lobby {al.getname()}: MATCH FOUND**__",color=0x03f8fc,
                               description="Type '!accept' to accept the match!")
    numplayers_waiting = len(al.getfullrosters()) - len(datab.accepted_players)
    al.matchfound_ui.add_field(name=f'**Number of players we are waiting for:',
                               value = f'{str(numplayers_waiting)}',
                               inline=True)
    if stat == 0: #initial
        al.ui_msg = await bot.qchannel.send(embed=al.ui)
    elif stat == 1: #someone queued
        await al.ui_msg.edit(embed=al.ui)
    elif stat == 2: #match found
        al.matchfound_ui_msg = await bot.qchannel.send(embed=al.matchfound_ui)
        return
    elif stat == 3: #players accepted match
        await al.matchfound_ui_msg.edit(embed=al.matchfound_ui)
        if numplayers_waiting == 0:
            await matchmake(inter)
            await start_game(inter)
        return
    if al.ismatchfull():
        await bot.qchannel.send(f"Full lobby! Game starting soon...")
        await full_match_found(inter)


'''
Called when a match is accepted by all 10 players
Swaps players between teams to balance out players based on rank/in-house elo
Stops when the teams are closest to balanced
'''
async def matchmake(inter: discord.Interaction):
    #swap around players
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
    al.startmatch_ui_msg = await bot.qchannel.send(embed=al.startmatch_ui)

    all_players = bot.active_lobby.getfullrosters()
    
    #adds players to indicate they are now in active game
    datab.in_game_players = datab.in_game_players + all_players

    random_player = random.choice(all_players)
    playerid_make_lobby = random_player.getplayerid()

    await bot.qchannel.send(f'<@{str(playerid_make_lobby)}> You are responsible this game for creating the lobby and inviting the other players.')
    bot.index += 1 # /start will now create and point to next queue

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

    await bot.qchannel.send(f'''Match Found!\n{ping_players}\nType !accept to accept the queue, !decline to decline.
                   Note that declining too many times or not responding will time you out of queueing.''')
    await update_queue_ui(inter,2)


'''
Player who was pinged by bot that match was found, can accept with this command
Update match found embed
'''
@bot.tree.command(name="accept")
async def accept_match(inter: discord.Interaction):
    playerid = str(inter.user.id)
    if findplayer(playerid,bot.active_lobby.getfullrosters()) != False:
        datab.accepted_players.append(playerid)
        await inter.response.send_message('You have accepted the match.', ephemeral=True)
        await update_queue_ui(inter,3)
    else:
        await inter.response.send_message(f'You are not even in queue!!',ephemeral=True)
        

'''
Player who was pinged by bot that match was found, can decline with this command
'''
@bot.tree.command(name="decline")
async def decline_match(inter: discord.Interaction):
    await inter.response.send_message(f'You have declined queue. Penalties may apply.',ephemeral=True)
    # apply_penalty(inter)
    dq_player_id = str(inter.user.id) 
    bot.active_lobby.remove_player_from_match(dq_player_id)
    await bot.qchannel.send(f'A player has decilned the match. Going back to queue...')
    await update_queue_ui(inter,1)


'''
Called if there is at least one person in the waitlist. 
Queues players from waitlist into currently active queue
Queue should either be empty (start), or close to full (someone declined)
'''
async def queue_from_waitlist(inter:discord.Interaction):
    for playerlist in datab.waitlist_players: #each element is a list that contains [player,role]
        
        



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
        await inter.response.send_message('Error: Queue has not started yet.',ephemeral=True)
        return
    #player has not signed up yet
    if findplayer(str(inter.user.id),datab.all_players) == False:
        await inter.response.send_message("You are not signed up. Please sign up using '!signup [rank]'\nE.g. !signup Emerald 2 or !signup Masters",ephemeral=True)
        return
    
    #TEST ADMIN FUNCTION FOR QUEUEING ALL
    if msgrole.lower() == 'all':
        print('im here')
        if str(inter.user.id) != str(datab.my_id):
            await inter.response.send_message(f'YOU DO NOT HAVE PERMISSION TO USE THIS FUNCTION. GTFO', ephemeral=True)
            return
        else:
            admin = findplayer(str(inter.user.id),datab.all_players)
            for team in teams:
                team.setplayerasrole(admin,'top')
                team.setplayerasrole(admin,'jng')
                team.setplayerasrole(admin,'mid')
                team.setplayerasrole(admin,'bot')
                team.setplayerasrole(admin,'sup')
            await inter.response.send_message('Test queue all successful',ephemeral=True)
            await update_queue_ui(inter,0)
        return
    #proper role input not found
    if is_proper_role(msgrole) == False:
        await inter.response.send_message('Error: Invalid role',ephemeral=True)
        return
    #player is already in an active game. To officially end the game, use !win to declare winner
    if findplayer(str(inter.user.id),datab.in_game_players) != False:
        await inter.response.send_message("You are already in an active match! If your game ended, use !win to declare the winner", ephemeral=True)
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
    if not already in queue, try to find a spot
    '''
    curr_player = None
    found_team = False
    for team in teams:
        if found_team == False:
            if not team.isfilled(msgrole.lower()):
                curr_player = findplayer(str(inter.user.id),datab.all_players)
                team.setplayerasrole(curr_player,msgrole)
                found_team = True
                await inter.response.send_message(f'Successfully added to {team.getteamname()}', ephemeral=True)
    if found_team == False:
        datab.waitlist_players.append([curr_player,msgrole])
        await inter.response.send_message(f'Current queue has no availble spots for {msgrole.lower()}. You have been added to the waitlist.',ephemeral=True)
        return
    await update_queue_ui(inter,1)


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


# '''
# For testing purposes - queues all 10 spots
# '''
# @bot.tree.command(name="queueall")
# async def queue_all(inter:discord.Interaction):
#     await queue_role(inter,'top')


'''
Unqueue user if they are in queue
'''
@bot.tree.command(name="unqueue")
async def unqueue(inter: discord.Interaction):
    dq_player_id = str(inter.user.id) 
    # await inter.response.send_message('Removing you from the queue...')
    if findplayer(dq_player_id,bot.active_lobby.getfullrosters()) == False:
        print(f'Not currency in main lobby.. Could be waitlisted?')
    else:
        bot.active_lobby.remove_player_from_match(dq_player_id)
        await inter.response.send_message(f'You have been removed from queue',ephemeral=True)
        await update_queue_ui(inter,1)
        return
    if findplayer(dq_player_id, datab.waitlist_players) == False:
        await inter.response.send_message(f'You are not in queue.',ephemeral=True)
    else:
        datab.waitlist_players.remove_player_from_match(dq_player_id)
        await inter.response.send_message(f'You have been removed from the waitlist',ephemeral=True)
        await update_queue_ui(inter,1)
        return


'''
Set winning team
'''
@bot.tree.command(name="win")
async def winning_team(inter: discord.Interaction, match_number: str, won_team: str):
    if won_team.lower() != 'red' | won_team.lower() != 'blue':
        inter.response.send_message("Incorrect Input. Team should either be 'red' or 'blue'",ephemeral=True)
        return
    else:
        bot.lobbies[int(match_number)-1].setwinningteam(won_team)


@bot.event
async def on_error(event, *args, **kwargs):
    message = args[0] #Gets the message object
    logging.warning(traceback.format_exc()) #logs the error
    await bot.echannel.send(f"You caused an error!") #send the message to the channel


load_dotenv(Path("E:\Coding\DSB\.env"))
token = os.getenv("bcsbot_token")
bot.run(token)


