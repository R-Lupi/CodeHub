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
    solution_code = models.TextField()
    function_header = models.TextField(blank=True, null=True)
    input_vars = models.JSONField(default=list, blank=True)
    return_type = models.CharField(max_length=50, default='None')
    # New fields to track unique users
    attempted_by = models.ManyToManyField(User, related_name='attempted_problems', blank=True)
    solved_by = models.ManyToManyField(User, related_name='solved_problems', blank=True)

    def __str__(self):
        return self.title

    def get_likes_count(self):
        return self.ratings.filter(vote=1).count()

    def get_dislikes_count(self):
        return self.ratings.filter(vote=-1).count()

    @property
    def attempt_count(self):
        return self.attempted_by.count()

    @property
    def solve_count(self):
        return self.solved_by.count()

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

class ProblemRating(models.Model):
    VOTE_CHOICES = (
        (1, 'Like'),
        (-1, 'Dislike'),
    )
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_ratings')
    vote = models.SmallIntegerField(choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('problem', 'user')

    def __str__(self):
        return f"{self.user.username} {'liked' if self.vote == 1 else 'disliked'} {self.problem.title}"

class FavoriteProblem(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='favorited_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_problems')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('problem', 'user')

    def __str__(self):
        return f"{self.user.username} favorited {self.problem.title}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"