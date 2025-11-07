from app import app as app

# This module exposes the Flask WSGI app for Vercel serverless.
# All routes are defined in the root-level app.py. Vercel will import
# this file and use the top-level `app` callable.