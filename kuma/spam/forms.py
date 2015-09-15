from functools import wraps
from django import forms
from tower import ugettext_lazy as _

from . import akismet


def needs_cleaned_data(func):
    @wraps(func)
    def wrapper(self):
        if not hasattr(self, 'cleaned_data'):
            raise forms.ValidationError(
                'The form data has not yet been validated. Please try again'
            )
        return func(self)
    return wrapper


class AkismetFormMixin(object):
    """
    The main form mixin for Akismet checks.

    Form classes using this can reimplement the methods starting with
    "akismet_" below to extend its functionality.
    """
    ERROR_MESSAGE = _('The submitted data contains invalid content.')

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.akismet = akismet.Akismet()
        super(AkismetFormMixin, self).__init__(*args, **kwargs)

    @needs_cleaned_data
    def akismet_parameters(self):
        """
        When using this mixin make sure you implement this method,
        get the parent class' value and return a dictionary of
        parameters matching the ones of the Akismet.check_comment method.

        Use the self.instance or self.request variables to build it.
        """
        return {
            'user_ip': self.request.META.get('REMOTE_ADDR', ''),
            'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
            'referrer': self.request.META.get('HTTP_REFERER', ''),
        }

    @needs_cleaned_data
    def akismet_enabled(self):
        """
        Decides whether to even check for spam during the form validation.

        Checks the API client if it's ready by default.
        """
        return self.akismet.ready

    @needs_cleaned_data
    def akismet_error(self):
        """
        Upon receiving an error from the API client raises an "invalid"
        form validation error with a predefined error message.
        """
        raise forms.ValidationError(self.ERROR_MESSAGE, code='invalid')

    def clean(self):
        cleaned_data = super(AkismetFormMixin, self).clean()
        if self.akismet_enabled():
            akismet_parameters = self.akismet_parameters()
            try:
                self.akismet.check_comment(**akismet_parameters)
            except akismet.AkismetError:
                self.akismet_error()
        return cleaned_data
