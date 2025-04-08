# Configuração do banco de dados - prioriza PostgreSQL no Render
database_url = os.getenv('DATABASE_URL', 'sqlite:///financas.db')

# Corrige URL do PostgreSQL para versões mais recentes do SQLAlchemy
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)