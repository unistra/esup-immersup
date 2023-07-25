import time
from functools import wraps

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden


def is_ajax_request(view_func):
    """
    Check if the request is ajax
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.is_ajax():
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("<h1>Forbidden</h1>You do not have \
            permission to access this page.")
    return wrapper


def is_post_request(view_func):
    """
    Check if the request is POST
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method == 'POST':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("<h1>Forbidden</h1>You do not have \
            permission to access this page.")
    return wrapper


def groups_required(*groups, login_url='/'):
    def in_groups(user):
        return getattr(user, 'has_groups', False) and user.has_groups(*groups)

    return user_passes_test(in_groups, login_url=login_url)


def timer(func):
    """helper function to display execution time"""

    @wraps(func)  # used for copying func metadata
    def wrapper(*args, **kwargs):
        # record start time
        start = time.time()

        # func execution
        result = func(*args, **kwargs)

        duration = (time.time() - start) * 1000
        # output execution time to console
        print('view {} takes {:.2f} ms'.format(
            func.__name__,
            duration
            ))
        return result
    return wrapper