import discord
import asyncio
import os

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
        self.wteam = None
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
        if self.name != "":
            return self.name
        else:
            #produce error
            print("Match name not set. Create a name first.")
    
    def getblue(self):
        return self.blue
    
    def getred(self):
        return self.red

    def getfullrosters(self):
        return self.getblue().getteamplayers() + self.getred().getteamplayers()

    def remove_player_from_match(self, playerid):
        self.blue.removeplayer(playerid)
        self.red.removeplayer(playerid)

'''
A single team in LoL
Has 1 Player in each of the 5 roles
'''
class Team:
    
    def __init__(self,name):
        
        self.name = name
        self.top = Player()
        self.jng = Player()
        self.mid = Player()
        self.bot = Player()
        self.sup = Player()
        self.players = [self.top,self.jng,self.mid,self.bot,self.sup]

    '''
    Checks if the specified role is filled by a player
    '''
    def isfilled(self,role:str):
        if getattr(self,role).name != "":
            return True
        else:
            return False
        
    def setteamname(self,name:str):
        self.name = name

    def getteamname(self):
        return self.name

    def getteamplayers(self):
        return [self.top,self.jng,self.mid,self.bot,self.sup]

    '''
    Sets specified player into specified role in the team
    '''
    def setplayerasrole(self,player,role):
        setattr(self, role, player)

    def removeplayer(self, playerid):
        for player in self.players:
            if player.getplayerid() == playerid:
                player.setplayerid("")
                player.setplayername("")
                player.setplayerrank(0)
                player.setplayerelo(0)


'''
Representing a single palyer
Has name (discord name) and rank, which is a point based on lol rank/division
*A player cannot play another game until their last game has been declared finished* (To be implemented later)
Each player has a unique id that is identified with, in case their name changes (To be implemented later)
'''
class Player:

    def __init__(self):
        
        self.id = ""
        self.name = ""
        self.rank = 0 #Tier + Division
        self.inhouseelo = 0

    def getplayerid(self):
        return self.id
    
    def getplayername(self):
        return self.name
    
    def getplayerrank(self):
        return self.rank
    
    def getplayerelo(self):
        return self.inhouseelo
    
    def setplayerid(self,id):
        self.id = id

    def setplayername(self,name:str):
        self.name = name

    def setplayerrank(self,rank:int):
        self.rank = rank

    def setplayerelo(self,elo:int):
        self.inhouseelo = elo



