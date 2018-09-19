#-*- coding: utf-8 -*-

from django.db import models

class VARIANT(models.Model):
	class Meta:
		pass

	alteration = None
	protein_change = None
	oncogenicity = None
	mutation_effect = None
	full_name = None

	influences = models.ManyToMany('TRANSCRIPT')

