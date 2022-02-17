from django import forms
from django.conf import settings

from .models import Document


class SearchForm(forms.Form):
    q = forms.CharField(label='Search',
                        widget=forms.TextInput(attrs={'autofocus': True}))
    lang = forms.CharField(widget=forms.HiddenInput, initial='en')

    def clean(self):
        cleaned_data = super().clean()

        lang_iso = cleaned_data.get('lang', 'en')
        pg_lang = settings.MYSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get('name')

        if pg_lang not in Document.get_supported_langs():
            pg_lang = settings.MYSE_FAIL_OVER_LANG

        cleaned_data['lang'] = pg_lang
        return cleaned_data
