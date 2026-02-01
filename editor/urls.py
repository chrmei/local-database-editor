from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_redirect),
    path("databases/", views.database_list, name="database_list"),
    path(
        "databases/<str:db_alias>/schemas/",
        views.schema_list,
        name="schema_list",
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
]
