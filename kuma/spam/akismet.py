import urlparse

from constance import config
from django.conf import settings
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter
from requests import Session, exceptions


class AkismetError(Exception):
    """
    A custom exception that takes the requests' response, its status code
    and an optional debug help directly from Akismet.
    """
    def __init__(self, response, status_code, debug_help):
        self.response = response
        self.status_code = status_code
        self.debug_help = debug_help

    def __str__(self):
        return ('%s response, debug help: %s, full response: %s' %
                (self.status_code, self.debug_help, self.response.text))


class Akismet(object):
    """
    The Akismet client implementation wrapping a request session and
    having API specific methods for easy spam and ham handling.
    """
    submission_success = 'Thanks for making the web a better place.'

    def __init__(self):
        self.key = config.AKISMET_KEY
        self.domain = settings.DOMAIN
        self.session = Session()
        self.adapter = HTTPAdapter(
            max_retries=Retry(
                # number of total retries
                total=5,
                # retry once in case we can't connect to Akismet
                connect=1,
                # retry once in case we can't read the response from Akismet
                read=1,
                # retry once in case we're redirect by Akismet
                redirect=1,
                # definitely retry if Akismet is unwell
                status_forcelist=[500, 503])
        )
        self.session.mount('http://', self.adapter)
        self.session.mount('https://', self.adapter)
        # define if this client is even usable
        # use this in the app code
        try:
            self.ready = self.verify_key()
        except AkismetError:
            # just take a shortcut when there was an
            # error accessing Akismet
            self.ready = False

    @property
    def url(self):
        return 'https://%s.rest.akismet.com/1.1/' % self.key

    def send(self, method, user_ip='', user_agent='', **payload):
        payload.update({
            'blog': self.domain,
            'user_ip': user_ip,
            'user_agent': user_ip,
        })
        url = urlparse.urljoin(self.url, method)
        try:
            return self.session.post(url, data=payload)
        except exceptions.RequestException:
            # let this exception bubble up for now since the mail_admins
            # log handler and Sentry will let us know about this
            raise

    def error(self, response):
        """
        The error handler we'll be used by all the API endpoints' methods.

        This should implement a common strategy for handling Akismet errors
        so that we have a stable API for error handling when using this
        Akismet client.
        """
        raise AkismetError(response,
                           response.status_code,
                           response.headers.get('X-Akismet-Debug-Help',
                                                'Not provided'))

    def verify_key(self):
        """
        An API call method to test the provided API key.

        This is automatically called when the Akismet client is
        instantiated so that the app code can decide if it's usable right
        away.
        """
        # quick bailout when the key isn't given
        if not self.key:
            return False
        response = self.send('verify-key', **{'key': self.key})
        try:
            return {'valid': True, 'invalid': False}[response.text]
        except KeyError:
            self.error(response)

    def check_comment(self, user_ip, user_agent, **optional):
        """
        Submits content to Akismet to check if it's spam or not.

        Takes optional keys sent over to Akismet, as defined on
        http://akismet.com/development/api/#comment-check

        :raises AkismetError: if the response from Akismet was unexpected
        :rtype: bool

        Required:

        :param str user_ip: The IP address of the user submitting the content
        :param str user_agent: The user agent of the user submitting the data

        Optional:

        :param str referrer: The content of the HTTP_REFERER header should
                             be sent here.
        :param str permalink: The permanent location of the entry the
                              comment was submitted to
        :param str comment_type: May be blank, comment, trackback, pingback,
                                 or a made up value like "registration".
        :param str comment_author: Name submitted with the comment.
        :param str comment_author_email: Email address submitted with the
                                         comment.
        :param str comment_author_url: URL submitted with comment.
        :param str comment_content: The content that was submitted.
        :param str blog_lang: Indicates the language(s) in use on the blog or
                              site, in ISO 639-1 format, comma-separated.
                              A site with articles in English and French
                              might use "en, fr_ca".
        :param str blog_charset: The character encoding for the form values
                                 included in comment_* parameters,
                                 such as "UTF-8" or "ISO-8859-1".
        """
        response = self.send('comment-check', user_ip, user_agent, **optional)
        try:
            return {'true': True, 'false': False}[response.text]
        except KeyError:
            self.error(response)

    def submit_spam(self, user_ip, user_agent, **optional):
        """
        Submits content as spam to Akismet.

        Takes same parameters as :meth:`Akismet.check_comment`.

        :rtype: None
        :raises AkismetError: if the submission wasn't succesful
        """
        response = self.send('submit-spam', user_ip, user_agent, **optional)
        if response.text != self.submission_success:
            self.error(response)

    def submit_ham(self, user_ip, user_agent, **optional):
        """
        Submits content as ham to Akismet.

        Takes same parameters as :meth:`Akismet.check_comment`.

        :rtype: None
        :raises AkismetError: if the submission wasn't succesful
        """
        response = self.send('submit-ham', user_ip, user_agent, **optional)
        if response.text != self.submission_success:
            self.error(response)
