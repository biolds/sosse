from django import forms
from django.conf import settings

from .models import Document


class SearchForm(forms.Form):
    q = forms.CharField(label='Search',
                        required=False,
                        widget=forms.TextInput(attrs={'autofocus': True}))
    l = forms.CharField(widget=forms.HiddenInput, initial='en', required=False)
    ps = forms.IntegerField(widget=forms.HiddenInput, initial=settings.MYSE_DEFAULT_PAGE_SIZE, required=False)

    def clean(self):
        cleaned_data = super().clean()

        lang_iso = cleaned_data.get('l', 'en')
        pg_lang = settings.MYSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get('name')

        if pg_lang not in Document.get_supported_langs():
            pg_lang = settings.MYSE_FAIL_OVER_LANG

        cleaned_data['l'] = pg_lang

        page_size = cleaned_data.get('ps', settings.MYSE_DEFAULT_PAGE_SIZE) or settings.MYSE_DEFAULT_PAGE_SIZE
        page_size = min(page_size, settings.MYSE_MAX_PAGE_SIZE)
        cleaned_data['ps'] = page_size

        doc_lang = self.data.get('doc_lang')
        if doc_lang in settings.MYSE_LANGDETECT_TO_POSTGRES:
            cleaned_data['doc_lang'] = doc_lang
        return cleaned_data
