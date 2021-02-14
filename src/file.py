from fbclient import FirebaseApp
import pandas as pd
import json

storage = FirebaseApp.st
db = FirebaseApp.fs
ALLOWED_EXTENSIONS = {'csv'}


def allowed_file(filename):
    try:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    except:
        raise


class File():
    def upload(request):
            
        # LOAD FILE
        print(request.files)
        try:uploaded_file = request.files['dataset']
        except: 
            return {
                'message':'La petición no contiene archivo'
            }, 400
        
        
        if uploaded_file.filename == '':
            return {
                "message":'El archivo no contiene nombre'
            }, 400
        else: filename = uploaded_file.filename
        try: allowed_file(uploaded_file.filename)
        except:
            return {
                "message": "El archivo de estar en formato csv"
            }, 400
        
        
        reffilename = filename.replace(' ', '_')
        
        
        
        # local_path = 'api/uploads/'+filename
        print('Archivo ok')
        
        # READ FILE
        df = pd.read_csv(uploaded_file,  decimal=".", header=0, thousands=r",")
        
        
        # NOTE IMPORTANTE BORRAR ESTA LINEA EN EL MOMENTO DE LANZAR A PRODUCCIÓN
        df = df.head()
        
        columns = df.columns.tolist()
        count = df.shape[0]
            
        
        #STORAGE IN FIREBASE
        # Agregamos los datos válidos para obtener un id de firestore
        files_ref = db.collection(u'prodlists')
        doc = files_ref.add({
            'items_cant': int(count),
            'file_name': filename,
        })
        doc_id = doc[1].id
        print('Id obtenido')
        
        
        # UPLOAD FILE CSV TO STORAGE
        cloud_path = 'prodlists/'+doc_id+'/'
        df.fillna(value=0, inplace=True)
        df_file = df.to_csv()
        fileURL = upload_file(cloud_path, reffilename, df_file)
        print('Archivo cargado a storage')
        
        
        result_data = {
            'items_cant': int(count),
            'fileURL':fileURL,
            'file_name': filename,
            'doc_id':doc_id, 
            'columns': columns,
            'file_ref': reffilename
        }
        
        print('Documento actualizado')
        files_ref.document(doc_id).update(result_data)
        
        
        return {
            'status': 201,
            'message': 'ok', 
            'result': result_data
            }, 201


    def define_columns(request):
        
        try: 
            fileid = request.json['fileid']
            doc_ref = db.collection(u'prodlists').document(fileid)
        except:
            return {
                'message': 'La petición no contiene la url del archivo'
            }, 400
            
        try: synonyms_cols = request.json['columns']
        except:
            return {
                'message': 'La petición no contiene la lista de columnas'
            }, 400

        if request.json['stockValue']:
            stockValue = request.json['stockValue']
        
        
        try:
            doc = doc_ref.get()
            doc_URL = doc.to_dict()['fileURL']
            file_ref = doc.to_dict()['file_ref']
        except: 
            return {
                'message': 'El archivo no exite o fue eliminado', 
            }, 404
        
        
        # READ DOCUMENT
        df = pd.read_csv(doc_URL,  decimal=".", thousands=",")  
        print('File readed')
        
        
        required_cols = [
            "id",
            "precio",
        ]

        default_cols = [
            "categorias",
            "descripcion",
            "onStock",
            "referencia",
            "stockCant",
            "imagenUrl"
        ]

        avalible_cols = []
        
        for key, value in synonyms_cols.items():
            # Se intenta cambiar las columnas, si no es posible, se rechaza la petición
            try:
                df = df.rename(columns={value:key})
                avalible_cols.append(key)
            except: return {
                'message': f'fallo al intentar cambiar columna {key} a {value}',
                'status': 404
            }, 404
        print('columns renamed')
        
        
        # The stockValue must to be a dict to changes values for booleans
        # {'yes': True, 'no': False}
        if stockValue:
            try:df.replace({'onStock':stockValue})
            except:
                return {
                "message": "No se pudo cambiar los valores de onStock"
            }, 400
        
        
        try:
            for req_col in required_cols:
                try: df[req_col]
                except:
                    raise
        except:
            return {
                "message": "Hace falta una columna requerida. Son necesarios id y precio"
            }, 400
        print('Todas las columnas bien')
        
        product_model_list = df[avalible_cols]
        items = product_model_list.to_json(orient="records")
        items = json.loads(items)
        print('Default columns stored')
        
        avalible_cols.remove('id')
        as_details = df.drop(avalible_cols, axis=1)
        items_details = as_details.to_json(orient="records")
        items_details = json.loads(items_details)
        print('Details columns stored')
        
        
        
        firebase_status = 'ok'
        try:storage.bucket().delete_blob(f'prodlists/{fileid}/{file_ref}')
        except Exception as e:
            firebase_status = str(e)
            pass            
        
        try: doc_ref.delete()
        except Exception as e:
            firebase_status = str(e)
            pass
        
        print(firebase_status)
        
        return {
            'items': items,
            'items_details': items_details,
            'firebase_status': firebase_status
        }, 200
        


def upload_file(cloud_path, filename, file):
    bucket = storage.bucket()
    cloud_file = bucket.blob(cloud_path+filename)
    cloud_file.upload_from_string(file, content_type='application/octet-stream')
    cloud_file.make_public()
    return cloud_file.public_url

