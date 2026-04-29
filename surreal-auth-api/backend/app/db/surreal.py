from surrealdb import Surreal

from app.core import config

db = Surreal(config.SURREAL_URL)

def connect():
    db.signin({"username": config.SURREAL_USERNAME, "password": config.SURREAL_PASSWORD})
    db.use(config.SURREAL_NAMESPACE, config.SURREAL_DB)
