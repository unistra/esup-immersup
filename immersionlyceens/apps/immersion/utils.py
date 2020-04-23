import logging

from django.forms.models import model_to_dict
from django.http.response import HttpResponseNotFound
from django.template.loader import get_template

import weasyprint

logger = logging.getLogger(__name__)


class DocxMergeError(Exception):
    pass


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
        logger.error('Docx generation error ', e)
        raise DocxMergeError("Failed to merge document")


def generate_pdf(request, template_name, context, **kwargs):
    """
    Returns a pdf based on
        template_name : path of html template
        context : vars used in the template
    """
    base_url = request.build_absolute_uri("/")
    template = get_template(template_name)
    context = {'tpl_vars': context}
    html = template.render(context)
    response = HttpResponse(content_type="application/pdf")
    weasyprint.HTML(string=html, base_url=base_url).write_pdf(response)
    return response
