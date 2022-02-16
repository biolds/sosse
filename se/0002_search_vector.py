from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('se', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
              CREATE FUNCTION weight_vector() RETURNS trigger AS $$
              BEGIN
                new.vector = setweight(to_tsvector(new.vector_lang, new.title), 'A') ||
                             setweight(to_tsvector(new.vector_lang, new.url), 'A') ||
                             setweight(to_tsvector(new.vector_lang, new.content), 'B');
                return new;
              END
              $$ LANGUAGE plpgsql;

              CREATE TRIGGER vector_column_trigger
              BEFORE INSERT OR UPDATE OF url, title, content, vector_lang
              ON se_document
              FOR EACH ROW EXECUTE PROCEDURE weight_vector();
            ''',

            reverse_sql = '''
              DROP TRIGGER IF EXISTS vector
              ON se_document;
            '''
        ),
    ]
