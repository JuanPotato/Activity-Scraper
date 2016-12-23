#!/usr/bin/python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import hashlib
import random
import codecs
import shutil
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

        j = {}

        try:
            j = page.json()
        except:
            pass

        return (page.status_code, j)

    def get_viewing_activity(self):
        self.session.get('http://www.hulu.com/welcome')
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
            'locale': env_config['_Language'].lower(),
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

    def get_captcha(self):
    # I can't check if this works because I havent been able to get it to trigger me a captcha for some reason :\
        page = self.session.get('https://auth.hulu.com/login', headers=self.headers)
        recaptcha_key = re.search(r'recaptchaKey: \'(.*?)\',', page.text)
        recaptcha_key = recaptcha_key.group(1)

        url = 'https://www.google.com/recaptcha/api/challenge'

        paramaters = {
            'k': recaptcha_key,
            'ajax': 1,
            'cachestop': '%.17f' % random.random()
        }

        page = self.session.get(url, params=paramaters, headers=self.headers)

        recaptcha_state = re.search(r'RecaptchaState\s+=\s+({[\s\S]+?});', page.text)
        recaptcha_state = json.loads(self.escape(recaptcha_state.group(1)))

        reload_params = {
            'c': recaptcha_state['challenge'],
            'k': recaptcha_key,
            'lang': 'en',
            'reason': 'i',
            'type': 'image'
        }

        data = self.session.get("http://www.google.com/recaptcha/api/reload" , params=reload_params).text
        challenge = re.search(r"finish_reload\('(.*?)'", data).group(1)

        c_hash = hashlib.md5(challenge.encode()).hexdigest()
        
        for _ in range(3):
            c_hash += hashlib.md5(c_hash.encode()).hexdigest()

        r = self.session.get("http://www.google.com/recaptcha/api/image", params={'c': challenge, 'th': c_hash}, stream=True)
        if r.status_code == 200:
            with open('captcha.jpg', 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)     



email = input('Email: ')
password = input('Password: ')

user = HuluSession(email, password)

log = user.login()
while log[0] != 200:
    print(log)
    if log[0] == 403:
        if 'message' in log[1]:
            print(log[1]['message'])

        if 'error' in log[1] and log[1]['error'] == 'retry_limit':
            print('We\'ve encountered a captcha due to too many incorrect tries, please try again later.') # TODO: Generate script that downloads the captcha
            get_captcha()
    else:
        print('An unknown error occured :(')
        print('Please try again...')

    print('')
    email = input('Email: ')
    password = input('Password: ')

    user = HuluSession(email, password)

print('Fetching activity...')


user_activity = user.get_viewing_activity()

print('\n'.join([video['display_title'] for video in user_activity]))
