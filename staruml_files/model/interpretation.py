#-*- coding: utf-8 -*-

from django.db import models

class INTERPRETATION(models.Model):
	class Meta:
		pass

	description = None
	tier = None

	concerns = models.ManyToMany('MORPHOLOGY')
	concerns = models.ManyToMany('TOPOGRAPHY')
	 = models.ForeingKey('GENE', on_delete=models.PROTECT)

