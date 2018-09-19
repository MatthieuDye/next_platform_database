#-*- coding: utf-8 -*-

from django.db import models

class REFERENCE(models.Model):
	class Meta:
		pass

	type = None
	description = None

	gives_details = models.ManyToMany('DRUG_EFFECT')

