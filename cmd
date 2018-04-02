PYTHONPATH=`pwd`:`pwd`/lib twistd --pidfile=/tmp/web_app.pid -ny ./web_app.py
#pkill -F twistd.pid
