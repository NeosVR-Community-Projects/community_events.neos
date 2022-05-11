import json
import requests
import time
import toml

from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask
from flask import jsonify
from flask import request

from discord import Discord
from utils.google import GoogleCalendar

with open('config.toml', 'r') as f:
    config = toml.load(f)

DISCORD_BOT_TOKEN = config['DISCORD_BOT_TOKEN']
CALENDARS_ACCEPTED = config['CALENDARS_ACCEPTED']
CREDENTIALS_FILE = config['CREDENTIALS_FILE']

class GetData:
    guilds = {}
    str_events = ''
    str_aggregated_events = ''
    dict_events = []
    dict_aggregated_events = []
    discord = Discord(DISCORD_BOT_TOKEN)
    google = GoogleCalendar(CALENDARS_ACCEPTED, CREDENTIALS_FILE)

    def _parse(self, events):
        data = []
        for index, event in enumerate(events):
            description = event['description']
            if description:
                description = description.replace('`', ' ')
                description = description.replace('\n\n', ' ')
                description = description.replace('\n\r', ' ')
                description = description.replace('\n', ' ')
                description = description.replace('\r', ' ')
            else:
                description = ''

            if event['guild_id'].isdigit():
                guild_id = self.guilds[event['guild_id']]
            else:
                guild_id = event['guild_id']
            data.append(
                {'name': event['name'], 'description': description, 'entity_metadata': event['entity_metadata']['location'], 'scheduled_start_time': event['scheduled_start_time'], 'scheduled_end_time': event['scheduled_end_time'], 'guild_id': guild_id}
            )
        return data

    def _format(self, events, quick=False):
        text_data = ""
        for index, event in enumerate(events):
            description = event['description']
            if description:
                description = description.replace('`', ' ')
                description = description.replace('\n\n', ' ')
                description = description.replace('\n\r', ' ')
                description = description.replace('\n', ' ')
                description = description.replace('\r', ' ')
            else:
                description = ''

            if quick:
                text_data += f"{event['name']}`{description}`{event['entity_metadata']}`{event['scheduled_start_time']}`{event['scheduled_end_time']}`{event['guild_id']}"
            else:
                if event['guild_id'].isdigit():
                    guild_id = self.guilds[event['guild_id']]
                else:
                    guild_id = event['guild_id']
                text_data += f"{event['name']}`{description}`{event['entity_metadata']['location']}`{event['scheduled_start_time']}`{event['scheduled_end_time']}`{guild_id}"
            if index != len(events)-1:
                text_data += '\n\r'
        return text_data

    def get_guilds(self):
        self.guilds = {}
        for guild in self.discord.get_guilds():
            self.guilds[guild['id']] = guild['name']

    def get(self):
        events = []
        aggregated_events = []
        self.get_guilds()
        for guild_id in self.guilds.keys():
            try:
                events.extend(self.discord.list_guild_events(guild_id))
            except Exception as e:
                pass
        for server in config['SERVERS_EVENT']:
            r = requests.get(server + '/v1/events')
            if r.status_code != 200:
                print(f'Error {r.status_code}: {r.text}')
                continue
            if not r.text:
                continue
            _server_events = r.text.split('\n\r')
            server_events = [event.split('`') for event in _server_events]
            aggregated_events.extend(
                [{'name': event[0], 'description': event[1], 'entity_metadata': {'location': event[2]}, 'scheduled_start_time': event[3], 'scheduled_end_time': event[4], 'guild_id': event[5]} for event in server_events]
            )

        def clean_google_description(description):
            description = description.replace('<span>', ' ')
            description = description.replace('</span>', ' ')
            description = description.replace('<html-blob>', ' ')
            description = description.replace('</html-blob>', ' ')
            description = description.strip(' ')
            return description

        def parse_date(date):
            if 'date' in date:
                return date['date']
            else:
                return date['dateTime']

        google_data = self.google.get_events()
        google_events = []
        for event in google_data[0]['items']:
            guild_id, name = event['summary'].split('`')
            start_time = parse_date(event['start'])
            end_time = parse_date(event['end'])
            description = ''
            if 'description' in event:
                description = clean_google_description(event['description'])
            google_events.extend(
                [{
                    'name': name,
                    'description': description,
                    'entity_metadata': {'location': event['location']},
                    'scheduled_start_time': start_time,
                    'scheduled_end_time': end_time,
                    'guild_id': guild_id,
                }]
            )
        events.extend(google_events)
        aggregated_events.extend(events)

        aggregated_events.sort(key=lambda x: x['scheduled_start_time'])
        self.dict_aggregated_events = self._parse(aggregated_events)
        self.str_aggregated_events = self._format(aggregated_events)

        events = sorted(events, key=lambda d: d['scheduled_start_time'])
        self.dict_events = self._parse(events)
        self.str_events = self._format(events)

getData = GetData()

getData.get()

sched = BackgroundScheduler(daemon=True)
sched.add_job(getData.get,'interval',minutes=5)
sched.start()

app = Flask(__name__)

def get_communities_sorted_events(events, communities):
    sorted_events = []
    for community in communities:
        for event in events:
            if event['guild_id'] == community:
                sorted_events.append(event)
    return sorted_events

def get_communities_events(communities, aggregated_events=False):
    if communities:
        if aggregated_events:
            events = getData.dict_aggregated_events
        else:
            events = getData.dict_events
        communities = communities.split(',')
        sorted_events = get_communities_sorted_events(
            events, communities
        )
        sorted_events.sort(key=lambda x: x['scheduled_start_time'])
        return getData._format(sorted_events, quick=True)
    else:
        if aggregated_events:
            return getData.str_aggregated_events
        else:
            return getData.str_events

@app.route("/v1/events")
def get_data():
    return get_communities_events(
        request.args.get('communities'),
    )
    return data

@app.route("/v1/aggregated_events")
def get_aggregated_data():
    return get_communities_events(
        request.args.get('communities'),
        aggregated_events=True,
    )

@app.route("/")
def index():
    return "This API provide a list of events of NeosVR groups agragated by the USFN group. If you want to have your group listed or have any question please contact us at the USFN discord group (<a href='https://discord.gg/V3bXqm9j'>https://discord.gg/V3bXqm9j</a>). Source code available at <a href='https://github.com/brodokk/community_events.neos'>https://github.com/brodokk/community_events.neos</a>"