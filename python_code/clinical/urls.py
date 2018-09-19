from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^patients/$', views.PatientsListView.as_view(), name='patients_list'),
    url(r'^patients/(?P<patient_id>[0-9]+)/$', views.PatientView.as_view(), name='patient'),
    url(r'^cases/$', views.CasesListView.as_view(), name='cases_list'),
    url(r'^cases/(?P<case_id>[0-9]+)/$', views.CaseView.as_view(), name='case'),
    url(r'^report/(?P<patient_id>[0-9]+)/$', views.ReportView.as_view(), name='report'),
    url(r'^treatments/(?P<case_id>[0-9]+)/$', views.UpdateTreatmentsView.as_view(), name='update-treatments'),
    url(r'^treatment/$', views.TreatmentView.as_view(), name='treatment'),
    url(r'^api/morphologies', views.MorphologyAutocomplete.as_view(), name='morphology-autocomplete'),
    url(r'^api/topographies', views.TopographyAutocomplete.as_view(), name='topography-autocomplete'),
    url(r'^api/diagnoses', views.DiagnosisAutocomplete.as_view(), name='diagnosis-autocomplete'),
    url(r'^api/drugs', views.DrugAutocomplete.as_view(), name='drug-autocomplete'),
    url(r'^api/patients$', views.PatientListEndpoint.as_view(), name='patient-list-api'),
    url(r'^api/patients/(?P<centre_id>[0-9]+)$', views.PatientListEndpoint.as_view(), name='patient-list-api-centre'),
    url(r'^api/cases$', views.CaseListEndpoint.as_view(), name='case-list-api'),
    url(r'^api/cases/(?P<project_id>[0-9]+)$', views.CaseListEndpoint.as_view(), name='case-list-api-project'),
    url(r'^api/projects$', views.ProjectListEndpoint.as_view(), name='project-list-api'),
    url(r'^api/projects/(?P<centre_id>[0-9]+)$', views.ProjectListEndpoint.as_view(), name='project-list-api-centre')
]
