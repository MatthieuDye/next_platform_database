from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^files/$', views.FilesListView.as_view(), name='files'),
    url(r'^files/(?P<file_id>[0-9]+)/$', views.FileView.as_view(), name='file'),
    url(r'^api/fileupload', views.FileUploadEndpoint.as_view(), name='file_upload_endpoint'),
    url(r'^search/$', views.SearchVariantsView.as_view(), name='search_variants'),
    url(r'^gene/(?P<gene_id>[0-9]+)$', views.GeneInfoView.as_view(), name='gene_info'),
    url(r'^drug/(?P<drug_id>[0-9]+)$', views.DrugView.as_view(), name='drug_info'),
    url(r'^extra-info/(?P<gene_name>[A-Z0-9]+)$', views.ExtraInfoEndpoint.as_view(), name='extra_info_endpoint'),
    url(r'^batch-upload/$', views.BatchUploadView.as_view(), name='batch_upload'),
    url(r'^api/batch_upload/$', views.BatchUploadApiEndpoint.as_view(), name='batch_upload_endpoint'),
]
