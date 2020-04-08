
from mailmerge import MailMerge

from django.forms.models import model_to_dict



def merge_docx(request, **kwargs):

    try:
        # TODO: try to put all availables objects related to docx merging
        immersion = kwargs.get('immersion', None)
        user = kwargs.get('user', None)
        doc = kwargs.get('doc', None)


        tpl = doc.document.path
        docx = MailMerge(tpl)
        docx.merge(
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            email=user.email,

        )
        return docx
    except Exception as e:
        print(str(e))
