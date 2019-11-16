from bredlbot.bot import BredlThread
from dynopy.dynopy import DynoPy
from time import sleep, time

POLL_TIME = 300


class BotServer:
    def __init__(self, debug=False):
        self._aws = DynoPy()
        self._channel_info = dict()
        for c in self._aws.get_all_items('Channels'):
            self._channel_info[c['name']] = {'token': c['token']}
        self._channels = [i['name'] for i in self._aws.get_all_items(
            'Bots') if i['enabled'] == 'True']
        self._threads = dict()
        self._debug = debug
        for c in self._channels:
            print(self._channel_info[c])
            self._threads[c] = BredlThread(
                c,
                oauth_token=self._channel_info[c]['token'],
                twitch_irc=True,
                log_only=False)

    def deploy_bots(self):
        for c in self._channels:
            self._threads[c].start()

    def poll(self):
        start = time()
        while True:
            self._channels = [i['name'] for i in self._aws.get_all_items(
                'Bots') if i['enabled'] == 'True']

            for c in self._channels:
                if c not in self._threads:
                    if self._debug:
                        print('{} is being added to the server.'.format(c))
                    self._threads[c] = BredlThread(
                        c, oauth_token=self._channel_info[c]['token'], twitch_irc=True, log_only=False)
                    self._threads[c].start()

            to_remove = []
            for k in self._threads.keys():
                if k not in self._channels:
                    if self._debug:
                        print('{} is being stopped.'.format(k))
                    self._threads[k].stop()
                    to_remove.append(k)

                if self._threads[k].oauth_expired:
                    self._aws.delete('Channel', item={'name': c})
                    self._aws.delete('Bots', item={'name': c})
                    self._threads[k].stop()
                    to_remove.append(k)

            for k in to_remove:
                del self._threads[k]

            if self._debug:
                print('Bredl-Bot-Server: ... Elapsed: {}'.format(time() - start))
                print('Active channels: {}'.format(self._channels))
            sleep(POLL_TIME)


if __name__ == '__main__':
    server = BotServer(debug=True)
    server.deploy_bots()
    server.poll()
