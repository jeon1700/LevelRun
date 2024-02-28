from datetime import datetime
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mysql.connector import Error
import pytz

import requests

from config import Config
from mysql_connection import get_connection
      
class MissionResource(Resource):
    # 임무완료
    @jwt_required()
    def post(self):
        userId = get_jwt_identity()
        data = request.get_json()
        mission = "isClear" + str(data['mission'])

        if data['mission'] == 1 :
            exp = 10
        elif data['mission'] == 2 :
            exp = 30
        elif data['mission'] == 3 :
            exp = 50
        elif data['mission'] == 4 :
            exp = 300
        elif data['mission'] == 5 :
            exp = 500

        try :            
            connection = get_connection()
            
            query = '''select *
                        from mission
                        where userId = %s;'''
            
            record = (userId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            # 테이블에 임무 정보가 없으면 insert 한다
            if len(result_list) == 0 :
                query = '''insert into mission
                            (userId, ''' + mission + ''')
                            values
                            (%s, 1);'''
                
                record = (userId,)
                cursor = connection.cursor()
                cursor.execute(query, record)

            # 테이블에 임무 정보가 있으면 오늘 날짜가 있는지 확인한다
            else :
                is_equal = 0
                # 현재 시간 정보를 받아온다
                seoul_timezone = pytz.timezone('Asia/Seoul')
                current_time = datetime.now().astimezone(seoul_timezone)
                current_time = current_time.strftime("%Y-%m-%d")

                # db에서 받아온 표준시간을 서울시간으로 변경후 비교한다.
                for row in result_list :
                    db_time = row['createdAt']
                    db_time = db_time.astimezone(seoul_timezone)
                    db_time = db_time.strftime("%Y-%m-%d")
                    
                    if current_time  == db_time :
                        is_equal = 1
                        date_time = row['createdAt']

                #  오늘 날짜 정보가 있으면 update 한다
                if is_equal == 1 :
                    query = '''update mission
                                set ''' + mission + '''= 1
                                where userId = %s and createdAt = %s'''
                    
                    record = (userId, date_time)
                    cursor = connection.cursor()
                    cursor.execute(query, record)

                # 오늘 날짜가 없으면 insert 한다.
                else :
                    query = '''insert into mission
                            (userId, ''' + mission + ''')
                            values
                            (%s, 1);'''
                
                    record = (userId, )
                    cursor = connection.cursor()
                    cursor.execute(query, record)

            # 레벨 테이블을 조회한다.
            query = '''select *
                        from level
                        where userId = %s;'''
            record = (userId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result = cursor.fetchall()

            level = result[0]['level']
            userExp = result[0]['exp']            

            # 레벨업일 때
            if ((level*1000) < (userExp+exp)) :
                setExp = (userExp+exp) - (level*1000)
                query = '''update level
                            set level = %s, exp = %s
                            where userId = %s;'''
                record = (level+1, setExp, userId)
                cursor = connection.cursor()
                cursor.execute(query, record)
            
            # 레벨업이 아닐 때
            else :
                setExp = (userExp+exp)
                query = '''update level
                            set exp = %s
                            where userId = %s;'''
                record = (setExp, userId)
                cursor = connection.cursor()
                cursor.execute(query, record)

            query = '''select *
                        from level
                        where userId = %s;'''
            record = (userId,)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            connection.commit()
            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"result": "fail", "error": str(e)}, 500

        return {"result": "success",
                "items" : result_list}, 200

class MissionInfoResource(Resource):
    # 임무완료 정보 가져오기
    @jwt_required()
    def get(self):
        userId = get_jwt_identity()

        try :            
            connection = get_connection()

            query = '''select *
                        from level;'''
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            result = cursor.fetchall()

            # 현재 시간 정보를 받아온다
            seoul_timezone = pytz.timezone('Asia/Seoul')
            current_time = datetime.now().astimezone(seoul_timezone)
            current_day = current_time.strftime("%Y-%m")
            current_time= current_time.strftime("%Y-%m-%d")

            i = 0
            for row in result :
                if row['userId'] == userId :
                    rank = i + 1
                i = i + 1
            
            query = '''select l.*, m.isClear1, m.isClear2, 
                        m.isClear3, m.isClear4, m.isClear5, m.createdAt
                        from level as l
                        left join mission as m
                        on m.userId = l.userId
                        where l.userId = %s
                        order by m.createdAt desc;'''
            
            record = (userId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            i = 0
            isClear4 = 0
            isClear5 = 0
            for row in result_list :                
                db_time = row['createdAt']
                db_time = db_time.astimezone(seoul_timezone)
                db_day = db_time.strftime("%Y-%m")
                db_time = db_time.strftime("%Y-%m-%d")

                if current_day == db_day :
                    if row['isClear4'] == 1 :
                        isClear4 = 1
                    if row['isClear5'] == 1 :
                        isClear5 = 1
                        
                del result_list[i]['createdAt']
                i = i+1
            
            result_list[0]['isClear4'] = isClear4
            result_list[0]['isClear5'] = isClear5

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"result": "fail", "error": str(e)}, 500

        return {"result": "success",
                "rank" : rank,
                "items" : result_list}, 200

