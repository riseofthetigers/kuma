from django import forms
from django.test import SimpleTestCase, RequestFactory
from django.utils import six
from django.utils.encoding import force_unicode

from constance.test import override_config
import responses

from . import VERIFY_URL_RE, CHECK_URL_RE
from ..forms import AkismetFormMixin


class AkismetTestForm(AkismetFormMixin, forms.Form):
    pass


class AkismetContentTestForm(AkismetTestForm):
    content = forms.CharField()

    def akismet_parameters(self):
        parameters = super(AkismetTestForm, self).akismet_parameters()
        parameters.update(**self.cleaned_data)
        return parameters


@override_config(AKISMET_KEY='form-api')
class AkismetFormTests(SimpleTestCase):
    rf = RequestFactory()
    remote_addr = '0.0.0.0',
    http_user_agent = 'Mozilla Firefox',
    http_referer = 'https://www.netscape.com/',

    def setUp(self):
        super(AkismetFormTests, self).setUp()
        responses.start()
        self.request = self.rf.get(
            '/',
            REMOTE_ADDR=self.remote_addr,
            HTTP_USER_AGENT=self.http_user_agent,
            HTTP_REFERER=self.http_referer,
        )

    def tearDown(self):
        super(AkismetFormTests, self).tearDown()
        responses.stop()
        responses.reset()

    def test_akismet_parameters(self):
        responses.add(responses.POST, VERIFY_URL_RE, body='valid')
        responses.add(responses.POST, CHECK_URL_RE, body='true')

        form = AkismetContentTestForm(
            self.request,
            data={'content': 'some content'},
        )
        six.assertRaisesRegex(
            self,
            forms.ValidationError,
            'The form data has not yet been validated',
            form.akismet_parameters,
        )
        self.assertTrue(form.is_valid())
        self.assertIn('content', form.cleaned_data)
        parameters = form.akismet_parameters()
        self.assertEqual(parameters['content'], 'some content')
        # super method called
        self.assertEqual(parameters['user_ip'], self.remote_addr)
        self.assertEqual(parameters['user_agent'], self.http_user_agent)
        self.assertEqual(parameters['referrer'], self.http_referer)

    def test_akismet_enabled(self):
        responses.add(responses.POST, VERIFY_URL_RE, body='valid')
        responses.add(responses.POST, CHECK_URL_RE, body='true')

        form = AkismetTestForm(self.request, data={})
        six.assertRaisesRegex(
            self,
            forms.ValidationError,
            'The form data has not yet been validated',
            form.akismet_enabled,
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.akismet_enabled())

    @override_config(AKISMET_KEY='')
    def test_akismet_not_enabled(self):
        responses.add(responses.POST, VERIFY_URL_RE, body='valid')
        responses.add(responses.POST, CHECK_URL_RE, body='true')

        form = AkismetTestForm(self.request, data={})
        six.assertRaisesRegex(
            self,
            forms.ValidationError,
            'The form data has not yet been validated',
            form.akismet_enabled,
        )
        self.assertTrue(form.is_valid())
        self.assertFalse(form.akismet_enabled())

    def test_akismet_error(self):
        responses.add(responses.POST, VERIFY_URL_RE, body='valid')
        responses.add(responses.POST, CHECK_URL_RE, body='yada yada')

        form = AkismetTestForm(self.request, data={})
        # not valid because we found a wrong response from akismet
        self.assertFalse(form.is_valid())
        self.assertIn(form.ERROR_MESSAGE, form.errors['__all__'])
        six.assertRaisesRegex(
            self,
            forms.ValidationError,
            force_unicode(form.ERROR_MESSAGE),
            form.akismet_error,
        )

    def test_form_clean(self):
        responses.add(responses.POST, VERIFY_URL_RE, body='valid')
        responses.add(responses.POST, CHECK_URL_RE, body='true')

        form = AkismetTestForm(self.request, data={})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})
