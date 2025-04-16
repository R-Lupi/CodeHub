from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path('', views.problem_list, name='problem_list'),
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('create/', views.create_problem, name='create_problem'),
    path('signup/', views.signup, name='signup'),
    path('problem/<int:problem_id>/submit/', views.submit_solution, name='submit_solution'),
    path('accounts/profile/', views.profile, name='profile'),  
    path('problem/<int:problem_id>/rate/', views.rate_problem, name='rate_problem'), 
    path('problem/<int:problem_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('problem/<int:problem_id>/delete/', views.delete_problem, name='delete_problem'),  
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.problem_list, name='problem_list'),
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('create/', views.create_problem, name='create_problem'),
    path('signup/', views.signup, name='signup'),
    path('problem/<int:problem_id>/submit/', views.submit_solution, name='submit_solution'),
    path('accounts/profile/', views.profile, name='profile'),
    path('problem/<int:problem_id>/rate/', views.rate_problem, name='rate_problem'),
    path('problem/<int:problem_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('problem/<int:problem_id>/delete/', views.delete_problem, name='delete_problem'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)