from django.urls import path

from erp import views


urlpatterns = [
    path("session/", views.session_view, name="api-session"),
    path("session/login/", views.login_view, name="api-login"),
    path("session/logout/", views.logout_view, name="api-logout"),
    path("data/", views.data_view, name="api-data"),
    path("data/<slug:collection>/", views.collection_view, name="api-collection"),
]
