from django import forms
from .models import News, Comment, Coin
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth import authenticate

class CoinForm(forms.ModelForm):
    #content = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Coin
        fields = ['name', 'trustRate', 'openToBuy', 'isActive']

    def __init__(self, *args, **kwargs):
        super(CoinForm, self).__init__(*args, **kwargs)

class NewsForm(forms.ModelForm):
    #content = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = News
        fields = ['title', 'content', 'image']

    def __init__(self, *args, **kwargs):
        super(NewsForm, self).__init__(*args, **kwargs)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']

    def __init__(self, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs = {'class': 'form-control'}


class LoginForm(forms. Form):
    username = forms.CharField(required=True, max_length=50, label='Username', widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(required=True, max_length=50, label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError('Hatalı Kullanıcı Adı veya şifre Girdiniz')
