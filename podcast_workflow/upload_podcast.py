import boto3
import pdb
import xml.etree.ElementTree as ET
import copy
import os
import ntpath
import datetime
import pytz
from datetime import timedelta
from mutagen.mp3 import MP3



# get clients
sts_client = boto3.client('sts')
sts_client.get_session_token()
s3_client = boto3.client('s3')
s3 = boto3.resource('s3')

# file vars
remote_file_name = "data/rss_feed.xml"
local_file_name = "rss_feed.xml"
bucket_name = "fourth-official-soccer-podcast"
gmt = pytz.timezone('GMT')
eastern = pytz.timezone('US/Eastern')

def push_new_audio():
  audio_file = input(f"Enter exact path of final version of podcast: e.g. C:/file/file.mp3\n")
  
  # get audio duration
  audio = MP3(audio_file)
  duration = str(datetime.timedelta(seconds=int(audio.info.length)))

  s3_obj_name = ntpath.basename(audio_file)
  with open(audio_file, "rb") as f:
    s3_client.upload_fileobj(f, bucket_name, f"episodes/{s3_obj_name}", ExtraArgs={'ACL': 'public-read'})
    return (f"https://{bucket_name}.s3.amazonaws.com/episodes/{s3_obj_name}", s3_obj_name, duration)

def rss_update_new_audio(audio_obj):

  # download rss file from s3
  s3.meta.client.download_file(bucket_name, remote_file_name, local_file_name)

  # get object and use some of its params in rss_feed.xml
  audio_url = audio_obj[0]
  audio_obj_key = audio_obj[1]
  audio_duration = audio_obj[2]
  audio_obj_data = s3_client.get_object(Bucket = bucket_name, Key = f"episodes/{audio_obj_key}")

  # get EST version of upload time by adding 15 mins to S3 upload time
  time = audio_obj_data['ResponseMetadata']['HTTPHeaders']['last-modified']
  date = datetime.datetime.strptime(time, '%a, %d %b %Y %H:%M:%S GMT')
  date = date + timedelta(minutes=15)
  dategmt = gmt.localize(date)
  dateeastern = dategmt.astimezone(eastern)
  fmt = '%a, %d %b %Y %H:%M:%S %Z'
  pubDate = dateeastern.astimezone(eastern).strftime(fmt)

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
      child.set("length", str(audio_obj_data['ContentLength']))
      child.set("url",audio_url )
    elif idx == 6:
      child.text = audio_duration
    elif idx == 7:
      child.text = new_episode_element[3].text
    elif idx < 7:
      child.text = input(f"Enter new: {child.tag}, e.g. {child.text}\n")

  channel_element.append(new_episode_element)
  tree.write(local_file_name)


  # push parsed file to s3 with public-read permissions
  with open(local_file_name, "rb") as f:
    s3_client.upload_fileobj(f, bucket_name, remote_file_name, ExtraArgs={'ACL': 'public-read'}) 

  # delete file from local
  if os.path.exists(local_file_name):
    os.remove(local_file_name)


audio_url = push_new_audio()
rss_update_new_audio(audio_url)
