from flask import current_app as app
from flask import render_template, redirect, request, session, url_for, flash, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from .utils.database.database  import database
from werkzeug.datastructures   import ImmutableMultiDict
from pprint import pprint
import json
import random
import functools
from . import socketio
db = database()


#######################################################################################
# AUTHENTICATION RELATED
#######################################################################################
def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if "email" not in session:
            return redirect(url_for("login", next=request.url))
        return func(*args, **kwargs)
    return secure_function

def getUser(get_boards = True):
	user = {}
	if 'email' in session :
		user['email'] = db.reversibleEncrypt('decrypt', session['email'])
		user['is_authenticated'] = True
		# get this user's boards
		if get_boards:
			user['boards'] = db.getBoards(user['email'])

	 
	return user

@app.route('/login')
def login():
	return render_template('login.html', user=getUser())

@app.route('/signup')
def signup():
	return render_template('signup.html', user=getUser())

@app.route('/logout')
def logout():
	session.pop('email', default=None)
	return redirect('/')

@app.route('/processsignup', methods = ["POST"])
def processsignup():
	form_fields = dict((key, request.form.getlist(key)[0]) for key in list(request.form.keys()))

	if form_fields['password'] != form_fields['confirm_password']:
		flash("Passwords do not match. Please try again.", "error")
		return redirect(url_for('signup'))
	
	create = db.createUser(email=form_fields['email'], password=form_fields['password'], role='user')

	if create['success'] == 1:
		session['email'] = db.reversibleEncrypt('encrypt', form_fields['email'])
		flash("Account created successfully! Please log in.", "success")
		return redirect(url_for('home'))
	if create['success'] == -1:
		flash("Email already exists. Try again.", "error")
		return redirect(url_for('signup'))
	flash("Cannot create account.", "error")
	return redirect(url_for('signup'))


@app.route('/processlogin', methods = ["POST"])
def processlogin():
	form_fields = dict((key, request.form.getlist(key)[0]) for key in list(request.form.keys()))
	status = db.authenticate(email=form_fields['email'], password=form_fields['password'])
	print(form_fields['email'], form_fields['password'])
	print(status)
	if  status['success'] == 1:
		session['email'] = db.reversibleEncrypt('encrypt', form_fields['email'])
		return redirect('/') 
	# Failed Login
	flash("Invalid email or password. Please try again.", "error")
	return redirect(url_for('login'))

#######################################################################################
# OTHER
#######################################################################################

@app.route('/')
def root():
	return redirect('/home')

@app.route('/home')
def home():
	user = getUser()
	#db.createBoard('Goon Tube', 'A wild ride', user['email'], [])
	return render_template('home.html', user=user)

@app.route('/create_board', methods = ["POST"])
def create_board():
	data = request.get_json()

	user = getUser(get_boards=False)

	# verify if the users exist before making the db
	if len(data['members']) != 0:
		members_exist = db.verifyMembers(data['members'])
		print(members_exist	)
		if members_exist['success'] == 0:
			return jsonify(members_exist)
	
	# make sure the user isn't listed as one of the members
	if user['email'] in data['members']:
		return jsonify({'success': 0, 'message' : 'Please remove yourself as a member.'})
	

	status = db.createBoard(data['name'], data['description'], user['email'], data['members'])
	status['boards'] = db.getBoards(user['email'])

	return jsonify(status)

def getBoard(board_id):
	board_rows = db.query("SELECT * FROM boards WHERE board_id=%s", [board_id])
	board = board_rows[0]
	
	# need to get the lists
	list_rows = db.query("SELECT * FROM lists WHERE board_id=%s", [board['board_id']])
	list_rows = sorted(list_rows, key=lambda x: x['position'])
	for list in list_rows:
		print(list['name'], list['position'])
	board['lists'] = list_rows
	for list in list_rows:
		# get the cards for this list
		card_rows = db.query("SELECT * FROM cards WHERE list_id=%s", [list['list_id']])
		card_rows = sorted(card_rows, key=lambda x: x['position'])
		list['cards'] = card_rows
	return board

@app.route('/view_board/<int:board_id>')
@login_required
def view_board(board_id):
	user = getUser()
	if db.authorizeBoard(user['email'], board_id):
		board = getBoard(board_id)
		return render_template('view_board.html', board=board, user=user)
	return redirect('/')


@app.route("/static/<path:path>")
def static_dir(path):
    return send_from_directory("static", path)

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r


#######################################################################################
# LIVE COLLAB RELATED
#######################################################################################

# Store connected users for debugging or management purposes
CONNECTED_USERS = {}
ROOM_DATA = {}

@socketio.on('join_board')
def join_board(data):
	board_id = data['board_id']
	room = int(board_id)
	board = getBoard(board_id)
	print(board)
	join_room(room)

	if room not in ROOM_DATA:
		ROOM_DATA[room] = {'total': 1, 'users': [getUser()['email']], 'locked_cards': []}
	else:
		ROOM_DATA[room]['total'] += 1
		ROOM_DATA[room]['users'].append(getUser()['email'])


	print("yass")
	emit('user_joined', {'message': f'User joined board {board_id}'}, room=room)
	emit('current_board', {'board' : board}, room=room)
	emit('receive_lock', ROOM_DATA[room]['locked_cards'])


@socketio.on('leave_room')
def leave_board(data):
	board_id = data['board_id']
	room = f"board_{board_id}"
	leave_room(room)
	print("HERE")
	CONNECTED_USERS[room] = max(0, CONNECTED_USERS.get(room, 1) - 1)
	emit('user_left', {'message': f'User left board {board_id}'}, room=room)

@socketio.on('toggle_card')
def toggle_card(data):
	current_set = ROOM_DATA[data['room']]['locked_cards']
	if data['card_id'] in current_set:
		ROOM_DATA[data['room']]['locked_cards'].remove(data['card_id'])
	else:
		ROOM_DATA[data['room']]['locked_cards'].append(data['card_id'])
	emit('receive_lock', ROOM_DATA[data['room']]['locked_cards'], room=data['room'])

@socketio.on('create_card')
def create_card(data):
	print(data)
	# add the data to the database.
	card_id = db.addCard(data['list_id'], data['card']['title'], data['card']['description'], data['card']['position'])
	data['card']['card_id'] = card_id
	emit('new_card', data, room=data['room'])

@socketio.on('edit_card')
def edit_card(data):
	# add the new data to the database.
	db.updateCard(data['card_id'], data['description'])
	print(db.query('SELECT description FROM cards'))
	emit('card_edited', data, room=data['room'])

@socketio.on('delete_card')
def delete_card(data):
	# remove from the database.
	db.deleteCard(data['card_id'])

	# remove from the lock list if it's there
	if data['card_id'] in ROOM_DATA[data['room']]['locked_cards']:
		ROOM_DATA[data['room']]['locked_cards'].remove(data['card_id'])
	emit('card_deleted', data, room=data['room'])

@socketio.on('card_moved')
def card_moved(data):
	# edit the database
	db.moveCard(data['card_id'], data['new_list'], data['new_position'])

	emit('card_moved', data, room=data['room'])

@socketio.on('out_message')
def out_message(data):
	user = getUser()
	
	print(data['msg'])

	emit('in_message', {'msg': data['msg'], 'user': user['email']}, room=data['room'])

@socketio.on('create_list')
def create_list(data):
	list_id = db.addList(data['name'], data['room'], data['position'])
	emit('new_list', {'list_id': list_id, 'list_name': data['name']}, room=data['room'])

@socketio.on('reorder_lists')
def reorder_lists(data):
	
	db.reorderList(data['order'])

	print(db.query("SELECT * FROM lists"))
	
	emit('lists_reordered', data, room=data['room'], include_self=False)