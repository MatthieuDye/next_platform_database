#-*- coding: utf-8 -*-

from django.db import models

class DRUG_EFFECT(models.Model):
	class Meta:
		pass

	description = None
	tier = None
	level = None
	actionable = None

	advises = models.ManyToMany('DRUG')

