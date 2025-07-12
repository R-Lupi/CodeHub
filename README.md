# CodeHub

Welcome to **CodeHub**, a Django-based web application designed to help users solve coding problems, track their progress, and engage with a community of learners. This project includes features like problem-solving with test cases, user authentication, favoriting problems, and solution submission with real-time testing using Docker. This was completed over the course of half a semester as part of my undergraduate CS studies.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Overview
CodeHub is a platform where users can:
- Browse and solve coding problems.
- Submit solutions and run them against test cases.
- Track their progress with ratings and favoriting features.
- View community solutions and engage with other users.

The project leverages Django for the backend, Docker for isolated code execution, and static files for assets like the project logo.

## Features
- User authentication and authorization.
- Problem detail pages with test case execution.
- Solution submission with real-time feedback.
- Favoriting problems for easy access.
- Community solution viewing (excluding own solutions).
- Static asset management (e.g., logo, profile images).

## Prerequisites
Before setting up the project, ensure you have the following installed:
- **Python 3.13** or later
- **pip** (Python package manager)
- **virtualenv** (recommended for environment isolation)
- **Docker** (for running test cases)
- **Git** (for version control)
- **Node.js** and **npm** (if using JavaScript dependencies, e.g., for templates)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/codehub.git
cd codehub
