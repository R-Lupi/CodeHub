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
        'dict': json.loads,
        'None': lambda x: None  # Handle None explicitly
    }

    for test_case in test_cases:
        input_json = test_case.input_value
        expected_output = test_case.expected_output

        input_dict = json.loads(input_json)
        for var in input_vars:
            if var['name'] in input_dict:
                converter = type_converters.get(var['type'], str)
                try:
                    input_dict[var['name']] = converter(input_dict[var['name']])
                except (ValueError, json.JSONDecodeError):
                    input_dict[var['name']] = input_dict[var['name']]

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

            try:
                actual_output = json.loads(actual_output_raw)
            except json.JSONDecodeError:
                actual_output = actual_output_raw

            console_logs_str = "\n".join(console_logs).strip() if console_logs else "No console output"
            print(f"Container logs:\n{logs}")

            expected_parsed = json.loads(expected_output) if expected_output.startswith('"') else expected_output
            return_type = test_case.__dict__.get('return_type', 'str')
            converter = type_converters.get(return_type, str)
            try:
                if return_type == 'None':
                    expected_parsed = None if expected_output == 'null' else expected_output
                    actual_output = None if actual_output is None else actual_output
                elif return_type in ['int', 'float', 'bool']:
                    actual_output = converter(actual_output)
                    expected_parsed = converter(expected_parsed)
                elif return_type == 'str':
                    actual_output = str(actual_output)
                    expected_parsed = str(expected_parsed)
            except (ValueError, TypeError):
                pass

            passed = actual_output == expected_parsed
            print(f"Debug: actual_output={actual_output} (type={type(actual_output)}), expected_parsed={expected_parsed} (type={type(expected_parsed)}), passed={passed}, return_type={return_type}")

            results.append({
                'input': input_json,
                'expected': expected_output,
                'actual': actual_output_raw,
                'passed': passed,
                'console_logs': console_logs_str
            })
        except docker.errors.ContainerError as e:
            results.append({'error': f"Container error: {str(e)}"})
        except docker.errors.APIError as e:
            results.append({'error': f"Execution timed out or failed: {str(e)}"})
        except Exception as e:
            results.append({'error': f"Unexpected error: {str(e)}"})

    return results

def generate_function_header(input_vars, return_type):
    """Generate a function header from input variables and return type"""
    params = [f"{var['name']}: {var['type']}" for var in input_vars if var['name'] and var['type']]
    return f"def solution({', '.join(params)}) -> {return_type}:\n    pass"

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

@login_required
def create_problem(request):
    if request.method == 'POST':
        print(f"Full POST data: {request.POST}")
        if 'generate_header' in request.POST:
            problem_form = ProblemForm(request.POST)
            input_vars = []
            i = 0
            while True:
                name_key = f'input_name_{i}'
                type_key = f'input_type_{i}'
                name = request.POST.get(name_key)
                var_type = request.POST.get(type_key)
                print(f"Checking {name_key}: {name}, {type_key}: {var_type}")
                if name is None and var_type is None:
                    break
                if name and var_type:
                    input_vars.append({'name': name, 'type': var_type})
                i += 1
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

            test_cases = []
            test_case_data = []
            total_forms = int(request.POST.get('form-TOTAL_FORMS', 0))
            max_index = max([int(k.split('-')[1]) for k in request.POST.keys() if k.startswith('form-') and 'param_' in k] + [total_forms - 1], default=0)
            print(f"Max test case index: {max_index + 1}")
            for i in range(max_index + 1):
                input_dict = {}
                test_case_input = {}
                param_values = request.POST.getlist(f'form-{i}-param_{input_vars[0]["name"]}')
                expected_values = request.POST.getlist(f'form-{i}-expected_output')
                print(f"Test case {i} - param_values: {param_values}, expected_values: {expected_values}")
                if param_values and expected_values:
                    for param, expected in zip(param_values, expected_values):
                        if param and expected:
                            input_dict[input_vars[0]['name']] = param
                            test_case_input[input_vars[0]['name']] = param
                            test_cases.append(type('TestCase', (), {
                                'input_value': json.dumps(input_dict),
                                'expected_output': json.dumps(expected) if return_type != 'None' else expected,
                                'return_type': return_type
                            }))
                            test_case_data.append({
                                'inputs': test_case_input.copy(),
                                'expected_output': expected
                            })
            print(f"Test cases: {test_cases}")
            print(f"Test case data: {test_case_data}")

            if problem_form.is_valid():
                solution_code = problem_form.cleaned_data['solution_code']
                full_function_header = generate_function_header(input_vars, return_type)
                if not solution_code.strip().startswith('def solution'):
                    solution_code = full_function_header.replace('pass', '') + solution_code

                if 'run' in request.POST:
                    print(f"Solution code: {solution_code}")
                    results = run_code_in_docker(solution_code, test_cases, input_vars)
                    all_tests_passed = all(result.get('passed', False) for result in results) and len(results) == len(test_cases)
                    request.session['last_run_results'] = results
                    print(f"Results from run_code_in_docker: {results}, all_tests_passed: {all_tests_passed}")
                    return render(request, 'create_problem.html', {
                        'problem_form': problem_form,
                        'test_case_formset': test_case_formset,
                        'results': results,
                        'solution_code': solution_code,
                        'input_vars': input_vars,
                        'return_type': return_type,
                        'function_header': function_header,
                        'header_generated': True,
                        'test_case_data': test_case_data,
                        'all_tests_passed': all_tests_passed
                    })
                elif 'save' in request.POST:
                    print(f"Re-running tests before save with solution code: {solution_code}")
                    results = run_code_in_docker(solution_code, test_cases, input_vars)
                    all_tests_passed = all(result.get('passed', False) for result in results) and len(results) == len(test_cases)
                    if all_tests_passed:
                        print("Attempting to save problem")
                        problem = problem_form.save(commit=False)
                        problem.created_by = request.user
                        problem.input_vars = input_vars
                        problem.return_type = return_type
                        problem.function_header = function_header
                        problem.solution_code = solution_code
                        problem.save()
                        
                        for test_case in test_cases:
                            TestCase.objects.create(
                                problem=problem,
                                input_value=test_case.input_value,
                                expected_output=test_case.expected_output
                            )
                        print(f"Problem saved with ID: {problem.id}")
                        if 'last_run_results' in request.session:
                            del request.session['last_run_results']
                        return redirect('problem_detail', problem_id=problem.id)
                    else:
                        print("Cannot save: Not all tests passed with current test cases")
                        return render(request, 'create_problem.html', {
                            'problem_form': problem_form,
                            'test_case_formset': test_case_formset,
                            'results': results,
                            'solution_code': solution_code,
                            'input_vars': input_vars,
                            'return_type': return_type,
                            'function_header': function_header,
                            'header_generated': True,
                            'test_case_data': test_case_data,
                            'all_tests_passed': False,
                            'error': 'All test cases must pass with the current configuration before submitting.'
                        })
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
        if 'last_run_results' in request.session:
            del request.session['last_run_results']
        problem_form = ProblemForm()
        return render(request, 'create_problem.html', {
            'problem_form': problem_form,
            'input_vars': [],
            'return_type': 'None',
            'header_generated': False
        })

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
            for tc in test_cases:
                tc.return_type = problem.return_type
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
            for tc in test_cases:
                tc.return_type = problem.return_type
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