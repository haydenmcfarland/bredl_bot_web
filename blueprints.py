from flask import Blueprint, render_template, session, request, redirect, current_app, url_for, flash, abort
from twitchpy.api import TwitchAPI
from twitchpy.extensions.authentication import Oauth
from twitchpy.other.exceptions import TwitchOauthError
from helper import batch_request_get, generate_nonce, dict_gen
import re
from datetime import datetime
import constants
from helper import PickleHelper, format_date_str
from forms import UserForm, LogForm
from dynopy.dynopy import ClientError


# TWITCH OAUTH BLUEPRINT
twitch_oauth = Blueprint('twitch_oauth', __name__)


@twitch_oauth.route('/twitch/oauth')
def authorize():
    params = batch_request_get(
        request, [
            'code', 'scope', 'state', 'force_verify', 'nonce', 'error'])
    if params['code'] and params['state']:
        if 'state' in session and params['state'] == session['state']:
            response = Oauth.acf_request(
                current_app.config['CID'],
                current_app.config['SECRET'],
                params['code'],
                current_app.config['REDIRECT_URI'],
                session.pop('state'))
            try:
                api_caller = TwitchAPI(
                    current_app.config['CID'],
                    'OAuth ' + response['access_token'])
                user = api_caller.users.get_user()
                payload = dict_gen(
                    name=user['display_name'].lower(),
                    token='OAuth ' + response['access_token'])
                current_app.config['db'].put('Channels', payload)
                session['user'] = dict_gen(name=user['display_name'])
                return render_template(
                    'oauth_success.html',
                    username=user['display_name'])
            except TwitchOauthError:
                flash('Oops. Something went wrong when communicating with Twitch.')
        return render_template('oauth_failed.html')
    else:
        return render_template('oauth.html')


@twitch_oauth.route('/twitch/oauth/redirect')
def twitch_redirect():
    m = re.match(current_app.config['REGEX_HOST_NAME'], request.referrer)
    if m and m.group(1) == '/twitch/oauth':
        session['state'] = generate_nonce()
        return redirect(
            Oauth.acf_connect_link(
                current_app.config['CID'],
                scope='openid+user_read',
                redirect_uri=current_app.config['REDIRECT_URI'],
                state=session['state']))
    return redirect(url_for('.authorize'))


# CHAT LOG BLUEPRINT
chat_logs = Blueprint('chat_logs', __name__)
emotes = PickleHelper.load_obj('emotes')


@chat_logs.route('/logs', methods=constants.METHODS)
def logs():
    form = LogForm(request.form)
    if request.method == 'POST' and form.validate():
        channels = [i['name'].lower()
                    for i in current_app.config['db'].get_all_items('Channels')]
        channel = form.channel.data.lower()
        if channel in channels:
            try:
                item = dict_gen(channel=channel)
                dates = current_app.config['db'].get(
                    'Chat', item=item, projection="log_dates")['log_dates']
                links = [
                    '<a href="/logs/{}/{}">{}</a>'.format(channel, d, format_date_str(d)) for d in dates]
                return render_template('logs.html', logs=links)
            except ClientError:
                flash('Communication with the database failed.')
        else:
            flash('There are no logs for {}'.format(channel))
    return render_template('logs.html', form=form)


@chat_logs.route('/logs/<channel>/<date>', methods=constants.METHODS)
def channel_logs(channel, date):
    form = UserForm(request.form)
    try:
        q = current_app.config['db'].get(
            'Chat',
            item=dict_gen(
                channel=channel),
            projection='logs.#d',
            expression_values={
                '#d': date})
        data = q['logs'][date]
    except (ClientError, KeyError):
        abort(404)

    to_return = []
    for u in data[1:]:
        message = u[0].split(':')
        if request.method == 'POST' and form.validate(
        ) and message[0] != form.username.data.lower():
            continue
        message[-1] = message[-1][1:]
        meta = u[-1]
        if 'display-name' in meta:
            message[0] = meta['display-name']
        if 'color' in meta:
            message[0] = '<p style="color:{}">{}</p>'.format(
                meta['color'], message[0])
        else:
            message[0] = '<p>{}<p>'.format(message[0])
        if 'subscriber' in meta:
            if meta['subscriber'] == '1':
                message[0] = 'SUB <i class="fa fa-star"></i>' + message[0]
        if 'mod' in meta:
            if meta['mod'] == '1':
                message[0] = 'MOD <i class="fa fa-shield"></i> ' + message[0]
        if 'emotes' in meta:
            emote_data = meta['emotes'].split('/')
            for e in emote_data:
                eid = int(e.split(':')[0])
                if eid in emotes:
                    emote = emotes[eid]
                    image_link = '<img src="{}">'.format(emote['src'])
                    message[-1] = re.sub(emote['regex'],
                                         image_link, message[-1])
        if 'sent-ts' in meta:
            sent_utc = datetime.utcfromtimestamp(int(meta['sent-ts']) / 1000)
            sent_utc = sent_utc.strftime('%Y-%m-%d | %H:%M:%S UTC')
            message[-1] += '<br><small style="color:#afafaf;">{}</small>'.format(
                sent_utc)
        to_return.append('{}{}'.format(message[0], message[-1]))
    return render_template(
        'log.html',
        channel=channel,
        date=format_date_str(date),
        data=to_return,
        form=form)
