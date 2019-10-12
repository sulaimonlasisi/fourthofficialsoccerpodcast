from __future__ import print_function
import time
import boto3
# get clients
sts_client = boto3.client('sts')
sts_client.get_session_token()
transcribe = boto3.client('transcribe')

job_name = "episode0_transcript"
job_uri = "https://s3.us-east-1.amazonaws.com/fourth-official-soccer-podcast/episodes/fourth_official_soccer_podcast_ep0.mp3"
transcribe.start_transcription_job(
    TranscriptionJobName=job_name,
    Media={'MediaFileUri': job_uri},
    Settings={'MaxSpeakerLabels':2, 'ShowSpeakerLabels': True},
    MediaFormat='mp3',
    LanguageCode='en-US'
)
while True:
    status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
        break
    print("Not ready yet...")
    time.sleep(5)
print(status)
