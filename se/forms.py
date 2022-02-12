from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(label='Search',
                        widget=forms.TextInput(attrs={'autofocus': True}))
