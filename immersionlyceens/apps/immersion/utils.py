

from mailmerge import MailMerge


def merge_docx(request, **kwargs):

    try:
        # TODO: try to put all availables objects related to docx merging
        slot = kwargs.get('slot')
        slot_list = kwargs.get('slot_list')
        course = kwargs.get('course')
        immersion = kwargs.get('immersion')
        user = kwargs.get('user')
        doc = kwargs.get('doc')

        tpl = doc.document.path
        docx = MailMerge(tpl)
        docx.merge(
            name='test', title='My title',
        )

        return docx
    except Exception as e:
        print(str(e))
