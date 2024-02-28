from cgi import FieldStorage
from datetime import datetime
from fileinput import filename
from flask import request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error
from PIL import Image

from email_validator import EmailNotValidError, validate_email
from utils import check_password, hash_password

import boto3

# 회원가입
class UserRegisterResource(Resource) :
    def post(self) :
        data = request.get_json()        

        # 이메일 유효성 검사
        try :
            validate_email(data['email'])

        except EmailNotValidError as e :
            print(e)
            return {"result" : str(e)}, 400

        # 비밀번호 길이 검사
        if len(data['password']) < 4 or len(data['password']) > 14 :
            return {"result" : "비밀번호 길이가 올바르지 않습니다."}, 400

        # 단방향 암호화된 비밀번호를 저장
        password = hash_password(data['password'])

        try :
            connection = get_connection()

            # 닉네임 중복 검사
            query = '''select *
                    from user
                    where nickName = %s;'''
            record = (data['nickName'],)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result_list = cursor.fetchall()

            if len(result_list) != 0 :
                return {"result" : "중복된 닉네임이 존재 합니다."}, 406
            
            #  이메일 중복 검사
            query = '''select *
                    from user
                    where email = %s;'''
            record = (data['email'],)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result_list = cursor.fetchall()

            if len(result_list) != 0 :
                return {"result" : "중복된 이메일이 존재 합니다."}, 406
            

            # 중복검사 후 이상 없으면 회원가입 진행

            query = '''insert into user
                    (nickName, email, password, type)
                    value(%s, %s, %s, 0);'''
            record = (data['nickName'], data['email'], password)

            cursor = connection.cursor()
            cursor.execute(query, record)

            # 회원가입시 생성한 유저아이디를 데이터베이스에서 가져와
            # 초기 레벨 테이블 정보를 넣어준다.
            userId = cursor.lastrowid

            query = '''insert into level
                        (userId)
                        values
                        (%s);'''

            record = (userId,)
            
            # 커서 초기화 
            cursor = connection.cursor()
            cursor.execute(query, record)

            # exercise 테이블 생성
            query = '''insert into exercise
                        (userId)
                        values
                        (%s);'''

            record = (userId,)

            cursor = connection.cursor()
            cursor.execute(query, record)            

            # randomBox 테이블 생성
            query = '''insert into randomBox
                        (userId)
                        values
                        (%s);'''

            record = (userId,)

            cursor = connection.cursor()
            cursor.execute(query, record)

            connection.commit()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"result" : str(e)}, 500
        
        # user 테이블의 id로 JWT 토큰을 만들어야 한다.
        access_token = create_access_token(userId)
        
        return {"result" : "success", "accessToken" : access_token}, 200


    pass

# 로그인
class UserLoginResource(Resource) :
    def post(self) :
        data = request.get_json()
        try :
            connection = get_connection()

            query = '''select id, nickName, email, password 
                        from user
                        where email = %s;'''
            
            record = (data['email'],)

            # 딕셔너리 형태로 가져옴
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"result" : str(e)}, 500        

        # 가입정보 확인
        if len(result_list) == 0 :
            return {"result" : "회원가입된 정보가 없습니다."}, 400
                
        password = str(data['password'])
        

        check = check_password(password, result_list[0]['password'])
        if check == False :
            return {"result" : "비밀번호가 맞지 않습니다."}, 406
        
        # 암호화 토큰생성
        access_token = create_access_token(result_list[0]['id'])

        return {"result" : "success", "accessToken" : access_token}, 200
    

# 카카오 로그인 닉네임 중복 체크
class KakaoLoginResource(Resource) :
    def post(self) :
        data = request.get_json()
        nickName = data["nickName"]
        email = data["email"]        
        profileUrl = data['profileUrl']        

        try :
            connection = get_connection()

            query = '''select id, nickName, email, password
                    from user
                    where email = %s;'''
            
            record = (email,)

            # 딕셔너리 형태로 가져옴
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            # 이메일 정보가 있을 때
            if len(result_list) != 0 :
                if result_list[0]['password'] is not None :
                    cursor.close()
                    connection.close()
                    return {"result" : "해당 이메일 주소로 가입된 정보가 있습니다."}, 406
            
                # 카카오 유저 데이터 베이스에 정보가 있을 경우 로그인 진행 
                else :
                    # 암호화 토큰생성
                    cursor.close()
                    connection.close()

                    access_token = create_access_token(result_list[0]['id'])

                    return {"result" : "success", "accessToken" : access_token}, 200
            
            
            # 데이터 베이스에 가입정보가 없으면 정보를 저장한다.
            # 닉네임 중복검사
            query = '''select id, nickName, email, password
                    from user
                    where nickName = %s;'''
            
            record = (nickName,)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            # 이미 만들어진 이메일이 있을 때
            if len(result_list) != 0 :
                cursor.close()
                connection.close()
                return {"result" : "중복된 닉네임이 존재 합니다."}, 406
            
            
            # 회원가입
            query = '''insert into user
                        (nickName, email, profileUrl, type)
                        value(%s, %s, %s, 1);'''
            record = (nickName, email, profileUrl)

            # 위에서 한번 사용했기 때문에 커서 초기화 시킨다.
            connection.cursor()
            cursor.execute(query, record)

            
            # 회원가입시 생성한 유저아이디를 데이터베이스에서 가져와
            # 초기 레벨 테이블 정보를 넣어준다.
            userId = cursor.lastrowid

            # level 테이블 생성
            query = '''insert into level
                        (userId)
                        values
                        (%s);'''

            record = (userId,)
            
            # 커서 초기화 
            cursor = connection.cursor()
            cursor.execute(query, record)

            # exercise 테이블 생성
            query = '''insert into exercise
                        (userId)
                        values
                        (%s);'''

            record = (userId,)

            cursor = connection.cursor()
            cursor.execute(query, record)            

            # randomBox 테이블 생성
            query = '''insert into randomBox
                        (userId)
                        values
                        (%s);'''

            record = (userId,)

            cursor = connection.cursor()
            cursor.execute(query, record)  

            connection.commit()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"fail" : str(e)}, 500        
        
        # 암호화 토큰생성
        access_token = create_access_token(userId)

        return {"result" : "success", "accessToken" : access_token}, 200

# 유저 정보 수정, 유저 정보 가져오기
class UserInfoResource(Resource) :
    # 유저 정보 수정
    @jwt_required()
    def put(self) :

        nickName = request.form.get('nickName')
        file = request.files.get('imgProfile')
        userId = get_jwt_identity()

        # 파일 처리
        current_time = datetime.now()
        new_file_name = current_time.isoformat().replace(':', '_') + str(userId) +'jpeg'
        file.filename = new_file_name
        s3 = boto3.client('s3',
                          aws_access_key_id = Config.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY)
        try:
            s3.upload_fileobj(file, Config.S3_BUCKET,
                              file.filename,
                              ExtraArgs = {'ACL':'public-read',
                                           'ContentType':'image/jpeg'})
        except Exception as e:
            print(e)
            return {'result':str(e)}, 500
    

        try:
            connection = get_connection()

            # 닉네임 중복 체크
            query = '''select id, nickName, email, password
                    from user
                    where nickName = %s;'''
            
            record = (nickName,)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            if len(result_list) != 0 :
                cursor.close()
                connection.close()
                return {"result" : "중복된 닉네임이 존재 합니다."}, 406

            # 유저정보 업데이트
            query = '''update user
                        set profileUrl = %s,
                        nickName = %s
                        where id = %s;'''
            profileUrl = Config.S3_LOCATION + file.filename
            record = (profileUrl, nickName, userId)
            cursor = connection.cursor()
            cursor.execute(query, record)
            connection.commit()
            cursor.close()
            connection.close()
        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'result':str(e)}, 500
        return {'result':'success'}, 200

    # 유저 정보가져오기
    @jwt_required()
    def get(self) :
        userId = get_jwt_identity()

        try :
            connection = get_connection()
            query = '''select u.id, u.nickName, u.email, u.profileUrl, 
                        u.createdAt, l.level, l.exp, r.count as boxCount
                    from user as u
                    join level as l
                    on u.id = l.userId
                    join  randomBox as r
                    on r.userId = u.id
                    order by l.level desc, l.exp desc, u.createdAt;'''
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query,)
            result_list = cursor.fetchall()            

            i = 0                
            for row in result_list :            
                if(userId == row['id']) :
                    rank = i+1
                    data = row
                    data['createdAt'] = row['createdAt'].isoformat()
                i = i+1


            query ='''select c.*, ch.imgUrl
                    from collection as c
                    join `character` as ch
                    on c.characterId = ch.id
                    where c.userId = %s;'''
            record = (userId,)

            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            i = 0                
            for row in result_list :
                result_list[i]['createdAt'] = row['createdAt'].isoformat()
                i = i+1


            cursor.close()
            connection.close()
        
        except Error as e:
            print(e)
            cursor.close()
            connection.close()

            return {"result" : "fail"}, 500
        
        
        return {"result" : "success",
                "id" : data['id'], 
                "rank" : rank,
                "nickName" : data['nickName'],
                "email" : data['email'],
                "profileUrl" : data['profileUrl'],
                "level" : data['level'],
                "exp" : data['exp'],
                "boxCount" : data['boxCount'],
                "createdAt" : data['createdAt'],
                "items" : result_list}, 200

jwt_blocklist = set()
class UserLogoutResource(Resource) :            # 로그아웃
    @jwt_required()
    def delete(self) :
        jti = get_jwt()['jti']          # 토큰안에 있는 jti 정보
        print()
        print(jti)
        print()
        jwt_blocklist.add(jti)

        return {"result" : "success"}, 200


