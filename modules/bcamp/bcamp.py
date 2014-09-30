import elementtree.ElementTree as ET
from basecamp import Basecamp
import ConfigParser
import re
from datetime import datetime, timedelta
import time
from threading import Thread
import requests
import json
import redis
from apscheduler.scheduler import Scheduler

from HTMLParser import HTMLParser
class MessageParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.output = ''

	def handle_endtag(self, tag):
		if tag == 'br':
			self.output = self.output + '\n\n'

	def handle_data(self, data):
		self.output = self.output + ' ' + data


class Bcamp:
	def __init__(self):
		config = ConfigParser.RawConfigParser()
		config.read("modules/bcamp/bcamp.cfg")
		self.api_token = config.get('Setup','apitoken')
		self.slack_token = config.get('Setup','slacktoken')
		self.keyword = config.get('Setup','keyword')

	def cacheData(self):

		getparams = {"token": "xoxp-2315794369-2421792110-2468567197-93f2c6","channel": "G02BLVCKM", "username": "banana", "text": "```Starting to update Basecamp archives```" }
		req = requests.post('https://slack.com/api/chat.postMessage',params=getparams, verify=False)

		r = redis.StrictRedis(host='localhost',port=6379,db=0)
		bc = Basecamp('https://seertechnologies.basecamphq.com', self.api_token)
		i = 1
		userlist = {}

		xml = bc.people().text
		items = ET.fromstring(xml).findall('person')
		for item in items:
			#all users in seer
			r.hset('Users:' + item.find('email-address').text, 'name',item.find('first-name').text + " " + item.find('last-name').text)
			r.hset('Users:' + item.find('email-address').text, 'id',item.find('id').text)
			r.hset('Users:' + item.find('email-address').text, 'email',item.find('email-address').text)

			r.zadd('Users', 1,item.find('id').text)

			r.hset('Users:' + item.find('id').text, 'latestLog', "1970-01-01")
			r.hset('Users:' + item.find('id').text, 'email',item.find('email-address').text)
			

		xml = bc.projects().text
		items = ET.fromstring(xml).findall('project')
		for item in items:
			#all projects under seer
			projectname = item.find('name').text
			projectid = item.find('id').text

			r.hset('Projects:' + projectname,"name",projectname)
			r.hset('Projects:' + projectname,"id",projectid)

			r.zadd('Projects',1,projectname)

			x = 1
			while 1:
				#every time log in a project
				time_entries_data = bc.time_entries_per_project(project_id = int(projectid), page = x)

				if x > int(time_entries_data.headers['X-Pages']):
					break

				time_entries = time_entries_data.text

				items2 = ET.fromstring(time_entries).findall('time-entry')
				count = 0
				for item2 in items2:

					timeentryid = item2.find('id').text
					todoitemid = item2.find('todo-item-id').text

					count = count + 1
					r.hset('Time_entry:' + timeentryid,'date',item2.find('date').text)
					r.hset('Time_entry:' + timeentryid,'description', item2.find('description').text)
					r.hset('Time_entry:' + timeentryid,'hours',item2.find('hours').text)
					r.hset('Time_entry:' + timeentryid,'id',item2.find('id').text)
					r.hset('Time_entry:' + timeentryid,'person-id',item2.find('person-id').text)
					r.hset('Time_entry:' + timeentryid,'project-id',item2.find('project-id').text)
					r.hset('Time_entry:' + timeentryid,'todo-item-id',item2.find('todo-item-id').text)

					r.zadd('Time_entry:' + projectid, int(item2.find('person-id').text),timeentryid)

					logDate = datetime(int(item2.find('date').text[0:4]), int(item2.find('date').text[5:7]), int(item2.find('date').text[8:10]))
					dateToday = datetime.now()
					
					if dateToday.month==logDate.month and dateToday.year==logDate.year and dateToday.day-1==logDate.day:
						totalLogs = float(r.hget('Users:' + item2.find('person-id').text, 'totalLogsForTheWeek'))
						totalLogs = totalLogs + float(item2.find('hours').text)
						r.hset('Users:' + item2.find('person-id').text, 'totalLogsForTheWeek', totalLogs)
						r.hset('Users:' + item2.find('person-id').text, 'latestLog', item2.find('date').text)

					i = i + 1

				if count != 50:
					break

				x = x + 1

			todosearch = bc.todo_lists_per_project(project_id = int(projectid), filter = 'all').text
			todo_lists = ET.fromstring(todosearch).findall('todo-list')
			for todo_list in todo_lists:
				#per todo list in a project
				listid = todo_list.find('id').text

				r.hset("Todo_list:" + listid,'id',listid)
				r.hset("Todo_list:" + listid,'name',todo_list.find('name').text)
				r.hset("Todo_list:" + listid,'project-id',todo_list.find('project-id').text)
				r.hset("Todo_list:" + listid,'completed',todo_list.find('completed').text)
				r.hset("Todo_list:" + listid,'completed-count',todo_list.find('completed-count').text)
				r.hset("Todo_list:" + listid,'uncompleted-count',todo_list.find('uncompleted-count').text)
				r.hset("Todo_list:" + listid,'position',todo_list.find('position').text)

				r.zadd('Todo_list:' + projectid, 1, listid)

				todoitemsearch = bc.items(list_id = int(listid)).text
				todo_items = ET.fromstring(todoitemsearch).findall('todo-item')
				for todo_item in todo_items:
					#per todo item in a todo list
					itemid = todo_item.find('id').text

					r.hset("Todo_item:" + itemid,'id',itemid)
					r.hset("Todo_item:" + itemid,'content',todo_item.find('content').text)
					r.hset("Todo_item:" + itemid,'todo-list-id',todo_item.find('todo-list-id').text)

					r.zadd('Todo_item:' + listid, 1, itemid)

			messagesearch = bc.messages_per_project(project_id = int(projectid)).text
			messages = ET.fromstring(messagesearch).findall('post')
			for message in messages:
				#per message in a project
				postid = message.find('id').text

				r.hset("Message:" + postid,'id',postid)

				body = message.find('body').text

				#parser = MessageParser()
				#parser.feed(body)

				#parsed_message = parser.output
				parsed_message = body

				r.hset("Message:" + postid,'body',parsed_message)
				r.hset("Message:" + postid,'author-id',message.find('author-id').text)
				r.hset("Message:" + postid,'project-id',message.find('body').text)
				r.hset("Message:" + postid,'title',message.find('title').text)
				r.hset("Message:" + postid,'posted-on',message.find('posted-on').text)
				r.hset("Message:" + postid,'category-id',message.find('category-id').text)
				r.hset("Message:" + postid,'category-name',message.find('category-name').text)
				r.hset("Message:" + postid,'attachments-count',message.find('attachments-count').text)

				if int(message.find('attachments-count').text) > 0:
					attachments = message.findall('attachment')
					
					attachment_count = 1
					for attachment in attachments:
						r.hset("Attachment:" + postid + ":" + str(attachment_count),'id', attachment.find('id').text)
						r.hset("Attachment:" + postid + ":" + str(attachment_count),'download-url', attachment.find('download-url').text)
						r.hset("Attachment:" + postid + ":" + str(attachment_count),'project-id', attachment.find('project-id').text)
						r.hset("Attachment:" + postid + ":" + str(attachment_count),'person-id', attachment.find('person-id').text)
						r.hset("Attachment:" + postid + ":" + str(attachment_count),'name', attachment.find('name').text)
						attachment_count = attachment_count + 1

				r.zadd('Message:' + projectid, 1, postid)


			filesearch = bc.attachments(project_id = int(projectid)).text
			attachments = ET.fromstring(filesearch).findall('attachment')
			for attachment in attachments:
				#per attachment in a project
				attachmentid = attachment.find('id').text

				r.hset("Attachment:" + attachmentid,'id', attachment.find('id').text)
				r.hset("Attachment:" + attachmentid,'download-url', attachment.find('download-url').text)
				r.hset("Attachment:" + attachmentid,'project-id', attachment.find('project-id').text)
				r.hset("Attachment:" + attachmentid,'person-id', attachment.find('person-id').text)
				r.hset("Attachment:" + attachmentid,'name', attachment.find('name').text)


		for item in items:
			projectid = item.find('id').text

			projectpeople = bc.people_per_project(int(item.find('id').text)).text
			peoplesearch = ET.fromstring(projectpeople).findall('person')
			for person in peoplesearch:
				r.zadd("peopleperproject:" + projectid, int(person.find('id').text),person.find('email-address').text)

		getparams = {'token': self.slack_token,'pretty':'1'}
		req = requests.get('https://slack.com/api/users.list', params=getparams, verify=False)
		userlist = json.loads(req.content)
		for user in userlist['members']:
			r.hset('Slack:Users:' + user['profile']['email'], 'id', user['id'])


		getparams = {"token": "xoxp-2315794369-2421792110-2468567197-93f2c6","channel": "G02BLVCKM", "username": "banana", "text": "```Basecamp updated!```" }
		req = requests.post('https://slack.com/api/chat.postMessage',params=getparams, verify=False)


	def run(self,input,sender,channel):
		regex = '(.*)\s%s\s+(\S*)' % self.keyword
		method_checker = re.match(regex,input)
		response = 'default'
		if(method_checker.group(2) == 'update'):
			""" banana: basecamp update"""
			self.cacheData()
			response = 'Updated!'

		elif(method_checker.group(2) == 'Cron'):
			""" banana: basecamp Cron"""
			
			sched = Scheduler()
			
			sched.add_cron_job(self.cacheData,hour=2,minute=0)

			sched.start()

			response = 'Started cron'

		elif(method_checker.group(2) == 'log'):

			response = 'Logging turned off'
			return response

			""" banana:: basecamp log <email> <"project name"> <hours> <"desc">"""
			regex = '(.*)\s%s\s+log\s+(.*)\s+["|\'](.*)["|\']\s+([0-9]*[0-9]?\.?[0-9]+)\s+["|\'](.*)["|\']((\s+)([0-9][0-9][0-9][0-9][-][0-9][0-9][-][0-9][0-9]))?' % self.keyword
			parser = re.match(regex,input)
			if parser:
				projectid = ''
				projectname = parser.group(3)

				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				project = r.hgetall("Projects:" + projectname)
				if project == None or project == [] or project == {}:
					response = 'Project not found'
					return response
				
				projectid = int(project['id'])

				hour = parser.group(4)
				desc = parser.group(5)
				date = ''
				inputdate = parser.group(6)
				if inputdate == "" or inputdate is None:
					date = int(time.strftime("%Y%m%d"))

				else:
					date = int(inputdate[1:5] + inputdate[6:8] + inputdate[9:11])

				user_email = parser.group(2)
				userid = ''

				bc = Basecamp('https://seertechnologies.basecamphq.com', self.api_token)
				xml = bc.people().text
				items = ET.fromstring(xml).findall('person')
				for item in items:
					if item.find('email-address').text == user_email:
						userid = item.find('id').text
						break
				
				if userid == '':
					response = 'Email not recognized!'
					return response

				projectpeople = bc.people_per_project(projectid).text
				peoplesearch = ET.fromstring(projectpeople).findall('person')
				for person in peoplesearch:
					if person.find('id').text == userid:
						bc.create_time_entry(desc,float(hour),int(userid),date,int(projectid),None).text
						response = 'Logged successfully!'

						totalLogs = float(r.hget('Users:' + userid, 'BananaLogsForTheWeek'))
						totalLogs = totalLogs + float(hour)
						r.hset('Users:' + userid, 'BananaLogsForTheWeek', totalLogs)

						bananaUsage = r.hget('Users:' + userid, 'BananaUsageForTheWeek')
						dateToday = datetime.now().weekday()
						if dateToday == len(bananaUsage):
							bananaUsage = bananaUsage + 'B'
							r.hset('Users:' + userid, 'BananaUsageForTheWeek',bananaUsage)

						return response

				response = 'You do not belong to that project.'
				return response


			""" banana:: basecamp log <"project name"> <hours> <"desc">"""
			regex = '(.*)\s%s\s+log\s+["|\'](.*)["|\']\s+([0-9]*[0-9]?\.?[0-9]+)\s+["|\'](.*)["|\']((\s+)([0-9][0-9][0-9][0-9][-][0-9][0-9][-][0-9][0-9]))?' % self.keyword
			parser = re.match(regex,input)
			
			if parser:
				projectid = ''
				projectname = parser.group(2)

				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				project = r.hgetall("Projects:" + projectname)
				if project == None or project == [] or project == {}:
					response = 'Project not found'
					return response
				
				projectid = project['id']

				hour = parser.group(3)
				desc = parser.group(4)

				date = ''
				inputdate = parser.group(5)
				if inputdate == "" or inputdate is None:
					date = int(time.strftime("%Y%m%d"))

				else:
					date = int(inputdate[1:5] + inputdate[6:8] + inputdate[9:11])


				getparams = {'token': self.slack_token,'pretty':'1'}
				req = requests.get('https://slack.com/api/users.list', params=getparams, verify=False)
				userlist = json.loads(req.content)
				user_email = ''
				for user in userlist['members']:
					if user['id'] == sender:
						user_email = user['profile']['email']

				userid = r.hget('Users:' + user_email,'id')
				if userid == None or userid == '':
					response = 'Your email does not exist :<'
					return response

				checker = r.zrangebyscore("peopleperproject:" + projectid, userid, userid)
				if checker == None or checker == "" or checker == []:
					response = 'Your email is not recognized. Please try banana:: basecamp log <email> <"project name"> <hours> <"desc">'
					return response

				bc = Basecamp('https://seertechnologies.basecamphq.com', self.api_token)
				bc.create_time_entry(desc,float(hour),int(userid),date,int(projectid),None).text
				
				totalLogs = float(r.hget('Users:' + userid, 'BananaLogsForTheWeek'))
				totalLogs = totalLogs + float(hour)
				r.hset('Users:' + userid, 'BananaLogsForTheWeek', totalLogs)

				bananaUsage = r.hget('Users:' + userid, 'BananaUsageForTheWeek')
				dateToday = datetime.now().weekday()
				if dateToday == len(bananaUsage):
					bananaUsage = bananaUsage + 'B'
					r.hset('Users:' + userid, 'BananaUsageForTheWeek',bananaUsage)

				response = 'successfully logged!'
				return response

			else:
				response = 'Wrong set of parameters. Must be banana:: basecamp log <"project name"> <hours> <"description">'

		elif method_checker.group(2) == "getProjects":
			""" banana:: basecamp getProjects <email>"""
			regex = '(.*)\s%s\s+getProjects\s+(.*)' % self.keyword
			parser = re.match(regex,input)
			if parser:

				email = parser.group(2)
				projectlist = []



				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				user = r.hgetall('Users:' + email)

				if user == None or user == "" or user == {}:
					response = 'Email not found!'
					return response

				userid = user['id']

				projects = r.zrange('Projects',0,-1)
				for project in projects:
					projectid = r.hget("Projects:" + project,'id')
					projectname = r.hget("Projects:" + project,'name')
					checker = r.zrangebyscore("peopleperproject:" + projectid, userid, userid)
					if checker != None and checker != "" and checker != []:
						projectlist.append(projectname)

				response = "Projects of %s: \n\n" % email
				for project in projectlist:
					response = response + project + "\n"

			else:
				response = 'Wrong set of parameters. Must be banana:: basecamp getProjects <email>'

		elif method_checker.group(2) == "getLogs":
			""" banana:: basecamp getLogs <project name in quotation marks> <email> <yyyy-mm-dd> <yyyy-mm-dd>"""
			regex = '(.*)\s%s\s+getLogs\s+["|\'](.*)["|\']\s+(.*)\s+([0-9][0-9][0-9][0-9][-][0-9][0-9][-][0-9][0-9])\s+([0-9][0-9][0-9][0-9][-][0-9][0-9][-][0-9][0-9])' % self.keyword
			parser = re.match(regex,input)
			if parser:
				
				projectid = ''
				userid = ''
				projectname = parser.group(2)
				email = parser.group(3)
				date1 = parser.group(4)
				date1 = datetime(int(date1[0:4]), int(date1[5:7]), int(date1[8:10]))
				date2 = parser.group(5)
				date2 = datetime(int(date2[0:4]), int(date2[5:7]), int(date2[8:10]))
				user_time_entry = []



				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				userid = r.hget('Users:' + email,'id')

				if userid == None or userid == "":
					response = 'Email not found!'
					return response

				pname = r.hget('Projects:' + projectname,'name')
				if pname == "" or pname == None:
					response = 'Project not found'
					return response

				projectid = r.hget('Projects:' + projectname,'id')

				userposts = r.zrangebyscore('Time_entry:' + projectid,userid,userid)
				if userposts != None and userposts != "" and userposts != []:

					for userpost in userposts:
						timedetails = r.hgetall("Time_entry:" + str(userpost))
						entrydate = timedetails['date']
						entrydate = datetime(int(entrydate[0:4]), int(entrydate[5:7]), int(entrydate[8:10]))
						if entrydate >= date1 and entrydate <= date2:
							time_instance = []
							time_instance.append(timedetails['date'])
							time_instance.append(timedetails['hours'])
							time_instance.append(timedetails['description'])
							user_time_entry.append(time_instance)

				response = "Logs of %s: \n\n" % email
				for entry in user_time_entry:
					response = response + entry[0] + "   " + entry[1] + "   " + entry[2] + "\n"

			else:
				response = 'Wrong set of parameters. Must be banana:: basecamp getLogs <"project name"> <email> <yyyy-mm-dd> <yyyy-mm-dd>'


		elif method_checker.group(2) == "getDistribution":
			""" banana:: basecamp getDistribution <email>"""
			regex = '(.*)\s%s\s+getDistribution\s+(.*)' % self.keyword
			parser = re.match(regex,input)
			if parser:
				userid = ''
				email = parser.group(2)
				"""distribution = [{'name':'example','hours':'69', 'percent':100}]"""
				distribution = []
				projectlist = []

				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				userid = r.hget('Users:' + email,'id')

				if userid == None or userid == "":
					response = 'Email not found!'
					return response

				projects = r.zrange('Projects',0,-1)

				for project in projects:
					projectid = r.hget('Projects:' + project,'id')
					projectname = r.hget('Projects:' + project,'name')

					userposts = r.zrangebyscore("Time_entry:" + projectid,userid,userid)
					if userposts != None and userposts != "" and userposts != []:

						instance = {'name':projectname,'hours':0,'percent':100}

						for userpost in userposts:
							timedetails = r.hgetall("Time_entry:" + userpost)
							instance['hours'] = instance['hours'] + float(timedetails['hours'])

						distribution.append(instance)



				response = "Logs of %s: \n\n" % email
				total_hours = 0
				for entry in distribution:
					total_hours = total_hours + entry['hours']

				for entry in distribution:
					entry['percent'] = round((float(entry['hours'])/float(total_hours)) * 100,2)

				for entry in distribution:
					response = response + entry['name'] + "   " + str(entry['percent']) + "\n"

			else:
				response = 'Wrong set of parameters. Must be banana:: basecamp getDistribution <email>'

		elif method_checker.group(2) == "get-logs":
			""" banana: basecamp get-logs <"Project Name">"""
			regex = '(.*)\s%s\s+get[-]logs\s+["|\'](.*)["|\']' % self.keyword
			parser = re.match(regex,input)

			response = ''

			if parser:
				projectname = parser.group(2)

				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				project = r.hgetall("Projects:" + projectname)
				if project == None or project == [] or project == {}:
					response = 'Project not found'
					return response

				projectid = project['id']

				people = r.zrange('peopleperproject:' + projectid, 0, -1)

				for user in people:
					userdata = r.hgetall('Users:' + user)
					response = response + userdata['name'] + '\n'

					time_entries = r.zrangebyscore("Time_entry:" + projectid, userdata['id'], userdata['id'])
					

					csvcontent = ''

					for time_entry in time_entries:
						time_entry_data = r.hgetall("Time_entry:" + time_entry)
						#response = response + '    ' + time_entry_data['description'] + '\n'

						csvcontent = csvcontent + time_entry_data['description'] + ',' + time_entry_data['hours'] + ',' + time_entry_data['date'] + ','

						#TO ADD LATER: Put these into seperate csv files

					postparams = {"content":csvcontent}
					getparams = {"token":self.slack_token,"channels":"C02BW6E2L", "filetype":"csv", "title":userdata['name'] + ' logs'}
					req = requests.post('https://slack.com/api/files.upload',params=getparams,data=postparams)

				response = 'Logs successfully saved in csv files!'


		elif method_checker.group(2) == 'getTodoLists':
			""" banana: basecamp getTodoLists <"Project Name">"""
			regex = '(.*)\s%s\s+getTodoLists\s+["|\'](.*)["|\']' % self.keyword
			parser = re.match(regex,input)

			response = ''

			if parser:
				projectname = parser.group(2)

				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				project = r.hgetall("Projects:" + projectname)
				if project == None or project == [] or project == {}:
					response = 'Project not found'
					return response
					
				projectid = project['id']

				todolists = r.zrange("Todo_list:" + projectid,0,-1)
				for todolist in todolists:
					todolistdata = r.hgetall("Todo_list:" + todolist)
					response = response + todolistdata['name']

					todolistid = todolistdata['id']

					response = response + "\n"

		elif method_checker.group(2) == 'getMessages':
			""" banana: basecamp getMessages <"Project Name">"""
			regex = '(.*)\s%s\s+getMessages\s+["|\'](.*)["|\']' % self.keyword
			parser = re.match(regex,input)

			response = ''

			if parser:
				projectname = parser.group(2)

				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				project = r.hgetall("Projects:" + projectname)
				if project == None or project == [] or project == {}:
					response = 'Project not found'
					return response
					
				projectid = project['id']

				messages = r.zrange("Message:" + projectid,0,-1)
				for message in messages:
					messagedata = r.hgetall("Message:" + message)

					parser = MessageParser()
					parser.feed(messagedata['body'])

					response = response + parser.output + '\n'
					response = response + "\n"

					parser.close()

		elif method_checker.group(2) == 'addTodoList':
			""" banana: basecamp addTodoList <"Project Name"> <"Todo List Name">"""
			regex = '(.*)\s%s\s+addTodoList\s+["|\'](.*)["|\']\s+["|\'](.*)["|\']' % self.keyword
			parser = re.match(regex,input)

			response = ''

			if parser:
				projectname = parser.group(2)
				todolistname = parser.group(3)

				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				project = r.hgetall("Projects:" + projectname)
				if project == None or project == [] or project == {}:
					response = 'Project not found'
					return response
					
				projectid = project['id']

				bc = Basecamp('https://seertechnologies.basecamphq.com', self.api_token)
				bc.create_todo_list(project_id=int(projectid),name=todolistname)

				response = 'Todo List created successfully'

		elif method_checker.group(2) == "getDistributionLastMonth":
			""" banana:: basecamp getDistributionLastMonth <email>"""
			regex = '(.*)\s%s\s+getDistributionLastMonth\s+(.*)' % self.keyword
			parser = re.match(regex,input)
			if parser:
				userid = ''
				email = parser.group(2)
				"""distribution = [{'name':'example','hours':'69', 'percent':100}]"""
				distribution = []
				projectlist = []

				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				userid = r.hget('Users:' + email,'id')

				if userid == None or userid == "":
					response = 'Email not found!'
					return response

				projects = r.zrange('Projects',0,-1)

				for project in projects:
					projectid = r.hget('Projects:' + project,'id')
					projectname = r.hget('Projects:' + project,'name')

					userposts = r.zrangebyscore("Time_entry:" + projectid,userid,userid)
					if userposts != None and userposts != "" and userposts != []:

						instance = {'name':projectname,'hours':0,'percent':100}

						for userpost in userposts:
							timedetails = r.hgetall("Time_entry:" + userpost)

							entrydate = timedetails['date']
							entrydate = datetime(int(entrydate[0:4]), int(entrydate[5:7]), int(entrydate[8:10]))
							datetoday = datetime.now()

							if (entrydate.month+1 == datetoday.month and entrydate.year == datetoday.year) or (entrydate.month == 12 and datetoday.month == 1 and entrydate.year+1 == datetoday.year):
								instance['hours'] = instance['hours'] + float(timedetails['hours'])

						distribution.append(instance)



				response = "Logs of %s: \n\n" % email
				total_hours = 0
				for entry in distribution:
					total_hours = total_hours + entry['hours']

				for entry in distribution:
					entry['percent'] = round((float(entry['hours'])/float(total_hours)) * 100,2)

				for entry in distribution:
					response = response + entry['name'] + "   " + str(entry['percent']) + "\n"

			else:
				response = 'Wrong set of parameters. Must be banana:: basecamp getDistributionLastMonth <email>'

		elif method_checker.group(2) == "getStarbucks":
			""" banana:: basecamp getStarbucks"""
			regex = '(.*)\s%s\s+getStarbucks' % self.keyword
			parser = re.match(regex,input)
			if parser:

				response = 'People who logged at least 32 hours using banana last week: \n'
				r = redis.StrictRedis(host='localhost',port=6379,db=0)
				users = r.zrange('Users',0,-1)
				for user in users:
					totalLogs = r.hget('Users:' + user, 'totalLogsLastWeek')
					bananalogs = r.hget('Users:' + user, 'totalLogsLastWeek')
					bananaUsage = r.hget('Users:' + user, 'totalLogsLastWeek')

			else:
				response = 'Wrong set of parameters. Must be banana:: basecamp getProjects <email>'

		else:
			response = 'Module not found!'

		return response

	def Cron(self):
		r = redis.StrictRedis(host='localhost',port=6379,db=0)

		t = datetime.now()
		if t.hour >= 2:
			t = t + timedelta(days = 1)
		
		target = datetime(t.year,t.month,t.day,2,0)
		t = datetime.now()

		while 1:

			t += timedelta(minutes=1)

			while datetime.now() > target:
				time.sleep((t - datetime.now()).seconds)


			if datetime.now() > target:
				target += timedelta(days=1)


				getparams = {"token": "xoxp-2315794369-2421792110-2468567197-93f2c6","channel": "G02BLVCKM", "username": "banana", "text": "```Starting to update Basecamp archives```" }
				req = requests.post('https://slack.com/api/chat.postMessage',params=getparams, verify=False)

				self.cacheData()

				i = 1
				users = r.zrange('Users',0,-1)
				datecheck = datetime.now()

				'''if datecheck.weekday() <= 5 and datecheck.weekday() > 0:

					for user in users:
						latestLog = r.hget("Users:" + user,'latestLog')
						latestLog = datetime(int(latestLog[0:4]), int(latestLog[5:7]), int(latestLog[8:10]))
						dateDiff = abs((datecheck - latestLog).days)
						if dateDiff>1:
							email = r.hget("Users:" + user,'email')
							userid = r.hget("Slack:Users:" + email,'id')
							print userid
							if userid is not None:
								postparams = {"channel": userid, "username": "banana", "text": "Hi, it seems you do not logged your time for yesterday. Please log it ASAP." }
								getparams = {"token":"PBD7gPUVByYLziBPQ4XkrjvJ"}
								#req = requests.post('https://seertech.slack.com/services/hooks/incoming-webhook?token=PBD7gPUVByYLziBPQ4XkrjvJ',params=getparams,data=json.dumps(postparams))
								print email

				elif datecheck.weekday()==0:

					users = r.zrange('Users',0,-1)
					for user in users:

						r.hset('Users:' + user, 'totalLogsForTheWeek', "0")
						r.hset('Users:' + user, 'BananaLogsForTheWeek', "0")
						r.hset('Users:' + user, 'BananaUsageForTheWeek', "")

				elif datecheck.weekday()==6:

					users = r.zrange('Users',0,-1)
					for user in users:

						totalLogs = r.hget('Users:' + user, 'totalLogsForTheWeek')
						bananalogs = r.hget('Users:' + user, 'BananaLogsForTheWeek')
						bananausage = r.hget('Users:' + user, 'BananaUsageForTheWeek')

						r.hset('Users:' + user, 'totalLogsLastWeek', totalLogs)
						r.hset('Users:' + user, 'BananaLogsLastWeek', bananalogs)
						r.hset('Users:' + user, 'BananaUsageForLastWeek', bananausage)'''

				time.sleep(30)

				getparams = {"token": "xoxp-2315794369-2421792110-2468567197-93f2c6","channel": "G02BLVCKM", "username": "banana", "text": "```Basecamp updated!```" }
	        	req = requests.post('https://slack.com/api/chat.postMessage',params=getparams, verify=False)
