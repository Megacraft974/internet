import os
import queue
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
import traceback

import requests
from instagrapi import Client
from instagrapi.exceptions import (ClientNotFoundError, DirectThreadNotFound,
                                   LoginRequired, MediaNotFound)
from instagrapi.extractors import extract_direct_thread
from instagrapi.types import Media, Story
from sympy import EX

import secret

print(f'---{datetime.now().isoformat()}---')

class Follower():
    FOLLOW = 1 # We followed the user
    UNFOLLOW = 2 # We unfollowed the user
    FOLLOWED = 3 # The user followed us
    UNFOLLOWED = 4 # The user unfollowed us
    
    KEEP = 5 # Don't unfollow
    UNKEEP = 6 # Can unfollow

    def __init__(self, *args, **kwargs) -> None:
        # Construct an instance from sql request data
        self.data = {}
        args = list(args)
        for key in ('pk', 'name', 'follow_since', 'keep', 'following', 'followed'):
            if key in kwargs:
                val = kwargs[key]
            elif args: # Not empty
                val = args.pop(0)
            else:
                val = None

            self.data[key] = val
    
    def __getitem__(self, *args, **kwargs):
        return self.data.__getitem__(*args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        return self.data.__getitem__(*args, **kwargs)

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

AUTH_SETTINGS_FILE = './insta_data/login.json'
DATABASE = './insta_data/database.db'
UNFOLLOW_DELAY = 7 * 24 * 60 * 60 # Unfollow after one week

def get_db():
    global con, cur
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

def login(use_cache=True):
    global cl
    cl = Client()
    if use_cache and os.path.exists(AUTH_SETTINGS_FILE):
        try:
            cl.load_settings(AUTH_SETTINGS_FILE)
        except Exception as e:
            print('Error while loading login settings:', e)

    cl.login(secret.USERNAME, secret.PASSWORD)
    cl.dump_settings(AUTH_SETTINGS_FILE)

    try:
        return cl.account_info()
    except LoginRequired:
        if use_cache:
            return login(use_cache=False)
        else:
            raise

def custom_direct_thread(self, thread_id: int, amount: int = 20, cursor = None):
    # Iterate over all messages from thread
    assert self.user_id, "Login required"
    params = {
        "visual_message_return_type": "unseen",
        "direction": "older",
        "seq_id": "40065",  # 59663
        "limit": "20",
    }
    items = []
    while True:
        if cursor:
            params["cursor"] = cursor
        try:
            result = self.private_request(
                f"direct_v2/threads/{thread_id}/", params=params
            )
        except ClientNotFoundError as e:
            raise DirectThreadNotFound(e, thread_id=thread_id, **self.last_json)
        thread = result["thread"]
        for item in thread["items"]:
            yield item
            # items.append(item)
        cursor = thread.get("oldest_cursor")
        if not cursor or (amount and len(items) >= amount):
            break

def list_threads():
    # List all threads
    threads = cl.direct_threads(thread_message_limit=1)
    for t in threads:
        print(t.id, t.thread_title)

def get_conv_logs(thread_id):
    root = os.path.join('insta_data', 'threads')
    if not os.path.exists(root):
        os.mkdir(root)

    output = os.path.join(root, f'{str(thread_id)}.txt')
    open(output, 'w').close() # Clear file

    thread = cl.direct_thread(thread_id)
    users = {int(u.pk): u.full_name for u in thread.users}
    users[user_id] = info.full_name
    c = 0
    with open(output, 'a', encoding='utf-8') as f:
        for item in custom_direct_thread(cl, thread_id):
            c += 1
            timestamp = item['timestamp']
            sender = users.get(item['user_id'], item['user_id'])
            if item['item_type'] == 'text':
                content = item['text']
            else:
                content = item['item_type']
            data = f'{timestamp}-{sender}: {content}\n'
            f.write(data)
            if c%10 == 0:
                print(f'Saved {c} msgs')

    print('Done')

# print(thread)
# print(cl.direct_thread_by_participants([target_id]))

# medias = cl.user_medias(user_id, 20)

# highlights = cl.user_highlights(user_id)

# reels = cl.get_reels_tray_feed() # Recent stories

# feed = cl.get_timeline_feed()
# stories = cl.news_inbox_v1()

def get_follows(reload=False):
    if reload:
        print('Fetching followers')
        followers = cl.user_followers(user_id)
        print('Fetching following')
        following = cl.user_following(user_id)
        print('Saving data')
        print(f'{len(followers)} followers, {len(following)} following')

        sql = """
            INSERT OR REPLACE INTO users (pk, name, follow_since, keep, following, followed) VALUES (?, ?, ?, ?, ?, ?)
        """
        def iter():
            for pk, u in followers.items():
                followed = pk in following
                yield Follower(pk, u.username, int(time.time()), Follower.UNKEEP, True, followed)
            for pk, u in following.items():
                if pk not in followers:
                    yield Follower(pk, u.username, int(time.time()), Follower.UNKEEP, False, True)

        exists_test = "SELECT EXISTS(SELECT 1 FROM users WHERE pk=?)"
        update = "UPDATE users SET name=?, following=?, followed=? WHERE pk=?"
        insert = "INSERT INTO users (pk, name, follow_since, keep, following, followed) VALUES (?, ?, ?, ?, ?, ?)"
        for follow in iter():
            cur.execute(exists_test, (follow['pk'],))
            exists = cur.fetchone()
            if exists:
                cur.execute(update, (follow['name'], follow['following'], follow['follower'], follow['pk']))
            else:
                cur.execute(insert, follow)
        # cur.executemany(sql, iter())
        con.commit()
    else:
        cur.execute('SELECT pk FROM users WHERE followed=1')
        followers = [e[0] for e in cur.fetchall()]
        cur.execute('SELECT pk FROM users WHERE following=1')
        following = [e[0] for e in cur.fetchall()]

    return followers, following

def unfollow_users():
    unfollow = "UPDATE users SET followed=0 WHERE pk=?"
    log_unfollow = "INSERT INTO follows(pk, action, timestamp) VALUES (?, ?, ?)"
    delete_user = "DELETE FROM users WHERE pk=?"

    sql = f"SELECT * FROM users WHERE followed=1 AND following=0 AND keep={Follower.UNKEEP}"
    cur.execute(sql)
    users = cur.fetchall()

    if len(users) == 0:
        print('No user not following back')
        return
    print(f'{len(users)} users not following back, unfollowing')

    try:
        for user in users:
            pk, name, follow_since, keep, following, followed = user
            follow_time = int(time.time() - follow_since)
            if follow_time > UNFOLLOW_DELAY:
                print(f'Unfollowing {user["name"]}')
                try:
                    out = cl.user_unfollow(pk)
                except requests.exceptions.JSONDecodeError:
                    # User not found / deleted account?
                    print(f'Account not found: {user["name"]}, deleting from db, pk: {pk}')
                    if pk and len(str(pk)) > 0:
                        cur.execute(delete_user, (pk,))
                    continue

                # out = cl.public_a1_request(f"/web/friendships/{pk}/unfollow/")
                if out is not True: # Could be None ?
                    print('Potential error:', user)
                    break

                cur.execute(unfollow, (pk,))
                cur.execute(log_unfollow, (pk, Follower.UNFOLLOW, int(time.time())))
                time.sleep(1)
                # a = cl.user_info(pk)
            else:
                print(f'Still need to wait to unfollow {user["name"]}')
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        print('Saved db')
        con.commit()

def create_dir(path):
    if not os.path.exists(path):
        root = os.path.dirname(path)
        if not os.path.exists(root):
            create_dir(root)
        os.mkdir(path)

def ddl_media(m, user):
    if isinstance(m, dict):
        m = AttrDict(**m)

    root = os.path.abspath(os.path.join('./insta_data', 'stories', user))
    root = Path(root)
    create_dir(root)

    timestamp = m['taken_at']
    if type(timestamp) is int:
        timestamp = str(timestamp)
    elif type(timestamp) is datetime:
        timestamp = str(int(timestamp.timestamp()))

    filename = f'{timestamp}-{m["code"]}'

    path = os.path.join(root, filename)
    if os.path.exists(path):
        return [path]

    try:
        paths = []
        if m['media_type'] == 1 and m['product_type'] == 'story':
            # Story - Photo
            paths.append(cl.story_download_by_url(m['thumbnail_url'], filename=filename, folder=root))
        elif m['media_type'] == 1:
            # Photo
            paths.append(cl.photo_download_by_url(m['thumbnail_url'], filename=filename, folder=root))
        elif m['media_type'] == 2 and m['product_type'] == 'feed':
            # Video
            if m['video_url'] is None:
                return
            paths.append(cl.video_download_by_url(m['video_url'], filename=filename, folder=root))
        elif m['media_type'] == 2 and m['product_type'] == 'story':
            # Story - Video
            paths.append(cl.story_download_by_url(m['video_url'], filename=filename, folder=root))
        elif m['media_type'] == 2 and m['product_type'] == 'igtv':
            # IGTV
            paths.append(cl.video_download(m['pk'], filename=filename, folder=root))
        elif m['media_type'] == 2 and m['product_type'] == 'clips':
            # Reels
            paths.append(cl.video_download(m['pk'], filename=filename, folder=root))
        elif m['media_type'] == 8:
            # Album
            for path in cl.album_download(m['pk'], filename=filename, folder=root):
                paths.append(path)
        else:
            raise Exception(f'Unknown media: {m}')
    except AssertionError as e:
        print(e)
        pass
    return paths

def ddl_story(user_id, que):
    # threads = []

    stories = cl.user_stories(user_id)
    for i, story in enumerate(stories):
        story = story.dict()
        user = story['user']['username']
        print(f'({i+1}/{len(stories)}) {user} - {story["id"]}\n', end="")
        que.put((story, user))

def que_handler(que):
    while True:
        data = que.get()
        if data == 'STOP':
            return
        try:
            ddl_media(*data)
        except Exception as e:
            print(f'Error on download, data: {data}\n error: {e}')

def get_tracked_stories():
    threads = []
    sql = f"SELECT * FROM users WHERE keep={Follower.KEEP}"
    cur.execute(sql)
    tracked_ids = [Follower(*e) for e in cur.fetchall()]

    que = queue.Queue()
    handler = threading.Thread(target=que_handler, args=(que,))
    handler.start()

    for follower in tracked_ids:
        t = threading.Thread(target=ddl_story, args=(follower['pk'],que))
        t.start()
        # t.join()
        threads.append(t)

    for t in threads:
        t.join()
    que.put('STOP')
    handler.join()

def schedule():
    info = login()
    user_id = info.pk

    get_db()

    print(f'Logged in as {info.username}')

    get_tracked_stories()

    followers, following = get_follows()
    unfollow_users()

def send_error(e):
    err_text = traceback.format_exception(e)
    text = (
        '<@309008287888834571>, an error occured on insta_api.py!\n'
        f'Timestamp: {datetime.now().isoformat()}\n'
    ) + ''.join(err_text)

    data = {'content': text}
    requests.post(secret.WEBHOOK_URL, data)

if 'schedule' in sys.argv:
    try:
        schedule()
    except Exception as e:
        print(f'Error: {e}')
        send_error(e)
    exit()

info = login()
user_id = info.pk

get_db()

print(f'Logged in as {info.username}')

target_id = 17949864373890812

# thread_id=340282366841710300949128145641763046122 # Seb
thread_id = 340282366841710300949128151283337671427 # Lana

followers, following = get_follows()
unfollow_users()

get_tracked_stories()
