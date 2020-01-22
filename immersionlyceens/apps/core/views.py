from django.shortcuts import render, redirect


# Create your views here.

# TODO: !!!!!!!!!!!!!!!!!!!!!!! AUTHORIZATION REQUIRED !!!!!!!!!!!!!!!!!!!!!!!
def import_holidays(request):
    """Import holidays from API if it's convigured"""

    # TODO: dynamic redirect
    return redirect('/admin/core/holiday')
