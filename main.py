import os, datetime, pytz, timeago
from flask import Flask, render_template, request, session, redirect, url_for, g
from flask_sqlalchemy import SQLAlchemy
from flask_github import GitHub


#session['pet'] = 0 for bird, 1 for cat, 2 for dog, 3 for bunny
tz_name = 'America/Los_Angeles'
tz_pacific = pytz.timezone(tz_name)
app = Flask(__name__)

db_name = 'userdb'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

app.config['GITHUB_CLIENT_ID'] = os.environ['OAUTH_CLIENT_ID']
app.config['GITHUB_CLIENT_SECRET'] = os.environ['OAUTH_CLIENT_SECRET']
github = GitHub(app)

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
    last_got_fed = db.Column(db.DateTime())
    who_last_fed = db.Column(db.String(32))
    visitors = db.Column(db.JSON)
    def __repr__(self):
        return '<User %r>' % self.username
# db.drop_all()
db.create_all()

app.secret_key = os.getenv('SECRET_KEY')


def remove_points(bar_type):
    user = UserPet.query.filter_by(id=session['id']).scalar()
    key = user.pet
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
    if bar_type == 0:
        print('food bar')
        curr_food = user.current_food_bar
        if curr_food > 0:
            print(curr_food, food_decrement_switch[key])
            setattr(user, 'current_food_bar', curr_food - food_decrement_switch[key])
            db.session.commit()
    else:
        curr_play = user.current_play_bar
        if curr_play > 0:
            print(curr_play, play_decrement_switch[key])
            setattr(user, 'current_play_bar', curr_play - play_decrement_switch[key])
            db.session.commit()


def get_pet_type(n):
    type_switch={
        0: 'parrot',
        1: 'cat',
        2: 'dog',
        3: 'bunny',
    }
    return type_switch[n]

def get_max_bars(n):
    max_food_bar_switch={
        0: 8,
        1: 24,
        2: 32,
        3: 16,
    }
    max_play_bar_switch={
        0: 16,
        1: 24,
        2: 32,
        3: 8,
    }
    return (max_food_bar_switch[n], max_play_bar_switch[n])

def get_bars(curf, maxf, curp, maxp):
    food_string = "["
    for i in range(curf):
        food_string += '▓'
    for i in range(maxf - curf):
        food_string += '░'
    food_string += ']'

    play_string = "["
    for i in range(curp):
        play_string += '▓'
    for i in range(maxp - curp):
        play_string += '░'
    play_string += ']'
    
    return food_string, play_string

def get_normal_state(curf, maxf, curp, maxp):
    if (curf < maxf/2) or (curp < maxp/2):
        return '_sad'
    return ''

def render_initial():
    # print(session)
    key = session['pet']
    pet_type = session['pet_type'] = get_pet_type(key)
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
    session['food_decrement'] = food_decrement_switch[key]
    session['play_decrement'] = play_decrement_switch[key]
    session['max_food_bar'], session['max_play_bar'] = get_max_bars(key)
    session['current_food_bar'], session['current_play_bar'] = get_max_bars(key)
    session['action'] = 0
    session['creation_time'] = datetime.datetime.now()
    exists = db.session.query(db.exists().where(UserPet.id == session['id'])).scalar()
    if exists:
        user = UserPet.query.filter_by(id=session['id']).scalar()
        setattr(user, 'pet_creation_time', session['creation_time'])
        setattr(user, 'current_food_bar', session['current_food_bar'])
        setattr(user, 'current_play_bar', session['current_play_bar'])
        setattr(user, 'pet', key)
        if user.points_exp is None:
            setattr(user, 'points_exp', 0)
        db.session.commit()

    return render_template('name.html', type=pet_type, img=url_for('static', filename=pet_type+'.gif'), logged_in=1) #ask for pet name

def initialize_session_from_db():
    exists = db.session.query(db.exists().where(UserPet.id == session['id'])).scalar()
    if exists:
        user = UserPet.query.filter_by(id=session['id']).scalar()
        # session['username'] = user.username
        if user.pet is not None:
            pet = user.pet
            session['pet'] = pet
            session['pet_type'] = get_pet_type(pet)
            session['pet_name'] = user.pet_name
            session['creation_time'] = user.pet_creation_time
            session['tz'] = user.timezone
            session['max_food_bar'], session['max_play_bar'] = get_max_bars(pet)
            session['current_food_bar'], session['current_play_bar'] = user.current_food_bar, user.current_play_bar
            session['points'] = user.points_exp
            # session['tz'] = user.timezone
        # session['visitors'] = user.visitors

@app.route('/')
def hello_world():
    id = None
    username = None
    has_pet = 0
    logged_in = 0
    if 'github_login' in session:
        logged_in = 1
        id = session['id']
        username = session['username']
        if 'pet' not in session:
            initialize_session_from_db()
        if len(session) > 7:
            has_pet = 1
    # print('got here')
    users_db = UserPet.query.order_by(UserPet.last_got_fed.desc())
    users = {}
    counter = 0
    now = datetime.datetime.now()
    for user in users_db:
        if user.pet_name is not None and user.who_last_fed is not None:
            time = user.last_got_fed
            # print(relativedelta(time, datetime.datetime.now()))
            ago = timeago.format(time, now)
            if 'tz' in session and session['tz'] is not None:
                user_tz = pytz.timezone(session['tz'])
                time = time.astimezone(user_tz)
                
                time = time.strftime("%B %-d, %Y at %-I:%M:%S %p")
                
            else:
                
                time = time.strftime("%B %-d, %Y at %-I:%M:%S %p UTC")
                
            counter += 1
            users[user.username] = [user.who_last_fed, user.pet_name, ago, time]
        if counter > 9:
            break
    # print(users)
    return render_template(
        'index.html',
        id=id,
        username=username,
        has_pet=has_pet,
        users=users,
        logged_in=logged_in
    )

@app.route('/main')
def main_pet():
    try:
        exists = db.session.query(db.exists().where(UserPet.id == session['id'])).scalar()
        if not exists:
            user = UserPet(id=session["id"], username=session["username"], pet_name=session["pet_name"], pet=session['pet'], user_creation_time=session['creation_time'], pet_creation_time=session['creation_time'], current_food_bar=session['current_food_bar'], current_play_bar=session['current_play_bar'], points_exp=0, gift=0, last_fed=None)
            db.session.add(user)
            db.session.commit()
        else:
            user = UserPet.query.filter_by(id=session['id']).scalar()
            initialize_session_from_db()
            visitors = user.visitors
            # print(visitors)
            visiting_users = ''
            if visitors and len(visitors['users']) > 0:
                users_length = len(visitors['users'])
                visitors_short = visitors['users'][:10]
                for n, user in enumerate(visitors_short):
                    visiting_users += user
                    if n != users_length - 1:
                        if users_length > 2:
                            if n < users_length - 2:
                                visiting_users += ", "
                            else:
                                visiting_users += ", and "
                        else:
                            visiting_users += " and "
                if users_length > 1:
                    visiting_users += " have"
                else:
                    visiting_users += " has"
                visiting_users += " visited you!"
                # print(visiting_users)
        pet_type = session['pet_type']
        food_bar, play_bar = get_bars(session['current_food_bar'], session['max_food_bar'], session['current_play_bar'], session['max_play_bar'])
        pet_state = get_normal_state(session['current_food_bar'], session['max_food_bar'], session['current_play_bar'], session['max_play_bar'])
        default_img = url_for('static', filename=pet_type + pet_state + ".gif")
        if 'action' in session:
            act = session['action']
            if act == 1:
                pet_state = '_eating'
            if act == 2:
                pet_state = '_playing'
        action_img = url_for('static', filename=pet_type + pet_state + ".gif")
        session['action'] = 0
        return render_template('main.html', type=pet_type.capitalize(), name=session['pet_name'], food=food_bar, play=play_bar, img=action_img, alt_img=default_img, points=session['points'], visitors=visiting_users, logged_in=1)
    except KeyError as e:
        if str(e) == "'id'":
            return render_template('cant_do_that.html', message="Please log in to access your pet!")
        else:
            print(str(e))
            return render_template('cant_do_that.html', message="Please choose a pet first!")
    except Exception as e:
        print(e.__class__)
        return render_template('cant_do_that.html', message="Exception: " + str(e), logged_in=1)

@app.route('/check-name')
def check_name():
    invalid_string = ''
    if 'pet_type' not in session:
        return redirect('/')
    if 'name' in session:
        return render_template('cant_do_that.html', message="No sneaky renaming.")
    name = request.args['pet_name']
    pet_type = session['pet_type']
    name_length = len(name)
    if name_length <= 32 and name_length > 0:
        session['pet_name'] = name
        exists = db.session.query(db.exists().where(UserPet.id == session['id'])).scalar()
        if exists:
            user = UserPet.query.filter_by(id=session['id']).scalar()
            setattr(user, 'pet_name', session['pet_name'])
            db.session.commit()
        return redirect(url_for('main_pet'))
    else:
        invalid_string = 'Choose a shorter name!' if name_length == 1 else 'Choose a longer name!'
        return render_template('name.html', type=pet_type, img=url_for('static', filename=pet_type+'.gif'), invalid=invalid_string, logged_in=1)

@app.route('/reset-pet')
def reset_pet():
    if 'id' in session:
        exists = db.session.query(db.exists().where(UserPet.id == session['id'])).scalar()
        if exists:
            user = UserPet.query.filter_by(id=session['id']).scalar()
            setattr(user, 'pet_creation_time', None)
            setattr(user, 'pet', None)
            setattr(user, 'pet_name', None)
            setattr(user, 'current_food_bar', None)
            setattr(user, 'current_play_bar', None)
            setattr(user, 'gift', 0)
            setattr(user, 'last_fed', None)
            setattr(user, 'last_got_fed', None)
            setattr(user, 'who_last_fed', None)
            db.session.commit()
        id = session['id']
        username = session['username']
        session.clear()
        session['id'] = id
        session['username'] = username
        session['github_login'] = 1
        return redirect('/')
    return redirect('/')

@app.route('/reset-everything')
def reset():
    if 'id' in session:
        exists = db.session.query(db.exists().where(UserPet.id == session['id'])).scalar()
        if exists:
            user = UserPet.query.filter_by(id=session['id']).scalar()
            setattr(user, 'pet_creation_time', None)
            setattr(user, 'pet', None)
            setattr(user, 'pet_name', None)
            setattr(user, 'current_food_bar', None)
            setattr(user, 'current_play_bar', None)
            setattr(user, 'points_exp', 0)
            setattr(user, 'gift', 0)
            setattr(user, 'last_fed', None)
            setattr(user, 'last_got_fed', None)
            setattr(user, 'who_fed', None)
            setattr(user, 'visitors', None)
            db.session.commit()
        id = session['id']
        username = session['username']
        session.clear()
        session['id'] = id
        session['username'] = username
        session['github_login'] = 1
        return redirect('/')
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/feed')
def feed():
    if 'id' in session:
        max_food = session['max_food_bar']
        user = UserPet.query.filter_by(id=session['id']).scalar()
        setattr(user, 'current_food_bar', max_food)
        setattr(user, 'last_got_fed', datetime.datetime.now())
        setattr(user, 'who_last_fed', session['username'])
        db.session.commit()
        session['current_food_bar'] = max_food
        session['action'] = 1
        return redirect(url_for('main_pet'))

@app.route('/play')
def play():
    max_play = session['max_play_bar']
    user = UserPet.query.filter_by(id=session['id']).scalar()
    setattr(user, 'current_play_bar', max_play)
    db.session.commit()
    session['current_play_bar'] = max_play
    session['action'] = 2
    return redirect(url_for('main_pet'))

@app.route('/minus-food')
def minus_food():
    remove_points(0)
    return redirect(url_for('main_pet'))
    
@app.route('/minus-play')
def minus_play():
    remove_points(1)
    return redirect(url_for('main_pet'))

@app.route('/parrot/0')
def initial_parrot():
    if 'id' in session:
        session['pet'] = 0
        return render_initial()
    return render_template('cant_do_that.html', message="Please log in to adopt a pet!")
    
@app.route('/cat/0')
def initial_cat():
    if 'id' in session:
        session['pet'] = 1
        return render_initial()
    return render_template('cant_do_that.html', message="Please log in to adopt a pet!")

@app.route('/dog/0')
def initial_dog():
    if 'id' in session:
        session['pet'] = 2
        return render_initial()
    return render_template('cant_do_that.html', message="Please log in to adopt a pet!")

@app.route('/bunny/0')
def initial_bunny():
    if 'id' in session:
        session['pet'] = 3
        return render_initial()
    return render_template('cant_do_that.html', message="Please log in to adopt a pet!")

@app.route('/settings')
def settings():
    logged_in = 0
    if 'id' in session:
        logged_in = 1
    alerts = ''
    tz = ''
    if 'alerts' in session:
        alerts = session['alerts']
        session.pop('alerts')
    if 'tz' in session and session['tz'] is not None:
        tz = session['tz']
    return render_template('settings.html', timezones=pytz.common_timezones, alerts=alerts, tz=tz, logged_in=logged_in)

@app.route('/submit_settings', methods=["POST", "GET"])
def submit_settings():
    alerts = ''
    if(request.args['chosen_tz'] in pytz.all_timezones):
        session['tz'] = request.args['chosen_tz']
        if 'id' in session:
            user = UserPet.query.filter_by(id=session['id']).scalar()
            setattr(user, 'timezone', session['tz'])
            db.session.commit()
    else:
        alerts += 'Invalid timezone'
        session['alerts'] = alerts
    return redirect(url_for('settings'))

@app.route('/community')
def community():
    logged_in = 0
    if 'id' in session:
        logged_in = 1
    users_db = UserPet.query
    users_dict = {}
    for user in users_db:
        username = user.username
        current_dict = {}
        if user.pet is not None:
            pet = user.pet
            current_dict['pet_name'] = user.pet_name
            time = user.user_creation_time
            if 'tz' in session and session['tz'] is not None:
                user_tz = pytz.timezone(session['tz'])
                time = time.astimezone(user_tz)
                time = time.strftime("%B %-d, %Y at %-I:%M %p")
            else:
                time = time.strftime("%B %-d, %Y at %-I:%M %p UTC")
            current_dict['user_creation_date'] = time
            pet_type = get_pet_type(pet)
            current_dict['pet_type'] = pet_type
            max_food, max_play = get_max_bars(pet)
            cur_food, cur_play = user.current_food_bar, user.current_play_bar
            pet_state = ''
            if (cur_food < max_food/2) or (cur_play < max_play/2):
                pet_state = '_sad'
            current_dict['img'] = url_for('static', filename=pet_type + pet_state + ".gif")
            users_dict[username] = current_dict
    # print(users_dict)
    return render_template('community.html', users=users_dict, logged_in=logged_in)

@app.route('/<user>')
def community_pet(user):
    logged_in = 0
    community_user = UserPet.query.filter_by(username=user).scalar()
    # print(community_user)
    if community_user:
        username = community_user.username
        pet = community_user.pet
        pet_name = community_user.pet_name
        # time = community_user.user_creation_time
        # if 'tz' in session:
        #     user_tz = pytz.timezone(session['tz'])
        #     time = time.astimezone(user_tz)
        # time = time.strftime("%B %-d, %Y at %-I:%M %p")
        pet_type = get_pet_type(pet)
        session['community_max_food_bar'], session['community_max_play_bar'] = max_food, max_play = get_max_bars(pet)
        session['community_current_food_bar'], session['community_current_play_bar'] = cur_food, cur_play = community_user.current_food_bar, community_user.current_play_bar
        food_bar, play_bar = get_bars(cur_food, max_food, cur_play, max_play)
        points = community_user.points_exp
        pet_state = get_normal_state(cur_food, max_food, cur_play, max_play)
        default_img = url_for('static', filename=pet_type + pet_state + ".gif")
        if 'community_action' in session:
            act = session['community_action']
            if act == 1:
                pet_state = '_eating'
            if act == 2:
                pet_state = '_playing'
        action_img = url_for('static', filename=pet_type + pet_state + ".gif")
        session['community_action'] = 0
        if 'id' in session:
            logged_in = 1
            your_username = session['username']
            visitors = community_user.visitors
            if your_username != username:
                if visitors == None:
                    visitors = {}
                    visitors['users'] = [your_username]
                else:
                    if your_username in visitors['users']:
                        visitors['users'].remove(your_username)
                    visitors['users'].insert(0, your_username)
                setattr(community_user, 'visitors', visitors)
                db.session.commit()
                
        return render_template('community_pet.html', type=pet_type.capitalize(), name=pet_name, food=food_bar, play=play_bar, img=action_img, alt_img=default_img, username=username, points=points, logged_in=logged_in)
    return render_template('cant_do_that.html', message="Page not found")

@app.route('/<username>/feed')
def community_feed(username):
    try:
        if 'id' in session:
            max_food = session['community_max_food_bar']
            community_user = UserPet.query.filter_by(username=username).scalar()
            setattr(community_user, 'current_food_bar', max_food)
            now = datetime.datetime.now()
            user = UserPet.query.filter_by(id=session['id']).scalar()
            setattr(user, 'last_fed', now)
            setattr(community_user, 'who_last_fed', session['username'])
            setattr(community_user, 'last_got_fed', now)
    
            db.session.commit()
            session['community_current_food_bar'] = max_food
            session['community_action'] = 1
            
            return redirect('/' + username)
        return render_template('cant_do_that.html', message="Please log in before feeding " + user + "'s pet for them!")
    except:
        return render_template('cant_do_that.html', message="Please adopt your own pet first!")

@app.route('/<username>/play')
def community_play(username):
    try:
        if 'id' in session:
            max_play = session['community_max_play_bar']
            user = UserPet.query.filter_by(username=username).scalar()
            if user:
                setattr(user, 'current_play_bar', max_play)
                db.session.commit()
                session['community_current_play_bar'] = max_play
                session['community_action'] = 2
                return redirect('/' + username)
            return render_template('cant_do_that.html', message="Page not found")
        return render_template('cant_do_that.html', message="Please log in before playing with " + user + "'s pet for them!")
    except:
        return render_template('cant_do_that.html', message="Please adopt your own pet first!")

@app.route('/leaderboard')
def leaderboard():
    logged_in = 0
    
    users_db = UserPet.query.order_by(UserPet.points_exp.desc())
    users = {}
    counter = 0
    top_user = 'n/a'
    message = "Get to the top!"
    for user in users_db:
        if user.points_exp is not None:
            counter += 1
            if counter == 1:
                top_user = user.username
            users[user.username] = [counter, user.points_exp]
        if counter > 9:
            break
    if 'id' in session:
        logged_in = 1
        if session['username'] == top_user:
            message = "You're at the top!"

    return render_template('leaderboard.html', users=users, logged_in=logged_in, message=message)
@app.route('/login')
def login():
    return github.authorize()

@github.access_token_getter
def token_getter():
    if 'oauth_token' in g:
        return g.oauth_token
    else:
        return None
      
@app.route('/callback')
@github.authorized_handler
def authorized(oauth_token):
    # print("oauth_token=", oauth_token)
    if oauth_token is None:
        session.clear()
        return "Authorization failed."
    g.oauth_token = oauth_token
    try:
        github_user = github.get('/user')
        session['username'] = github_user['login']
        session['id'] = github_user['id']
        session['github_login'] = 1
    except Exception as e:
        print("Exception",e)
        session["user"] = None
    return redirect('/')

@app.route('/test')
def session_test():
    pcfctime = datetime.datetime.now()
    pcfctime = pcfctime.astimezone(tz_pacific)
    return render_template(
        'test.html',
        username = session['username'],
        id = session['id'],
        time = pcfctime
    )

if __name__=="__main__":
    app.run(host='0.0.0.0', port=8080)