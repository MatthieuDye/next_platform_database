"""Forms used in the clinical app."""
from dal import autocomplete

from django import forms

from .models import Case, Diagnosis, Drug, Morphology, Patient, Project, Topography, Treatment


class PatientForm(forms.ModelForm):
    """Form to create patients."""

    class Meta:
        """Model and fields for the form."""

        model = Patient
        fields = ('centre_patient_id', 'birthdate', 'sex')
        widgets = {
            'birthdate': forms.DateInput(attrs={'class': 'datepicker'}),
        }

    def __init__(self, centre, *args, **kwargs):
        """Override the init function."""
        self.centre = centre
        super(PatientForm, self).__init__(*args, **kwargs)

    def save(self, **kwargs):
        """Override the save function."""
        kwargs['commit'] = False
        patient = super(PatientForm, self).save(**kwargs)
        patient.centre = self.centre
        patient.save()
        return patient


class CaseForm(forms.ModelForm):
    """Form to create cases."""

    morphology = forms.ModelChoiceField(
        queryset=Morphology.objects.all(),
        widget=autocomplete.ModelSelect2(url='morphology-autocomplete')
    )
    topography = forms.ModelChoiceField(
        queryset=Topography.objects.all(),
        widget=autocomplete.ModelSelect2(url='topography-autocomplete')
    )
    diagnosis = forms.ModelChoiceField(
        queryset=Diagnosis.objects.all(),
        widget=autocomplete.ModelSelect2(url='diagnosis-autocomplete')
    )

    class Meta:
        """Model and fields for the form."""

        model = Case
        fields = ('project_case_id', 'morphology', 'topography', 'diagnosis', 'diagnosis_date', 'relapse_number', 'status', 'status_date')
        widgets = {
            'diagnosis_date': forms.DateInput(attrs={'class': 'datepicker'}),
            'status_date': forms.DateInput(attrs={'class': 'datepicker'}),
        }

    def __init__(self, patient, *args, **kwargs):
        """Override the init function."""
        self.patient = patient
        super(CaseForm, self).__init__(*args, **kwargs)

    def save(self, **kwargs):
        """Override the save function."""
        kwargs['centre'] = self.patient.centre
        kwargs['name'] = self.patient.centre.name + ' main project'
        default_project, created = Project.objects.get_or_create(kwargs)
        case = super(CaseForm, self).save(commit=False)
        case.patient = self.patient
        case.project = default_project
        case.save()
        return case


class TreatmentForm(forms.ModelForm):
    """Form to create treatment elements"""

    code = forms.ModelChoiceField(
        queryset=Drug.objects.all(),
        widget=autocomplete.ModelSelect2(url='drug-autocomplete')
    )

    def __init__(self, case, *args, **kwargs):
        self.case = case
        super(TreatmentForm, self).__init__(*args, **kwargs)

    class Meta:
        """Model and fields for the form."""

        model = Treatment
        exclude = ('case', )
        # exclude = ()

        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'datepicker'}),
            'end_date': forms.DateInput(attrs={'class': 'datepicker'})
        }

    def save(self, **kwargs):
        """Override the save function."""
        kwargs['commit'] = False
        treatment_elem = super(TreatmentForm, self).save(**kwargs)

        treatment_elem.case = self.case
        treatment_elem.save()
        return treatment_elem
