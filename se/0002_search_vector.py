from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('se', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
              CREATE TRIGGER vector_column_trigger
              BEFORE INSERT OR UPDATE OF url, title, content, vector
              ON se_document
              FOR EACH ROW EXECUTE PROCEDURE
              tsvector_update_trigger(
                vector, 'pg_catalog.english', url, title, content
              );

              UPDATE se_document SET vector = NULL;
            ''',

            reverse_sql = '''
              DROP TRIGGER IF EXISTS vector
              ON se_document;
            '''
        ),
    ]
