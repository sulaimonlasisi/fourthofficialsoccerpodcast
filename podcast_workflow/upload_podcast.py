import boto3
import copy
import configparser
import json
import logging
import os
import ntpath
import pdb
import pprint
import pytz
import requests
import spotipy
import time
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from datetime import datetime
from datetime import timedelta
from gmusicapi import Mobileclient
from mutagen.mp3 import MP3
from operator import itemgetter
from spotipy.oauth2 import SpotifyClientCredentials

# global clients
sts_client = boto3.client('sts')
sts_client.get_session_token()
s3_client = boto3.client('s3')
s3 = boto3.resource('s3')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
config = configparser.ConfigParser()
config.read('config.ini')

# file vars
remote_file_name = config['DEFAULT']['REMOTE_FILENAME']
local_file_name = config['DEFAULT']['LOCAL_FILENAME']
bucket_name = config['DEFAULT']['BUCKET_NAME']
eastern = pytz.timezone('US/Eastern')
wait_time = 60 # wait time is 10 minutes

def push_new_episode_audio():
  '''Pushes a new episode's audio file to s3
     Returns:
       - dictionary containing:
         - size: size of audio (in bytes)
         - duration of episode (in hours/minutes/seconds)
         - audio_url: the s3 URL of the audio
         - s3_obj_name: the name of the audio in s3
  '''

  audio_file = input(f"Enter exact path of final version of podcast: e.g. C:/file/file.mp3\n")
  
  # get audio duration and size
  audio = MP3(audio_file)
  duration = str(timedelta(seconds=int(audio.info.length)))
  size = str(os.path.getsize(audio_file))

  s3_obj_name = ntpath.basename(audio_file)
  with open(audio_file, "rb") as f:
    try:
      s3_client.upload_fileobj(f, bucket_name, f"episodes/{s3_obj_name}", ExtraArgs={'ACL': 'public-read'})
      logger.debug("Uploaded file successfully.")
      return {
        'audio_url': f"https://{bucket_name}.s3.amazonaws.com/episodes/{s3_obj_name}",
        's3_obj_name': s3_obj_name,
        'duration': duration,
        'size': size
      }
    except Exception as e:
      logger.error(f"Logging failed: {e}")
      raise e

def rss_update_for_new_episode(audio_meta):
  '''Retrieves rss feed and uses metadata of new audio to generate rss data
     Pushes updated rss feed to s3
     Returns: Length of Episodes in RSS Feed
  '''

  # download rss file from s3
  s3.meta.client.download_file(bucket_name, remote_file_name, local_file_name)

  # get meta and use its params in rss_feed.xml
  audio_url = audio_meta['audio_url']
  audio_meta_key = audio_meta['s3_obj_name']
  audio_duration = audio_meta['duration']
  audio_size = audio_meta['size']

  # Add 20 mins to current time
  date = datetime.now(tz=eastern)
  date = date + timedelta(minutes=20)
  fmt = '%a, %d %b %Y %H:%M:%S %Z'
  pubDate = date.astimezone(eastern).strftime(fmt)

  # parse file, ask for new values, create new item, append to xml
  tree = ET.parse(local_file_name)
  root = tree.getroot()
  channel_element = root[0]
  new_episode_element = copy.deepcopy(channel_element[len(root[0])-1]) # make a copy of most recent episode
  for idx, child in enumerate(new_episode_element):
    if idx == 1 or idx == 5:
      child.text = audio_url
    elif idx == 2:
      child.text = pubDate
    elif idx == 4:
      child.set("length", audio_size)
      child.set("url",audio_url )
    elif idx == 6:
      child.text = audio_duration
    elif idx == 7:
      child.text = new_episode_element[3].text
    elif idx < 7:
      child.text = input(f"Enter new: {child.tag}, e.g. {child.text}\n")

  channel_element.append(new_episode_element)
  episodes_list = [child for child in root[0] if child.tag == 'item']
  num_episodes = len(episodes_list)
  tree.write(local_file_name)


  # push parsed file to s3 with public-read permissions
  with open(local_file_name, "rb") as f:
    s3_client.upload_fileobj(f, bucket_name, local_file_name, ExtraArgs={'ACL': 'public-read'}) 

  # delete file from local
  if os.path.exists(local_file_name):
    os.remove(local_file_name)
  
  # return number of episodes which will be used in get_itunes_podcast_info()
  return num_episodes


def get_spotify_info():
  '''Returns the name of the episode, the release date,
  spotify link and the description of the episode;
  all of which can be used to create the snippet
  about the episode.
  '''
    
  client_credentials_manager = SpotifyClientCredentials()
  sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
  search_str = "fourth official soccer podcast"
  media_type = "episode"
  results_limit = 10
  results_offset = 0
  market = "US"
  result = sp.search(search_str, results_limit, results_offset, media_type, market)
  episodes_list  = sorted(result['episodes']['items'], key=itemgetter('release_date'), reverse=True)
  last_episode = episodes_list[0]
  return {
      'name': last_episode['name'],
      'description': last_episode['description'],
      'release_date': last_episode['release_date'],
      'url': last_episode['external_urls']['spotify']
  }


def get_google_music_info():
  '''Returns podcast information of the current episode from Google
  Podcasts. The name of the episode, the release date and the description of the episode;
  all of which can be used to create the about the episode.
  '''

  here = os.path.dirname(os.path.realpath(__file__))
  oauth_path = os.path.join(here, config['DEFAULT']['OAUTH_FILEPATH'])
  device_id = config['DEFAULT']['DEVICE_ID']
  mc = Mobileclient()
  series_title = "Fourth Official Soccer Podcast"
  google_music_url = "https://play.google.com/music/m/"
  
  # mc.perform_oauth() only needed once (can be avoided by providing an oauth file)  
  mc.oauth_login(device_id, oauth_path)
    
  episodes_list = mc.get_all_podcast_episodes(device_id)  
  episodes_list = [episode for episode in episodes_list if episode['seriesTitle'] == series_title]
  episodes_list  = sorted(episodes_list, key=itemgetter('publicationTimestampMillis'), reverse=True)
  last_episode = episodes_list[0]
  underscored_title = last_episode['title'].replace(" ", "_")
  underscored_series_title = last_episode['seriesTitle'].replace(" ", "_")
  
  return {
      'name': last_episode['title'],
      'description': last_episode['description'],
      'publication_timestamp_millis': last_episode['publicationTimestampMillis'],
      'url': f"{google_music_url}{last_episode['episodeId']}?t={underscored_title}-{underscored_series_title}"
  }


def get_itunes_podcast_info(num_episodes_in_rss):
  '''Uses the podcast ID to retrieve information about the iTunes Podcast URL
  More tedious effort involved for this than Google and Spotify
  Uses BeautifulSoup4 for parsing
  '''
  url = config['DEFAULT']['APPLE_PODCAST_URL']
  response = requests.get(url)
  soup = BeautifulSoup(response.text, "html.parser")
  info_script_id = "shoebox-ember-data-store"
  info_script_type = "fastboot/shoebox"
  episode_type = "media/podcast-episode"

  def matches_id_and_type(tag):
    return tag.has_attr('id') and tag.has_attr('type') and tag['id'] == info_script_id and tag['type'] == info_script_type

  info_script = soup.findAll(matches_id_and_type)
  itunes_episodes_count = json.loads(info_script[0].contents[0])["data"]["attributes"]["trackCount"]
  episodes_list = [episode for episode in json.loads(info_script[0].contents[0])["included"] if \
    episode['type'] == episode_type]
  episodes_list  = sorted(episodes_list, key=itemgetter('id'), reverse=True)
  latest_episode = episodes_list[0]

  # If itunes_episodes_count is equal to num_episodes_in_rss, use last episode URL
  # Else, use main podcast URL. This is to anticipate any delay in itunes publishing
  # new podcast episode

  updated = True

  if num_episodes_in_rss == itunes_episodes_count:
    episode_url = latest_episode['attributes']['url']
  else:
    episode_url = json.loads(info_script[0].contents[0])["data"]["attributes"]["url"]
    updated = False

  return {
      'name': latest_episode['attributes']['name'],
      'description': latest_episode['attributes']['description']['standard'],
      'release_date': latest_episode['attributes']['releaseDateTime'],
      'url': episode_url,
      'podcast_updated': updated
  }


audio_meta = push_new_episode_audio()
num_episodes_in_rss = rss_update_for_new_episode(audio_meta)
time.sleep(wait_time)

spotify_episode_info = get_spotify_info()
pprint.pprint(spotify_episode_info)

google_music_info = get_google_music_info()
pprint.pprint(google_music_info)


apple_episode_info = get_itunes_podcast_info(num_episodes_in_rss)
pprint.pprint(apple_episode_info)