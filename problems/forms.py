# problems/forms.py
from django import forms
from django.forms import formset_factory
from .models import Problem, TestCase, Tag, Profile
import json

class ProblemForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        help_text="Comma-separated tags",
        widget=forms.TextInput(attrs={'placeholder': 'tag1, tag2, tag3'})
    )
    solution_code = forms.CharField(widget=forms.Textarea, help_text="Enter the solution code (e.g., 'def solution(a, b): return a + b')")

    class Meta:
        model = Problem
        fields = ['title', 'description', 'difficulty', 'solution_code']

    def save(self, commit=True, user=None):
        problem = super().save(commit=False)
        if user:
            problem.created_by = user
        if commit:
            problem.save()
            tags = {tag.strip() for tag in self.cleaned_data['tags'].split(',') if tag.strip()}
            tag_objects = [Tag.objects.get_or_create(name=tag)[0] for tag in tags]
            problem.tags.set(tag_objects)  # More efficient than multiple `.add()`
        return problem


class TestCaseForm(forms.ModelForm):
    input_value = forms.CharField(help_text="Enter JSON, e.g., {'nums': [1, 2, 3]}", required=False)
    expected_output = forms.CharField(help_text="Enter JSON, e.g., 6")

    class Meta:
        model = TestCase
        fields = ['input_value', 'expected_output']

    def clean_input_value(self):
        data = self.cleaned_data['input_value']
        try:
            json.loads(data)  # Validate JSON
            return data.strip()  # Return string
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format. Ensure it is a valid JSON string.")

    def clean_expected_output(self):
        data = self.cleaned_data['expected_output']
        try:
            json.loads(data)  # Validate JSON
            return data.strip()  # Return string
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format. Ensure it is a valid JSON string.")

def get_test_case_formset(extra=1):
    return formset_factory(TestCaseForm, extra=extra)

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture']

TestCaseFormSet = get_test_case_formset(extra=1)