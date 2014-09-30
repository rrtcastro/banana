from flask import Flask, request
import threading
import core
import redis
import cStringIO
import urllib
import re

#FLASK SLACK LISTENER
app = Flask(__name__)
@app.route("/listen/", methods=['POST'])
def slack():
    username = "banana"
    msguser = request.form.get("user_name","")
    if username == msguser or msguser.lower() == "slackbot":
        return ""


    command = ''
    slashcheck = request.form.get("text", "")
    slashcommand = request.form.get("command", "")
    if slashcheck[0] == '/':
        command = 'banana:: ' + slashcheck[8:]
    elif slashcommand == '/banana':
        command = 'banana:: ' + slashcheck
    else:
        command = slashcheck
        format = command.split(' ')
        command = ''
        for token in format:
            regex = '<(.*)\|(.*)>'
            parser = re.match(regex,token)
            if parser:
                command = command + parser.group(2) + ' '
            else:
                command = command + token + ' '

        commandlength = len(command)
        command = command[0:commandlength-1]


    slackid = request.form.get("user_id", "")
    channel = request.form.get("channel_id","")

    r.hset('command','message',command)
    r.hset('command','gateway','slack')
    r.hset('command','channel',channel)
    r.hset('command','sender',slackid)
    r.rpush('inQ','command')

    return ""

@app.route("/oauth2callback")
def oauth():
    print "GMAIL AUTH"
    return ""

@app.route("/ping", methods=['POST'])
def ping():
    print "PONG"
    msguser = request.form.get("text","")
    print msguser
    return ""
    
if __name__ == "__main__":
    r = redis.StrictRedis(host='localhost',port=6379,db=0)

    coreThread = core.core(r)
    listenThread = core.listen(r)
 
    coreThread.start()      
    listenThread.start()  

    app.run(debug=True, host = '0.0.0.0', port=5555)