from youtube_dl import YoutubeDL
from time import sleep
import json

def search(arg):
    with YoutubeDL({'format': 'bestaudio', 'noplaylist':'True'}) as ydl:
        try: requests.get(arg)
        except: info = ydl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]
        else: info = ydl.extract_info(arg, download=False)
    return (info, info['formats'][0]['url'])

filename = "C:/Users/willi/Downloads/spotify-backup-master/spotify-backup-master/best.json"

with open(filename,'r') as file:
    songs = json.load(file)

with open('playlist.txt','w') as file:
    for track in songs[0]['tracks']:
        name = track['track']['name']
        artist = track['track']['artists'][0]['name']
        try:
            video, source = search(name + " " + artist)
            link = "https://www.youtube.com/watch?v={}".format(video['webpage_url_basename'])
        except:
            print("Can't create link for song: {}".format(video['title']))
        print(video['title'],link)
        file.write(link)
        
