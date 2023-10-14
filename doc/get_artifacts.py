#!/usr/bin/python3
# Copyright 2022-2023 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

import os
import gitlab
import requests
from io import BytesIO
from zipfile import ZipFile


PROJECT_ID = 41220530
jobs_name = ['doc_gen', 'functional_tests_chromium']

gl = gitlab.Gitlab()
project = gl.projects.get(PROJECT_ID)

commit_hash = os.environ['READTHEDOCS_GIT_COMMIT_HASH']
commit = project.commits.get(commit_hash)
pipeline_id = commit.last_pipeline['id']
print('Pipeline ID %s' % pipeline_id)
pipeline = project.pipelines.get(pipeline_id)

for job in pipeline.jobs.list():
    if job.name in jobs_name:
        if job.status != 'success':
            print('Job %s did not succeed, state: %s' % (job.web_url, job.state))
            exit(1)

        artifact = job.web_url + '/artifacts/download'

        print('Download artifact for %s at %s' % (job.name, artifact))
        req = requests.get(artifact)
        try:
            with ZipFile(BytesIO(req.content)) as zip_file:
                zip_file.extractall()
        except:  # noqa
            with open('/tmp/artifact', 'wb') as f:
                f.write(req.content)
            raise
        jobs_name.remove(job.name)

if len(jobs_name):
    print('Job(s) %s not found' % (', '.join(jobs_name)))
    exit(1)
