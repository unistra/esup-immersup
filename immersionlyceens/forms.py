from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext
from django_summernote.widgets import SummernoteInplaceWidget


class ContactUsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['subject'] = forms.CharField(label=_("Subject"), max_length=100, required=True)

        self.fields['body'] = forms.CharField(
            widget=SummernoteInplaceWidget(
                attrs={'summernote': {'width': '100%', 'height': '200px', 'rows': 6, 'airMode': False,}}
            )
        )

        #
        self.fields['subject'].widget.attrs['class'] = 'form-control'
