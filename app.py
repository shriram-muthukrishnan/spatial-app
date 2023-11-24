import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask, request,render_template

load_dotenv()
app = Flask(__name__)
host = os.getenv("hostname")
dbname = os.getenv("database")
user = os.getenv("username")
password = os.getenv("pwd")
port = os.getenv("port_id")

connection = psycopg2.connect(
        host = host,
        dbname = dbname,
        user = 'azureuser',
        password = password,
        port = port
    )

@app.route('/')
def welcome():
    return render_template('index.html')

if __name__=="__main__":
    app.run(debug=False,host='0.0.0.0',port=5000)


@app.post("/movie_recommendation")
def get_recommended_movies():
    data = request.get_json()
    print(data)
    query = data["query"]
    vector_similarity_query = "select * from (select movieid,title,genres, cosine_distance(embedding, cast (azure_openai.create_embeddings('shri-azureai-deployment-1', '" + query + "') as vector(1536))) as cosineformula from Movies_with_tags_dup) t1 where t1.cosineformula is not NULL  order by t1.cosineformula asc LIMIT 5;"
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(vector_similarity_query)
            arr_list = []
            for record in cursor.fetchall():
                obj = []
                obj.append(record[1])
                obj.append(record[2])
                arr_list.append(obj)
            print(arr_list)
    return {"result": arr_list,"message":"Vector recommendations"},201 
