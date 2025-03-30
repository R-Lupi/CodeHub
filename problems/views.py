import docker
import json
import time
import requests
import re
import platform
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import Problem, Tag, Solution, TestCase
from .forms import ProblemForm, TestCaseFormSet

# Docker-based code execution
def run_code_in_docker(code, test_cases, input_vars, language='python'):
    results = []
    if platform.system() == 'Windows':
        base_url = 'npipe:////./pipe/docker_engine'
    else:
        base_url = 'unix:///var/run/docker.sock'
    client = docker.DockerClient(base_url=base_url)

    type_converters = {
        'int': int,
        'float': float,
        'str': str,
        'bool': lambda x: x.lower() == 'true',
        'list': json.loads,
        'dict': json.loads
    }

    for test_case in test_cases:
        input_json = test_case.input_value
        expected_output = test_case.expected_output

        # Convert input values to expected types
        input_dict = json.loads(input_json)
        for var in input_vars:
            if var['name'] in input_dict:
                converter = type_converters.get(var['type'], str)
                try:
                    input_dict[var['name']] = converter(input_dict[var['name']])
                except (ValueError, json.JSONDecodeError):
                    input_dict[var['name']] = input_dict[var['name']]  # Keep as is if conversion fails

        wrapper_code = f"""
import json
import sys

{code}

input_data = {json.dumps(input_dict)}
print("Parameters: " + str(input_data))
result = solution(**input_data)
print("RESULT_SEPARATOR:" + json.dumps(result))
"""
        print(f"Running wrapper code:\n{wrapper_code}")
        try:
            container = client.containers.create(
                image='python:3.9-slim',
                command='python -c "{}"'.format(wrapper_code.replace('"', '\\"')),
                mem_limit='128m',
                cpu_quota=10000,
                network_disabled=True,
                working_dir='/tmp',
            )
            container.start()
            result = container.wait(timeout=5)
            logs = container.logs(stdout=True, stderr=True).decode().strip()
            container.remove()

            log_lines = logs.split('\n')
            console_logs = []
            actual_output_raw = ""

            for line in log_lines:
                if line.startswith("RESULT_SEPARATOR:"):
                    actual_output_raw = line.replace("RESULT_SEPARATOR:", "").strip()
                else:
                    console_logs.append(line)

            # Parse actual output as JSON to match expected format
            try:
                actual_output = json.loads(actual_output_raw)
            except json.JSONDecodeError:
                actual_output = actual_output_raw  # Fallback to raw if not JSON

            console_logs_str = "\n".join(console_logs).strip() if console_logs else "No console output"
            print(f"Container logs:\n{logs}")

            # Compare parsed actual with expected (both as JSON strings)
            expected_parsed = json.loads(expected_output)
            results.append({
                'input': input_json,
                'expected': expected_output,
                'actual': actual_output_raw,
                'passed': actual_output == expected_parsed,
                'console_logs': console_logs_str
            })
        except docker.errors.ContainerError as e:
            results.append({'error': f"Container error: {str(e)}"})
        except docker.errors.APIError as e:
            results.append({'error': f"Execution timed out or failed: {str(e)}"})
        except Exception as e:
            results.append({'error': f"Unexpected error: {str(e)}"})

    return results

# Generate function header from input variables and return type
def generate_function_header(input_vars, return_type):
    """Generate a function header from input variables and return type"""
    params = [f"{var['name']}: {var['type']}" for var in input_vars if var['name'] and var['type']]
    return f"def solution({', '.join(params)}) -> {return_type}:\n    pass"

# Signup view
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('problem_list')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

# Problem list view
def problem_list(request):
    tag = request.GET.get('tag')
    query = request.GET.get('q')
    problems = Problem.objects.all()
    if tag:
        problems = problems.filter(tags__name=tag)
    if query:
        problems = problems.filter(title__icontains=query) | problems.filter(description__icontains=query)
    tags = Tag.objects.all()
    return render(request, 'problem_list.html', {'problems': problems, 'tags': tags})

# Problem detail view with all solutions
def problem_detail(request, problem_id):
    problem = Problem.objects.get(id=problem_id)
    user_solution = None
    all_solutions = Solution.objects.filter(problem=problem).order_by('-created_at')
    if request.user.is_authenticated:
        user_solution = Solution.objects.filter(problem=problem, created_by=request.user).order_by('-created_at').first()
    return render(request, 'problem_detail.html', {
        'problem': problem,
        'user_solution': user_solution,
        'all_solutions': all_solutions,
        'function_header': problem.function_header,
        'input_vars': problem.input_vars,
        'return_type': problem.return_type
    })

# Create problem view with two-step process
@login_required
def create_problem(request):
    if request.method == 'POST':
        if 'generate_header' in request.POST:
            problem_form = ProblemForm(request.POST)
            input_vars = []
            for i in range(int(request.POST.get('input_count', 0))):
                name = request.POST.get(f'input_name_{i}')
                var_type = request.POST.get(f'input_type_{i}')
                if name and var_type:
                    input_vars.append({'name': name, 'type': var_type})
            return_type = request.POST.get('return_type', 'None')
            function_header = generate_function_header(input_vars, return_type)
            
            test_case_formset = TestCaseFormSet()
            print(f"Generated header: {function_header}, input_vars: {input_vars}")
            return render(request, 'create_problem.html', {
                'problem_form': problem_form,
                'test_case_formset': test_case_formset,
                'input_vars': input_vars,
                'return_type': return_type,
                'function_header': function_header,
                'header_generated': True
            })

        elif 'run' in request.POST or 'save' in request.POST:
            problem_form = ProblemForm(request.POST)
            test_case_formset = TestCaseFormSet(request.POST)
            input_vars_raw = request.POST.get('input_vars', '[]')
            print(f"Raw input_vars: {input_vars_raw}")
            try:
                input_vars = json.loads(input_vars_raw)
                if not isinstance(input_vars, list):
                    input_vars = []
            except json.JSONDecodeError:
                input_vars = []
                print("Invalid input_vars JSON:", input_vars_raw)
            print(f"Parsed input_vars: {input_vars}")

            return_type = request.POST.get('return_type', 'None')
            function_header = generate_function_header(input_vars, return_type)

            print(f"POST data: {request.POST}")

            # Process all test cases
            test_cases = []
            test_case_data = []
            total_forms = int(request.POST.get('form-TOTAL_FORMS', 0))
            max_index = max([int(k.split('-')[1]) for k in request.POST.keys() if k.startswith('form-') and 'param_' in k] + [total_forms - 1], default=0)
            print(f"Max test case index: {max_index + 1}")
            for i in range(max_index + 1):
                input_dict = {}
                test_case_input = {}
                for var in input_vars:
                    key = f'form-{i}-param_{var["name"]}'
                    value = request.POST.get(key, '')
                    print(f"Checking {key}: {value}")
                    if value:
                        input_dict[var['name']] = value
                        test_case_input[var['name']] = value
                expected_key = f'form-{i}-expected_output'
                expected_output = request.POST.get(expected_key, '')
                print(f"Checking {expected_key}: {expected_output}")
                if input_dict and expected_output:
                    test_cases.append(type('TestCase', (), {
                        'input_value': json.dumps(input_dict),
                        'expected_output': json.dumps(expected_output)
                    }))
                    test_case_data.append({
                        'inputs': test_case_input,
                        'expected_output': expected_output
                    })
            print(f"Test cases: {test_cases}")
            print(f"Test case data: {test_case_data}")

            if problem_form.is_valid():
                if 'run' in request.POST:
                    solution_code = problem_form.cleaned_data['solution_code']
                    full_function_header = generate_function_header(input_vars, return_type)
                    if not solution_code.strip().startswith('def solution'):
                        solution_code = full_function_header.replace('pass', '') + solution_code
                    print(f"Solution code: {solution_code}")
                    results = run_code_in_docker(solution_code, test_cases, input_vars)
                    print(f"Results from run_code_in_docker: {results}")
                    return render(request, 'create_problem.html', {
                        'problem_form': problem_form,
                        'test_case_formset': test_case_formset,
                        'results': results,
                        'solution_code': solution_code,
                        'input_vars': input_vars,
                        'return_type': return_type,
                        'function_header': function_header,
                        'header_generated': True,
                        'test_case_data': test_case_data
                    })
                elif 'save' in request.POST:
                    print("Attempting to save problem")
                    problem = problem_form.save(commit=False)
                    problem.created_by = request.user
                    problem.input_vars = input_vars
                    problem.return_type = return_type
                    problem.function_header = function_header
                    problem.solution_code = problem_form.cleaned_data['solution_code']  # Save creator's solution
                    problem.save()
                    
                    for test_case in test_cases:
                        TestCase.objects.create(
                            problem=problem,
                            input_value=test_case.input_value,
                            expected_output=test_case.expected_output
                        )
                    print(f"Problem saved with ID: {problem.id}")
                    return redirect('problem_detail', problem_id=problem.id)
            print("Form errors:", problem_form.errors, test_case_formset.errors)
            return render(request, 'create_problem.html', {
                'problem_form': problem_form,
                'test_case_formset': test_case_formset,
                'input_vars': input_vars,
                'return_type': return_type,
                'function_header': function_header,
                'header_generated': True,
                'test_case_data': test_case_data,
                'error': 'Please correct the errors in the form.'
            })
    else:
        problem_form = ProblemForm()
        return render(request, 'create_problem.html', {
            'problem_form': problem_form,
            'input_vars': [],
            'return_type': 'None',
            'header_generated': False
        })

# Submit solution view with edit functionality
@login_required
def submit_solution(request, problem_id):
    problem = Problem.objects.get(id=problem_id)
    function_header = problem.function_header
    test_cases = problem.test_cases.all()
    user_solution = Solution.objects.filter(problem=problem, created_by=request.user).order_by('-created_at').first()
    initial_code = user_solution.code if user_solution else function_header

    if request.method == 'POST':
        code = request.POST.get('code')
        if 'run' in request.POST:
            results = run_code_in_docker(code, test_cases)
            return render(request, 'submit_solution.html', {
                'problem': problem,
                'function_header': function_header,
                'code': code,
                'results': results,
                'input_vars': problem.input_vars,
                'return_type': problem.return_type
            })
        elif 'submit' in request.POST:
            results = run_code_in_docker(code, test_cases)
            if all(result.get('passed', False) for result in results):
                if user_solution:
                    user_solution.code = code
                    user_solution.save()
                else:
                    Solution.objects.create(problem=problem, code=code, created_by=request.user)
                return redirect('problem_detail', problem_id=problem.id)
            return render(request, 'submit_solution.html', {
                'problem': problem,
                'function_header': function_header,
                'code': code,
                'results': results,
                'error': 'Solution failed some test cases',
                'input_vars': problem.input_vars,
                'return_type': problem.return_type
            })

    return render(request, 'submit_solution.html', {
        'problem': problem,
        'function_header': function_header,
        'code': initial_code,
        'input_vars': problem.input_vars,
        'return_type': problem.return_type
    })

@login_required
def profile(request):
    user_solutions = Solution.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'profile.html', {
        'user': request.user,
        'solutions': user_solutions
    })