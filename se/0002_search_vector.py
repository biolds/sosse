from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('se', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
              CREATE FUNCTION weight_vector() RETURNS trigger AS $$
              begin
                new.vector = setweight(to_tsvector('english', new.title), 'A') ||
                             setweight(to_tsvector('english', new.url), 'A') ||
                             setweight(to_tsvector('english', new.content), 'B');
                return new;
              end
              $$ LANGUAGE plpgsql;

              CREATE TRIGGER vector_column_trigger
              BEFORE INSERT OR UPDATE OF url, title, content
              ON se_document
              FOR EACH ROW EXECUTE PROCEDURE weight_vector();
            ''',

            reverse_sql = '''
              DROP TRIGGER IF EXISTS vector
              ON se_document;
            '''
        ),
    ]
