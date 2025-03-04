from django.contrib.auth import get_user_model
from django.contrib.auth.views import LogoutView
from django.http import HttpResponseServerError
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from two_factor.forms import MethodForm
from two_factor.utils import default_device
from two_factor.views import LoginView, QRGeneratorView, SetupView
from two_factor.views.utils import class_view_decorator
from two_factor.forms import MethodForm, AuthenticationTokenForm, BackupTokenForm
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rocky.settings import LOGIN_REDIRECT_URL
from tools.models import OrganizationMember
from account.forms import LoginForm

User = get_user_model()


@class_view_decorator(sensitive_post_parameters())
@class_view_decorator(never_cache)
class LoginRockyView(LoginView):
    form_list = (
        ("auth", LoginForm),
        ("token", AuthenticationTokenForm),
        ("backup", BackupTokenForm),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        # if default device is set then the user has enabled two factor auth
        context["two_factor_enabled"] = default_device(self.request.user)
        context["form_name"] = "login"
        context["breadcrumbs"] = [
            {
                "url": reverse("landing_page"),
                "text": _("KAT"),
            },
            {
                "url": reverse("login"),
                "text": _("Login"),
            },
        ]
        return context

    def get_success_url(self):
        url = self.get_redirect_url()
        if default_device(self.request.user) is None:
            url = resolve_url("setup")
        return url or resolve_url(LOGIN_REDIRECT_URL)


@class_view_decorator(sensitive_post_parameters())
@class_view_decorator(never_cache)
class QRGeneratorRockyView(QRGeneratorView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, *args, **kwargs):
        # We only allow enabling TFA for verified users to shield new organization members before we approve them
        if not is_verified(self.request.user):
            return HttpResponseServerError()

        return super().get(request, *args, **kwargs)


@class_view_decorator(sensitive_post_parameters())
@class_view_decorator(never_cache)
class SetupRockyView(SetupView):
    # This is set to skip the extra welcome form which is for KAT a redundant step.
    form_list = (("method", MethodForm),)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context["breadcrumbs"] = [
            {
                "url": reverse("login"),
                "text": _("Login"),
            },
            {
                "url": reverse("setup"),
                "text": _("Two factor authentication"),
            },
        ]
        # if default device is set then the user has enabled two factor auth
        context["verified"] = is_verified(self.request.user)

        return context


class LogoutRockyView(LogoutView):
    next_page = "/"


def is_verified(user: User) -> bool:
    if user.is_superuser:
        return True

    if not OrganizationMember.objects.filter(user=user).exists():
        return False

    organizationmember = OrganizationMember.objects.get(user=user)

    return organizationmember.verified
