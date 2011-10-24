import inspect

from django.db import models as django_models
from django.contrib import admin

from finance import models as finance_models

for model_name in dir(finance_models):
    model = getattr(finance_models, model_name)
    if inspect.isclass(model) and issubclass(model, django_models.Model):
       admin_interface = getattr(finance_models, model_name+'Admin', None)
       if admin_interface:
          admin.site.register(model, admin_interface)
       else:
          admin.site.register(model)
