from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional, NumberRange
from app.models import User

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        """Validate that the username is not already taken."""
        user = User.get_by_username(username.data)
        if user is not None:
            raise ValidationError('Please use a different email address.')


class SettingsForm(FlaskForm):
    """Form for user settings."""
    elevenlabs_api_key = StringField('ElevenLabs API Key', validators=[Optional()])
    anthropic_api_key = StringField('Anthropic API Key', validators=[Optional()])
    twitter_email = StringField('Twitter Email', validators=[Optional(), Email()])
    twitter_password = PasswordField('Twitter Password', validators=[Optional()])
    default_voice_id = StringField('Default Voice ID', validators=[Optional()])
    submit = SubmitField('Save Settings')


class NewJobForm(FlaskForm):
    """Form for creating a new job."""
    target_twitter_handle = StringField('Twitter Handle', validators=[DataRequired()])
    max_tweets = IntegerField('Maximum Tweets', 
                             validators=[Optional(), NumberRange(min=1, max=100)],
                             default=20)
    describe_images = BooleanField('Describe Images', default=False)
    voice_id = SelectField('Voice', validators=[DataRequired()])
    submit = SubmitField('Start Job')

    def __init__(self, *args, **kwargs):
        """Initialize the form with available voices."""
        super(NewJobForm, self).__init__(*args, **kwargs)
        # Voice choices will be populated dynamically in the route 