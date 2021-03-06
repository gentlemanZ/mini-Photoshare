######################################
# author ben lawson <balawson@bu.edu> 
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask.ext.login as flask_login

import time

#for image uploading
from werkzeug import secure_filename
import os, base64


current_date = time.strftime("%Y-%m-%d")
mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'ZTY941128aa'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users") 
users = cursor.fetchall()

def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT email from Users") 
    return cursor.fetchall()

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not(email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user

@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not(email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
    data = cursor.fetchall()
    pwd = str(data[0][0] )
    user.is_authenticated = request.form['password'] == pwd 
    return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
    return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return '''
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='email'></input>
                <input type='password' name='password' id='password' placeholder='password'></input>
                <input type='submit' name='submit'></input>
               </form></br>
	       <a href='/'>Home</a>
               '''
    #The request method is POST (page is recieving data)
    email = flask.request.form['email']
    cursor = conn.cursor()
    #check if email is registered
    if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
        data = cursor.fetchall()
        pwd = str(data[0][0] )
        if flask.request.form['password'] == pwd:
            user = User()
            user.id = email
            flask_login.login_user(user) #okay login in user
            return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

    #information did not match
    return "<a href='/login'>Try again</a>\
            </br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('hello.html', message='Logged out') 

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html') 

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')  

@app.route("/register", methods=['POST'])
def register_user():
    try:
        email=request.form.get('email')
        password=request.form.get('password')
        firstName = request.form.get('firstName')
        lastName = request.form.get('lastName')
    except:
        print "couldn't find all tokens" #this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test =  isEmailUnique(email)
    if test:
        print cursor.execute("INSERT INTO Users (email, password,firstName,lastName) VALUES ('{0}', '{1}','{2}', '{3}')".format(email, password,firstName,lastName))
        conn.commit()
        user = User()
        user.id = email
        flask_login.login_user(user)
        return render_template('profile.html', name=email, message='Account Created!')
    else:
        print "couldn't find all tokens"
        return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, picture_id FROM Pictures WHERE user_id = '{0}'".format(uid))
    return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
    return cursor.fetchone()[0]

def isEmailUnique(email):
    #use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)): 
        #this means there are greater than zero entries with that email
        return False
    else:
        return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    photos = getUsersPhotos(uid)
    return render_template('profile.html', name=flask_login.current_user.id, message="Here's your profile",photos = photos)

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload():
    if request.method == 'POST':
        uid = getUserIdFromEmail(flask_login.current_user.id)
        #lname = getUserNameFromId(uid)
        imgfile = request.files['photo']
        #caption = request.form.get('caption')
        #print caption
        album = request.form.get('album')
        photo_data = base64.standard_b64encode(imgfile.read())
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Pictures (imgdata,user_id,Album_Name) VALUES ('{0}', '{1}', '{2}')".format(photo_data,uid,album))
        conn.commit()       
        return render_template('profile.html', name=flask_login.current_user.id, message="Photo uploaded")
    # The method is GET so we return a  HTML form to upload the a photo.
    else:
        uid = getUserIdFromEmail(flask_login.current_user.id)
        return render_template('upload.html', albums = getAlbumList(uid))
#end photo uploading code 

@app.route('/friends', methods=['GET'])
@flask_login.login_required
def findingFriends():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    users = getUserInformationlist()
    Friends = getFriendList(uid)
    return render_template('friends.html', name=flask_login.current_user.id, message='This is your friends list',Users =users,Friends = Friends)



@app.route('/friends', methods=['POST'])
@flask_login.login_required
def searchFriends():
    firstName = request.form.get('firstName')
    searchResult = getUsersFromFirstNmae(firstName)
    return render_template('friends.html', name=flask_login.current_user.id, message='This is your friends list', searchResult = searchResult)

@app.route('/friends/addingFriend', methods=['GET'])
@flask_login.login_required
def addingFriend():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    friend_id = request.args['info']
    cursor = conn.cursor()
    cursor.execute("INSERT INTO friends (user_id, friend_id) VALUES ('{0}', '{1}' )".format(uid,friend_id))
    conn.commit()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    users = getUserInformationlist()
    Friends = getFriendList(uid)
    return render_template('friends.html', name=flask_login.current_user.id, message='You two are offically friends!',Users =users,Friends = Friends)
@app.route('/creatingAlbum', methods=['GET','POST'])
@flask_login.login_required
def creatingAlbum():
    if request.method == 'POST':
        AlbumName = request.form.get("album_name")
        uid = getUserIdFromEmail(flask_login.current_user.id)

        cursor = conn.cursor()
        cursor.execute("INSERT INTO Albums (name, user_id,CreatingDate) VALUES ('{0}', '{1}','{2}' )".format(AlbumName,uid,current_date))
        conn.commit()
        return render_template('profile.html', name=flask_login.current_user.id, message="Here's your profile")
    else:
        return render_template('createAlbum.html', name=flask_login.current_user.id, message='creating new album')

@app.route('/photos/Like', methods=['GET'])
@flask_login.login_required
def likePhoto():
    photo_id = request.args['info']
    cursor = conn.cursor()
    cursor.execute ("""
   UPDATE Pictures
   SET NumberOfLike = NumberOfLike +1
   WHERE picture_id =%s
""", (photo_id))
    conn.commit()

    uid = getUserIdFromEmail(flask_login.current_user.id)
    photos = getUsersPhotos(uid)
    return render_template('profile.html', name=flask_login.current_user.id, message="Here's your profile",photos = photos)

@app.route('/photos/tagPhoto', methods=['GET'])
@flask_login.login_required
def tagPhoto():
    photo_id = request.args['info']
    return render_template('taggingPhoto.html', name=flask_login.current_user.id, message="Please tag this photo",photo_id=photo_id)

@app.route('/photos/tagPhoto', methods=['POST'])
@flask_login.login_required
def taggingPhoto():
    photo_id = request.form.get('photo_id')
    tag_txt = request.form.get('tag')
    #insert these two into tag table
    TagPhotoWithPhotoId(photo_id,tag_txt)
    uid = getUserIdFromEmail(flask_login.current_user.id)
    photos = getUsersPhotos(uid)
    return render_template('profile.html', name=flask_login.current_user.id, message="Here's your profile",photos = photos)

@app.route('/photos/commentPhoto', methods=['GET'])
@flask_login.login_required
def commentPhoto():
    photo_id = request.args['info']
    return render_template('commentingPhoto.html', name=flask_login.current_user.id, message="Please tag this photo",photo_id=photo_id)

@app.route('/photos/commentPhoto', methods=['POST'])
@flask_login.login_required
def commentingPhoto():
    photo_id = request.form.get('photo_id')
    tag_txt = request.form.get('comment')
    #insert these two into tag table
    CommentPhotoWithPhotoId(photo_id,tag_txt)
    uid = getUserIdFromEmail(flask_login.current_user.id)
    photos = getUsersPhotos(uid)
    return render_template('profile.html', name=flask_login.current_user.id, message="Here's your profile",photos = photos)


#helpper function:
def getUsersFromFirstNmae(firstName):
    cursor = conn.cursor()
    cursor.execute("SELECT user_id,firstName,lastName  FROM Users WHERE firstName = '{0}'".format(firstName))
    return cursor.fetchall()

def getUserInformationlist():
    cursor = conn.cursor()
    cursor.execute("SELECT user_id,firstName,lastName  FROM Users")
    return cursor.fetchall()

def getFriendList(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT Users.user_id,Users.firstName,Users.lastName  FROM Users,friends WHERE friends.user_id = {0} And Users.user_id = friends.friend_id".format(uid))
    return cursor.fetchall()

def getAlbumList(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT name, creatingDate from Albums WHERE user_id = '{0}'".format(uid))
    return cursor.fetchall()

def getUsersPhotos(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, picture_id, Album_Name,NumberOfLike FROM Pictures WHERE user_id = '{0}'".format(uid))
    return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def TagPhotoWithPhotoId(photo_id,tag_txt):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tags (picture_id,tag_txt) VALUES ('{0}', '{1}')".format(photo_id,tag_txt))
    conn.commit()

def CommentPhotoWithPhotoId(photo_id,comment_txt):
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO comments (picture_id,user_id,comment_txt) VALUES ('{0}', '{1}','{2}')".format(photo_id,uid,comment_txt))
    conn.commit()


#default page  
@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html', message='Welecome to Photoshare')


if __name__ == "__main__":
    #this is invoked when in the shell  you run 
    #$ python app.py 
    app.run(port=5000, debug=True)
