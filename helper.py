from math import fmod
import base64
from datetime import datetime
import os
import pickle


def dict_gen(**kwargs):
    filtered_dict = dict()
    for k in kwargs:
        if kwargs[k]:
            filtered_dict[k] = kwargs[k]
    return filtered_dict


def generate_nonce(length=8):
    if length < 1:
        return ''
    string = base64.b64encode(os.urandom(length), altchars=b'-_')
    indx = int(4 * fmod(length, 3))
    if length % 3 == 1:
        indx += 2
    elif length % 3 == 2:
        indx += 3
    return string[0:indx].decode()


def batch_request_get(req, l):
    params = dict()
    for p in l:
        temp = req.args.get(p)
        params[p] = temp
    return params


def format_date_str(date):
    return datetime.strptime(date, '%Y_%m_%d').strftime('%B %d, %Y')


class PickleHelper:
    @staticmethod
    def save_obj(obj, name):
        with open(name + '.pkl', 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load_obj(name):
        with open(name + '.pkl', 'rb') as f:
            return pickle.load(f)

    @staticmethod
    def all_emotes_to_pickle(api_caller, name):
        emote_data = api_caller.chat.get_all_emoticons()['emoticons']
        emotes = dict()
        for e in emote_data:
            emotes[e['id']] = dict_gen(
                regex=e['regex'], src=e['images'][0]['url'])
        PickleHelper.save_obj(emotes, name)
