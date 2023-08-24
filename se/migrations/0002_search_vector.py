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

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('se', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
              -- Doc update

              CREATE FUNCTION doc_weight_vector() RETURNS trigger AS $$
              BEGIN
                new.vector = setweight(to_tsvector(new.vector_lang, new.normalized_title), 'A') ||
                             setweight(to_tsvector(new.vector_lang, new.normalized_url), 'A') ||
                             setweight(to_tsvector(new.vector_lang, COALESCE('', (SELECT STRING_AGG(text, ' ') FROM se_link WHERE doc_to_id=new.id))), 'B') ||
                             setweight(to_tsvector(new.vector_lang, new.normalized_content), 'C');
                return new;
              END
              $$ LANGUAGE plpgsql;

              CREATE TRIGGER vector_column_trigger
              BEFORE INSERT OR UPDATE OF normalized_title, normalized_content, normalized_url, vector_lang
              ON se_document
              FOR EACH ROW EXECUTE PROCEDURE doc_weight_vector();

              -- Link update

              CREATE FUNCTION link_weight_vector() RETURNS trigger AS $$
              BEGIN
                UPDATE se_document SET
                    vector = setweight(to_tsvector(vector_lang, se_document.normalized_title), 'A') ||
                             setweight(to_tsvector(vector_lang, se_document.normalized_url), 'A') ||
                             setweight(to_tsvector(vector_lang, COALESCE('', (SELECT STRING_AGG(se_link.text, ' ') FROM se_link WHERE se_link.doc_to_id=se_document.id))), 'B') ||
                             setweight(to_tsvector(vector_lang, se_document.normalized_content), 'C')
                WHERE id = new.doc_to_id;
                RETURN new;
              END
              $$ LANGUAGE plpgsql;

              CREATE TRIGGER link_row_trigger
              BEFORE INSERT OR UPDATE
              ON se_link
              FOR EACH ROW
              WHEN (new.doc_to_id IS NOT NULL)
              EXECUTE PROCEDURE link_weight_vector();
            ''',

            reverse_sql = '''
              DROP TRIGGER link_row_trigger ON se_link;
              DROP TRIGGER vector_column_trigger ON se_document;
              DROP FUNCTION link_weight_vector;
              DROP FUNCTION doc_weight_vector;
            '''
        ),
    ]
