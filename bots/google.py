import os
import toml
import pytz
import logging
from dateutil.parser import parse

from disnake.ext import commands

from .utils.google import GoogleCalendarAPI
from ._base import Bot


class GoogleCalendar(Bot):
    jschema = {
        "$schema":"http://json-schema.org/draft-04/schema#",
        "title":"GoogleCalendarConfig",
        "description":"Config for GoogleCalendar",
        "type":"object",
        "properties":{
            "communities_name": {
                "description": "",
                "type": "array"
            },
            "email":{
                "description":"The email of the calendar to get events from",
                "type": "string"
            },
            "credentials_file":{
                "description":"The credential file of the calendar",
                "type": "string"
            }
        },
        "required":[
            "communities_name",
            "email",
            "credentials_file"
        ]
    }

    def __init__(self, bot, config, sched, dclient, rclient, *args, **kwargs):
        super().__init__(bot, config, sched, dclient, rclient)
        self.clients = []

        self.other_communities = self.communities_name
        for bot_config in getattr(self.config.BOTS, self.name, []):
            try:
                self.clients.append(
                    GoogleCalendarAPI(
                        bot_config.email,
                        bot_config.credentials_file,
                    )
                )
            except FileNotFoundError:
                logging.error(f"Ignore {self.name} for now. Google {bot_config.credentials_file} not found.")
                continue

            for community_name in bot_config.communities_name:
                self.update_communities(community_name)

            self.other_communities = [x for x in self.other_communities if x not in bot_config.communities_name]

    def parse_date(self, date):
        """ Parse data."""
        if 'date' in date:
            date = parse(date['date'])
            return date.replace(tzinfo=pytz.UTC).isoformat()
        else:
            date = date['dateTime']
            return parse(date).isoformat()

    def clean_google_description(self, description):
        """ Clean description from google. """
        description = description.replace('<span>', ' ')
        description = description.replace('</span>', ' ')
        description = description.replace('<html-blob>', ' ')
        description = description.replace('</html-blob>', ' ')
        description = description.strip(' ')
        return description

    @commands.Cog.listener()
    async def on_ready(self):
        print('google bot ready')
        self.sched.add_job(self.get_data, 'interval', args=(self.dclient,), minutes=5)
        await self.get_data(self.dclient)

    def format_event(self, event, api_ver):
        community_name, name = event['summary'].split('`')
        start_time = self.parse_date(event['start'])
        end_time = self.parse_date(event['end'])
        location = event['location']
        location_web_session_url = ''
        location_session_url = ''
        description = ''
        if 'description' in event:
            description = self.clean_google_description(event['description'])
            location_web_session_url = self.get_location_web_session_url(event['description'])
            location_session_url = self.get_location_session_url(event['description'])
        if api_ver == 1:
            event = self.sformat(
                title = name,
                description = description,
                location_str = location,
                start_time = start_time,
                end_time = end_time,
                community_name = community_name,
                api_ver = 1
            )
        if api_ver == 2:
            session_image = ''
            event = self.sformat(
                title = name,
                description = description,
                session_image = session_image,
                location_str = location,
                location_web_session_url = location_web_session_url,
                location_session_url = location_session_url,
                start_time = start_time,
                end_time = end_time,
                community_name = community_name,
                community_url = "",
                api_ver = 2
            )
        return event

    async def get_data(self, dclient):
        print('update google events')
        for google in self.clients:
            google_data = google.get_events()
            _events_v1 = []
            _events_v2 = []
            for event in google_data['items']:
                _events_v1.append(self.format_event(event, api_ver=1))
                _events_v2.append(self.format_event(event, api_ver=2))

            self.rclient.write('events_v1', _events_v1, api_ver=1, other_communities=self.other_communities)
            self.rclient.write('events_v2', _events_v2, api_ver=2, other_communities=self.other_communities)

            _aggregated_events_v1 = self.get_aggregated_events(api_ver=1)
            if _aggregated_events_v1:
                _events_v1.extend(_aggregated_events_v1)
            self.rclient.write('aggregated_events_v1', _events_v1, api_ver=1, other_communities=self.other_communities)

            _aggregated_events_v2 = self.get_aggregated_events(api_ver=2)
            if _aggregated_events_v2:
                _events_v2.extend(_aggregated_events_v2)
            self.rclient.write('aggregated_events_v2', _events_v2, api_ver=2, other_communities=self.other_communities)