import discord
import asyncio
import os

'''
A single match in a scrim/in-house game. 
Should have blue & red team. winning team (not determined until game is over and announced), 
'''
class Match:

    def __init__(self):
        
        self.name = ""

        self.blue = Team("Blue")
        self.red = Team("Red")

        self.playernames = self.blue.getteamplayernames() + self.red.getteamplayernames() #bug
        self.playerids = self.blue.getteamplayerids() + self.red.getteamplayerids() #bug
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
        
    def setname(self, name:str):
        self.name = str

    def getname(self):
        if self.name != "":
            return self.name
        else:
            #produce error
            print("Match name not found.")

    def getplayerids(self):
        return self.playerids
    
    def getplayernames(self):
        return self.playernames
    
    def setmatchname(self,name:str):
        self.name = name

    def getblue(self):
        return self.blue
    
    def getred(self):
        return self.red

'''
A single team in LoL
Has 1 player in each of the 5 roles
'''
class Team:
    
    def __init__(self,name):
        
        self.name = name
        self.top = Player()
        self.jng = Player()
        self.mid = Player()
        self.bot = Player()
        self.sup = Player()

    def isfilled(self,role:str):
        if getattr(self,role).name != "":
            return True
        else:
            return False
        
    def setteamname(self,name:str):
        self.name = name

    def getteamname(self):
        return self.name

    def getteamplayerids(self):
        return [self.top.getplayerid(), 
                self.jng.getplayerid(), 
                self.mid.getplayerid(), 
                self.bot.getplayerid(),                     
                self.sup.getplayerid()]
    
    def getteamplayernames(self):
                return [self.top.getplayername(), 
                self.jng.getplayername(), 
                self.mid.getplayername(), 
                self.bot.getplayername(),                     
                self.sup.getplayername()]

    
    def setplayerasrole(self,player,role):
        setattr(self, role, player)

'''
A single player in LoL
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

    def setplayername(self,name:str):
        self.name = name

    def setplayerrank(self,rank:int):
        self.rank = rank

    def setplayerelo(self,elo:int):
        self.inhouseelo = elo

    def setplayerid(self,id):
        self.id = id

    def getplayername(self):
        return self.name
    
    def getplayerrank(self):
        return self.rank
    
    def getplayerid(self):
        return self.id
    

# class Tier:

#     def __init__(self):


# class Division:

#     def __init__(self):


# class scrimData(discord.Client):

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.scrim_data = list()\

# client = scrimData(intents=intents)





