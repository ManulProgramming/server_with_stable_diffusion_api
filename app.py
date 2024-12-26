from flask import Flask, render_template, request, session, redirect
from flask_session import Session
import secrets
import sqlite3
import datetime
from argon2 import PasswordHasher, exceptions
from markupsafe import Markup
import uuid
import socket
import os
import json

#Needed for verifying users with their profiles, by checking if users fingerprints matches with encrypted ones in the database
ph = PasswordHasher()

#Change these values to those of your server which receives prompts and messages from users.
HOST = "IP_OF_YOUR_SERVER"
PORT = 65432

if HOST=="IP_OF_YOUR_SERVER":
    print(f"ERROR!\nPlease set the IP address and port of your server in this Python file (app.py).")
    exit(-1)

if not os.path.exists('database'):
    os.mkdir('database')
with sqlite3.connect("database/data.db") as conn:
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        user_req TEXT UNIQUE,
        color VARCHAR(50)
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS suggestions(
        sug_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        sug_text TEXT,
        width INTEGER,
        height INTEGER,
        is_allowed INTEGER,
        timee TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    cursor.execute('''select * from users''')
    data=cursor.fetchall()
    if not data:
        print("""ERROR! (raising an exception will mess up the message, so here is a regular error message)
Admin account is necessary as he is the primary moderator of all the messages/prompts that users send.
He is responsible for sending the prompt forward or declining it entirely.")
As for now, there can only be one Admin.
Please add him using a query that will be executed in the local database that was just created in /database folder:

INSERT INTO users VALUES(0,"HIS_IP_ADDRESS_USER_AGENT_AND_ACCCEPT_LANGUAGE_DIVIDED_BY_|","WHATEVER_COLOR_YOU_WANT");
    - First entry is responsible for his ID. I recommend you to use ID 0.
    - Second is the string containing user's IP address (WITH LAST 8 BITS BEING REPLACED BY A ZERO), user-agent and accept-language divided by the symbol '|' and is then ENCRYPTED using argon2 (THIS IS VERY IMPORTANT).
    - And the last one is the string stating the name of HTML color that you want an admin to have, for example "orange".

EXAMPLE QUERY:
INSERT INTO users VALUES(0,"$argon2id$v=19$m=65536,t=3,p=4$YWa4mvcU/Rqfs04nEADyRw$eCsX4gEyx9kGXurniBTXElYsInIGFXs+svEyrhXA8Qk","white");
Where in the second argument this value was encrypted using argon2:
'10.64.56.0|Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_9_8 rv:6.0; eu-ES) AppleWebKit/534.24.1 (KHTML, like Gecko) Version/4.0.1 Safari/534.24.1|en-US,en;q=1'

Warning! Declined prompts are still visible in the database, but this can be changed in the code itself for the sake of privacy.""")
        exit(-1)

#Establishing a connection with the remote server before the website has started, where it will accept messages from users.
socket_connection=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket_connection.settimeout(10) #How many seconds it will wait before timing out.
try:
    socket_connection.connect((HOST,PORT))
except:
    print(f"ERROR!\nNo connection could have been made with the remote server {HOST}:{PORT}. Is the remote server up?")
    exit(-1)

ADMIN_ID=0 #CHANGE THIS VALUE IF YOU SPECIFIED THAT THE ADMIN HAS A DIFFERENT ID IN THE DATABASE!
ADMIN_ID=data[0][0] #OR ALLOW THE SYSTEM TO DETECT IT AUTOMATICALLY


app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY_HERE'

#Just in case, but it is not used
app.config["SESSION_TYPE"] = "filesystem"
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024

Session(app)

html_color_names = {
    "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black",
    "blanchedalmond", "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse",
    "chocolate", "coral", "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue",
    "darkcyan", "darkgoldenrod", "darkgray", "darkgreen", "darkgrey", "darkkhaki", "darkmagenta",
    "darkolivegreen", "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen",
    "darkslateblue", "darkslategray", "darkslategrey", "darkturquoise", "darkviolet", "deeppink",
    "deepskyblue", "dimgray", "dimgrey", "dodgerblue", "firebrick", "floralwhite", "forestgreen",
    "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod", "gray", "green", "greenyellow",
    "grey", "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender", "lavenderblush",
    "lawngreen", "lemonchiffon", "lightblue", "lightcoral", "lightcyan", "lightgoldenrodyellow",
    "lightgray", "lightgreen", "lightgrey", "lightpink", "lightsalmon", "lightseagreen", "lightskyblue",
    "lightslategray", "lightslategrey", "lightsteelblue", "lightyellow", "lime", "limegreen", "linen",
    "magenta", "maroon", "mediumaquamarine", "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen",
    "mediumslateblue", "mediumspringgreen", "mediumturquoise", "mediumvioletred", "midnightblue", "mintcream",
    "mistyrose", "moccasin", "navajowhite", "navy", "oldlace", "olive", "olivedrab", "orange",
    "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise", "palevioletred",
    "papayawhip", "peachpuff", "peru", "pink", "plum", "powderblue", "purple", "rebeccapurple", "red",
    "rosybrown", "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell", "sienna",
    "silver", "skyblue", "slateblue", "slategray", "slategrey", "snow", "springgreen", "steelblue",
    "tan", "teal", "thistle", "tomato", "turquoise", "violet", "wheat", "white", "whitesmoke",
    "yellow", "yellowgreen"
} #A set of all html colors, that are used as profiles

@app.route('/allow',methods=['POST']) #POST webpage where the system will deny or allow certain messages posted by users. Only accessible by the admin.
def allow():
    #Verifying that it is really the admin trying to access this script.
    #WARNING! This method of authorization is insecure and unreliable, leading to multiple issues in the process!
    #DO NOT use it in the production environment!
    IP_address=str(request.remote_addr)
    #Trying to somehow add anonymization of the user's IP address, as it will be stored in the SQLite database.
    if ':' in IP_address:
        IP_address=':'.join(IP_address.split(':')[:4]) + "::"
    else:
        IP_address='.'.join(IP_address.split('.')[:3]) + ".0"
    user_agent=str(request.user_agent)
    accept_language=str(request.headers.get('Accept-Language'))
    initial_data=str(IP_address+'|'+user_agent+'|'+accept_language)
    with sqlite3.connect("database/data.db") as conn:
        cursor = conn.cursor()
        query='''select * from users where user_id=?'''
        cursor.execute(query,(ADMIN_ID,))
        data=cursor.fetchone()
    try:
        ph.verify(data[1],initial_data)
        user_input = request.form #user_input should only contain the suggestion ID and what to do with it (True - accept it, False - deny it)
        if user_input.get('dowe',None):
            splitted_user_input=user_input.get('dowe').split(',')
            with sqlite3.connect("database/data.db") as conn:
                cursor = conn.cursor()
                query='''SELECT * from suggestions WHERE sug_id=?'''
                cursor.execute(query,(splitted_user_input[0],))
                data=cursor.fetchone()
                if splitted_user_input[1]=="True": #If the message was approved by the Admin, then it is send to the remote server
                    query='''SELECT color FROM users WHERE user_id=?'''
                    cursor.execute(query,(data[1],))
                    data_color=cursor.fetchone()[0]
                    socket_connection.send(json.dumps({'time':data[6],'text':data[2],'width':data[3],'height':data[4],'color':data_color}).encode('utf-8'))
                    query='''UPDATE suggestions SET is_allowed=? WHERE sug_id=?'''
                    cursor.execute(query,(splitted_user_input[1],splitted_user_input[0]))
                    conn.commit()
                else: #If it was denied, then only the status of this message changes in the database (the user does not see the status of his messages, only the admin).
                    query='''UPDATE suggestions SET is_allowed=? WHERE sug_id=?'''
                    cursor.execute(query,(splitted_user_input[1],splitted_user_input[0]))
                    conn.commit()
        else: #If the admin sent a weird POST request, then his cookie files are cleaned, and he is redirected to the home page where he will see a special message.
            print(f"Someone has attempted to sent a bad POST request in /allow section. User's color: {str(session.get('temp_color',None))}") #Debug message
            session.pop('user_uuid',None)
            session.pop('temp_color',None)
    except exceptions.VerifyMismatchError: #If it was just a regular user, that tried to access this webpage, then once again, his cookie files are cleaned, and he is redirected to the home page where he will see a special message.
        print(f"Someone has attempted to sent a bad POST request in /allow section. User's color: {str(session.get('temp_color',None))}") #Debug message
        session.pop('user_uuid',None)
        session.pop('temp_color',None)
    return redirect('/')

@app.route('/submit', methods=['POST']) #POST webpage where a user is sending his prompt
def submit():
    user_input = request.form
    if user_input.get('input-box')!='' and user_input.get('input-box')!=None and len(user_input.get('input-box'))<2000: #Double check restrictions, in case user changed javascript's check
        with sqlite3.connect("database/data.db") as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT * FROM suggestions ORDER BY sug_id DESC LIMIT 1;''')
            data=cursor.fetchone()
            if data:
                prev_id=data[0]
            else:
                prev_id=-1
            now = datetime.datetime.now().strftime('%H:%M:%S')

            #WARNING! This method of authorization is insecure and unreliable, leading to multiple issues in the process!
            #DO NOT use it in the production environment!
            IP_address=str(request.remote_addr)
            #Trying to somehow add anonymization of the user's IP address, as it will be stored in the SQLite database.
            if ':' in IP_address:
                IP_address=':'.join(IP_address.split(':')[:4]) + "::"
            else:
                IP_address='.'.join(IP_address.split('.')[:3]) + ".0"
            user_agent=str(request.user_agent)
            accept_language=str(request.headers.get('Accept-Language'))
            initial_data=str(IP_address+'|'+user_agent+'|'+accept_language)

            current_user_id=None
            cursor.execute('''select * from users''')
            data=cursor.fetchall()
            for i in range(len(data)):
                try:
                    ph.verify(data[i][1],initial_data)
                    current_user_id=data[i][0]
                    break
                except:
                    continue
            query='''INSERT INTO suggestions VALUES (?,?,?,?,?,?,?);'''
            if current_user_id!=None:
                cursor.execute(query,(prev_id+1,current_user_id,user_input.get('input-box'),int(user_input.get('reswidth')),int(user_input.get('resheight')),'Pending',now))
                conn.commit()
            else: #If user SOMEHOW changed his user agent, IP address or accept-language while he tried to send the prompt, his request is denied and he is redirected to the initial home page where he will be registered as a new user
                print(f"User lost his fingerprints, and is now unrecognisable by the system. He will be registered as a new user. His previous color: {str(session.get('temp_color',None))}") #Debug message, to know what user has just lost his profile
                return redirect('/')
    return redirect('/')

@app.route('/')
def home():
    #This cookie file is needed for the individual session and is needed to display a "special message".
    #Special message - is a message that is displayed when the user somehow loses their cookie files (e.g. accessing the website using incognito mode).
    #The message lets the user know that the website still recognises him and makes a brief joke about it.
    previous_user=True
    if 'user_uuid' not in session:
        previous_user=False
        session['user_uuid']=uuid.uuid4()
        session['temp_color']=None #Only needed for debug

    #WARNING! This method of authorization is insecure and unreliable, leading to multiple issues in the process!
    #DO NOT use it in the production environment!
    IP_address=str(request.remote_addr)
    #Trying to somehow add anonymization of the user's IP address, as it will be stored in the SQLite database.
    if ':' in IP_address:
        IP_address=':'.join(IP_address.split(':')[:4]) + "::"
    else:
        IP_address='.'.join(IP_address.split('.')[:3]) + ".0"
    user_agent=str(request.user_agent)
    accept_language=str(request.headers.get('Accept-Language'))
    initial_data=str(IP_address+'|'+user_agent+'|'+accept_language)
    with sqlite3.connect("database/data.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''select * from users''')
        data=cursor.fetchall()
        found=False
        for i in range(len(data)):
            try:
                ph.verify(data[i][1],initial_data) #Check if the user was previously on the website (if he is in the database)
                found=True
                random_color=data[i][-1]
                session['temp_color']=random_color
                if data[i][0]==ADMIN_ID: #If it's an admin account, then get all the prompts and suggestions from user's
                    query='''select * from suggestions'''
                    cursor.execute(query)
                else: #This is for every other user. He gets only his prompts, and no others.
                    query='''select * from suggestions WHERE user_id=?'''
                    cursor.execute(query,(i,))
                messages=cursor.fetchall()
                allmessages=''
                for j,each_message in list(enumerate(messages))[::-1]:
                    #All user's messages in a beautiful html form. Markup.escape() is used to bypass HTML injections, which the user might send over.
                    allmessages+=f'''<div style="white-space: normal;overflow-wrap: break-word;width: 90%;max-width:1000px; border: 5px solid #1d1d1d; border-radius: 15px;">
                <b><p style="color: darkgray; text-align: center;">[{j+1}] {each_message[6]}</p></b>
                <p style="color: white; text-align: center">{Markup.escape(each_message[2])}</p>
                <p style="color: darkgray; text-align: center">Width: {each_message[3]}</p>
                <p style="color: darkgray; text-align: center">Heigth: {each_message[4]}</p>
                </div><br>'''
                    if data[i][0]==ADMIN_ID: #Selection panel with it's results, only given to the Admin account (ONCE AGAIN CHANGE VALUE IF HIS ID IS NOT 0).
                        if each_message[5]=="Pending":
                            allmessages+=f'''
                            <div style="width:90%;max-width:1200px;">
                            <form id="allowing-form" method="POST" action="/allow">
                            <div style="display: flex;">
                            <button class="button" style="color:white;background-color: darkgreen;" name="dowe" type="submit" value="{j},True">✓</button>
                            <p style="width:25%">&nbsp;</p>
                            <button class="button" style="color:white;background-color: darkred;" name="dowe" type="submit" value="{j},False">X</button>
                            </div>
                            </form>
                            </div>'''
                        elif each_message[5]=="False":
                            allmessages+=f'''
                            <div style="width:90%;max-width:1200px;">
                            <form id="allowing-form" method="POST" action="/allow">
                            <div style="display: flex;">
                            <button class="button" style="color:white;background-color: #003000;cursor: default;" name="dowe" disabled>✓</button>
                            <p style="width:25%">&nbsp;</p>
                            <button class="button" style="color:white;background-color: darkred;cursor: default;" name="dowe" disabled>X</button>
                            </div>
                            </form>
                            </div>'''
                        elif each_message[5]=="True":
                            allmessages+=f'''
                            <div style="width:90%;max-width:1200px;">
                            <form id="allowing-form" method="POST" action="/allow">
                            <div style="display: flex;">
                            <button class="button" style="color:white;background-color: darkgreen;cursor: default;" name="dowe" disabled>✓</button>
                            <p style="width:25%">&nbsp;</p>
                            <button class="button" style="color:white;background-color: #570000;cursor: default;" name="dowe" disabled>X</button>
                            </div>
                            </form>
                            </div>'''
                if not previous_user: #That is the special message I was talking about. Only triggers, when a user is registered in the database, but has lost his cookie file.
                    overlay=f'''<div class="overlay">
<div class="text initial-text">Are you lost?</div>
<div class="color-box-container">
    <div class="color-box"></div>
    <div class="color-name">{random_color.upper()}</div>
</div>
<div class="proceed-text">Please, do not test my nerves</div>
</div>'''
                    render_overlay='''document.addEventListener("DOMContentLoaded", () => {
const overlay = document.querySelector(".overlay");
const mainPage = document.querySelector(".main-page");
setTimeout(() => {
overlay.style.animation = "fadeOut 2s ease-in-out forwards";
setTimeout(() => {
overlay.style.display = "none";
mainPage.style.animation = "fadeIn 2s ease-in-out forwards";
}, 2000);
}, 10000);
});'''
                    return render_template('home.html',color=random_color,messages=allmessages,overlay=overlay,render_overlay=render_overlay,opacity=0,animation='animation: fadeIn 2s ease-in-out 10s forwards;')
                else: #This is a regular home page when the user was previously registered and has his cookie files in hand.
                    return render_template('home.html',color=random_color,messages=allmessages,overlay='',render_overlay='',opacity=100,animation='')
            except:
                continue
        if not found: #This is the case where the user is treated as the new one. He is then assigned a random color from the set of colors, excluding those colors which were previously assigned to different users.
            #So there is a strict limit of 148 users (including Admin) that may be registered and allowed in.
            cursor.execute('''select * from users''')
            data=cursor.fetchall()
            prev_id=data[-1][0]
            prev_colors={el[-1] for el in data}
            try:
                random_color=secrets.choice(list(html_color_names-prev_colors))
                session['temp_color']=random_color
                query='''INSERT INTO users VALUES (?,?,?);'''
                cursor.execute(query,(prev_id+1,ph.hash(initial_data),random_color))
                conn.commit()
                overlay=f'''<div class="overlay">
<div class="text initial-text">Your color is...</div>
<div class="color-box-container">
    <div class="color-box"></div>
    <div class="color-name">{random_color.upper()}</div>
</div>
<div class="proceed-text">Please, proceed forward</div>
</div>'''
                render_overlay='''document.addEventListener("DOMContentLoaded", () => {
const overlay = document.querySelector(".overlay");
const mainPage = document.querySelector(".main-page");
setTimeout(() => {
overlay.style.animation = "fadeOut 2s ease-in-out forwards";
setTimeout(() => {
overlay.style.display = "none";
mainPage.style.animation = "fadeIn 2s ease-in-out forwards";
}, 2000);
}, 10000);
});'''
                return render_template('home.html',color=random_color,messages='',overlay=overlay,render_overlay=render_overlay,opacity=0,animation='animation: fadeIn 2s ease-in-out 10s forwards;')
            except IndexError: #In case, the user limit is hit, a new special message is send to the user that is trying to visit the website after the user count has been larger than 148
                overlay=f'''<div class="overlay">
<div class="text initial-text">Unfortunately...</div>
<div class="color-box-container">
    <div class="color-name">USER</div>
</div>
<div class="proceed-text">We are not accepting anyone anymore.</div>
</div>'''
                return render_template('home.html',color='',messages='',overlay=overlay,render_overlay='',opacity=0,animation='')

    return redirect('/')


if __name__ == '__main__':
    #Just in case something goes completely wrong with the website, it will attempt to close the connection with the remote server.
    try:
        app.run('0.0.0.0',port=5000)
    except:
        socket_connection.close()
    try:
        socket_connection.close()
    except:
        None
