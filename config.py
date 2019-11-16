import os
import re

HOST_NAME = os.getenv('HOST_NAME')

class Production:
    SECRET_KEY = os.getenv('SECRET_KEY')
    NAME = 'BredlBot'
    CID = os.gentenv('CID')
    SECRET = os.getenv('SECRET')
    REDIRECT_URI = '{}/twitch/oauth'.format(HOST_NAME)
    DEBUG = False
    LOCAL = False
    THREADED = True
    REGEX_HOST_NAME = re.compile(
        r'{}(\/.+)*$'.format(HOST_NAME.replace('/', r'\/')))


class Local(Production):
    REDIRECT_URI = '{}/twitch/oauth'.format('127.0.0.1')
    DEBUG = True
    LOCAL = True
    THREADED = False
    REGEX_HOST_NAME = re.compile(r'{}(\/.+)*$'.format('127.0.0.1'))
