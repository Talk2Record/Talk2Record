# Talk2Record

Talk2Record converts WhatsApp voice notes from business staff into structured business records using AI

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

License: Apache Software License 2.0

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      uv run python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    uv run mypy talk2record

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    uv run coverage run -m pytest
    uv run coverage html
    uv run open htmlcov/index.html

#### Running tests with pytest

    uv run pytest

### `uv.lock` consistency (local vs CI)

The CI lockfile check uses a pinned uv Docker image (`ghcr.io/astral-sh/uv:python3.13-bookworm-slim`).
To avoid local/CI drift, regenerate the lock file with the same image:

    cd backend
    make uv-lock-ci

When you change Python dependencies:

1. Edit `pyproject.toml`
2. Run `make uv-lock-ci`
3. Commit both `pyproject.toml` and `uv.lock`

Avoid running ad-hoc local `uv lock` with a different uv version if you want CI to stay deterministic.

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

### Celery

This app comes with Celery.

To run a celery worker:

```bash
cd talk2record
uv run celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important _where_ the celery commands are run. If you are in the same folder with _manage.py_, you should be right.

To run [periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html), you'll need to start the celery beat scheduler service. You can start it as a standalone process:

```bash
cd talk2record
uv run celery -A config.celery_app beat
```

or you can embed the beat service inside a worker with the `-B` option (not recommended for production use):

```bash
cd talk2record
uv run celery -A config.celery_app worker -B -l info
```

### Email Server

In development, it is often nice to be able to see emails that are being sent from your application. For that reason local SMTP server [Mailpit](https://github.com/axllent/mailpit) with a web interface is available as docker container.

Container mailpit will start automatically when you will run all docker containers.
Please check [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally-docker.html) for more details how to start all containers.

With Mailpit running, to view messages that are sent by your application, open your browser and go to `http://127.0.0.1:8025`

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).

## Paddle billing (local dev)

Checkout requires both Paddle dashboard configuration and Django admin settings:

1. In the **Paddle sandbox** dashboard ([Checkout settings](https://sandbox-vendors.paddle.com/checkout-settings)):
   - Set **Default payment link** to `http://localhost:3000/checkout`
   - Approve `http://localhost:3000` under website approval if prompted
2. Run `uv run python manage.py seed_data` (or configure manually in Django admin → Paddle settings):
   - `default_payment_link`: `http://localhost:3000/checkout`
   - `client_side_token`: your Paddle.js token (`test_…` in sandbox)
   - Paddle API key + webhook secret for server-side calls
3. Sync plan prices to Paddle from Django admin after changing trial periods.

The frontend opens Paddle.js overlay checkout using `transactionId` from `POST /api/billing/change-plan/`. The `/checkout` page handles payment-link redirects (`?_ptxn=`) from Paddle emails and payment-method updates.

For Paddle webhooks in local dev, expose the backend with `make ngrok` and point your sandbox notification URL at `https://<your-ngrok-host>/api/billing/webhooks/paddle/`. Local settings already allow `*.ngrok-free.app` and `*.ngrok.io` in `ALLOWED_HOSTS`.
