# Fourth Official Soccer Podcast

## Repo Information

This repo automates the podcast update process for the Fourth Official Soccer podcast. 
The `podcast_workflow` folder contains the files needed to upload a new podcast episode to s3 and update the rss feed associated with the podcast so that the podcast becomes available on the major podcast platforms.
The `fourth_official_website` contains data and assets for the `www.fourthofficialsoccerpodcast.com` website.

## Workflow 

The main steps in the worlflow of this app are listed below:

  1. Most of the work is wrapped in `podcast_workflow/upload_podcast.py` and it is the entry point for the application. When this file is run, it asks the user for the location of the podcast recording mp3 which then gets uploaded to s3.
  2. The script then asks for more information (Podcast title and Podcast description) which gets uploaded to the `rss_feed.xml` file for the podcast and is automatically picked up by Spotify and Google Podcasts. 
  3. For Apple podcasts, you have to manually refresh the podcast catalog by logging in into the Apple podcasts page. It takes about 20-30 minutes for this podcast to reflect on all three platforms so we typically wait 30 minutes after this upload before proceeding to next phase.
  3. After 30 minutes have elapsed, the application extracts episode metadata information from each Podcast platform (Spotify, Google Podcasts and Apple Podcasts), then it uses these to generate twitterized links. These twitterized links, along with a short prompted description are posted on the Twitter page of the podcast (@4thOfficialSP).
  4. The application also posts links to the podcasts along with a longer description on the Podcast's [website](www.fourthofficialsoccerpodcast.com)
  5. This ends the workflow of socializing the podcast every week.

## Developer Information

To use or contribute to this repo, please follow the following steps and submit feedback for any gaps that could be missing.

1. Clone this Github repo
2. Create a `python3.7` virtual environment to install all required packages in a separate env.
3. `cd` into `podcast_workflow` folder and run `pip install -r requirements.txt`
4. Obtain a working version of `config.ini` from the owner of this repo
5. Run `python upload_podcast.py` and follow prompts.

