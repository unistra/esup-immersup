import logging

from django.forms.models import model_to_dict

from mailmerge import MailMerge

logger = logging.getLogger(__name__)


def merge_docx(request, **kwargs):

    try:
        # TODO: try to put all availables objects related to docx merging
        immersion = kwargs.get('immersion')
        user = kwargs.get('user')
        doc = kwargs.get('doc')
        birth_date = kwargs.get('birth_date')
        home_institution = kwargs.get('home_institution')
        slot_date = kwargs.get('slot_date')

        tpl = doc.document.path
        docx = MailMerge(tpl)

        # TODO: Should be agnostic and use kwargs splat more !
        docx.merge(
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            email=user.email,
            birth_date=birth_date,
            home_institution=home_institution,
            course=immersion.slot.course.label,
            campus=immersion.slot.campus.label,
            building=immersion.slot.building.label,
            slot_date=slot_date,
            start_time=immersion.slot.start_time.strftime("%-Hh%M"),
            end_time=immersion.slot.end_time.strftime("%-Hh%M"),
        )
        return docx
    except Exception as e:
        logger.error('Docx generation error ', str(e))
