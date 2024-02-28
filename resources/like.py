from datetime import datetime
from email_validator import EmailNotValidError, validate_email
from flask import request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error


class LikeResource(Resource):
    # 좋아요 처리
    @jwt_required()
    def post(self, postingId):
        user_id = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''select *
                        from likes
                        where likerId = %s and postingId = %s;'''
            
            record = (user_id, postingId)
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, record)
            result = cursor.fetchall()

            # 좋아요 처리
            if len(result) == 0 :
                query = '''insert into `likes`
                        (likerId, postingId)
                        values
                        (%s, %s);'''
                record = (user_id, postingId)
            
                cursor = connection.cursor()
                cursor.execute(query, record)                

            # 좋아요 해제
            else :
                query = '''delete from likes
                            where likerId = %s and postingId = %s;'''
                
                record = (user_id, postingId)            
                cursor = connection.cursor()
                cursor.execute(query, record)                
            
            
            connection.commit()
            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error":str(e)}, 500


        return {"result":"success"}, 200
    
    # 좋아요 유무 확인
    @jwt_required()
    def get(self, postingId):
        user_id = get_jwt_identity()
        try :
            connection = get_connection()

            query = '''select *
                        from likes
                        where likerId = %s and postingId = %s;'''
            
            record = (user_id, postingId)
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, record)
            result = cursor.fetchall()

            isLike = 0

            if len(result) != 0 :
                isLike = 1
            
            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error":str(e)}, 500


        return {"result" : "success",
                "userId" : user_id,
                "isLike" : isLike}, 200