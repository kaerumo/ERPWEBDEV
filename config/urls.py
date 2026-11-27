from django.contrib import admin
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from erp.views import frontend_page


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("erp.urls")),
    path("", frontend_page, {"page": "index.html"}, name="home"),
    path("<str:page>.html", frontend_page, name="frontend-page"),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
