# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-17 09:16
from __future__ import unicode_literals

import logging
import os
from functools import partial

import dirsync

from django.conf import settings
from django.db import migrations

from translate.lang.data import langcode_re


def _file_belongs_to_project(project, filename):
    ext = os.path.splitext(filename)[1][1:]
    filetype_extensions = list(
        project.filetypes.values_list(
            "extension__name", flat=True))
    template_extensions = list(
        project.filetypes.values_list(
            "template_extension__name", flat=True))
    return (
        ext in filetype_extensions
        or (ext in template_extensions))


def _detect_treestyle_and_path(project, proj_trans_path):
    dirlisting = os.walk(proj_trans_path)
    dirpath_, dirnames, filenames = dirlisting.next()

    if not dirnames:
        # No subdirectories
        if filter(partial(_file_belongs_to_project, project), filenames):
            # Translation files found, assume gnu
            return "gnu", ""

    # There are subdirectories
    has_subdirs = filter(
        (lambda dirname: dirname == 'templates'
         or langcode_re.match(dirname)),
        dirnames)
    if has_subdirs:
        return "nongnu", None

    # No language subdirs found, look for any translation file
    # in subdirs
    for dirpath_, dirnames, filenames in os.walk(proj_trans_path):
        if filter(partial(_file_belongs_to_project, project), filenames):
            return "gnu", dirpath_.replace(proj_trans_path, "")
    # Unsure
    return "nongnu", None


def _get_translation_mapping(project):
    old_translation_path = settings.POOTLE_TRANSLATION_DIRECTORY
    proj_trans_path = os.path.join(old_translation_path, project.code)
    old_treestyle, old_path = (
        _detect_treestyle_and_path(project, proj_trans_path)
        if project.treestyle == "auto"
        else (project.treestyle, None))
    project.treestyle = "pootle_fs"
    if old_treestyle == "nongnu":
        return "/<language_code>/<dir_path>/<filename>.<ext>"
    else:
        return "%s/<language_code>.<ext>" % (old_path or "")


def _set_project_config(Config, project_ct, project):
    old_translation_path = settings.POOTLE_TRANSLATION_DIRECTORY
    proj_trans_path = os.path.join(old_translation_path, project.code)
    configs = Config.objects.filter(
        content_type=project_ct,
        object_pk=project.pk)
    configs.delete()
    Config.objects.update_or_create(
        content_type=project_ct,
        object_pk=project.pk,
        key="pootle_fs.fs_url",
        defaults=dict(
            value=proj_trans_path))
    Config.objects.update_or_create(
        content_type=project_ct,
        object_pk=project.pk,
        key="pootle_fs.fs_type",
        defaults=dict(
            value="localfs"))
    Config.objects.update_or_create(
        content_type=project_ct,
        object_pk=project.pk,
        key="pootle_fs.translation_mappings",
        defaults=dict(
            value=dict(default=_get_translation_mapping(project))))


def convert_to_localfs(apps, schema_editor):
    Project = apps.get_model("pootle_project.Project")
    Store = apps.get_model("pootle_store.Store")
    StoreFS = apps.get_model("pootle_fs.StoreFS")
    Config = apps.get_model("pootle_config.Config")
    ContentType = apps.get_model("contenttypes.ContentType")
    project_ct = ContentType.objects.get_for_model(Project)
    old_translation_path = settings.POOTLE_TRANSLATION_DIRECTORY

    for project in Project.objects.exclude(treestyle="pootle_fs"):
        proj_trans_path = os.path.join(old_translation_path, project.code)
        proj_stores = Store.objects.filter(
            translation_project__project=project).exclude(file="")
        _set_project_config(Config, project_ct, project)
        project.treestyle = "pootle_fs"
        project.save()
        store_fs = StoreFS.objects.filter(
            store__translation_project__project=project)
        store_fs.delete()
        for store in proj_stores:
            filepath = store.file.path[len(proj_trans_path):]
            StoreFS.objects.update_or_create(
                project=project,
                store=store,
                defaults=dict(
                    path=filepath,
                    pootle_path=store.pootle_path,
                    last_sync_revision=store.last_sync_revision,
                    last_sync_mtime=store.file_mtime))
        fs_temp = os.path.join(
            settings.POOTLE_FS_WORKING_PATH, project.code)
        dirsync.sync(
            proj_trans_path,
            fs_temp,
            "sync",
            create=True,
            purge=True,
            logger=logging.getLogger(dirsync.__name__))


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('pootle_fs', '0001_initial'),
        ('pootle_format', '0003_remove_extra_indeces'),
        ('pootle_config', '0001_initial'),
        ('pootle_store', '0013_set_store_filetype_again'),
        ('pootle_project', '0016_change_treestyle_choices_label'),
    ]

    operations = [
        migrations.RunPython(convert_to_localfs),
    ]
