import ConfigParser
import re
import requests
from datetime import datetime, timedelta
import time
from threading import Thread
import json
import codecs
from apscheduler.scheduler import Scheduler

class Slack:
	def __init__(self):
		config = ConfigParser.RawConfigParser()
		config.read("modules/slack/slack.cfg")
		self.slack_token = config.get('Setup','slacktoken')
		self.keyword = config.get('Setup','keyword')

	def archive(self):

		getparams = {"token": "xoxp-2315794369-2421792110-2468567197-93f2c6","channel": "G02BLVCKM", "username": "banana", "text": "```Starting to update Slack archives```" }
		req = requests.post('https://slack.com/api/chat.postMessage',params=getparams, verify=False)


		getparams = {'token': self.slack_token}
		req = requests.get('http://slack.com/api/users.list', params=getparams, verify=False)
		memberlist = json.loads(req.content)

		members = {}

		for member in memberlist['members']:
			members[member['id']] = member['name']



		getparams = {'token': self.slack_token}
		req = requests.get('https://slack.com/api/channels.list', params=getparams, verify=False)
		channellist = json.loads(req.content)

		path = "archive/"

		for channel in channellist['channels']:
			channelid = channel['id']
			channelname = channel['name']

			temp = []

			oldest = 0
			f = ''

			try: 
				with open(path + channelname + '-ch.log','r') as f:
					data = f.readlines()


					checker = len(data) - 1

					while checker>=0:
						oldest = data[checker]
						regex = '^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][.][0-9][0-9][0-9][0-9][0-9][0-9]'
						ts_check = re.match(regex,oldest)
						if ts_check:
							oldest = data[checker][0:17]
							break
						checker = checker - 1
				
			except IOError:
				oldest = 0
				with open(path + channelname + '-ch.log','w') as f:
					f.write(channelid + ' ' + channelname + '\n')


			getparams = {'token': self.slack_token,'channel':channelid, 'oldest':oldest, 'count':1000}
			req = requests.get('https://slack.com/api/channels.history', params=getparams, verify=False)
			channelhistory = json.loads(req.content)

			for message in channelhistory['messages']:
				f = codecs.open(path + channelname + '-ch.log','a','utf8')
					#Append timestamp - date(mm-dd-yyyy) - sender - message

				if 'subtype' in message:
					continue

				instance = {'timestamp':message['ts'],'date':datetime.fromtimestamp(float(message['ts'])).strftime('%Y-%m-%d %H:%M:%S'),'user':members[message['user']],'text':message['text']}

				temp.append(instance)

				#f.write(message['ts'] + '   ' + datetime.fromtimestamp(float(message['ts'])).strftime('%Y-%m-%d %H:%M:%S') + '   ' + members[message['user']] + '  :  ' + message['text'] + '\n')
				#print message['text'].encode('utf8')

			temp2 = []

			checker = len(temp) - 1

			while checker>=0:
				temp2.append(temp[checker])
				checker = checker - 1

			for item in temp2:
				f.write(item['timestamp'] + '   ' + item['date'] + '   ' + item['user'] + '  :  ' + item['text'] + '\n')

			f.close()


		getparams = {'token': self.slack_token}
		req = requests.get('https://slack.com/api/groups.list', params=getparams, verify=False)
		grouplist = json.loads(req.content)

		for group in grouplist['groups']:
			groupid = group['id']
			groupname = group['name']

			temp = []

			oldest = 0
			f = ''

			try: 
				with open(path + groupname + '-pg.log','r') as f:
					data = f.readlines()

					checker = len(data) - 1

					while checker>=0:
						oldest = data[checker]
						regex = '^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][.][0-9][0-9][0-9][0-9][0-9][0-9]'
						ts_check = re.match(regex,oldest)
						if ts_check:
							oldest = data[checker][0:17]
							break
						checker = checker - 1
				
			except IOError:
				oldest = 0
				with open(path + groupname + '-pg.log','w') as f:
					f.write(groupid + ' ' + groupname + '\n')


			getparams = {'token': self.slack_token,'channel':groupid, 'oldest':oldest, 'count':1000}
			req = requests.get('https://slack.com/api/groups.history', params=getparams, verify=False)
			grouphistory = json.loads(req.content)

			for message in grouphistory['messages']:
				f = codecs.open(path + groupname + '-pg.log','a','utf8')
					#Append timestamp - date(mm-dd-yyyy) - sender - message

				if 'subtype' in message:
						continue

				instance = {'timestamp':message['ts'],'date':datetime.fromtimestamp(float(message['ts'])).strftime('%Y-%m-%d %H:%M:%S'),'user':members[message['user']],'text':message['text']}

				temp.append(instance)		

				#f.write(message['ts'] + '   ' + datetime.fromtimestamp(float(message['ts'])).strftime('%Y-%m-%d %H:%M:%S') + '   ' + members[message['user']] + '  :  ' + message['text'] + '\n')
				#print message['text'].encode('utf8')

			temp2 = []

			checker = len(temp) - 1

			while checker>=0:
				temp2.append(temp[checker])
				checker = checker - 1

			for item in temp2:
				f.write(item['timestamp'] + '   ' + item['date'] + '   ' + item['user'] + '  :  ' + item['text'] + '\n')

			f.close()

			getparams = {"token": "xoxp-2315794369-2421792110-2468567197-93f2c6","channel": "G02BLVCKM", "username": "banana", "text": "```Slack updated!```" }
	        req = requests.post('https://slack.com/api/chat.postMessage',params=getparams, verify=False)

	        return True


	def run(self,input,sender,channel):
		regex = '(.*)\s%s\s+(\S*)' % self.keyword
		method_checker = re.match(regex,input)
		response = 'default'
		if(method_checker.group(2) == 'archive'):
			""" banana:: slack archive"""
			self.archive()
			response = 'Slack Archived!'

		elif(method_checker.group(2) == 'cron'):
			""" banana:: slack cron """
			
			sched = Scheduler()
			
			sched.add_cron_job(self.archive,hour=1,minute=0)

			sched.start()

			response = 'Started cron'

		elif(method_checker.group(2) == 'getArchive'):
			""" banana:: slack getArchive """
			getparams = {'token': self.slack_token}
			req = requests.get('https://slack.com/api/channels.list', params=getparams, verify=False)
			channellist = json.loads(req.content)

			path = "archive/"
			response = ''
			f = ''

			for channelobj in channellist['channels']:
				channelid = channelobj['id']

				if channelid == channel:
					channelname = channelobj['name']

					try: 
						with open(path + channelname + '-ch.log','r') as f:
							data = f.readlines()

							for dataitem in data:
								response = response + dataitem + '\n'

					except IOError:
						response = 'Not yet archived.'
						return response

					postparams = {"content":response}
					getparams = {"token":self.slack_token,"channels":channel, "filetype":"txt", "title":channelname + ' logs'}
					req = requests.post('https://slack.com/api/files.upload',params=getparams,data=postparams, verify=False)
						
					response = 'Returning archives'

			getparams = {'token': self.slack_token}
			req = requests.get('https://slack.com/api/groups.list', params=getparams, verify=False)
			grouplist = json.loads(req.content)

			for group in grouplist['groups']:
				groupid = group['id']
				
				if groupid == channel:
					channelname = group['name']

					try: 
						with open(path + channelname + '-pg.log','r') as f:
							data = f.readlines()

							for dataitem in data:
								response = response + dataitem + '\n'

					except IOError:
						response = 'Not yet archived.'
						return response

					postparams = {"content":response}
					getparams = {"token":self.slack_token,"channels":channel, "filetype":"txt", "title":channelname + ' logs'}
					req = requests.post('https://slack.com/api/files.upload',params=getparams,data=postparams, verify=False)
						
					response = 'Returning archives'

		return response
