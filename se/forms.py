from django import forms


class SearchForm(forms.Form):
    search = forms.CharField(label='Search',
                             widget=forms.TextInput(attrs={'autofocus': True}))
