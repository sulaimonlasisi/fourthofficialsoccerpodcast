# Fourth Official Soccer Podcast

## Repo Information

This repo automates the podcast update process for the Fourth Official Soccer podcast. 
The `podcast_workflow` folder contains the files needed to upload a new podcast episode to s3 and update the rss feed associated with the podcast so that the podcast becomes available on the major podcast platforms.
The `fourth_official_website` contains data and assets for the `www.fourthofficialsoccerpodcast.com` website that is in the works and will also feature heavily in the work we have to do in this repo.

## Developer Information

To use or contribute to this repo, please follow the following steps and submit feedback for any gaps that could be missing.

1. Clone this Github repo
2. Create a `python3.7` virtual environment to install all required packages in a separate env.
3. `cd` into `podcast_workflow` folder and run `pip install -r requirements.txt`
4. Obtain a working version of `config.ini` from the owner of this repo
5. Run `python upload_podcast.py` and follow prompts.

