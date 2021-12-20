import time

from pydrive2.drive import GoogleDrive
from pydrive2.auth import GoogleAuth, AuthenticationError

def auth_gd() -> GoogleDrive:
    try:
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        return GoogleDrive(gauth)
    except AuthenticationError as e:
        exit(1)
