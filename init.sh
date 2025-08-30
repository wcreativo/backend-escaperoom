#!/bin/bash

# Initialize Django project
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

echo "EscapeRooms21 Django backend initialized!"
