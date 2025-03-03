from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_user, name='loginUser'),
    path('logout/', views.logout_user, name='logout'),
    path('register/', views.register_user, name='register'),
    path('donate/', views.donate, name='donate'),
    path('account/', views.account, name='account'),
    path('about/', views.about, name='about'),
    path('report/', views.report, name='report'),
    path('jobs/', views.jobs, name='jobs'),
    path("assign-agent/", views.assign_agent, name="assign_agent"),
    path('admin-dashboard/', views.admin_dashboard, name="admin_dashboard"),
]
