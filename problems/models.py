from django.db import models
from django.contrib.auth.models import User

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Problem(models.Model):
    DIFFICULTY_CHOICES = (
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=6, choices=DIFFICULTY_CHOICES, default='easy')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problems')
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    solution_code = models.TextField()  # New field for creator's solution
    function_header = models.TextField(blank=True, null=True)  # Added for function signature
    input_vars = models.JSONField(default=list, blank=True)  # Added for parameter storage
    return_type = models.CharField(max_length=50, default='None')  # Added for return type

    def __str__(self):
        return self.title

class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    input_value = models.JSONField()
    expected_output = models.JSONField()

    def __str__(self):
        return f"TestCase for {self.problem.title}"

class Solution(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='solutions')
    code = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solutions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Solution by {self.created_by.username} for {self.problem.title}"