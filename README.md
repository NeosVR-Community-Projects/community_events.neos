# community_event.neos

Small API for getting the events in multiple discord servers and Google Agenda with easier parsing for NeosVR.

This tool has been write in a way that different  community can host their own server and can be connected to
each other. There is a main instance available at [neos-community.events](https:/neos-community.events).
# Use

This is the new version 2.0, not tested in production yet, please see the git tag for the version 1.0.

## Configuration

Most of the configuration of this tool are available in the `config.toml` file and the following configuration
keys are available:

- `DISCORD_BOT_TOKEN`: The bot token, in a string format.
- `DISCORD_GUILDS_WHITELISTED`: A list of string discord IDs of different community.
- `SERVERS_EVENT`: A list of string URL of other events server to aggregate in the format of 'scheme://host:port'
- `CALENDARS_ACCEPTED`: The Google calendars ID string to sync event from
- `CREDENTIALS_FILE`: The path of the Google Server Account credentials file, as a string. See below for more information.
- `SHOW_WEBUI`: Enable or now the WebUI, depend if the tool will be used as an API only or no.


## Docker

As an example there is a compose file for start the full project really
easy.

## Metal

If you want to launch the project without docker you will need a
Redis database. This project is then separated in two parts,
the calendar update system and the calendar application by itself.
This two parts can be executed separately and are totally independent
from each other but the two depend of the redis database to work.

For the two applications there is an env variable for set the
redis host: `REDIS_HOST`, it default to `cache`.

## Calendar update system

The calendar update system work in a way that its always listen to
discord events and as a cron job, every 5 minutes to check for missed
events or in case of a reboot of this system.

The calendar update system can simply by launch via:

```
python bot.py
```
### Modularity note

The `bots` folder contains a list of modules to get events from. While
most of them are and will be for discord bot there is actually two
exception, for now. The module called `google` and `discord` are
for Google Calendar and Discord integrated event system. All of the
bot are based on the class `Bot` in the `_base.py` file.

## Calendar application

The calendar application is the system who will handle both API and
web request for now.

The calendar application can simply by launch via

```
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

# Endpoints

- `/v1/events`: return the list of the event in an easy readable format for NeosVR: ```name`description`location`start_time`end_time`community_name\n\r```
  Note: The last line don't have `\n\r`
- `/v1/aggregated_events`: same format as `/v1/events` but return the list of aggragated events from this instance with the ones from the instance listed in the config variable `SERVER_EVENTS`
- `/`: WebUI client

Both endpoints `events` and `aggregated_events` have the possibility to have only some community
listed with the querystring `communities` who take as a parameters a list of community name
separated by a coma.
They also return a list of events from a Google calendar. See configuration below.

# NeosVR facet client

Its possible to see the list of events available in NeosVR via a facet.
You can find the last version available in the public folder at this
address: neosrec:///U-GrayBoltWolf/R-1813632e-ca8f-4492-bec4-9259677394de

![NeosVR facet client](images/facet.png)

# WebUI client

The WebUI client is directly using the functions internally and don't talk to the API in HTTP. Its use a simple css
framework called [Bulma](https://bulma.io/) and are loaded directly from differents CDN for now.

Date are formated directly without taking in account of the timezone of the webbrowser.

There is a support of the discord timestamp but only for the `R` format.

And the neos session URL is automaticaly detected from the description if no URL already present in the locatization parameter.
It will automaticaly use the first, and only the first, URL starting with `http(s)://cloudx.azurewebsites.net` for set the locatization
parameter.

![WebUI client](images/webui.png)

# Add a google agenda

For adding a google agenda you need:

- create a Google calendar with your personal account
- create, or use, a Google Cloud Plateform account and create a new project. Enable the calendar API on it and create a `Service Account` with a `json` API key. Then you need to add the email of this Service Account API key as an authorized user of your personal Google calendar.
- Copy the `json` file next to the project or where you want on the system.
- Update the `config.toml` configuration depending on your need.

Note: The id of the calendar is in the settings of your Google Calendar under calendar integration.

# Note

Either the `title`, the `description`, or the `location` of the event must contain the word `Neos VR` for the event
being returned by the API. Keep in mind that this 3 fields will be striped of their space, new line, some special
char and will be lowered for detect this string.

By default the system have a discord guild whitelist for avoid abuse. If you want to add a guild to the whitelist you need to add it
with the list of the key `DISCORD_GUILDS_WHITELISTED` in the `config.toml` configuration file.
For found what is the id of a guild you can use the script `get_discord_server_list.py` who return the list of guild where the bot is
present.
