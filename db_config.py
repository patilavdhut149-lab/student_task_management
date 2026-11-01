
import mysql.connector
import os

def get_db_connection():
    return mysql.connector.connect(
        host="gateway01.ap-northeast-1.prod.aws.tidbcloud.com",
        port=4000,
        user="3BYuxSeV89cKwtX.root",
        password=os.getenv("TIDB_PASSWORD"),
        database="student_task_manager",
        ssl_ca="certs/ca.pem",
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )
