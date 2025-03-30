# problems/admin.py
from django.contrib import admin
from .models import Problem, Tag, TestCase, Solution

# Customize Tag admin view
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Customize TestCase admin view
@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('problem', 'input_value', 'expected_output')
    list_filter = ('problem',)
    search_fields = ('problem__title',)

# Customize Solution admin view
@admin.register(Solution)
class SolutionAdmin(admin.ModelAdmin):
    list_display = ('problem', 'created_by', 'created_at')
    list_filter = ('problem', 'created_at')
    search_fields = ('problem__title', 'created_by__username')

class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'created_by', 'created_at')
    list_filter = ('difficulty', 'created_at', 'tags')
    search_fields = ('title', 'description')
    filter_horizontal = ('tags',)
    inlines = [TestCaseInline]  # Add this