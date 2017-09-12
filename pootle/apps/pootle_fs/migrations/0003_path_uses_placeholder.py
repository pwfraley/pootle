# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-09-12 15:17
from __future__ import unicode_literals

from django.db import migrations

from django.conf import settings


def set_path_with_placeholder(apps, schema_editor):
    Config = apps.get_model("pootle_config.Config")
    ContentType = apps.get_model("contenttypes.ContentType")
    Project = apps.get_model("pootle_project.Project")
    project_ct = ContentType.objects.get_for_model(Project)
    for project in Project.objects.all():
        config = Config.objects.get(
            content_type=project_ct,
            object_pk=project.pk,
            key="pootle_fs.fs_url")
        if config.value.startswith(settings.POOTLE_TRANSLATION_DIRECTORY):
            config.value = (
                "{POOTLE_TRANSLATION_DIRECTORY}%s"
                % config.value[
                    len(settings.POOTLE_TRANSLATION_DIRECTORY.rstrip("/")) + 1:])
            config.save()


class Migration(migrations.Migration):

    dependencies = [
        ('pootle_fs', '0002_convert_localfs'),
    ]

    operations = [
        migrations.RunPython(set_path_with_placeholder),
    ]
