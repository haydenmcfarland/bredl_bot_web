from wtforms import StringField, Form, BooleanField, FileField
from wtforms.validators import Length, DataRequired


class LogForm(Form):
    channel = StringField('Channel', [DataRequired(), Length(min=4, max=25)])


class UserForm(Form):
    username = StringField('Username', [DataRequired(), Length(min=4, max=25)])


class BotForm(Form):
    log_only = BooleanField()
    public_logs = BooleanField()
