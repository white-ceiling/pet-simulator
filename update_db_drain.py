import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
db_name = 'userdb'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URL1']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

class UserPet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    user_creation_time = db.Column(db.DateTime())
    pet_creation_time = db.Column(db.DateTime())
    timezone = db.Column(db.String(32))
    pet_name = db.Column(db.String(32))
    pet = db.Column(db.Integer)
    current_food_bar = db.Column(db.Integer)
    current_play_bar = db.Column(db.Integer)
    points_exp = db.Column(db.Integer)
    gift = db.Column(db.Integer)
    last_fed = db.Column(db.DateTime())
    who_last_fed = db.Column(db.String(32))
    last_got_fed = db.Column(db.DateTime())
    visitors = db.Column(db.JSON)
    def __repr__(self):
        return '<User %r>' % self.username

def remove_points_for_everyone():
    users = UserPet.query
    food_decrement_switch={
        0: 1,
        1: 3,
        2: 4,
        3: 2,
    }
    play_decrement_switch={
        0: 2,
        1: 2,
        2: 4,
        3: 1,
    }

    for user in users:
        if user.pet is not None:
            key = user.pet
            curr_food = user.current_food_bar
            curr_points = user.points_exp
            if curr_food > 0:
                food_decrement = food_decrement_switch[key]
                curr_points += 60 * 8 * curr_food//food_decrement
                setattr(user, 'current_food_bar', curr_food - food_decrement)

            curr_play = user.current_play_bar
            if curr_play > 0:
                play_decrement = play_decrement_switch[key]
                curr_points += 60 * 8 * curr_play//play_decrement
                setattr(user, 'current_play_bar', curr_play - play_decrement)
            setattr(user, 'points_exp', curr_points)
    db.session.commit()

remove_points_for_everyone()