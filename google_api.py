import mimetypes
import os
import queue
from multiprocessing.pool import ThreadPool

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

ImageEditor, VideoEditor = None, None

try:
    from media_editor import ImageEditor, VideoEditor
except ImportError:
    import sys
    sys.path.append(os.path.abspath('../image'))
    try:
        from media_editor import ImageEditor, VideoEditor
    except ImportError:
        pass


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']
MAX_FILESIZE = 5000000  # Don't send files bigger than 5MB


class GoogleAPI:
    def __init__(self, files_root=None):
        self.creds = self.api_login()
        self.service = build('drive', 'v3', credentials=self.creds)

        self.mapped_folders = {}
        self.files = {}
        self.deleted = {}
        self.force_update = set()

        self.files_root = os.path.abspath(files_root or '.')
        self.drive_root = os.path.split(self.files_root)[-1]

        self.get_root_id()

    def api_login(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file(
                'token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    # Folder iteration

    def get_root_id(self):
        response = self.service.files().list(
            q=f'name = "{self.drive_root}" and mimeType = "application/vnd.google-apps.folder"',
            spaces='drive',
            fields='files(id)'
        ).execute()

        files = response.get("files")
        if files:
            self.root_id = files[0].get("id")
        else:
            self.root_id = self.create_folder(self.drive_root)

        self.mapped_folders[self.root_id] = self.drive_root

    def list_folder(self, force=False):
        def get_req_from_data(root_id, path, page_token):
            search = f"'{root_id}' in parents and trashed = false"
            req = self.service.files().list(
                q=search,
                spaces='drive',
                fields='nextPageToken, '
                'files(id, name, mimeType)',
                pageToken=page_token
            )
            id = f'{root_id}-*-{path}'
            return req, id

        def parse_folder(request_id, response, exception):
            root_id, path = request_id.split('-*-', 1)

            if exception is not None:
                reason = exception.error_details[0]['reason']
                if reason == 'notFound' or reason == 'internalError':
                    print(f'Error on {path}: {reason}')
                elif reason == 'userRateLimitExceeded' or reason == 'rateLimitExceeded':
                    print('Rate limit exceeded')
                    exit()
                else:
                    print(f'Unknown error on {path}: {reason}')
                return None, None

            files, que = {}, []

            for file in response.get('files', []):
                if file.get("mimeType") == 'application/vnd.google-apps.folder':
                    que.append((file.get("id"), path +
                               f'{file.get("name")}/', None))

                    self.mapped_folders[file['id']] = path + file['name']
                else:
                    file['name'] = path + file['name']
                    files[file['name']] = file['id']

            page_token = response.get('nextPageToken', None)
            if page_token is not None:
                que.append((root_id, path, page_token))

            return files, que

        def cb_wrapper(que):
            def wrapped(*args, **kwargs):
                new_files, out = parse_folder(*args, **kwargs)
                if new_files is not None:
                    for data in out:
                        que.put(data)
                    self.files |= new_files
            return wrapped

        if not force and self.files:
            return self.files

        print(f'Listing {self.drive_root} folder')

        count = 0

        que = queue.Queue()
        que.put((self.root_id, self.drive_root + '/', None))

        batch = self.service.new_batch_http_request(callback=cb_wrapper(que))
        while not que.empty():
            data = que.get()
            req, id = get_req_from_data(*data)
            batch.add(req, request_id=id)
            count += 1

            if count >= 100 or que.empty():
                batch.execute()
                count = 0
                batch = self.service.new_batch_http_request(
                    callback=cb_wrapper(que))

    def list_folder_v2(self):
        page_token = None
        self.get_root_id()
        folders = {self.root_id: (self.drive_root, None)}
        while True:
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token

                search = f"trashed = false and mimeType = 'application/vnd.google-apps.folder'"
                req = self.service.files().list(
                    q=search,
                    spaces='drive',
                    fields='nextPageToken, '
                    'files(id, name, parents)',
                    pageToken=page_token
                )
                req.execute()
                response = req.execute()

                for file in response.get('files', []):
                    parents = file.get('parents')
                    if parents:
                        parent = parents[0]
                    else:
                        parent = ''

                    folders[file.get('id')] = (file.get('name'), parent)

                page_token = response.get('nextPageToken', None)
                if not page_token:
                    break

            except HttpError as error:
                print(f'An error occurred: {error}')
                break

        for f_id, (name, parent) in folders.items():
            path = [name]
            while parent in folders:
                p_name, parent = folders[parent]
                path.append(p_name)
            
            path = '/'.join(reversed(path))
            
            self.mapped_folders[f_id] = path
        
        # Files

        page_token = None

        while True:
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token

                search = f"trashed = false and mimeType != 'application/vnd.google-apps.folder'"
                req = self.service.files().list(
                    q=search,
                    spaces='drive',
                    fields='nextPageToken, '
                    'files(id, name, parents)',
                    pageToken=page_token
                )
                req.execute()
                response = req.execute()

                for file in response.get('files', []):
                    parents = file.get('parents')
                    path = self.mapped_folders.get(parents[0], None) if parents else None
                    if path:
                        path += '/'
                    else:
                        path = ''

                    self.files[path + file.get('name')] = file.get('id')

                page_token = response.get('nextPageToken', None)
                if not page_token:
                    break

            except HttpError as error:
                print(f'An error occurred: {error}')
                break
        # TODO - List files too

    def find_folder(self, path):
        path = os.path.normpath(os.path.join(self.files_root, path))
        path = os.path.relpath(path, self.files_root)
        path = self.drive_root + '/' + path
        path = path.replace('\\', '/')

        if path == self.drive_root:
            return self.root_id

        self.list_folder()

        for id, f_path in self.mapped_folders.items():
            if f_path == path:
                return id
                
        # Create the folder
        root, filename = os.path.split(path)
        root = self.find_folder(root)

        folder = self.create_folder(filename, [root])

        self.mapped_folders[folder] = path

        print(f'Created {path}, id {folder}')
        return folder

    def create_folder(self, name, parents=[], execute=True):
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': parents
        }

        req = self.service.files().create(body=file_metadata, fields='id')

        if not execute:
            return req

        return req.execute().get("id")

    def dir_iter(self, root):
        for f in os.listdir(root):
            path = f"{root}/{f}"
            if os.path.isdir(path):
                for sub in self.dir_iter(path):
                    yield sub
            elif root != self.files_root:
                yield path

    # Send files

    def add_media(self, path):
        rootname, name = os.path.split(path)
        root = self.find_folder(rootname)
        file_type = mimetypes.guess_type(path)[0] or '*/*'

        file_metadata = {
            'name': name,
            'mimeType': file_type,
            'parents': [root]
        }
        media = MediaFileUpload(
            os.path.join(self.files_root, path),
            mimetype=file_type,
            resumable=True)
        file = self.service.files().create(
            body=file_metadata, media_body=media, fields='id').execute()

        print(f'Sent {path}, id {file.get("id")}')
        return file

    def get_media(self, file_id, path):
        request = self.service.files().get_media(fileId=file_id)
        # file = io.BytesIO()
        with open(path, 'wb') as file:
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                if status.progress() < 1:
                    print(F'Download {int(status.progress() * 100)}.')

    def get_new_medias(self):
        count = 0
        self.list_folder()
        for file, id in self.files.items():
            if not os.path.exists(file):
                print(F'Downloading file: {file}')
                count += 1
                self.get_media(id, file)
        print(f'Done, {count} new files')

    def add_new_medias(self, processes=1):

        self.list_folder()
        self.purge_deleted()

        deleted = self.get_deleted()
        files = (set(self.files) ^ set(deleted)) - self.force_update

        que = []

        for path in self.dir_iter(self.files_root):
            path = os.path.normpath(os.path.join(self.files_root, path))
            f = os.path.relpath(path, self.files_root)
            f = f.replace('\\', '/')

            if f not in files and not os.path.isdir(path):
                filesize = os.path.getsize(path)
                if filesize < MAX_FILESIZE:
                    try:
                        que.append(f)
                        # self.add_media(f)
                    except HttpError as e:
                        print(f'Error on {f}: {e}')

        if processes == 1:
            for f in que:
                self.add_media(f)
        else:
            with ThreadPool(processes=processes) as p:
                p.imap(self.add_media, que, 10)

    # Delete files

    def get_deleted(self, force=False):
        if not force and self.deleted:
            return self.deleted

        self.list_folder()

        print('Listing trashed files')

        files = {}
        page_token = None
        while True:
            search = f"trashed = true"
            response = self.service.files().list(
                q=search,
                spaces='drive',
                fields='nextPageToken, '
                'files(id, name, parents)',
                pageToken=page_token
            ).execute()
            for file in response.get('files', []):
                parent_id = file.get("parents")[0]

                parent_path = self.drive_root
                for id, path in self.mapped_folders.items():
                    if id == parent_id:
                        parent_path = path
                        break

                name = file.get("name")
                files[parent_path + '/' + name] = file.get("id")

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        self.deleted = files
        return files

    def delete_callback(self, request_id, response, exception):
        if exception is not None:
            # Do something with the exception
            reason = exception.error_details[0]['reason']
            if reason in ('notFound', 'internalError', 'transientError', 'insufficientFilePermissions'):
                print(f'Error on delete: {reason}')
            elif reason == 'userRateLimitExceeded' or reason == 'rateLimitExceeded':
                exit()
            else:
                print(f'Unknown error: {reason}')
        else:
            # Do something with the response
            pass

    def purge(self):
        batch = self.service.new_batch_http_request(
            callback=self.delete_callback)
        count = 0

        page_token = None
        while True:
            search = f"trashed = false"
            response = self.service.files().list(q=search,
                                                 spaces='drive',
                                                 fields='nextPageToken, '
                                                 'files(id)',
                                                 pageToken=page_token).execute()
            for file in response.get('files', []):
                batch.add(self.service.files().delete(fileId=file["id"]))
                count += 1

            if count >= 100:
                batch.execute()
                count = 0
                batch = self.service.new_batch_http_request(
                    callback=self.delete_callback)

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        if count > 0:
            batch.execute()

    def purge_deleted(self):
        batch = self.service.new_batch_http_request(
            callback=self.delete_callback)
        count = 0

        deleted = self.get_deleted()
        for path, id in deleted.items():
            if os.path.exists(path):
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    for f in self.dir_iter(path):
                        os.remove(f)
                    os.rmdir(path)

            batch.add(self.service.files().delete(fileId=id))
            count += 1

            if count >= 100:
                batch.execute()
                print(f'Removed {count} trashed files')
                count = 0
                batch = self.service.new_batch_http_request(
                    callback=self.delete_callback)

        if count > 0:
            batch.execute()
            print(f'Removed {count} trashed files')

    def purge_ghost_files(self):
        self.list_folder()
        count = 0
        batch = self.service.new_batch_http_request(
            callback=self.delete_callback)

        for file, id in self.files.items():
            if not os.path.exists(file):
                batch.add(self.service.files().delete(fileId=id))
                count += 1

                if count >= 100:
                    batch.execute()
                    print(f'Removed {count} ghost files')
                    count = 0
                    batch = self.service.new_batch_http_request(
                        callback=self.delete_callback)

        if count > 0:
            batch.execute()
            print(f'Removed {count} ghost files')

    # File operation

    def get_changes(self, pageToken=None):
        if pageToken is None:
            pageToken = self.service.changes().getStartPageToken().execute().get("startPageToken")
            pageToken = str(max(int(pageToken)-1000, 0)) # Get at most 1000 changes

        changes = []
        while True:
            # # This is kind of hacky, there might be duplicates
            # pageToken = str(int(pageToken)-max(len(changes), 100))

            req = self.service.changes().list(
                spaces='drive',
                fields='changes(time, file(id, parents, name))',
                includeRemoved=False,
                restrictToMyDrive=True,
                pageToken=pageToken,

            ).execute()

            changes = req.get("changes")
            for change in changes:
                yield change
            
            pageToken = req.get("nextPageToken")
            if not pageToken:
                yield 'STOP'
                yield req.get("newStartPageToken")
                return


    def get_comments(self, pageToken):
        def callback(request_id, response, exception):
            if exception is not None:
                # Do something with the exception
                reason = exception.error_details[0]['reason']
                if reason in ('notFound', 'internalError', 'transientError', 'insufficientFilePermissions'):
                    print(f'Error on comments: {reason}')
                elif reason == 'userRateLimitExceeded' or reason == 'rateLimitExceeded':
                    exit()
                else:
                    print(f'Unknown error: {reason}')
            else:
                # Do something with the response
                if not response.get('comments'):
                    return

                count, path = request_id.split('/', 1)

                for comment in response.get('comments'):
                    if comment.get('deleted') is True:
                        continue
                    # if comment.get('id') in parsed:
                    #     continue
                    # else:
                    #     parsed.add(comment.get('id'))
                    anchor = comment.get('anchor')
                    content = comment.get('content')

                    try:
                        self.parse_command(content, path)
                    except Exception as e:
                        print(f'Error while parsing command: {e}')

        # last_change = '2022-06-27T20:07:39.942Z'

        parsed = set()

        self.list_folder()

        batch = self.service.new_batch_http_request(
            callback=callback)
        count = 0

        changes = self.get_changes(pageToken)

        for change in changes:
            if change == 'STOP':
                break

            file = change.get('file')
            if file is None:
                continue

            if file.get('id') in parsed:
                continue

            parsed.add(file.get('id'))

            req = self.service.comments().list(
                fileId=file.get("id"),
                fields='comments(id, anchor, content, deleted)'
            )

            if file.get("name") == self.drive_root:
                continue

            path = None
            
            if file.get('id') in self.mapped_folders:
                path = f'{count}/{self.mapped_folders[file.get("id")]}'
            else:
                root = file.get('parents')
                if root is None:
                    # print(f'No parents for file {file.get("name")}')
                    continue
                root_id = root[0]

                if root_id in self.mapped_folders:
                    path = f'{count}/{self.mapped_folders[root_id]}/{file.get("name")}'

            if path is None:
                print(
                    f'Path not found for {file.get("name")}, parent id {root_id}')
                continue

            batch.add(req, request_id=path)
            count += 1

            if count >= 100:
                batch.execute()
                print(f'Parsed {count} changes')
                count = 0
                batch = self.service.new_batch_http_request(
                    callback=callback)

        if count > 0:
            batch.execute()
            print(f'Parsed {count} changes')
        
        return next(changes)


if __name__ == '__main__':
    # api = GoogleAPI()

    # api.purge()
    # api.list_folder()
    # api.get_new_medias()
    # api.add_new_medias()
    # api.add_media(None)
    # api.schedule()
    # api.purge_ghost_files()

    api = GoogleAPI(files_root=os.path.abspath('insta_data'))
    # api.get_comments()
    # api.list_folder_v2()
    api.add_new_medias()
    pass

    # api.add_new_medias(1)
