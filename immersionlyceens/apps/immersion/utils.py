import io


def GenerateDocx(request, **kwargs):

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
        name='testcoy', title='My title',
    )
    f = io.BytesIO()
    docx.write(f)
    f.seek(0)

    return f
