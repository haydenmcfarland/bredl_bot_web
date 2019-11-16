# MODULE IMPORTS
from os import environ
from time import time
from datetime import datetime
from htmlmin.main import minify

# FLASK IMPORTS
from flask import Flask, request, render_template, abort, flash, redirect, url_for, session

# TWITCH IMPORTS
from twitchpy.api import TwitchAPI
from twitchpy.extensions.embedded import EmbeddedChat, EmbeddedVideo

# DYNOPY IMPORTS
from dynopy.dynopy import DynoPy
from dynopy.dynopy import ClientError

# REQUESTS
import requests

# APPLICATION IMPORTS
import constants
from config import Local, Production
from helper import dict_gen
from blueprints import twitch_oauth, chat_logs

# Initialize Flask Application
app = Flask(__name__)
app.config.from_object(Local)
app.config['db'] = DynoPy(debug=app.config['DEBUG'])
app.register_blueprint(twitch_oauth)
app.register_blueprint(chat_logs)
db = app.config['db']

# Initialize Twitch Dependencies
access_token = db.get(
    'Channels', item=dict_gen(
        name=constants.BOT_NAME))['token']
app.config['twitch'] = TwitchAPI(app.config['CID'], access_token)


@app.after_request
def response_minify(response):
    if response.content_type == u'text/html; charset=utf-8':
        response.set_data(
            minify(response.get_data(as_text=True))
        )
        return response
    return response


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.context_processor
def curr_date():
    now = datetime.utcnow()
    return dict_gen(curr_time=now.strftime('%Y_%m_%d'))


@app.route('/')
def index():
    chat = EmbeddedChat(constants.BOT_NAME, width='100%')
    channels = [i['name'] for i in db.get_all_items('Channels')]
    return render_template(
        'index.html',
        chat=chat,
        channels=channels,
        news=None)


@app.route('/bredl/<u>')
def user(u):
    if 'user' in session:
        name = u.lower()
        if session['user']['name'].lower() == name:
            if 'bot' not in session['user']:
                try:
                    temp = db.get('Bots', item=dict_gen(name=name))
                    temp['time'] = int(temp['time'])
                    session['user']['bot'] = temp
                except ClientError:
                    session['user']['bot'] = None

            if 'chat' not in session['user']:
                session['user']['chat'] = EmbeddedChat(
                    name, width='100%').iframe

            if 'video' not in session:
                session['user']['video'] = EmbeddedVideo(
                    name, width='100%').iframe

            if session['user']['bot']:
                switch = session['user']['bot']['enabled'] == 'True'
                st = session['user']['bot']['time']
                session['user']['blocked'] = constants.BREDL_WAIT_TIME - \
                    int(time() - st) > 0
                tl = constants.BREDL_WAIT_TIME - \
                    int(time() - st) if session['user']['blocked'] else None
                return render_template(
                    'user.html',
                    switch=switch,
                    blocked=session['user']['blocked'],
                    time_left=tl,
                    chat=session['user']['chat'],
                    video=session['user']['video'])
            else:
                return render_template(
                    'user.html',
                    switch=False,
                    blocked=False,
                    chat=session['user']['chat'],
                    video=session['user']['video'])

    flash('User either doesn\'t exist or has not been authorized through Twitch.')
    abort(404)


@app.route('/logout')
def logout():
    if 'user' in session:
        session.pop('user')
        flash('You have been logged out!')
    return redirect(url_for('index'))


def _bot_option(enabled):
    if request.referrer and 'blocked' not in session and 'user' in session:
        if not session['user']['blocked']:
            response = None
            try:
                response = db.get(
                    'Bots', item=dict_gen(
                        name=session['user']['name'].lower()))
            except ClientError:
                if app.config['DEBUG']:
                    pass

            if response:
                bot = dict_gen(
                    name=session['user']['name'].lower(),
                    enabled=enabled,
                    time=int(
                        time()))
                db.put('Bots', bot)
                session['user']['bot'] = bot

                if request.referrer:
                    if enabled == 'True':
                        flash('Your bot will be deployed soon.')
                    else:
                        flash('Your bot will be halted soon.')
                    return request.referrer


@app.route('/bredl/deploy')
def deploy():
    response = _bot_option(enabled='True')
    if response:
        return redirect(response)
    abort(404)


@app.route('/bredl/stop')
def stop():
    response = _bot_option(enabled='False')
    if response:
        return redirect(response)
    abort(404)


if __name__ == "__main__":
    if app.config['LOCAL']:
        app.run(debug=app.config['DEBUG'])
    else:
        port = int(environ.get('PORT', 8000))
        app.run(
            host='0.0.0.0',
            port=port,
            threaded=app.config['THREADED'],
            debug=app.config['DEBUG'])
