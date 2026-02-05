from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_redirect),
    path("databases/", views.database_list, name="database_list"),
    path("databases/manage/", views.database_config_list, name="database_config_list"),
    path("databases/add/", views.database_config_add, name="database_config_add"),
    path("databases/<int:pk>/edit/", views.database_config_edit, name="database_config_edit"),
    path("databases/<int:pk>/delete/", views.database_config_delete, name="database_config_delete"),
    path("databases/test/", views.database_config_test, name="database_config_test"),
    path(
        "databases/<str:db_alias>/schemas/",
        views.schema_list,
        name="schema_list",
    ),
    path(
        "databases/<str:db_alias>/schemas/create/",
        views.schema_create,
        name="schema_create",
    ),
    path(
        "databases/<str:db_alias>/schemas/<str:schema_name>/delete/",
        views.schema_delete,
        name="schema_delete",
    ),
    path(
        "databases/<str:db_alias>/schemas/<str:schema_name>/tables/",
        views.table_list,
        name="table_list",
    ),
    path(
        "databases/<str:db_alias>/schemas/<str:schema_name>/tables/<str:table_name>/",
        views.table_grid,
        name="table_grid",
    ),
    path(
        "databases/<str:db_alias>/schemas/<str:schema_name>/tables/<str:table_name>/save/",
        views.table_save_rows,
        name="table_save_rows",
    ),
    path(
        "databases/<str:db_alias>/schemas/<str:schema_name>/tables/<str:table_name>/insert/",
        views.table_insert_row,
        name="table_insert_row",
    ),
    path(
        "databases/<str:db_alias>/schemas/<str:schema_name>/tables/<str:table_name>/delete/",
        views.table_delete_rows,
        name="table_delete_rows",
    ),
]
