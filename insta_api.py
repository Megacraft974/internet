import json
import multiprocessing.pool
import os
import queue
import random
import sqlite3
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
import zipfile

import requests
import urllib3
from instagrapi import Client
from instagrapi.types import Location, Media
from instagrapi.exceptions import (ClientError, ClientNotFoundError,
                                   DirectThreadNotFound, LoginRequired,
                                   UserNotFound, ClientLoginRequired, UnknownError)
from instagrapi.extractors import extract_user_short
from instagrapi.utils import json_value

import secret

print(f'---{datetime.now().isoformat()}---')

SETTINGS_FILE = './insta_data/settings.json'
if not os.path.exists(SETTINGS_FILE):
    open(SETTINGS_FILE, 'x').close()
    print('Please set new settings')
    exit()

with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
    SETTINGS = json.load(f)


class Follower():
    FOLLOW = 1  # We followed the user
    UNFOLLOW = 2  # We unfollowed the user
    FOLLOWED = 3  # The user followed us
    UNFOLLOWED = 4  # The user unfollowed us

    KEEP = 5  # Don't unfollow
    UNKEEP = 6  # Can unfollow

    def __init__(self, *args, **kwargs) -> None:
        # Construct an instance from sql request data
        self.data = {}
        args = list(args)
        for key in ('pk', 'name', 'follow_since', 'keep', 'is_following', 'is_followed'):
            if key in kwargs:
                val = kwargs[key]
            elif args:  # Not empty
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


def get_db():
    global con, cur
    con = sqlite3.connect(SETTINGS['DATABASE'])
    con.row_factory = sqlite3.Row
    cur = con.cursor()


def login(use_cache=True):
    global cl
    cl = Client()
    if use_cache and os.path.exists(SETTINGS['AUTH_SETTINGS_FILE']):
        try:
            cl.load_settings(SETTINGS['AUTH_SETTINGS_FILE'])
        except Exception as e:
            print('Error while loading login settings:', e)

    cl.login(secret.USERNAME, secret.PASSWORD)
    cl.dump_settings(SETTINGS['AUTH_SETTINGS_FILE'])

    try:
        return cl.account_info()
    except LoginRequired:
        if use_cache:
            return login(use_cache=False)
        else:
            raise


def custom_direct_thread(self, thread_id: int, amount: int = 20, cursor=None):
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
            raise DirectThreadNotFound(
                e, thread_id=thread_id, **self.last_json)
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
    open(output, 'w').close()  # Clear file

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
            if c % 10 == 0:
                print(f'Saved {c} msgs')

    print('Done')

# print(cl.direct_thread_by_participants([target_id]))

# medias = cl.user_medias(user_id, 20)

# highlights = cl.user_highlights(user_id)

# login()
# reels = cl.get_reels_tray_feed() # Recent reels - sorted??

# feed = cl.get_timeline_feed() # Posts feed
# stories = cl.news_inbox_v1() # News / Notifs / New follows / Stuff
# pass
# Follows


def get_follows(user_id, reload=False):
    if reload:
        print('Fetching followers')
        followers = cl.user_followers(user_id)
        print('Fetching followed')
        followed = cl.user_following(user_id)
        # print('\n'.join(f'{pk}-{u}' for pk, u in sorted(((pk, u.username) for pk, u in followed.items()), key=lambda e:e[1])))
        print('Saving data')
        print(f'{len(followers)} followers, {len(followed)} followed')

        def iter(followers, followed):
            for pk, u in followers.items():
                is_followed = pk in followed
                yield Follower(pk, u.username, int(time.time()), Follower.UNKEEP, True, is_followed)
            for pk, u in followed.items():
                if pk not in followers:
                    yield Follower(pk, u.username, int(time.time()), Follower.UNKEEP, False, True)

        exists_test = "SELECT EXISTS(SELECT 1 FROM users WHERE pk=?)"
        update = "UPDATE users SET name=?, is_following=?, is_followed=? WHERE pk=?"
        insert = "INSERT INTO users (pk, name, follow_since, keep, is_following, is_followed) VALUES (?, ?, ?, ?, ?, ?)"
        try:
            for follow in iter(followers, followed):
                cur.execute(exists_test, (follow['pk'],))
                exists = bool(cur.fetchone()[0])
                if exists:
                    cur.execute(
                        update, (follow['name'], follow['is_following'], follow['is_followed'], follow['pk']))
                else:
                    cur.execute(insert, (follow['pk'], follow['name'], follow['follow_since'],
                                follow['keep'], follow['is_following'], follow['is_followed']))
        finally:
            con.commit()
    else:
        cur.execute('SELECT pk FROM users WHERE is_followed=1')
        followers = [e[0] for e in cur.fetchall()]
        cur.execute('SELECT pk FROM users WHERE is_following=1')
        followed = [e[0] for e in cur.fetchall()]

    return followers, followed


def unfollow_users():
    print('Unfollowing is disabled')
    return 0 # Disabled
    unfollow = "UPDATE users SET is_followed=0 WHERE pk=?"
    log_unfollow = "INSERT INTO actions_logs(pk, action, timestamp) VALUES (?, ?, ?)"
    delete_user = "DELETE FROM users WHERE pk=?"
    count = 0

    sql = f"SELECT * FROM users WHERE is_followed=1 AND is_following=0 AND keep={Follower.UNKEEP}"
    cur.execute(sql)
    users = cur.fetchall()

    if len(users) == 0:
        print('No user not following back')
        return
    print(f'{len(users)} users not following back')

    try:
        for user in users:
            pk, name, follow_since, keep, is_following, is_followed, *_ = user
            follow_time = int(time.time() - follow_since)
            if follow_time > SETTINGS['UNFOLLOW_DELAY']:
                print(f'Unfollowing {user["name"]}')
                continue
                try:
                    out = cl.user_unfollow(pk)
                except requests.exceptions.JSONDecodeError:
                    # User not found / deleted account?
                    print(
                        f'Account not found: {user["name"]}, deleting from db, pk: {pk}')
                    if pk and len(str(pk)) > 0:
                        cur.execute(delete_user, (pk,))
                    continue

                # out = cl.public_a1_request(f"/web/friendships/{pk}/unfollow/")
                if out is not True:  # Could be None ?
                    print('Potential error:', user)
                    break

                count += 1
                cur.execute(unfollow, (pk,))
                cur.execute(
                    log_unfollow, (pk, Follower.UNFOLLOW, int(time.time())))
                time.sleep(1)
                # a = cl.user_info(pk)
            # else:
            #     print(f'Still need to wait to unfollow {user["name"]}')
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        con.commit()
    print(f'Unfollowed {count} users')
    return count


def update_users_info(limit=50):
    print('Updating users')
    count = 0
    sql = "SELECT pk FROM users WHERE followers is null;"  # Could use LIMIT 0,50; too
    cur.execute(sql)
    try:
        for row in cur.fetchall():
            try:
                time.sleep(1)
                pk = row[0]
                print(pk)
                info = cl.user_info(pk)
                sql = f"UPDATE users SET followers=:followers, following=:following, private=:private WHERE pk=:pk"
                data = {
                    'pk': pk,
                    'followers': info.follower_count,
                    'following': info.following_count,
                    'private': int(info.is_private)
                }
                cur.execute(sql, data)

                count += 1
                if count >= limit:
                    break
            except Exception as e:
                print(e)
    finally:
        con.commit()

# Media ddl


def create_dir(path):
    if not os.path.exists(path):
        root = os.path.dirname(path)
        if not os.path.exists(root):
            create_dir(root)
        os.mkdir(path)


def media_downloaded(m):
    # Check if a media has already been downloaded

    if isinstance(m, Media):
        m = m.dict()
    root, filename = get_media_filename(m)

    if m['media_type'] == 8:
        # Album
        for resource in m['resources']:
            # filename_ress = f"{filename}_{resource['pk']}"
            filename_ress = filename.format(resource['pk'])

            for f in os.listdir(root):
                f = f.rsplit('.', 1)[0]
                if f == filename_ress:
                    # File already exists
                    return True
    else:
        for f in os.listdir(root):
            if f.rsplit('.', 1)[0] == filename:
                # File already exists
                return True

    return False


def get_media_folder(m):
    if m['product_type'] == 'story':
        folder = 'stories'
    elif m['product_type'] == 'feed':
        folder = 'posts'
    elif m['product_type'] == 'igtv':
        folder = 'IGTV'
    elif m['product_type'] == 'clips':
        folder = 'reels'
    elif m['media_type'] == 1:
        # Post
        folder = 'posts'
    elif m['media_type'] == 8:
        # Album
        folder = 'posts'
    else:
        folder = 'others'

    return folder


def get_media_filename(m):
    if isinstance(m, Media):
        m = m.dict()
    user = m['user']['username']
    if user is None:
        pk = m['user']['pk']
        user = cl.username_from_user_id(pk)
        if user is None:
            raise Exception(f'User with pk {pk} was not found!')
            return None, None

    root = os.path.abspath(os.path.join(
        './insta_data', get_media_folder(m), user))

    timestamp = m['taken_at']
    if type(timestamp) is int:
        timestamp = str(timestamp)
    elif type(timestamp) is datetime:
        timestamp = str(int(timestamp.timestamp()))

    filename = f'{timestamp}-{m["pk"]}'

    if m['media_type'] == 8:
        # Album
        # Option 1: create a folder
        # root = os.path.join(root, filename)
        # filename = ''

        # Option 2: rename the images
        filename += '-{}'

    create_dir(root)
    return root, filename


def ddl_media(m, force=False):
    if isinstance(m, Media):
        m = m.dict()
    if isinstance(m, dict):
        m = AttrDict(**m)

    root, filename = get_media_filename(m)
    root = Path(root)

    if not force and media_downloaded(m):
        return []

    # print(f"{m['user']['username']} - {m['pk']}")

    try:
        paths = []
        if m['media_type'] == 1 and m['product_type'] == 'story':
            # Story - Photo
            paths.append(cl.story_download_by_url(
                m['thumbnail_url'], filename=filename, folder=root))
        elif m['media_type'] == 1:
            # Photo
            paths.append(cl.photo_download_by_url(
                m['thumbnail_url'], filename=filename, folder=root))
        elif m['media_type'] == 2 and m['product_type'] == 'feed':
            # Video
            if m['video_url'] is None:
                return
            paths.append(cl.video_download_by_url(
                m['video_url'], filename=filename, folder=root))
        elif m['media_type'] == 2 and m['product_type'] == 'story':
            # Story - Video
            paths.append(cl.story_download_by_url(
                m['video_url'], filename=filename, folder=root))
        elif m['media_type'] == 2 and m['product_type'] == 'igtv':
            # IGTV
            paths.append(cl.video_download_by_url(
                m['video_url'], filename=filename, folder=root))
        elif m['media_type'] == 2 and m['product_type'] == 'clips':
            # Reels
            paths.append(cl.video_download_by_url(
                m['video_url'], filename=filename, folder=root))
        elif m['media_type'] == 8:
            # Album
            for resource in m['resources']:
                # filename_ress = f"{filename}_{resource['pk']}"
                filename_ress = filename.format(resource['pk'])
                if resource['media_type'] == 1:
                    paths.append(
                        cl.photo_download_by_url(
                            resource['thumbnail_url'], filename=filename_ress, folder=root)
                    )
                elif resource['media_type'] == 2:
                    paths.append(
                        cl.video_download_by_url(
                            resource['video_url'], filename=filename_ress, folder=root)
                    )
        else:
            raise Exception(f'Unknown media: {m}')
    except AssertionError as e:
        print(e)
        pass
    return paths


def ddl_story(user_id, que):
    stories = cl.user_stories(user_id)
    if len(stories) == 0:
        return

    user = stories[0].dict()['user']['username']
    print(f'{user}: {len(stories)} stories\n', end="")

    for story in stories:
        story = story.dict()
        # user = story['user']['username']

        # print(f'({i+1}/{len(stories)}) {user} - {story["id"]}\n', end="")
        que.put(story)


def ddl_post(user_id, que):
    post = None
    for i, post in enumerate(user_medias(cl, user_id)):
        if media_downloaded(post):
            break

        que.put(post.dict())

    if post is None:
        return
    user = post.dict()['user']['username']
    print(f'{user}: {i} posts\n', end="")


def que_handler(que, paths_queue):
    count = 0
    while True:
        data = que.get()
        if data == 'STOP':
            que.put(count)
            return
        try:
            paths = ddl_media(data)
            paths_queue.put(paths)
            count += len(paths)
        except urllib3.exceptions.SSLError:
            print('SSLError, ignoring')
        except Exception as e:
            print(f'Error on download, data: {data}\n error: {e}, {type(e)}')


def get_tracked_medias():
    sql = f"SELECT * FROM users WHERE keep={Follower.KEEP}"
    cur.execute(sql)
    tracked_ids = [Follower(*e) for e in cur.fetchall()]

    paths_queue = queue.Queue()

    story_que = queue.Queue()
    story_handler = threading.Thread(target=que_handler, args=(story_que,paths_queue))
    story_handler.start()

    post_que = queue.Queue()
    post_handler = threading.Thread(target=que_handler, args=(post_que,paths_queue))
    post_handler.start()

    with multiprocessing.pool.ThreadPool(processes=5) as p:
        p.starmap(ddl_story, [(follower['pk'], story_que)
                  for follower in tracked_ids])

        p.starmap(ddl_post, [(follower['pk'], post_que)
                  for follower in tracked_ids])

    p.join()
    story_que.put('STOP')
    post_que.put('STOP')

    story_handler.join()
    post_handler.join()

    story_count = story_que.get()
    post_count = post_que.get()

    paths = []
    while not paths_queue.empty():
        paths.extend(paths_queue.get())

    return story_count, post_count, paths

# Iterators


def user_followers_gql_chunk(self, user_id: str, max_amount: int = 0, end_cursor: str = None):
    user_id = str(user_id)
    users = []
    variables = {
        "id": user_id,
        "include_reel": True,
        "fetch_mutual": False,
        "first": 12
    }
    self.inject_sessionid_to_public()
    while True:
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(
            variables, query_hash="5aefa9893005572d237da5068082d8d5"
        )
        if not data["user"] and not users:
            raise UserNotFound(user_id=user_id, **data)
        page_info = json_value(
            data, "user", "edge_followed_by", "page_info", default={})
        edges = json_value(data, "user", "edge_followed_by",
                           "edges", default=[])
        for edge in edges:
            user = extract_user_short(edge["node"])
            users.append(user)
            yield user
        end_cursor = page_info.get("end_cursor")
        if not page_info.get("has_next_page") or not end_cursor:
            break
        if max_amount and len(users) >= max_amount:
            break


def user_followers_v1_chunk(self, user_id: str, max_amount: int = 0, max_id: str = ""):
    unique_set = set()
    users = []
    while True:
        result = self.private_request(f"friendships/{user_id}/followers/", params={
            "max_id": max_id,
            "count": 10000,
            "rank_token": self.rank_token,
            "search_surface": "follow_list_page",
            "query": "",
            "enable_groups": "true"
        })
        for user in result["users"]:
            user = extract_user_short(user)
            if user.pk in unique_set:
                continue
            unique_set.add(user.pk)
            users.append(user)
            yield user

        max_id = result.get("next_max_id")
        if not max_id or (max_amount and len(users) >= max_amount):
            break


def user_followers(self, user_id, use_cache=True, amount=0):
    user_id = str(user_id)
    users = self._users_followers.get(user_id, {})
    if not use_cache or not users or (amount and len(users) < amount):
        try:
            for user in user_followers_gql_chunk(self, user_id, amount):
                yield user
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            for user in user_followers_v1_chunk(self, user_id, amount):
                yield user
        self._users_followers[user_id] = {user.pk: user for user in users}


def user_medias_gql(self, user_id: int, sleep: int = 2):
    user_id = int(user_id)
    end_cursor = None
    variables = {
        "id": user_id,
        "first": 50,  # These are Instagram restrictions, you can only specify <= 50
    }
    while True:
        if end_cursor:
            variables["after"] = end_cursor
        medias_page, end_cursor = self.user_medias_paginated_gql(
            user_id, sleep=sleep, end_cursor=end_cursor
        )
        for media in medias_page:
            yield media
        if not end_cursor:
            break
        time.sleep(sleep)


def user_medias_v1(self, user_id: int):
    user_id = int(user_id)
    next_max_id = ""
    while True:
        try:
            medias_page, next_max_id = self.user_medias_paginated_v1(
                user_id,
                end_cursor=next_max_id
            )
        except Exception as e:
            self.logger.exception(e)
            break
        for media in medias_page:
            yield media
        if not self.last_json.get("more_available"):
            break
        next_max_id = self.last_json.get("next_max_id", "")


def user_medias(self, user_id: int):
    user_id = int(user_id)
    try:
        try:
            for media in user_medias_gql(self, user_id):
                yield media
        except ClientLoginRequired as e:
            if not self.inject_sessionid_to_public():
                raise e
            for media in user_medias_gql(self, user_id):
                yield media
    except Exception as e:
        if not isinstance(e, ClientError):
            self.logger.exception(e)
        try:
            for media in user_medias_v1(self, user_id):
                yield media
        except UnknownError as e:
            print(
                f'instagrapi.exceptions.UnknownError on user_medias({user_id}): {e}')

# Target finder


def get_followers(target_pk):
    print('Looking for new users')
    max_users = 20
    count = 0
    sql_exists = "SELECT EXISTS(SELECT 1 FROM users WHERE pk=?), EXISTS(SELECT 1 FROM follows WHERE user=? AND follower=?)"
    sql_user = f"INSERT INTO users (pk, name, follow_since, keep, is_following, is_followed, followers, following, private) VALUES (:pk, :name, {int(time.time())}, {Follower.UNKEEP}, 0, 0, :followers, :following, :private)"
    sql_follow = "INSERT INTO follows (user, follower, last_check) VALUES (:user, :follower, :last_check)"
    sql_follow_update = "UPDATE follows last_check=:last_check WHERE user=:user AND follower=:follower"
    try:
        for follower in user_followers(cl, target_pk):
            pk = int(follower.pk)
            cur.execute(sql_exists, (pk, int(target_pk), pk))

            user_exists, follow_exists = list(map(bool, cur.fetchone()))
            info = cl.user_info(pk)
            if not user_exists:
                data = {
                    'pk': info.pk,
                    'name': info.username,
                    'followers': info.follower_count,
                    'following': info.following_count,
                    'private': int(info.is_private)
                }
                cur.execute(sql_user, data)

                count += 1
                print(
                    f'Saved new user {count}/{max_users}: {data["name"]}, {data["followers"]}/{data["following"]}')
                if count == max_users:
                    break

            data = {
                'user': target_pk,
                'follower': pk,
                'last_check': int(time.time())
            }
            req = sql_follow_update if follow_exists else sql_follow
            cur.execute(req, data)

    finally:
        con.commit()
    if count == 0:
        print('All users already parsed!')
    time.sleep(1)  # Make sure we don't spam too many requests


def find_new_followers():
    sql = "SELECT * FROM follows WHERE last_check = (SELECT MIN(last_check) FROM follows) LIMIT 0,1;"

# Repost


def repost_url(url, desc):
    pk = cl.media_pk_from_url(url)
    media = cl.media_info(pk).dict()

    paths = ddl_media(media, force=True)
    if len(paths) == 0:
        print(f'No media found for url: {url}')
        return

    if desc == '_copy':
        caption = media['caption']
    else:
        caption = desc
    if media['location'] is None:
        location = None
    else:
        location = Location(**media['location'])

    if media['media_type'] == 1:
        cl.photo_upload(
            path=paths[0],
            caption=caption,
            location=location
        )
    elif media['media_type'] == 2:
        cl.video_upload(
            path=paths[0],
            caption=caption,
            location=location
        )
    elif media['media_type'] == 8:
        cl.album_upload(
            paths=paths,
            caption=caption,
            location=location
        )
    else:
        print(f'Unknown media type: {media["media_type"]}')


def repost_scheduled():
    sql = "SELECT url, desc FROM posts WHERE posted=0 AND timestamp < ?"
    sql_save = "UPDATE posts SET posted=1 WHERE url=?"

    cur.execute(sql, (int(time.time()),))
    posts = cur.fetchall()
    if len(posts) == 0:
        print('No post scheduled')
        return
    try:
        for post in posts:
            url, desc = post
            repost_url(url, desc)

            cur.execute(sql_save, (url,))
    finally:
        con.commit()


def add_post(url, timestamp, desc_mode):
    get_db()
    
    sql_exists = "SELECT EXISTS(SELECT 1 FROM posts WHERE url=:url), EXISTS(SELECT 1 FROM posts WHERE url=:url AND posted=1)"
    sql_insert = "INSERT INTO posts (url, timestamp, desc, posted) VALUES (:url, :timestamp, :desc, 0)"
    sql_update = "UPDATE posts SET timestamp=:timestamp, desc=:desc WHERE url=:url"

    cur.execute(sql_exists, (url,))
    exists, post_exists = list(map(bool, cur.fetchone()))

    if exists:
        if post_exists:
            print('This image has already been posted!')
            return
        else:
            print('This image is already registered, updating')

    if isinstance(timestamp, datetime):
        timestamp = timestamp.timestamp()

    timestamp = int(timestamp)

    if desc_mode == 'none':
        desc = ''
    elif desc_mode == 'rnd_emoji':
        desc = random.choice(list(SETTINGS['EMOJIS']))
    else:
        desc = desc_mode

    data = {
        'url': url,
        'timestamp': timestamp,
        'desc': desc
    }
    print(data)
    sql = sql_update if exists else sql_insert
    cur.execute(sql, data)

    con.commit()

# Logistic ig


def schedule():
    info = login()
    user_id = info.pk

    get_db()

    print(f'Logged in as {info.username}')

    story_count, post_count, paths = get_tracked_medias()

    followers, following = get_follows(user_id, True)
    unfollowed = unfollow_users()

    try:
        repost_scheduled()
    except Exception as e:
        send_error(e)

    send_status(info, story_count, post_count, len(
        followers), len(following), unfollowed, paths)


def send_status(info, story_count, post_count, followers_count, following_count, unfollowed, paths):
    archives = create_archive(paths)
    text = (
        'Schedule ran correctly\n'
        f'Account: {info.username}\n'
        f'{story_count} new stories\n'
        f'{post_count} new posts\n'
        f'{followers_count} followers / {following_count} following\n'
        f'{unfollowed} unfollowed users'
    )
    data = {'content': text}
    if len(archives) == 0:
        files = None
    else:
        files = {
            'file': (os.path.basename(archives[0]), open(archives[0], 'rb')),
        }
    r = requests.post(secret.WEBHOOK_URL, data=data, files=files)
    r.raise_for_status()
    if len(archives) > 1:
        for archive in archives[1:]:
            files = {
                'file': (os.path.basename(archive), open(archive, 'rb')),
            }
            r = requests.post(secret.WEBHOOK_URL, files=files)
            r.raise_for_status()
            
    print('Webhook status sent!')
    del files # Close the file
    for archive in archives:
        try:
            os.remove(archive)
        except PermissionError as e:
            print(e)
            pass

def send_error(e):
    err_text = traceback.format_exception(
        type(e), value=e, tb=e.__traceback__)
    text = (
        'An error occured on insta_api.py!\n' if not SETTINGS[
            'DISCORD_PING'] else f'{SETTINGS["DISCORD_PING"]}, an error occured on insta_api.py!\n'
        f'Timestamp: {datetime.now().isoformat()}\n'
    ) + ''.join(err_text)

    data = {'content': text}
    requests.post(secret.WEBHOOK_URL, data)

def create_archive(paths):
    if len(paths) == 0:
        return []
    root = os.path.abspath('./insta_data')
    max_size = 8000000
    count = 0
    size = 0
    
    archive = os.path.join(root,f'new_medias_{count}.zip')
    archives = [archive]
    
    zipf = zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED)
    for path in paths:
        path = os.path.abspath(path)
        file_size = os.path.getsize(path)
        size += file_size
        if size >= max_size:
            zipf.close()
            count += 1
            size = file_size

            archive = os.path.join(root,f'new_medias_{count}.zip')
            archives.append(archive)
            zipf = zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED)

            if file_size > max_size:
                print(f'Skipping {path}: {file_size} bytes is too large')
                size = 0
                continue
        zipf.write(
            path,
            os.path.relpath(path, root)
        )
    zipf.close()
    return archives

if len(sys.argv) > 1:
    file, action, *args = sys.argv
    if action == 'schedule':
        try:
            schedule()
        except Exception as e:
            print(f'Error: {e}')
            send_error(e)
    elif action == 'post':
        keys = ('url', 'timestamp', 'desc_mode')
        while len(args) >= len(keys):
            kwargs = {}
            for k in keys:
                kwargs[k] = args.pop(0)

            # Probably an error if the date is more than 1yr away
            if kwargs['timestamp'].isdigit() and int(kwargs['timestamp'])-time.time() < 365*24*60*60:
                kwargs['timestamp'] = int(kwargs['timestamp'])
            else:
                d_format = '%Y/%m/%d:%H:%M:%S'
                try:
                    kwargs['timestamp'] = datetime.strptime(kwargs['timestamp'], d_format)
                except ValueError:
                    print(
                        f'Invalid timestamp! Must be UNIX timestamp or match the format "{d_format}"')
                    continue

            add_post(**kwargs)

    exit()

info = login()
user_id = info.pk

get_db()

print(f'Logged in as {info.username}')

schedule()
# repost_scheduled()

# def parse_dir(root):
#     for f in os.listdir(root):
#         path = os.path.join(root, f)
#         if os.path.isdir(path):
#             for file in parse_dir(path):
#                 yield file
#         else:
#             yield path

# paths = list(parse_dir('insta_data/posts')) + list(parse_dir('insta_data/stories'))

# create_archive(paths)

# get_followers(user_id)

# followers, following = get_follows(user_id, True)
# unfollow_users()
# update_users_info()

# get_tracked_stories()
