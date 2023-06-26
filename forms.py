from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp

from flask_login import current_user
from models import User



class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Regexp('^\+[1-9]\d{1,14}$', message='Please enter a valid phone number in international format.')])
    password = PasswordField('Password', validators=[DataRequired(),Length(min=8, max=20)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError( 'That email is taken. Please choose a different one.')
    def validate_phone(self, phone):
        if not phone.data.startswith("+"):
            phone.data = "+" + phone.data

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class AddToFavoritesForm(FlaskForm):
    submit = SubmitField('Add to Favorites')

class RemoveFromFavoritesForm(FlaskForm):
    event_id = StringField('Event ID', validators=[DataRequired()])
    submit = SubmitField('Remove from Favorites')

class AddToCartForm(FlaskForm):
    submit = SubmitField('Add to Cart')

class RemoveFromCartForm(FlaskForm):
    submit = SubmitField('Remove from Cart')

class CheckoutForm(FlaskForm):
    submit = SubmitField('Pay')
    