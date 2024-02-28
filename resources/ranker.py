from datetime import datetime
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mysql.connector import Error

import boto3

from config import Config
from mysql_connection import get_connection


class RankerResource(Resource):
    # 상위 랭커 20명 프로필 이미지 가져오기
    @jwt_required()
    def get(self) :
        
        userId = get_jwt_identity()
        
        try :
            connection = get_connection()
            
            query = '''select u.id, rank() over(order by level desc) as ranking, 
                            u.nickName, u.profileUrl, l.level, u.id as userId
                        from user u
                        join level l
                        on u.id = l.userId
                        order by l.level desc
                        limit 0, 20;'''
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            result_list = cursor.fetchall()

            i = 0
            for row in result_list :
                query = '''select *
                            from posting
                            where userId = %s
                            order by createdAt desc
                            limit 0, 1;'''
                
                record = (row['userId'],)

                cursor =connection.cursor(dictionary=True)
                cursor.execute(query, record)
                result = cursor.fetchall()
                
                if len(result) != 0 :
                    result_list[i]['postingId'] = result[0]['id']
                
                i = i + 1

                
                

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"result": "fail", "error": str(e)}, 500

        return {"result": "success", 
                "items": result_list,
                "count":len(result_list)}, 200    

class RankingListResource(Resource):
    # 유저들의 레벨정보를 가져온다.
    @jwt_required()
    def get(self):        
        userId = get_jwt_identity()

        try:            
            connection = get_connection()

            query = '''select u.nickName, l.*
                        from user as u
                        join level as l
                        on u.id = l.userId
                        order by l.level desc, l.exp desc, u.createdAt;'''

            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            result_list = cursor.fetchall()

            i = 0
            rank = 0
            for data in result_list :
                if(userId == result_list[i]['userId']) :
                    rank = i+1
                i = i+1

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"result": "fail", "error": str(e)}, 500

        return {"result": "success", 
                "items": result_list,
                "myRank" : rank,
                "count":len(result_list)}, 200