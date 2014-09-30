import ConfigParser
import requests
import re

class Feedback:
	def __init__(self):
		config = ConfigParser.RawConfigParser()
		config.read("modules/feedback/feedback.cfg")
		self.keyword = config.get('Setup','keyword')

	def run(self,input,sender,channel):
		regex = '(.*)\s%s\s+(\S*)' % self.keyword
		method_checker = re.match(regex,input)
		response = 'default'
		if(method_checker.group(2) == 'getFeedback'):
			""" banana:: feedback getFeedback"""
			try: 
				with open('feedback.txt','r') as f:
					data = f.readlines()
					response = ''
					for dataitem in data:
						response = response + dataitem + '\n'

					postparams = {"content":response}
					getparams = {"token":"xoxp-2315794369-2421792110-2468567197-93f2c6","channels":channel, "filetype":"txt", "title":'feedback'}
					req = requests.post('https://slack.com/api/files.upload',params=getparams,data=postparams, verify=False)

			except IOError:
				response = 'cannot read feedback.txt'
				return response

			return ''

		else:
			""" banana:: feedback <feedback>"""
			feedback = input
			try: 
				with open('feedback.txt','a') as f:
					f.write(sender + ' ' + channel + ' ' + feedback + '\n')
					response = 'Thank you for your feedback. :* :)'
			except IOError:
				response = 'cannot create/open feedback file.'

		return response
