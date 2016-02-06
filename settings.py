#CELERY_ACCEPT_CONTENT = ['pickle']
#CELERY_TASK_SERIALIZER = ['pickle']
#CELERY_ACCEPT_CONTENT = ['json']
#CELERY_TASK_SERIALIZER = 'json'
#CELERY_RESULT_SERIALIZER = 'json'

CELERY_ROUTES = {
    'cmover_del.procFiles': {'queue': 'mover_del.files', 'delivery_mode':1},
    'cmover_del.procDir': {'queue': 'mover_del.dir', 'delivery_mode':1},
    'cmover.procFiles': {'queue': 'mover.files', 'delivery_mode':1},
    'cmover.procDir': {'queue': 'mover.dir', 'delivery_mode':1},
    'cmover_dirtime.procDir': {'queue': 'mover_dirtime.dir', 'delivery_mode':1}
}

CELERY_ACKS_LATE=True
CELERY_IGNORE_RESULT=True

