from django.urls import path
from django.contrib.auth import views as auth_views
from .views.auth_views import login_user, logout_user, register_user
from .views.donation_views import donate, account
from .views.need_views import need_list, need_create, need_update, need_delete
from .views.profile_views import profile, edit_profile
from .views.admin_views import admin_dashboard,report
from .views.general_views import home,about,jobs, assign_agent, unassign_agent,mark_completed
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Authentication
    path("login/", login_user, name="login_user"),
    path("logout/", logout_user, name="logout_user"),
    path("register/", register_user, name="register"),

    # General Pages
    path("", home, name="home"),
    path("about/", about, name="about"),
    path('account/', account, name='account'),
     path('report/', report, name='report'),

    # Donations
    path("donate/", donate, name="donate"),
    path('donations/<int:donation_id>/complete/', mark_completed, name='mark_completed'),

    # Profile & User Management
    path("profile/", profile, name="profile"),
    path("profile/edit/", edit_profile, name="edit_profile"),

    # Jobs & Agent Management
    path("jobs/", jobs, name="jobs"),
    path("assign-agent/", assign_agent, name="assign_agent"),
    path("unassign-agent/", unassign_agent, name="unassign_agent"),

    # Admin Dashboard
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),

    # Needs Management
    path("needs/", need_list, name="need_list"),
    path("needs/create/", need_create, name="need_create"),
    path("needs/<int:pk>/update/", need_update, name="need_update"),
    path("needs/<int:pk>/delete/", need_delete, name="need_delete"),
    
    # Password reset links (built-in)
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name="password_reset.html",
             email_template_name='password_reset_email.txt',
             html_email_template_name='password_reset_email.html',
             subject_template_name='password_reset_subject.txt',
             success_url='/password_reset/done/'), 
         name='password_reset'
         ),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name="password_reset_done.html"), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"), name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)