import discord
import match
from discord.ext import commands
import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
from collections import deque
import datab
import random

'''
Bot
'''
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

bot.active_lobby = match.Match()

load_dotenv(Path("E:\Coding\DSB\.env"))
token = os.getenv("bcsbot_token")
bot.run(token)


'''
To run when bot starts AND 
When !start command is made AND 
When previous lobby starts its game and new lobby needs to be formed
Creates a new match 
'''
@bot.command(name="start")
async def start(ctx):
    #placeholder... number or alphabet?
    index = 1
    bot.active_lobby.setmatchname(index)

    await update_queue_ui(ctx,0)


'''
Registers player to be able to queue. 
Either to be reset every day or permanently stored unless they leave the server, or banned
'''
@bot.command(name="signup")
async def sign_up(ctx,msgrank):

    await ctx.send('Adding you as a player...')

    playerid = str(ctx.message.author.id)
    playername = str(ctx.message.author.name) #author name is discord username, NOT server nickname
    playerrank = str(msgrank).lower().replace(" ","")

    newplayer = match.Player()
    newplayer.setplayerid(playerid)
    newplayer.setplayername(playername)
    newplayer.setplayerrank(playerrank)

    datab.all_players.append(newplayer)

    await ctx.send('Successfully signed up. Welcome!')


'''
Update & Send the currently active lobby as an discord embed
Sends signal to check if lobby is full. If full, start match
'''
async def update_queue_ui(ctx,stat:int):

    al = bot.active_lobby

    al.ui = discord.Embed(title=f"__**Lobby {al.getname()}:**__",color=0x03f8fc,
                               description="Type '!queue [role]' to queue into the game!")
    al.ui.add_field(name=f'**Blue Team**',
                         value=f'Top:  {al.blue.top.name}\nJng:   {al.blue.jng.name}\nMid:  {al.blue.mid.name}\nBot:  {al.blue.bot.name}\nSup:  {al.blue.sup.name}',
                         inline=True)
    al.ui.add_field(name=f'**Red Team**',
                         value=f'Top:  {al.red.top.name}\nJng:   {al.red.jng.name}\nMid:  {al.red.mid.name}\nBot:  {al.red.bot.name}\nSup:  {al.red.sup.name}',
                         inline=True)
    
    al.matchfound_ui = discord.Embed(title=f"__**Lobby {al.getname()}: MATCH FOUND**__",color=0x03f8fc,
                               description="Type '!accept' to accept the match!")
    numplayers_waiting = len(al.getfullrosters()) - len(datab.accepted_players)
    al.matchfound_ui.add_field(name=f'**Number of players we are waiting for:',
                               value = f'{str(numplayers_waiting)}',
                               inline=True)
    if stat == 0: #initial
        al.ui_msg = await ctx.send(embed=al.ui)
    elif stat == 1: #someone queued
        await al.ui_msg.edit(embed=al.ui)
    elif stat == 2: #match found
        al.matchfound_ui_msg = await ctx.send(embed=al.matchfound_ui)
        return
    elif stat == 3: #players accepted match
        await al.matchfound_ui_msg.edit(embed=al.matchfound_ui)
        if numplayers_waiting == 0:
            await start_game(ctx)
        return
    if al.ismatchfull():
        await ctx.send("Full lobby! Game starting soon...")
        await full_match_found(ctx)


'''
Starts the match. Pings all players in the match. 
If at least one player does not accept (react?) within x seconds, match returns to lobby (queue). 
The player(s) who did not accept will be removed and disallowed to queue again for y minutes. 
'''
async def full_match_found(ctx):
    
    all_players_id = bot.active_lobby.getfullrostersids()
    ping_players = ""

    for playerid in all_players_id:
        ping_player = "<@" + str(playerid) + ">"
        ping_players = ping_players + " " + ping_player

    await ctx.send(f'''Match Found!\n{ping_players}\nType !accept to accept the queue, !decline to decline.
                   Note that declining too many times or not responding will time you out of queueing.''')
    await update_queue_ui(ctx,2)


'''
Player who was pinged by bot that match was found, can accept with this command
Update match found embed
'''
@bot.command(name="accept")
async def accept_match(ctx):
    datab.accepted_players.append(str(ctx.message.author.id))
    await update_queue_ui(ctx,3)


'''
Player who was pinged by bot that match was found, can decline with this command
'''
@bot.command(name="decline")
async def decline_match(ctx):
    await ctx.send(f'A player has decilned the match. Going back to queue...')
    # apply_penalty(ctx)
    await unqueue(ctx)


'''
Shows final player Embed UI
Randomly selects one player to create lobby and invite the 9 other players
Tournament Code if available(?)
'''
async def start_game(ctx):

    al = bot.active_lobby
    al.startmatch_ui = discord.Embed(title=f"__**Lobby {al.getname()}:**__",color=0x03f8fc,
                               description="Match Accepted! Enjoy the game!")
    al.startmatch_ui.add_field(name=f'**Blue Team**',
                         value=f'Top:  {al.blue.top.name}\nJng:   {al.blue.jng.name}\nMid:  {al.blue.mid.name}\nBot:  {al.blue.bot.name}\nSup:  {al.blue.sup.name}',
                         inline=True)
    al.startmatch_ui.add_field(name=f'**Red Team**',
                         value=f'Top:  {al.red.top.name}\nJng:   {al.red.jng.name}\nMid:  {al.red.mid.name}\nBot:  {al.red.bot.name}\nSup:  {al.red.sup.name}',
                         inline=True)
    al.startmatch_ui_msg = await ctx.send(embed=al.startmatch_ui)

    all_players_id = bot.active_lobby.getfullrostersids()
    player_make_lobby = random.choice(all_players_id)

    await ctx.send(f'<@{str(player_make_lobby)}> You are responsible this game for creating the lobby and inviting the other players.')


'''
For players to put themselves in queue
Players are only able to queue into 1 role at a time (for now)
Game will start if there are 2 people in each of the 5 roles.
'''
@bot.command(name="queue")
async def queue_role(ctx, msgrole):
    if bot.active_lobby.getname() == "":
        await ctx.send(content='Error: Queue has not started yet.',ephemeral=True)
        return
    if is_proper_role(msgrole) == False:
        await ctx.send('Error: Invalid role')
        return
    team_blue = bot.active_lobby.getblue()
    team_red = bot.active_lobby.getred()
    teams = [team_blue,team_red]
    '''
    if player already in queue, send error
    '''
    # for team in teams:
    #     for player in team.getteamplayers():
    #         if player.getplayerid() != "":
    #             if str(ctx.message.author.id) == player.getplayerid():
    #                 await ctx.send(f'You are already in queue!')
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
            if team.isfilled(msgrole.lower()):
                continue
            else:
                ''' if player is in player database (list of just id for now), aka signed up using signup command
                , then add the player to queue'''
                curr_player = findplayer(str(ctx.message.author.id),datab.all_players)
                if curr_player == False:
                    await ctx.send("Player is not signed up. Please sign up using '!signup [rank]'\nE.g. !signup Emerald 2 or !signup Masters")
                    return
                else:
                    team.setplayerasrole(curr_player,msgrole)
                    found_team = True
                    await ctx.send(f'Successfully added to {team.getteamname()}')
        else:
            continue
    if found_team == False:
        datab.waitlist_players.append(curr_player)
        await ctx.send(f'Current queue has no availble spots for {msgrole.lower()}. You have been added to the waitlist.')
    await update_queue_ui(ctx,1)


'''
sub-function: given player id, find player info. If player is not signed up, return False
'''
def findplayer(id:str,players: list[match.Player]):
    for player in players:
        if player.getplayerid() == id:
            return player
        else:
            continue
    return False


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
For testing purposes - queues all 10 spots
'''
@bot.command(name="queueall")
async def queue_all(ctx):
    await queue_role(ctx,"top")
    await queue_role(ctx,"top")
    await queue_role(ctx,"jng")
    await queue_role(ctx,"jng")
    await queue_role(ctx,"mid")
    await queue_role(ctx,"mid")
    await queue_role(ctx,"bot")
    await queue_role(ctx,"bot")
    await queue_role(ctx,"sup")
    await queue_role(ctx,"sup")


'''
Unqueue user if they are in queue
'''
@bot.command(name="unqueue")
async def unqueue(ctx):

    dq_player_id = str(ctx.message.author.id) 

    # await ctx.send('Removing you from the queue...')
    if findplayer(dq_player_id,bot.active_lobby.getfullrosters()) == False:
        await ctx.send(f'Not currency in main lobby.. Could be waitlisted?')
    else:
        print(bot.active_lobby.getfullrostersnames())
        print(bot.active_lobby.getfullrostersids())
        bot.active_lobby.remove_player_from_match(dq_player_id)
        await ctx.send(f'You have been removed from queue')
        await update_queue_ui(ctx,1)
        print(bot.active_lobby.getfullrostersnames())
        print(bot.active_lobby.getfullrostersids())
        return
    if findplayer(dq_player_id, datab.waitlist_players) == False:
        await ctx.send(f'You are not in queue.')
    else:
        datab.waitlist_players.remove_player_from_match(dq_player_id)
        await ctx.send(f'You have been removed from the waitlist')
        await update_queue_ui(ctx,1)
        return


'''
Set winning team
'''
@bot.command(name="win")
async def winning_team(ctx, won_team):
    bot.active_lobby.setwinningteam(won_team)
    #should be able to send error if input is not blue or red, and in future give points to winning team players






