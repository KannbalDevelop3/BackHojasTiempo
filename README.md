Versión Python 3.9+

# BackHojasTiempo
#Ejecutar Migraciones (Cambios en la DB) en windows 
python manage.py makemigrations
python manage.py migrate

# Ejecutar Migraciones (Cambios en la DB) en linux
python3 manage.py makemigrations
python3 manage.py migrate

#Ejecutar servidor a nivel local
python manage.py runserver 8081
#Ejecutar en servidor (Solo Linux)
gunicorn --bind 0.0.0.0:8081 hojas_tiempo.wsgi:application

