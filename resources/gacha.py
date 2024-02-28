from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mysql.connector import Error
import random
from config import Config
from mysql_connection import get_connection
class GachaResource(Resource):
    # 뽑기(가챠) 획득하고 컬렉션에 저장
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        check = True
        img_url = None
        try:
            connection = get_connection()
            # 유저의 상자 갯수 조회
            query_box_count = '''SELECT userId, count
                                FROM randomBox
                                WHERE userId = %s;'''
            record_box_count = (user_id, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query_box_count, record_box_count)
            result = cursor.fetchall()
            box_count = result[0]['count']
            # 상자 갯수가 0인 경우
            if box_count == 0:
                return {"result": "fail", "error": "상자 갯수가 0개입니다."}, 404
            # 상자 갯수 줄이기
            query_update_box = '''UPDATE randomBox
                                SET count = count - 1
                                WHERE userId = %s;'''
            record_update_box = (user_id, )
            box_count = box_count-1
            cursor.execute(query_update_box, record_update_box)
            # 랜덤으로 캐릭터 뽑기
            rand = random.randint(1, 36)
            # 유저가 방금 랜덤으로 뽑은 캐릭터가 있는지 확인
            query_check_character = '''SELECT characterId
                                        FROM collection
                                        WHERE userId = %s and characterId = %s;'''
            record_check_character = (user_id, rand)
            cursor.execute(query_check_character, record_check_character)
            result_check_character = cursor.fetchall()
            # 이미 보유한 캐릭터인 경우
            if len(result_check_character) != 0 :
                check = False
            if(check) :
                # 새로운 몬스터면 DB에 저장
                query_insert_character = '''INSERT INTO collection
                                            (userId, characterId)
                                            VALUES (%s, %s);'''
                record_insert_character = (user_id, rand)
                cursor.execute(query_insert_character, record_insert_character)
            query_img_url = '''select *
                                from `character`
                                where id = %s;'''
            record_img_url = (rand, )
            cursor.execute(query_img_url, record_img_url)
            img_url = cursor.fetchall()
            connection.commit()
            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {"result": "fail", "error": str(e)}, 500
        
        return {"result": "success",
                "items" : img_url,
                "boxCount" : box_count}, 200