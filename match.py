import discord
import asyncio
import os
import datab

'''
A single match in a scrim/in-house game. 
2 Teams, Blue and Red. At the end of the match, one winning team is announced
Also has a Discord Embed and Message representing the match. 
'''
class Match:

    def __init__(self):
        self.name = ""
        self.blue = Team("Blue")
        self.red = Team("Red")
        self.wteam = ""
        self.ui = discord.Embed()
        self.ui_msg  = discord.message
    
    def setwinningteam(self, team: str):
        if team.lower() == "blue":
            self.wteam = self.blue
        elif team.lower() == "red":
            self.wteam = self.red
        else:
            return False #error: input should be either blue or red
        
    def setmatchname(self,name:str):
        self.name = name

    def getname(self):
        return self.name

    def getblue(self):
        return self.blue
    
    def getred(self):
        return self.red

    def getfullrosters(self):
        return self.getblue().getteamplayers() + self.getred().getteamplayers()
    
    def getfullrostersnames(self):
        players = self.getfullrosters()
        player_names = []
        for player in players:
            player_names.append(player.getplayerign())
        return player_names
    
    def getfullrostersids(self):
        players = self.getfullrosters()
        player_ids = []
        for player in players:
            player_ids.append(player.getplayerid())
        return player_ids
    
    def getwteam(self):
        return self.wteam

    def remove_player_from_match(self, playerid):
        if self.blue.removeplayer(playerid) != False:
            print('removed from blue')
            return
        else:
            self.red.removeplayer(playerid)
            print('removed from red')

    def cntemptyspots(self): # counts the number of empty spots in queue
        return self.blue.getnum_teamemptyspots() + self.red.getnum_teamemptyspots()
    
    def ismatchfull(self):
        all_players = self.getfullrosters()
        cnt = 0
        for player in all_players:
            if player.getplayerid() != "":
                cnt += 1
        if cnt == 10:
            return True
        else:
            return False
        
    def swapplayers(self,role: str):
        temp_player = getattr(self.blue,role)
        self.blue.setplayerasrole(getattr(self.red,role),role)
        self.red.setplayerasrole(temp_player,role)


'''
A single team in LoL
Has 1 Player in each of the 5 roles
'''
class Team:
    
    def __init__(self,name):
        
        self.name = name
        self.top = Player()
        self.jg = Player()
        self.mid = Player()
        self.bot = Player()
        self.sup = Player()

    '''
    Checks if the specified role is filled by a player
    '''
    def isfilled(self,role:str):
        if getattr(self,role).getplayerign() != "":
            return True
        else:
            return False
        
    # def getplayer(self,role:str):
    #     return getattr(self,role)
        
    def setteamname(self,name:str):
        self.name = name

    def getteamname(self):
        return self.name

    def getteamplayers(self):
        return [self.top,self.jg,self.mid,self.bot,self.sup]

    '''
    Sets specified player into specified role in the team
    '''
    def setplayerasrole(self,player,role):
        setattr(self, role, player)

    '''
    Playerid must match one of the roles' players. 
    Replaces the player with new empty player (so that people can queue in it)
    '''
    def removeplayer(self, playerid):
        # print(self.getteamplayers())
        player = Player()
        if self.top.getplayerid() == playerid:
            self.top = player
            return True
        elif self.jg.getplayerid() == playerid:
            self.jg = player
            return True
        elif self.mid.getplayerid() == playerid:
            self.mid = player
            return True
        elif self.bot.getplayerid() == playerid:
            self.bot = player
            return True
        elif self.sup.getplayerid() == playerid:
            self.sup = player
            return True
        else:
            print("ERROR: Could not remove any player. Check the other team?")
            return False

    def getnum_teamemptyspots(self):
        n = 0   # number of empty spots
        for player in self.getteamplayers():
            if player.getplayerid() == "":
                n += 1
        return n
    
    def getteammmr(self):
        team_mmr = 0.0
        for player in self.getteamplayers():
            team_mmr += player.getmmr()
        team_mmr = team_mmr / 5
        return team_mmr
    
    def getteammulti(self):
        url = "https://www.op.gg/multisearch/NA?summoners="
        for player in self.getteamplayers():
            url += player.getplayerign().replace(" ","+").replace("#","%23")
            url += ","
        return url

'''
Representing a single palyer
Has name (discord name) and rank, which is a point based on lol rank/division
*A player cannot play another game until their last game has been declared finished* (To be implemented later)
Each player has a unique (discord) id that is identified with, in case their name changes 
Elo is the points they gain from the inhouse games
'''
class Player:

    def __init__(self):
        
        self.id = "" #discord id
        self.ign = "" #league ign
        self.rank = "" #Tier + Division in solq
        self.inhouseelo = 1200  #gains points after every match

    def getplayerid(self):
        return self.id
    
    def getplayerign(self):
        return self.ign
    
    def getplayerrank(self):
        return self.rank
    
    def getplayerelo(self):
        return self.inhouseelo
    
    def setplayerid(self,id):
        self.id = id

    def setplayerign(self,name:str):
        self.ign = name

    def setplayerrank(self,rank:int):
        self.rank = rank

    def setplayerelo(self,elo:int):
        self.inhouseelo = elo

    def getmmr(self):
        return datab.rank_dict.get(self.rank)



