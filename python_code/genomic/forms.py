from django import forms

from .models import File, CHROMOSOMES


class VcfForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ('file', 'lab_info')

    def __init__(self, user, case, *args, **kwargs):
        self.user = user
        self.case = case
        super(VcfForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        vcf_file = super(VcfForm, self).save(commit=False)
        vcf_file.size = vcf_file.file.size
        vcf_file.uploader = self.user
        vcf_file.case = self.case
        vcf_file.name = vcf_file.file.name
        if commit:
            vcf_file.save()
        return vcf_file


class SearchByPositionForm(forms.Form):
    chromosome = forms.ChoiceField(required=False, choices=CHROMOSOMES)
    start_position = forms.IntegerField(required=False)
    end_position = forms.IntegerField(required=False)


class SearchByGeneForm(forms.Form):
    gene = forms.CharField(max_length=45, required=False)