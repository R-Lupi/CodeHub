# leetcode_forum/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout as auth_logout
from django.shortcuts import render, redirect

# Custom logout view with confirmation
def logout_view(request):
    if request.method == 'GET':
        # Render confirmation page on GET
        return render(request, 'logout.html', {})
    elif request.method == 'POST':
        # Perform logout on POST and redirect
        auth_logout(request)
        return redirect('problem_list')
    return redirect('problem_list')  # Fallback for other methods

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', logout_view, name='logout'),  # Use custom view
    path('', include('problems.urls')),
]