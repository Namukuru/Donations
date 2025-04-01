from django.urls import path
from . import views
from . import auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', auth_views.login_user, name='login_user'),
    path('logout/', auth_views.logout_user, name='logout_user'),
    path('register/', auth_views.register_user, name='register'),
    path('donate/', views.donate, name='donate'),
    path('account/', views.account, name='account'),
    path('about/', views.about, name='about'),
    path('profile/', views.profile, name='profile'),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path('report/', views.report, name='report'),
    path('jobs/', views.jobs, name='jobs'),
    path('mark_completed/<int:donation_id>/', views.mark_completed, name='mark_completed'),
    path("assign-agent/", views.assign_agent, name="assign_agent"),
    path('unassign_agent/', views.unassign_agent, name='unassign_agent'),
    path('admin-dashboard/', views.admin_dashboard, name="admin_dashboard"),
    path('needs/', views.need_list, name='need_list'),
    path('needs/create/', views.need_create, name='need_create'),
    path('needs/<int:pk>/update/', views.need_update, name='need_update'),
    path('needs/<int:pk>/delete/', views.need_delete, name='need_delete'),
]
