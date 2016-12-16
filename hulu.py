#!/usr/bin/python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import codecs
import json
import re


class HuluSession:
    '''Class to manage Hulu sessions for scraping'''
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0'}

    def __init__(self, email, password):
        self.session.get('http://www.hulu.com/welcome')
        page = self.session.get('https://auth.hulu.com/login', headers=self.headers)
        soup = BeautifulSoup(page.text, 'lxml')

        csrf = soup.find('input', attrs={'id': 'csrf'})['value']

        self.paramaters = {
            'user_email': email,
            'password': password,
            'csrf': csrf,
            'recaptcha_response_field': ''
        }

    def escape(self, string):
        # escape anything that isnt escaped (\xXX)
        string = re.sub(r'\\([^x])', r'\\\\\1', string)
        # unescape \xXX codes
        return codecs.decode(string, 'unicode_escape')

    def login(self):
        ''' Returns False if incorrect pass/email, otherwise True '''
        page = self.session.post('https://auth.hulu.com/v1/web/password/authenticate',
                                  data=self.paramaters, headers=self.headers)

        return page.status_code

    def get_viewing_activity(self):
        page = self.session.get('https://secure.hulu.com/account/history', headers=self.headers)
        print(page)
        soup = BeautifulSoup(page.text, 'lxml')

        url = 'https://secure.hulu.com/api/2.0/retrieve_history'

        env_config = re.search(r'w\._EnvConfig\s+=\s+({[\s\S]+?});', page.text)
        env_config = json.loads(self.escape(env_config.group(1)))

        csrf_values = re.search(r'w\.CsrfValues\s+=\s+({[\s\S]+?});', page.text)
        csrf_values = json.loads(self.escape(csrf_values.group(1)))

        contentPgid = re.search(r'var contentPgid = (\d+);', page.text)
        contentPgid = contentPgid.group(1)

        page = 1

        paramaters = {
            'items_per_page': 1000,
            'order': 'desc',
            'page': page,
            '_user_pgid': env_config['_UserPgids']['freePgid'],
            '_content_pgid': contentPgid,
            '_device_id': 1,
            'region': env_config['_Region'],
            'locale': self.session.cookies.get_dict()['locale'],
            'language': env_config['_Language'],
            'csrf':  csrf_values['/api/2.0/retrieve_history']
        }

        viewing_activity = []

        while True:
            paramaters['page'] = page
            res = self.session.get(url, params=paramaters).json()

            viewing_activity.extend(res['data'])

            if page < res['page_count']:
                page += 1
            else:
                break

        return viewing_activity


email = input('Email: ')
password = input('Password: ')

user = HuluSession(email, password)

log = user.login()
while log != 200:
    if log == 403:
        print('We\'ve probably encountered a captcha for spamming Hulu too '\
              'much, I\'ll try to a selenium fallback if this is a problem '\
              'that happens on the first try. Please talk to be in Slack if '\
              'you are having these issues without any real cause.\n'\
              'Try again later ¯\_(\'_\')_/¯')  # nonunicode-shrug because I bet you someone is going to crash because of unicode
        exit(1)
    else:
        print('Incorrect username or password!')
        print('Please try again...')


    print('')
    email = input('Email: ')
    password = input('Password: ')

    user = HuluSession(email, password)

print('Fetching activity...')


user_activity = user.get_viewing_activity()

print('\n'.join([video['display_title'] for video in user_activity]))
