import discord

class Scrim(object):

    def __init__(self, your_team, opponent, matchss, draftss, date):

        self.your_team = your_team
        self.opponent = opponent
        self.matchss = matchss
        self.draftss = draftss
        # match should be a gyazo screenshot of match, or in the future incorporate API to include link of stats
        self.date = date


class scrimData(discord.Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scrim_data = list()

        



intents = discord.Intents.default()
intents.message_content = True

client = scrimData(intents=intents)
client.run('MTA0OTg5Mjk0NDQ2OTAzNzExNg.GSQ-AB.XJ9eXNaN-D2tug7g8iAmDFGJyTkjExjgDQPu0c')