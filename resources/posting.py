from datetime import datetime
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mysql.connector import Error

import boto3
import sys
import urllib.request

import requests

from config import Config
from mysql_connection import get_connection


class PostingListResouce(Resource) :
    # 포스팅 생성
    @jwt_required()
    def post(self) :
        data = request.get_json()
        userId = get_jwt_identity()

        if data['imgURL'] == "" :
            return {'error' : '이미지를 업로드 해주세요'}, 400
        
        if data['content'] == "" :
            return {'error' : '내용을 입력해주세요'}, 400
        

        # 포스팅 저장
        try:
            connection = get_connection()

            query = '''insert into posting
                        (userId, imgUrl, content)
                        values
                        (%s, %s, %s);'''            

            record = (userId, data['imgURL'], data['content'])

            cursor = connection.cursor()
            cursor.execute(query, record)

            postingId = cursor.lastrowid

            str_tags = data['tags']
            contain = ","
            
            if contain in str_tags :
                str_tags = str_tags.replace(",", "")

            tag = str_tags.split("#")[1:]

            for row in tag :
                tag = row.lower()
                print(tag)
                query = '''select *
                            from tagName
                            where name = %s;''' 
                
                record = (tag, )

                cursor = connection.cursor(dictionary=True)
                cursor.execute(query, record)

                result_list = cursor.fetchall()
                
                # 태그가 db에 저장돼 있을 때
                if len(result_list) != 0:
                    tagNameId = result_list[0]['id']
                    print(tagNameId)

                # 태그가 db에 저장되어 있지 않을 때
                else:
                    query = '''insert into tagName
                                (name)
                                values
                                (%s);'''
            
                    record = (tag, )

                    cursor = connection.cursor()
                    cursor.execute(query, record)

                    tagNameId = cursor.lastrowid

                query = '''insert into tag
                            (postingId, tagNameId)
                            values
                            (%s, %s);'''

                record = (postingId, tagNameId)

                cursor = connection.cursor()
                cursor.execute(query, record)

            
            connection.commit()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500
        
        return {"result" : "success"}, 200
 
    # 모든 포스팅 가져오기(최신순)
    @jwt_required()
    def get(self) :        
        userId = get_jwt_identity()
        offset = request.args.get('offset')
        limit = request.args.get('limit')

        try :

            connection = get_connection()
            
            query = '''select *
                        from posting
                        order by createdAt desc
                        limit '''+offset+''', '''+limit+''';'''
            
            record = (userId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            result_list = cursor.fetchall()

            i = 0
            for row in result_list :
                result_list[i]['createdAt'] = row['createdAt'].isoformat()
                result_list[i]['updatedAt'] = row['updatedAt'].isoformat()
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


class PostingLabelResouce(Resource) :
    # 라벨 생성
    @jwt_required()
    def post(self) :        
        source_language = "en"
        target_language = "ko"

        file = request.files.get('image')        
        userId = get_jwt_identity()

        if file is None :
            return {'error' : '이미지를 업로드 해주세요'}, 400

        currentTime = datetime.now()
        newFileName = currentTime.isoformat().replace(':', '_') + str(userId) +'jpeg'
        file.filename = newFileName        

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
            return {'error' : str(e)}, 500
                
        # rekognition 서비스 이용
        tag_list = self.detect_labels(newFileName, Config.S3_BUCKET)

        newFileName = Config.S3_LOCATION + newFileName
        
        i = 0
        for row in tag_list :
            text_to_translate = row
            tag_list[i] = "#" + self.translate_text(text_to_translate, source_language, target_language)

            if "." in tag_list[i] :                
                tag_list[i] = tag_list[i].replace('.', '')
            i = i+1
            
        
        return {"result" : "success",
                "tagList" : tag_list,
                "fileUrl" : newFileName}, 200

    # 오토 태깅(rekognition)
    def detect_labels(self, photo, bucket):

        client = boto3.client('rekognition', 
                              'ap-northeast-2', 
                              aws_access_key_id = Config.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY)


        response = client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':photo}},
        MaxLabels=5, )

        labels_list = []
        for label in response['Labels']:
            print("Label: " + label['Name'])
            print("Confidence: " + str(label['Confidence']))
                        
            if label['Confidence'] >= 90 :
                labels_list.append(label['Name'])
        
        return labels_list    

    # 태깅 번역
    def translate_text(self, text, source_lang, target_lang):
        url = "https://openapi.naver.com/v1/papago/n2mt"
        headers = {
            "X-Naver-Client-Id": Config.X_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": Config.X_NAVER_CLIENT_SECRET
        }
        data = {
            "source": source_lang,
            "target": target_lang,
            "text": text
        }

        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            translated_text = response.json()["message"]["result"]["translatedText"]
            return translated_text
        else:
            return "번역에 실패했습니다. 상태 코드: {}".format(response.status_code)
        
        
class PostingResource(Resource):
    # 포스팅 상세 보기
    @jwt_required()
    def get(self, postingId):
        user_id = get_jwt_identity()

        try:
            connection = get_connection()
            
            # 포스팅 상세정보 쿼리
            query = '''select p.id as postingId, u.profileUrl,
                                u.nickName, l.level, p.imgURL as postingUrl,
                                t2.name as tagName, p.content, p.createdAt
                        from posting as p
                        join user as u
                        on p.userId = u.id
                        join level as l
                        on u.id = l.userId
                        left join tag as t
                        on t.postingId = p.id
                        join tagName as t2
                        on t2.id = t.tagNameId
                        where p.id = %s;'''
            
            record = (postingId,)
        
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()
            
            tag_list = []
            # 태그가 있을 때
            if len(result_list) != 0 :
                for row in result_list :
                    tag_list.append(row['tagName'])

                i = 0
                for row in result_list :
                    del result_list[i]['tagName']
                    result_list[i]['createdAt'] = row['createdAt'].isoformat()
                    i = i+1
            
            query = '''select p.id as postingId, u.profileUrl,
                                u.nickName, l.level, p.imgURL as postingUrl,
                                p.content, p.createdAt
                        from posting as p
                        join user as u
                        on p.userId = u.id
                        join level as l
                        on u.id = l.userId
                        where p.id = %s;'''
        
            record = (postingId,)
        
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result = cursor.fetchall()
            
            if len(result) == 0 :
                return {"result" : "존재하지 않는 포스팅입니다."}, 400
            
            result[0]['createdAt'] = result[0]['createdAt'].isoformat()            
            
            # 좋아요 누른 유저 가져오기
            query = '''select u.nickName
                        from posting as p
                        join likes as l
                        on p.id = l.postingId
                        join user as u
                        on u.id = l.likerId
                        where p.id = %s;'''
            
            record = (postingId, )

            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result_list = cursor.fetchall()

            liker_list = []
            for row in result_list :
                liker_list.append(row['nickName'])

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error":str(e)}, 500        
        
        return {"result" : "success",
                "item" : result,
                "tagList" : tag_list,
                "likerList" : liker_list}, 200
    
    # 포스팅 수정
    @jwt_required()
    def put(self, postingId):
        data = request.get_json()
        content = data['content']
        tag = data['tags']
        imgURL = data['imgURL']
        userId = get_jwt_identity()       

        if content is None:
            return {'error': '내용을 입력해주세요'}, 400
        
        # 받아온 태그의 공백과 쉼표를 지운다.
        tag = tag.replace(" ", "")        
        tag = tag.replace(",", "")
        
        tag_list = tag.split("#")
        del tag_list[0]
        currentTime = datetime.now()        

        try:
            connection = get_connection()

            # 기존에 있던 태그테이블의 컬럼을 지운다.
            query = '''delete from tag
                        where postingId = %s;'''
            record = (postingId,)
            
            cursor = connection.cursor()
            cursor.execute(query, record)

            if imgURL :
                query = '''update posting
                            set imgURl = %s,
                            content = %s
                            where id = %s and userId = %s;'''
                record = (imgURL, content, postingId, userId)

            else:
                query = '''update posting
                            set content = %s
                            where id = %s and userId = %s;'''
                record = (content, postingId, userId)
                
            cursor = connection.cursor()
            cursor.execute(query, record)

            # 포스팅 수정시 받은 태그가 db에 있는지 확인한다.
            for row in tag_list:                
                query = '''select *
                            from tagName
                            where name = %s;'''
                record = (row, )

                cursor = connection.cursor(dictionary=True)
                cursor.execute(query, record)

                result_list = cursor.fetchall()

                # db에 태그정보가 있을 때 저장한다.
                if len(result_list) != 0:
                    tagNameId = result_list[0]['id']

                # db에 태그정보가 없으면 태그네임 테이블에 저장하고 id값을 세팅한다.
                else:
                    query = '''insert into tagName
                                (name)
                                values
                                (%s);'''
            
                    record = (row, )

                    cursor = connection.cursor()
                    cursor.execute(query, record)

                    tagNameId = cursor.lastrowid

                query = '''insert into tag
                            (tagNameId, postingId)
                            values
                            (%s, %s);'''
  
                record = (tagNameId, postingId)

                cursor = connection.cursor()
                cursor.execute(query, record)

            connection.commit()

            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error':str(e)}, 500
        
        return {'result':'success'}, 200

    # 포스팅 삭제
    @jwt_required()
    def delete(self, postingId):
        
        userId = get_jwt_identity()

        try :
            connection = get_connection()
            query = '''delete from posting
                        where id = %s and userId = %s;'''
            record = (postingId, userId)

            cursor = connection.cursor()
            cursor.execute(query, record)

            connection.commit()

            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {"error":str(e)}, 500

        return {"result":"success"}, 200
      

class PostingPopResource(Resource):
    # 포스팅 인기순 정렬
    @jwt_required()
    def get(self):
        userId = get_jwt_identity()
        offset = request.args.get('offset')
        limit = request.args.get('limit')

        try :

            connection = get_connection()
            
            query = '''select p.*, count(l.id) as likersCnt
                        from posting as p
                        left join likes as l
                        on l.postingId = p.id
                        group by p.id
                        order by likersCnt desc, p.createdAt desc
                        limit ''' + offset + ''', ''' + limit + ''';'''            
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            result_list = cursor.fetchall()

            i = 0
            for row in result_list :
                result_list[i]['createdAt'] = row['createdAt'].isoformat()
                result_list[i]['updatedAt'] = row['updatedAt'].isoformat()
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

