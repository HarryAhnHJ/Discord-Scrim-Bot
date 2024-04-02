
import requests
import json
import codecs
import riotapi
import os
from dotenv import load_dotenv
from pathlib import Path

class SauderStats():

    def __init__(self):
        # api_dev = ""
        # api_prod = ""
        # with open("api.txt") as api:
        #     lines = api.readlines()
        
        #     api_dev = lines[0].replace("\n","")
        #     api_prod = lines[1]

        #variables used for requests
        # self.my_api = api_dev
        self.my_region = "NA1"
        self.my_puuid = ""
        self.my_summid = ""

        load_dotenv(Path("E:\Coding\DSB\.env"))
        tokenapi = os.getenv("riotapi_token")

        #required header for url request, change API key until app is approved
        self.header = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 OPR/92.0.0.0",
                            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
                            "Origin": "https://developer.riotgames.com",
                            "X-Riot-Token": tokenapi
                        }

        self.platform_url = "https://na1.api.riotgames.com"
        self.region_url = "https://americas.api.riotgames.com"


    '''
    Uses Riot API to verify user information
    '''
    def get_summoner_data(self,summoner_name:str,tag:str):
        summoner_data = requests.get(self.region_url + '/riot/account/v1/accounts/by-riot-id/' + summoner_name + '/' + tag,
        headers=self.header)
        # print(summoner_data)
        summoner_data_json = summoner_data.json()
        # print(summoner_data_json)
        self.my_puuid = summoner_data_json.get('puuid')
        

        puuid_data = requests.get(self.platform_url + '/lol/summoner/v4/summoners/by-puuid/' + self.my_puuid, headers=self.header)
        
        puuid_data_json = puuid_data.json()
        # print(puuid_data_json)
        self.my_summid = puuid_data_json.get('id')

        rank_data = requests.get(self.platform_url + '/lol/league/v4/entries/by-summoner/' + self.my_summid, headers=self.header)
        # print(rank_data)
        rank_data_json = rank_data.json()
        print(rank_data_json) #this will return [] if not ranked (placements not complete)

        if len(rank_data_json) == 0:
            return False

        for jason in rank_data_json:
            print(jason)
            if jason.get('queueType') == 'RANKED_SOLO_5x5':
                rank = jason.get('tier')
                division = jason.get('rank')
                name = jason.get('summonerName')
                print("do we ever get here?")
                #["UBC Sauder", "DIAMOND","III"]
                return [name + '#'  + tag,rank,division]
            else:
                continue
        return []
        # print('Name: ' + summoner_data_json['name'] + '\n' + 
        #       'Level: ' + str(summoner_data_json['summonerLevel']) + '\n' + 
        #       'Rank: ' +  rank
        #       )
        
    
    def getrankmmr(self,rank):
        return