from immersionlyceens.forms import ContactUsForm


def context_contact_us_form(request):
    return {'contact_us_form': ContactUsForm()}
